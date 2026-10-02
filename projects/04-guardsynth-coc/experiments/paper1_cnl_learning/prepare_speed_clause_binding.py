"""Bind source claims to proposed speed clauses; never dispatch or produce action gold."""

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
from itertools import product
import json
from pathlib import Path
import re

ROOT = next(p for p in Path(__file__).resolve().parents if (p / 'PROJECT_REGISTRY.json').is_file())
BASE = ROOT / 'artifacts/projects/guardsynth-coc/restricted/guardsynth-paper1-training-readiness-001'
PREPARATION = BASE / 'longitudinal-endpoint-preparation-2026-09-28-002'
PREFLIGHT = BASE / 'm17-machine-preflight-2026-09-28-002'
DESIGN = ROOT / 'projects/04-guardsynth-coc/docs/designs/PAPER1_SPEED_CLAUSE_BINDING_DESIGN_V01.md'
ACTIONS = ('MAINTAIN_SPEED', 'DECELERATE', 'STOP_OR_WAIT', 'START_OR_ACCELERATE')
KINDS = ('SPEED_REDUCTION_REQUIRED', 'STOP_REQUIRED')
MOTIONS = ('MOVING', 'STATIONARY', 'UNKNOWN')
TRUTHS = ('TRUE', 'FALSE', 'UNKNOWN', 'CONFLICT')
UNRESOLVED = 'UNRESOLVED'
BLOCKED = 'EXCLUDED_BY_PROPOSED_CLAUSE'
NOT_EXCLUDED = 'NOT_EXCLUDED_BY_THIS_CLAUSE_NOT_PERMISSION'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def probe(kind, motion, applicability, evidence_valid):
    """Synthetic single-clause proposal, not a scene policy or appropriateness oracle."""
    if (kind not in KINDS or motion not in MOTIONS or applicability not in TRUTHS
            or type(evidence_valid) is not bool):
        raise ValueError('unsupported speed interface input')
    result = dict.fromkeys(ACTIONS, UNRESOLVED)
    if motion == 'UNKNOWN' or not evidence_valid or applicability in ('UNKNOWN', 'CONFLICT'):
        return result
    if kind == 'SPEED_REDUCTION_REQUIRED' and motion == 'STATIONARY':
        return result
    excluded = {'MAINTAIN_SPEED', 'START_OR_ACCELERATE'}
    if kind == 'STOP_REQUIRED':
        excluded.add('DECELERATE')
    for action in ACTIONS:
        if motion == 'STATIONARY' and action in ('MAINTAIN_SPEED', 'DECELERATE'):
            continue
        result[action] = BLOCKED if applicability == 'TRUE' and action in excluded else NOT_EXCLUDED
    return result


def source_claim(row):
    text = row['original_coc']
    if sha(text.encode()) != row['original_coc_sha256']:
        raise ValueError('original CoC hash mismatch')
    match = re.match(r'(?:Gentle |Strong )?(?:deceleration|acceleration)|Decelerate|Stop|Resume speed|Adapt speed', text)
    if not match:
        raise ValueError('unsupported source recommendation')
    phrase = match.group()
    if 'decelerat' in phrase.lower():
        action, kind = 'DECELERATE', 'SPEED_REDUCTION_REQUIRED'
    elif phrase == 'Stop':
        action, kind = 'STOP_OR_WAIT', 'STOP_REQUIRED'
    elif 'acceleration' in phrase:
        action, kind = 'START_OR_ACCELERATE', None
    else:
        action, kind = None, None
    return {'text': phrase, 'start': match.start(), 'end': match.end(),
            'source_recommendation_action': action, 'proposed_clause_kind': kind,
            'authority': 'SOURCE_CLAIM_NOT_NORMATIVE_OR_GOLD',
            'single_action_mapping': 'UNRESOLVED' if action is None else 'LEXICAL_SOURCE_ONLY',
            'magnitude_evaluated': False}


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

    def load(run, name):
        manifest = json.loads(pin(run / 'RUN_MANIFEST.json'))
        return json.loads(pin(run / name, manifest['output_hashes'][name]))

    prior = load(PREPARATION, 'coordinator_reuse_audit.json')
    previous_result = load(PREPARATION, 'RESULT.json')
    # Keep these references pinned, without modifying or redistributing reviewer material.
    load(PREPARATION, 'action_input_draft.json')
    load(PREPARATION, 'unfilled_action_records.json')
    old = load(PREFLIGHT, 'grounding_scope_audit.json')['records']
    exposure = load(PREFLIGHT, 'split_exposure_ledger.json')
    pin(DESIGN)
    by_id = {r['candidate_digest']: r for r in old}
    rows = prior['records']
    if (len(rows) != 21 or len({r['candidate_digest'] for r in rows}) != 21
            or len(by_id) != len(old) or len(prior['outside_speed_subset']) + len(rows) != 32
            or previous_result['candidate_denominator'] != 32):
        raise ValueError('candidate denominator mismatch')
    records = []
    for row in rows:
        historic = by_id[row['candidate_digest']]
        if any(row[k] != historic[k] for k in ('clip_id', 'event_timestamp_us')):
            raise ValueError('source identity mismatch')
        if row['reuse']['raw_answer'] != historic['raw_answer']:
            raise ValueError('source observation changed')
        contracts = []
        if 'conditional_artifact_directory' in historic:
            name = historic['conditional_artifact_directory'] + '/action_contract.json'
            contract = load(PREFLIGHT, name)
            if contract['policy'] != 'CLEAR_REQUIRED_FOR_ENTRY':
                raise ValueError('unexpected legacy policy')
            contracts.append({'path': str((PREFLIGHT / name).relative_to(ROOT)),
                              'sha256': inputs[str((PREFLIGHT / name).relative_to(ROOT))],
                              'contract_id': contract['contract_id'], 'obligations': contract['obligations'],
                              'speed_action_entailment': 'UNSUPPORTED_NO_AUTOMATIC_TRANSLATION'})
        claim = source_claim(row)
        records.append({
            'candidate_index': row['candidate_index'], 'candidate_digest': row['candidate_digest'],
            'clip_id': row['clip_id'], 'event_timestamp_us': row['event_timestamp_us'],
            'original_coc': row['original_coc'], 'original_coc_sha256': row['original_coc_sha256'],
            'source_claim': claim, 'legacy_contracts': contracts,
            'reused_record_ref': str((PREPARATION / 'coordinator_reuse_audit.json').relative_to(ROOT))
                                 + '#candidate_digest=' + row['candidate_digest'],
            'scope_reminders': row['scope_reminders'], 'current_motion_state': 'UNKNOWN',
            'speed_clause_applicability': 'UNKNOWN', 'speed_evidence_valid': False,
            'proposal_status': 'PROPOSED_NOT_ACCEPTED',
            'scene_clause_verdicts': dict.fromkeys(ACTIONS, UNRESOLVED),
            'action_gold': None, 'independent_violation_reference': None, 'independent_progress_reference': None,
            'training_allowed': False, 'reviewer_dispatch_allowed': False,
        })
    cases = [{'clause_kind': k, 'motion_state': m, 'applicability': t, 'evidence_valid': v,
              'verdicts': probe(k, m, t, v)} for k, m, t, v in product(KINDS, MOTIONS, TRUTHS, (False, True))]
    result = {
        'project_id': 'guardsynth-coc', 'status': 'SPEED_CLAUSE_PROPOSAL_PREPARED_HUMAN_DECISION_REQUIRED',
        'candidate_denominator': 32, 'speed_candidates': len(records),
        'speed_clip_groups': len({r['clip_id'] for r in records}),
        'source_observations_reused': len(records),
        'legacy_contract_links': sum(len(r['legacy_contracts']) for r in records),
        'proposed_clause_counts': dict(Counter(r['source_claim']['proposed_clause_kind'] or 'NO_CLAUSE_PROPOSED' for r in records)),
        'single_action_mapping_unresolved': [r['candidate_index'] for r in records if r['source_claim']['source_recommendation_action'] is None],
        'synthetic_interface_cases': len(cases), 'synthetic_action_verdicts': len(cases) * len(ACTIONS),
        'speed_smt_queries': 0, 'accepted_speed_clauses': 0,
        'independent_speed_action_gold': 0, 'reviewer_dispatched': 0, 'human_assignment_count': None,
        'new_training_scenes': 0, 'main_endpoint_frozen': False, 'main_split_frozen': False,
        'violation_metric': 'NOT_EVALUATED', 'nominal_progress_metric': 'NOT_EVALUATED',
        'old_action_review_suspended': True, 'repeat_source_survey_requested': False,
        'excluded_test_clips': len(exposure['excluded_test_clip_ids']),
        'm16_gate': 'PARTIAL', 'm17_gate': 'PARTIAL',
        'next_step': 'COORDINATOR_PROPOSED_CLAUSE_AND_ENDPOINT_INPUT_DECISION',
    }
    output.mkdir(parents=True, exist_ok=False, mode=0o700)

    def write(name, value):
        (output / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')

    write('RESULT.json', result)
    write('source_clause_bindings.json', {'audience': 'COORDINATOR_ONLY_NOT_ACTION_REVIEWER',
          'records': records, 'outside_speed_subset': prior['outside_speed_subset']})
    write('proposed_interface_cases.json', {'scope': 'SYNTHETIC_PROPOSAL_NOT_SCENE_VERIFICATION', 'cases': cases})
    (output / 'REPORT_KO.md').write_text(
        '# 속도 행동 source 연결 및 clause 제안 실행\n\n'
        f'21원답/19 clips를 재사용하고 원문 행동 구절·문자 offset·hash를 연결했다. 기존 진입 계약 {result["legacy_contract_links"]}건을 '
        '출처로 연결하되 속도 의미의 근거로 전환하지 않았다. 전체 분모 32와 시험 제외 81 clips를 유지한다.\n\n'
        '감속 의무 9건·정지 의무 6건은 원문에서 찾은 제안 후보이며 수용된 의무가 아니다. '
        '가속 2건은 source 주장만 연결했다. Resume #48/#50/#85 및 Adapt #94는 단일 행동 연결을 미확정으로 남겼다.\n\n'
        '2 clause × 3 motion × 4 applicability × 2 validity = 48 합성 경우/192 행동 결과를 실행했다. '
        'UNKNOWN/CONFLICT/invalid는 STOP 정답이 되지 않으며 FALSE는 전체 가속 허가가 아니다. '
        'SMT 실행 0; 실제 21건의 새 속도 적용성/움직임은 UNKNOWN, 모든 행동 verdict는 UNRESOLVED다.\n\n'
        '## 담당자에게 필요한 두 판단\n\n'
        '1. 감속 의무는 유지·가속을 배제하고, 정지 의무는 완전 정지를 목표로 하지 않는 감속까지 배제하는 '
        '개발 의미 제안을 수용할지 결정해 주세요. 그 밖의 행동도 자동 허용/적절 판정은 아닙니다.\n'
        '2. 과거 영상+네 선택지+판단 불가의 공통 개발 입력을 수용하고, 경로 민감 #79/#81은 '
        '문맥 수용 전 보류할지 결정해 주세요. 실제 배정 수/배포는 별도이며 전체 분모는 유지합니다.\n\n'
        f'구체 표와 제한: `{DESIGN.relative_to(ROOT)}`. 본 결정은 main endpoint/gold/split freeze가 아니다. '
        '이후 Jonh 본인 노출 선언·담당자 입력 수용·배정 결정과 ACTION→CNL 순서가 필요하다. '
        '한 명은 2인 formal gate를 대체하지 않는다.\n\n'
        '독립 속도 정답 0/21, 위반·progress reference 없음/NOT_EVALUATED. 새 설문·학습 0, 기존 ACTION 중단 유지, M16/M17 PARTIAL.\n')
    write('RUN_MANIFEST.json', {
        'project_id': 'guardsynth-coc', 'experiment_id': output.parent.name, 'run_id': output.name,
        'created_at_utc': datetime.now(timezone.utc).isoformat(), 'status': result['status'],
        'network_used': False, 'input_hashes': inputs,
        'code_hashes': {str(Path(__file__).relative_to(ROOT)): sha(Path(__file__).read_bytes())},
        'output_hashes': {p.name: sha(p.read_bytes()) for p in sorted(output.iterdir())},
    })
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    args = parser.parse_args()
    if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*-[0-9]+', args.run_id):
        parser.error('unused numeric-suffix run ID required')
    print(json.dumps(execute(BASE / args.run_id), ensure_ascii=False, indent=2))
