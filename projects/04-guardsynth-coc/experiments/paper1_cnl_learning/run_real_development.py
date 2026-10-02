"""Matched real-image scene18 launch check; never a speed cohort or efficacy study."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import random
import subprocess
import time

import run as learning

ROOT = learning.ROOT
BASE = ROOT / 'artifacts/projects/guardsynth-coc/restricted/guardsynth-eblc-learning-001'
READINESS = ROOT / 'artifacts/projects/guardsynth-coc/restricted/guardsynth-paper1-training-readiness-001'
EXPORT = READINESS / 'development-data-2026-09-08-001'


def digest(path):
    with path.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def verified_examples():
    manifest = json.loads((EXPORT / 'RUN_MANIFEST.json').read_text())
    # Verify immutable output bytes and the recorded scope; do not rerun the old survey exporter.
    for name, expected in manifest['output_hashes'].items():
        if digest(EXPORT / name) != expected:
            raise ValueError('export output drift: ' + name)
    examples = [json.loads((EXPORT / (arm.lower() + '_development.jsonl')).read_text()) for arm in ('L0', 'L3')]
    for x in examples:
        if (x['dataset_scope'] != 'DEVELOPMENT_SFT_DEBUG_ONLY' or not x['development_training_allowed']
                or x['main_training_allowed'] or x['main_test_eligibility'] or x['split'] != 'dev'
                or x['preview_only'] or digest(Path(x['image'])) != x['image_sha256']):
            raise ValueError('scene18 development authority/identity mismatch')
    if (examples[0]['common_example_sha256'] != examples[1]['common_example_sha256']
            or examples[0]['input'] != examples[1]['input'] or examples[0]['action'] != examples[1]['action']):
        raise ValueError('unmatched real examples')
    return examples


def idle_gpu(index):
    raw = subprocess.check_output(['nvidia-smi', f'--id={index}',
        '--query-gpu=index,uuid,memory.used,memory.free,utilization.gpu', '--format=csv,noheader,nounits'], text=True).strip()
    fields = [s.strip() for s in raw.split(',')]
    if len(fields) != 5 or int(fields[2]) > 100 or int(fields[3]) < 30000 or int(fields[4]) != 0:
        raise RuntimeError('GPU is occupied; refusing to share or interrupt: ' + raw)
    return {'physical_index': index, 'uuid': fields[1], 'snapshot': raw}


def execute(output, train=False, gpu=4):
    if output.exists():
        raise FileExistsError(output)
    examples = verified_examples()
    resource = idle_gpu(gpu) if train else None
    if train:
        os.environ['CUDA_VISIBLE_DEVICES'] = resource['uuid']
    os.environ['HF_HUB_OFFLINE'] = '1'
    os.environ['TOKENIZERS_PARALLELISM'] = 'false'
    import torch
    from transformers import AutoProcessor
    torch.set_num_threads(4)
    processor = AutoProcessor.from_pretrained(learning.MODEL_PATH, local_files_only=True)
    batches, metrics = [], []
    for example in examples:
        full, prompt = learning.encode(processor, example)
        n = prompt['input_ids'].shape[1]
        assert (full['labels'][:, :n] == -100).all()
        assert full['labels'][:, n:].equal(full['input_ids'][:, n:])
        batches.append(full)
        metrics.append({'arm': example['arm'], 'prompt_tokens': n, 'sequence_tokens': full['input_ids'].numel(),
            'supervised_tokens': int((full['labels'] != -100).sum()), 'pixel_values_shape': list(full['pixel_values'].shape),
            'image_grid_thw': full['image_grid_thw'].tolist(), 'assistant_only_mask_verified': True})
    output.mkdir(parents=True, exist_ok=False, mode=0o700)
    def write(name, value):
        (output / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
    for example in examples:
        (output / (example['arm'].lower() + '_development.jsonl')).write_text(json.dumps(example, ensure_ascii=False) + '\n')
    config = {'model_id': learning.MODEL_ID, 'model_revision': learning.REVISION, 'arms': ['L0', 'L3'],
        'seed': 42, 'optimizer_steps_per_arm': 1, 'batch_size': 1, 'learning_rate': 2e-4, 'weight_decay': .01,
        'lora_r': 8, 'lora_alpha': 16, 'lora_dropout': 0., 'max_sequence_length': 8192, 'truncate': False,
        'precision': 'bfloat16', 'attention': 'sdpa', 'vision_training': False,
        'target_modules': 'language_model attention q_proj/k_proj/v_proj/o_proj',
        'loss': 'ASSISTANT_ONLY_ALL_TARGET_TOKENS_EQUAL_WEIGHT',
        'same_optimizer_budget': True, 'matched_compute_claim': False,
        'main_training_allowed': False, 'one_frame_vs_review_21_frame_mismatch': True}
    write('locked_smoke_config.json', config)
    write('processor_checks.json', metrics)
    # Config is written before any model result or optimizer step.
    results = []
    if train:
        idle_gpu(gpu)  # Recheck immediately before model allocation.
        from transformers import Qwen3VLForConditionalGeneration
        from peft import LoraConfig, TaskType, get_peft_model
        if not torch.cuda.is_available():
            raise RuntimeError('CUDA unavailable in authorized environment')
        device = torch.device('cuda:0')
        model = Qwen3VLForConditionalGeneration.from_pretrained(learning.MODEL_PATH,
            local_files_only=True, dtype=torch.bfloat16, attn_implementation='sdpa').to(device)
        model.config.use_cache = False
        targets = [name for name, module in model.named_modules() if isinstance(module, torch.nn.Linear)
            and 'language_model' in name and name.rsplit('.', 1)[-1] in {'q_proj','k_proj','v_proj','o_proj'}]
        lora = LoraConfig(r=8, lora_alpha=16, lora_dropout=0., bias='none', task_type=TaskType.CAUSAL_LM, target_modules=targets)
        for i, (example, batch_cpu) in enumerate(zip(examples, batches)):
            random.seed(42); torch.manual_seed(42); torch.cuda.manual_seed_all(42)
            adapter = example['arm'].lower()
            if i == 0:
                model = get_peft_model(model, lora, adapter_name=adapter)
                model.enable_input_require_grads()
            else:
                model.add_adapter(adapter, lora)
            model.set_adapter(adapter)
            trainable = {n:p for n,p in model.named_parameters() if p.requires_grad}
            if not trainable or any('lora_' not in n or 'language_model' not in n for n in trainable):
                raise RuntimeError('trainable scope drift')
            before = {n:p.detach().cpu().clone() for n,p in trainable.items()}
            initial = hashlib.sha256(b''.join(p.float().numpy().tobytes() for p in before.values())).hexdigest()
            batch = {k:v.to(device) for k,v in batch_cpu.items()}
            image_tokens = int((batch['input_ids'] == model.config.image_token_id).sum())
            if image_tokens == 0: raise RuntimeError('missing image tokens')
            optimizer = torch.optim.AdamW(trainable.values(), lr=2e-4, weight_decay=.01)
            model.train(); optimizer.zero_grad(set_to_none=True)
            started = time.monotonic()
            torch.cuda.reset_peak_memory_stats(device)
            loss = model(**batch, use_cache=False).loss
            if not torch.isfinite(loss): raise RuntimeError('nonfinite real-image loss')
            loss.backward()
            grad = float(torch.nn.utils.clip_grad_norm_(list(trainable.values()), 1.))
            if not 0 < grad < float('inf'): raise RuntimeError('invalid gradient')
            optimizer.step(); torch.cuda.synchronize()
            changes = [float((p.detach().cpu()-before[n]).abs().max()) for n,p in trainable.items()]
            if not any(changes): raise RuntimeError('no parameter update')
            model.save_pretrained(output / 'adapters', selected_adapters=[adapter])
            r = {'arm': example['arm'], 'optimizer_steps': 1, 'loss': float(loss.detach()),
                'gradient_norm': grad, 'initial_adapter_sha256': initial, 'changed_tensors': sum(v>0 for v in changes),
                'max_parameter_delta': max(changes), 'trainable_parameters': sum(p.numel() for p in trainable.values()),
                'image_tokens': image_tokens, 'seconds': time.monotonic()-started,
                'peak_gpu_bytes': torch.cuda.max_memory_allocated(device), 'performance_evidence': False}
            results.append(r); write(adapter + '_training.json', r); print(json.dumps(r), flush=True)
            del optimizer, before, batch, loss
            torch.cuda.empty_cache()
        if len({r['initial_adapter_sha256'] for r in results}) != 1:
            raise RuntimeError('unpaired adapter initialization')
    result = {'status': 'REAL_IMAGE_DEVELOPMENT_SMOKE_COMPLETE' if train else 'REAL_IMAGE_PROCESSOR_PREFLIGHT_COMPLETE',
        'project_id': 'guardsynth-coc', 'unique_scene_count': 1, 'arm_records': 2, 'speed_training_scenes': 0,
        'optimizer_steps': len(results), 'arms': results, 'gpu': resource, 'processor_checks': metrics,
        'main_training_scenes': 0, 'independent_test_scenes': 0, 'effect': 'NOT_EVALUATED',
        'authority': 'EXISTING_DEVELOPMENT_TRAINING_ALLOWED_PLUS_CURRENT_USER_BOUNDED_SMOKE_REQUEST'}
    write('RESULT.json', result)
    (output / 'REPORT_KO.md').write_text('# 실제 scene18 개발 실행\n\n'
        f'기존 검토된 진입 과제1장면/L0·L3 각1행. optimizer steps={len(results)}. 속도 과제와 본 성능 실험이 아니다.\n'
        '원본 CoC/검토 CNL/ACTION/이미지 재사용, assistant-only mask·이미지 tensor·무절단 검증. '
        '기존 21-frame 검토와1-frame 입력 차이는 유지하며 효과/일반화·main test를 주장하지 않는다.\n')
    manifest = {'project_id':'guardsynth-coc','run_id':output.name,'created_at_utc':datetime.now(timezone.utc).isoformat(),
        'status':'COMPLETE','input_hashes':{str(p.relative_to(ROOT)):digest(p) for p in
            [EXPORT/'RUN_MANIFEST.json',EXPORT/'l0_development.jsonl',EXPORT/'l3_development.jsonl',EXPORT/'scene18_input.jpg']},
        'code_hashes':{str(p.relative_to(ROOT)):digest(p) for p in [Path(__file__),Path(learning.__file__)]},
        'model_file_hashes':{str(p):digest(p) for p in learning.MODEL_PATH.iterdir() if p.is_file()},
        'output_hashes':{str(p.relative_to(output)):digest(p) for p in output.rglob('*') if p.is_file()},
        'network_used':False}
    write('RUN_MANIFEST.json',manifest)
    return result


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('mode',choices=['prepare','train']);p.add_argument('--run-id',required=True);p.add_argument('--gpu',type=int,default=4)
    a=p.parse_args()
    if not __import__('re').fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*-[0-9]+',a.run_id):p.error('invalid run-id')
    print(json.dumps(execute(BASE/a.run_id,a.mode=='train',a.gpu),ensure_ascii=False,indent=2))
