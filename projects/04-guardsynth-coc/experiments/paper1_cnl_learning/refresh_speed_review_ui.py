"""Refresh only assigned ACTION UI, preserving packet identity and saved drafts."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import assign_speed_review as assignment

SOURCE = assignment.BASE / 'speed-action-assigned-2026-09-29-001'


def execute(output):
    if output.exists():
        raise FileExistsError(output)
    packet_path = SOURCE / 'action_review_packet.json'
    data = packet_path.read_bytes()
    manifest = json.loads((SOURCE / 'RUN_MANIFEST.json').read_text())
    digest = assignment.prep.sha(data)
    if digest != manifest['output_hashes']['action_review_packet.json']:
        raise ValueError('assigned packet drift')
    packet = json.loads(data)
    html = assignment.TEMPLATE.read_text().replace('__PACKET__', json.dumps(
        {**packet, 'packet_sha256': digest}, ensure_ascii=False).replace('<', '\\u003c'))
    output.mkdir(parents=True, exist_ok=False, mode=0o700)
    (output / 'assigned_speed_action_review.html').write_text(html)
    result = {'project_id': 'guardsynth-coc', 'status': 'UI_REFRESH_PREPARED',
              'assignment_id': packet['assignment_id'], 'packet_sha256': digest,
              'assigned_scenes': len(packet['scenes']), 'existing_draft_compatible': True,
              'question_choices_and_completion_criteria_changed': False,
              'new_assignments': 0, 'responses_added': 0, 'publication_verified': False}
    (output / 'RESULT.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    (output / 'REPORT_KO.md').write_text('# 장면별 저장·완료 버튼\n\n'
        '이 장면 임시 저장, 이 장면 완료 · 다음 버튼과 현재 장면 작성 상태를 추가했다. '
        '네 판단과 근거 누락 시 이동하지 않으며 저장 실패도 안내한다. '
        '기존 assignment_id/packet SHA/저장 키/JSON 형식/완료 집계 기준은 유지한다. '
        '기존 답변을 초기화하거나 재배정하지 않는다. 질문·선택지 변경 없음.\n\n'
        '이 실행은 UI 준비이며 실제 게시 및 브라우저 검증은 별도 확인한다. '
        '브라우저 저장은 서버 접수가 아니며 19장면 완료 후 최종 JSON을 전달해야 한다.\n')
    (output / 'RUN_MANIFEST.json').write_text(json.dumps({
        'project_id': 'guardsynth-coc', 'experiment_id': output.parent.name,
        'run_id': output.name, 'created_at_utc': datetime.now(timezone.utc).isoformat(),
        'input_hashes': {str(p.relative_to(assignment.prep.ROOT)): assignment.prep.sha(p.read_bytes())
                         for p in (packet_path, SOURCE / 'RUN_MANIFEST.json')},
        'code_hashes': {str(p.relative_to(assignment.prep.ROOT)): assignment.prep.sha(p.read_bytes())
                        for p in (Path(__file__), assignment.TEMPLATE)},
        'output_hashes': {p.name: assignment.prep.sha(p.read_bytes()) for p in output.iterdir()},
    }, indent=2) + '\n')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    args = parser.parse_args()
    if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*-[0-9]+', args.run_id):
        parser.error('unused numeric-suffix run ID required')
    print(json.dumps(execute(assignment.BASE / args.run_id), ensure_ascii=False, indent=2))
