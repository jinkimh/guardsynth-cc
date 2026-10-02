"""Two-hour cohort decision and preregistered development boundary, not main admission."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path

import run_real_development as real
from score_speed_development import score
from speed_admission import audit_row, canonical_sha

ROOT, BASE, R = real.ROOT, real.BASE, real.READINESS


def execute(output, evidence_path=None):
    if output.exists():raise FileExistsError(output)
    import pyarrow.parquet as pq
    inputs={}
    def pin(path):
        path=path.resolve()
        inputs[str(path.relative_to(ROOT))]=real.digest(path)
        return path.read_bytes()
    def load(run,name):
        manifest=json.loads(pin(run/'RUN_MANIFEST.json'))
        data=pin(run/name)
        if real.digest(run/name)!=manifest['output_hashes'][name]:raise ValueError('immutable input drift')
        return json.loads(data)
    evidence=json.loads(pin(evidence_path)) if evidence_path else {'cnl_receipts':[],'policies':[]}
    evidence=evidence.get('admission_evidence',evidence)
    if evidence.get('immutable_run'):
        evidence=load(ROOT/evidence['immutable_run'],'admission_evidence.json')
    examples=real.verified_examples()
    for n in ['RUN_MANIFEST.json','l0_development.jsonl','l3_development.jsonl','scene18_input.jpg']:pin(real.EXPORT/n)
    source=load(R/'stop-control-source-acceptance-2026-09-29-001','source_speed_bindings.json')['records']
    exposure=load(R/'speed-source-binding-2026-09-29-001','split_exposure_ledger.json')
    intake=R/'speed-action-intake-2026-09-29-001'
    mi=json.loads(pin(intake/'RUN_MANIFEST.json'))
    for name in ['development_action_targets.jsonl','development_action_inputs.jsonl']:
        pin(intake/name)
        if real.digest(intake/name)!=mi['output_hashes'][name]:raise ValueError('evaluation bank drift')
    targets=[json.loads(s) for s in (intake/'development_action_targets.jsonl').read_text().splitlines()]
    # Generation/source audit is completed using source rows only; targets are used only for scoring.
    admission=[]
    accepted_run=R/'stop-control-source-acceptance-2026-09-29-001'
    for row in source:
        stem='candidate_'+str(row['candidate_index'])
        contract=mapping=cnl=None
        if (accepted_run/(stem+'_contract.json')).exists():
            contract=load(accepted_run,stem+'_contract.json')
            mapping=load(accepted_run,stem+'_cnl_mapping.json')
            cnl_path=accepted_run/(stem+'_cnl.txt')
            cnl=pin(cnl_path).decode()
            m=json.loads((accepted_run/'RUN_MANIFEST.json').read_text())
            if real.digest(cnl_path)!=m['output_hashes'][cnl_path.name]:raise ValueError('CNL drift')
            if evidence.get('projection_run'):
                # Explicitly selected proposed projection; no old policy/receipt carries across versions.
                from guard_synth_eblc.speed_common_consequence import derive
                from guard_synth_eblc.speed_contract import parse_speed_contract
                projection_run=ROOT/evidence['projection_run']
                proof=load(projection_run,stem+'_proof.json')
                premise=row['speed_premises']
                recomputed=derive(parse_speed_contract(contract),premise['applicability'],premise['evidence_valid'])
                if proof!=recomputed:raise ValueError('common-consequence proof/contract drift')
                projected_text=pin(projection_run/(stem+'_cnl.txt')).decode()
                projection_manifest=json.loads((projection_run/'RUN_MANIFEST.json').read_text())
                if real.digest(projection_run/(stem+'_cnl.txt'))!=projection_manifest['output_hashes'][stem+'_cnl.txt']:
                    raise ValueError('projected CNL drift')
                records=load(projection_run,'RESULT.json')['records']
                record=next(r for r in records if r['candidate_index']==row['candidate_index'])
                if (record['source_ref']!=row['accepted_stop_control']['source_ref']
                        or record['cnl_sha256']!=real.digest(projection_run/(stem+'_cnl.txt'))):
                    raise ValueError('projected scene/source mapping drift')
                cnl=projected_text
                mapping={'text_sha256':record['cnl_sha256'],'contract_sha256':canonical_sha(contract),
                    'source_refs':[record['source_ref']],'semantic_projection_version':proof['derivation_version'],
                    'projection_proof_sha256':real.digest(projection_run/(stem+'_proof.json'))}
        # Real subsequent receipts can be passed explicitly; empty collections mean none supplied.
        # Provenance and exact source/CNL/version binding remain mandatory.
        admission.append(audit_row(row,contract,cnl,mapping,
            receipts=evidence['cnl_receipts'],policies=evidence['policies']))
    # Frozen by clip identity alone, before model predictions; never balance by answers or method success.
    groups=sorted({r['clip_group'] for r in targets},key=lambda g: __import__('hashlib').sha256(('m18-dev-20260929:'+g).encode()).hexdigest())
    train=set(groups[:12]);test=set(groups[12:])
    split={'status':'LOCKED_DEVELOPMENT_EXPLORATORY_ONLY','locked_at_utc':datetime.now(timezone.utc).isoformat(),
        'main_test':False,'results_available_at_lock':False,'train_clip_groups':sorted(train),'evaluation_clip_groups':sorted(test),
        'records':[{'sample_id':r['sample_id'],'clip_group':r['clip_group'],'partition':'train' if r['clip_group'] in train else 'evaluation'} for r in targets],
        'admissible_speed_training_rows_at_lock':0,'admissible_speed_evaluation_rows_at_lock':0,
        'currently_executable_as_performance_experiment':False,'scene18_separate_entry_task_not_pooled':True}
    original_split=BASE/'m18-cohort-feasibility-2026-09-29-001'
    if original_split.exists():
        split=load(original_split,'exploratory_split_lock.json')
    # Exhaust pinned local upstream files, notebooks and schema, without online interpolation.
    corpus=[ROOT/'third_party/physical_ai_av/src/physical_ai_av/egomotion.py',
        ROOT/'third_party/physical_ai_av/src/physical_ai_av/utils/tf.py',
        ROOT/'third_party/physical_ai_av/src/physical_ai_av/dataset.py',
        ROOT/'third_party/physical_ai_av/notebooks/data_visualization.ipynb',
        ROOT/'third_party/cascade-devkit/src/cascade_av/dataset.py',
        ROOT/'data/restricted/nvidia_physicalai/features.csv']
    for path in corpus:pin(path)
    motion=[]
    for row in source:
        path=ROOT/row['motion_evidence']['file'];pin(path)
        table=pq.read_table(path);data=table.select(['timestamp','vx','vy','vz']).to_pylist()
        past=[v for v in data if 0<=v['timestamp']<=row['event_timestamp_us']]
        tail=past[-3:]
        motion.append({'candidate_index':row['candidate_index'],'schema':str(table.schema),
            'last_three_causal_rows':tail,'source_sha256':real.digest(path),
            'time_unit':'MICROSECONDS','time_basis':'CLIP_RELATIVE_UPSTREAM_SDK_CONVENTION',
            'clock_independently_calibrated':False,'velocity_unit':'NOT_DECLARED_IN_LOCAL_AUTHORITATIVE_SCHEMA',
            'error_bounds':'NOT_FOUND','stationary_threshold':'NOT_DECLARED','event_motion':'UNKNOWN',
            'offline_or_future_interpolation_used':False})
    reasoning=ROOT/'data/restricted/nvidia_physicalai/reasoning/ood_reasoning.parquet';pin(reasoning)
    available=set(pq.read_table(reasoning,columns=['clip_id']).column('clip_id').to_pylist())
    excluded=set(exposure['excluded_test_clip_ids']) | {x['clip_id'] for x in source} | {examples[0]['group_id']}
    fresh={'status':'UNLABELLED_RETRIEVAL_LEADS_NOT_FROZEN_TEST','reasoning_clip_count':len(available),
        'excluded_clip_ids':sorted(excluded),'candidate_clip_ids':sorted(available-excluded),
        'human_action_labels':0,'verified_source_cnl_rows':0,'test_eligible_rows':0,
        'remaining_checks':['episode linkage','source/CNL eligibility','blind ACTION','power','image availability']}
    # Primary Project01 run records, not re-labelled Project04 experiments.
    prior_records=[]
    patterns={'COC_ONLY':'temporal-coc-only-seed{}-v0','INLINE_NL_CONSTRAINT':'temporal-rich-coc-seed{}-v0',
        'SEPARATE_NL_GUARD':'temporal-natural-guard-seed{}-v0','SHUFFLED_GUARD':'temporal-shuffled-guard-seed{}-v0',
        'LOGIC_GUARD':'temporal-logic-guard-seed{}-v0'}
    for condition,pattern in patterns.items():
        for seed in (42,17,123):
            directory=ROOT/'artifacts/results/public/small-vlm-guard-v0'/pattern.format(seed)
            path=directory/'result.json';d=json.loads(pin(path));pin(directory/'adapter/adapter_config.json')
            weights=directory/'adapter/adapter_model.safetensors';pin(weights)
            assert d['seed']==seed and sum(h['optimizer_steps'] for h in d['history'])==72
            rows=d['post_test']['rows'];rate=sum(r['guard_violation'] for r in rows)/len(rows)
            assert abs(rate-d['post_test']['guard_violation_rate'])<1e-12
            prior_records.append({'owner':'safety-constrained-coc','condition':condition,'seed':seed,
                'primary_run_record':str(path.relative_to(ROOT)),
                'run_manifest_present':(directory/'RUN_MANIFEST.json').exists(),
                'optimizer_steps':72,'adapter_sha256':real.digest(weights),'post_test_violation_rate':rate,
                'post_test_safe_completion':d['post_test']['safe_goal_completion_rate'],
                'unseen_time_safe_completion':d['post_unseen']['safe_goal_completion_rate'],
                'guard_visible_at_inference':True,'current_L3':False})
    provider_inventory={}
    for name in ('speed-source-providers-2026-09-29-001','matched-speed-providers-2026-09-29-001'):
        run=BASE/name
        if not (run/'RUN_MANIFEST.json').exists():continue
        records=[json.loads(s) for s in pin(run/'provider_outputs.jsonl').decode().splitlines()]
        m=json.loads(pin(run/'RUN_MANIFEST.json'))
        if real.digest(run/'provider_outputs.jsonl')!=m['output_hashes']['provider_outputs.jsonl']:
            raise ValueError('provider output drift')
        provider_inventory[name]={arm:dict(__import__('collections').Counter(
            r['status'] for r in records if r['arm']==arm)) for arm in ('L1','L2')}
    protocol={'priority_window_hours':48,'cohort_viability_budget_hours':2,'model_id':real.learning.MODEL_ID,
        'model_revision':real.learning.REVISION,'primary_next_comparison':['L0','L3'],
        'four_arm_main_gate_unchanged':True,
        'provider_implementation_present':(Path(__file__).with_name('run_matched_speed_providers.py')).exists(),
        'provider_outputs':provider_inventory,'main_qualified_provider_cohort':False,
        'L3_status':'SCENE18_REVIEWED_ENTRY_ONLY_SPEED_ADMISSION_FIDELITY_PENDING',
        'common_inputs_labels_budget_required':True,'inference_gold_CNL_forbidden':True,
        'hypothesis_metrics':['reference_inappropriate','normal_progress_reference','unnecessary_stop_reference','coverage'],
        'safety_violation':'NOT_IDENTIFIED_FROM_APPROPRIATENESS_ONLY_LABELS',
        'seed_repeats_do_not_replace_independent_clips':True,'test_tuning':False,
        'no_silent_relaxation_of_original_success_criteria':True,
        'decision_if_no_viable_cohort':'REPORT_INCONCLUSIVE_AND_PRIOR_RESULT_ATTRIBUTION_NOT_MAIN_EFFECT'}
    baseline=[{'sample_id':r['sample_id'],'action':'STOP_OR_WAIT'} for r in targets]
    diagnostic=score(targets,baseline);diagnostic['prediction_origin']='ALWAYS_STOP_SOFTWARE_DIAGNOSTIC_NOT_VLM'
    result={'project_id':'guardsynth-coc','status':'NO_VIABLE_REAL_SPEED_PERFORMANCE_COHORT_CURRENT_GATES',
        'reviewed_entry_development_scenes':len({r['group_id'] for r in examples}),
        'speed_action_reference_scenes':len(targets),'speed_clip_groups':len(groups),
        'speed_training_eligible':sum(r['training_eligible'] for r in admission),
        'speed_mechanically_ready':sum(r['checks']['mechanical_ready'] for r in admission),
        'speed_human_cnl_receipts':sum(r['checks']['human_cnl_receipt'] for r in admission),
        'speed_policy_scope_met':sum(r['checks']['research_policy_scope'] for r in admission),
        'speed_independent_main_test_eligible':0,
        'accepted_stop_source_scenes':sum(r['source_stop_premise_accepted'] for r in admission),
        'motion_states_resolved':sum(r['motion_state']!='UNKNOWN' for r in admission),
        'motion_time_convention_resolved':len(motion),
        'fresh_unlabelled_clip_leads':len(available-excluded),'fresh_labelled_test_rows':0,
        'prior_primary_runs_audited':len(prior_records),'prior_project04_results_added':0,
        'main_training_started':False,'one_scene_smoke_is_performance_deliverable':False}
    if result['speed_training_eligible']:
        result['status']='ROW_ADMISSION_PRESENT_COHORT_COVERAGE_STILL_REQUIRES_ASSESSMENT'
    output.mkdir(parents=True,exist_ok=False,mode=0o700)
    artifacts={'admission_audit.json':admission,'exploratory_split_lock.json':split,'local_motion_evidence.json':motion,
        'fresh_inventory.json':fresh,'protocol_lock.json':protocol,'prior_project01_evidence.json':prior_records,
        'always_stop_diagnostic.json':diagnostic,'RESULT.json':result,'admission_evidence.json':evidence}
    for name,value in artifacts.items():(output/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
    (output/'REPORT_KO.md').write_text('# 48시간 우선순위: 코호트 가능성 판정\n\n'
        f"현재 속도 학습 적격{result['speed_training_eligible']}/{len(source)}, 기계 연결 충족{result['speed_mechanically_ready']}, "
        f"실제 사람 CNL receipt{result['speed_human_cnl_receipts']}, 속도 개발 정책 범위 충족{result['speed_policy_scope_met']}. "
        '미노출 label/source/CNL 충족 test0. 기존 진입 scene18은 다른 과제와 섞지 않는다. '
        '누락 gate는 행별 근거 검사에서 계산하며 응답을 만들지 않는다. 두 STOP 사례만으로 정상 진행을 평가할 수 없다.\n\n'
        '기존 결과 전 hash-only 개발 partition을 그대로 재사용했다. 이후 수용 수가 변해도 분할을 다시 고르지 않으며 fresh main test가 아니다. '
        '독립 ACTION-only scorer는 선택 부적절성/정상 진행/불필요 정지 참조율·coverage·장면별 출력·clip bootstrap을 계산한다. 부적절성을 실제 안전 위반 정답으로 바꾸지 않는다. always-stop은 소프트웨어 진단이다.\n\n'
        '로컬 SDK/노트북/parquet는 clip-relative microseconds와 velocity 열을 뒷받침한다. 단위·센서 오차/정지 기준은 확보된 권위 파일에 없어 임계값 없이 motion은UNKNOWN 유지. 과거3표본과 schema/hash를 기록했다.\n\n'
        'Project01 원 primary result/adapter15개(5조건×3seed)를 확인했다. 실제72updates/seed의 supplied-guard 연구다. 별도 RUN_MANIFEST는 없어 있다고 쓰지 않았다. '
        '기존 실제 학습 근거를 인정하며 Project04 L3 또는 no-gold-at-test 성능으로 재표기하지 않는다.\n\n'
        'L1/L2 구현 존재와 실제 출력/기권/구문 실패 수는 protocol_lock.json에 분리했다. '
        'source-only 출력은 본 CoC/영상 matched arm과 다르며, source-supported subset 출력도 main arm 완료가 아니다. '
        'L0 대비만으로 EBLC 우월성을 주장하지 않는다. 원고는 prior actual evidence, 개발 baseline, 신규 source binding의 제한을 구분한다.\n')
    manifest={'project_id':'guardsynth-coc','run_id':output.name,'status':'COMPLETE',
        'created_at_utc':datetime.now(timezone.utc).isoformat(),'input_hashes':inputs,
        'code_hashes':{str(p.relative_to(ROOT)):real.digest(p) for p in [Path(__file__),Path(__file__).with_name('score_speed_development.py'),Path(__file__).with_name('speed_admission.py')]},
        'output_hashes':{p.name:real.digest(p) for p in output.iterdir()},'network_used':False}
    (output/'RUN_MANIFEST.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run-id',required=True)
    p.add_argument('--admission-evidence',type=Path);a=p.parse_args()
    if not __import__('re').fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*-[0-9]+',a.run_id):p.error('invalid run-id')
    print(json.dumps(execute(BASE/a.run_id,a.admission_evidence),indent=2))
