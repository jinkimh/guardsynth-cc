"""Reanalyze preserved review evidence without changing historical labels or runs."""
from __future__ import annotations

import argparse
from collections import Counter
import csv
import hashlib
import json
from pathlib import Path
import platform
import sys

FIELDS = ('temporal_requirement_explicit', 'required_action_sequence', 'textual_consistency')


def agreement(votes):
    if not votes or len(votes[0]) < 2 or any(len(row) != len(votes[0]) for row in votes):
        raise ValueError('A complete panel with at least two raters is required')
    n = len(votes[0])
    counts = Counter(label for row in votes for label in row)
    raw = sum(sum(c * (c - 1) for c in Counter(row).values()) / (n * (n - 1)) for row in votes) / len(votes)
    expected = sum((c / (len(votes) * n)) ** 2 for c in counts.values())
    return {'raw_agreement': raw, 'kappa': (raw - expected) / (1 - expected) if expected < 1 else None}


def sensitivity_counts(records):
    result = dict(total=0, always_detected=0, setting_sensitive=0, never_detected=0)
    for row in records:
        n, total = row['detected_profile_count'], row['profile_count']
        if not isinstance(n, int) or not isinstance(total, int) or total <= 0 or not 0 <= n <= total:
            raise ValueError('Invalid detector profile count')
        result['total'] += 1
        result['never_detected' if n == 0 else 'always_detected' if n == total else 'setting_sensitive'] += 1
    return result


def index_reviews(rows):
    indexed = {row['review_id']: row for row in rows}
    if len(indexed) != len(rows):
        raise ValueError('Duplicate review ID')
    return indexed


def align_panel(panel):
    indexed = {name: index_reviews(rows) for name, rows in panel.items()}
    if len(indexed) < 2 or len({frozenset(rows) for rows in indexed.values()}) != 1:
        raise ValueError('Panel review IDs do not match')
    return indexed


def read_csv(path):
    with path.open(encoding='utf-8-sig', newline='') as stream:
        return list(csv.DictReader(stream))


def write_csv(path, rows, fields=None):
    if fields is None:
        fields = list(rows[0]) if rows else ['status']
    with path.open('w', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def save(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def analyze(root, output):
    root, output = root.resolve(), output.resolve()
    # A completed or partial prior run is never overwritten.
    output.mkdir(parents=True, exist_ok=False)
    sys.path.insert(0, str(root))
    from experiments.sequential_coc.extract_windows import load_reasoning_events, load_local_trajectory_raw_events, read_natural_windows
    from experiments.sequential_coc.trajectory_contracts import build_trajectory_records, _load_scene_trace, evaluate_trajectory_contract, THRESHOLD_SETS
    from experiments.sequential_coc.contract_compiler import build_summary, compile_text
    from experiments.sequential_coc.build_review_app import select_review_items
    from experiments.sequential_coc.stateful_checker import transition_rule_description, transition_table_sha256
    import pandas, pyarrow

    legacy = root / 'artifacts/results/restricted/sequential-coc-consistency-v1'
    review = legacy / 'review'
    cohort_path = root / 'artifacts/results/public/chunk-0000-94/weak-kinematic-cohort-result.json'
    cohort = json.loads(cohort_path.read_text())
    inputs = list(legacy.rglob('*.csv')) + list(legacy.rglob('*.json')) + list(legacy.glob('*.jsonl')) + [cohort_path]
    code_root = root / 'projects/03-sequential-coc-verification/experiments/sequential_coc'
    inputs += list(code_root.glob('*.py'))
    source_parquet = root / 'data/baseline/coc_nusc/reasoning/ood_reasoning.parquet'
    ego_dir = root / 'data/baseline/coc_nusc/labels/egomotion'
    inputs += [source_parquet, root / 'data/baseline/coc_nusc/UPSTREAM_README.md'] + sorted(ego_dir.glob('*.parquet'))
    inventory = [{'path': str(p.relative_to(root)), 'bytes': p.stat().st_size, 'sha256': digest(p)} for p in sorted(set(inputs))]
    write_csv(output / 'artifact_inventory.csv', inventory)
    manifest = {'project_id': 'sequential-coc-verification', 'status': 'RUNNING', 'source_root': str(root), 'run_id': output.name, 'python': sys.version, 'pandas': pandas.__version__, 'pyarrow': pyarrow.__version__, 'platform': platform.platform(), 'analysis_code_sha256': digest(Path(__file__)), 'command': sys.argv, 'input_count': len(inventory)}
    save(output / 'RUN_MANIFEST.json', manifest)

    paths = sorted(review.glob('contract_review_[AB](*).csv'))
    panel = align_panel({f'R{i+1}': read_csv(p) for i, p in enumerate(paths)})
    save(output / 'reviewer_mapping.json', {f'R{i+1}': p.name for i,p in enumerate(paths)})
    ids = sorted(next(iter(panel.values())))
    consensus = index_reviews(read_csv(review / 'contract_review_consensus.csv'))
    mapping = {row['review_id']: row for row in json.loads((review / 'adjudication-mapping.json').read_text())}
    if set(consensus) != set(ids) or set(mapping) != set(ids):
        raise ValueError('Review, consensus and scene mapping identities differ')
    field_stats, distribution, disagreement = {}, [], []
    for field in FIELDS:
        votes = [[rows[rid][field] for rows in panel.values()] for rid in ids]
        field_stats[field] = {**agreement(votes), 'disputed_items': sum(len(set(v)) > 1 for v in votes)}
        for name, rows in panel.items():
            distribution += [{'reviewer': name, 'field': field, 'label': k, 'count': v} for k, v in sorted(Counter(row[field] for row in rows.values()).items())]
        for rid, rowvotes in zip(ids, votes):
            if len(set(rowvotes)) > 1:
                disagreement.append({'review_id': rid, 'scene_id': mapping[rid]['cluster_id'], 'field': field, 'votes': json.dumps(dict(zip(panel, rowvotes))), 'label_combination': '|'.join(sorted(set(rowvotes))), 'consensus': consensus[rid][field], 'original_notes': json.dumps({k: v[rid]['notes'] for k,v in panel.items()}, ensure_ascii=False), 'consensus_note': consensus[rid]['notes'], 'cause_attribution': 'REQUIRES_HUMAN_REVIEW_NOT_INFERRED_FROM_VOTES'})
    write_csv(output / 'reviewer_distribution.csv', distribution)
    write_csv(output / 'disagreement_cases.csv', disagreement)
    save(output / 'agreement.json', field_stats)
    old_panel = json.loads((review / 'panel-review-summary.json').read_text())
    for field in FIELDS:
        for key in ['kappa','raw_agreement']:
            assert abs(field_stats[field][key] - old_panel['field_agreement'][field][key]) < 1e-12

    events = [row for episode in cohort['episodes'] for row in episode['events']]
    profile_rows = [e['three_second_robustness'] for e in events if e.get('three_second_robustness')]
    sensitivity = sensitivity_counts(profile_rows)
    write_csv(output / 'threshold_cases.csv', [{'event_id': e['event_id'], **e['three_second_robustness']} for e in events if e.get('three_second_robustness')])
    save(output / 'threshold_summary.json', sensitivity)
    selection = {'all_events':len(events), 'quality_pass':sum(e['quality_pass'] for e in events), 'exclusion_reasons':dict(Counter(str(e.get('exclusion_reason')) for e in events)), 'contract_verdicts':dict(Counter(e['weak_kinematic_contract'] for e in events)), 'detector_events':len(profile_rows), 'declared_cohort':cohort['cohort'], 'thresholds':cohort['contract']}
    save(output / 'selection_flow.json', selection)

    windows = read_natural_windows(legacy / 'natural-windows.jsonl')
    _, rebuilt_mapping, rebuilt_selection = select_review_items(windows)
    assert {(r['review_id'],r['cluster_id'],r['group']) for r in rebuilt_mapping} == {(r['review_id'],r['cluster_id'],r['group']) for r in mapping.values()}
    save(output / 'review_selection_reproduction.json', rebuilt_selection)
    save(output / 'compiler_coverage.json', build_summary(windows))
    save(output / 'transition_contract.json', transition_rule_description())

    raw_scenes = load_local_trajectory_raw_events(source_parquet, ego_dir)
    # Rerun the unchanged historical evaluator to recover missing event-level reasons.
    summary = build_trajectory_records(raw_scenes, ego_dir)[0]
    scene_records = summary['scene_records']
    event_records = []
    for sid, sources in sorted(raw_scenes.items()):
        trace = _load_scene_trace(sid, ego_dir)
        for source in sorted(sources, key=lambda e: (e.timestamp_us,e.original_position)):
            compiled = compile_text(source.source_text, f'{sid}@{source.timestamp_us}:{source.original_position}', sid, source.timestamp_us)
            if not trace or source.timestamp_us < trace[0].timestamp_us or source.timestamp_us > trace[-1].timestamp_us:
                thresholds = {t.name: {'verdict':'UNKNOWN','reason':'EVENT_TIMESTAMP_OUTSIDE_EGOMOTION'} for t in THRESHOLD_SETS}
            else:
                thresholds = {t.name:evaluate_trajectory_contract(compiled,trace,t).to_dict() for t in THRESHOLD_SETS}
            event_records.append({'scene_cluster_id':sid, 'timestamp_us':source.timestamp_us, 'original_position':source.original_position, 'source_text_sha256':source.source_text_sha256, 'threshold_results':thresholds})
    assert len(event_records)==summary['sample_units']['event']
    for t in THRESHOLD_SETS:
        assert dict(Counter(e['threshold_results'][t.name]['verdict'] for e in event_records))==summary['verdict_counts']['event'][t.name]
    save(output / 'trajectory_reexecution.json', summary)
    for name, rows in [('trajectory_event_records.jsonl',event_records), ('trajectory_scene_records.jsonl',scene_records)]:
        (output / name).write_text(''.join(json.dumps(row,ensure_ascii=False)+'\n' for row in rows))
    old_trajectory = json.loads((legacy / 'trajectory-results.jsonl').read_text())
    old_scenes = {r['scene_cluster_id']:r for r in old_trajectory['scene_records']}
    new_scenes = {r['scene_cluster_id']:r for r in scene_records}
    differences = [sid for sid in sorted(old_scenes) if old_scenes[sid]['threshold_results'] != new_scenes[sid]['threshold_results']]
    cases = []
    for rid in ids:
        sid = mapping[rid]['cluster_id']
        records = [r for r in event_records if r['scene_cluster_id']==sid]
        cases.append({'review_id':rid,'scene_id':sid,'text_consensus':consensus[rid]['textual_consistency'],'trajectory_verdict':new_scenes[sid]['threshold_results']['baseline']['verdict'],'scene_reason':new_scenes[sid]['threshold_results']['baseline']['reason'],'event_reasons':json.dumps(dict(Counter(r['threshold_results']['baseline']['reason'] for r in records))), 'missing_evidence':'SEE_EVENT_REASONS; NOT_A_SAFETY_GOLD', 'historical_verdict':old_scenes[sid]['threshold_results']['baseline']['verdict']})
    write_csv(output / 'scene_evidence_cases.csv', cases)

    mutations = [json.loads(line) for line in (legacy / 'mutations.jsonl').read_text().splitlines()]
    mutation_stats = {}
    for kind in sorted({p['oracle'] for p in mutations}):
        pairs = [p for p in mutations if p['oracle']==kind]
        mutation_stats[kind] = {'count':len(pairs),'evaluation_role':'PROCESSING_FAULT' if kind=='STALE_OBLIGATION' else 'ANNOTATION_OR_STRUCTURED_EVENT_RULE', 'stateful_detected':sum(p['checker_results']['mutated']['stateful']['verdict']=='CONTRADICTION' for p in pairs), 'event_local_detected':sum(p['checker_results']['mutated']['event_local']['verdict']=='CONTRADICTION' for p in pairs)}
    save(output / 'mutation_reclassification.json', mutation_stats)

    all_scenes = load_reasoning_events(source_parquet)
    exposures = []
    review_scenes = {r['cluster_id'] for r in mapping.values()}
    for sid, rows in sorted(all_scenes.items()):
        exposures.append({'scene_id':sid,'event_count':len(rows),'known_old_review':sid in review_scenes,'known_trajectory_analysis':sid in raw_scenes,'exposure_status':'KNOWN_ANALYSIS' if sid in raw_scenes else 'UNKNOWN_EXPOSURE','eligible_unreviewed_candidate':len(rows)>=2 and sid not in raw_scenes,'strict_heldout_confirmed':False})
    write_csv(output / 'exposure_manifest.csv',exposures)
    upstream = (root/'data/baseline/coc_nusc/UPSTREAM_README.md').read_text()
    provenance=[{'field':'labeling_model_family','value':'Qwen/Qwen3.5-35B-A3B','evidence':'UPSTREAM_README.md','status':'UPSTREAM_DECLARED_NOT_PINNED_PER_RUN'}, {'field':'model_checkpoint_revision','value':'UNKNOWN','evidence':'not recovered','status':'UNRECORDED'}, {'field':'generation_prompt_and_configuration','value':'UNKNOWN','evidence':'not recovered','status':'UNRECORDED'}, {'field':'quality_filter','value':'saved quality_pass boolean','evidence':'check_cohort.py','status':'DOWNSTREAM_RULE_RECOVERED_UPSTREAM_SCORE_THRESHOLDS_NOT_RECOVERED'}]
    assert 'Qwen3.5-35B-A3B' in upstream
    write_csv(output/'provenance_inventory.csv',provenance)
    result={'status':'REANALYSIS_COMPLETE_WITH_OPEN_GATES','project_id':'sequential-coc-verification','panel':{'reviewers':len(panel),'scenes':len(ids),'fields':field_stats,'consensus_notes_nonempty':sum(bool(r['notes'].strip()) for r in consensus.values())},'threshold_sensitivity':sensitivity,'selection_flow':selection,'trajectory_reproduction':{'scene_differences':differences,'reviewed_counts':dict(Counter(r['trajectory_verdict'] for r in cases))},'mutation_reclassification':mutation_stats,'source_inventory':{'scenes':len(all_scenes),'events':sum(len(e) for e in all_scenes.values()),'candidate_multicoc_scenes_outside_trajectory':sum(r['eligible_unreviewed_candidate'] for r in exposures),'confirmed_heldout_scenes':0},'implementation':{'transition_contract_sha256':transition_table_sha256(),'active_obligation_capacity':1,'compiler_observational_evidence':'ALL_UNKNOWN_BY_CONSTRUCTION'},'open_gates':['human disagreement-cause review','historical reviewer training/adjudication reconstruction','independent exposure certification','independent mutation gold','upstream prompt/checkpoint recovery']}
    save(output/'RESULT.json',result)
    manifest['status']='COMPLETE';manifest['result_sha256']=digest(output/'RESULT.json');save(output/'RUN_MANIFEST.json',manifest)
    report=f'''# 기존 실험 재분석 결과\n\n- 소유: sequential-coc-verification\n- 상태: 계산 재현 완료, 사람 검토·독립 평가 전\n\n## 주요 결과\n\n- 네 평가자의 27장면 일치도는 기존 집계와 일치한다. 텍스트 κ={field_stats['textual_consistency']['kappa']:.6f}, 평균 쌍별 일치율={field_stats['textual_consistency']['raw_agreement']:.6f}.\n- 텍스트 불일치 {field_stats['textual_consistency']['disputed_items']}/27. 합의 CSV의 근거 메모가 있는 장면은 {result['panel']['consensus_notes_nonempty']}/27이다. 합의 이유를 새로 추정하여 과거 사실로 기록하지 않는다.\n- 130개 탐지 대상: 항상 검출 {sensitivity['always_detected']}, 설정 의존 {sensitivity['setting_sensitive']}, 항상 미검출 {sensitivity['never_detected']}. 따라서 58건 전체를 설정 변화 사례로 부르는 표현을 수정해야 한다.\n- 기존 궤적 판정과 새 실행의 장면별 차이: {len(differences)}건. 사람 검토 27장면 분포: {result['trajectory_reproduction']['reviewed_counts']}. 원인별 근거는 scene_evidence_cases.csv와 사건별 JSONL에 있다.\n- 전체 CoC {len(all_scenes)}장면, 새 표본 후보 {result['source_inventory']['candidate_multicoc_scenes_outside_trajectory']}장면. 개발 미사용 이력은 확인되지 않아 독립 held-out으로 인증하지 않는다.\n\n## 방법론상 확인 사항\n\n현재 상태 검사기의 활성 요구 용량은 1이다. 복수 요구는 지원 성능으로 주장할 수 없다. 문장 compiler는 조건의 문구를 보존하지만 관측된 해제·충족 여부를 모두 Unknown으로 두므로 문장만으로 의미 증거를 판정하는 범용 추출기가 아니다. M5/M6 및 문장부터의 평가에 이 한계를 명시해야 한다.\n\nP4는 별도 처리 시험으로 분리한다. upstream README는 생성 모델 계열을 명시하지만 정확한 checkpoint revision과 prompt/config는 복원되지 않았다. 전체 미상이라고 하거나 완전 재현이라고 하지 않는다.\n\n## 다음 작업\n\nE2 명세와 현 구현의 범위 및 P4 의미를 정리한 뒤, E3 검토 패킷을 준비한다. 원시 의견의 원인 분류·새 정답 확인은 실제 사람 검토가 필요하다. 이 실행은 새 자연 오류 정확도나 독립 오류 주입 성능을 산출하지 않았다.\n'''
    (output/'REPORT_KO.md').write_text(report)
    # Ensure read-only input promise holds even across evaluator execution.
    assert all(digest(root/r['path'])==r['sha256'] for r in inventory)
    print(json.dumps({'output':str(output),'thresholds':sensitivity,'reviewed_counts':result['trajectory_reproduction']['reviewed_counts'],'trajectory_differences':len(differences)},ensure_ascii=False))


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--source-root',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    analyze(args.source_root,args.output)
