"""Authored scenario feasibility evaluation, not natural-error accuracy.

Expected semantic labels are declared by variant before any detector is run.
Frames and spans are authored alongside text, not extracted by a learned parser.
Legacy implementations are imported without changes. A separately coded FSM is
an executable comparator, not an independent human oracle.
"""
from __future__ import annotations
import argparse
from collections import Counter
from dataclasses import asdict
import hashlib
import html
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT=next(p for p in Path(__file__).resolve().parents if (p/'PROJECT_REGISTRY.json').is_file())
sys.path.insert(0,str(ROOT))
from experiments.sequential_coc.contract_ir import Action,ContractEvent
from experiments.sequential_coc.contract_compiler import compile_text
from experiments.sequential_coc.stateful_checker import check_stateful,transition_table_sha256
from experiments.sequential_coc.event_local_checker import check_event_local
from experiments.sequential_coc.uppaal_generator import build_uppaal_model,write_uppaal_artifacts
from experiments.sequential_coc.run_uppaal import run_verifyta,last_verifyta_run_metadata

FAMILIES=(
 ('pedestrian','pedestrian','the pedestrian has passed','The pedestrian is still crossing.'),
 ('cyclist','cyclist','the cyclist has cleared the crossing','The cyclist is still crossing.'),
 ('lead_vehicle','lead vehicle','the lead vehicle has moved clear','The lead vehicle still blocks the lane.'),
 ('cross_traffic','cross traffic','cross traffic has cleared the intersection','Cross traffic still occupies the intersection.'),
 ('bus','bus','the bus has cleared the lane','The bus still blocks the lane.'),
 ('obstacle','obstacle','the obstacle has been removed','The obstacle still blocks the lane.'),
)
EXPECTED={
 'held_local_conflict':('CONTRADICTION','UNRELEASED_OBLIGATION','A'),
 'held_memory_conflict':('CONTRADICTION','UNRELEASED_OBLIGATION','A'),
 'released_normal':('CONSISTENT',None,None),
 'missing_release':('UNKNOWN','RELEASE_EVIDENCE_MISSING','A'),
 'wrong_release':('UNKNOWN','RELEASE_EVIDENCE_MISSING','A'),
 'order_violation':('CONTRADICTION','PRECONDITION_FALSE','PRECONDITION'),
 'multi_partial':('CONTRADICTION','UNRELEASED_OBLIGATION','C'),
 'multi_all_released':('CONSISTENT',None,None),
}

def span(text,quote,role):
    start=text.index(quote)
    return {'start':start,'end':start+len(quote),'quote':quote,'role':role}


def build_cases():
    cases=[]
    for family,target,release,blocked in FAMILIES:
        for variant,(verdict,reason,oid) in EXPECTED.items():
            for gap in (0,2,6):
                cid=f'{family}-{variant}-gap{gap}'
                events=[]
                def add(text,action,obligation=None,evidence=(),precondition=None,precondition_quote=None):
                    eid=f'{cid}:e{len(events)}'
                    quotes=[span(text,{'STOP':'Stop','GO':'Proceed','WAIT':'Maintain speed'}[action],'action')]
                    if obligation:quotes.append(span(text,obligation['quote'],'obligation'))
                    for item in evidence:quotes.append(span(text,item['quote'],'evidence:'+item['condition_id']))
                    if precondition_quote:quotes.append(span(text,precondition_quote,'precondition'))
                    events.append({'event_id':eid,'timestamp_us':len(events)*1000000,'text':text,'action':action,'obligation':obligation,'evidence':list(evidence),'precondition':precondition,'source_spans':quotes})
                initial=f'Stop until {release}. The required mirror check has been completed.'
                evidence=[]
                if variant=='held_memory_conflict':
                    quote=f'Throughout this recorded interval: {blocked}'
                    initial+=' '+quote
                    evidence=[{'condition_id':'A','value':False,'quote':quote,'scope':'WHOLE_RECORDED_INTERVAL'}]
                add(initial,'STOP',{'id':'A','target':target,'condition_id':'A','condition':release,'quote':f'Stop until {release}'},evidence,True,'The required mirror check has been completed.')
                if variant.startswith('multi_'):
                    add('Stop until the other crossing is clear.','STOP',{'id':'C','target':'other crossing','condition_id':'C','condition':'the other crossing is clear','quote':'Stop until the other crossing is clear'})
                for _ in range(gap):add('Maintain speed. The road surface is dry.','WAIT')
                b='The traffic signal is green.'
                final=b+' Proceed.'
                ev=[{'condition_id':'B','value':True,'quote':b}]
                pre=None;prequote=None
                if variant=='held_local_conflict':
                    final=blocked+' '+final
                    ev.insert(0,{'condition_id':'A','value':False,'quote':blocked})
                elif variant in ('released_normal','order_violation','multi_partial','multi_all_released'):
                    quote=release[0].upper()+release[1:]+'.'
                    final=quote+' '+final
                    ev.insert(0,{'condition_id':'A','value':True,'quote':quote})
                elif variant=='wrong_release':
                    quote='A different object has cleared another crossing.'
                    final=quote+' '+final
                    ev.insert(0,{'condition_id':'OTHER','value':True,'quote':quote})
                if variant.startswith('multi_'):
                    value=variant=='multi_all_released'
                    quote='The other crossing is clear.' if value else 'The other crossing is still blocked.'
                    final=quote+' '+final
                    ev.append({'condition_id':'C','value':value,'quote':quote})
                if variant=='order_violation':
                    pre=False;prequote='The required mirror check has not been completed.'
                    final=prequote+' '+final
                add(final,'GO',evidence=ev,precondition=pre,precondition_quote=prequote)
                expected={'verdict':verdict,'reason':reason,'obligation_id':oid,'first_event_id':events[-1]['event_id'] if verdict=='CONTRADICTION' else None,'issue_event_id':events[-1]['event_id'] if reason else None}
                cases.append({'case_id':cid,'family':family,'variant':variant,'gap':gap,'scope':'MULTI_OBLIGATION_CHALLENGE' if variant.startswith('multi_') else 'SINGLE_OBLIGATION','source_kind':'AUTHORED_SYNTHETIC_NOT_NATURAL','events':events,'expected':expected})
    return cases


def project_frames(case):
    """Project authored condition-linked evidence onto legacy single-obligation IR.

    Only condition A can be represented as the primary release channel; retain
    extra STOP events so legacy overlap is observed. Never assign B/OTHER to A.
    Projection loss is recorded, never silently counted as extraction success.
    """
    primary=case['events'][0]['obligation'];events=[];links=[]
    for frame in case['events']:
        obligation=frame['obligation']
        condition=obligation['condition_id'] if obligation else primary['condition_id']
        evidence=next((e for e in frame['evidence'] if e['condition_id']==condition),None)
        pre=frame['precondition']
        events.append(ContractEvent(scene_id=case['case_id'],event_id=frame['event_id'],timestamp_us=frame['timestamp_us'],action={'STOP':Action.STOP_OR_HOLD,'WAIT':Action.MAINTAIN_SPEED,'GO':Action.ACCELERATE_OR_PROCEED}[frame['action']],target=obligation['target'] if obligation else primary['target'],satisfaction_known=pre is not None,satisfaction_value=bool(pre),release_known=evidence is not None,release_value=bool(evidence['value']) if evidence else False,provenance='AUTHORED_CONDITION_LINKED_FRAME',parse_status='PARSED',source_text=frame['text'],release_condition=obligation['condition'] if obligation else primary['condition']))
        links.append({'event_id':frame['event_id'],'bound_condition':condition,'bound_release_evidence':evidence,'ignored_nonrelease_evidence':[e for e in frame['evidence'] if e['condition_id'] not in ('A','C')],'unrepresentable_conditions':[e['condition_id'] for e in frame['evidence'] if e['condition_id']=='C' and condition!='C'],'source_spans':frame['source_spans']})
    return events,links


def check_fsm(frames):
    """Straightforward condition-ID dictionary monitor; no legacy checker calls.

    Unknown release is actionable at GO, not merely while safely waiting.
    Explicit interval-scoped evidence may persist. Scenarios do not assert
    indefinite real-world persistence of observations.
    """
    active={};known={};sources={};issues=[];trace=[];pre=None;pre_source=None
    for f in frames:
        o=f['obligation']
        if o:active[o['id']]={**o,'origin_event_id':f['event_id']}
        for e in f['evidence']:
            known[e['condition_id']]=e['value'];sources[e['condition_id']]={'event_id':f['event_id'],'quote':e['quote']}
        if f['precondition'] is not None:pre=f['precondition'];pre_source=f['event_id']
        released=[]
        for oid,o in list(active.items()):
            if known.get(o['condition_id']) is True:released.append(oid);del active[oid]
        if f['action']=='GO':
            if pre is False:issues.append({'event_id':f['event_id'],'obligation_id':'PRECONDITION','reason':'PRECONDITION_FALSE','severity':'CONTRADICTION','evidence':{'event_id':pre_source}})
            for oid,o in active.items():
                value=known.get(o['condition_id'])
                issues.append({'event_id':f['event_id'],'obligation_id':oid,'origin_event_id':o['origin_event_id'],'condition_id':o['condition_id'],'reason':'UNRELEASED_OBLIGATION' if value is False else 'RELEASE_EVIDENCE_MISSING','severity':'CONTRADICTION' if value is False else 'UNKNOWN','evidence':sources.get(o['condition_id'])})
        trace.append({'event_id':f['event_id'],'active_after':list(active),'released':released,'known_conditions':dict(known),'evidence_sources':dict(sources)})
    contradictions=[i for i in issues if i['severity']=='CONTRADICTION']
    return {'verdict':'CONTRADICTION' if contradictions else 'UNKNOWN' if issues else 'CONSISTENT','first_event_id':contradictions[0]['event_id'] if contradictions else None,'issues':issues,'trace':trace}


def summarize(rows):
    labels=('CONTRADICTION','CONSISTENT','UNKNOWN','NOT_APPLICABLE')
    matrix={a:{b:0 for b in labels} for a in labels}
    for r in rows:matrix[r['expected']][r['predicted']]+=1
    positive=sum(matrix['CONTRADICTION'].values());normal=sum(matrix['CONSISTENT'].values())
    tp=matrix['CONTRADICTION']['CONTRADICTION'];fp=sum(matrix[a]['CONTRADICTION'] for a in labels if a!='CONTRADICTION')
    return {'count':len(rows),'three_class_correct':sum(matrix[a][a] for a in labels),'confusion_matrix':matrix,'recall_all_positive':tp/positive if positive else None,'positive_abstentions':matrix['CONTRADICTION']['UNKNOWN']+matrix['CONTRADICTION']['NOT_APPLICABLE'],'normal_false_alarm_rate':matrix['CONSISTENT']['CONTRADICTION']/normal if normal else None,'precision_flagged':tp/(tp+fp) if tp+fp else None,'unresolved_count':sum(matrix[a]['UNKNOWN']+matrix[a]['NOT_APPLICABLE'] for a in labels),'uncertainty_interval':'NOT_ESTIMATED_DETERMINISTIC_AUTHORED_FACTORIAL_CASES'}


def save(path,obj):path.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def window_check(events,n):
    results=[check_stateful(events[max(0,i-n):i+1]).to_dict() for i in range(len(events))]
    violations=[r for r in results if r['verdict']=='CONTRADICTION']
    unknown=[r for r in results if r['verdict']=='UNKNOWN']
    first=min((r['first_event_id'] for r in violations),key=lambda eid:next(i for i,e in enumerate(events) if e.event_id==eid)) if violations else None
    return {'verdict':'CONTRADICTION' if violations else 'UNKNOWN' if unknown else 'CONSISTENT','first_event_id':first,'window_results':results}


def build_trace_html(cases,records):
    parts=['<!doctype html><html lang="ko"><meta charset="utf-8"><title>CoC 통제 시나리오 추적</title><style>body{font:15px/1.6 sans-serif;max-width:1200px;margin:auto;padding:24px}article{border-top:2px solid #345;margin-top:35px}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#f5f5f5;padding:12px}table{border-collapse:collapse}td,th{border:1px solid #bbb;padding:6px}</style><h1>의무·해제 근거와 행동 전환: 통제 시나리오</h1><p>설계자 작성 합성 사례입니다. 자연 발생 오류·독립 사람 정답 평가가 아닙니다. 프레임은 원문과 함께 작성했으며 자동 추출 성공을 뜻하지 않습니다.</p>']
    for case,rec in zip(cases,records):
        parts.append('<article><h2>'+html.escape(case['case_id'])+'</h2><p>명세 기대: '+case['expected']['verdict']+' / 범위: '+case['scope']+'</p><ol>')
        for e in case['events']:parts.append('<li><b>'+html.escape(e['event_id'])+'</b>: '+html.escape(e['text'])+'</li>')
        parts.append('</ol><table><tr><th>경로</th><th>판정</th><th>최초 위반</th></tr>')
        for name,r in rec['predictions'].items():parts.append('<tr><td>'+name+'</td><td>'+r['verdict']+'</td><td>'+html.escape(str(r.get('first_event_id')))+'</td></tr>')
        parts.append('</table><details><summary>의무 발생→조건 증거→행동 전환 추적</summary><pre>'+html.escape(json.dumps({'semantic_trace':rec['predictions']['fsm']['trace'],'semantic_issues':rec['predictions']['fsm']['issues'],'projection_links':rec['projection_links'],'legacy_state_trace':rec['predictions']['legacy_full']['state_trace']},ensure_ascii=False,indent=2))+'</pre></details></article>')
    return ''.join(parts)+'</html>'


def run(output,verifyta):
    output=output.resolve();output.mkdir(parents=True,exist_ok=False)
    start=time.time();cases=build_cases()
    save(output/'cases.json',cases)
    # Persist labels and input bytes BEFORE invoking any detector.
    frozen_hash=sha(output/'cases.json')
    manifest={'project_id':'sequential-coc-verification','source_kind':'AUTHORED_SYNTHETIC','human_gold':False,'independent_external_evaluation':False,'case_count':len(cases),'family_count':6,'gap_values':[0,2,6],'cases_sha256':frozen_hash,'transition_contract_sha256':transition_table_sha256(),'script_sha256':sha(Path(__file__)),'source_root':str(ROOT),'expected_label_policy':'FIXED_BY_VARIANT_BEFORE_EXECUTION_NO_FILTERING','claims':'SCENARIO_FEASIBILITY_TRACEABILITY_AND_IMPLEMENTATION_AGREEMENT_ONLY','verifyta':str(verifyta)}
    save(output/'RUN_MANIFEST.json',manifest)
    records=[];solver_errors=[]
    for i,case in enumerate(cases):
        events,links=project_frames(case)
        predictions={'legacy_full':check_stateful(events).to_dict(),'legacy_local':check_event_local(events).to_dict(),'fsm':check_fsm(case['events'])}
        for n in (1,3,5):predictions[f'previous_{n}']=window_check(events,n)
        auto=[];mapping={}
        for f in case['events']:
            parsed=compile_text(f['text'],f['event_id'],case['case_id'],f['timestamp_us'])
            for e in parsed:mapping[e.event_id]=f['event_id']
            auto.extend(parsed)
        raw=check_stateful(auto).to_dict() if auto else {'verdict':'NOT_APPLICABLE','first_event_id':None}
        if raw.get('first_event_id'):raw['first_event_id']=mapping[raw['first_event_id']]
        raw['compiled_event_count']=len(auto)
        raw['events']=[e.to_dict(include_text=True) for e in auto]
        predictions['legacy_auto_text']=raw
        modeldir=output/'uppaal'/case['case_id']
        tree,queries=build_uppaal_model(events)
        model=modeldir/'model.xml';query=modeldir/'queries.q'
        write_uppaal_artifacts(tree,queries,model,query)
        result=run_verifyta(model,query,verifyta)
        meta=last_verifyta_run_metadata()
        # Preserve raw solver evidence by executing the same command once more;
        # record it separately, never present the rerun as the parsed first run.
        if meta and meta.returncode==0:
            rawrun=subprocess.run(list(meta.command),capture_output=True,text=True,timeout=120)
            (modeldir/'verifyta_stdout.txt').write_text(rawrun.stdout)
            (modeldir/'verifyta_stderr.txt').write_text(rawrun.stderr)
            save(modeldir/'run_metadata.json',{'parsed_run':asdict(meta),'raw_evidence_rerun_returncode':rawrun.returncode})
            if rawrun.returncode:solver_errors.append({'case_id':case['case_id'],'reason':'RAW_EVIDENCE_RERUN_FAILED'})
        else:solver_errors.append({'case_id':case['case_id'],'reason':result.to_dict()})
        predictions['uppaal']=result.to_dict()
        record={'case_id':case['case_id'],'family':case['family'],'variant':case['variant'],'gap':case['gap'],'scope':case['scope'],'expected':case['expected'],'structured_events':[e.to_dict(include_text=True) for e in events],'projection_links':links,'predictions':predictions,'uppaal_run':asdict(meta) if meta else None}
        records.append(record)
        with (output/'results.jsonl').open('a') as f:f.write(json.dumps(record,ensure_ascii=False)+'\n')
        if (i+1)%24==0:print(f'Completed {i+1}/{len(cases)} scenarios',flush=True)
    assert sha(output/'cases.json')==frozen_hash
    methods=list(records[0]['predictions'])
    scores={}
    for name in methods:
        rows=[{'expected':r['expected']['verdict'],'predicted':r['predictions'][name]['verdict']} for r in records]
        scores[name]=summarize(rows)
        for dimension in ('variant','gap','scope'):
            scores[name]['by_'+dimension]={str(value):summarize([row for r,row in zip(records,rows) if r[dimension]==value]) for value in sorted({r[dimension] for r in records})}
        positive=[r for r in records if r['expected']['first_event_id']]
        scores[name]['first_violation_exact']={'correct':sum(r['predictions'][name].get('first_event_id')==r['expected']['first_event_id'] for r in positive),'denominator':len(positive)}
    comparison_fields=('verdict','contradiction_types','first_event_id','unknown_reasons')
    mismatches=[{'case_id':r['case_id'],'fields':[k for k in comparison_fields if r['predictions']['legacy_full'][k]!=r['predictions']['uppaal'][k]]} for r in records if any(r['predictions']['legacy_full'][k]!=r['predictions']['uppaal'][k] for k in comparison_fields)]
    failures=[{'case_id':r['case_id'],'expected':r['expected'],'actual':r['predictions']['legacy_full']} for r in records if r['expected']['verdict']!=r['predictions']['legacy_full']['verdict']]
    save(output/'scores.json',scores);save(output/'semantic_mismatches.json',failures);save(output/'uppaal_mismatches.json',mismatches)
    save(output/'RESULT.json',{'status':'COMPLETED' if not solver_errors else 'COMPLETED_WITH_SOLVER_ERRORS','case_count':len(cases),'semantic_mismatch_count':len(failures),'python_uppaal_mismatch_count':len(mismatches),'solver_errors':solver_errors,'elapsed_seconds':time.time()-start,'natural_error_accuracy_established':False,'automated_extraction_validated':False})
    (output/'scenario_trace.html').write_text(build_trace_html(cases,records))
    lines=['# 통제 시나리오 실험 결과','', '6개 상황 × 8개 변형 × 중간 사건 0/2/6개 = 144개 조합 시험. 원문과 구조화 프레임은 설계자가 함께 작성했다. 정답은 검사 실행 전에 변형별로 고정했으며 결과에 따른 선별은 하지 않았다. 자연 발생 오류 정확도나 외부 독립 검증이 아니다.','','| 경로 | 3분류 일치 | 확정 오류 recall | 정상 오탐률 | 최초 위반 위치 |','|---|---:|---:|---:|---:|']
    for name,s in scores.items():lines.append(f"| {name} | {s['three_class_correct']}/{s['count']} | {s['recall_all_positive']} | {s['normal_false_alarm_rate']} | {s['first_violation_exact']['correct']}/{s['first_violation_exact']['denominator']} |")
    lines+=['',f'Python–UPPAAL 비교 불일치: {len(mismatches)}/144. solver 오류: {len(solver_errors)}. 비교 항목은 판정, 오류 종류, 최초 위반 ID, 미상 사유이다. 상태 경로 전체의 동등성은 주장하지 않는다.','', '## 해석 범위','', '- `legacy_full`은 원문에서 자동 추출한 것이 아니라 조건 ID를 연결한 작성 프레임의 투영 결과다. 자동 경로는 `legacy_auto_text`다.','- 이전 N 비교는 기존 검사기를 창에 적용한 ablation이며 독립 경쟁 알고리즘이 아니다. `fsm`은 별도 구현한 단순 비교기지만 동일 설계자가 작성했고 외부 정답의 대용이 아니다.','- 복수 요구의 C 해제 정보를 단일 IR이 모두 담지 못하는 경우 projection_links에 손실을 기록한다. 성공한 부분만 성능 분모로 채택하지 않는다.','- 최초 위반 위치 정확도는 모든 의미상 양성을 분모로 삼는다. 미상도 recall 분모에 포함하며 확정 모순으로 합치지 않는다.','- 시나리오 반복은 통계적 독립 표본이 아니므로 모집단 신뢰구간이나 자연 오류율을 산출하지 않는다.','- 자동 원문 경로의 미상과 구조화 경로의 성공을 분리해야 한다. UPPAAL 일치는 동일 의미 규칙의 구현 일치 근거다.','','실패 전수: semantic_mismatches.json. 원문→프레임→IR→판정의 추적: scenario_trace.html. 입력과 기대 판정: cases.json. 실제 XML/query 및 실행 로그: uppaal/.']
    (output/'REPORT_KO.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps({'output':str(output),'case_count':len(cases),'semantic_mismatches':len(failures),'uppaal_mismatches':len(mismatches),'solver_errors':len(solver_errors)},ensure_ascii=False),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--verifyta',type=Path,required=True)
    args=p.parse_args();run(args.output,args.verifyta)
