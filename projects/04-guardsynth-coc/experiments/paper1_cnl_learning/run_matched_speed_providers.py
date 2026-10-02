"""CoC + causal images + identical source context for L1/L2; supported development subset only."""
import argparse
import base64
import hashlib
import io
import json
import os
from pathlib import Path
import re

import speed_source_providers as providers
import run_real_development as real


def execute(output):
    if output.exists():raise FileExistsError(output)
    hashes={}
    def read(run,name):
        p=real.READINESS/run/name;m=json.loads((p.parent/'RUN_MANIFEST.json').read_text())
        if real.digest(p)!=m['output_hashes'][name]:raise ValueError('input drift '+name)
        hashes[str(p.relative_to(real.ROOT))]=real.digest(p)
        return json.loads(p.read_text())
    rows=read('stop-control-source-acceptance-2026-09-29-001','source_speed_bindings.json')['records']
    bindings=read('speed-contract-execution-2026-09-28-001','coordinator_bindings.json')['records']
    mapping=read('speed-action-assignment-preparation-2026-09-29-001','assignment_proposal.json')
    packet=read('speed-action-assigned-2026-09-29-001','action_review_packet.json')
    sample_by_candidate=dict(zip(mapping['candidate_indices'],mapping['sample_ids'],strict=True))
    by_candidate={r['candidate_index']:r for r in bindings}
    scenes={r['sample_id']:r for r in packet['scenes']}
    requests=[];selected=[]
    for row in rows:
        if not row.get('accepted_stop_control'):continue
        idx=row['candidate_index'];bound=by_candidate[idx];scene=scenes[sample_by_candidate[idx]]
        if any(row[k]!=bound[k] for k in ('candidate_digest','clip_id','event_timestamp_us')):
            raise ValueError('source identity drift')
        if scene['event_timestamp_us']!=row['event_timestamp_us']:raise ValueError('frame event drift')
        coc=bound['original_coc']
        if hashlib.sha256(coc.encode()).hexdigest()!=row['original_coc_sha256']:raise ValueError('CoC drift')
        for f in scene['frames']:
            if hashlib.sha256(base64.b64decode(f['data_url'].split(',',1)[1])).hexdigest()!=f['sha256']:
                raise ValueError('image drift')
            if f['timestamp_us']>row['event_timestamp_us']:raise ValueError('future frame')
        for arm in ('L1','L2'):
            prompt=(providers.request_for(row,arm)+'\nOriginal CoC (unchanged source claim, NOT gold or authority):\n'
                +coc+'\nUse the same causal frames supplied here. Keep any CoC/source disagreement explicit; '
                'do not certify a red light from a worker STOP paddle. Do not rewrite the original CoC. '
                'No ACTION reference is supplied.\n')
            requests.append({'candidate_index':idx,'arm':arm,'prompt':prompt,'sample_id':scene['sample_id'],
                             'frame_hashes':[f['sha256'] for f in scene['frames']]})
        selected.append(idx)
    output.mkdir(parents=True,exist_ok=False,mode=0o700)
    def write(name,value):(output/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
    write('requests.json',requests)
    write('protocol_lock.json',{'scope':'SOURCE_SUPPORTED_SUBSET_PROVIDER_DEVELOPMENT_NOT_MAIN_ARM_COMPLETION',
        'selection_rule':'ALL_ACCEPTED_STOP_CONTROL_SOURCE_ROWS_BEFORE_GENERATION',
        'selected_candidates':selected,'full_denominator_candidates':[r['candidate_index'] for r in rows],
        'model_revision':real.learning.REVISION,'do_sample':False,'max_new_tokens':256,'seed':42,
        'image_sampling':'ALL_7_CAUSAL_FRAMES','resize':'PIL_LANCZOS_THUMBNAIL_640',
        'CoC_unchanged':True,'ACTION_answers_used':False,'training_eligible':False,
        'requests_sha256':real.digest(output/'requests.json'),'code_sha256':real.digest(Path(__file__))})
    if os.getloadavg()[0]>os.cpu_count()/2:raise RuntimeError('CPU occupied')
    os.environ['CUDA_VISIBLE_DEVICES']='';os.environ['HF_HUB_OFFLINE']='1'
    import torch
    from PIL import Image
    from transformers import AutoProcessor,Qwen3VLForConditionalGeneration
    torch.set_num_threads(4);torch.manual_seed(42)
    processor=AutoProcessor.from_pretrained(real.learning.MODEL_PATH,local_files_only=True)
    model=Qwen3VLForConditionalGeneration.from_pretrained(real.learning.MODEL_PATH,
        local_files_only=True,dtype=torch.bfloat16,attn_implementation='sdpa').eval()
    sources={r['candidate_index']:r for r in rows};outputs=[]
    with (output/'provider_outputs.jsonl').open('x') as stream:
        for request in requests:
            images=[]
            for frame in scenes[request['sample_id']]['frames']:
                image=Image.open(io.BytesIO(base64.b64decode(frame['data_url'].split(',',1)[1]))).convert('RGB')
                image.thumbnail((640,640),Image.Resampling.LANCZOS);images.append(image)
            chat=[{'role':'user','content':[{'type':'image'} for _ in images]+[{'type':'text','text':request['prompt']}]}]
            text=processor.apply_chat_template(chat,tokenize=False,add_generation_prompt=True)
            batch=processor(text=[text],images=images,return_tensors='pt')
            with torch.inference_mode():ids=model.generate(**batch,do_sample=False,max_new_tokens=256)
            raw=processor.decode(ids[0,batch['input_ids'].shape[1]:],skip_special_tokens=True).strip()
            result={'candidate_index':request['candidate_index'],'arm':request['arm'],'raw_output':raw}
            if request['arm']=='L2':
                try:result.update(providers.render_candidate(raw,sources[request['candidate_index']]))
                except (ValueError,TypeError,KeyError) as exc:result.update(status='INVALID_CANDIDATE',error=str(exc),cnl=None)
            else:result.update(status='ABSTAIN' if raw=='ABSTAIN' else 'UNREVIEWED_DIRECT_NL',cnl=None if raw=='ABSTAIN' else raw)
            stream.write(json.dumps(result,ensure_ascii=False)+'\n');stream.flush();outputs.append(result)
            print(json.dumps({'candidate_index':request['candidate_index'],'arm':request['arm'],'completed':True}),flush=True)
    result={'source_supported_scenes':len(selected),'full_scene_denominator':len(rows),'provider_outputs':len(outputs),
        'training_admitted_outputs':0,'main_arm_completion':False,'CoC_image_source_matched_across_L1_L2':True}
    write('RESULT.json',result)
    write('RUN_MANIFEST.json',{'project_id':'guardsynth-coc','run_id':output.name,'status':'COMPLETE',
        'input_hashes':hashes,'provider_code_sha256':real.digest(Path(providers.__file__)),
        'output_hashes':{p.name:real.digest(p) for p in output.iterdir()}})
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run-id',required=True);a=p.parse_args()
    if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*-[0-9]+',a.run_id):p.error('invalid run id')
    print(json.dumps(execute(real.BASE/a.run_id),indent=2))
