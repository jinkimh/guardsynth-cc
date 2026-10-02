"""Frozen six-arm expansion: prior five controls plus executable EBLC/CNL.

No checkpoint selection or threshold fitting on validation/test. The run uses
the final fixed-budget checkpoint and reports all outcomes, including failures.
"""
import argparse
from dataclasses import asdict, replace
from datetime import datetime, timezone
import gc
import hashlib
import json
import os
from pathlib import Path
import re
import time

import numpy as np
import temporal_training_data as d
from run_real_development import idle_gpu

ARMS = ('P0', 'P1', 'P2', 'NATURAL_GUARD', 'SHUFFLED_GUARD', 'LOGIC_GUARD')
SEEDS = (42, 17, 123)
SPLITS = ('validation', 'test', 'paraphrase', 'unseen_duration')
DATA = d.t.BASE / 'temporal-training-data-2026-09-29-001'
FIELDS = {'accuracy': 'correct', 'guard_violation_rate': 'guard_violation',
          'hold_violation_rate': 'hold_violation', 'deadlock_rate': 'deadlock',
          'goal_completion_rate': 'goal_complete', 'safe_goal_completion_rate': 'safe_goal_complete',
          'coverage': 'valid', 'contract_swap_pair_accuracy': 'pair_correct'}


def mode(arm):
    return {'P0': 'COC_ONLY', 'P1': 'RICH_COC', 'P2': 'RICH_COC',
            'NATURAL_GUARD': 'NATURAL_GUARD', 'SHUFFLED_GUARD': 'NATURAL_GUARD',
            'LOGIC_GUARD': 'LOGIC_GUARD'}[arm]


def examples(split, arm, seed):
    underlying = split if split in ('train', 'validation') else 'test'
    rows = d.load_examples(DATA, underlying, arm if arm in ('P0', 'P1', 'P2') else 'P1')
    result = []
    for e in rows:
        duration = e.required_clear_duration
        if split == 'unseen_duration':
            # Exact 0.1-second precision; all entry offsets shift +0.3 seconds.
            duration = .8 if e.contract_level == 'short' else 1.8
            scene = replace(e.scene, candidates=tuple(replace(c,
                entry_time=None if c.entry_time is None else (round(c.entry_time * 1000) + 300) / 1000)
                for c in e.scene.candidates))
            e = replace(e, scene=scene, required_clear_duration=duration)
            target = d.t.independent_score(e, 'INVALID')['independent_target']
            e = replace(e, target=target)
        raw = d.t.contract(duration)
        guard = d.t.world._guard(duration, split == 'paraphrase')
        # Shared held-out paraphrase removes P1/P2 wording differences, not meaning.
        cnl = guard if split == 'paraphrase' else d.t.render(raw)
        logic = ('INVARIANT occupied(conflict_zone) -> ego_before_stop_line; '
                 f'RELEASE clear_duration_s >= {duration:.1f}; '
                 'FALLBACK uncertain(occupancy) -> HOLD')
        e = replace(e, guard_text=guard, rich_coc_text=d.t.world.COC_TEXT + ' ' +
                    (cnl if arm == 'P2' else guard), logic_guard_text=logic)
        result.append(e)
    if arm == 'SHUFFLED_GUARD' and split == 'train':
        result = d.t.world.shuffled_guard_control(result, seed + 77777)
    return result


def signature(rows, arm):
    encoded = [{'scene': asdict(e.scene), 'duration': e.required_clear_duration,
                'prompt': d.t.world.prompt_for(e, mode(arm)), 'target': e.target} for e in rows]
    return hashlib.sha256(json.dumps(encoded, sort_keys=True).encode()).hexdigest()


def score(example, prediction):
    result = d.t.independent_score(example, prediction)
    candidate = next((c for c in example.scene.candidates if c.label == prediction), None)
    entry = None if candidate is None or candidate.entry_time is None else round(candidate.entry_time * 1000)
    clear = round(example.scene.clear_time * 1000)
    status = 'INVALID_OUTPUT_NOT_EXECUTABLE' if candidate is None else d.action_test(
        round(example.required_clear_duration * 1000), clear, entry)
    if candidate is not None and status != ('UNSAT' if result['guard_violation'] else 'SAT'):
        raise ValueError('executable EBLC disagrees with independent environment')
    result.update(hold_violation=bool(candidate and entry is not None and entry < clear),
                  goal_complete=bool(candidate and entry is not None), eblc_status=status,
                  semantic_cluster=f'clear-{clear}', clear_ms=clear, entry_ms=entry,
                  enters=bool(candidate and entry is not None))
    return result


def pair_rows(rows):
    groups = {}
    for row in rows:
        groups.setdefault(row['scene_id'], []).append(row)
    for pair in groups.values():
        if len(pair) != 2 or {r['contract_level'] for r in pair} != {'short', 'long'}:
            raise ValueError('incomplete contract pair')
        for row in pair:
            row['pair_correct'] = all(r['correct'] for r in pair)
    return rows


def metrics(rows):
    pair_rows(rows)
    return {name: sum(r[field] for r in rows) / len(rows) for name, field in FIELDS.items()}


def verify_hashes(base, manifest):
    for name, value in manifest['output_hashes'].items():
        if d.t.sha(base / name) != value:
            raise ValueError('frozen output drift: ' + name)
    for name, value in manifest.get('input_hashes', {}).items():
        if d.t.sha(d.t.ROOT / name) != value:
            raise ValueError('frozen input drift: ' + name)


def prepare(path):
    if path.exists():
        raise FileExistsError(path)
    verify_hashes(DATA, json.loads((DATA / 'RUN_MANIFEST.json').read_text()))
    path.mkdir(parents=True)
    cfg = {'protocol_id': 'temporal-expanded-six-arm-v0.1', 'arms': ARMS, 'seeds': SEEDS,
           'train_rows': 960, 'evaluation_rows_per_split': 240, 'evaluation': SPLITS,
           'epochs': 3, 'batch_size': 2, 'gradient_accumulation': 8, 'learning_rate': .0002,
           'lora_rank': 8, 'lora_alpha': 16, 'lora_dropout': .05,
           'optimizer_updates_per_arm_seed': 180, 'total_optimizer_updates': 3240,
           'checkpoint_policy': 'FINAL_FIXED_BUDGET_NO_VALIDATION_SELECTION',
           'model_revision': json.loads(d.t.CONFIG.read_text())['model_revision'],
           'initialization': 'SAME_PRETRAINED_BASE_EACH_ARM_SEED_NO_OLD_ADAPTER',
           'metrics': FIELDS, 'bootstrap_replicates': 2000, 'bootstrap_seed': 20260929,
           'cluster': 'CLEAR_TIME_WITH_ALL_CANDIDATE_ROTATIONS_PATTERNS_AND_CONTRACT_PAIRS',
           'primary_comparisons': ['P2-P0', 'P2-P1'],
           'claim': 'CONTROLLED_SYNTHETIC_EFFECT_PRESERVATION_NOT_VERIFICATION_CAUSAL_GAIN',
           'test_exposure_policy': 'NO_TUNING_FROM_TEST_OR_VALIDATION',
           'success_criteria': json.loads(d.t.CONFIG.read_text())['criteria'],
           'criteria_scope': 'TEST_POINT_CRITERIA_ONLY_GENERALIZATION_REPORTED_SEPARATELY',
           'historical_comparison': 'DESCRIPTIVE_DIFFERENT_TRAINING_BUDGET_NOT_CAUSAL_DATA_SCALING',
           'prior_controls': 'All five original controls plus P2; logic text is not the executable oracle.',
           'paraphrase_note': 'P0/LOGIC inputs unchanged; not independent additional evidence.',
           'limits': ['60 synthetic images, not diverse physical environments.',
                      'P0 input lacks duration and can have conflicting target pairs.',
                      '3 seeds and10 test clear-time clusters do not establish formal equivalence.',
                      '240 test variants share images with paraphrase/unseen-duration; report separately.',
                      'UNKNOWN/occlusion and reoccupation are not tested.']}
    d.dump(path / 'protocol.json', cfg)
    training = {}
    for arm in ARMS:
        training[arm] = {}
        for seed in SEEDS:
            rows = examples('train', arm, seed)
            if len(rows) != cfg['train_rows']:
                raise ValueError('unexpected training count')
            training[arm][str(seed)] = signature(rows, arm)
        with (path / f'evaluation_{arm.lower()}.jsonl').open('w') as stream:
            for split in SPLITS:
                for e in examples(split, arm, SEEDS[0]):
                    if not score(e, e.target)['correct']:
                        raise ValueError('reference disagreement')
                    stream.write(json.dumps({'split': split, 'example': asdict(e),
                        'prompt': d.t.world.prompt_for(e, mode(arm))}) + '\n')
    d.dump(path / 'training_signatures.json', training)
    sources = [Path(__file__), Path(d.__file__), Path(d.t.__file__), d.t.CONFIG,
               DATA / 'RUN_MANIFEST.json',
               d.t.PRIOR / 'vlm_guard_learning/temporal_guard_world.py',
               d.t.PRIOR / 'vlm_guard_learning/train_qwen_temporal_guard_lora.py',
               d.t.PRIOR / 'vlm_guard_learning/train_qwen_guard_lora.py']
    d.dump(path / 'RESULT.json', {'status': 'PROTOCOL_FROZEN_BEFORE_TRAINING',
        'planned_fits': 18, 'planned_predictions': 17280, 'optimizer_updates': 0})
    d.dump(path / 'RUN_MANIFEST.json', {'project_id': 'guardsynth-coc',
        'input_hashes': {str(p.relative_to(d.t.ROOT)): d.t.sha(p) for p in sources},
        'output_hashes': {p.name: d.t.sha(p) for p in path.iterdir() if p.is_file()}})
    return cfg


def train(model, processor, rows, arm, seed, cfg, progress):
    import torch
    from torch.utils.data import DataLoader
    from vlm_guard_learning.train_qwen_temporal_guard_lora import TemporalDataset, TemporalCollator
    from vlm_guard_learning.train_qwen_guard_lora import to_device
    loader = DataLoader(TemporalDataset(rows), batch_size=cfg['batch_size'], shuffle=True,
        generator=torch.Generator().manual_seed(seed + 1000), num_workers=0,
        collate_fn=TemporalCollator(processor, mode(arm)))
    params = [p for p in model.parameters() if p.requires_grad]
    optimizer = torch.optim.AdamW(params, lr=cfg['learning_rate'], weight_decay=.01)
    optimizer.zero_grad(set_to_none=True)
    history, updates = [], 0
    for epoch in range(cfg['epochs']):
        model.train()
        loss_sum, count, steps = 0., 0, 0
        for index, batch in enumerate(loader):
            batch = to_device(batch, 'cuda:0')
            with torch.autocast('cuda', dtype=torch.bfloat16):
                loss = model(**batch, use_cache=False).loss / cfg['gradient_accumulation']
            if not torch.isfinite(loss).item():
                raise ValueError('nonfinite training loss')
            loss.backward()
            n = int(batch['input_ids'].shape[0]); count += n
            loss_sum += float(loss.detach()) * cfg['gradient_accumulation'] * n
            if (index + 1) % cfg['gradient_accumulation'] == 0 or index + 1 == len(loader):
                torch.nn.utils.clip_grad_norm_(params, 1.)
                optimizer.step(); optimizer.zero_grad(set_to_none=True)
                steps += 1; updates += 1
                if updates % 10 == 0:
                    state = {'status': 'TRAINING', 'arm': arm, 'seed': seed, 'epoch': epoch + 1,
                             'optimizer_updates': updates, 'mean_loss_so_far': loss_sum / count}
                    d.dump(progress, state)
                    print(json.dumps(state), flush=True)
        history.append({'epoch': epoch + 1, 'mean_loss': loss_sum / count, 'optimizer_steps': steps})
    return history


def analyze(run, cfg):
    stats = {}
    all_rows = {}
    for split in SPLITS:
        all_rows[split] = {}
        arrays = {}
        stats[split] = {'arms': {}, 'paired_differences': {}}
        for arm in ARMS:
            by_seed = [[json.loads(line) for line in
                (run / f'{arm.lower()}-seed{s}' / f'{split}.jsonl').read_text().splitlines()] for s in SEEDS]
            if any(len(rows) != 240 for rows in by_seed):
                raise ValueError('incomplete evaluation')
            for rows in by_seed:
                pair_rows(rows)
            all_rows[split][arm] = by_seed
            clusters = sorted({r['semantic_cluster'] for r in by_seed[0]})
            rng = np.random.default_rng(cfg['bootstrap_seed'])
            draws = rng.integers(0, len(clusters), (cfg['bootstrap_replicates'], len(clusters)))
            arrays[arm] = {}
            stats[split]['arms'][arm] = {}
            for name, field in FIELDS.items():
                per_seed = [sum(r[field] for r in rows) / len(rows) for rows in by_seed]
                cluster_means = np.array([np.mean([r[field] for rows in by_seed for r in rows
                                                  if r['semantic_cluster'] == c]) for c in clusters])
                distribution = cluster_means[draws].mean(1)
                arrays[arm][name] = distribution
                stats[split]['arms'][arm][name] = {'mean': float(np.mean(per_seed)),
                    'std_population': float(np.std(per_seed)), 'per_seed': per_seed,
                    'cluster_95ci': np.quantile(distribution, [.025, .975]).tolist()}
        reference_ids = [[(r['scene_id'], r['contract_level']) for r in rows] for rows in all_rows[split]['P0']]
        for arm in ARMS:
            if [[(r['scene_id'], r['contract_level']) for r in rows] for rows in all_rows[split][arm]] != reference_ids:
                raise ValueError('unpaired results')
        for other in ('P0', 'P1', 'SHUFFLED_GUARD'):
            stats[split]['paired_differences']['P2-' + other] = {name: {
                'mean': stats[split]['arms']['P2'][name]['mean'] - stats[split]['arms'][other][name]['mean'],
                'cluster_95ci': np.quantile(arrays['P2'][name] - arrays[other][name], [.025, .975]).tolist()
            } for name in FIELDS}
    c = cfg['success_criteria']; m = stats['test']['arms']
    v, s = 'guard_violation_rate', 'safe_goal_completion_rate'
    checks = {}
    for arm in ('P1', 'P2'):
        prefix = 'P1_replication' if arm == 'P1' else 'P2'
        checks[arm + '_level'] = all(x <= c[prefix + '_max_violation'] for x in m[arm][v]['per_seed']) and all(
            x >= c[prefix + '_min_safe_completion'] for x in m[arm][s]['per_seed'])
    for other in ('P0', 'P1'):
        vk = 'P2_minus_P0_max_violation_difference' if other == 'P0' else 'P2_minus_P1_violation_margin'
        sk = 'P2_minus_P0_min_safe_completion_difference' if other == 'P0' else 'P2_minus_P1_safe_completion_margin'
        checks['P2_vs_' + other] = all(a-b <= c[vk] for a,b in zip(m['P2'][v]['per_seed'], m[other][v]['per_seed'])) and all(
            a-b >= c[sk] for a,b in zip(m['P2'][s]['per_seed'], m[other][s]['per_seed']))
    result = {'status': 'COMPLETE', 'fits': 18, 'optimizer_updates': 3240, 'predictions': 17280,
              'results': stats, 'test_point_criteria': checks,
              'verdict': 'SUPPORTED_ON_CONTROLLED_TASK' if all(checks.values()) else 'NOT_SUPPORTED',
              'formal_noninferiority': 'NOT_ESTABLISHED', 'limits': cfg['limits']}
    d.dump(run / 'RESULT.json', result)
    lines = ['# 추가 학습·평가 결과', '', '- 기존5조건 + EBLC/CNL, 3 seeds, 동일180 updates/fit.',
             '- 합성 시각·후보 과제. 실제 도로 일반화나 검증 자체의 성능 향상 주장이 아님.',
             '- 이전72 updates 실험과 학습량이 다르므로 데이터 증가만의 인과 효과는 주장하지 않음.',
             '- EBLC 실행 판정은 독립 환경 정답과 대조. 임의 logic text baseline과 구별.', '']
    for split, values in stats.items():
        lines.extend([f'## {split}', '', '| 조건 | 정확도 | 위반 | 정상 완료 | 정지 | 계약쌍 | coverage |',
                      '|---|---:|---:|---:|---:|---:|---:|'])
        for arm, values in values['arms'].items():
            keys = ('accuracy', v, s, 'deadlock_rate', 'contract_swap_pair_accuracy', 'coverage')
            lines.append('| ' + arm + ' | ' + ' | '.join(f'{values[k]["mean"]:.4f}' for k in keys) + ' |')
        lines.append('')
    lines.extend(['전체 지표·seed별 결과·paired clear-time cluster 구간은 RESULT.json에 보존.',
                  'P0/LOGIC의 paraphrase는 동일 입력 반복이며 독립 추가 증거로 세지 않음.',
                  '시험 이미지는10개이며 계약·후보·표현 파생을 독립 장면으로 세지 않음.',
                  '사전 고정 시험 point criteria: ' + result['verdict'] + '. 정식 비열등성/동등성 증명 아님.'])
    (run / 'REPORT_KO.md').write_text('\n'.join(lines) + '\n')
    return result


def execute(run, protocol, gpu):
    if run.exists():
        raise FileExistsError(run)
    verify_hashes(protocol, json.loads((protocol / 'RUN_MANIFEST.json').read_text()))
    verify_hashes(DATA, json.loads((DATA / 'RUN_MANIFEST.json').read_text()))
    cfg = json.loads((protocol / 'protocol.json').read_text())
    signatures = json.loads((protocol / 'training_signatures.json').read_text())
    resource = idle_gpu(gpu)
    os.environ['CUDA_VISIBLE_DEVICES'] = resource['uuid']
    os.environ['HF_HUB_OFFLINE'] = '1'; os.environ['TOKENIZERS_PARALLELISM'] = 'false'
    import torch
    from peft import LoraConfig, TaskType, get_peft_model
    from transformers import AutoProcessor, Qwen3VLForConditionalGeneration
    from vlm_guard_learning.train_qwen_guard_lora import language_attention_targets, seed_all
    from vlm_guard_learning.train_qwen_temporal_guard_lora import generate_choice, TemporalCollator
    torch.set_num_threads(4)
    run.mkdir(parents=True)
    manifest = {'project_id': 'guardsynth-coc', 'status': 'RUNNING', 'resource': resource,
        'started_at_utc': datetime.now(timezone.utc).isoformat(), 'input_hashes': {
            str(protocol.relative_to(d.t.ROOT) / 'RUN_MANIFEST.json'): d.t.sha(protocol / 'RUN_MANIFEST.json')}}
    d.dump(run / 'RUN_MANIFEST.json', manifest)
    d.dump(run / 'RESULT.json', {'status': 'RUNNING', 'completed_fits': 0, 'optimizer_updates': 0})
    (run / 'REPORT_KO.md').write_text('# 추가 학습·평가 실행 중\n\n아직 완료된 성능 결과가 아닙니다. progress.json을 확인하세요.\n')
    model_path = Path.home() / '.cache/huggingface/hub/models--Qwen--Qwen3-VL-2B-Instruct/snapshots' / cfg['model_revision']
    completed = 0
    try:
        processor = AutoProcessor.from_pretrained(model_path, local_files_only=True)
        processor.tokenizer.padding_side = 'right'
        for seed in SEEDS:
            for arm in ARMS:
                start = time.monotonic(); seed_all(seed)
                target = run / f'{arm.lower()}-seed{seed}'; target.mkdir()
                training = examples('train', arm, seed)
                if signature(training, arm) != signatures[arm][str(seed)]:
                    raise ValueError('training input differs from frozen protocol')
                model = Qwen3VLForConditionalGeneration.from_pretrained(model_path, local_files_only=True,
                    dtype=torch.bfloat16, attn_implementation='sdpa').to('cuda:0')
                model.config.use_cache = False
                model = get_peft_model(model, LoraConfig(r=cfg['lora_rank'], lora_alpha=cfg['lora_alpha'],
                    lora_dropout=cfg['lora_dropout'], bias='none', task_type=TaskType.CAUSAL_LM,
                    target_modules=language_attention_targets(model)))
                model.enable_input_require_grads()
                encoded = TemporalCollator(processor, mode(arm))._encode(training[0])
                if not ((encoded['labels'] == -100).any() and (encoded['labels'] != -100).any()
                        and encoded['pixel_values'].numel() > 0):
                    raise ValueError('visual processor or assistant loss mask failure')
                print(f'START {arm} seed={seed} rows={len(training)}', flush=True)
                history = train(model, processor, training, arm, seed, cfg, run / 'progress.json')
                updates = sum(x['optimizer_steps'] for x in history)
                if updates != cfg['optimizer_updates_per_arm_seed']:
                    raise ValueError('update budget mismatch')
                model.save_pretrained(target / 'adapter')
                tensors = [p for n, p in model.named_parameters() if 'lora_B' in n]
                if not tensors or any(not p.count_nonzero().item() for p in tensors):
                    raise ValueError('adapter did not update')
                d.dump(target / 'training.json', {'arm': arm, 'seed': seed, 'history': history,
                    'optimizer_updates': updates, 'nonzero_lora_B_tensors': len(tensors)})
                print(f'CHECKPOINT {arm} seed={seed} updates={updates}', flush=True)
                evaluations = {}; model.eval()
                frozen = [json.loads(line) for line in
                    (protocol / f'evaluation_{arm.lower()}.jsonl').read_text().splitlines()]
                for split in SPLITS:
                    evaluation = examples(split, arm, seed)
                    expected = [r for r in frozen if r['split'] == split]
                    if len(evaluation) != len(expected):
                        raise ValueError('evaluation count drift')
                    rows = []
                    with (target / f'{split}.jsonl').open('w') as stream:
                        for index, e in enumerate(evaluation):
                            # JSON converts candidate tuples to lists; normalize the dataclass.
                            if json.loads(json.dumps(asdict(e))) != expected[index]['example'] or d.t.world.prompt_for(e, mode(arm)) != expected[index]['prompt']:
                                raise ValueError('frozen evaluation drift')
                            prediction, raw = generate_choice(model, processor, e, mode(arm), 'cuda:0')
                            row = {'scene_id': e.scene.scene_id, 'contract_level': e.contract_level,
                                   'seed': seed, 'prediction': prediction, 'raw': raw, **score(e, prediction)}
                            stream.write(json.dumps(row) + '\n'); stream.flush(); rows.append(row)
                            if (index + 1) % 60 == 0:
                                d.dump(run / 'progress.json', {'status': 'EVALUATING', 'arm': arm, 'seed': seed,
                                    'split': split, 'predictions': index + 1, 'completed_fits': completed})
                    evaluations[split] = metrics(rows)
                    print(f'EVAL {arm} seed={seed} {split} {evaluations[split]}', flush=True)
                d.dump(target / 'RESULT.json', {'status': 'COMPLETE', 'evaluation': evaluations,
                    'elapsed_seconds': time.monotonic() - start})
                d.dump(target / 'RUN_MANIFEST.json', {'output_hashes': {
                    str(p.relative_to(target)): d.t.sha(p) for p in target.rglob('*') if p.is_file()}})
                completed += 1
                d.dump(run / 'RESULT.json', {'status': 'RUNNING', 'completed_fits': completed,
                    'optimizer_updates': completed * updates})
                del tensors, model; gc.collect(); torch.cuda.empty_cache()
        analyze(run, cfg)
        d.dump(run / 'progress.json', {'status': 'COMPLETE', 'completed_fits': completed})
        manifest['status'] = 'COMPLETE'
    except Exception as exc:
        manifest['status'] = 'FAILED'
        d.dump(run / 'failure.json', {'type': type(exc).__name__, 'message': str(exc), 'completed_fits': completed})
        d.dump(run / 'RESULT.json', {'status': 'FAILED', 'completed_fits': completed, 'message': str(exc)})
        raise
    finally:
        manifest['output_hashes'] = {str(p.relative_to(run)): d.t.sha(p) for p in run.rglob('*')
                                     if p.is_file() and p != run / 'RUN_MANIFEST.json'}
        d.dump(run / 'RUN_MANIFEST.json', manifest)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--protocol-id', required=True)
    parser.add_argument('--run-id')
    parser.add_argument('--prepare', action='store_true')
    parser.add_argument('--gpu', type=int, default=2)
    args = parser.parse_args()
    for value in (args.protocol_id, args.run_id):
        if value and not re.fullmatch(r'temporal-expansion-(?:protocol|learning)-\d{4}-\d{2}-\d{2}-\d{3}', value):
            parser.error('invalid owner-scoped run ID')
    if args.prepare:
        print(json.dumps(prepare(d.t.BASE / args.protocol_id), indent=2))
    elif args.run_id:
        execute(d.t.BASE / args.run_id, d.t.BASE / args.protocol_id, args.gpu)
    else:
        parser.error('--run-id or --prepare required')
