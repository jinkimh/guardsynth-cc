"""Verify pinned AI frame observations and source-compatible endpoint triage; never create gold."""

import argparse
import base64
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

ROOT = next(p for p in Path(__file__).resolve().parents if (p / 'PROJECT_REGISTRY.json').is_file())
BASE = ROOT / 'artifacts/projects/guardsynth-coc/restricted/guardsynth-paper1-training-readiness-001'
SOURCE = BASE / 'm17-original-coc-context-audit-2026-09-28-002'
FRAMES = BASE / 'source-gap-ui-2026-09-09-002'
NOTES = Path(__file__).with_name('context_visual_observations_v0_1.json')
DESIGN = ROOT / 'projects/04-guardsynth-coc/docs/designs/PAPER1_ORIGINAL_ACTION_ENDPOINT_DESIGN_V01.md'
POLICY = ROOT / 'projects/04-guardsynth-coc/docs/decisions/PAPER1_ORIGINAL_CONTEXT_PRESERVATION_DECISION_V01.md'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def check_frames(scene, note, source):
    """All packet frames are causal/hash checked; only explicitly logged frames were visually inspected."""
    if scene['event_timestamp_us'] != source['event_timestamp_us'] or scene['clip_id'] != source['clip_id']:
        raise ValueError('scene identity mismatch')
    if scene['original_coc'] != source['original_coc']:
        raise ValueError('scene CoC mismatch')
    previous = None
    for frame in scene['frames']:
        timestamp = frame['timestamp_us']
        if type(timestamp) is not int or timestamp > source['event_timestamp_us']:
            raise ValueError('noncausal frame')
        if previous is not None and timestamp <= previous:
            raise ValueError('frame order mismatch')
        previous = timestamp
        prefix, encoded = frame['data_url'].split(',', 1)
        if prefix != 'data:image/jpeg;base64' or sha(base64.b64decode(encoded, validate=True)) != frame['sha256']:
            raise ValueError('frame hash mismatch')
    if [f['ordinal'] for f in note['inspected_frames']] != [0, 2, 4, 6]:
        raise ValueError('visual coverage mismatch')
    for ref in note['inspected_frames']:
        frame = scene['frames'][ref['ordinal']]
        if any(ref[k] != frame[k] for k in ('timestamp_us', 'sha256')):
            raise ValueError('inspected frame mismatch')
    if note['action_gold'] is not None or note['context_accepted'] is not False:
        raise ValueError('AI observation cannot promote gold/context')


def execute(output):
    if output.exists():
        raise FileExistsError(output)
    inputs = {}

    def pin(path, expected=None):
        data = path.read_bytes()
        if expected is not None and sha(data) != expected:
            raise ValueError('input hash mismatch: ' + str(path))
        inputs[str(path.relative_to(ROOT))] = sha(data)
        return data

    def read_run(run, name):
        manifest = json.loads(pin(run / 'RUN_MANIFEST.json'))
        return json.loads(pin(run / name, manifest['output_hashes'][name]))

    rows = read_run(SOURCE, 'original_coc_context_audit.json')['records']
    scenes = read_run(FRAMES, 'source_gap_packet.json')['scenes']
    notes = json.loads(pin(NOTES))
    pin(DESIGN)
    pin(POLICY)
    if notes['observer'] != 'AI_ASSISTANT' or notes['independent_human_review'] is not False or notes['original_coc_exposed'] is not True:
        raise ValueError('observation role mismatch')
    contexts = [r for r in rows if r['context_spans']]
    if len(rows) != 32 or len({r['candidate_digest'] for r in rows}) != 32 or len(contexts) != 10:
        raise ValueError('candidate denominator mismatch')
    if sorted(n['candidate_index'] for n in notes['records']) != sorted(r['candidate_index'] for r in contexts):
        raise ValueError('note coverage mismatch')
    records = []
    all_frames, inspected_hashes = [], []
    for row in contexts:
        matches = [s for s in scenes if s['candidate_digest'] == row['candidate_digest']]
        if len(matches) != 1 or sha(row['original_coc'].encode()) != row['original_coc_sha256']:
            raise ValueError('source identity mismatch')
        note = next(n for n in notes['records'] if n['candidate_index'] == row['candidate_index'])
        scene = matches[0]
        check_frames(scene, note, row)
        all_frames.extend(scene['frames'])
        inspected_hashes.extend(f['sha256'] for f in note['inspected_frames'])
        records.append({**row, 'visual_observation': note, 'frame_packet_count': len(scene['frames']),
                        'endpoint_status': 'COORDINATOR_DRAFT_NOT_FROZEN', 'independent_visual_verification': False})
    result = {
        'project_id': 'guardsynth-coc', 'status': 'AI_CONTEXT_FRAME_ENDPOINT_TRIAGE_COMPLETE_NOT_ACCEPTED',
        'original_candidate_denominator': len(rows), 'context_candidates_audited': len(records),
        'other_candidates_not_visually_audited': len(rows) - len(records),
        'audited_clip_groups': len({r['clip_id'] for r in records}),
        'frame_packet_entries_hash_time_checked': len(all_frames),
        'visual_frame_inspections': len(inspected_hashes), 'unique_visually_inspected_jpegs': len(set(inspected_hashes)),
        'context_status_counts': dict(Counter(r['visual_observation']['context_status'] for r in records)),
        'endpoint_axis_counts': dict(Counter(r['visual_observation']['endpoint_axis'] for r in records)),
        'potential_source_action_tension_candidates': [88],
        'same_clip_candidate_groups': [sorted(r['candidate_index'] for r in records if r['clip_id'] == clip)
                                       for clip, count in Counter(r['clip_id'] for r in records).items() if count > 1],
        'neutral_contexts_accepted': 0, 'independent_action_gold_created': 0, 'new_training_scenes': 0,
        'route_assigned': False, 'new_review_ready': False, 'repeat_source_survey_requested': False,
        'main_cohort_frozen': False, 'old_action_review_suspended': True,
        'next_step': 'COMPLETE_ORIGINAL_ACTION_FAMILY_COVERAGE_AND_REVIEW_ENDPOINT_DRAFT_BEFORE_DISPATCH',
    }
    report = ['# 원문 문맥·과거 프레임·행동 평가 점검', '',
              '연구 질문과 원문 CoC는 그대로 유지했습니다. 이 결과는 CoC에 노출된 AI의 예비 점검이며 독립 인간 정답이 아닙니다.', '',
              f'- 전체 후보 32건 중 문맥 후보 10건/9 clips를 대조했습니다. 나머지 22건은 이번 시각 점검 범위 밖입니다.',
              f'- 과거 프레임 메타데이터/JPEG hash 확인 {len(all_frames)}건. 실제 시각 확인은 장면별 0·2·4·6번, 총 {len(inspected_hashes)}회/{len(set(inspected_hashes))}개 고유 JPEG입니다.',
              '- 600px 폭의 4분할 브라우저 표시; #66/#79/#88 마지막 프레임은 1200px 폭으로 추가 확인. 연속 영상·속도·정확한 거리 검증은 아닙니다.',
              '- 원문 환경 설명과 양립 8건, 회전 문맥 미확정 #79, 행동 자체를 문맥으로 주면 답이 되는 #66. 수용/학습 적격 수가 아닙니다.',
              '- 원래 평가 축: 종방향 5건, 통로 내 측방 조향 4건, 차로 변경 1건. 모두 채택하거나 새 과제로 전환한 것이 아닙니다.',
              '- #86/#94는 동일 clip의 다른 시점입니다. 독립 표본이나 다른 split으로 계산하지 않습니다.',
              '- 새 정답·학습 적격·검토자 배포 0. 기존 #18 개발 export 및 이전 관찰은 변경하지 않았습니다.', '',
              '## 장면별 점검 — 담당자용, 독립 행동 검토자에게 전달 금지', '',
              '| 후보 | 실제 보이는 내용 — AI 예비 관찰 | 판단 한계 | 보존할 평가 행동 |', '|---|---|---|---|']
    for row in records:
        note = row['visual_observation']
        report.append('| #' + str(row['candidate_index']) + ' | ' + ' | '.join(
            note[k].replace('|', '/') for k in ('observation_ko', 'limitation_ko', 'endpoint_note_ko')) + ' |')
    report += ['', '## 중요한 불일치 후보: #88', '',
               '원문은 보행자 해소 뒤 강한 가속을 권합니다. 마지막 프레임에는 적색 신호, 횡단보도 위 보행자, 좌측 차량이 보입니다.',
               '신호 적용 방향·실제 경로가 미확정이므로 CoC 오류나 정답 행동을 확정하지 않습니다. 다만 원문 권고를 정상 진행 정답으로 복사해서는 안 됩니다.',
               '이 사례를 유리한 데이터만 남기기 위해 삭제하지 않습니다. 원문과 부분 관찰을 보존하고 제약의 적용 범위를 독립적으로 판단해야 합니다.', '',
               '## 다음 작업', '',
               '평가 질문 초안은 PAPER1_ORIGINAL_ACTION_ENDPOINT_DESIGN_V01.md에 있습니다. 아직 새 설문은 배포하지 않았습니다.',
               '남은 원문 행동군의 coverage를 점검한 후, 1~2개 행동군·동일 입력·답 유도 없는 후보 집합을 담당자가 확정해야 합니다.',
               '기존 30개 관찰을 전부 다시 요구하지 않습니다. 모호한 항목만 남기고, 행동 정답/CNL 검토는 기존 관찰과 별도 단계로 유지합니다.',
               'M16/M17 PARTIAL. 본 VLM 학습과 held-out 성능 평가는 아직 시작하지 않았습니다.']
    output.mkdir(parents=True)

    def write(name, value):
        (output / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')

    write('RESULT.json', result)
    write('context_frame_endpoint_audit.json', {'audience': notes['audience'], 'method': notes['method'],
          'original_coc_exposed': True, 'independent_human_review': False, 'records': records,
          'outside_visual_subset': [r['candidate_index'] for r in rows if not r['context_spans']]})
    (output / 'REPORT_KO.md').write_text('\n'.join(report) + '\n')
    write('RUN_MANIFEST.json', {
        'project_id': 'guardsynth-coc', 'experiment_id': output.parent.name, 'run_id': output.name,
        'created_at_utc': datetime.now(timezone.utc).isoformat(), 'status': result['status'], 'network_used': False,
        'input_hashes': inputs, 'code_hashes': {str(Path(__file__).relative_to(ROOT)): sha(Path(__file__).read_bytes())},
        'output_hashes': {p.name: sha(p.read_bytes()) for p in sorted(output.iterdir())},
    })
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, required=True)
    print(json.dumps(execute(parser.parse_args().output_dir), ensure_ascii=False, indent=2))
