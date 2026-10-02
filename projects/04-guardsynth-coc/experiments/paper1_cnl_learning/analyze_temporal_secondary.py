"""Post-outcome descriptive metrics; never retune or rewrite frozen runs."""
import argparse
import copy
import hashlib
import json
import platform
import statistics as st
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT / 'artifacts/projects/guardsynth-coc/public/paper1-method-preservation-001'
SOURCE = BASE / 'temporal-expansion-learning-2026-09-29-001'
DATA = BASE / 'temporal-training-data-2026-09-29-001'
ARMS = ('P0', 'P1', 'P2', 'NATURAL_GUARD', 'SHUFFLED_GUARD', 'LOGIC_GUARD')
SEEDS = (42, 17, 123)
SPLITS = ('validation', 'test', 'paraphrase', 'unseen_duration')


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def dump(p, obj):
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False) + '\n')


def verify(base):
    manifest = json.loads((base / 'RUN_MANIFEST.json').read_text())
    for name, digest in manifest['output_hashes'].items():
        if sha(base / name) != digest:
            raise ValueError('source output drift: ' + name)
    for name, digest in manifest.get('input_hashes', {}).items():
        if sha(ROOT / name) != digest:
            raise ValueError('source input drift: ' + name)


def measure(source, prediction, split):
    """Progress scores are synthetic units, not meters; never trust role tags."""
    row = copy.deepcopy(source)
    clear = round(row['scene']['clear_time'] * 1000)
    duration = row['required_clear_ms']
    if split == 'unseen_duration':
        duration = 800 if row['contract_level'] == 'short' else 1800
    threshold = clear + duration
    candidates = row['scene']['candidates']
    for c in candidates:
        c['ms'] = None if c['entry_time'] is None else round(c['entry_time'] * 1000)
        if c['ms'] is not None and split == 'unseen_duration':
            c['ms'] += 300
        c['allowed'] = c['ms'] is None or c['ms'] >= threshold
    feasible = [c for c in candidates if c['allowed']]
    best = max(feasible, key=lambda c: c['progress'])
    selected = next((c for c in candidates if c['label'] == prediction), None)
    valid = selected is not None
    safe = valid and selected['allowed']
    enters = valid and selected['ms'] is not None
    violation = valid and not safe
    excess = max(0, threshold - selected['ms']) if enters else None
    progress_loss = best['progress'] - selected['progress'] if safe else None
    # Explicit composite convention: an unsafe/invalid choice earns zero useful progress.
    gated_loss = (1 - selected['progress'] / best['progress'] if safe else 1.) if best['progress'] > 0 else None
    return {'valid': valid, 'violation': violation, 'safe': safe, 'enters': enters,
            'entry_ms': selected['ms'] if valid else None, 'clear_ms': clear,
            'threshold_ms': threshold, 'best_progress': best['progress'],
            'selected_progress': selected['progress'] if valid else None,
            'safe_progress_loss_units': progress_loss, 'gated_progress_loss_fraction': gated_loss,
            'early_entry_ms': excess, 'occupancy_early_ms': max(0, clear-selected['ms']) if enters else None,
            'occupied_entry': bool(enters and selected['ms'] < clear),
            'release_wait_violation': bool(violation and selected['ms'] >= clear),
            'unnecessary_stop': bool(valid and not enters and best['progress'] > 0),
            'unnecessary_stop_eligible': best['progress'] > 0,
            'independent_target': best['label'],
            'excess_wait_ms': max(0, selected['ms']-threshold) if safe and enters else None}


def avg(xs):
    return st.mean(xs) if xs else None


def percentile(xs, q):
    if not xs:
        return None
    xs = sorted(xs); i = (len(xs)-1)*q; lo = int(i)
    return xs[lo] + (xs[min(lo+1, len(xs)-1)]-xs[lo])*(i-lo)


def summarize(rows):
    safe_losses = [r['safe_progress_loss_units'] for r in rows if r['safe_progress_loss_units'] is not None]
    gated = [r['gated_progress_loss_fraction'] for r in rows if r['gated_progress_loss_fraction'] is not None]
    early = [r['early_entry_ms'] for r in rows if r['enters']]
    violated = [r['early_entry_ms'] for r in rows if r['violation']]
    waits = [r['excess_wait_ms'] for r in rows if r['excess_wait_ms'] is not None]
    eligible = sum(r['unnecessary_stop_eligible'] for r in rows)
    return {'n': len(rows), 'valid_n': sum(r['valid'] for r in rows),
            'safe_n': len(safe_losses), 'violation_n': len(violated), 'entry_n': len(early),
            'unnecessary_stop_eligible_n': eligible,
            'unnecessary_stop_rate': sum(r['unnecessary_stop'] for r in rows)/eligible if eligible else None,
            'occupied_entry_rate': avg([r['occupied_entry'] for r in rows]),
            'release_wait_violation_rate': avg([r['release_wait_violation'] for r in rows]),
            'safe_progress_loss_units': avg(safe_losses),
            'safe_suboptimal_rate': avg([v > 0 for v in safe_losses]),
            'gated_progress_loss_fraction': avg(gated),
            'early_ms_per_entry': avg(early), 'early_ms_per_violation': avg(violated),
            'early_violation_p95_ms': percentile(violated, .95),
            'early_violation_max_ms': max(violated) if violated else None,
            'excess_wait_ms_per_safe_entry': avg(waits)}


def benchmark():
    # No GPU/model; each measured check constructs a solver, never a memoized verdict.
    import temporal_training_data as d
    import z3
    from guard_synth_eblc.smt_compiler import solve_assignment
    cases = [(duration, clear, entry) for duration in (500, 1500, 800, 1800)
             for clear in (11000, 11500, 11900)
             for entry in (None, clear+duration-1, clear+duration, clear+duration+1)]
    def compile_one(duration):
        return d.t.compile_core_model(d.t.parse_core_model(d.t.lower(d.t.contract(duration/1000))))
    models = {v: compile_one(v) for v in (500, 1500, 800, 1800)}
    timings = {}; results = []
    # Warm library initialization, deliberately excluded from both measurements.
    solve_assignment(models[500], {('clear_ms', None): 0, ('entry_ms', None): 500, ('enters', None): True})
    for mode in ('compile_and_solve', 'reused_compilation_solve'):
        samples = []
        for repeat in range(3):
            for duration, clear, entry in cases:
                assignment = {('clear_ms', None): clear, ('entry_ms', None): entry or 0,
                              ('enters', None): entry is not None}
                start = time.perf_counter_ns()
                model = compile_one(duration) if mode == 'compile_and_solve' else models[duration]
                verdict = solve_assignment(model, assignment)['status']
                elapsed = (time.perf_counter_ns()-start)/1e6
                expected = 'UNSAT' if entry is not None and entry < clear+duration else 'SAT'
                if verdict != expected:
                    raise ValueError('timing semantic mismatch')
                samples.append(elapsed)
                results.append({'mode': mode, 'repeat': repeat, 'duration_ms': duration,
                                'clear_ms': clear, 'entry_ms': entry, 'status': verdict, 'elapsed_ms': elapsed})
        timings[mode] = {'checks': len(samples), 'mean_ms': avg(samples), 'median_ms': st.median(samples),
                         'p95_ms': percentile(samples, .95), 'serial_checks_per_second': 1000/avg(samples)}
    return {'timings': timings, 'samples': results, 'z3': z3.get_version_string(),
            'python': platform.python_version(), 'cpu': platform.processor(), 'platform': platform.platform(),
            'scope': '48 synthetic bindings x3 repeats per mode, single process, warm libraries; excludes model/video/IO/startup; not real-time guarantee'}, d


def run(output):
    if output.exists():
        raise FileExistsError(output)
    verify(SOURCE); verify(DATA)
    original = json.loads((SOURCE/'RESULT.json').read_text())
    if original['status'] != 'COMPLETE':
        raise ValueError('upstream incomplete')
    inputs = {str(p.relative_to(ROOT)): sha(p) for p in (Path(__file__), Path(__file__).with_name('test_temporal_secondary.py'),
              SOURCE/'RUN_MANIFEST.json', SOURCE/'RESULT.json', DATA/'RUN_MANIFEST.json')}
    rows_by_split = {}
    for split in ('validation', 'test'):
        p = DATA/f'{split}_paired.jsonl'; inputs[str(p.relative_to(ROOT))] = sha(p)
        rows_by_split[split] = {(r['scene']['scene_id'], r['contract_level']): r
                               for r in map(json.loads, p.read_text().splitlines())}
    stats = {}; detailed = []
    for split in SPLITS:
        stats[split] = {}
        lookup = rows_by_split['validation' if split == 'validation' else 'test']
        for arm in ARMS:
            pooled = []; per_seed = []
            for seed in SEEDS:
                p = SOURCE/f'{arm.lower()}-seed{seed}'/f'{split}.jsonl'
                inputs[str(p.relative_to(ROOT))] = sha(p)
                records = list(map(json.loads, p.read_text().splitlines()))
                keys = [(r['scene_id'], r['contract_level']) for r in records]
                if len(keys) != len(lookup) or set(keys) != set(lookup):
                    raise ValueError('incomplete/duplicate source rows')
                measured = []
                for pred in records:
                    m = measure(lookup[(pred['scene_id'], pred['contract_level'])], pred['prediction'], split)
                    for old, new in [('valid','valid'), ('guard_violation','violation'), ('hold_violation','occupied_entry'),
                                     ('deadlock','unnecessary_stop'), ('entry_ms','entry_ms'), ('independent_target','independent_target')]:
                        if pred[old] != m[new]:
                            raise ValueError('original metric mismatch: '+old)
                    measured.append(m)
                    detailed.append(dict(m, split=split, arm=arm, seed=seed, scene_id=pred['scene_id'], contract_level=pred['contract_level']))
                per_seed.append(dict(summarize(measured), seed=seed)); pooled.extend(measured)
            summary = summarize(pooled)
            variation = {}
            for key in summary:
                if key in ('n',) or key.endswith('_n'):
                    continue
                values = [r[key] for r in per_seed if r[key] is not None]
                variation[key] = {'mean': avg(values), 'std_population': st.pstdev(values) if values else None,
                                  'defined_seed_n': len(values)}
            stats[split][arm] = {'pooled': summary, 'per_seed': per_seed, 'seed_summary': variation}
    timing, d = benchmark()
    for fn in (d.action_test, d.t.contract, d.t.compile_core_model, d.t.parse_core_model, d.solve_assignment):
        p = Path(fn.__wrapped__.__code__.co_filename if hasattr(fn, '__wrapped__') else fn.__code__.co_filename)
        inputs[str(p.relative_to(ROOT))] = sha(p)
    output.mkdir(parents=True)
    definitions = {
        'safe_progress_loss_units': 'best feasible progress minus chosen progress, ONLY valid compliant choices; abstract score units, report safe_n',
        'gated_progress_loss_fraction': '1 - safe credited progress / best feasible progress; unsafe/invalid credited0; null if best<=0; NOT independent safety evidence',
        'early_ms_per_entry': 'max(0, clear+required_wait-entry) over valid entering choices, including compliant zeros',
        'early_ms_per_violation': 'same shortfall conditional on violations; no violations => null, not zero',
        'excess_wait_ms_per_safe_entry': 'entry-(clear+required_wait) over compliant moving choices; candidate discretization can force positive delay',
        'unnecessary_stop_rate': 'stopped while a feasible positive-progress candidate exists / eligible choices, includes invalid in denominator but reports valid_n',
        'uncertainty': 'descriptive per-seed mean/population SD only; pooled conditional stats differ from equally weighted seed stats; no new significance claims'}
    dump(output/'RESULT.json', {'status':'COMPLETE', 'analysis_kind':'POST_HOC_EXPLORATORY_NO_THRESHOLD_TUNING',
        'source_run':str(SOURCE.relative_to(ROOT)), 'row_count':len(detailed), 'definitions':definitions,
        'results':stats, 'timing':{k:v for k,v in timing.items() if k!='samples'},
        'limits':['Same synthetic task and frozen predictions, no retraining.',
                  'Four splits share templates; rows/seeds are not independent road scenes.',
                  'Safe-only statistics must be read with violation rates; composite includes safety by construction.',
                  'Timing varies with hardware/load; this is a bounded CPU microbenchmark.']})
    dump(output/'timing_samples.json', timing['samples'])
    with (output/'per_prediction.jsonl').open('w') as stream:
        for r in detailed: stream.write(json.dumps(r, allow_nan=False)+'\n')
    report = ['# 추가 행동 지표 및 EBLC 처리시간', '', '결과 열람 후 정의한 탐색적 분석. 원 protocol/판정/가중치는 변경하지 않음.',
              '전체6조건×3seeds×4평가 묶음, 17,280개 원예측 재사용. 새로운 학습/모델 호출 없음.', '',
              '진행 점수는 합성 후보의 임의 단위이며 m가 아니다. 안전 선택 내 손실은 안전 선택만을 분모로 한다.',
              '전체 손실은 위반/무응답의 유효 진행을0으로 계산하는 복합 지표다. 낮을수록 좋다.',
              '조기 진입은 허용시점 부족분이며 충돌 위험 크기가 아니다. 위반0건의 조건부 평균은 N/A다.',
              '아래 조건부 수치는3seed pooled이며 seed별 값/평균/표준편차는 RESULT.json에 함께 보존한다.', '']
    def fmt(x, factor=1): return 'N/A' if x is None else f'{x*factor:.3f}'
    for split in SPLITS:
        report += [f'## {split}', '', '| 조건 | 안전 선택 n/720 | 안전 선택 내 진행 손실 | 전체 진행 손실(%) | 위반 n | 위반당 조기 진입(s) | p95(s) | 불필요 정지(%) |',
                   '|---|---:|---:|---:|---:|---:|---:|---:|']
        for arm in ARMS:
            s = stats[split][arm]['pooled']
            report.append(f"| {arm} | {s['safe_n']}/720 | {fmt(s['safe_progress_loss_units'])} | {fmt(s['gated_progress_loss_fraction'],100)} | {s['violation_n']} | {fmt(s['early_ms_per_violation'],.001)} | {fmt(s['early_violation_p95_ms'],.001)} | {fmt(s['unnecessary_stop_rate'],100)} |")
        report.append('')
    report += ['## CPU 검증 시간', '', '48개 서로 다른 binding을 mode별3회, 각144회 직렬 측정. 판정 결과 캐시를 사용하지 않음.',
               '라이브러리 초기화·모델·영상·IO 제외. compile_and_solve는 계약 구성/파싱/컴파일 포함, 다른 mode는 컴파일 재사용.',
               '이는 전체 데이터 제작 처리량/실시간 차량 검증 보장이 아니며 동시 시스템 부하에 영향을 받음.', '',
               '| 경로 | 평균 ms | 중앙값 ms | p95 ms | checks/s |','|---|---:|---:|---:|---:|']
    for mode,s in timing['timings'].items():
        report.append(f"| {mode} | {s['mean_ms']:.3f} | {s['median_ms']:.3f} | {s['p95_ms']:.3f} | {s['serial_checks_per_second']:.1f} |")
    (output/'REPORT_KO.md').write_text('\n'.join(report)+'\n')
    for name,digest in inputs.items():
        if sha(ROOT/name) != digest: raise ValueError('input changed during analysis')
    dump(output/'RUN_MANIFEST.json', {'project_id':'guardsynth-coc','status':'COMPLETE','input_hashes':inputs,
        'output_hashes':{str(p.relative_to(output)):sha(p) for p in sorted(output.iterdir())}})
    print(json.dumps({'status':'COMPLETE','output':str(output),'rows':len(detailed),'timing':timing['timings']}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--run-id', required=True)
    args = parser.parse_args()
    import re
    if not re.fullmatch(r'temporal-secondary-metrics-\d{4}-\d{2}-\d{2}-\d{3}', args.run_id):
        parser.error('invalid run ID')
    run(BASE/args.run_id)
