"""Execute accepted development semantics and prepare unassigned blind speed inputs."""

import argparse
import base64
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sys

ROOT = next(p for p in Path(__file__).resolve().parents if (p / 'PROJECT_REGISTRY.json').is_file())
sys.path[:0] = [str(ROOT), str(ROOT / 'platforms/eblc-bcv/src'), str(Path(__file__).parent)]
from cli.solver_runtime import configure_project_z3
SOLVER = configure_project_z3(ROOT)
from guard_synth_eblc.speed_contract import parse_speed_contract, lower_speed_contract, render_speed_contract, eq, ACTIONS
from guard_synth_eblc.action_contract import conjunction, neg
from guard_synth_eblc.core_ir import parse_core_model
from guard_synth_eblc.smt_compiler import compile_core_model, check_queries
import prepare_speed_clause_binding as prior

BASE = prior.BASE
PROPOSAL = BASE / 'speed-clause-binding-2026-09-28-001'
DECISION = ROOT / 'projects/04-guardsynth-coc/docs/decisions/PAPER1_SPEED_DEVELOPMENT_APPROVAL_DECISION_V01.md'
DESIGN = ROOT / 'projects/04-guardsynth-coc/docs/designs/PAPER1_SPEED_CLAUSE_BINDING_DESIGN_V02.md'
PACKET = BASE / 'source-gap-ui-2026-09-09-002'
HELD = {79, 81}


def contract_for(kind, cid, refs):
    return parse_speed_contract({'contract_version': 'eblc-speed-contract-v0.1', 'contract_id': cid,
        'subject_id': 'ego', 'target_entity_id': None, 'predicate_id': kind.lower(), 'clause_kind': kind,
        'rule_ref': refs[0], 'source_refs': refs, 'claim_scope': 'CONDITIONAL_SINGLE_DECISION_NOT_VEHICLE_SAFETY'})


def add_query(core, qid, formula, expected):
    core['queries'].append({'id': qid, 'formula': formula, 'expected': expected,
        'classification': 'EXAMPLE', 'source_refs': core['source_refs'], 'description': qid})


def premises(motion, truth, valid):
    return conjunction(eq('motion', motion, 'Motion'), eq('applicability', truth, 'Truth'), eq('evidence_valid', valid))


def verification_core(contract, cases):
    core = lower_speed_contract(contract)
    translated = {prior.UNRESOLVED: 'UNRESOLVED', prior.BLOCKED: 'EXCLUDED',
                  prior.NOT_EXCLUDED: 'NOT_EXCLUDED_BY_THIS_CLAUSE'}
    for i, case in enumerate(cases):
        if case['clause_kind'] != contract.raw['clause_kind']:
            continue
        premise = premises(case['motion_state'], case['applicability'], case['evidence_valid'])
        add_query(core, f'case_{i}_premise', premise, 'SAT')
        for action, verdict in case['verdicts'].items():
            expected = eq(action.lower() + '_verdict', translated[verdict], 'SpeedVerdict')
            prefix = f'case_{i}_{action.lower()}'
            add_query(core, prefix + '_verdict', conjunction(premise, expected), 'SAT')
            add_query(core, prefix + '_wrong', conjunction(premise, neg(expected)), 'UNSAT')
            add_query(core, prefix + '_action', conjunction(premise, eq('action', action, 'SpeedAction')),
                      'UNSAT' if verdict == prior.BLOCKED else 'SAT')
    return core


def blind_pool(rows, draft, source_scenes):
    by_sample = {r['sample_id']: r for r in draft['scenes']}
    by_id = {s['candidate_digest']: s for s in source_scenes}
    if len(by_sample) != len(draft['scenes']) or len(by_id) != len(source_scenes):
        raise ValueError('duplicate reviewer input identity')
    scenes = []
    for row in rows:
        if row['candidate_index'] in HELD:
            continue
        scene = by_id[row['candidate_digest']]
        expected = by_sample[row['sample_id']]
        if any(row[k] != scene[k] for k in ('clip_id', 'event_timestamp_us')):
            raise ValueError('review scene identity mismatch')
        frames = []
        if len(scene['frames']) != len(expected['frames']) or not scene['frames']:
            raise ValueError('frame coverage mismatch')
        for actual, reference in zip(scene['frames'], expected['frames']):
            if any(actual[k] != reference[k] for k in ('timestamp_us', 'frame_index', 'sha256')):
                raise ValueError('review frame identity mismatch')
            if actual['timestamp_us'] > row['event_timestamp_us']:
                raise ValueError('future reviewer frame')
            prefix, encoded = actual['data_url'].split(',', 1)
            if prefix != 'data:image/jpeg;base64' or prior.sha(base64.b64decode(encoded, validate=True)) != actual['sha256']:
                raise ValueError('review image hash mismatch')
            frames.append({k: actual[k] for k in ('timestamp_us', 'sha256', 'data_url')})
        if any(a['timestamp_us'] >= b['timestamp_us'] for a, b in zip(frames, frames[1:])):
            raise ValueError('unordered reviewer frames')
        scenes.append({'sample_id': row['sample_id'], 'event_timestamp_us': row['event_timestamp_us'], 'frames': frames})
    # Explicit allowlist also for top-level fields; no coordinator material can pass through.
    return {'status': 'PREPARED_POOL_NOT_ASSIGNED_NOT_DISPATCHED',
            **{k: draft[k] for k in ('question_ko', 'actions', 'assessment_choices', 'instructions_ko', 'time_scope')},
            'scenes': scenes}


def execute(output):
    if output.exists():
        raise FileExistsError(output)
    inputs = {}

    def pin(path, expected=None):
        data = path.read_bytes()
        if expected is not None and prior.sha(data) != expected:
            raise ValueError('pinned input hash mismatch: ' + str(path))
        inputs[str(path.relative_to(ROOT))] = prior.sha(data)
        return data

    def load(run, name):
        m = json.loads(pin(run / 'RUN_MANIFEST.json'))
        return json.loads(pin(run / name, m['output_hashes'][name]))

    policy_ref = 'sha256:' + prior.sha(pin(DECISION)) + '#accepted-development-semantics'
    pin(DESIGN)
    bindings = load(PROPOSAL, 'source_clause_bindings.json')
    cases = load(PROPOSAL, 'proposed_interface_cases.json')['cases']
    reused = load(prior.PREPARATION, 'coordinator_reuse_audit.json')['records']
    draft = load(prior.PREPARATION, 'action_input_draft.json')
    scenes = load(PACKET, 'source_gap_packet.json')['scenes']
    exposure = load(prior.PREFLIGHT, 'split_exposure_ledger.json')
    rows = bindings['records']
    if (len(rows) != 21 or len(reused) != 21 or len({r['candidate_digest'] for r in rows}) != 21
            or len(rows) + len(bindings['outside_speed_subset']) != 32):
        raise ValueError('candidate denominator mismatch')
    for row, previous in zip(rows, reused):
        if any(row[k] != previous[k] for k in ('candidate_digest', 'candidate_index', 'original_coc', 'original_coc_sha256')):
            raise ValueError('source binding drift')
    pool = blind_pool(reused, draft, scenes)
    if len(pool['scenes']) != 19:
        raise ValueError('held route scenes not excluded')
    output.mkdir(parents=True, exist_ok=False, mode=0o700)

    def write(name, value):
        (output / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')

    def check(name, core):
        checked = check_queries(compile_core_model(parse_core_model(core)))
        if checked['query_count'] != checked['matches_expected']:
            raise ValueError('speed SMT check failed')
        write(name + '_core.json', core)
        write(name + '_checks.json', checked)
        return checked['query_count']

    total = mutations = scene_queries = 0
    for kind in prior.KINDS:
        contract = contract_for(kind, kind.lower(), [policy_ref])
        total += check(kind.lower(), verification_core(contract, cases))
        mutant = lower_speed_contract(contract)
        mutant['clauses'] = [c for c in mutant['clauses'] if c['id'] != 'speed_action_gate']
        premise = premises('MOVING', 'TRUE', True)
        add_query(mutant, 'mutation_premise', premise, 'SAT')
        add_query(mutant, 'excluded_maintain_counterexample', conjunction(premise, eq('action', 'MAINTAIN_SPEED', 'SpeedAction')), 'SAT')
        mutations += check(kind.lower() + '_mutation', mutant)
    records = []
    for row in rows:
        kind = row['source_claim']['proposed_clause_kind']
        record = {**row, 'proposal_status': 'DEVELOPMENT_SEMANTICS_ACCEPTED_SOURCE_PENDING',
                  'route_hold': row['candidate_index'] in HELD, 'contract_file': None, 'cnl_file': None,
                  'reviewer_dispatch_allowed': False, 'training_allowed': False}
        if kind:
            name = 'candidate_' + str(row['candidate_index'])
            refs = [policy_ref, 'sha256:' + row['original_coc_sha256'] + '#source-claim-not-authority',
                    'sha256:' + inputs[str((PROPOSAL / 'source_clause_bindings.json').relative_to(ROOT))] + '#' + row['candidate_digest']]
            contract = contract_for(kind, name, refs)
            core = lower_speed_contract(contract)
            premise = premises('UNKNOWN', 'UNKNOWN', False)
            add_query(core, 'scene_unknown_premise', premise, 'SAT')
            for action in ACTIONS:
                add_query(core, action.lower() + '_not_certified', conjunction(premise,
                    neg(eq(action.lower() + '_verdict', 'UNRESOLVED', 'SpeedVerdict'))), 'UNSAT')
                add_query(core, action.lower() + '_not_excluded', conjunction(premise, eq('action', action, 'SpeedAction')), 'SAT')
            scene_queries += check(name, core)
            document = render_speed_contract(contract)
            write(name + '_contract.json', contract.raw)
            write(name + '_cnl_mapping.json', document.mapping_record())
            (output / (name + '_cnl.txt')).write_text(document.text)
            record.update(contract_file=name + '_contract.json', cnl_file=name + '_cnl.txt')
        records.append(record)
    write('coordinator_bindings.json', {'audience': 'COORDINATOR_ONLY_NOT_ACTION_REVIEWER', 'records': records,
                                       'outside_speed_subset': bindings['outside_speed_subset']})
    write('action_input_pool.json', pool)
    write('review_preparation.json', {'status': 'UNASSIGNED_NOT_RESPONSES', 'intended_available_reviewer': 'Jonh',
        'actual_assignment_count': None, 'dispatch_authorized': False,
        'exposure_declaration': {'reviewer_id': None, 'declared_at': None,
            'seen_original_coc': None, 'seen_source_answers': None, 'seen_polygons_or_machine_verdicts': None,
            'seen_cnl_or_model_outputs': None, 'notes': None},
        'response_template': [{'sample_id': s['sample_id'], 'reviewer_id': None, 'reviewed_at': None,
            'action_assessments': dict.fromkeys(ACTIONS), 'reason': None} for s in pool['scenes']],
        'required_order': 'ACTION_BEFORE_CNL', 'formal_reviewers_required': 2})
    result = {'project_id': 'guardsynth-coc', 'status': 'SPEED_EXECUTION_COMPLETE_REVIEWER_DECLARATION_AND_ASSIGNMENT_PENDING',
        'development_semantics_accepted': True, 'common_input_accepted': True, 'candidate_denominator': 32,
        'speed_candidates': 21, 'held_candidates': sorted(HELD), 'prepared_action_scenes': 19,
        'prepared_causal_jpegs': sum(len(s['frames']) for s in pool['scenes']), 'conditional_contracts': 15,
        'conditional_cnl_documents': 15, 'synthetic_smt_queries': total, 'mutation_queries': mutations,
        'scene_unknown_queries': scene_queries, 'solver_matches_expected': total + mutations + scene_queries,
        'scene_applicability_certified': 0, 'independent_speed_action_gold': 0, 'independent_cnl_reviews': 0,
        'reviewer_dispatched': 0, 'actual_assignment_count': None, 'new_training_scenes': 0,
        'main_endpoint_frozen': False, 'main_split_frozen': False, 'old_action_review_suspended': True,
        'excluded_test_clips': len(exposure['excluded_test_clip_ids']), 'm16_gate': 'PARTIAL', 'm17_gate': 'PARTIAL',
        'violation_metric': 'NOT_EVALUATED', 'nominal_progress_metric': 'NOT_EVALUATED'}
    write('RESULT.json', result)
    (output / 'REPORT_KO.md').write_text('# 승인된 속도 개발 의미 실행\n\n'
        '사용자의 두 승인 사항을 결정 문서로 기록하고 기존 제안/immutable run은 보존했다.\n\n'
        f'조건부 속도 계약/CNL 15건, 합성 SMT {total}질의, 규칙 제거 mutation {mutations}질의, '
        f'실제 scene UNKNOWN 전제 {scene_queries}질의가 예상과 일치했다. 이는 승인된 개발 의미의 '
        '검증이며 장면 적용성·독립 행동 정답·실제 안전성 검증이 아니다. 모든 실제 motion/applicability는 UNKNOWN이다.\n\n'
        '기존 원답 21건 및 전체 분모 32를 유지했다. #79/#81을 문맥 확인까지 보류하고 나머지 '
        '19건/133 causal JPEG를 CoC·답변·도형·기계판정 없는 미배정 ACTION 입력으로 준비했다. '
        '입력 JSON은 자체 이미지 포함, 새 UI/포털 등록/배포는 없다. 원문 강도는 보존하지만 평가하지 않는다.\n\n'
        '## 실제 필요한 다음 사람 입력\n\n'
        'Jonh 본인의 CoC/기존 답변/도형·기계판정/CNL·모델 출력 노출 여부 선언이 필요하다. '
        '그 선언과 검토 가능 범위를 받은 뒤 실제 장면 배정·배포를 별도로 결정해야 한다. '
        '현재 준비 수 19는 배정 수가 아니며 이를 자동 배포하지 않는다. 이미 승인된 정책·공통 입력은 다시 묻지 않는다.\n\n'
        'ACTION 뒤 CNL 순서 및 2인 formal gate 유지. 독립 속도 gold 0/21, 독립 CNL 검토 0, '
        '위반/진행 NOT_EVALUATED, 신규 학습 0. 본 endpoint/cohort/gold/split 미동결, M16/M17 PARTIAL.\n')
    code = [Path(__file__), Path(prior.__file__)]
    code += sorted((ROOT / 'platforms/eblc-bcv/src/guard_synth_eblc').glob('*.py'))
    code += sorted((ROOT / 'platforms/eblc-bcv/src/guard_synth_eblc/schemas').glob('*.json'))
    code.append(ROOT / 'cli/solver_runtime.py')
    write('RUN_MANIFEST.json', {'project_id': 'guardsynth-coc', 'experiment_id': output.parent.name,
        'run_id': output.name, 'created_at_utc': datetime.now(timezone.utc).isoformat(), 'status': result['status'],
        'input_hashes': inputs, 'code_hashes': {str(p.relative_to(ROOT)): prior.sha(p.read_bytes()) for p in code},
        'output_hashes': {p.name: prior.sha(p.read_bytes()) for p in sorted(output.iterdir())},
        'solver_runtime': SOLVER.manifest(), 'network_used': False})
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    args = parser.parse_args()
    if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*-[0-9]+', args.run_id):
        parser.error('unused numeric-suffix run ID required')
    print(json.dumps(execute(BASE / args.run_id), ensure_ascii=False, indent=2))
