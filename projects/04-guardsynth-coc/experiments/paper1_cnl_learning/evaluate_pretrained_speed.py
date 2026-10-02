"""Apply the existing scorer to immutable baseline predictions and the pre-result clip split."""
import argparse
from collections import Counter
import json
from pathlib import Path
import re

import run_real_development as real
from score_speed_development import score


def execute(baseline, output):
    if output.exists():raise FileExistsError(output)
    hashes={}
    def read(run,name,jsonl=False):
        manifest=json.loads((run/'RUN_MANIFEST.json').read_text());path=run/name
        if real.digest(path)!=manifest['output_hashes'][name]:raise ValueError('immutable evidence drift '+str(path))
        hashes[str(path.relative_to(real.ROOT))]=real.digest(path)
        return [json.loads(s) for s in path.read_text().splitlines()] if jsonl else json.loads(path.read_text())
    predictions=read(baseline,'predictions.jsonl',True)
    protocol=read(baseline,'protocol_lock.json')
    prior=real.BASE/'m18-cohort-feasibility-2026-09-29-001'
    split=read(prior,'exploratory_split_lock.json')
    score_path=Path(__file__).with_name('score_speed_development.py')
    prior_manifest=json.loads((prior/'RUN_MANIFEST.json').read_text())
    if real.digest(score_path)!=prior_manifest['code_hashes'][str(score_path.relative_to(real.ROOT))]:
        raise ValueError('scorer changed after original protocol lock')
    targets=read(real.READINESS/'speed-action-intake-2026-09-29-001','development_action_targets.jsonl',True)
    if [p['sample_id'] for p in predictions]!=[r['sample_id'] for r in split['records']]:
        raise ValueError('original denominator/order changed')
    partition={r['sample_id']:r['partition'] for r in split['records']}
    results={'all_development':score(targets,predictions)}
    for name in ('train','evaluation'):
        selected={sample for sample,part in partition.items() if part==name}
        results[name]=score([r for r in targets if r['sample_id'] in selected],
                            [r for r in predictions if r['sample_id'] in selected])
    for result in results.values():
        for row in result['rows']:row['partition']=partition[row['sample_id']]
    # The primary model snapshot was already pinned during the real launch; verify it again.
    smoke=json.loads((real.BASE/'real-development-smoke-2026-09-29-001/RUN_MANIFEST.json').read_text())
    for filename,expected in smoke['model_file_hashes'].items():
        if real.digest(Path(filename))!=expected:raise ValueError('pinned base model drift')
    result={'label':'PRETRAINED_DEVELOPMENT_BASELINE','model_revision':protocol['revision'],
        'optimizer_updates':0,'trained_L0':False,'fresh_main_test':False,'improvement_claim':False,
        'scores':results,'action_counts':dict(Counter(p['action'] for p in predictions)),
        'total_inference_seconds':sum(p['seconds'] for p in predictions),
        'source_CNL_inference_visible':False,'no_test_tuning':True,
        'single_reviewer_reference':True,'inter_rater_reliability':'NOT_MEASURED_SINGLE_REVIEWER',
        'model_files_reverified':len(smoke['model_file_hashes']),
        'prior_smoke_manifest_sha256':real.digest(real.BASE/'real-development-smoke-2026-09-29-001/RUN_MANIFEST.json')}
    output.mkdir(parents=True,exist_ok=False,mode=0o700)
    (output/'RESULT.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    lines=['# 사전학습 Qwen 개발 baseline\n',
        '고정 프롬프트·인과 프레임133개/19장면, 추가 학습0. 기존17clip 개발 분할을 유지했다. '
        'train/evaluation 표기는 기존 분할의 위치이며 이번 모델은 어느 행으로도 학습하지 않았다. '
        '노출 개발 자료이므로 새 독립 main test, trained L0, 방법 개선 효과가 아니다.\n',
        '|분할|장면|clip|출력 coverage|부적절 선택 참조율|정상 진행 참조율|불필요 정지 참조율|',
        '|---|---:|---:|---:|---|---|---|']
    for name,res in results.items():
        rates=[]
        for key in ('reference_inappropriate','normal_progress_reference','unnecessary_stop_reference'):
            m=res['metrics'][key];rates.append(f"{m['numerator']}/{m['denominator']} (95% clip CI {m['clip_bootstrap_95_percentile']})")
        lines.append(f"|{name}|{res['scene_denominator']}|{res['clip_groups']}|{res['valid_output_count']}/{res['scene_denominator']}|"+'|'.join(rates)+'|')
    lines.append('\n부적절 선택은 실제 안전 위반 정답이 아니다. safety violation/physical completion은 NOT_EVALUATED. '
        '세 scope mask와 판단불가를 보존하며 clip bootstrap은 검토자 편향이나 main power를 해결하지 않는다. '
        '장면별 예측·독립 참조 대응·분할·분모는 RESULT.json에 보존한다.\n')
    (output/'REPORT_KO.md').write_text('\n'.join(lines))
    (output/'RUN_MANIFEST.json').write_text(json.dumps({'project_id':'guardsynth-coc','run_id':output.name,
        'status':'COMPLETE','input_hashes':hashes,'scorer_sha256':real.digest(score_path),
        'code_sha256':real.digest(Path(__file__)),
        'output_hashes':{p.name:real.digest(p) for p in output.iterdir()}},indent=2)+'\n')
    return {k:{'scene_count':v['scene_denominator'],'metrics':v['metrics']} for k,v in results.items()}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--baseline-run-id',required=True)
    p.add_argument('--run-id',required=True);a=p.parse_args()
    if any(not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*-[0-9]+',s) for s in (a.run_id,a.baseline_run_id)):
        p.error('invalid run id')
    print(json.dumps(execute(real.BASE/a.baseline_run_id,real.BASE/a.run_id),indent=2))
