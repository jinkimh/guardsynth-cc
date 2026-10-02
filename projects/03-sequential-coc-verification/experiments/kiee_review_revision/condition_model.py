"""Condition-indexed experimental UPPAAL monitor of authored symbolic frames.

Developed AFTER legacy scenario evaluation; this is an explicitly disclosed
same-case semantic refinement/retest, not a held-out or natural accuracy test.
No legacy model/checker is changed. No text extraction is performed here.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import xml.etree.ElementTree as ET


def encode(frames):
    obligations={}
    for f in frames:
        o=f['obligation']
        if o:
            if o['id'] in obligations and obligations[o['id']]!=o['condition_id']:raise ValueError('Obligation condition changed')
            obligations[o['id']]=o['condition_id']
    ids=list(obligations);conditions=list(obligations.values())
    return {'event_ids':[f['event_id'] for f in frames],'obligation_ids':ids,'conditions':conditions,'actions':[{'STOP':0,'WAIT':1,'GO':2}[f['action']] for f in frames],'new_obligations':[ids.index(f['obligation']['id']) if f['obligation'] else -1 for f in frames],'preconditions':[-1 if f['precondition'] is None else int(f['precondition']) for f in frames],'observations':[next((int(e['value']) for e in f['evidence'] if e['condition_id']==condition),-1) for f in frames for condition in conditions]}


def model_bytes(encoded):
    n=len(encoded['event_ids']);k=len(encoded['obligation_ids'])
    if not n or not k:raise ValueError('Scenario requires events and obligations')
    def arr(values):return '{'+','.join(str(x) for x in values)+'}'
    declaration=f'''// Authored condition-linked frame monitor; experimental revision 1.
const int N = {n};
const int K = {k};
const int actions[N] = {arr(encoded['actions'])};
const int creates[N] = {arr(encoded['new_obligations'])};
const int preconditions[N] = {arr(encoded['preconditions'])};
const int observations[N*K] = {arr(encoded['observations'])};
bool active[K];
int known[K] = {arr([-1]*k)};
int precondition = -1;
int idx = 0;
bool bad = false;
bool missing = false;
bool bad_hold = false;
bool bad_pre = false;
int first_bad_idx = -1;
int first_missing_idx = -1;
int first_bad_obligation = -1;
int first_missing_obligation = -1;
void step() {{
  int j;
  if (creates[idx] >= 0) active[creates[idx]] = true;
  if (preconditions[idx] >= 0) precondition = preconditions[idx];
  for (j = 0; j < K; j++) {{
    if (observations[idx*K+j] >= 0) known[j] = observations[idx*K+j];
    if (active[j] && known[j] == 1) active[j] = false;
  }}
  if (actions[idx] == 2) {{
    if (precondition == 0) {{
      bad = true; bad_pre = true;
      if (first_bad_idx < 0) {{ first_bad_idx = idx; first_bad_obligation = -2; }}
    }}
    for (j = 0; j < K; j++) {{
      if (active[j] && known[j] == 0) {{
        bad = true; bad_hold = true;
        if (first_bad_idx < 0) {{ first_bad_idx = idx; first_bad_obligation = j; }}
      }}
      if (active[j] && known[j] == -1) {{
        missing = true;
        if (first_missing_idx < 0) {{ first_missing_idx = idx; first_missing_obligation = j; }}
      }}
    }}
  }}
}}
'''
    root=ET.Element('nta');ET.SubElement(root,'declaration').text=declaration
    template=ET.SubElement(root,'template');ET.SubElement(template,'name').text='ScenarioObserver'
    loc=ET.SubElement(template,'location',{'id':'run','x':'0','y':'0'});ET.SubElement(loc,'name').text='Run';ET.SubElement(loc,'committed')
    loc=ET.SubElement(template,'location',{'id':'done','x':'200','y':'0'});ET.SubElement(loc,'name').text='Done'
    ET.SubElement(template,'init',{'ref':'run'})
    for target,guard,assignment in [('run','idx < N','step(), idx++'),('done','idx == N',None)]:
        t=ET.SubElement(template,'transition');ET.SubElement(t,'source',{'ref':'run'});ET.SubElement(t,'target',{'ref':target});ET.SubElement(t,'label',{'kind':'guard'}).text=guard
        if assignment:ET.SubElement(t,'label',{'kind':'assignment'}).text=assignment
    ET.SubElement(root,'system').text='Observer = ScenarioObserver(); system Observer;'
    return ET.tostring(root,encoding='utf-8',xml_declaration=True)


def parse_result(output,event_ids,obligation_ids=()):
    statuses=[not x for x in re.findall(r'Formula\s+is\s+(?:(NOT)\s+)?satisfied',output)]
    if len(statuses)!=5 or not statuses[2]:raise ValueError('Missing solver results or incomplete sequence')
    def first_value(name):
        values=[int(x) for x in re.findall(r'\b'+name+r'\s*=\s*(-?\d+)',output)]
        return next((x for x in values if x>=0 or x==-2),None)
    bad_index=first_value('first_bad_idx');missing_index=first_value('first_missing_idx')
    bad_oid=first_value('first_bad_obligation');missing_oid=first_value('first_missing_obligation')
    verdict='CONTRADICTION' if not statuses[0] else 'UNKNOWN' if not statuses[1] else 'CONSISTENT'
    def event(index):return event_ids[index] if index is not None and 0<=index<len(event_ids) else None
    def obligation(index):return 'PRECONDITION' if index==-2 else obligation_ids[index] if index is not None and 0<=index<len(obligation_ids) else None
    reasons=[]
    if statuses[3]:reasons.append('UNRELEASED_OBLIGATION')
    if statuses[4]:reasons.append('PRECONDITION_FALSE')
    if not statuses[1]:reasons.append('RELEASE_EVIDENCE_MISSING')
    return {'verdict':verdict,'first_event_id':event(bad_index) if verdict=='CONTRADICTION' else None,'first_issue_event_id':event(bad_index) if verdict=='CONTRADICTION' else event(missing_index),'obligation_id':obligation(bad_oid if verdict=='CONTRADICTION' else missing_oid),'reasons':reasons,'query_statuses':statuses}


def save(path,obj):path.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')


def run(source,output,verifyta):
    source=source.resolve();output=output.resolve();output.mkdir(parents=True,exist_ok=False)
    cases=json.loads((source/'cases.json').read_text());rows=[]
    queries=['A[] not bad','A[] not missing','A<> Observer.Done','E<> Observer.Done && bad_hold','E<> Observer.Done && bad_pre']
    version=subprocess.run([str(verifyta),'--version'],capture_output=True,text=True,timeout=15)
    for case in cases:
        folder=output/case['case_id'];folder.mkdir();encoded=encode(case['events'])
        model=folder/'model.xml';model.write_bytes(model_bytes(encoded));q=folder/'queries.q';q.write_text('\n'.join(queries)+'\n')
        command=[str(verifyta),'-q','-t1',str(model),str(q)]
        result=subprocess.run(command,capture_output=True,text=True,timeout=120)
        (folder/'stdout.txt').write_text(result.stdout);(folder/'stderr.txt').write_text(result.stderr)
        if result.returncode:raise RuntimeError(f'verifyta failed: {case["case_id"]} ({result.returncode})')
        prediction=parse_result(result.stdout+'\n'+result.stderr,encoded['event_ids'],encoded['obligation_ids'])
        rows.append({'case_id':case['case_id'],'variant':case['variant'],'gap':case['gap'],'expected':case['expected'],'prediction':prediction,'encoded':encoded,'command':command,'returncode':result.returncode})
    save(output/'results.json',rows)
    count=len(rows);positive=[r for r in rows if r['expected']['verdict']=='CONTRADICTION'];issues=[r for r in rows if r['expected']['reason']]
    result={'status':'COMPLETED','case_count':count,'verdict_matches':sum(r['prediction']['verdict']==r['expected']['verdict'] for r in rows),'first_violation_matches':sum(r['prediction']['first_event_id']==r['expected']['first_event_id'] for r in positive),'positive_count':len(positive),'issue_location_matches':sum(r['prediction']['first_issue_event_id']==r['expected']['issue_event_id'] for r in issues),'issue_obligation_matches':sum(r['prediction']['obligation_id']==r['expected']['obligation_id'] for r in issues),'issue_reason_matches':sum(r['expected']['reason'] in r['prediction']['reasons'] for r in issues),'issue_count':len(issues),'evaluation_kind':'POST_BASELINE_DEVELOPMENT_SAME_CASE_RETEST','legacy_implementation_changed':False}
    save(output/'RESULT.json',result)
    save(output/'RUN_MANIFEST.json',{'project_id':'sequential-coc-verification','source_run':str(source),'cases_sha256':hashlib.sha256((source/'cases.json').read_bytes()).hexdigest(),'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'verifyta':str(verifyta),'verifyta_version':(version.stdout or version.stderr).splitlines()[0],'labels_changed':False,'new_independent_sample':False,'conditions':'identifier-linked authored symbolic evidence; no automatic NLP','semantics':'unknown waiting alone is not a problem; unresolved GO is UNKNOWN; false release at GO is CONTRADICTION; all matching obligations independently tracked'})
    (output/'REPORT_KO.md').write_text(f'''# 의무별 조건을 연결한 UPPAAL 보완 모델 재시험

기존 144사례 실행에서 확인한 단일 의무 표현 손실과 대기 중 미상의 누적을 분석한 뒤 별도 모델을 작성했다. 같은 cases.json을 그대로 재사용했으며 정답을 바꾸지 않았다. 따라서 이 결과는 개발 후 동일 사례 재시험이며 독립 일반화 성능이 아니다. 기존 Python/UPPAAL 구현과 최초 결과는 보존했다.

- 의미 판정 일치: {result['verdict_matches']}/{count}.
- 확정 오류 최초 사건 일치: {result['first_violation_matches']}/{len(positive)}.
- 문제 위치 / 관련 의무 / 사유 일치: {result['issue_location_matches']} / {result['issue_obligation_matches']} / {result['issue_reason_matches']} (각 분모 {len(issues)}).
- 실제 verifyta에 의무별 활성 상태, 종료 조건별 증거, 선행조건과 사건 순서를 넣었다. 새 행동 근거 B를 A의 종료 증거로 쓰지 않는다.
- 안전하게 기다리는 동안 종료 여부가 미상인 것과 미상 상태에서 진행하는 것을 구분한다. 복수 의무는 각 종료 조건이 참인 경우에만 해제한다.
- 시나리오가 명시한 상태·조건의 논리 관계를 검사하며 영상에서 실제 상태를 추론하지 않는다. 정량적 시간 제한은 이번 중심 모델에 포함하지 않는다.

각 사례의 XML/query와 stdout/stderr를 보존했다. 이 모델은 기존 논문의 모델에서 이미 지원했던 범위라고 소급하여 기술하면 안 된다. 독립 평가가 아닌 조건 연결 및 오류 추적의 실행 가능한 보완 예시다.
''')
    print(json.dumps(result),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--verifyta',type=Path,required=True)
    a=p.parse_args();run(a.source,a.output,a.verifyta)
