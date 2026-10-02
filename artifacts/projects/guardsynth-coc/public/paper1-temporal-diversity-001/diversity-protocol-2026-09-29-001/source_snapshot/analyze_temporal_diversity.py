"""Prespecified paired diagnostics; no threshold tuning or whole-CoC claims."""
import argparse
from collections import Counter
import json
import numpy as np
import temporal_diversity as d

METRICS=['violation','safe_completion','deadlock','unnecessary_stop','correct','valid','pair_correct']


def estimate(records,metric,config):
    groups=sorted({r['semantic_group'] for r in records})
    grid=np.array([[np.mean([r[metric] for r in records if r['seed']==seed and r['semantic_group']==g])
                    for g in groups] for seed in d.SEEDS])
    if not np.isfinite(grid).all():raise ValueError('unbalanced or incomplete seed/group cell')
    rng=np.random.default_rng(config['analysis']['seed'])
    ns=config['analysis']['bootstrap']
    seeds=rng.integers(0,3,(ns,3));clusters=rng.integers(0,len(groups),(ns,len(groups)))
    values=grid[seeds[:,:,None],clusters[:,None,:]].mean((1,2))
    return {'mean':float(grid.mean()),'paired_seed_group_95ci':np.quantile(values,[.025,.975]).tolist(),
        'per_seed':dict(zip(map(str,d.SEEDS),grid.mean(1).tolist())),'semantic_groups':len(groups)}


def quality_summary(items):
    grouped={}
    for kind in sorted({r['kind'] for r in items}):
        rows=[r for r in items if r['kind']==kind]
        grouped[kind]={'count':len(rows),'detected':sum(not r['accepted_with_verification'] for r in rows),
            'misses':sum(r['injected_error'] and r['accepted_with_verification'] for r in rows),
            'false_rejections':sum(not r['injected_error'] and not r['accepted_with_verification'] for r in rows),
            'layer_detection_counts':{k:sum(r['detection_layers'][k] for r in rows) for k in rows[0]['detection_layers']},
            'internally_SAT_count':sum(r['internal_consistency_SAT'] is True for r in rows)}
    accepted=[r for r in items if r['accepted_with_verification']]
    valid=[r for r in items if not r['injected_error']]
    return {'by_type':grouped,'candidate_count':len(items),'same_candidate_ids_in_both_conditions':True,
        'bypass_accepted':len(items),'verified_accepted':len(accepted),
        'bypass_error_fraction':sum(r['injected_error'] for r in items)/len(items),
        'verified_error_fraction':sum(r['injected_error'] for r in accepted)/len(accepted),
        'valid_acceptance_coverage':sum(r['accepted_with_verification'] for r in valid)/len(valid),
        'overall_acceptance_coverage':len(accepted)/len(items),
        'scope':'BALANCED_INJECTED_ERRORS_NOT_NATURAL_PREVALENCE; SHARED_SOURCE_ERROR_NEGATIVE_CONTROL_OUTSIDE_TRUSTED_SOURCE_ASSUMPTION'}


def analyze(protocol,run):
    d.verify_manifest(protocol);manifest=d.verify_manifest(run)
    if manifest['status']!='COMPLETE':raise ValueError('incomplete inference run')
    cfg=json.loads((protocol/'protocol.json').read_text())
    cases={r['case_id']:r for r in map(json.loads,(protocol/'cases.jsonl').read_text().splitlines())}
    rows=[]
    for arm in d.ARMS:
        for seed in d.SEEDS:
            predicted=[json.loads(line) for line in (run/f'{arm.lower()}-seed{seed}.jsonl').read_text().splitlines()]
            if len(predicted)!=len(cases) or {r['case_id'] for r in predicted}!=set(cases):raise ValueError('case count/identity drift')
            for pred in predicted:
                case=cases[pred['case_id']]
                if pred['input_sha256']!=case['input_sha256'][arm]:raise ValueError('prediction input mismatch')
                score=d.oracle(case,pred['prediction'])
                if score!=pred['source_score']:raise ValueError('independent scorer drift')
                rows.append({**case,**pred,**score})
    by_key={(r['arm'],r['seed'],r['experiment'],r['variant'],r['base_id']):r for r in rows}
    for r in rows:
        pair=[x for x in rows if (x['arm'],x['seed'],x['experiment'],x['variant'],x['pair_id'])==
              (r['arm'],r['seed'],r['experiment'],r['variant'],r['pair_id'])]
        if len(pair)!=2:raise ValueError('counterfactual pair broken')
        r['pair_correct']=all(x['correct'] for x in pair)
        if r['experiment'] in ('D2','D3'):
            control='canonical' if r['experiment']=='D2' else 'original'
            old=by_key[(r['arm'],r['seed'],r['experiment'],control,r['base_id'])]
            r['prediction_changed']=r['prediction']!=old['prediction']
            r['correct_change']=int(r['correct'])-int(old['correct'])
            r['safe_completion_change']=int(r['safe_completion'])-int(old['safe_completion'])
        if r['image_mode']=='swapped':
            implied=d.oracle(r,r['prediction'],r['implied_clear_ms'])
            r['image_implied_correct']=implied['correct'];r['image_implied_violation']=implied['violation']
    results={}
    for experiment,variant in sorted({(r['experiment'],r['variant']) for r in rows}):
        group=[r for r in rows if (r['experiment'],r['variant'])==(experiment,variant)]
        key=experiment+'/'+variant;results[key]={'arms':{},'P2_minus_P1':{}}
        metrics=METRICS+(['prediction_changed','correct_change','safe_completion_change'] if experiment in ('D2','D3') else [])
        if variant=='swapped':metrics+=['image_implied_correct','image_implied_violation']
        for arm in d.ARMS:
            subset=[r for r in group if r['arm']==arm]
            results[key]['arms'][arm]={m:estimate(subset,m,cfg) for m in metrics}
        paired=[]
        for r in group:
            if r['arm']!='P2':continue
            p1=by_key[('P1',r['seed'],experiment,variant,r['base_id'])]
            paired.append({**r,**{m:float(r[m])-float(p1[m]) for m in METRICS}})
        results[key]['P2_minus_P1']={m:estimate(paired,m,cfg) for m in METRICS}
    quality=quality_summary(json.loads((protocol/'constraint_quality.json').read_text()))
    core_valid=[r for r in rows if r['valid']]
    return {'protocol_id':cfg['protocol_id'],'results':results,'D4':quality,
        'prediction_rows':len(rows),'valid_core_executions':len(core_valid),
        'core_oracle_disagreements':sum(not r['core_execution']['oracle_agreement'] for r in core_valid),
        'training_updates':0,'claim_scope':'POST_PRIMARY_EXPLORATORY_DIAGNOSTICS',
        'limits':['Only three independent semantic parameter groups per stratum and three model seeds.',
          'Label rotations and repeated P0 paraphrase inputs are not independent cases.',
          'Blank and source-image-conflict metrics retain diagnostic references, not road error rates.',
          'Schema/source correspondence/Core-oracle/CNL checks have distinct claims; SAT alone cannot reject consistent wrong sources.']}


def report(result):
    lines=['# D1–D4 후속 진단 결과','',
      '기존9개 adapter 재사용, 신규 학습0. 기존 주 실험 결과 이후 설계·별도 동결한 탐색적 후속 진단이다.',
      '모델 선택을 Core에 바인딩해 실행하고 독립 환경 규칙과 대조했다. 모델 예측은 참조 정답이 아니다.','',
      '| 묶음 | arm | 위반 | 안전 완료 | 정확도 | 불필요 정지 | coverage | 입력 개입 후 선택 변화 |',
      '|---|---|---:|---:|---:|---:|---:|---:|']
    for group,item in result['results'].items():
        for arm,m in item['arms'].items():
            nums=[m[k]['mean'] for k in ['violation','safe_completion','correct','unnecessary_stop','valid']]
            change=f"{m['prediction_changed']['mean']:.4f}" if 'prediction_changed' in m else '—'
            lines.append('| '+group+' | '+arm+' | '+' | '.join(f'{x:.4f}' for x in nums)+' | '+change+' |')
    lines.extend(['','## D4: 제약 품질','',
        '| 주입 종류 | 수 | 탐지 | 미탐 | 정상 오탐 | 내부 SAT |','|---|---:|---:|---:|---:|---:|'])
    for kind,r in result['D4']['by_type'].items():
        lines.append(f"| {kind} | {r['count']} | {r['detected']} | {r['misses']} | {r['false_rejections']} | {r['internally_SAT_count']} |")
    q=result['D4'];lines.extend(['',f"동일 후보 {q['candidate_count']}개: 검증 생략 수용{q['bypass_accepted']}, 검증 후 수용{q['verified_accepted']}; 정상 계약 수용률{q['valid_acceptance_coverage']:.3f}.",
        'shared_source_error는 source 자체와 계약을 함께 잘못 바꾼 부정 대조다. 신뢰한 source의 오류는 미탐으로 보존하며 SAT 탐지로 쓰지 않는다.',
        '이 비율은 사전 균형 주입 구성의 결과이며 자연 발생 오류율·CoC 전체 사실성·모델 성능 개선을 뜻하지 않는다.',
        '', '모든 per-seed 수치와 paired seed/semantic-group bootstrap95%CI는 RESULT.json에 보존했다.',
        '단3개 semantic parameter groups/묶음의 제한적 불확실성이다. D3 결측/모순은 실제 도로 정확도와 분리한다.'])
    return '\n'.join(lines)+'\n'

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--protocol-id',required=True);p.add_argument('--run-id',required=True)
    p.add_argument('--analysis-id',required=True);a=p.parse_args()
    protocol=d.BASE/a.protocol_id;run=d.BASE/a.run_id;out=d.BASE/a.analysis_id
    if out.exists():raise FileExistsError(out)
    result=analyze(protocol,run);out.mkdir()
    d.dump(out/'RESULT.json',result);(out/'REPORT_KO.md').write_text(report(result))
    d.dump(out/'RUN_MANIFEST.json',{'project_id':'guardsynth-coc','input_hashes':{
        str(protocol/'RUN_MANIFEST.json'):d.primary.sha(protocol/'RUN_MANIFEST.json'),
        str(run/'RUN_MANIFEST.json'):d.primary.sha(run/'RUN_MANIFEST.json')},
        'output_hashes':{p.name:d.primary.sha(p) for p in out.iterdir() if p.is_file()}})
    print(json.dumps({'rows':result['prediction_rows'],'core_disagreements':result['core_oracle_disagreements'],'D4':result['D4']},indent=2))
