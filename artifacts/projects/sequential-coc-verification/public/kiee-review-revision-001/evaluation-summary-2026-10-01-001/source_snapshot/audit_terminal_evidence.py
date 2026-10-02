"""Diagnostic final-state queries; retain original prefix-counterexample outputs."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

REASONS=(('sticky_parse_status_unknown','PARSE_STATUS_UNKNOWN'),('sticky_overlapping_obligation','OVERLAPPING_OBLIGATION'),('sticky_stale_release_unknown','STALE_RELEASE_UNKNOWN'),('sticky_active_release_unknown','ACTIVE_RELEASE_UNKNOWN'),('sticky_active_satisfaction_unknown','ACTIVE_SATISFACTION_UNKNOWN'))

def parse_terminal(output):
    matches=re.findall(r'Formula\s+is\s+(?:(NOT)\s+)?satisfied',output)
    if len(matches)!=6 or matches[0]=='NOT':raise ValueError('Incomplete property results or unreachable Done')
    return [name for (_,name),status in zip(REASONS,matches[1:]) if status!='NOT']

def save(path,data):path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')

def run(source,output,verifyta):
    source=source.resolve();output=output.resolve();output.mkdir(parents=True,exist_ok=False)
    records=[json.loads(line) for line in (source/'results.jsonl').read_text().splitlines()]
    rows=[]
    for r in records:
        cid=r['case_id'];folder=output/cid;folder.mkdir()
        model=source/'uppaal'/cid/'model.xml'
        queries=['E<> Observer.Done']+[f'E<> Observer.Done && {flag}' for flag,_ in REASONS]
        q=folder/'terminal.q';q.write_text('\n'.join(queries)+'\n')
        command=[str(verifyta),'-q',str(model),str(q)]
        result=subprocess.run(command,capture_output=True,text=True,timeout=120)
        (folder/'stdout.txt').write_text(result.stdout);(folder/'stderr.txt').write_text(result.stderr)
        if result.returncode:raise RuntimeError(f'verifyta failed for {cid}: {result.returncode}')
        reasons=parse_terminal(result.stdout+'\n'+result.stderr)
        row={'case_id':cid,'python_reasons':r['predictions']['legacy_full']['unknown_reasons'],'original_counterexample_reasons':r['predictions']['uppaal']['unknown_reasons'],'terminal_reasons':reasons,'matches_python':reasons==r['predictions']['legacy_full']['unknown_reasons'],'command':command,'returncode':result.returncode,'source_model_sha256':hashlib.sha256(model.read_bytes()).hexdigest()}
        rows.append(row)
    save(output/'terminal_results.json',rows)
    result={'status':'COMPLETED','cases':len(rows),'terminal_reason_mismatches':sum(not r['matches_python'] for r in rows),'original_reason_mismatches':sum(r['python_reasons']!=r['original_counterexample_reasons'] for r in rows),'legacy_code_changed':False}
    save(output/'RESULT.json',result)
    save(output/'RUN_MANIFEST.json',{'project_id':'sequential-coc-verification','source_run':str(source),'source_results_sha256':hashlib.sha256((source/'results.jsonl').read_bytes()).hexdigest(),'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'purpose':'DIAGNOSTIC_TERMINAL_QUERY_NOT_NEW_TEST_SET'})
    (output/'REPORT_KO.md').write_text(f'''# UPPAAL 미상 사유 기록 진단

원 실행의 판정·오류 종류·최초 위반 위치는 Python과 같았지만 미상 사유 목록은 {result['original_reason_mismatches']}건 달랐다. `A[] not sticky_unknown`의 반례는 첫 미상 발생 시점에서 끝날 수 있다. 기존 출력 파서는 이 접두 경로의 플래그를 읽으므로 그 뒤 발생한 미상 사유를 놓칠 수 있다.

원래 XML과 기존 실행 출력은 변경하지 않고, `Observer.Done`에서 각 미상 플래그가 참인지 별도 질의하였다. {len(rows)}개 모델의 종료 상태 미상 사유는 Python과 {result['terminal_reason_mismatches']}건 불일치했다. 이는 모델 의미 차이와 반례 기록 범위 차이를 구분하는 진단이다. 원래 보고된 24건 불일치를 삭제하거나 기존 파서가 수정됐다고 주장하지 않는다.

기존 질의/출력 파서를 유지한다면 미상 사유 전체 일치를 주장할 수 없다. 전체 사건열의 사유가 필요할 때는 이 종료 상태 질의를 함께 실행해야 한다. 진단은 같은 시나리오 재질의이며 새 독립 실험이 아니다.
''')
    print(json.dumps(result))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--verifyta',type=Path,required=True)
    args=p.parse_args();run(args.source,args.output,args.verifyta)
