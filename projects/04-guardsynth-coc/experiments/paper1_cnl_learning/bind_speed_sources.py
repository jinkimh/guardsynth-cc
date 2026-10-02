"""Bind existing source observations and causal sensor samples, never ACTION targets.

Reported source predicates are executable facts about reports, not speed obligations.
No implicit entry-to-speed policy, motion threshold, or observer-to-CASCADE identity join.
"""
import argparse
import base64
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re
import sys

ROOT = next(p for p in Path(__file__).resolve().parents if (p / 'PROJECT_REGISTRY.json').is_file())
sys.path[:0] = [str(ROOT / 'projects/04-guardsynth-coc/src'), str(Path(__file__).parent)]
from guard_synth.event_source_binding import source_index
import execute_speed_contracts as execution

BASE = execution.BASE
SOURCE = BASE / 'conditional-candidates-2026-09-08-002'
OBSERVATIONS = BASE / 'source-observation-intake-2026-09-28-001'
CONTRACTS = BASE / 'speed-contract-execution-2026-09-28-001'
MATERIALIZED = ROOT / 'data/restricted/nvidia_physicalai/internal-derived'
SELECTED = (6, 7, 31, 48, 50, 52, 53, 55, 59, 60, 64, 68, 74, 84, 85, 86, 88, 93, 94)
FIELDS = ('target_status', 'target_description', 'target_point', 'zone_status', 'zone_polygon',
          'ped_truth', 'ped_reason', 'road_context', 'road_truth', 'road_reason',
          'control_context', 'control_truth', 'control_reason')
PREDICATES = ('ped_truth', 'road_truth', 'control_truth')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def motion_sample(rows, event_us, ref, feature):
    """Last past raw sample only; offline smoothing and future interpolation are excluded."""
    if feature != 'egomotion':
        raise ValueError('offline or unknown feature cannot supply causal motion')
    if type(event_us) is not int or not rows:
        raise ValueError('invalid event or empty motion data')
    times = [r['timestamp'] for r in rows]
    if any(type(t) is not int for t in times) or any(a >= b for a, b in zip(times, times[1:])):
        raise ValueError('motion timestamps must be strictly increasing integers')
    indices = [i for i, t in enumerate(times) if 0 <= t <= event_us]
    if not indices:
        return {'status': 'NO_PAST_SAMPLE', 'motion_state': 'UNKNOWN', 'source_ref': ref}
    i = indices[-1]
    vector = [rows[i][k] for k in ('vx', 'vy', 'vz')]
    if any(type(v) not in (int, float) or not math.isfinite(v) for v in vector):
        raise ValueError('invalid velocity sample')
    norm = math.hypot(*vector)
    return {'status': 'PAST_RAW_SAMPLE_BOUND', 'source_ref': ref + f'#/rows/{i}',
            'row_index': i, 'timestamp_us': times[i], 'age_us': event_us - times[i],
            'velocity_xyz_native': vector, 'velocity_norm_native': norm,
            'sample_velocity_nonzero': norm != 0,
            'unit': 'NOT_DECLARED_IN_PINNED_PARQUET_SCHEMA',
            'motion_state': 'UNKNOWN', 'event_state_certified': False,
            'reason': 'NO_ACCEPTED_EVENT_FRESHNESS_ERROR_BOUND_OR_STATIONARY_THRESHOLD',
            'clock_scope': 'EXISTING_CLIP_EVENT_CLOCK_NOT_INDEPENDENTLY_CALIBRATED',
            'future_samples_used': 0, 'offline_smoothing_used': False}


def bind_sources(candidate, answer, annotation, annotation_sha, answer_ref, motion):
    """Explicit field allowlist prevents unused ACTION/CoC labels influencing bindings."""
    if (answer['candidate_digest'] != candidate['candidate_digest']
            or answer['event_timestamp_us'] != candidate['event_timestamp_us']
            or annotation['video']['clip_id'] != candidate['clip_id']):
        raise ValueError('source identity mismatch')
    t = candidate['event_timestamp_us']
    if type(t) is not int or not 0 <= t <= annotation['video']['duration_s'] * 1_000_000:
        raise ValueError('event outside source duration')
    observation = {k: answer[k] for k in FIELDS}
    facts = {}
    for field in PREDICATES:
        raw = observation[field]
        if raw not in {'TRUE', 'FALSE', 'UNKNOWN', 'CONFLICT', 'NOT_APPLICABLE'}:
            raise ValueError('invalid source observation choice')
        facts[field] = {'raw': raw, 'reported_truth': raw if raw != 'NOT_APPLICABLE' else 'UNKNOWN',
                        'source_ref': answer_ref + '/' + field,
                        'scope': 'REPORTED_ENTRY_PREDICATE_NOT_SPEED_OBLIGATION',
                        'legacy_na_unresolved': raw == 'NOT_APPLICABLE'}
    index = source_index(annotation['annotation'], annotation_sha, t)
    actors, controls = [], []
    for item in index.values():
        if item['source_category'] == 'EGO' or not item['active_at_event']:
            continue
        value = item['value']
        witness = {k: item[k] for k in ('source_ref_id', 'parent_entity_id', 'evidence_ref',
                   'interval', 'ancestor_intervals')}
        if item['source_category'] == 'ACTOR' and item['source_ref_id'] == item['parent_entity_id']:
            actors.append({**witness, 'entity_type': value.get('type'),
                           'observer_identity_established': False})
        if (value.get('property_type') == 'Signal' and value.get('signaling_details')) or 'color' in value:
            controls.append({**witness, 'signal': value.get('signaling_details'),
                             'color': value.get('color'), 'applicability_to_ego': 'UNKNOWN',
                             'scope': 'DECLARED_ANNOTATION_INTERVAL_NOT_INDEPENDENT_VISUAL_TRUTH'})
    target = {'status': 'UNRESOLVED', 'observation_target_id': None, 'cascade_entity_id': None,
              'source_ref': answer_ref + '/target_point', 'description': observation['target_description'],
              'point': observation['target_point'], 'physical_identity_confirmed': False}
    if observation['target_status'] == 'CONFIRMED':
        p = observation['target_point']
        if (not isinstance(p, list) or len(p) != 2
                or any(type(v) not in (float, int) or not math.isfinite(v) or not 0 <= v <= 1 for v in p)
                or not observation['target_description'].strip()):
            raise ValueError('confirmed observation target lacks valid point/description')
        target.update(status='REPORTED_TARGET_ANCHOR_BOUND',
                      observation_target_id='source_target_' + candidate['candidate_digest'].split(':')[1])
    # Preserve both evidence channels. Matching words/counts are not object identity or a rule.
    stop_witnesses = [c['evidence_ref'] for c in controls if (c['signal'] or {}).get('intent') == 'Stop']
    agreement = observation['control_context'] == 'APPLICABLE' and observation['control_truth'] == 'TRUE' and bool(stop_witnesses)
    gaps = [
        {'field': 'speed_applicability', 'reason': 'NO_ACCEPTED_SOURCE_PREDICATE_TO_SPEED_POLICY',
         'source_refs': [facts[k]['source_ref'] for k in PREDICATES],
         'required': 'Source-curation acceptance and explicit speed-specific rule; not ACTION labels.'},
        {'field': 'motion_state', 'reason': motion.get('reason', motion['status']),
         'source_refs': [motion['source_ref']],
         'required': 'Source units/clock and accepted causal freshness/error/zero-speed interpretation.'},
        {'field': 'target_entity_id', 'reason': 'NO_TIME_MATCHED_OBSERVER_TO_CASCADE_IDENTITY',
         'source_refs': [answer_ref + '/target_point'] + [a['evidence_ref'] for a in actors],
         'required': 'Keep the reported image anchor; do not assign an Agent ID by uniqueness or prose.'}]
    return {'candidate_index': candidate['geometry_index'], 'candidate_digest': candidate['candidate_digest'],
            'clip_id': candidate['clip_id'], 'event_timestamp_us': t,
            'observation': observation, 'observation_ref': answer_ref, 'reported_predicates': facts,
            'target_binding': target, 'active_source_actors': actors, 'active_source_controls': controls,
            'motion_evidence': motion, 'reported_applied_control_with_stop_annotation': bool(agreement),
            'stop_annotation_refs': stop_witnesses, 'gaps': gaps,
            'speed_premises': {'motion_state': 'UNKNOWN', 'applicability': 'UNKNOWN', 'evidence_valid': False},
            'training_allowed': False, 'formal_source_accepted': False}


def source_core(contract, row):
    """Constrain source report facts separately; disallow silently certifying a speed premise."""
    core = execution.lower_speed_contract(execution.parse_speed_contract(contract))
    refs = [row['observation_ref'], row['motion_evidence']['source_ref']] + [
        b['source_ref'] for b in row['reported_predicates'].values()]
    core['source_refs'] = list(dict.fromkeys(core['source_refs'] + refs))
    facts = []
    for field, binding in row['reported_predicates'].items():
        name = 'reported_' + field
        core['declarations'].append({'name': name, 'sort': 'ENUM', 'time_varying': True,
            'enum_name': 'Truth', 'enum_values': ['TRUE', 'FALSE', 'UNKNOWN', 'CONFLICT'],
            'unit': None, 'frame': None, 'source_refs': [binding['source_ref']]})
        facts.append(execution.eq(name, binding['reported_truth'], 'Truth'))
    facts.append(execution.premises('UNKNOWN', 'UNKNOWN', False))
    core['clauses'].append({'id': 'pinned_source_report_facts', 'kind': 'INVARIANT',
        'enforcement': 'INITIAL', 'formula': execution.conjunction(*facts),
        'source_refs': refs, 'description': 'Reported predicates; no entry-to-speed implication.'})
    for field, binding in row['reported_predicates'].items():
        execution.add_query(core, field + '_drift', execution.neg(execution.eq(
            'reported_' + field, binding['reported_truth'], 'Truth')), 'UNSAT')
    for truth in ('TRUE', 'FALSE'):
        execution.add_query(core, 'no_unsupported_' + truth.lower(), execution.eq('applicability', truth, 'Truth'), 'UNSAT')
    for action in execution.ACTIONS:
        execution.add_query(core, action.lower() + '_unresolved', execution.neg(execution.eq(
            action.lower() + '_verdict', 'UNRESOLVED', 'SpeedVerdict')), 'UNSAT')
    return core


def sensor_member(manifest, material_root, video, clip_id):
    """A materialized clip may support multiple events; never alias their event identities."""
    relative = str((video.parent.parent / 'egomotion/egomotion.parquet').relative_to(material_root))
    found = [r for r in manifest['records'] if r['relative_path'] == relative and r['role'] == 'egomotion']
    videos = [r for r in manifest['records'] if r['relative_path'] == str(video.relative_to(material_root))]
    if len(found) != 1 or len(videos) != 1 or any(r['clip_id'] != clip_id for r in found + videos):
        raise ValueError('motion/video manifest clip identity mismatch')
    if found[0]['candidate_digest'] != videos[0]['candidate_digest']:
        raise ValueError('materialization identity mismatch')
    return found[0]


def execute(output):
    if output.exists():
        raise FileExistsError(output)
    import pyarrow.parquet as pq
    inputs = {}

    def pin(path, expected=None):
        data = path.read_bytes()
        digest = sha(data)
        if expected is not None and digest != expected:
            raise ValueError('input hash mismatch: ' + str(path))
        inputs[str(path.relative_to(ROOT))] = digest
        return data

    def load(run, name):
        manifest = json.loads(pin(run / 'RUN_MANIFEST.json'))
        return json.loads(pin(run / name, manifest['output_hashes'][name]))

    candidates = load(SOURCE, 'candidate_readiness.json')['records']
    submission = load(OBSERVATIONS, 'review_submission.json')
    observations = submission['records']
    packet_run = BASE / 'source-gap-ui-2026-09-09-002'
    packet = load(packet_run, 'source_gap_packet.json')
    if inputs[str((packet_run / 'source_gap_packet.json').relative_to(ROOT))] != submission['packet_sha256']:
        raise ValueError('source observation packet mismatch')
    scene_packet = {r['candidate_digest']: (i, r) for i, r in enumerate(packet['scenes'])}
    ui_manifest = json.loads(pin(packet_run / 'RUN_MANIFEST.json'))
    ui = pin(packet_run / 'source_gap_review.html', ui_manifest['output_hashes']['source_gap_review.html']).decode()
    if "if(mode==='view'||frame!==scene().frames.length-1)return" not in ui:
        raise ValueError('source target last-frame drawing convention not verified')
    prior_records = load(CONTRACTS, 'coordinator_bindings.json')['records']
    if len(candidates) != 32 or len({r['candidate_digest'] for r in candidates}) != 32:
        raise ValueError('candidate denominator drift')
    if len({r['candidate_digest'] for r in observations}) != len(observations):
        raise ValueError('duplicate source observation')
    by_obs = {r['candidate_digest']: (i, r) for i, r in enumerate(observations)}
    by_prior = {r['candidate_index']: r for r in prior_records}
    exposure = load(execution.prior.PREFLIGHT, 'split_exposure_ledger.json')
    if len(exposure['excluded_test_clip_ids']) != 81 or exposure['split_status'] != 'NOT_FROZEN':
        raise ValueError('exposure boundary drift')
    # Fixed input boundary: no speed ACTION intake, targets, submissions, or clarifications are opened.
    for name in ('SOURCE_GAP_OBSERVATION_ACCEPTANCE_DECISION_V01.md',
                 'PAPER1_SPEED_DEVELOPMENT_APPROVAL_DECISION_V01.md',
                 'PAPER1_ORIGINAL_CONTEXT_PRESERVATION_DECISION_V01.md'):
        pin(ROOT / 'projects/04-guardsynth-coc/docs/decisions' / name)
    pin(Path(__file__).with_name('bind_speed_sources.py'))
    pin(ROOT / 'projects/04-guardsynth-coc/src/guard_synth/event_source_binding.py')
    pin(ROOT / 'third_party/physical_ai_av/src/physical_ai_av/egomotion.py')
    pin(ROOT / 'projects/04-guardsynth-coc/docs/designs/PAPER1_SPEED_SOURCE_BINDING_DESIGN_V01.md')
    records, checks, cores = [], {}, {}
    for number in SELECTED:
        c = next(r for r in candidates if r['geometry_index'] == number)
        prior = by_prior[number]
        if any(c[k] != prior[k] for k in ('candidate_digest', 'clip_id', 'event_timestamp_us')):
            raise ValueError('prior scene identity drift')
        i, answer = by_obs[c['candidate_digest']]
        obs_ref = 'sha256:' + inputs[str((OBSERVATIONS / 'review_submission.json').relative_to(ROOT))] + f'#/records/{i}'
        annotation = json.loads(pin(ROOT / c['annotation_path'], c['annotation_sha256']))
        video = ROOT / c['raw_video']
        material_root = video.parents[2]
        if material_root not in (MATERIALIZED / 'm16-shortlist-v1', MATERIALIZED / 'm16-reserve-v1'):
            raise ValueError('unregistered materialized sensor root')
        manifest = json.loads(pin(material_root / 'MANIFEST.json'))
        sensor = sensor_member(manifest, material_root, video, c['clip_id'])
        path = material_root / sensor['relative_path']
        pin(path, sensor['sha256'])
        table = pq.read_table(path, columns=['timestamp', 'vx', 'vy', 'vz'])
        if table.num_rows != sensor['rows']:
            raise ValueError('motion row count drift')
        motion = motion_sample(table.to_pylist(), c['event_timestamp_us'], 'sha256:' + sensor['sha256'], sensor['feature'])
        motion['file'] = str(path.relative_to(ROOT))
        motion['materialization_candidate_digest'] = sensor['candidate_digest']
        motion['materialization_event_timestamp_us'] = sensor['event_timestamp_us']
        motion['requested_event_timestamp_us'] = c['event_timestamp_us']
        row = bind_sources(c, answer, annotation, c['annotation_sha256'], obs_ref, motion)
        packet_i, scene = scene_packet[c['candidate_digest']]
        if any(scene[k] != c[k] for k in ('clip_id', 'event_timestamp_us')):
            raise ValueError('observation image identity mismatch')
        frame = scene['frames'][-1]
        if frame['timestamp_us'] > c['event_timestamp_us'] or sha(base64.b64decode(
                frame['data_url'].split(',', 1)[1], validate=True)) != frame['sha256']:
            raise ValueError('observation anchor image hash or time mismatch')
        row['target_binding']['image_anchor'] = {k: frame[k] for k in ('frame_index', 'timestamp_us', 'sha256')}
        row['target_binding']['image_anchor']['event_offset_us'] = frame['timestamp_us'] - c['event_timestamp_us']
        row['target_binding']['image_anchor']['source_ref'] = 'sha256:' + inputs[str(
            (packet_run / 'source_gap_packet.json').relative_to(ROOT))] + f'#/scenes/{packet_i}/frames/{len(scene["frames"])-1}'
        row['original_coc_sha256'] = sha(c['original_coc'].encode())
        row['existing_contract_ref'] = None
        if prior['contract_file']:
            contract = load(CONTRACTS, prior['contract_file'])
            row['existing_contract_ref'] = str((CONTRACTS / prior['contract_file']).relative_to(ROOT))
            core = source_core(contract, row)
            checked = execution.check_queries(execution.compile_core_model(execution.parse_core_model(core)))
            if checked['query_count'] != checked['matches_expected']:
                raise ValueError('source-bound SMT regression')
            cores[f'candidate_{number}_source_core.json'] = core
            checks[str(number)] = checked
        else:
            row['gaps'].append({'field': 'speed_contract', 'reason': 'NO_ACCEPTED_CLAUSE_FOR_SOURCE_ACTION',
                                'source_refs': [], 'required': 'Do not copy a reduction/stop contract into recovery/acceleration.'})
        records.append(row)
    result = {'project_id': 'guardsynth-coc', 'status': 'SOURCE_BINDINGS_EXECUTED_ACCEPTANCE_POLICY_PENDING',
        'candidate_denominator': 32, 'speed_candidates': 21, 'bound_scene_records': len(records),
        'clip_groups': len({r['clip_id'] for r in records}), 'held_candidates': [79, 81],
        'reported_target_anchors': sum(r['target_binding']['observation_target_id'] is not None for r in records),
        'cascade_control_scenes': sum(bool(r['active_source_controls']) for r in records),
        'raw_motion_samples_bound': sum(r['motion_evidence']['status'] == 'PAST_RAW_SAMPLE_BOUND' for r in records),
        'sample_age_us_range': [min(r['motion_evidence']['age_us'] for r in records), max(r['motion_evidence']['age_us'] for r in records)],
        'control_stop_agreement_candidates': [r['candidate_index'] for r in records if r['reported_applied_control_with_stop_annotation']],
        'source_bound_core_models': len(cores), 'smt_queries': sum(c['query_count'] for c in checks.values()),
        'gap_counts': dict(Counter(g['reason'] for r in records for g in r['gaps'])),
        'action_response_inputs_read': 0, 'motion_states_certified': 0, 'scene_applicability_certified': 0,
        'cascade_target_identity_certified': 0, 'new_training_scenes': 0, 'new_review_requests': 0,
        'formal_gold_added': 0, 'main_training_started': False, 'main_split_frozen': False,
        'exposure_ledger_preserved': True, 'excluded_test_clips': 81,
        'source_anchor_images_verified': 19, 'm16_gate': 'PARTIAL', 'm17_gate': 'PARTIAL'}
    output.mkdir(parents=True, exist_ok=False, mode=0o700)
    def write(name, value):
        (output / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
    write('source_speed_bindings.json', {'records': records, 'held_candidates': [79, 81]})
    write('source_binding_checks.json', checks)
    write('split_exposure_ledger.json', exposure)
    for name, core in cores.items():
        write(name, core)
    write('RESULT.json', result)
    report = ['# 속도 source 조건·대상·이동 근거 연결', '',
        'ACTION 답/이유/설명 파일을 읽지 않고 기존 source 관찰과 원본 CASCADE, raw egomotion을 연결했다. 원답·CoC·이전 run은 변경하지 않았다.', '',
        f"19장면/17 clips: 관찰 대상 anchor {result['reported_target_anchors']}건, CASCADE 통제 {result['cascade_control_scenes']}장면, 과거 raw velocity sample 19건. sample age는 {result['sample_age_us_range']}us다.",
        f"13개 Core에 source 보고 predicate를 별도 변수로 실제 고정하고 {result['smt_queries']}질의를 통과했다. 기존 조건부 CNL을 재생성하지 않았다.", '',
        '| 후보 | 관찰 ped/control | 관찰 대상 | CASCADE 통제 | 과거 velocity norm (원 단위) / age us |',
        '|---|---|---|---|---|']
    for r in records:
        sigs = [str((c['signal'] or {}).get('intent') or c['color']) for c in r['active_source_controls']]
        m = r['motion_evidence']
        report.append(f"| #{r['candidate_index']} | {r['observation']['ped_truth']} / {r['observation']['control_truth']} | {r['target_binding']['status']} | {', '.join(sigs) or '없음(부재 확정 아님)'} | {m['velocity_norm_native']:.8g} / {m['age_us']} |")
    report += ['', '## 남은 정확한 판단 경계', '',
        '- source_speed_bindings.json 각 행은 원답 field JSON pointer, CASCADE interval/ref, sensor 파일 SHA와 row index 및 필드별 gaps를 포함한다.',
        '- 관찰 target anchor는 설명/좌표의 출처 연결이다. CASCADE Agent 동일성이나 실제 충돌 영역 인증은 아니다. 해당 ID를 계약의 물리적 target으로 자동 승격하지 않았다.',
        '- #7/#68은 기존 control APPLICABLE+TRUE와 사건 시점 Stop 주석이 함께 있다. 이는 구체적인 source 수용 검토 후보이며 자동 STOP 의무 확정이 아니다. #68의 STOP paddle은 원 CoC red-light 주장과 별개로 유지한다.',
        '- #52/#84의 control UNKNOWN은 CASCADE Stop/Slow Down으로 덮어쓰지 않는다. #60/#86/#94 entry-control FALSE는 속도 해제가 아니다. #85의 동시 Stop/red도 누락하지 않는다.',
        '- 수치 velocity는 직전 raw sample만 사용했다. offline smoothing·미래 보간·실제 운전 action labels는 사용하지 않았다. pinned schema의 unit·오차/zero/freshness 정책과 독립 clock 확인이 없어 현재 MOVING/STATIONARY로 인증하지 않는다. #7의 sample 0도 정지 의도나 정지 완료 정답이 아니다.',
        '- ped TRUE/FALSE/legacy NA는 보고된 진입 조건이다. 어떤 관찰을 감속/정지의 충분조건으로 삼을지 승인된 speed-specific source 정책이 없다. speed applicability UNKNOWN과 evidence_valid=false를 유지했다. 표본 수·SMT 통과는 이 판단을 대신하지 않는다.',
        '- 다음 사람 판단: #7/#68의 일치 근거를 정지 통제의 개발 source 전제로 수용할지, #68을 red light와 별도 STOP paddle 근거로만 사용할지 결정이 필요하다. 이는 새 ACTION 설문이나 이미 승인된 행동 배제 의미의 재승인 요청이 아니다.',
        '- 그 외 필드별 source/정책 gap은 JSON에 유지한다. ACTION19/19 수용·3마스크·#52/#55/#60 원문 불일치 기록·계약 없는6건·held79/81·전체32분모·81clip 시험제외·2인 formal gate를 그대로 유지한다. 학습/export·새 설문·UI·게시·commit/push 없음.', '']
    (output / 'REPORT_KO.md').write_text('\n'.join(report))
    code_paths = [Path(__file__), Path(execution.__file__),
                  ROOT / 'projects/04-guardsynth-coc/tests/integration/test_speed_source_binding.py',
                  ROOT / 'platforms/eblc-bcv/src/guard_synth_eblc/speed_contract.py']
    write('RUN_MANIFEST.json', {'project_id': 'guardsynth-coc', 'run_id': output.name,
        'created_at_utc': datetime.now(timezone.utc).isoformat(), 'status': 'COMPLETE',
        'input_hashes': inputs, 'code_hashes': {str(p.relative_to(ROOT)): sha(p.read_bytes()) for p in code_paths},
        'output_hashes': {p.name: sha(p.read_bytes()) for p in output.iterdir()}, 'network_used': False})
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    args = parser.parse_args()
    if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*-[0-9]+', args.run_id):
        parser.error('run-id must be kebab-case ending in a number')
    print(json.dumps(execute(BASE / args.run_id), ensure_ascii=False, indent=2))
