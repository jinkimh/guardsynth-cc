"""Reuse observations and prepare blinded speed-action inputs without dispatch or gold."""

import argparse
import base64
from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

ROOT = next(p for p in Path(__file__).resolve().parents if (p / 'PROJECT_REGISTRY.json').is_file())
BASE = ROOT / 'artifacts/projects/guardsynth-coc/restricted/guardsynth-paper1-training-readiness-001'
COVERAGE = BASE / 'remaining-action-coverage-2026-09-28-001'
INTAKE = BASE / 'source-observation-intake-2026-09-28-001'
PACKET = BASE / 'source-gap-ui-2026-09-09-002'
DESIGN = ROOT / 'projects/04-guardsynth-coc/docs/designs/PAPER1_LONGITUDINAL_ENDPOINT_DESIGN_V01.md'
QUESTION = ('마지막 시점까지의 영상만 보고, 에고 차량이 지금 시작할 속도 조절로 아래 행동이 각각 '
            '적절한지 판단해 주세요. 여러 행동이 가능할 수 있습니다. 정보가 부족한 행동은 판단 불가로 '
            '남겨 주세요. 근거는 영상에서 보이는 내용으로 적어 주세요.')
ACTIONS = {
    'MAINTAIN_SPEED': '현재 이동 속도 유지: 움직이고 있을 때 속도를 유지하며, 정지 상태 유지는 아닙니다.',
    'DECELERATE': '감속: 우선 속도를 낮춥니다. 완전 정지를 목표로 결정한 행동과 구분합니다.',
    'STOP_OR_WAIT': '정지 또는 정지 유지: 이동 중이면 정지를 목표로 감속을 시작하고, 정지 중이면 계속 대기합니다.',
    'START_OR_ACCELERATE': '출발 또는 속도 높이기: 정지 중이면 출발하고, 이동 중이면 속도를 높입니다.',
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def reuse_observation(observation):
    answer = deepcopy(observation['raw_answer'])
    choices = ('target_status', 'zone_status', 'ped_truth', 'road_context', 'road_truth',
               'control_context', 'control_truth')
    return {
        'raw_answer': answer,
        'reported_unknown_fields': sorted(k for k in choices if answer.get(k) == 'UNKNOWN'),
        'legacy_not_applicable_fields': sorted(k for k in choices if answer.get(k) == 'NOT_APPLICABLE'),
        'entry_clearance_implies_speed_release': False,
        'speed_action_gold': None, 'repeat_source_survey_requested': False,
    }


def blind_input(row, scene, sample_id):
    if any(row[k] != scene[k] for k in ('candidate_digest', 'clip_id', 'event_timestamp_us')):
        raise ValueError('scene identity mismatch')
    frames = scene['frames']
    if (not frames or any(type(f['timestamp_us']) is not int or f['timestamp_us'] > row['event_timestamp_us'] for f in frames)
            or any(a['timestamp_us'] >= b['timestamp_us'] for a, b in zip(frames, frames[1:]))):
        raise ValueError('noncausal or unordered frame input')
    # References only: not a deployed questionnaire or a copy of the source answers/overlays.
    return {'sample_id': sample_id, 'event_timestamp_us': row['event_timestamp_us'], 'frames': [
        {k: frame[k] for k in ('frame_index', 'timestamp_us', 'sha256')} for frame in frames]}


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

    def load_run(run, name):
        manifest = json.loads(pin(run / 'RUN_MANIFEST.json'))
        return json.loads(pin(run / name, manifest['output_hashes'][name]))

    coverage = load_run(COVERAGE, 'remaining_action_coverage.json')
    source_result = load_run(COVERAGE, 'RESULT.json')
    intake = load_run(INTAKE, 'observation_interpretations.json')['records']
    submission = load_run(INTAKE, 'review_submission.json')
    scenes = load_run(PACKET, 'source_gap_packet.json')['scenes']
    load_run(BASE / 'm17-machine-preflight-2026-09-28-002', 'split_exposure_ledger.json')
    pin(DESIGN)
    rows = coverage['coverage_ledger']
    selected = [r for r in rows if r['endpoint_axis'] == 'LONGITUDINAL']
    if (len(rows) != 32 or len({r['candidate_digest'] for r in rows}) != 32 or len(selected) != 21
            or [r['candidate_index'] for r in selected] != source_result['proposed_candidate_indices']):
        raise ValueError('coverage denominator mismatch')
    obs_by_id = {r['candidate_digest']: r for r in intake}
    raw_by_id = {r['candidate_digest']: r for r in submission['records']}
    scene_by_id = {s['candidate_digest']: s for s in scenes}
    if len(obs_by_id) != len(intake) or len(scene_by_id) != len(scenes) or len(raw_by_id) != len(submission['records']):
        raise ValueError('duplicate source identity')
    audits, blind, unfilled = [], [], []
    frame_count = 0
    for i, row in enumerate(selected, 1):
        key = row['candidate_digest']
        observation, scene = obs_by_id[key], scene_by_id[key]
        answer = observation['raw_answer']
        if (answer != raw_by_id[key] or answer['candidate_digest'] != key
                or answer['event_timestamp_us'] != row['event_timestamp_us']
                or observation['event_timestamp_us'] != row['event_timestamp_us']
                or observation['original_coc'] != row['original_coc']
                or scene['original_coc'] != row['original_coc']
                or sha(row['original_coc'].encode()) != row['original_coc_sha256']):
            raise ValueError('observation/source identity mismatch')
        if len(scene['frames']) != 7:
            raise ValueError('source frame coverage mismatch')
        for frame in scene['frames']:
            prefix, encoded = frame['data_url'].split(',', 1)
            if prefix != 'data:image/jpeg;base64' or sha(base64.b64decode(encoded, validate=True)) != frame['sha256']:
                raise ValueError('frame JPEG hash mismatch')
            frame_count += 1
        sample = f'speed-dev-{i:03d}'
        blind.append(blind_input(row, scene, sample))
        reuse = reuse_observation(observation)
        audits.append({
            **row, 'sample_id': sample, 'reuse': reuse,
            'field_interpretations': deepcopy(observation['field_interpretations']),
            'user_clarification': deepcopy(observation['user_clarification']),
            'scope_reminders': {
                'unknown_report_present': bool(reuse['reported_unknown_fields']),
                'legacy_not_applicable_present': bool(reuse['legacy_not_applicable_fields']),
                'reported_control_false_not_speed_release': answer['control_truth'] == 'FALSE',
                'original_source_claim_check': row['candidate_index'] in (59, 68, 88),
                'route_sensitive_original_context': row['candidate_index'] in (79, 81),
            },
            'current_motion_state': None, 'new_endpoint_action_reference': None,
            'independent_violation_reference': None, 'independent_progress_reference': None,
            'old_entry_contract_covers_speed_actions': False, 'training_allowed': False,
            'test_allowed': False, 'repeat_source_survey_requested': False,
        })
        unfilled.append({'sample_id': sample, 'reviewer_id': None, 'reviewed_at': None,
                         'action_assessments': {action: None for action in ACTIONS}, 'reason': None})
    flag_counts = dict(Counter(k for row in audits for k, value in row['scope_reminders'].items() if value))
    result = {
        'project_id': 'guardsynth-coc', 'status': 'SPEED_ENDPOINT_REUSE_PREPARATION_NOT_DISPATCHED',
        'candidate_denominator': len(rows), 'speed_candidates': len(selected),
        'speed_clip_groups': len({r['clip_id'] for r in selected}),
        'source_observations_reused': len(audits), 'causal_jpegs_verified': frame_count,
        'scope_reminder_scene_counts_overlapping': flag_counts,
        'new_endpoint_gold_missing': len(unfilled), 'independent_speed_action_gold': 0,
        'draft_action_slots': len(unfilled) * len(ACTIONS), 'reviewer_dispatched': 0,
        'human_assignment_count': None, 'repeat_source_survey_requested': False,
        'new_training_scenes': 0, 'main_endpoint_frozen': False,
        'scope_preparation_authorized': True, 'new_review_ready': False,
        'old_action_review_suspended': True, 'original_observations_preserved': True,
        'next_step': 'SPEED_ACTION_CLAUSE_BINDING_AND_ENDPOINT_INTERPRETABILITY_PREFLIGHT',
    }
    packet = {
        'version': 'paper1-speed-endpoint-draft-v0.1', 'status': 'NOT_DISPATCHED_NOT_FROZEN',
        'question_ko': QUESTION, 'actions': ACTIONS,
        'assessment_choices': {'APPROPRIATE': '적절', 'INAPPROPRIATE': '부적절', 'UNDETERMINED': '판단 불가'},
        'instructions_ko': '여러 행동이 적절할 수 있습니다. 현재 이동/정지 여부 등 필요한 정보가 없으면 판단 불가로 남깁니다. 미래를 추측하지 않습니다.',
        'time_scope': 'FIRST_SPEED_DECISION_AT_LAST_OBSERVED_TIME_NOT_FIXED_DURATION_ROLLOUT',
        'scenes': blind,
    }
    output.mkdir(parents=True)

    def write(name, value):
        (output / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')

    write('RESULT.json', result)
    write('coordinator_reuse_audit.json', {'audience': 'COORDINATOR_ONLY_NOT_ACTION_REVIEWER',
          'records': audits, 'outside_speed_subset': [r['candidate_index'] for r in rows if r not in selected]})
    write('action_input_draft.json', packet)
    write('unfilled_action_records.json', {'status': 'TEMPLATE_NOT_RESPONSES', 'records': unfilled})
    lines = ['# 속도 행동 평가 준비 및 기존 관찰 재사용', '',
             '- 기존 관찰 21/21건을 원답 그대로 연결했습니다. 전체 32후보 분모·노출 이력은 유지합니다.',
             '- 19 clips의 과거 JPEG 147개를 해시/시점 확인했습니다. 새 시각 판정이나 독립 행동 정답은 만들지 않았습니다.',
             '- 질문과 네 행동 선택지, 판단 불가·복수 적절 행동을 포함하는 개발 초안을 준비했습니다. 본 endpoint 동결 아님.',
             '- 독립 검토용 초안은 프레임 참조와 공통 질문만 사용합니다. CoC·관찰 답변·점·도형·기계 판정은 제외했습니다.',
             '- 원본 이미지 파일은 복사하지 않았습니다. 이 JSON은 아직 검토 화면이나 배포 패킷이 아닙니다.', '',
             '## 무엇을 다시 하지 않아도 되는가', '',
             '대상·영역을 다시 그리거나 기존 관찰 설문을 전부 반복하지 않습니다. NOT_APPLICABLE과 UNKNOWN은 그대로 보존합니다.',
             '#86/#94의 진입 차단 FALSE와 천천히 메모는 함께 보존하며 속도 제한 해제로 바꾸지 않습니다.', '',
             '## 기계가 정리한 사항 — 중복 포함, 사람 질문 수 아님', '',
             f'{flag_counts}', '',
             '| 후보 | 기존 UNKNOWN 항목 | 기존 해당 없음 항목 수 | 기존 진입 차단 FALSE |', '|---|---|---:|---|']
    for row in audits:
        reuse = row['reuse']
        lines.append(f"| #{row['candidate_index']} | {', '.join(reuse['reported_unknown_fields']) or '없음'} | {len(reuse['legacy_not_applicable_fields'])} | {row['scope_reminders']['reported_control_false_not_speed_release']} |")
    lines += ['', '## 사람 검토의 실제 공백', '',
              '새 속도 행동 정답은 0/21입니다. 21건 모두 최종 수용된다면 최대 21장면의 독립 행동 판단이 필요할 수 있습니다.',
              '지금 21건 검토를 요청하는 것은 아닙니다. 초안 84개 행동 슬롯은 빈 자리이며 답변/배정/새 정답이 아닙니다.',
              '기존 #18 진입/보류 정답을 속도 정답으로 변환하지 않았습니다. 실제 배정 장면 수는 아직 미확정입니다.', '',
              '## 다음 기계 작업', '',
              '기존 clause와 네 속도 행동의 연결 및 질문 해석 가능성을 점검합니다. 과거 ENTER_ZONE 검증으로 완료 처리하지 않습니다.',
              '적절성 응답만으로 위반률/정상 진행 정답을 만들지 않습니다. 독립 위반·진행 근거가 있어야 효과 평가가 가능합니다.',
              '기존 ACTION 화면 중단 유지. 새 설문 배포 0, 새 학습 적격 0, M16/M17 PARTIAL.']
    (output / 'REPORT_KO.md').write_text('\n'.join(lines) + '\n')
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
