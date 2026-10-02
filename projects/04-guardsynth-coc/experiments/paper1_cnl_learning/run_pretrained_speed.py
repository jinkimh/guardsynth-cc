"""Frozen blind, pretrained development baseline; no adapters or training labels in inference."""
import argparse
import base64
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import re
import time

import run_real_development as real

ACTIONS = ('MAINTAIN_SPEED', 'DECELERATE', 'STOP_OR_WAIT', 'START_OR_ACCELERATE')
PROMPT = ('시간 순서의 전방 영상 프레임입니다. 마지막 관찰 시점에서 에고 차량이 지금 시작할 '
          '속도 행동 하나를 선택하세요. 이후 상황을 추측하지 마세요.\n'
          'MAINTAIN_SPEED: 이동 중 현재 속도 유지(정지 유지 아님).\n'
          'DECELERATE: 완전 정지를 목표로 하지 않는 감속.\n'
          'STOP_OR_WAIT: 이동 중이면 정지를 목표로 감속, 정지 중이면 대기.\n'
          'START_OR_ACCELERATE: 정지 중 출발 또는 이동 중 속도 높이기.\n'
          '정보가 부족하여 선택할 수 없으면 UNDETERMINED를 출력하세요. '
          '설명 없이 위 영문 행동 이름 하나 또는 UNDETERMINED만 출력하세요.')


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def prepare(output):
    if output.exists():
        raise FileExistsError(output)
    intake = real.READINESS / 'speed-action-intake-2026-09-29-001'
    path = intake / 'development_action_inputs.jsonl'
    manifest = json.loads((intake / 'RUN_MANIFEST.json').read_text())
    if real.digest(path) != manifest['output_hashes'][path.name]:
        raise ValueError('blind input drift')
    rows = [json.loads(s) for s in path.read_text().splitlines()]
    packets, frozen = {}, []
    for row in rows:
        p = real.ROOT / row['packet_ref']
        if str(p) not in packets:
            if real.digest(p) != row['packet_sha256']:
                raise ValueError('packet drift')
            packets[str(p)] = json.loads(p.read_text())
        scene = packets[str(p)]['scenes'][int(row['scene_pointer'].split('/')[-1])]
        if scene['sample_id'] != row['sample_id']:
            raise ValueError('scene identity drift')
        frames = []
        for actual, expected in zip(scene['frames'], row['frames'], strict=True):
            data = base64.b64decode(actual['data_url'].split(',', 1)[1])
            if (hashlib.sha256(data).hexdigest() != expected['sha256']
                    or actual['timestamp_us'] != expected['timestamp_us']
                    or actual['timestamp_us'] > scene['event_timestamp_us']):
                raise ValueError('frame hash/time drift')
            frames.append({'timestamp_us': actual['timestamp_us'], 'sha256': expected['sha256'],
                           'data_url': actual['data_url']})
        frozen.append({'sample_id': row['sample_id'], 'frames': frames})
    output.mkdir(parents=True, exist_ok=False, mode=0o700)
    write(output / 'blind_inputs.json', frozen)
    write(output / 'protocol_lock.json', {
        'label': 'PRETRAINED_DEVELOPMENT_BASELINE', 'locked_at_utc': datetime.now(timezone.utc).isoformat(),
        'model_id': real.learning.MODEL_ID, 'revision': real.learning.REVISION,
        'prompt': PROMPT, 'sampling': 'ALL_PROVIDED_CAUSAL_FRAMES_CHRONOLOGICAL',
        'resize': 'PIL_LANCZOS_THUMBNAIL_MAX_640_BY_640_NO_UPSCALE',
        'do_sample': False, 'max_new_tokens': 48, 'seed': 42, 'batch_size': 1,
        'input_sha256': real.digest(path), 'frozen_inputs_sha256': real.digest(output / 'blind_inputs.json'),
        'code_sha256': real.digest(Path(__file__)), 'scene_count': len(frozen),
        'frame_count': sum(len(r['frames']) for r in frozen),
        'adapters': None, 'optimizer_updates': 0, 'main_test': False,
        'answer_coc_cnl_in_input': False, 'single_selection_not_four_assessment_reproduction': True,
        'split_lock_ref': str((real.BASE / 'm18-cohort-feasibility-2026-09-29-001/exploratory_split_lock.json').relative_to(real.ROOT))})
    return {'prepared_scenes': len(frozen), 'output': str(output)}


def infer(output, gpu, device='cuda:0'):
    if (output / 'predictions.jsonl').exists():
        raise FileExistsError('prediction attempt exists; do not overwrite or tune')
    lock = json.loads((output / 'protocol_lock.json').read_text())
    if (real.digest(output / 'blind_inputs.json') != lock['frozen_inputs_sha256']
            or real.digest(Path(__file__)) != lock['code_sha256']):
        raise ValueError('frozen protocol/input/code drift')
    if device == 'cpu':
        available = int(next(s.split()[1] for s in Path('/proc/meminfo').read_text().splitlines()
                             if s.startswith('MemAvailable:'))) * 1024
        if available < 24 * 1024**3 or os.getloadavg()[0] > os.cpu_count() / 2:
            raise RuntimeError('CPU resource check failed')
        resource = {'device': 'cpu', 'threads': 4, 'available_memory_bytes': available,
                    'load_average': os.getloadavg(), 'gpu_used': False}
        os.environ['CUDA_VISIBLE_DEVICES'] = ''
    else:
        resource = real.idle_gpu(gpu)
        os.environ['CUDA_VISIBLE_DEVICES'] = resource['uuid']
    os.environ['HF_HUB_OFFLINE'] = '1'
    os.environ['TOKENIZERS_PARALLELISM'] = 'false'
    import torch
    from PIL import Image
    from transformers import AutoProcessor, Qwen3VLForConditionalGeneration
    torch.set_num_threads(4)
    torch.manual_seed(lock['seed'])
    processor = AutoProcessor.from_pretrained(real.learning.MODEL_PATH, local_files_only=True)
    if device != 'cpu': real.idle_gpu(gpu)
    model = Qwen3VLForConditionalGeneration.from_pretrained(real.learning.MODEL_PATH,
        local_files_only=True, dtype=torch.bfloat16, attn_implementation='sdpa').to(device).eval()
    rows = json.loads((output / 'blind_inputs.json').read_text())
    with (output / 'predictions.jsonl').open('x') as stream:
        for row in rows:
            images = []
            for frame in row['frames']:
                image = Image.open(io.BytesIO(base64.b64decode(frame['data_url'].split(',', 1)[1]))).convert('RGB')
                image.thumbnail((640, 640), Image.Resampling.LANCZOS)
                images.append(image)
            content = [{'type': 'image'} for _ in images] + [{'type': 'text', 'text': lock['prompt']}]
            text = processor.apply_chat_template([{'role': 'user', 'content': content}],
                                                  tokenize=False, add_generation_prompt=True)
            batch = processor(text=[text], images=images, return_tensors='pt').to(device)
            start = time.monotonic()
            with torch.inference_mode():
                tokens = model.generate(**batch, do_sample=False, max_new_tokens=lock['max_new_tokens'])
            raw = processor.decode(tokens[0, batch['input_ids'].shape[1]:], skip_special_tokens=True).strip()
            action = raw if raw in ACTIONS + ('UNDETERMINED',) else 'INVALID_OUTPUT'
            record = {'sample_id': row['sample_id'], 'action': action, 'raw_output': raw,
                      'prompt_tokens': batch['input_ids'].shape[1], 'seconds': time.monotonic() - start}
            stream.write(json.dumps(record, ensure_ascii=False) + '\n'); stream.flush()
            print(json.dumps({'sample_id': row['sample_id'], 'completed': True}), flush=True)
    # References are first read AFTER every model prediction has been durably written.
    from score_speed_development import score
    target = real.READINESS / 'speed-action-intake-2026-09-29-001/development_action_targets.jsonl'
    intake_manifest = json.loads((target.parent / 'RUN_MANIFEST.json').read_text())
    if real.digest(target) != intake_manifest['output_hashes'][target.name]:
        raise ValueError('scoring reference drift')
    result = score([json.loads(s) for s in target.read_text().splitlines()],
                   [json.loads(s) for s in (output / 'predictions.jsonl').read_text().splitlines()])
    result.update(label=lock['label'], optimizer_updates=0, trained_L0=False, fresh_main_test=False)
    write(output / 'RESULT.json', result)
    write(output / 'RUN_MANIFEST.json', {'project_id': 'guardsynth-coc', 'run_id': output.name,
        'status': 'COMPLETE', 'resource': resource, 'targets_sha256': real.digest(target),
        'output_hashes': {p.name: real.digest(p) for p in output.iterdir() if p.is_file()}})
    return result


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--stage', choices=['prepare', 'infer'], required=True)
    p.add_argument('--run-id', required=True); p.add_argument('--gpu', type=int, default=4)
    p.add_argument('--device', choices=['cpu','cuda:0'], default='cuda:0')
    a = p.parse_args()
    if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*-[0-9]+', a.run_id): p.error('invalid run id')
    out = real.BASE / a.run_id
    print(json.dumps(prepare(out) if a.stage == 'prepare' else infer(out, a.gpu,a.device), ensure_ascii=False, indent=2))
