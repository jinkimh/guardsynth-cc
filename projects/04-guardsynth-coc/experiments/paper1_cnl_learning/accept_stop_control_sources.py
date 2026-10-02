"""Apply two conversation-confirmed STOP controls without reading ACTION labels."""
import argparse
from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
import re

import bind_speed_sources as prior
e = prior.execution
ROOT, BASE = prior.ROOT, prior.BASE
SOURCE = BASE / 'speed-source-binding-2026-09-29-001'
DECISION = ROOT / 'projects/04-guardsynth-coc/docs/decisions/PAPER1_STOP_CONTROL_SOURCE_CONFIRMATION_DECISION_V01.md'
STATEMENTS = {7: '#7 - 작업자의 STOP 표지가 에고 차량에 대한 정지 지시로 보임',
              68: '#68 - 작업자의 STOP 표지가 에고 차량에 대한 정지 지시로 보임'}


def apply_confirmation(row, confirmation, ref):
    n = row['candidate_index']
    if (n not in STATEMENTS or confirmation['verbatim'] != STATEMENTS[n]
            or confirmation['source_type'] != 'USER_CONVERSATION'
            or any(confirmation[k] != row[k] for k in ('candidate_index', 'candidate_digest', 'event_timestamp_us'))
            or confirmation['authenticated_reviewer_attestation'] is not False):
        raise ValueError('confirmation identity/provenance/scope mismatch')
    stop = [c for c in row['active_source_controls'] if (c['signal'] or {}).get('intent') == 'Stop'
            and (c['signal'] or {}).get('sign_type') == 'Stop Sign'
            and (c['signal'] or {}).get('source') == 'Holding sign']
    if len(stop) != 1 or not row['reported_applied_control_with_stop_annotation']:
        raise ValueError('expected scoped STOP source corroboration missing')
    bound = deepcopy(row)
    bound['speed_premises'] = {'motion_state': 'UNKNOWN', 'applicability': 'TRUE', 'evidence_valid': True}
    bound['accepted_stop_control'] = {'target_id': f'user_reported_stop_paddle_{n}',
        'source_ref': ref, 'description_ko': '사용자가 ego에 대한 정지 지시로 확인한 작업자의 STOP 표지',
        'scope': 'USER_CONFIRMED_DEVELOPMENT_STOP_CONTROL_ONLY',
        'cascade_corroboration_ref': stop[0]['evidence_ref'], 'cascade_physical_identity_certified': False,
        'red_light_certified': False, 'motion_certified': False, 'release_certified': False}
    # The old observer point remains separate; no false Agent/point identity is introduced.
    bound['gaps'] = [g for g in bound['gaps'] if g['field'] != 'speed_applicability']
    bound['gaps'].append({'field': 'cnl_human_fidelity', 'reason': 'INDEPENDENT_SEMANTIC_ACCEPTANCE_PENDING',
                         'source_refs': [ref], 'required': 'No human CNL answer is fabricated.'})
    return bound


def bound_core(contract, row, motion='UNKNOWN'):
    if (row['speed_premises'] != {'motion_state': 'UNKNOWN', 'applicability': 'TRUE', 'evidence_valid': True}
            or contract['target_entity_id'] != row['accepted_stop_control']['target_id']
            or motion not in ('UNKNOWN', 'MOVING', 'STATIONARY')):
        raise ValueError('unaccepted or mismatched stop premise')
    core = prior.source_core(contract, row)
    fact_clause = next(c for c in core['clauses'] if c['id'] == 'pinned_source_report_facts')
    fact_clause['formula']['args'][-1] = e.premises(motion, 'TRUE', True)
    fact_clause['source_refs'].append(row['accepted_stop_control']['source_ref'])
    core['queries'] = core['queries'][:1]
    for name, value, enum in [('motion', motion, 'Motion'), ('applicability', 'TRUE', 'Truth'), ('evidence_valid', True, None)]:
        e.add_query(core, name + '_cannot_drift', e.neg(e.eq(name, value, enum)), 'UNSAT')
    verdicts = e.prior.probe('STOP_REQUIRED', motion, 'TRUE', True)
    translate = {e.prior.UNRESOLVED: 'UNRESOLVED', e.prior.BLOCKED: 'EXCLUDED', e.prior.NOT_EXCLUDED: 'NOT_EXCLUDED_BY_THIS_CLAUSE'}
    for action, verdict in verdicts.items():
        e.add_query(core, action.lower() + '_wrong', e.neg(e.eq(action.lower() + '_verdict', translate[verdict], 'SpeedVerdict')), 'UNSAT')
        e.add_query(core, action.lower() + '_selection', e.eq('action', action, 'SpeedAction'),
                    'UNSAT' if verdict == e.prior.BLOCKED else 'SAT')
    return core


def render_bound_cnl(contract, row):
    if row['speed_premises'] != {'motion_state': 'UNKNOWN', 'applicability': 'TRUE', 'evidence_valid': True}:
        raise ValueError('renderer requires exact accepted premise')
    base = e.render_speed_contract(e.parse_speed_contract(contract))
    control = row['accepted_stop_control']
    text = (f"후보 #{row['candidate_index']}, 판단 시점 {row['event_timestamp_us']}us. 사용자 대화 확인에 따라 "
            f"{control['target_id']}의 작업자 STOP 표지는 ego에 대한 정지 지시로 개발 범위에서 수용되었다. "
            "이 정지 통제의 applicability=TRUE, evidence_valid=true이다. motion=UNKNOWN이므로 "
            "현재 네 행동 verdict는 모두 UNRESOLVED이며, 정지 완료나 행동 적절성을 인증하지 않는다. "
            "STOP_OR_WAIT는 이동 중 정지를 위한 감속을 포함한다. 정지 목적 감속을 금지하지 않는다. "
            "정지 통제 해제와 다른 의무는 확인되지 않았다.\n")
    if row['candidate_index'] == 68:
        text += '이번 근거는 작업자의 STOP paddle이다. 원 CoC의 red-light 주장은 별개이며 확인되지 않았다.\n'
    text += '\n' + base.text
    mapping = {'renderer_version': 'paper1-stop-source-cnl-v0.1', 'base_renderer_version': base.renderer_version,
        'text_sha256': prior.sha(text.encode()), 'contract_sha256': base.input_sha256,
        'scene_field_paths': ['$.candidate_index', '$.event_timestamp_us', '$.accepted_stop_control', '$.speed_premises'],
        'source_refs': [control['source_ref'], control['cascade_corroboration_ref']],
        'base_mapping': base.mapping_record(), 'human_semantic_acceptance': False}
    return text, mapping


def execute(output):
    if output.exists():
        raise FileExistsError(output)
    inputs = {}
    def pin(path, expected=None):
        data = path.read_bytes()
        if expected is not None and prior.sha(data) != expected:
            raise ValueError('input hash mismatch: ' + str(path))
        inputs[str(path.relative_to(ROOT))] = prior.sha(data)
        return data
    def load(run, name):
        m = json.loads(pin(run / 'RUN_MANIFEST.json'))
        return json.loads(pin(run / name, m['output_hashes'][name]))
    rows = load(SOURCE, 'source_speed_bindings.json')['records']
    exposure = load(SOURCE, 'split_exposure_ledger.json')
    decision_ref = 'sha256:' + prior.sha(pin(DECISION))
    pin(ROOT / 'projects/04-guardsynth-coc/docs/decisions/PAPER1_SINGLE_REVIEWER_ACTION_DECISION_V01.md')
    confirmations = {'source_type': 'USER_CONVERSATION', 'recorded_date': '2026-09-29',
        'utterance_timestamp': None, 'speaker': 'USER_AS_RELAYED_IN_CURRENT_CONVERSATION',
        'authenticated_reviewer_attestation': False, 'jonh_new_attestation': False, 'records': []}
    for row in rows:
        if row['candidate_index'] in STATEMENTS:
            confirmations['records'].append({**{k: row[k] for k in ('candidate_index', 'candidate_digest', 'event_timestamp_us')},
                'verbatim': STATEMENTS[row['candidate_index']], 'source_type': 'USER_CONVERSATION',
                'authenticated_reviewer_attestation': False, 'scope': 'EGO_APPLICABLE_WORKER_STOP_PADDLE_ONLY'})
    if len(rows) != 19 or len(confirmations['records']) != 2:
        raise ValueError('source denominator mismatch')
    payload = json.dumps(confirmations, ensure_ascii=False, indent=2) + '\n'
    artifacts, checks = {}, {}
    updated = deepcopy(rows)
    for i, note in enumerate(confirmations['records']):
        pos = next(j for j, r in enumerate(rows) if r['candidate_index'] == note['candidate_index'])
        ref = 'sha256:' + prior.sha(payload.encode()) + f'#/records/{i}'
        row = apply_confirmation(rows[pos], note, ref)
        updated[pos] = row
        original = load(prior.CONTRACTS, f"candidate_{note['candidate_index']}_contract.json")
        contract = deepcopy(original)
        contract.update(target_entity_id=row['accepted_stop_control']['target_id'],
            predicate_id='worker_stop_control_applies_to_ego',
            source_refs=[original['rule_ref'], decision_ref, ref, row['accepted_stop_control']['cascade_corroboration_ref']])
        if contract['clause_kind'] != 'STOP_REQUIRED':
            raise ValueError('scoped acceptance cannot alter clause kind')
        prefix = f"candidate_{note['candidate_index']}"
        artifacts[prefix + '_contract.json'] = contract
        for motion in ('UNKNOWN', 'MOVING', 'STATIONARY'):
            core = bound_core(contract, row, motion)
            checked = e.check_queries(e.compile_core_model(e.parse_core_model(core)))
            if checked['query_count'] != checked['matches_expected']:
                raise ValueError('scoped source SMT regression')
            label = prefix + ('_actual' if motion == 'UNKNOWN' else '_hypothetical_' + motion.lower())
            artifacts[label + '_core.json'] = core
            checks[label] = checked
        text, mapping = render_bound_cnl(contract, row)
        artifacts[prefix + '_cnl.txt'] = text
        artifacts[prefix + '_cnl_mapping.json'] = mapping
    result = {'project_id': 'guardsynth-coc', 'status': 'TWO_STOP_CONTROL_PREMISES_ACCEPTED_MOTION_CNL_PENDING',
        'accepted_source_candidates': [7, 68], 'source_type': 'USER_CONVERSATION', 'new_authenticated_jonh_attestation': False,
        'source_scene_denominator': 19, 'unchanged_other_scenes': 17, 'held_candidates': [79, 81],
        'actual_source_core_models': 2, 'hypothetical_motion_models': 4, 'scene_cnl_documents': 2,
        'actual_smt_queries': sum(v['query_count'] for k, v in checks.items() if k.endswith('_actual')),
        'hypothetical_smt_queries': sum(v['query_count'] for k, v in checks.items() if not k.endswith('_actual')),
        'actual_motion': 'UNKNOWN', 'actual_action_verdicts': 'ALL_UNRESOLVED', 'red_light_certified': False,
        'action_targets_read': 0, 'new_training_scenes': 0, 'main_training_started': False,
        'action_reviewer_count_requirement_met': True, 'inter_rater_reliability': 'NOT_MEASURED_SINGLE_REVIEWER',
        'cnl_human_fidelity_accepted': False, 'm16_gate': 'PARTIAL', 'm17_gate': 'PARTIAL'}
    artifacts.update({'confirmation.json': payload, 'source_speed_bindings.json': {'records': updated, 'held_candidates': [79, 81]},
        'split_exposure_ledger.json': exposure, 'checks.json': checks, 'RESULT.json': result})
    artifacts['REPORT_KO.md'] = ('# 두 STOP 통제 source 확인 적용\n\n'
        '#7/#68의 사용자 원문을 USER_CONVERSATION으로 confirmation.json에 기록했다. 정확한 발화 시각은 null이며 새 인증 Jonh 진술이 아니다.\n\n'
        '두 장면의 작업자 STOP 표지 → ego 정지 지시 전제를 개발 범위에서 수용했다. applicability TRUE/evidence_valid true로 실제 Core에 고정했다. scene-local 표지 식별자를 연결했으며 CASCADE Agent 동일성은 인증하지 않았다. #68 원 CoC red-light 주장은 별개로 보존한다.\n\n'
        f"실제 UNKNOWN-motion Core2개 {result['actual_smt_queries']}질의, 가정 MOVING/STATIONARY4개 {result['hypothetical_smt_queries']}질의 통과. 가정은 현재 motion 확인이나 ACTION 정답이 아니다. 현재 모든 행동 verdict는 UNRESOLVED다.\n\n"
        '장면별 CNL2건과 source/field/hash 대응을 생성했다. 정지 목적 감속 금지로 의미가 뒤집히지 않는지 검사한다. 독립 CNL 의미 수용은 미완료다.\n\n'
        '남은 gap: 두 장면의 motion 단위·시계·오차/정지 기준, CASCADE 물리적 대상 동일성, 독립 CNL fidelity. 다른17장면의 적용성 gap과 계약 없는6건은 그대로다. #52/#55/#60 원문 불일치,3마스크,held79/81,32분모,81clip 시험제외와 split/power를 보존한다.\n\n'
        '단일 검토자 ACTION19건은 검토자 수 요건을 충족한다. 새 ACTION/설문/UI·학습/export·commit/push 없음. 두 STOP 관찰은 다시 묻지 않는다. 다음은 이동 근거의 해석 범위와 생성된 두 CNL의 독립 의미 확인이며, source 확인 자체는 완료다.\n')
    output.mkdir(parents=True, exist_ok=False, mode=0o700)
    for name, value in artifacts.items():
        (output / name).write_text(value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, indent=2) + '\n')
    code = [Path(__file__), Path(prior.__file__), ROOT / 'platforms/eblc-bcv/src/guard_synth_eblc/speed_contract.py',
            ROOT / 'projects/04-guardsynth-coc/tests/integration/test_stop_control_source_acceptance.py']
    manifest = {'project_id': 'guardsynth-coc', 'run_id': output.name, 'status': 'COMPLETE',
        'created_at_utc': datetime.now(timezone.utc).isoformat(), 'input_hashes': inputs,
        'code_hashes': {str(p.relative_to(ROOT)): prior.sha(p.read_bytes()) for p in code},
        'output_hashes': {p.name: prior.sha(p.read_bytes()) for p in output.iterdir()}, 'network_used': False}
    (output / 'RUN_MANIFEST.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    args = parser.parse_args()
    if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*-[0-9]+', args.run_id):
        parser.error('invalid run-id')
    print(json.dumps(execute(BASE / args.run_id), indent=2))
