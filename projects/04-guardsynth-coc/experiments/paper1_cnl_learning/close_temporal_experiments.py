"""Audit completed frozen experiments and collect every metric without changing verdicts."""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
BASE = ROOT/'artifacts/projects/guardsynth-coc/public/paper1-method-preservation-001'
EXP = BASE/'temporal-expansion-learning-2026-09-29-001'
COST = BASE/'temporal-cost-learning-2026-09-29-001'
SECONDARY = BASE/'temporal-secondary-metrics-2026-09-29-001'
SEEDS = (42, 17, 123)
FIELDS = {'accuracy':'correct', 'guard_violation_rate':'guard_violation',
          'hold_violation_rate':'hold_violation', 'deadlock_rate':'deadlock',
          'goal_completion_rate':'goal_complete', 'safe_goal_completion_rate':'safe_goal_complete',
          'coverage':'valid', 'invalid_rate':'invalid'}


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''): h.update(chunk)
    return h.hexdigest()


def load(path): return json.loads(path.read_text())


def audit(base, seen):
    p = base/'RUN_MANIFEST.json'; m = load(p)
    if m.get('status', 'COMPLETE') != 'COMPLETE': raise ValueError('incomplete manifest')
    paths = [(base/k,v) for k,v in m['output_hashes'].items()]
    paths += [(ROOT/k,v) for k,v in m.get('input_hashes',{}).items()]
    for hashes in m.get('adapter_hashes',{}).values(): paths += [(ROOT/k,v) for k,v in hashes.items()]
    for path,digest in paths:
        if sha(path) != digest: raise ValueError('hash mismatch: '+str(path))
        seen[str(path.relative_to(ROOT))] = digest
    seen[str(p.relative_to(ROOT))] = sha(p)
    return len(paths)


def check_predictions(base, result, expected_n, expected_updates):
    count=0; steps=0; checkpoints=0
    for arm in next(iter(result['results'].values()))['arms']:
        for i,seed in enumerate(SEEDS):
            folder=base/f'{arm.lower()}-seed{seed}'
            if load(folder/'RESULT.json')['status'] != 'COMPLETE': raise ValueError('unfinished fit')
            if arm!='PRE_ADAPTER':
                t=load(folder/'training.json'); steps+=t['optimizer_updates']; checkpoints+=1
                if not (folder/'adapter/adapter_model.safetensors').is_file(): raise ValueError('missing adapter')
                if 'adapter_change' in t:
                    source=EXP/f'p2-seed{seed}/adapter/adapter_model.safetensors'
                    if sha(source)==sha(folder/'adapter/adapter_model.safetensors'): raise ValueError('no weight update')
                elif t['nonzero_lora_B_tensors']<=0: raise ValueError('zero adapter')
            for split, summary in result['results'].items():
                records=list(map(json.loads,(folder/f'{split}.jsonl').read_text().splitlines()))
                keys=[(r['scene_id'],r['contract_level']) for r in records]
                if len(records)!=240 or len(set(keys))!=240: raise ValueError('missing/duplicate predictions')
                count+=len(records); pairs={}
                for r in records:
                    pairs.setdefault(r['scene_id'],[]).append(r)
                    if r['valid'] and r['eblc_status']!=('UNSAT' if r['guard_violation'] else 'SAT'):
                        raise ValueError('EBLC recorded verdict mismatch')
                if any(len(p)!=2 or {r['contract_level'] for r in p}!={'short','long'} for p in pairs.values()):
                    raise ValueError('unpaired contracts')
                for metric,m in summary['arms'][arm].items():
                    if metric=='contract_swap_pair_accuracy':
                        value=sum(all(r['correct'] for r in p) for p in pairs.values())/len(pairs)
                    else: value=sum(r[FIELDS[metric]] for r in records)/len(records)
                    if not math.isclose(value,m['per_seed'][i],abs_tol=1e-12): raise ValueError('aggregate mismatch')
    if count!=expected_n or steps!=expected_updates: raise ValueError('planned counts mismatch')
    return {'predictions':count,'optimizer_updates':steps,'trained_checkpoints':checkpoints,
            'rows_and_metrics_recomputed':True}


def run(output):
    if output.exists(): raise FileExistsError(output)
    inputs={str(Path(__file__).relative_to(ROOT)):sha(Path(__file__))}; checks={}
    for base in (BASE/'temporal-expansion-protocol-2026-09-29-001',EXP,
                 BASE/'temporal-cost-protocol-2026-09-29-001',COST,SECONDARY):
        checks[base.name]={'verified_hash_entries':audit(base,inputs)}
    exp,cost,secondary=map(lambda p:load(p/'RESULT.json'),(EXP,COST,SECONDARY))
    for r in (exp,cost,secondary):
        if r['status']!='COMPLETE': raise ValueError('unfinished run')
    checks[EXP.name].update(check_predictions(EXP,exp,17280,3240))
    checks[COST.name].update(check_predictions(COST,cost,6480,360))
    for seed in SEEDS:
        a=load(COST/f'ce_only-seed{seed}/training.json'); b=load(COST/f'ce_eblc-seed{seed}/training.json')
        for key in ('optimizer_updates','examples','input_tokens','assistant_tokens','example_order_sha256','trainable_parameters'):
            if a[key]!=b[key]: raise ValueError('unmatched cost training: '+key)
    checks['cost_matched_training']='PASS'
    output.mkdir(parents=True)
    columns=['experiment','split','arm','metric','mean','std_population','seed42','seed17','seed123','ci_low','ci_high']
    with (output/'all_primary_metrics.csv').open('w',newline='') as f:
        w=csv.writer(f); w.writerow(columns)
        for label,result in [('expansion',exp),('cost',cost)]:
            for split,v in result['results'].items():
                for arm,metrics in v['arms'].items():
                    for metric,m in metrics.items():
                        ci=m.get('cluster_95ci',m.get('paired_cluster_95ci'))
                        w.writerow([label,split,arm,metric,m['mean'],m['std_population'],*m['per_seed'],*ci])
    result={'status':'COMPLETE','execution_scope':'EXPANDED_AND_COST_EXPERIMENTS_CLOSED_NOT_ALL_ROAD_MILESTONES',
            'checks':checks,'unique_verified_files':len(inputs),
            'expansion':exp,'cost':cost,'secondary':secondary,
            'remaining':'M20 manuscript integration; not additional training or new reviewer tasks',
            'reporting':'All outcomes retained. No retrospective success relabeling.'}
    report=['# 통제 학습·후속 실험 마감', '',
            '계획한 확장 및 비용 실험의 실행·집계·무결성 점검 완료. 신규 학습/모델 호출 없음.',
            '실행 완료와 가설 지지는 별도다. 원 run과 사전 판정은 변경하지 않았다.', '',
            '- 확장:18 checkpoint,3,240 updates,17,280 predictions(검증 묶음 포함).',
            '- 비용:6 추가 checkpoint,360 updates,6,480 predictions(추가 학습 전3개 모델 평가 포함).',
            '- 추가 지표:같은17,280예측의 사후 분석; 독립 추가 표본으로 세지 않음.',
            '- 모든 예측 파일240행, 계약 쌍·seed별 모든 지표 재집계 일치.',
            '- 비용 양군의 데이터 순서/토큰 수/학습 파라미터/updates 일치, 추가 adapter 원본 대비 hash 변화 확인.',
            f'- 입력/출력 해시:{len(inputs)}개 고유 파일 확인.', '',
            '## 전체 성능 표', '', '모든 값은3seed 평균(%). 표준편차·개별seed·기존 조건부 bootstrap95%CI는 all_primary_metrics.csv에 보존.',
            'CI는 제한된 합성 시간 cluster를 재표집한 값이며 일반 도로/seed 모집단의 불확실성을 대신하지 않는다.', '']
    metrics=('accuracy','guard_violation_rate','safe_goal_completion_rate','contract_swap_pair_accuracy')
    for label,result in [('확장',exp),('비용',cost)]:
        for split,v in result['results'].items():
            report += [f'### {label} / {split}', '', '| 조건 | 정확도 | 위반율 | 준수·목표 달성 | 계약쌍 |', '|---|---:|---:|---:|---:|']
            for arm,m in v['arms'].items(): report.append('| '+arm+' | '+' | '.join(f"{m[k]['mean']*100:.3f}" for k in metrics)+' |')
            report.append('')
    report += ['## 판정과 한계', '',
        '- 확장 원판정 NOT_SUPPORTED: 모든 seed20%p 개선이라는 운영 기준 미달. P2 절대 수준/P1 대비 point 보존은 충족. 결과 공개 gate가 아니다.',
        '- 비용 원판정 INCONCLUSIVE: canonical CE_ONLY 위반0.556%라 요구한2%p 감소의 여지가 없음. 원 기준은 변경하지 않음.',
        '- 비용 canonical: 위반0.556→0%, 정확도99.167→98.333%, 계약쌍98.333→96.667%. 감소한 위반과 감소한 최적 행동 선택을 모두 보고.',
        '- 비용 표현변경: 위반1.806→0.139%, 정확도97.639→96.250%. 미학습시간: 위반1.250→0.139%, 정확도98.611→98.889%.',
        '- 무위반 관측은 위반 확률0의 보장이 아니며 비용학습은 RL/외부 shield가 아님.',
        '- P0는 계약 시간 정보가 없고 P1/P2는 학습·평가 모두 계약 제공. 검증 자체의 인과적 성능 향상 주장이 아님.',
        '- 확장 시험10개, 비용 시험10개 합성 이미지. 파생행을 독립 실제 도로 장면으로 세지 않음.',
        '- 이전72-update 실험 및 D1–D4는 별도 실험이다. D1 일반화 실패와 D4 공유 source 오류24미탐도 원고에서 누락하지 않음.',
        '- 실제 도로 자동 추출/실차 검증/형식적 비열등성 미입증. Studio 설계는 이 실험 마감의 선행조건이 아님.', '',
        '## 남은 작업', '', '실험 실행은 닫고, 기존 및 이번 표·추가 지표·제약 품질·실패 사례를 M20 원고/보충자료에 통합한다.',
        '현재 paper snapshot001/002가 이번 모든 실험을 포함한다고 주장하지 않는다.']
    for path,obj in [(output/'RESULT.json',result)]: path.write_text(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
    (output/'REPORT_KO.md').write_text('\n'.join(report)+'\n')
    manifest={'project_id':'guardsynth-coc','status':'COMPLETE','input_hashes':inputs,
              'output_hashes':{p.name:sha(p) for p in output.iterdir()}}
    (output/'RUN_MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps({'status':'COMPLETE','checks':checks,'verified_files':len(inputs),'output':str(output)}))


if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('--run-id',required=True); args=parser.parse_args()
    import re
    if not re.fullmatch(r'temporal-experiment-closure-\d{4}-\d{2}-\d{2}-\d{3}',args.run_id): parser.error('invalid run ID')
    run(BASE/args.run_id)
