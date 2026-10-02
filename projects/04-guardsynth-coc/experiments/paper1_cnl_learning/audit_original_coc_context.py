"""Trace exact original CoC context/action spans without assigning a route or an action label."""

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re

ROOT = next(p for p in Path(__file__).resolve().parents if (p / 'PROJECT_REGISTRY.json').is_file())
BASE = ROOT / 'artifacts/projects/guardsynth-coc/restricted/guardsynth-paper1-training-readiness-001'
PARENT = BASE / 'conditional-candidates-2026-09-08-002'
POLICY = ROOT / 'projects/04-guardsynth-coc/docs/decisions/PAPER1_ORIGINAL_CONTEXT_PRESERVATION_DECISION_V01.md'
CONTEXT_RULES = (
    ('TEMPORARY_LANE', r'the temporary lane delineated by traffic cones'),
    ('CONE_GUIDED_PATH', r'following the guidance of the traffic cones'),
    ('LEAD_VEHICLE_FOLLOWING', r'following the lead vehicle'),
    ('LEFT_LANE_CHANGE', r'lane change to the left'),
    ('TURN_DIRECTION_UNSPECIFIED', r'while turning'),
    ('STRAIGHT', r'proceed straight'),
    ('INTERSECTION_TRAVERSAL_UNSPECIFIED', r'proceed through the intersection'),
)
ACTION_RULES = (
    ('STOP', r'^Stop\b'), ('YIELD', r'^Yield\b'),
    ('DECELERATE', r'^(?:(?:Gentle|Strong) deceleration|Decelerate)\b'),
    ('SPEED_RECOVERY_OR_ACCELERATION', r'^(?:Resume speed|(?:Gentle|Strong) acceleration)\b'),
    ('LATERAL_STEERING', r'^(?:Steer (?:right|left)|Shift slightly left)\b'),
    ('LANE_CHANGE', r'^Lane change to the left\b'),
    ('SPEED_ADAPTATION', r'^Adapt speed\b'),
)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def spans(text, rules):
    return [{'kind': kind, 'text': m.group(), 'span': [m.start(), m.end()]}
            for kind, pattern in rules for m in re.finditer(pattern, text, re.I)]


def audit_text(text):
    contexts, actions = spans(text, CONTEXT_RULES), spans(text, ACTION_RULES)
    family = actions[0]['kind'] if len(actions) == 1 else 'UNCLASSIFIED_REQUIRES_REVIEW'
    return {
        'context_spans': contexts, 'recommended_action_spans': actions,
        'source_action_family': family,
        'classification': 'EXPLICIT_CONTEXT_FRAGMENT_REQUIRES_REVIEW' if contexts else
            ('LATERAL_ACTION_ONLY_NOT_ROUTE' if family == 'LATERAL_STEERING' else 'NO_EXPLICIT_PATH_IN_SCREEN'),
        'answer_bearing_remainder': {'text': text[actions[0]['span'][1]:],
                                    'span': [actions[0]['span'][1], len(text)]} if actions else None,
        'context_verified': False, 'neutral_prompt': None, 'action_gold': None,
        'route_assigned': False, 'new_review_ready': False, 'learning_export_allowed': False,
        'scope': 'LEXICAL_SOURCE_SCREEN_NOT_VISUAL_VALIDATION_OR_GENERAL_NLP_EXTRACTOR',
    }


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
    rows = load_run(PARENT, 'candidate_readiness.json')['records']
    bindings = {r['candidate_digest']: r for r in load_run(PARENT, 'event_source_bindings.json')['records']}
    old_audit = load_run(BASE / 'm17-action-task-audit-2026-09-28-001', 'RESULT.json')
    ui = load_run(BASE / 'm17-action-review-ui-2026-09-28-001', 'RESULT.json')
    pin(POLICY)
    records = []
    for row in rows:
        text = row['original_coc']
        binding = bindings[row['candidate_digest']]
        if sha(text.encode()) != row['coc_sha256'] or binding['coc']['text'] != text or binding['coc']['sha256'] != row['coc_sha256']:
            raise ValueError('original CoC drift')
        if binding['event_timestamp_us'] != row['event_timestamp_us']:
            raise ValueError('event mismatch')
        pin(ROOT / row['annotation_path'], row['annotation_sha256'])
        records.append({
            'candidate_digest': row['candidate_digest'], 'candidate_index': row['geometry_index'],
            'video_review_index': row['review_index'], 'clip_id': row['clip_id'],
            'event_timestamp_us': row['event_timestamp_us'], 'original_coc': text,
            'original_coc_sha256': row['coc_sha256'], **audit_text(text),
            'source_observed_actions_context_only': binding['active_ego_actions'],
            'source_action_annotations_are_route_log': False,
            'prior_pedestrian_clear_report': row['geometry_index'] in old_audit['reported_clear_candidates'],
        })
    if len(records) != 32 or len({r['candidate_digest'] for r in records}) != 32:
        raise ValueError('candidate denominator mismatch')
    contexts = [r for r in records if r['context_spans']]
    progress = [r for r in records if r['source_action_family'] == 'SPEED_RECOVERY_OR_ACCELERATION']
    result = {
        'project_id': 'guardsynth-coc', 'status': 'ORIGINAL_COC_STUDY_PRESERVED_CONTEXT_AUDIT_COMPLETE',
        'original_coc_verified': len(records), 'context_screen_counts': dict(Counter(r['classification'] for r in records)),
        'source_action_family_counts': dict(Counter(r['source_action_family'] for r in records)),
        'context_candidate_indices': [r['candidate_index'] for r in contexts],
        'source_progress_recommendation_indices': [r['candidate_index'] for r in progress],
        'progress_recommendation_and_prior_clear_overlap': [r['candidate_index'] for r in progress if r['prior_pedestrian_clear_report']],
        'neutral_contexts_accepted': 0, 'independent_action_gold_created': 0, 'new_training_scenes': 0,
        'arbitrary_maneuver_prototype': 'WITHDRAWN_AND_EXECUTION_BLOCKED',
        'original_observations_preserved': True, 'old_action_review_suspended': True,
        'repeat_source_survey_requested': False, 'new_review_ready': False,
        'next_step': 'CAUSAL_FRAME_CONTEXT_AND_ORIGINAL_ACTION_ENDPOINT_COMPATIBILITY_AUDIT',
    }
    output.mkdir(parents=True)
    def write_json(name, value):
        (output / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
    write_json('RESULT.json', result)
    write_json('original_coc_context_audit.json', {'audience': 'COORDINATOR_ONLY_NOT_ACTION_REVIEWER', 'records': records})
    write_json('context_followup_queue.json', {'records': [
        {'candidate_index': r['candidate_index'], 'candidate_digest': r['candidate_digest'],
         'source_spans': r['context_spans'], 'source_action_family': r['source_action_family'],
         'checks': ['MATCH_CAUSAL_FRAMES', 'DEFINE_ORIGINAL_COMPATIBLE_ENDPOINT', 'REMOVE_ANSWER_CUES_WITHOUT_CHANGING_TASK'],
         'reviewer_ready': False} for r in contexts]})
    report = ['# 원본 CoC 문맥 보존 감사', '',
              '연구 질문은 원본 CoC에 검증된 제약을 추가했을 때의 VLM 학습 효과입니다. 임의 경로 과제는 철회했습니다.', '',
              f'- 32건 원본 CoC hash·source 연결 일치. 문맥 구절 후보 {len(contexts)}건이며 시각 검증·중립 문맥 수용 0건.',
              f'- 문맥 분류: {result["context_screen_counts"]}.',
              f'- 원문 권고 행동 분류: {result["source_action_family_counts"]}. 행동 정답이 아닙니다.',
              f'- 속도 회복/가속 원문 {len(progress)}건 후보: {result["source_progress_recommendation_indices"]}. 기존 보행자 FALSE와 겹치는 후보: {result["progress_recommendation_and_prior_clear_overlap"]}. 정상 진행 정답은 0건입니다.',
              '- 후보 #27 CoC에는 우회전이 없고, 별도 사후 행동 주석에만 우회전이 있습니다. CoC의 경로로 자동 보완하지 않았습니다.',
              '- 감속과 정지는 같지 않고, 조향과 회전도 같지 않습니다. 모든 행동을 진입/보류로 바꾸는 질문은 재사용하지 않습니다.',
              '- 이전 관찰·영역·EBLC·CNL·#18 개발 export는 원래 범위로 보존. 본 학습/추가 행동 검토 없음.', '',
              '## 장면별 원문 감사 — 독립 행동 검토자에게 전달하지 않음', '',
              '| 후보 | 원본 CoC | 문맥 구절 후보 | 원문 행동 분류 |', '|---|---|---|---|']
    for r in records:
        clean = lambda s: s.replace('|', '/').replace('\n', ' ')
        report.append(f"| #{r['candidate_index']} | {clean(r['original_coc'])} | {clean('; '.join(s['text'] for s in r['context_spans']) or '경로 단서 미검출')} | {r['source_action_family']} |")
    report += ['', '## 다음 기계/담당자 작업', '',
               '문맥 구절 후보를 기존 과거 프레임과 대조하고, 원래 행동군에 맞는 평가 선택지를 정의합니다.',
               '예: 직진 문맥은 속도 판단의 공통 조건이 될 수 있으나 방향 선택 정답을 묻는 과제에는 답을 노출합니다.',
               '구절을 발견했다고 바로 검토자에게 제공하지 않습니다. 원문 권고·위험·해소 이유와 분리되는지 확인합니다.',
               '문맥을 확인하지 못한 사례는 보류하되 분모에 남깁니다. 임의 직진/우회전 지정이나 기존 정답 복사는 금지합니다.',
               'M16/M17 PARTIAL 유지. 같은 문맥·데이터·모델·예산의 L0–L3 비교라는 연구 기조는 변경하지 않습니다.']
    (output / 'REPORT_KO.md').write_text('\n'.join(report) + '\n')
    template = Path(__file__).with_name('action_review_suspended.html')
    suspended = template.read_text().replace('__DRAFT_KEY__', json.dumps('guardsynth-action-batch:' + ui['bundle_sha256'] + ':' + ui['reviewer_id']))
    suspended = suspended.replace('<h1>', '<p>원래 연구 기조를 유지합니다. 임의 경로 배정은 철회했으며 원본 CoC 문맥과 평가 질문을 점검 중입니다.</p><h1>', 1)
    (output / 'action_review_suspended.html').write_text(suspended)
    write_json('RUN_MANIFEST.json', {
        'project_id': 'guardsynth-coc', 'experiment_id': output.parent.name, 'run_id': output.name,
        'created_at_utc': datetime.now(timezone.utc).isoformat(), 'status': result['status'], 'network_used': False,
        'input_hashes': inputs, 'code_hashes': {str(p.relative_to(ROOT)): sha(p.read_bytes()) for p in (Path(__file__), template)},
        'output_hashes': {p.name: sha(p.read_bytes()) for p in sorted(output.iterdir())},
    })
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, required=True)
    print(json.dumps(execute(parser.parse_args().output_dir), ensure_ascii=False, indent=2))
