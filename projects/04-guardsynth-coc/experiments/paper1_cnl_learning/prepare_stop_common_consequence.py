"""Source-linked two-scene proposal; does not modify accepted contracts or human receipts."""
import argparse
import json
from pathlib import Path
import re

import execute_speed_contracts as e
import run_real_development as real
from guard_synth_eblc.speed_common_consequence import derive, VERSION


def execute(output):
    if output.exists(): raise FileExistsError(output)
    source = real.READINESS/'stop-control-source-acceptance-2026-09-29-001'
    manifest=json.loads((source/'RUN_MANIFEST.json').read_text())
    def read(name):
        if real.digest(source/name)!=manifest['output_hashes'][name]:raise ValueError('source drift')
        return json.loads((source/name).read_text())
    rows=read('source_speed_bindings.json')['records']
    artifacts={};records=[]
    for row in rows:
        if not row.get('accepted_stop_control'):continue
        idx=row['candidate_index']; contract=read(f'candidate_{idx}_contract.json')
        p=row['speed_premises']; result=derive(e.parse_speed_contract(contract),p['applicability'],p['evidence_valid'])
        checked=e.check_queries(e.compile_core_model(e.parse_core_model(result['proof_core'])))
        if checked['agreement']!=1 or result['excluded_by_all_supported_branches']!=['START_OR_ACCELERATE']:
            raise ValueError('proof regression')
        source_ref=row['accepted_stop_control']['source_ref']
        cnl=(f'장면 #{idx}: 사용자가 확인한 작업자의 STOP 표지는 에고 차량에 대한 정지 지시다. '
             '이 지시가 적용되는 현재 판단에서, 차량이 이동 중인지 정지 중인지 확인되지 않아도 '
             '두 상태에서 공통으로 배제되는 새 출발·가속(START_OR_ACCELERATE)은 선택하지 않는다. '
             '정지를 위한 감속이나 정지 유지를 금지한다는 뜻은 아니다. '
             '유지·비정지 목적 감속의 추가 배제, 지시 해제, 실제 이동 상태와 전체 안전성은 확정하지 않는다.\n'
             + ('원 CoC의 빨간 신호등 주장은 이 STOP 표지 확인과 별개이며 확인되지 않았다.\n' if idx==68 else '')
             + f'출처: {source_ref}\n')
        artifacts[f'candidate_{idx}_proof.json']=result
        artifacts[f'candidate_{idx}_checks.json']=checked
        artifacts[f'candidate_{idx}_cnl.txt']=cnl
        records.append({'candidate_index':idx,'source_ref':source_ref,'version':VERSION,
                        'cnl_sha256':__import__('hashlib').sha256(cnl.encode()).hexdigest(),
                        'excluded':result['excluded_by_all_supported_branches'],'query_count':checked['query_count'],
                        'human_cnl_receipt':False,'policy_admitted':False})
    artifacts['RESULT.json']={'records':records,'smt_queries':sum(r['query_count'] for r in records),
        'legacy_semantics_changed':False,'motion_facts_added':0,'training_rows_added':0}
    artifacts['REPORT_KO.md']=('# UNKNOWN 이동 상태의 공통 결과 — 별도 제안\n\n'
        '기존 v0.1은 그대로 UNKNOWN에서 모든 verdict를 UNRESOLVED로 둔다. 별도 파생은 물리적 상태 후보 '
        '{MOVING, STATIONARY} 각각의 일관성을 확인하고 모든 후보에서 증명되는 배제만 교집합으로 취한다. '
        '새 관찰이나 ACTION 답을 사용하지 않는다. UNKNOWN 자체를 MOVING/STATIONARY로 바꾸지 않는다.\n\n'
        '구체적 남은 판단: 위 두 CNL이 확인한 STOP 지시의 의미를 보존하는지, 그리고 새 출발·가속의 '
        '공통 배제만을 #7/#68의 DEVELOPMENT 속도 감독에 사용할지. 기존 관찰 재질문이나 main 학습 승인이 아니다.\n')
    output.mkdir(parents=True,exist_ok=False,mode=0o700)
    for name,value in artifacts.items():
        (output/name).write_text(value if isinstance(value,str) else json.dumps(value,ensure_ascii=False,indent=2)+'\n')
    (output/'RUN_MANIFEST.json').write_text(json.dumps({'project_id':'guardsynth-coc','run_id':output.name,
        'status':'COMPLETE','source_manifest_sha256':real.digest(source/'RUN_MANIFEST.json'),
        'output_hashes':{p.name:real.digest(p) for p in output.iterdir()}},indent=2)+'\n')
    return artifacts['RESULT.json']


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run-id',required=True);a=p.parse_args()
    if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*-[0-9]+',a.run_id):p.error('invalid run id')
    print(json.dumps(execute(real.READINESS/a.run_id),ensure_ascii=False,indent=2))
