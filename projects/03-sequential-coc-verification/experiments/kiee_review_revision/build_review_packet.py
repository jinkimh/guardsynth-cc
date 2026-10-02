"""Prepare blinded natural-CoC review inputs; never fabricate gold labels."""
from __future__ import annotations
import argparse
import csv
import hashlib
import html
import json
from pathlib import Path
import random
import sys


def select_scenes(scenes, excluded, count, seed):
    if count <= 0:
        raise ValueError('Sample size must be positive')
    candidates=sorted(sid for sid,events in scenes.items() if sid not in excluded and len(events)>=2)
    return random.Random(seed).sample(candidates,min(count,len(candidates)))


def validate_exposure(rows, scenes):
    ids=[r['scene_id'] for r in rows]
    if len(set(ids)) != len(ids) or set(ids) != set(scenes):
        raise ValueError('Exposure manifest must cover every source scene exactly once')
    for row in rows:
        for field in ('known_trajectory_analysis', 'known_old_review'):
            if row.get(field) not in ('True', 'False'):
                raise ValueError('Exposure flag absent or invalid')
    return {r['scene_id'] for r in rows if r['known_trajectory_analysis']=='True' or r['known_old_review']=='True'}


def render_html(items):
    chunks=['<!doctype html><html lang="ko"><meta charset="utf-8"><title>연속 CoC 독립 검토</title><style>body{font:16px/1.65 sans-serif;max-width:1000px;margin:32px auto;padding:0 20px}article{border-top:2px solid #345;padding:20px 0}td,th{padding:8px;border:1px solid #ddd;vertical-align:top}table{border-collapse:collapse;width:100%}th:first-child{width:80px}p{white-space:pre-wrap}</style><h1>연속 CoC 독립 검토</h1><p>지침을 읽고 reviewer CSV에 판단을 기록하십시오. 정답·검사기 출력은 제공되지 않습니다. 사건의 언급 누락은 실제 사건의 미발생 증거가 아닙니다. 문장 모순 / 일관됨 / 외부 증거 부족 / 문장 모호 / 적용 대상 아님을 구분하십시오.</p>']
    for item in items:
        chunks.append('<article><h2>'+html.escape(item['review_id'])+'</h2><table><tr><th>문장 인덱스</th><th>상대 시간(초)</th><th>CoC 원문</th></tr>')
        for event in item['events']:
            chunks.append(f'<tr><td>{event["event_index"]}</td><td>{event["time_s"]:.3f}</td><td>{html.escape(event["text"])}</td></tr>')
        chunks.append('</table></article>')
    return ''.join(chunks)+'</html>'


def save(path,data):
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')


def write_csv(path,rows,fields):
    with path.open('w',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader();writer.writerows(rows)


def build(root,analysis,output,count=24,seed=20260930):
    root=root.resolve();analysis=analysis.resolve();output=output.resolve()
    output.mkdir(parents=True,exist_ok=False,mode=0o700)
    sys.path.insert(0,str(root))
    from experiments.sequential_coc.extract_windows import load_reasoning_events
    parquet=root/'data/baseline/coc_nusc/reasoning/ood_reasoning.parquet'
    scenes=load_reasoning_events(parquet)
    with (analysis/'exposure_manifest.csv').open() as f:exposure=list(csv.DictReader(f))
    excluded=validate_exposure(exposure,scenes)
    with (analysis/'artifact_inventory.csv').open() as f: inventory=list(csv.DictReader(f))
    source_hash=hashlib.sha256(parquet.read_bytes()).hexdigest()
    matches=[r for r in inventory if r['path']==str(parquet.relative_to(root))]
    if len(matches)!=1 or matches[0]['sha256']!=source_hash:
        raise ValueError('Exposure analysis and current source hashes differ')
    chosen=select_scenes(scenes,excluded,count,seed)
    materials=[];mapping=[];extraction=[]
    for sid in chosen:
        rid='REV-'+hashlib.sha256(f'{seed}:{sid}'.encode()).hexdigest()[:16]
        events=sorted(enumerate(scenes[sid]),key=lambda pair:(int(pair[1]['event_start_timestamp']),pair[0]))
        origin=int(events[0][1]['event_start_timestamp'])
        texts=[{'event_index':i,'time_s':(int(e['event_start_timestamp'])-origin)/1e6,'text':e.get('cot',e.get('coc',''))} for i,e in events]
        if not all(isinstance(e['text'],str) and e['text'].strip() for e in texts):raise ValueError('Source text absent')
        materials.append({'review_id':rid,'events':texts})
        mapping.append({'review_id':rid,'scene_id':sid,'event_count':len(events),'exposure_status':'UNKNOWN_EXPOSURE_NOT_CERTIFIED_HELDOUT'})
        indexes=sorted(random.Random(f'{seed}:{sid}:extraction').sample(range(len(texts)),min(4,len(texts))))
        for idx in indexes:
            e=texts[idx]
            extraction.append({'review_id':rid,'event_index':e['event_index'],'source_text':e['text'],'actions':'','continuing_requirements':'','end_conditions':'','preconditions':'','source_spans':'','evidence_status':'','notes':''})
    manifest={'project_id':'sequential-coc-verification','status':'AWAITING_INDEPENDENT_HUMAN_LABELS_AND_EXPOSURE_CONFIRMATION','seed':seed,'source_sha256':hashlib.sha256(parquet.read_bytes()).hexdigest(),'known_scene_exclusions':sorted(excluded),'selected_scene_ids':chosen,'selected_count':len(chosen),'extraction_count':len(extraction),'selection_rule':'sorted eligible IDs; random.Random(seed).sample without replacement; at least two CoCs','gold_available':False,'development_independence':'NOT_CERTIFIED','review_packet_code_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'source_root':str(root),'analysis_run':str(analysis),'analysis_input_hashes':{name:hashlib.sha256((analysis/name).read_bytes()).hexdigest() for name in ['exposure_manifest.csv','artifact_inventory.csv','RUN_MANIFEST.json']}}
    save(output/'sampling_manifest.json',manifest);save(output/'private_scene_mapping.json',mapping)
    (output/'review_packet.jsonl').write_text(''.join(json.dumps(i,ensure_ascii=False)+'\n' for i in materials))
    (output/'review_packet.html').write_text(render_html(materials))
    fields=['review_id','temporal_requirement_explicit','required_action_sequence','textual_consistency','evidence_span','notes']
    for name in ['A','B']:
        write_csv(output/f'reviewer_{name.lower()}.csv',[dict.fromkeys(fields,'')|{'review_id':r['review_id']} for r in materials],fields)
        write_csv(output/f'extraction_{name.lower()}.csv',extraction,list(extraction[0]) if extraction else ['review_id'])
    (output/'ANNOTATION_GUIDELINE.md').write_text('''# 독립 검토 지침

이 패킷은 새 사람 검토용 초안이다. 기존 94장면과 알려진 27검토 장면을 제외했지만 전체 개발 사용 이력은 확인되지 않아 독립 held-out으로 인증하지 않았다. 자료 관리자가 이력을 확인한 뒤 확정하며 목록이 바뀌면 새 run ID를 사용한다.

## 제공 정보와 판단 범위

review_packet.html에는 같은 장면의 모든 CoC와 원본 문장 인덱스 및 상대 시간만 있다. 영상·검사기 출력·예상 판정은 제공하지 않는다. 각 검토자는 상대 검토자의 답을 보지 않고 자신의 CSV만 작성한다. private_scene_mapping.json과 집계 결과는 검토자에게 주지 않는다.

## 판정 범주

- temporal_requirement_explicit: YES / NO / AMBIGUOUS
- required_action_sequence: 의미 순서에 따라 STOP_OR_HOLD, YIELD_OR_DECELERATE, ACCELERATE_OR_PROCEED, MAINTAIN_SPEED, OTHER를 `>`로 연결한다. 시간적으로 연속된 동일 의미 행동만 합치며 대상·조건이 바뀌면 메모한다. 판정 불가 시 AMBIGUOUS, 행동 없음은 NO_EXPLICIT_ACTION.
- textual_consistency: TEXTUAL_CONTRADICTION / TEXTUALLY_CONSISTENT / UNKNOWN_EXTERNAL_EVIDENCE_REQUIRED / AMBIGUOUS_TEXT / NOT_APPLICABLE_NO_TEMPORAL_REQUIREMENT
- evidence_span: 판정에 사용한 문장 인덱스와 원문 구절. notes에는 판정 이유 또는 부족한 증거를 기록한다.

## 결정 순서

1. 서로 이어지는 요구가 있는지 확인한다. 없으면 NOT_APPLICABLE_NO_TEMPORAL_REQUIREMENT.
2. 문장 자체가 해석 불가이면 AMBIGUOUS_TEXT.
3. 같은 대상·같은 조건에서 유지 중임이 명시되는데 진행하는 등 텍스트만으로 충돌이 확정될 때만 TEXTUAL_CONTRADICTION.
4. 종료 여부를 알려면 텍스트 밖 증거가 필요하면 UNKNOWN_EXTERNAL_EVIDENCE_REQUIRED.
5. 요구와 해제·순서가 문장 안에서 명시적으로 양립하면 TEXTUALLY_CONSISTENT.

‘통과할 때까지 정지’ 뒤 ‘아직 횡단 중인데 진행’은 모순이다. ‘통과했으므로 진행’은 일관됨이다. ‘이제 진행’만 있으면 통과 사실이 생략된 것이므로 미상이다. 이 예시는 설명용이며 실제 평가 정답이 아니다.

## 추출 정답

extraction CSV의 source_text는 수정하지 않는다. 행동·지속 요구·종료 조건·선행조건과 근거 구절을 기록한다. 조건 문구와 그 조건이 실제 참인지의 증거를 구분한다. 외부 근거 없이 관측된 True/False를 채우지 않는다. 자유 형식 필드는 JSON 배열로 작성하며 없음은 []로 구분한다. evidence_status는 TRUE/FALSE/UNKNOWN/MIXED 중 하나와 notes의 대상·근거를 사용한다. 이는 사람의 원문 해석이며 현 parser의 제한에 맞추어 정답을 축소하지 않는다.

## 절차 기록

자료 관리자는 검토자 자격·기존 연구 참여·사전 교육 일시와 사용한 지침 버전을 별도로 기록한다. 원시 CSV는 변경하지 않고 합의 표는 별도 생성한다. 합의 근거가 없으면 합의되었다고 자동 처리하지 않는다. 오류 주입은 이 원문 정답 확인 후 적격 정상 원문에만 적용한다.
''')
    save(output/'RUN_MANIFEST.json',manifest)
    save(output/'RESULT.json',{'status':'PACKET_READY_LABELS_NOT_COLLECTED','scene_count':len(chosen),'event_count':sum(len(x['events']) for x in materials),'extraction_count':len(extraction),'predictions_executed':False,'gold_count':0})
    (output/'REPORT_KO.md').write_text(f'# 독립 사람 검토 패킷 준비\n\n원문 {len(chosen)}장면, 추출 대상 {len(extraction)}문장. 두 검토자 CSV는 빈 상태이며 정답을 만들거나 모델 판정을 실행하지 않았다. 개발 사용 이력 확인과 실제 검토자 배정이 남아 있다. 이 패킷의 원문 정상 판정이 확보된 후 가상 오류 주입을 시작한다.\n')
    for path in output.iterdir():
        if path.is_file():path.chmod(0o600)
    print(json.dumps({'output':str(output),'scenes':len(chosen),'extraction':len(extraction),'status':'AWAITING_HUMAN_REVIEW'},ensure_ascii=False))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source-root',type=Path,required=True);p.add_argument('--analysis',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    args=p.parse_args();build(args.source_root,args.analysis,args.output)
