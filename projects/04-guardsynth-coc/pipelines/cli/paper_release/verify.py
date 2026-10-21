"""Recompute central NCA metrics from a frozen release, without GPU or ML packages.

Owner: guardsynth-coc. Historical JSON keys 'accuracy' mean the percentage of
preferred-candidate matches (preferred-selection score), not general driving quality.
"""
import argparse
from collections import defaultdict
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import statistics

PUBLIC = Path('projects/04-guardsynth-coc/artifacts/public')
BASELINE = PUBLIC / 'paper1-vlm-constraint-baselines-001/vlm-constraint-baselines-2026-10-12-001'


def rows(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def oracle(case):
    meta = case['meta']
    if case['family'] == 'temporal':
        clear = int(Decimal(str(meta['scene']['clear_time'])) * 1000)
        allowed = {c['label']: (c['entry_time'] is None or
                   int(Decimal(str(c['entry_time'])) * 1000) >= clear + meta['required_clear_ms'])
                   for c in meta['scene']['candidates']}
        candidates = meta['scene']['candidates']
    else:
        candidates = meta['candidates']
        times = meta['eblc']['sample_times_ms']
        assert all(len(c['xy_mm']) == len(times) for c in candidates)
        allowed = {c['label']: all(x*x + y*y <= 200*200
                   for time, (x, y) in zip(times, c['xy_mm']) if time <= meta['hold_ms'])
                   for c in candidates}
    best = max((c for c in candidates if allowed[c['label']]), key=lambda c: c['progress'])['label']
    assert best == case['target'], case['id']
    assert {k for k, v in allowed.items() if v} == set(case['allowed_labels']), case['id']
    return best, allowed


def metrics(predictions, cases):
    correct, violations, invalid, caps = 0, 0, 0, 0
    pairs = defaultdict(list)
    assert len({r['id'] for r in predictions}) == len(predictions)
    for row in predictions:
        case = cases[row['id']]
        target, allowed = oracle(case)
        prediction = row['prediction']
        is_correct = prediction == target
        is_valid = prediction in allowed
        is_violation = not allowed[prediction] if is_valid else None
        assert (row['correct'], row['valid'], row['violation']) == (is_correct, is_valid, is_violation)
        correct += is_correct
        invalid += not is_valid
        violations += is_violation is True
        caps += row['response']['hit_token_cap']
        pairs[case['pair_id']].append(is_correct)
    assert all(len(pair) == 2 for pair in pairs.values())
    n = len(predictions)
    return dict(rows=n, pairs=len(pairs), preferred_selection_score=100*correct/n,
                violation_rate=100*violations/n, invalid_rate=100*invalid/n,
                token_cap_rate=100*caps/n,
                rule_pair_score=100*sum(all(pair) for pair in pairs.values())/len(pairs))


def verify(root):
    manifest = json.loads((root / 'SOURCE_MANIFEST.json').read_text())
    for item in manifest['files']:
        path = root / item['path']
        assert path.is_file() and not path.is_symlink(), item['path']
        assert hashlib.sha256(path.read_bytes()).hexdigest() == item['sha256'], item['path']
    cases = {r['id']: r for name in ('temporal_test.jsonl', 'position_hold_test.jsonl')
             for r in rows(root / BASELINE / name)}
    for case in cases.values():
        oracle(case)
        assert (root / case['image_path']).is_file(), case['image_path']
    per_seed = []
    for task in ('temporal', 'position_hold'):
        for arm in ('ce_no_rule', 'semantic_no_rule', 'ce_rule', 'semantic_rule'):
            for seed in (42, 17, 123):
                name = 'common_rule_predictions.jsonl' if 'no_rule' in arm else 'predictions.jsonl'
                predictions = rows(root / BASELINE / f'{task}_{arm}_seed{seed}' / name)
                for encoding in sorted({r['encoding'] for r in predictions}):
                    selected = [r for r in predictions if r['encoding'] == encoding]
                    per_seed.append(dict(task=task, arm=arm, seed=seed, encoding=encoding,
                                         **metrics(selected, cases)))
    means = []
    for task, arm, encoding in sorted({(r['task'], r['arm'], r['encoding']) for r in per_seed}):
        group = [r for r in per_seed if (r['task'], r['arm'], r['encoding']) == (task, arm, encoding)]
        means.append(dict(task=task, arm=arm, encoding=encoding,
                         **{key: statistics.mean(r[key] for r in group)
                            for key in ('preferred_selection_score', 'violation_rate', 'rule_pair_score')}))
    pretrained = []
    for size in ('2b', '8b'):
        predictions = rows(root / BASELINE / f'pretrained_{size}/predictions.jsonl')
        for task, encoding in [('temporal', 'candidate_scalars'),
                               ('position_hold', 'interval_maxima'), ('position_hold', 'xy_waypoints')]:
            selected = [r for r in predictions if r['task'] == task and r['encoding'] == encoding]
            pretrained.append(dict(model=size, task=task, encoding=encoding, **metrics(selected, cases)))
    expected = {('temporal', 'ce_rule', 'candidate_scalars'): (98.47, 1.11, 96.94),
                ('position_hold', 'ce_rule', 'interval_maxima'): (96.09, 0.00, 92.71),
                ('position_hold', 'ce_rule', 'xy_waypoints'): (93.49, 1.56, 86.98)}
    for item in means:
        key = item['task'], item['arm'], item['encoding']
        if key in expected:
            assert tuple(round(item[m], 2) for m in ('preferred_selection_score', 'violation_rate', 'rule_pair_score')) == expected[key]
    assert [round(r['rule_pair_score'], 2) for r in pretrained if r['model'] == '8b'] == [0.83, 51.56, 23.44]
    faults = json.loads((root / PUBLIC / 'paper1-learning-specification-faults-001/learning-specification-faults-2026-10-12-001/RESULT.json').read_text())['aggregate']
    assert (faults['supported_detected'], faults['valid_accepted'], faults['shared_source_missed']) == (288, 48, 48)
    composition = json.loads((root / PUBLIC / 'paper1-constraint-composition-001/document-grounded-composition-2026-10-17-002/RESULT.json').read_text())['aggregate']
    assert (composition['cases'], composition['full_unsat'], composition['full_sat'], composition['pairwise_sat_full_unsat']) == (176, 58, 118, 12)
    return dict(status='PASS', manifest_files=len(manifest['files']), oracle_test_rows=len(cases),
                common_rule_means=means, pretrained=pretrained,
                fault_aggregate_record=faults, composition_aggregate_record=composition,
                scope='Behavior metrics recomputed from predictions and independent integer oracles; checker aggregates read and checked here. Rerun checker scripts to validate SMT results.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, default=Path.cwd())
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    result = verify(args.root.resolve())
    output = json.dumps(result, indent=2) + '\n'
    if args.output:
        args.output.write_text(output)
    else:
        print(output)
