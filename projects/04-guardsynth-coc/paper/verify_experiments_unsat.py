"""Replay the manuscript's SMT evidence without modifying original experiments."""
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import sys

ROOT = next(p for p in Path(__file__).resolve().parents if (p / 'PROJECT_REGISTRY.json').exists())
sys.path.insert(0, str(ROOT))
from cli.solver_runtime import configure_project_z3

runtime = configure_project_z3(ROOT)
import z3

BASE = ROOT / 'artifacts/projects/guardsynth-coc/public/paper1-method-preservation-001'
OUT = BASE / 'experiments-section-2026-09-30-002'
assert OUT.is_dir() and not (OUT / 'RESULT.json').exists(), 'Completed runs are immutable'
hashes = {}


def read(path):
    hashes[str(path.relative_to(ROOT))] = hashlib.sha256(path.read_bytes()).hexdigest()
    return path.read_text()


def solver():
    s = z3.Solver()
    s.set(timeout=5000)
    return s


def replay(groups):
    counts = Counter()
    for group in groups:
        for query in group['results']:
            s = solver()
            s.from_string(query['smt2'])
            status = str(s.check()).upper()
            assert status == query['status'], query['query_id']
            assert status == query['expected'], query['query_id']
            counts[status] += 1
    return dict(counts)


source = BASE / 'methodology-2026-09-30-001'
bridge = replay(json.loads(read(source / 'bridge_verification.json')))
examples = json.loads(read(source / 'manuscript_examples.json'))
manuscript = replay([x['checks'] for x in examples])
assert bridge == {'SAT': 76, 'UNSAT': 24}
assert manuscript == {'SAT': 8, 'UNSAT': 4}
assertions = {
    x['duration_ms']: z3.parse_smt2_string(next(q['smt2'] for q in x['checks']['results']
                                             if q['query_id'] == 'base_consistency'))
    for x in examples
}
entry = z3.Int('supplied_temporal_release__entry_ms__const')
clear = z3.Int('supplied_temporal_release__clear_ms__const')
enters = z3.Bool('supplied_temporal_release__enters__const')
cache, splits = {}, {}
reasons, totals = Counter(), Counter()
rows_checked = 0
for split in ('train', 'validation', 'test'):
    counts = Counter()
    for line in read(BASE / 'temporal-training-data-2026-09-29-001' / f'{split}_paired.jsonl').splitlines():
        row = json.loads(line)
        c, duration = round(row['scene']['clear_time'] * 1000), row['required_clear_ms']
        progressing = 0
        for label, test in row['action_tests'].items():
            key = duration, c, test['entry_ms']
            assert test['enters'] == (test['entry_ms'] is not None)
            if key not in cache:
                s = solver()
                s.add(assertions[duration])
                s.add(clear == c, enters == test['enters'],
                      entry == (test['entry_ms'] if test['enters'] else 0))
                cache[key] = str(s.check()).upper()
            status = cache[key]
            expected = 'UNSAT' if test['enters'] and test['entry_ms'] < c + duration else 'SAT'
            assert status == expected == test['eblc_status'] == test['environment_expected'], row['id']
            counts[status] += 1
            totals[status] += 1
            if status == 'UNSAT':
                reasons['before_clear' if test['entry_ms'] < c else 'wait_incomplete'] += 1
            progressing += status == 'SAT' and test['enters']
        assert progressing > 0, row['id']
        assert row['action_tests'][row['reference_action']]['eblc_status'] == 'SAT', row['id']
        rows_checked += 1
    splits[split] = dict(counts)
assert dict(totals) == {'SAT': 3840, 'UNSAT': 1920}
assert len(cache) == 960 and Counter(cache.values()) == {'SAT': 540, 'UNSAT': 420}
assert reasons == {'before_clear': 480, 'wait_incomplete': 1440}
assert rows_checked == 1440

quality_path = ROOT / 'artifacts/projects/guardsynth-coc/public/paper1-temporal-diversity-001/diversity-protocol-2026-09-29-001/constraint_quality.json'
quality = defaultdict(Counter)
for case in json.loads(read(quality_path)):
    counts = quality[case['kind']]
    counts['contracts'] += 1
    counts['stored_base_sat'] += case['internal_consistency_SAT'] is True
    for query in (case['checks'] or {}).get('results', []):
        s = solver()
        s.from_string(query['smt2'])
        status = str(s.check()).upper()
        assert status == query['status'] and status != 'UNKNOWN'
        if status != query['expected']:
            counts[query['expected'] + '_to_' + status] += 1
assert quality['threshold_change']['SAT_to_UNSAT'] == 24
assert quality['reverse_comparison']['SAT_to_UNSAT'] == 24
assert quality['reverse_comparison']['UNSAT_to_SAT'] == 24
assert quality['delete_release']['UNSAT_to_SAT'] == 24

query = next(q for q in examples[0]['checks']['results'] if q['query_id'] == 'before_release')
clauses = []
for assertion in z3.parse_smt2_string(query['smt2']):
    clauses.extend(assertion.children() if z3.is_and(assertion) else [assertion])
s = solver()
for i, clause in enumerate(clauses):
    s.assert_and_track(clause, f'clause_{i}')
assert s.check() == z3.unsat
core = [str(x) for x in s.unsat_core()]
deletions = []
for i, clause in enumerate(clauses):
    trial = solver()
    trial.add(*[c for j, c in enumerate(clauses) if i != j])
    status = str(trial.check()).upper()
    assert status == 'SAT'
    deletions.append({'removed': f'clause_{i}', 'expression': str(clause), 'remaining_status': status})
assert len(core) == len(clauses) == 4
result = {
    'project_id': 'guardsynth-coc', 'runtime': runtime.manifest(),
    'bridge': bridge, 'manuscript_examples': manuscript,
    'candidate_bindings': dict(totals), 'candidate_bindings_by_split': splits,
    'unique_assignments': dict(Counter(cache.values())), 'unsat_reasons_with_repetitions': dict(reasons),
    'rows_with_admissible_entry_and_sat_reference': rows_checked,
    'unexpected_unmodified_outcomes': 0, 'solver_unknown': 0,
    'injected_errors': dict(quality),
    'representative_core': {'duration_ms': 500, 'query_id': 'before_release',
                            'core': core, 'deletion_checks': deletions, 'deletion_minimal': True},
    'original_runs_modified': False, 'new_model_calls': 0,
    'input_hashes': hashes, 'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
}
(OUT / 'unsat_review.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
print(json.dumps({k: result[k] for k in ('bridge', 'manuscript_examples', 'candidate_bindings',
                                       'unique_assignments', 'unexpected_unmodified_outcomes')}))
