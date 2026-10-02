"""Accept a relayed reviewer self-report and prepare, never dispatch, a blind ACTION proposal."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re

ROOT = next(p for p in Path(__file__).resolve().parents if (p / 'PROJECT_REGISTRY.json').is_file())
BASE = ROOT / 'artifacts/projects/guardsynth-coc/restricted/guardsynth-paper1-training-readiness-001'
SOURCE = BASE / 'speed-contract-execution-2026-09-28-001'
TEMPLATE = Path(__file__).with_name('speed_action_review.html')
INDICES = [6, 7, 31, 48, 50, 52, 53, 55, 59, 60, 64, 68, 74, 84, 85, 86, 88, 93, 94]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def declaration():
    return {'reviewer_id': 'Jonh', 'evidence_type': 'REVIEWER_SELF_REPORT_RELAYED_BY_USER',
        'recorded_date': '2026-09-29', 'declared_at': None,
        'question_scope_ko': 'Jonh 본인이 원본 CoC, 기존 검토 답변·도형·기계 판정, 생성된 CNL·모델 출력을 이전에 보았는지.',
        'relayed_answer_verbatim': '아니요',
        'relay_confirmation_question_verbatim': '해당 자료를 본 적이 없다는 뜻으로 이해했습니다. 검토자 Jonh 본인의 답변을 전달해 주신 것이 맞나요? 맞다면 그 확인을 기록하고, 기존 설문을 반복하지 않는 별도의 행동 검토 배정 단계로 이어가겠습니다.',
        'relay_confirmation_answer_verbatim': '네', 'relay_confirmed_by_user': True,
        'interpretation': 'REPORTED_NO_PRIOR_EXPOSURE_TO_LISTED_MATERIALS',
        'provenance': 'USER_MESSAGE_IN_CURRENT_CONVERSATION_2026-09-29',
        'identity_authenticated': False, 'signed': False, 'webform_submission': False,
        'access_logs_verified': False, 'assignment_authorized': False}


def accept_declaration(record):
    if (record['reviewer_id'] != 'Jonh' or record['evidence_type'] != 'REVIEWER_SELF_REPORT_RELAYED_BY_USER'
            or record['relayed_answer_verbatim'] != '아니요' or record['relay_confirmation_answer_verbatim'] != '네'
            or record['relay_confirmed_by_user'] is not True):
        raise ValueError('missing or conflicting reviewer self-report provenance')
    if record['declared_at'] is not None or any(record[k] is not False for k in (
            'identity_authenticated', 'signed', 'webform_submission', 'access_logs_verified', 'assignment_authorized')):
        raise ValueError('unsupported certification or assignment claim')
    return {'status': 'ACCEPTED_RELAYED_SELF_REPORT_FOR_DEVELOPMENT_PREPARATION',
            'reviewer_id': 'Jonh', 'independence_scope': 'SELF_REPORTED_NOT_AUTHENTICATED',
            'actual_assignment_count': None, 'dispatch_allowed': False, 'formal_two_reviewer_gate_met': False}


def make_packet(pool):
    fields = ('question_ko', 'actions', 'assessment_choices', 'instructions_ko', 'time_scope')
    scenes = []
    for s in pool['scenes']:
        if set(s) != {'sample_id', 'event_timestamp_us', 'frames'}:
            raise ValueError('unexpected scene field / potential answer cue')
        for f in s['frames']:
            if set(f) != {'timestamp_us', 'sha256', 'data_url'} or f['timestamp_us'] > s['event_timestamp_us']:
                raise ValueError('unexpected or noncausal frame')
        scenes.append(s)
    return {'status': 'PROPOSED_NOT_ASSIGNED_NOT_DISPATCHED', **{k: pool[k] for k in fields}, 'scenes': scenes}


def execute(output):
    if output.exists():
        raise FileExistsError(output)
    inputs = {}
    def pin(path, expected=None):
        data = path.read_bytes()
        if expected and sha(data) != expected:
            raise ValueError('input hash mismatch')
        inputs[str(path.relative_to(ROOT))] = sha(data)
        return data
    m = json.loads(pin(SOURCE / 'RUN_MANIFEST.json'))
    def load(name):
        return json.loads(pin(SOURCE / name, m['output_hashes'][name]))
    pool, coordinator = load('action_input_pool.json'), load('coordinator_bindings.json')
    result_before = load('RESULT.json')
    selected = [r for r in coordinator['records'] if not r['route_hold']]
    if ([r['candidate_index'] for r in selected] != INDICES or len(pool['scenes']) != 19
            or result_before['held_candidates'] != [79, 81]):
        raise ValueError('assignment scope drift')
    # Sample identity mapping is pinned by the prior preparation; keep it coordinator-only.
    previous = BASE / 'longitudinal-endpoint-preparation-2026-09-28-002'
    pm = json.loads(pin(previous / 'RUN_MANIFEST.json'))
    reuse = json.loads(pin(previous / 'coordinator_reuse_audit.json', pm['output_hashes']['coordinator_reuse_audit.json']))
    by_id = {r['candidate_digest']: r for r in reuse['records']}
    expected = [by_id[r['candidate_digest']]['sample_id'] for r in selected]
    if [s['sample_id'] for s in pool['scenes']] != expected or len(set(expected)) != 19:
        raise ValueError('sample binding drift')
    evidence = declaration()
    acceptance = accept_declaration(evidence)
    packet = make_packet(pool)
    data = (json.dumps(packet, ensure_ascii=False, indent=2) + '\n').encode()
    display = {**packet, 'packet_sha256': sha(data)}
    template = pin(TEMPLATE).decode()
    html = template.replace('__PACKET__', json.dumps(display, ensure_ascii=False).replace('<', '\\u003c'))
    proposal = {'status': 'PROPOSED_REQUIRES_ASSIGNMENT_AND_DISPATCH_APPROVAL', 'reviewer_id': 'Jonh',
        'review_kind': 'DEVELOPMENT_ACTION_ONLY', 'proposed_scene_count': 19, 'proposed_action_slots': 76,
        'candidate_indices': INDICES, 'sample_ids': expected, 'held_candidate_indices': [79, 81],
        'clip_groups': len({r['clip_id'] for r in selected}),
        'packet_sha256': sha(data), 'actual_assignment_count': None, 'dispatched': False,
        'order': 'ALL_ASSIGNED_ACTION_BEFORE_ANY_CNL_OR_SOURCE',
        'formal_reviewers_required': 2, 'available_reviewers': 1,
        'source_survey_repeated': False, 'gold_created': False}
    output.mkdir(parents=True, exist_ok=False, mode=0o700)
    def write(name, value):
        (output / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
    write('reviewer_self_report.json', evidence)
    write('declaration_acceptance.json', acceptance)
    write('assignment_proposal.json', proposal)
    (output / 'action_review_packet.json').write_bytes(data)
    (output / 'action_review_preview.html').write_text(html)
    result = {'project_id': 'guardsynth-coc', 'status': 'SPEED_ACTION_ASSIGNMENT_APPROVAL_PENDING',
        'reviewer_self_report_accepted': True, 'self_report_authenticated': False,
        'proposed_scene_count': 19, 'proposed_action_slots': 76, 'held_candidate_indices': [79, 81],
        'actual_assignment_count': None, 'reviewer_dispatched': 0, 'action_responses_received': 0,
        'independent_speed_action_gold': 0, 'new_training_scenes': 0,
        'formal_two_reviewer_gate_met': False, 'm16_gate': 'PARTIAL', 'm17_gate': 'PARTIAL'}
    write('RESULT.json', result)
    (output / 'REPORT_KO.md').write_text('# Jonh 비노출 진술 수용 및 ACTION 배정 준비\n\n'
        '2026-09-29 사용자 전달: 비노출 질문에 “아니요”, Jonh 본인의 답변 전달 여부 확인에 “네”. '
        '대화로 전달된 reviewer self-report로 수용했다. 실제 선언 시각은 미기록(null), '
        '신원/서명/웹폼/열람 로그 인증은 아니다. 동일 질문을 반복하지 않는다.\n\n'
        f'배정 제안: Jonh 한 명에게 개발 ACTION {len(INDICES)}장면/76행동 판단. 후보 {INDICES}. '
        '#79/#81은 보류하며 21개 속도 후보/전체 32개 분모를 유지한다. 기존 관찰 재설문이 아니다.\n\n'
        '답 단서 없는 과거 JPEG와 공통 질문/선택지의 독립 미리보기 화면을 준비했다. '
        '초기 답변 null, 부분 작성·브라우저 자동 저장·JSON 저장/복원 지원. 미리보기 저장은 임시 초안이며 '
        '실제 제출/배정/독립 gold로 접수하지 않는다. 포털 등록·검토자 전달은 하지 않았다.\n\n'
        '## 필요한 별도 결정\n\n'
        '위 19건을 Jonh에게 단일 검토자 개발 ACTION으로 실제 배정·배포할지 승인 요청한다. '
        '모든 배정 ACTION을 마친 뒤 CNL을 별도로 진행한다. 1인은 2인 formal gate를 대체하지 않는다. '
        '승인 전 실제 배정 수 null, 배포·답변·gold·학습 0. 기존 승인 두 사항과 immutable run은 보존했다.\n')
    write('RUN_MANIFEST.json', {'project_id': 'guardsynth-coc', 'experiment_id': output.parent.name,
        'run_id': output.name, 'created_at_utc': datetime.now(timezone.utc).isoformat(),
        'status': result['status'], 'input_hashes': inputs,
        'code_hashes': {str(Path(__file__).relative_to(ROOT)): sha(Path(__file__).read_bytes())},
        'output_hashes': {p.name: sha(p.read_bytes()) for p in sorted(output.iterdir())}, 'network_used': False})
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    args = parser.parse_args()
    if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*-[0-9]+', args.run_id):
        parser.error('unused numeric-suffix run ID required')
    print(json.dumps(execute(BASE / args.run_id), ensure_ascii=False, indent=2))
