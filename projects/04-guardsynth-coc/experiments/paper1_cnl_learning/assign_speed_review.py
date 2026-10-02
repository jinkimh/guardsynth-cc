"""Record explicit assignment approval and build the isolated ACTION delivery asset."""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import prepare_speed_assignment as prep

BASE = prep.BASE
PRIOR = BASE / 'speed-action-assignment-preparation-2026-09-29-001'
TEMPLATE = Path(__file__).with_name('assigned_speed_action_review.html')
SUBMISSIONS = BASE / 'speed-action-submission-2026-09-29-001'


def execute(output):
    if output.exists():
        raise FileExistsError(output)
    inputs = {}
    def pin(path, expected=None):
        data = path.read_bytes()
        if expected and prep.sha(data) != expected:
            raise ValueError('pinned assignment input drift')
        inputs[str(path.relative_to(prep.ROOT))] = prep.sha(data)
        return data
    m = json.loads(pin(PRIOR / 'RUN_MANIFEST.json'))
    def load(name):
        return json.loads(pin(PRIOR / name, m['output_hashes'][name]))
    proposal = load('assignment_proposal.json')
    evidence = load('reviewer_self_report.json')
    prep.accept_declaration(evidence)
    packet = load('action_review_packet.json')
    if proposal['candidate_indices'] != prep.INDICES or proposal['held_candidate_indices'] != [79, 81]:
        raise ValueError('assignment scope drift')
    if [s['sample_id'] for s in packet['scenes']] != proposal['sample_ids']:
        raise ValueError('assignment sample drift')
    packet = prep.make_packet(packet)
    packet.update(status='ASSIGNED_DEVELOPMENT_ACTION', reviewer_id='Jonh', assignment_id=output.name)
    data = (json.dumps(packet, ensure_ascii=False, indent=2) + '\n').encode()
    display = {**packet, 'packet_sha256': prep.sha(data)}
    html = pin(TEMPLATE).decode().replace('__PACKET__', json.dumps(display, ensure_ascii=False).replace('<', '\\u003c'))
    approval = {'recorded_date': '2026-09-29', 'approved_at': None,
        'question_verbatim': '이 19장면을 Jonh에게 개발용 행동 검토로 배정하고, 화면 점검 후 게시할까요? 기존 관찰 설문을 반복하는 것이 아니라, 각 행동의 적절성을 판단하는 검토입니다.',
        'answer_verbatim': '네..', 'source': 'USER_RELAY_OF_EXPLICIT_ASSIGNMENT_AND_PUBLICATION_APPROVAL',
        'scope': 'EXACT_19_SCENES_JONH_DEVELOPMENT_ACTION_BROWSER_CHECK_THEN_PORT8766_PUBLICATION',
        'responses_gold_training_or_main_split_approved': False}
    assignment = {**proposal, 'status': 'ASSIGNED_PUBLICATION_PENDING_BROWSER_CHECK',
        'assignment_id': output.name, 'actual_assignment_count': 19,
        'packet_sha256': prep.sha(data), 'assignment_approved': True, 'publication_approved': True,
        'dispatched': False, 'external_message_sent': False,
        'submission_directory': str(SUBMISSIONS.relative_to(prep.ROOT))}
    output.mkdir(parents=True, exist_ok=False, mode=0o700)
    def write(name, value):
        (output / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
    write('approval_record.json', approval)
    write('assignment_record.json', assignment)
    (output / 'action_review_packet.json').write_bytes(data)
    (output / 'assigned_speed_action_review.html').write_text(html)
    result = {'project_id': 'guardsynth-coc', 'status': assignment['status'], 'reviewer_id': 'Jonh',
        'actual_assignment_count': 19, 'action_slots': 76, 'held_candidates': [79, 81],
        'publication_pending_browser_check': True, 'responses_received': 0,
        'independent_action_gold_added': 0, 'training_scenes_added': 0,
        'm16_gate': 'PARTIAL', 'm17_gate': 'PARTIAL', 'formal_two_reviewer_gate_met': False}
    write('RESULT.json', result)
    (output / 'REPORT_KO.md').write_text('# Jonh 19장면 개발 ACTION 배정\n\n'
        '사용자의 “네..”를 정확한 19장면/76판단 배정 및 브라우저 점검 후 port8766 게시 승인으로 기록했다. '
        '승인의 정확한 시각은 미기록이다. 이전 비노출 self-report와 두 개발 기준을 재사용했다.\n\n'
        f'배정 후보: {prep.INDICES}. #79/#81 보류. 모든 배정 ACTION 뒤 CNL, 1인 개발 검토와 2인 formal gate 구분.\n\n'
        '이 run은 배정 완료·게시 전 패키지다. 별도 브라우저 검사/게시 receipt에서 실제 HTTP 게시를 기록한다. '
        '초기 응답 0, gold/학습/본 split 변경 없음. 최종 JSON 다운로드는 서버 접수가 아니다.\n\n'
        f'제출 폴더: `{SUBMISSIONS.relative_to(prep.ROOT)}`. 테스트 다운로드는 이 폴더에 넣지 않는다.\n')
    write('RUN_MANIFEST.json', {'project_id': 'guardsynth-coc', 'experiment_id': output.parent.name,
        'run_id': output.name, 'created_at_utc': datetime.now(timezone.utc).isoformat(), 'status': result['status'],
        'input_hashes': inputs, 'code_hashes': {str(p.relative_to(prep.ROOT)): prep.sha(p.read_bytes()) for p in (Path(__file__), Path(prep.__file__))},
        'output_hashes': {p.name: prep.sha(p.read_bytes()) for p in output.iterdir()}, 'network_used': False})
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    args = parser.parse_args()
    if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*-[0-9]+', args.run_id):
        parser.error('unused numeric-suffix run ID required')
    print(json.dumps(execute(BASE / args.run_id), ensure_ascii=False, indent=2))
