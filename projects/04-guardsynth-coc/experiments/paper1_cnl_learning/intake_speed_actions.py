"""Accept actual development ACTION responses and export a scoped evaluation bank.

Response receipt is not scene applicability, formal two-reviewer gold or SFT admission.
Original responses and user clarification provenance remain separate.
"""
import argparse
import base64
from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
import re

import execute_speed_contracts as execution
import prepare_speed_assignment as prep

ROOT, BASE = prep.ROOT, prep.BASE
ASSIGNMENT = BASE / 'speed-action-assigned-2026-09-29-001'
DECLARATION = BASE / 'speed-action-assignment-preparation-2026-09-29-001'
PUBLICATION = BASE / 'speed-action-publication-2026-09-29-001'
CLARIFICATION = BASE / 'speed-action-clarification-2026-09-29-001'
SUBMISSION = BASE / 'speed-action-submission-2026-09-29-001'
ACTIONS = execution.ACTIONS
CHOICES = {'APPROPRIATE', 'INAPPROPRIATE', 'UNDETERMINED'}


def validate_response(response, packet, digest):
    if (response.get('status') != 'COMPLETED_NOT_RECEIVED'
            or response.get('packet_sha256') != digest
            or any(response.get(k) != packet[k] for k in ('assignment_id', 'reviewer_id'))):
        raise ValueError('submission status or assignment/packet identity mismatch')
    stamp = datetime.fromisoformat(response['exported_at'].replace('Z', '+00:00'))
    if stamp.tzinfo is None:
        raise ValueError('export timestamp lacks timezone')
    rows = response.get('records')
    if not isinstance(rows, list) or len(rows) != len(packet['scenes']):
        raise ValueError('response coverage mismatch')
    expected = [s['sample_id'] for s in packet['scenes']]
    if len(set(expected)) != len(expected) or [r.get('sample_id') for r in rows] != expected:
        raise ValueError('response sample identity/order mismatch')
    for row in rows:
        answers = row.get('action_assessments')
        if (not isinstance(answers, dict) or set(answers) != set(ACTIONS)
                or any(v not in CHOICES for v in answers.values())):
            raise ValueError('missing or invalid action judgment')
        if not isinstance(row.get('reason'), str) or not row['reason'].strip():
            raise ValueError('missing action reason')
        if 'BROWSER TEST ONLY' in row['reason'] or 'NOT A REVIEWER RESPONSE' in row['reason']:
            raise ValueError('synthetic browser response is not a submission')


def targets_with_scope(response, clarifications, assignment):
    targets = []
    for row, candidate in zip(response['records'], assignment['candidate_indices']):
        targets.append({'sample_id': row['sample_id'], 'candidate_index': candidate,
            'raw_assessments': deepcopy(row['action_assessments']), 'raw_reason': row['reason'],
            'endpoint_assessments': deepcopy(row['action_assessments']),
            'scope_limited_actions': {}, 'evidence_class': 'SINGLE_REVIEWER_DEVELOPMENT_SELF_REPORT',
            'training_allowed': False, 'main_test_allowed': False})
    seen = set()
    for note in clarifications['records']:
        position, action = note['review_position'] - 1, note['affected_action']
        if position < 0 or position >= len(targets) or action not in ACTIONS:
            raise ValueError('clarification position/action mismatch')
        row = targets[position]
        if ((position, action) in seen or row['sample_id'] != note['sample_id']
                or row['candidate_index'] != note['candidate_index']
                or row['raw_assessments'][action] != note['original_assessment']
                or note['normalized_assessment'] is not None or note['raw_answer_overwritten']):
            raise ValueError('clarification binding mismatch')
        seen.add((position, action))
        # Mask the broad endpoint interpretation, never invent an alternative judgment.
        row['endpoint_assessments'][action] = None
        row['scope_limited_actions'][action] = {
            'meaning': note['interpretation'], 'clarification_ko': note['clarification_ko'],
            'source': clarifications['source'], 'new_reviewer_attestation': False}
    return targets


def score_development(targets, predictions):
    """Three-way predictions, but score only definite, unmasked reviewer assessments."""
    ids = [r['sample_id'] for r in targets]
    if (len(predictions) != len(ids) or len(set(ids)) != len(ids)
            or [r.get('sample_id') for r in predictions] != ids):
        raise ValueError('prediction coverage/order mismatch')
    matched = scored = abstained = 0
    for row, prediction in zip(targets, predictions):
        answers = prediction.get('action_assessments')
        if (not isinstance(answers, dict) or set(answers) != set(ACTIONS)
                or any(v not in CHOICES for v in answers.values())):
            raise ValueError('prediction action schema mismatch')
        for action, truth in row['endpoint_assessments'].items():
            if truth in (None, 'UNDETERMINED'):
                continue
            scored += 1
            matched += answers[action] == truth
            abstained += answers[action] == 'UNDETERMINED'
    return {'metric': 'DEVELOPMENT_REVIEWER_JUDGMENT_AGREEMENT_NOT_SAFETY',
        'scenes_retained': len(targets), 'slots_total': len(targets) * len(ACTIONS),
        'slots_scored': scored, 'matches': matched, 'prediction_abstentions_on_scored_slots': abstained,
        'agreement': matched / scored if scored else None}


def execute(output):
    if output.exists():
        raise FileExistsError(output)
    inputs = {}

    def pin(path, expected=None):
        data = path.read_bytes()
        digest = prep.sha(data)
        if expected is not None and digest != expected:
            raise ValueError('pinned input drift: ' + str(path))
        inputs[str(path.relative_to(ROOT))] = digest
        return data

    def load(run, name):
        manifest = json.loads(pin(run / 'RUN_MANIFEST.json'))
        return json.loads(pin(run / name, manifest['output_hashes'][name]))

    assignment = load(ASSIGNMENT, 'assignment_record.json')
    packet = load(ASSIGNMENT, 'action_review_packet.json')
    packet_sha = prep.sha((ASSIGNMENT / 'action_review_packet.json').read_bytes())
    if (assignment['candidate_indices'] != prep.INDICES or assignment['held_candidate_indices'] != [79, 81]
            or not assignment['assignment_approved'] or assignment['packet_sha256'] != packet_sha):
        raise ValueError('assigned scope mismatch')
    declaration = load(DECLARATION, 'reviewer_self_report.json')
    prep.accept_declaration(declaration)
    published = load(PUBLICATION, 'RESULT.json')
    if not published['publication_verified'] or published['assigned_scenes'] != len(packet['scenes']):
        raise ValueError('publication evidence mismatch')
    clarifications = load(CLARIFICATION, 'clarifications.json')
    raw = pin(SUBMISSION / 'jonh_speed_action_submission.json', clarifications['submission_sha256'])
    draft_bytes = pin(SUBMISSION / 'jonh_speed_action_draft.json')
    response, draft = json.loads(raw), json.loads(draft_bytes)
    validate_response(response, packet, packet_sha)
    if draft['records'] != response['records'] or any(draft[k] != response[k]
            for k in ('assignment_id', 'reviewer_id', 'packet_sha256')):
        raise ValueError('draft/final discrepancy needs reconciliation')
    targets = targets_with_scope(response, clarifications, assignment)
    bindings = load(prep.SOURCE, 'coordinator_bindings.json')
    reuse = load(BASE / 'longitudinal-endpoint-preparation-2026-09-28-002', 'coordinator_reuse_audit.json')
    by_index = {r['candidate_index']: r for r in bindings['records']}
    sample_map = {r['candidate_index']: r['sample_id'] for r in reuse['records']}
    exported_inputs, comparisons, fidelity, cnl_groups = [], [], [], {}
    frame_count = query_count = 0
    for i, (scene, target) in enumerate(zip(packet['scenes'], targets)):
        candidate = target['candidate_index']
        bound = by_index[candidate]
        if bound['route_hold'] or sample_map[candidate] != scene['sample_id']:
            raise ValueError('held candidate or sample mapping drift')
        frames = scene['frames']
        if not frames or any(a['timestamp_us'] >= b['timestamp_us'] for a, b in zip(frames, frames[1:])):
            raise ValueError('invalid frame order')
        for frame in frames:
            prefix, encoded = frame['data_url'].split(',', 1)
            if (prefix != 'data:image/jpeg;base64' or frame['timestamp_us'] > scene['event_timestamp_us']
                    or prep.sha(base64.b64decode(encoded, validate=True)) != frame['sha256']):
                raise ValueError('causal frame identity mismatch')
        frame_count += len(frames)
        target['clip_group'] = bound['clip_id']
        target['sample_time_us'] = scene['event_timestamp_us']
        exported_inputs.append({'sample_id': scene['sample_id'], 'question_ko': packet['question_ko'],
            'actions': packet['actions'], 'assessment_choices': packet['assessment_choices'],
            'instructions_ko': packet['instructions_ko'], 'time_scope': packet['time_scope'],
            'packet_ref': str((ASSIGNMENT / 'action_review_packet.json').relative_to(ROOT)),
            'packet_sha256': packet_sha, 'scene_pointer': f'/scenes/{i}',
            'frames': [{k: f[k] for k in ('timestamp_us', 'sha256')} for f in frames]})
        source_action = bound['source_claim']['source_recommendation_action']
        assessed = target['endpoint_assessments'].get(source_action)
        outcome = ('UNMAPPED_SOURCE_ACTION' if source_action is None else
                   'SCOPE_LIMITED' if assessed is None else
                   'UNDETERMINED' if assessed == 'UNDETERMINED' else
                   'AGREES_AT_ACTION_CATEGORY_ONLY' if assessed == 'APPROPRIATE' else
                   'SOURCE_ACTION_DISAGREEMENT')
        comparison = {'candidate_index': candidate, 'sample_id': scene['sample_id'],
            'original_coc': bound['original_coc'], 'original_coc_sha256': bound['original_coc_sha256'],
            'source_action': source_action, 'reviewer_assessment_of_source_action': assessed,
            'comparison': outcome, 'contract_available': bool(bound['contract_file']),
            'scene_applicability': bound['speed_clause_applicability'],
            'motion_state': bound['current_motion_state'],
            'scene_verdicts': bound['scene_clause_verdicts'],
            'cnl_vs_action_agreement': 'NOT_EVALUATED_MISSING_SCENE_PREMISES',
            'training_allowed': False}
        comparisons.append(comparison)
        if not bound['contract_file']:
            continue
        contract_raw = load(prep.SOURCE, bound['contract_file'])
        contract = execution.parse_speed_contract(contract_raw)
        document = execution.render_speed_contract(contract)
        m = json.loads(pin(prep.SOURCE / 'RUN_MANIFEST.json'))
        text = pin(prep.SOURCE / bound['cnl_file'], m['output_hashes'][bound['cnl_file']]).decode()
        mapping_name = bound['cnl_file'].replace('_cnl.txt', '_cnl_mapping.json')
        mapping = load(prep.SOURCE, mapping_name)
        if document.text != text or json.loads(json.dumps(document.mapping_record())) != mapping:
            raise ValueError('CNL replay/field mapping mismatch')
        core = load(prep.SOURCE, bound['contract_file'].replace('_contract.json', '_core.json'))
        checked = execution.check_queries(execution.compile_core_model(execution.parse_core_model(core)))
        if checked['matches_expected'] != checked['query_count']:
            raise ValueError('scene UNKNOWN replay failed')
        query_count += checked['query_count']
        clauses = [c for c in mapping['clauses'] if c['clause_id'] in ('speed.actions', 'speed.gate')]
        key = prep.sha(json.dumps(clauses and [c['text'] for c in clauses], ensure_ascii=False).encode())
        group = cnl_groups.setdefault(key, {'kind': contract_raw['clause_kind'], 'candidate_indices': [],
            'clauses': [{'clause_id': c['clause_id'], 'text': c['text']} for c in clauses],
            'human_fidelity_review': 'NOT_RECEIVED', 'scene_grounding_review_substituted': False})
        group['candidate_indices'].append(candidate)
        fidelity.append({'candidate_index': candidate, 'text_replay_matches': True,
            'mapping_replay_matches': True, 'conditional_unknown_queries_passed': checked['query_count'],
            'target_bound': contract_raw['target_entity_id'] is not None,
            'scene_applicability_certified': False, 'human_meaning_review': False})

    counts = Counter(v for r in targets for v in r['endpoint_assessments'].values())
    source_counts = Counter(r['comparison'] for r in comparisons)
    baselines = {label: score_development(targets, [
        {'sample_id': r['sample_id'], 'action_assessments': dict.fromkeys(ACTIONS, label)} for r in targets])
        for label in sorted(CHOICES)}
    result = {'project_id': 'guardsynth-coc', 'status': 'DEVELOPMENT_ACTION_INTAKE_COMPLETE_SOURCE_GROUNDING_PENDING',
        'action_response_receipt_complete': True, 'accepted_response_scenes': len(targets),
        'raw_judgments_received': len(targets) * len(ACTIONS), 'reason_count': len(targets),
        'scope_limited_fields': counts[None], 'comparable_fields_including_undetermined': len(targets) * 4 - counts[None],
        'determinate_development_fields': counts['APPROPRIATE'] + counts['INAPPROPRIATE'],
        'undetermined_development_fields': counts['UNDETERMINED'],
        'fully_unmasked_scene_records': sum(not r['scope_limited_actions'] for r in targets),
        'clip_groups': len({r['clip_group'] for r in targets}), 'causal_images_verified': frame_count,
        'cohort_denominator': 32, 'speed_candidates': 21, 'held_candidates': [79, 81],
        'conditional_cnl_linked': len(fidelity), 'no_speed_contract': len(targets) - len(fidelity),
        'conditional_smt_queries_replayed': query_count, 'cnl_semantic_template_groups': len(cnl_groups),
        'source_action_comparison': dict(source_counts),
        'source_action_disagreement_candidates': [r['candidate_index'] for r in comparisons if r['comparison'] == 'SOURCE_ACTION_DISAGREEMENT'],
        'independence_basis': 'RELAYED_SELF_REPORT_NOT_AUTHENTICATED',
        'formal_two_reviewer_gate_met': False, 'formal_gold_added': 0,
        'scene_applicability_certified': 0, 'new_cnl_human_reviews': 0,
        'new_training_scenes': 0, 'new_review_requests': 0, 'main_split_frozen': False,
        'm16_gate': 'PARTIAL', 'm17_gate': 'PARTIAL'}
    output.mkdir(parents=True, exist_ok=False, mode=0o700)
    def write(name, value):
        (output / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
    (output / 'review_submission.json').write_bytes(raw)
    (output / 'review_draft.json').write_bytes(draft_bytes)
    write('clarifications.json', clarifications)
    write('reviewer_self_report.json', declaration)
    for name, rows in [('development_action_inputs.jsonl', exported_inputs), ('development_action_targets.jsonl', targets)]:
        (output / name).write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in rows))
    write('source_action_comparison.json', {'scope': 'COORDINATOR_ONLY_LEXICAL_COMPARISON_NOT_SOURCE_TRUTH', 'records': comparisons})
    write('cnl_replay.json', fidelity)
    write('cnl_reuse_index.json', {'status': 'MACHINE_REUSE_INDEX_NOT_NEW_REVIEW_REQUEST',
        'groups': list(cnl_groups.values()), 'claim': 'Repeated template text only; not scene-level fidelity or applicability.'})
    write('development_diagnostics.json', {'scope': 'CONSTANT_BASELINES_NOT_VLM_OR_LEARNING_EFFECT', 'baselines': baselines})
    write('RESULT.json', result)
    (output / 'REPORT_KO.md').write_text(
        '# 19장면 행동 응답 수용 및 개발 평가 데이터\n\n'
        f'실제 Jonh 응답 {len(targets)}장면/76판단/19근거를 정식 개발 응답으로 수용했다. '
        '원본과 초안을 바이트 그대로 보존하고 배정/시점/133 JPEG를 검증했다. '
        '이는 단일 검토자의 비노출 자기진술 기반 개발 자료이며 2인 formal gold가 아니다.\n\n'
        '## 이번에 완료한 부분\n\n'
        '- 행동 답변 수집·수용 완료: 19/19. 같은 설문을 다시 요청하지 않는다.\n'
        f'- 개발 평가 입력/응답 JSONL 각 19행, {result["clip_groups"]} clip groups. 입력과 정답 파일을 분리했다.\n'
        f'- 원답 76개 중 사용자 설명 범위 제한 3개는 넓은 행동 코드의 평가에서 제외한다. 나머지 73개 중 판단 불가 1개, 확정 응답 72개. 이는 학습 적격 수가 아니다.\n'
        '- #68의 정지 목적 감속을 비정지 감속 정답으로 쓰지 않으며 #86/#94 저속 출발을 추가 가속 정답으로 쓰지 않는다. 원답은 바꾸지 않았다.\n'
        f'- 연결된 조건부 CNL {len(fidelity)}건의 텍스트/대응 재생성과 UNKNOWN 전제 SMT {query_count}질의 통과. '
        f'중복 행동/규칙 문장은 {len(cnl_groups)}종으로 묶었다. 새 설문은 만들거나 배포하지 않았다.\n\n'
        '## 실제 학습 연결을 막는 부분\n\n'
        f'- 원본 CoC의 직접 행동 권고를 검토자가 부적절로 본 후보: {result["source_action_disagreement_candidates"]}. '
        '원문이 틀렸다고 단정하거나 자동 수정하지 않고 전체 분모에 보존한다.\n'
        f'- {len(fidelity)}개 명세는 아직 대상 미연결/현재 속도 의무 적용성 UNKNOWN인 조건부 템플릿이다. '
        'SAT 통과나 행동 정답만으로 적용성을 TRUE로 채우면 정답에서 제약을 역으로 만드는 순환이 된다.\n'
        f'- 나머지 {len(targets)-len(fidelity)}개는 기존 속도 계약이 없다. 행동 응답은 보존하되 CNL을 임의 복제하지 않는다.\n'
        '- 다음 기계 작업은 독립 행동 답변을 생성 근거에서 제외한 기존 source/관찰 기반 속도 조건 바인딩이다. '
        '그 연결 전에는 장면 CNL 정확도, 위반률, 정상 진행률, SFT export를 주장하지 않는다.\n\n'
        '## 실행 가능한 개발 진단\n\n'
        'development_action_inputs.jsonl은 고정된 기존 이미지 패킷 참조와 공통 질문만 포함한다. '
        'development_action_targets.jsonl은 원답·범위 제한·clip group을 별도로 둔다. '
        'score_development는 72개 확정·비제한 응답에서 동일 분모로 판정 일치를 계산한다. '
        '판단 불가 예측은 확정 분모에서 제외하지 않고 불일치/abstention으로 센다. '
        '상수 baseline은 채점기 진단일 뿐 VLM 결과나 안전 위반 지표가 아니다.\n\n'
        'M16: ACTION 수용 완료, source·CNL 의미·formal 조건은 PARTIAL. '
        'M17: 실행 가능한 개발 평가 데이터/채점 경로 추가, 본 split·품질 검증은 PARTIAL. '
        '기존 #18 개발 SFT 1장면은 별개로 유지하며 이번 속도 SFT 추가 0, main 학습 0.\n')
    code = [Path(__file__), Path(execution.__file__), ROOT / 'platforms/eblc-bcv/src/guard_synth_eblc/speed_contract.py']
    write('RUN_MANIFEST.json', {'project_id': 'guardsynth-coc', 'experiment_id': output.parent.name,
        'run_id': output.name, 'created_at_utc': datetime.now(timezone.utc).isoformat(),
        'input_hashes': inputs, 'code_hashes': {str(p.relative_to(ROOT)): prep.sha(p.read_bytes()) for p in code},
        'output_hashes': {p.name: prep.sha(p.read_bytes()) for p in output.iterdir()},
        'solver_runtime': execution.SOLVER.manifest(), 'network_used': False})
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    args = parser.parse_args()
    if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*-[0-9]+', args.run_id):
        parser.error('unused numeric-suffix run ID required')
    print(json.dumps(execute(BASE / args.run_id), ensure_ascii=False, indent=2))
