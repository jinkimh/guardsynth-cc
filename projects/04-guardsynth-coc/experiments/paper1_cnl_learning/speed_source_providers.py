"""Actual local Qwen source-to-NL / source-to-candidate providers; no ACTION targets."""
import argparse
import json
import os
from pathlib import Path
import re

import execute_speed_contracts as e
import run_real_development as real


def request_for(row, arm):
    # Deliberate allowlist: even accidental extra ACTION/reason fields cannot enter generation.
    source={k:row[k] for k in ('candidate_digest','event_timestamp_us','observation_ref','observation',
                              'active_source_controls','speed_premises')}
    if row.get('accepted_stop_control'):source['accepted_stop_control']=row['accepted_stop_control']
    common=('Use only the following independent source observations. Entry predicates are not speed obligations. '
            'UNKNOWN motion remains unknown. Do not infer a red light from a STOP paddle, release, motion, '
            'legal authority, or an action answer. Abstain when a speed obligation is not supported.\n')
    if arm=='L1':
        instruction=('Write a concise Korean natural-language constraint directly, without EBLC or solver. '
                     'State uncertainty and source scope; if unsupported output ABSTAIN.\n')
    elif arm=='L2':
        instruction=('Return ONLY JSON with fields clause_kind (STOP_REQUIRED or SPEED_REDUCTION_REQUIRED), '
            'predicate_id (identifier), target_entity_id (identifier or null), source_refs (exact evidence references '
            'from the input), or {"abstain":true}. This is an unverified candidate, not a scene certification.\n')
    else:raise ValueError('provider arm must be L1 or L2')
    return common+instruction+json.dumps(source,ensure_ascii=False,sort_keys=True)


def render_candidate(raw_text, row):
    candidate=json.loads(raw_text)
    if candidate=={'abstain':True}:return {'status':'ABSTAIN','cnl':None}
    if set(candidate)!={'clause_kind','predicate_id','target_entity_id','source_refs'}:
        raise ValueError('unverified candidate shape')
    refs={row['observation_ref']}
    refs.update(c['evidence_ref'] for c in row['active_source_controls'])
    if row.get('accepted_stop_control'):refs.add(row['accepted_stop_control']['source_ref'])
    if not candidate['source_refs'] or not set(candidate['source_refs'])<=refs:
        raise ValueError('candidate invented source reference')
    # Syntax/provenance checks only, deliberately no semantic SMT filtering of L2 candidates.
    contract=e.parse_speed_contract({**candidate,'contract_version':'eblc-speed-contract-v0.1',
        'contract_id':'provider_candidate_'+str(row['candidate_index']),'subject_id':'ego',
        'rule_ref':candidate['source_refs'][0],'claim_scope':'CONDITIONAL_SINGLE_DECISION_NOT_VEHICLE_SAFETY'})
    return {'status':'UNVERIFIED_CANDIDATE','contract':contract.raw,
            'cnl':e.render_speed_contract(contract).text,'semantic_verification_performed':False}


def execute(output, generate=False):
    if output.exists():raise FileExistsError(output)
    source=real.READINESS/'stop-control-source-acceptance-2026-09-29-001'
    manifest=json.loads((source/'RUN_MANIFEST.json').read_text())
    path=source/'source_speed_bindings.json'
    if real.digest(path)!=manifest['output_hashes'][path.name]:raise ValueError('source drift')
    rows=json.loads(path.read_text())['records']
    requests=[{'candidate_index':r['candidate_index'],'arm':arm,'prompt':request_for(r,arm)}
              for r in rows for arm in ('L1','L2')]
    output.mkdir(parents=True,exist_ok=False,mode=0o700)
    def write(name,value):(output/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
    write('requests.json',requests)
    write('protocol_lock.json',{'model':real.learning.MODEL_ID,'revision':real.learning.REVISION,
        'do_sample':False,'max_new_tokens':256,'source_sha256':real.digest(path),
        'requests_sha256':real.digest(output/'requests.json'),'ACTION_read':False,
        'L1':'DIRECT_NL_NO_SOLVER','L2':'UNVERIFIED_CANDIDATE_COMMON_RENDERER',
        'outputs_are_training_eligible':False,'code_sha256':real.digest(Path(__file__))})
    outputs=[]
    if generate:
        # CPU-only bounded source generation does not claim a free GPU or disturb GPU users.
        if os.getloadavg()[0]>os.cpu_count()/2:raise RuntimeError('CPU occupied')
        os.environ['CUDA_VISIBLE_DEVICES']='';os.environ['HF_HUB_OFFLINE']='1'
        import torch
        from transformers import AutoProcessor,Qwen3VLForConditionalGeneration
        torch.set_num_threads(4);torch.manual_seed(42)
        processor=AutoProcessor.from_pretrained(real.learning.MODEL_PATH,local_files_only=True)
        model=Qwen3VLForConditionalGeneration.from_pretrained(real.learning.MODEL_PATH,
            local_files_only=True,dtype=torch.bfloat16,attn_implementation='sdpa').eval()
        by_id={r['candidate_index']:r for r in rows}
        with (output/'provider_outputs.jsonl').open('x') as stream:
            for request in requests:
                chat=[{'role':'user','content':[{'type':'text','text':request['prompt']}]}]
                batch=processor.apply_chat_template(chat,tokenize=True,add_generation_prompt=True,
                    return_dict=True,return_tensors='pt')
                with torch.inference_mode():
                    ids=model.generate(**batch,do_sample=False,max_new_tokens=256)
                raw=processor.decode(ids[0,batch['input_ids'].shape[1]:],skip_special_tokens=True).strip()
                result={'candidate_index':request['candidate_index'],'arm':request['arm'],'raw_output':raw}
                if request['arm']=='L2':
                    try:result.update(render_candidate(raw,by_id[request['candidate_index']]))
                    except (ValueError,TypeError,KeyError) as exc:result.update(status='INVALID_CANDIDATE',error=str(exc),cnl=None)
                else:result.update(status='ABSTAIN' if raw=='ABSTAIN' else 'UNREVIEWED_DIRECT_NL',cnl=None if raw=='ABSTAIN' else raw)
                stream.write(json.dumps(result,ensure_ascii=False)+'\n');stream.flush();outputs.append(result)
                print(json.dumps({'candidate_index':request['candidate_index'],'arm':request['arm'],'completed':True}),flush=True)
    result={'request_count':len(requests),'output_count':len(outputs),'source_scene_count':len(rows),
            'training_eligible_outputs':0,'main_training_started':False,'ACTION_targets_read':0}
    write('RESULT.json',result)
    write('RUN_MANIFEST.json',{'project_id':'guardsynth-coc','run_id':output.name,'status':'COMPLETE',
        'output_hashes':{p.name:real.digest(p) for p in output.iterdir()}})
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run-id',required=True)
    p.add_argument('--generate',action='store_true');a=p.parse_args()
    if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*-[0-9]+',a.run_id):p.error('invalid run id')
    print(json.dumps(execute(real.BASE/a.run_id,a.generate),indent=2))
