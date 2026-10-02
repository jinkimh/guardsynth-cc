"""Seal actual browser-check and local-publication evidence, without test responses."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import prepare_speed_assignment as prep

ASSIGNMENT = prep.BASE / 'speed-action-assigned-2026-09-29-001'
PORTAL = prep.ROOT / 'artifacts/projects/guardsynth-coc/restricted/guardsynth-project-portal-001/portal-2026-09-29-001'
SUBMISSIONS = prep.BASE / 'speed-action-submission-2026-09-29-001'
URL = 'http://127.0.0.1:8766/reviews/paper1_speed_action_jonh.html'


def execute(output, preflight, http_checks):
    if output.exists():
        raise FileExistsError(output)
    checks = [json.loads((d / 'browser_checks.json').read_text()) for d in (preflight, http_checks)]
    if any(c['status'] != 'PASS' or c['real_responses_received'] != 0 or not c['test_only'] for c in checks):
        raise ValueError('browser evidence failed or not test-only')
    if checks[1]['url'] != URL or any(c['fresh_context_count'] != '0/19' for c in checks):
        raise ValueError('published URL or clean-context evidence mismatch')
    assigned = ASSIGNMENT / 'assigned_speed_action_review.html'
    served = PORTAL / 'reviews/paper1_speed_action_jonh.html'
    if assigned.read_bytes() != served.read_bytes():
        raise ValueError('published HTML differs from browser-tested assignment')
    if sorted(p.name for p in SUBMISSIONS.iterdir()) != ['README.md']:
        raise ValueError('submission directory requires actual receipt reconciliation')
    data = json.loads((PORTAL / 'PORTAL_DATA.json').read_text())
    project = next(p for p in data['research_projects'] if p['id'] == 'guardsynth-coc')
    if not any(p['href'] == 'reviews/paper1_speed_action_jonh.html' for p in project['review_pages']):
        raise ValueError('coordinator registration missing')
    output.mkdir(parents=True, exist_ok=False, mode=0o700)
    def write(name, value):
        (output / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
    for label, directory in (('prepublication', preflight), ('http', http_checks)):
        for name in ('browser_checks.json', 'initial.png', 'zoom.png'):
            shutil.copyfile(directory / name, output / (label + '_' + name))
    result = {'project_id': 'guardsynth-coc', 'status': 'ASSIGNED_AND_PUBLISHED_ACTION_RESPONSES_PENDING',
        'reviewer_id': 'Jonh', 'assigned_scenes': 19, 'action_slots': 76, 'held_candidates': [79, 81],
        'reviewer_url': URL, 'coordinator_url': 'http://127.0.0.1:8766/reviews.html',
        'publication_verified': True, 'browser_workflows_passed': 2, 'initial_count': '0/19',
        'external_messages_sent': 0, 'responses_received': 0, 'gold_added': 0, 'training_started': False,
        'test_responses_in_operational_submission_folder': 0,
        'submission_directory': str(SUBMISSIONS.relative_to(prep.ROOT)),
        'formal_two_reviewer_gate_met': False, 'm16_gate': 'PARTIAL', 'm17_gate': 'PARTIAL'}
    write('RESULT.json', result)
    (output / 'REPORT_KO.md').write_text('# Jonh ACTION 게시 및 실제 브라우저 검사\n\n'
        f'검토자 전용 URL: {URL}\n\n담당자 목록: http://127.0.0.1:8766/reviews.html\n\n'
        '정확한 19장면/76판단을 배정하고 실제 Chromium 점검 뒤 기존 port8766 포털에 게시했다. '
        '다른 세션/포트는 변경하지 않았다. 기존 중단 URL 및 immutable run은 보존했다.\n\n'
        '파일 화면 및 실제 HTTP 화면에서 초기0/19, 이미지 확대/복귀 시 응답 유지, 장면 이동/reload, '
        '부분 저장/복원, 잘못된 파일 거부, 미응답/근거 누락 안내, 최종 JSON19행 저장과 새 context0/19를 검사했다. '
        '검토자 페이지에는 CoC/기존답변/도형/판정/CNL 및 해당 자료 링크가 없다. 스크린샷도 확인했다.\n\n'
        '## Jonh 안내\n\n과거 프레임을 확인하고 네 행동을 각각 판단한 뒤 근거를 적는다. 여러 적절 행동/판단 불가 허용. '
        '부분 초안을 저장하거나 복원할 수 있다. 19/19 완료 후 최종 JSON 저장으로 '
        '`jonh_speed_action_submission.json`을 내려받아 담당자에게 전달한다. 저장은 서버 업로드가 아니다.\n\n'
        f'실제 제출 폴더: `{SUBMISSIONS.relative_to(prep.ROOT)}`. 현재 README만 있고 응답0. '
        '테스트 데이터는 일회용 browser context와 /tmp 다운로드에만 존재하며 실제 검토/응답 수가 아니다.\n\n'
        '#79/#81 보류, 모든 ACTION 뒤 CNL, 1인 개발 검토/2인 formal gate 구분 유지. '
        'Gold·학습·main split·안전성 승인 없음. 외부 이메일/메신저 발송 없음. M16/M17 PARTIAL.\n')
    paths = [ASSIGNMENT / 'RUN_MANIFEST.json', ASSIGNMENT / 'approval_record.json', ASSIGNMENT / 'assignment_record.json',
             assigned, served, PORTAL / 'RUN_MANIFEST.json', SUBMISSIONS / 'README.md']
    write('RUN_MANIFEST.json', {'project_id': 'guardsynth-coc', 'experiment_id': output.parent.name,
        'run_id': output.name, 'created_at_utc': datetime.now(timezone.utc).isoformat(), 'status': result['status'],
        'input_hashes': {str(p.relative_to(prep.ROOT)): prep.sha(p.read_bytes()) for p in paths},
        'code_hashes': {str(Path(__file__).relative_to(prep.ROOT)): prep.sha(Path(__file__).read_bytes()),
                        'projects/04-guardsynth-coc/tests/integration/test_speed_review_browser.js': prep.sha((prep.ROOT / 'projects/04-guardsynth-coc/tests/integration/test_speed_review_browser.js').read_bytes())},
        'output_hashes': {p.name: prep.sha(p.read_bytes()) for p in output.iterdir()},
        'network_scope': 'LOCAL_HTTP_PORT8766_ONLY'})
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--preflight', type=Path, required=True)
    parser.add_argument('--http-checks', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(execute(prep.BASE / 'speed-action-publication-2026-09-29-001', args.preflight, args.http_checks), ensure_ascii=False, indent=2))
