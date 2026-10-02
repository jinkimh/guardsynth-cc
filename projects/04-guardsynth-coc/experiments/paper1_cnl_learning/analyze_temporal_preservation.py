"""Frozen-criterion paired analysis; template clusters, never seed-as-scene power."""
import argparse
import json
from pathlib import Path
import numpy as np
from temporal_preservation import BASE, ROOT, sha

FIELDS={'guard_violation_rate':'guard_violation','safe_goal_completion_rate':'safe_goal_complete',
        'deadlock_rate':'deadlock','accuracy':'correct','coverage':'valid',
        'contract_swap_pair_accuracy':'pair_correct'}


def verify_completed_run(run, protocol):
    manifest=json.loads((run/'RUN_MANIFEST.json').read_text())
    if manifest['status']!='COMPLETE':raise ValueError('training is not complete')
    for base in (run,protocol):
        record=json.loads((base/'RUN_MANIFEST.json').read_text())
        for name,digest in record['output_hashes'].items():
            if sha(base/name)!=digest:raise ValueError('immutable output drift: '+name)
    return manifest


def summarize(run, protocol):
    cfg=json.loads((protocol/'protocol.json').read_text())
    criteria=cfg['criteria'];seeds=cfg['seeds'];arms=cfg['arms']
    stats={};rows={}
    for split in cfg['evaluation']:
        rows[split]={}
        for arm in arms:
            rows[split][arm]=[]
            for seed in seeds:
                path=run/f'{arm.lower()}-seed{seed}'/(split+'.jsonl')
                data=[json.loads(line) for line in path.read_text().splitlines()]
                if len(data)!=2*cfg['test_scenes']:raise ValueError('incomplete evaluation')
                pairs={sid:[r for r in data if r['scene_id']==sid] for sid in {r['scene_id'] for r in data}}
                if any(len(pair)!=2 or len({r['contract_level'] for r in pair})!=2 for pair in pairs.values()):
                    raise ValueError('incomplete counterfactual pair')
                for row in data:
                    row['pair_correct']=all(r['correct'] for r in pairs[row['scene_id']])
                rows[split][arm].extend(dict(r,seed=seed) for r in data)
        # Pair by semantic example identity and model seed; never sort by outcomes.
        identity=lambda r:(r['seed'],r['scene_id'],r['contract_level'])
        for arm in arms:
            if list(map(identity,rows[split][arm]))!=list(map(identity,rows[split]['P0'])):
                raise ValueError('unpaired outcomes')
        clusters=sorted({r['semantic_cluster'] for r in rows[split]['P0']})
        rng=np.random.default_rng(cfg['uncertainty']['seed'])
        draws=rng.integers(0,len(clusters),(cfg['uncertainty']['bootstrap_replicates'],len(clusters)))
        arrays={}
        stats[split]={'unique_semantic_clusters':len(clusters),'arms':{},'paired_differences':{}}
        for arm in arms:
            data=rows[split][arm]
            arrays[arm]={}
            metrics={}
            for metric,field in FIELDS.items():
                # Cluster sums/counts retain multiplicity of generated instances;
                # resample the actual repeated template unit across all paired seeds.
                sums=np.array([sum(r[field] for r in data if r['semantic_cluster']==c) for c in clusters])
                sizes=np.array([sum(r['semantic_cluster']==c for r in data) for c in clusters])
                distribution=sums[draws].sum(1)/sizes[draws].sum(1)
                arrays[arm][metric]=distribution
                metrics[metric]={'estimate':sum(r[field] for r in data)/len(data),
                    'template_cluster_bootstrap_95ci':np.quantile(distribution,[.025,.975]).tolist(),
                    'per_seed':[sum(r[field] for r in data if r['seed']==s)/(2*cfg['test_scenes']) for s in seeds]}
            stats[split]['arms'][arm]=metrics
        for comparator in ('P0','P1'):
            stats[split]['paired_differences']['P2-'+comparator]={m:{
                'estimate':stats[split]['arms']['P2'][m]['estimate']-stats[split]['arms'][comparator][m]['estimate'],
                'template_cluster_bootstrap_95ci':np.quantile(arrays['P2'][m]-arrays[comparator][m],[.025,.975]).tolist()
            } for m in FIELDS}
    verdicts={}
    for split in ('benchmark_regression','new_seed_confirmation'):
        m=stats[split]['arms'];v='guard_violation_rate';s='safe_goal_completion_rate'
        checks={}
        for arm in ('P1','P2'):
            checks[arm+'_level']=all(x<=criteria[arm+'_replication_max_violation' if arm=='P1' else 'P2_max_violation'] for x in m[arm][v]['per_seed']) and all(x>=criteria[arm+'_replication_min_safe_completion' if arm=='P1' else 'P2_min_safe_completion'] for x in m[arm][s]['per_seed'])
        checks['P2_vs_P0']=all(a-b<=criteria['P2_minus_P0_max_violation_difference'] for a,b in zip(m['P2'][v]['per_seed'],m['P0'][v]['per_seed'])) and all(a-b>=criteria['P2_minus_P0_min_safe_completion_difference'] for a,b in zip(m['P2'][s]['per_seed'],m['P0'][s]['per_seed']))
        checks['P2_vs_P1']=all(a-b<=criteria['P2_minus_P1_violation_margin'] for a,b in zip(m['P2'][v]['per_seed'],m['P1'][v]['per_seed'])) and all(a-b>=criteria['P2_minus_P1_safe_completion_margin'] for a,b in zip(m['P2'][s]['per_seed'],m['P1'][s]['per_seed']))
        verdicts[split]={'checks':checks,'point_criteria':'SUPPORTED_ON_REUSED_TEMPLATES' if all(checks.values()) else 'NOT_SUPPORTED',
            'formal_noninferiority':'NOT_CLAIMED','fresh_environment_confirmation':'NOT_ESTABLISHED'}
    return {'protocol_id':cfg['protocol_id'],'results':stats,'verdicts':verdicts,
        'limits':['Six unique storyboard images across standard/unseen tasks.',
                  'New seeds reuse templates; uncertainty is conditional on those templates.',
                  'Unnecessary-stop proxy is deadlock; safe completion measures normal goal progress.',
                  'No actual-road or automatic source-extraction inference.']}


def report(result, run):
    lines=['# 통제 temporal 효과 보존 비교', '',
           '- project_id: `guardsynth-coc`',
           '- protocol: `paper1-method-preservation-v0.1`',
           '- Project01 generator/시각 collator/LoRA trainer를 읽기 전용으로 재사용한 신규 Project04 결과.',
           '- P1/P2는 학습·추론 모두 CoC 안에 제약을 제공한다. 실제 도로 자동 추출/무제약 추론 시험이 아니다.',
           '- 기존 benchmark와 새 seed 표본 모두 반복 template 평가이며 독립 새 환경으로 세지 않는다.', '']
    updates=[]
    for path in sorted(run.glob('*/training.json')):
        value=json.loads(path.read_text())
        updates.append(value['updates'])
    lines.append(f'실제 checkpoint {len(updates)}개, optimizer updates 합계 {sum(updates)}. 각 adapter/loss/raw prediction은 학습 run에 보존된다.')
    for split,stats in result['results'].items():
        lines.extend(['',f'## {split}', '',
            f"고유 semantic template clusters: {stats['unique_semantic_clusters']}. 각 seed/arm 48 생성 장면·96 판단; seed를 독립 환경으로 세지 않는다.", '',
            '| 조건 | 위반 | 안전 완료 | 불필요 정지(deadlock) | 정확도 | coverage | 계약쌍 정확도 |',
            '|---|---:|---:|---:|---:|---:|---:|'])
        order=['guard_violation_rate','safe_goal_completion_rate','deadlock_rate','accuracy','coverage','contract_swap_pair_accuracy']
        for arm,metrics in stats['arms'].items():
            lines.append('| '+arm+' | '+' | '.join(f"{metrics[m]['estimate']:.4f}" for m in order)+' |')
        lines.extend(['', 'P2의 paired 차이와 template-cluster bootstrap 95% 구간:'])
        for comparison,metrics in stats['paired_differences'].items():
            for m in ('guard_violation_rate','safe_goal_completion_rate'):
                x=metrics[m];ci=x['template_cluster_bootstrap_95ci']
                lines.append(f"- {comparison} {m}: {x['estimate']:.4f} [{ci[0]:.4f}, {ci[1]:.4f}]")
        if split in result['verdicts']:
            verdict=result['verdicts'][split]
            lines.extend(['',f"사전 고정 point criteria: **{verdict['point_criteria']}**.",
                          '각 seed별 P1/P2 수준, P2-P0 개선, P2-P1 허용 열화를 모두 검사했다.',
                          'formal 비열등성/동등성 또는 새로운 시각 환경 일반화는 입증하지 않았다.'])
    lines.extend(['','## 해석 한계','',
        '표준3·unseen3의 총6 storyboard만 존재한다. 좁은 template 재사용 연구이며 CI도 이 조건부 범위다.',
        'CoC 원문과 정답은 변경하지 않았다. 제약은 supplied source duration에서 생성하며 ACTION 정답에서 역생성하지 않았다.',
        'Core는 한 번의 clear 전환 아래 진입 시간 허용성을 검증한다. 전체 차량 운동/재점유/시각 grounding을 인증하지 않는다.',
        '원 Project01 평균 .319/.000 위반 및 .681/1.000 안전 완료는 역사적 참조이며 이 신규 결과로 재표기하지 않는다.',
        '원 unseen-time .625/.649 안전 완료 한계는 보존한다. 새 unseen 결과와 별도로 해석한다.',
        '본 run에는 LLM 확장 라벨/추가 인간 설문이 없으며 실제 도로 gate나 원답을 변경하지 않았다.'])
    return '\n'.join(lines)+'\n'

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--run-id',required=True);p.add_argument('--protocol-id',required=True)
    p.add_argument('--analysis-id',required=True);a=p.parse_args()
    run=BASE/a.run_id;protocol=BASE/a.protocol_id;out=BASE/a.analysis_id
    if out.exists():raise FileExistsError(out)
    verify_completed_run(run,protocol)
    result=summarize(run,protocol)
    from safetensors import safe_open
    checkpoints=[]
    for path in sorted(run.glob('*/adapter/adapter_model.safetensors')):
        with safe_open(path,framework='pt',device='cpu') as tensors:
            keys=list(tensors.keys())
            b_keys=[k for k in keys if 'lora_B' in k]
            nonzero=sum(bool(tensors.get_tensor(k).count_nonzero()) for k in b_keys)
            checkpoints.append({'arm_seed':path.parent.parent.name,'sha256':sha(path),
                'tensor_count':len(keys),'lora_B_count':len(b_keys),'nonzero_lora_B_count':nonzero})
    result['checkpoint_audit']=checkpoints
    if len(checkpoints)!=9 or any(c['nonzero_lora_B_count']!=c['lora_B_count'] for c in checkpoints):
        raise ValueError('missing or untrained adapter')
    out.mkdir()
    (out/'RESULT.json').write_text(json.dumps(result,indent=2)+'\n')
    (out/'REPORT_KO.md').write_text(report(result,run))
    (out/'RUN_MANIFEST.json').write_text(json.dumps({'input_hashes':{
        str(run.relative_to(ROOT)/'RUN_MANIFEST.json'):sha(run/'RUN_MANIFEST.json'),
        str(protocol.relative_to(ROOT)/'protocol.json'):sha(protocol/'protocol.json'),
        str(Path(__file__).relative_to(ROOT)):sha(Path(__file__))},'output_hashes':{
            name:sha(out/name) for name in ('RESULT.json','REPORT_KO.md')}},indent=2)+'\n')
    print(json.dumps(result['verdicts'],indent=2))
