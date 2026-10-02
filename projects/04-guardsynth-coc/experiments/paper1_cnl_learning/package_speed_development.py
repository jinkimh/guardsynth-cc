"""Matched real-data staging and processor masks; staging is never training admission."""
import argparse
import base64
import hashlib
import io
import json
from pathlib import Path
import re

import run_real_development as real


def target_segments(original_coc, target, cnl=None):
    segments=[{'text':'ORIGINAL_COC\n'+original_coc+'\n','supervise':True,'kind':'ORIGINAL_COC'}]
    for action,value in target['raw_assessments'].items():
        segments.append({'text':action+': '+value+'\n',
            'supervise':target['endpoint_assessments'][action] is not None,'kind':action})
    if cnl is not None:segments.append({'text':'CONSTRAINT\n'+cnl,'supervise':True,'kind':'CNL'})
    return segments


def encode(processor, frames, segments, prompt):
    from PIL import Image
    images=[]
    for frame in frames:
        image=Image.open(io.BytesIO(base64.b64decode(frame['data_url'].split(',',1)[1]))).convert('RGB')
        image.thumbnail((640,640),Image.Resampling.LANCZOS);images.append(image)
    user={'role':'user','content':[{'type':'image'} for _ in images]+[{'type':'text','text':prompt}]}
    text=''.join(s['text'] for s in segments)
    prompt_text=processor.apply_chat_template([user],tokenize=False,add_generation_prompt=True)
    full_text=processor.apply_chat_template([user,{'role':'assistant','content':[{'type':'text','text':text}]}],tokenize=False)
    prefix=processor(text=[prompt_text],images=images,return_tensors='pt')
    batch=processor(text=[full_text],images=images,return_tensors='pt')
    n=prefix['input_ids'].shape[1]
    if not batch['input_ids'][0,:n].equal(prefix['input_ids'][0]):raise ValueError('prompt prefix mismatch')
    target=processor.tokenizer(text,add_special_tokens=False,return_offsets_mapping=True)
    if batch['input_ids'][0,n:n+len(target['input_ids'])].tolist()!=target['input_ids']:
        raise ValueError('target token boundary mismatch; refuse approximate loss masks')
    labels=batch['input_ids'].clone();labels[:,:n]=-100
    offset=0;masked=[]
    for segment in segments:
        end=offset+len(segment['text'])
        if not segment['supervise']:
            indices=[i for i,(a,b) in enumerate(target['offset_mapping']) if a<end and b>offset]
            for i in indices:labels[0,n+i]=-100
            masked.append({'kind':segment['kind'],'token_count':len(indices)})
        offset=end
    if batch['input_ids'].shape[1]>8192:raise ValueError('no silent truncation')
    batch['labels']=labels
    return batch,{'prompt_tokens':n,'sequence_tokens':batch['input_ids'].shape[1],
                  'supervised_tokens':int((labels!=-100).sum()),'masked_fields':masked,
                  'visual_values':batch['pixel_values'].numel(),'prompt_fully_masked':bool((labels[:,:n]==-100).all())}


def execute(output,admission_run='m18-cohort-feasibility-2026-09-29-004'):
    if output.exists():raise FileExistsError(output)
    input_hashes={}
    def read(run,name,jsonl=False):
        manifest=json.loads((run/'RUN_MANIFEST.json').read_text());p=run/name
        if real.digest(p)!=manifest['output_hashes'][name]:raise ValueError('immutable input drift '+name)
        input_hashes[str(p.relative_to(real.ROOT))]=real.digest(p)
        return [json.loads(s) for s in p.read_text().splitlines()] if jsonl else json.loads(p.read_text())
    intake=real.READINESS/'speed-action-intake-2026-09-29-001'
    inputs=read(intake,'development_action_inputs.jsonl',True)
    targets=read(intake,'development_action_targets.jsonl',True)
    candidates=read(real.READINESS/'conditional-candidates-2026-09-08-002','candidate_readiness.json')['records']
    source=read(real.READINESS/'stop-control-source-acceptance-2026-09-29-001','source_speed_bindings.json')['records']
    by_digest={r['candidate_digest']:r for r in candidates};by_index={r['candidate_index']:r for r in source}
    audit=read(real.BASE/admission_run,'admission_audit.json')
    admission_evidence=read(real.BASE/admission_run,'admission_evidence.json')
    cnl_by_candidate={r['candidate_index']:r['cnl_text_sha256'] for r in audit}
    eligible={r['candidate_index']:r['training_eligible'] for r in audit}
    split=read(real.BASE/'m18-cohort-feasibility-2026-09-29-001','exploratory_split_lock.json')
    partitions={r['sample_id']:r['partition'] for r in split['records']}
    from transformers import AutoProcessor
    processor=AutoProcessor.from_pretrained(real.learning.MODEL_PATH,local_files_only=True)
    packets={};staging=[];checks=[]
    for blind,target in zip(inputs,targets,strict=True):
        if blind['sample_id']!=target['sample_id']:raise ValueError('paired identity mismatch')
        row=by_index[target['candidate_index']];coc=by_digest[row['candidate_digest']]['original_coc']
        if hashlib.sha256(coc.encode()).hexdigest()!=row['original_coc_sha256']:raise ValueError('original CoC drift')
        if blind['packet_ref'] not in packets:
            p=real.ROOT/blind['packet_ref']
            if real.digest(p)!=blind['packet_sha256']:raise ValueError('blind packet drift')
            packets[blind['packet_ref']]=json.loads(p.read_text())
        scene=packets[blind['packet_ref']]['scenes'][int(blind['scene_pointer'].split('/')[-1])]
        if scene['sample_id']!=blind['sample_id']:raise ValueError('packet identity mismatch')
        cnl=None
        if row.get('accepted_stop_control'):
            run=(real.ROOT/admission_evidence['projection_run'] if admission_evidence.get('projection_run')
                 else real.READINESS/'stop-control-source-acceptance-2026-09-29-001')
            p=run/f"candidate_{row['candidate_index']}_cnl.txt"
            if real.digest(p)!=json.loads((run/'RUN_MANIFEST.json').read_text())['output_hashes'][p.name]:
                raise ValueError('CNL drift')
            cnl=p.read_text();input_hashes[str(p.relative_to(real.ROOT))]=real.digest(p)
            if real.digest(p)!=cnl_by_candidate[row['candidate_index']]:raise ValueError('admission CNL mismatch')
        prompt=blind['question_ko']+'\n'+json.dumps(blind['actions'],ensure_ascii=False)
        for arm in ('L0','L3'):
            segments=target_segments(coc,target,cnl if arm=='L3' else None)
            batch,check=encode(processor,scene['frames'],segments,prompt)
            checks.append({'sample_id':blind['sample_id'],'arm':arm,**check})
            staging.append({'sample_id':blind['sample_id'],'candidate_index':row['candidate_index'],
                'clip_group':target['clip_group'],'partition':partitions[blind['sample_id']],'arm':arm,
                'input':blind,'original_coc_sha256':row['original_coc_sha256'],'target_segments':segments,
                'training_allowed':eligible[row['candidate_index']] and partitions[blind['sample_id']]=='train',
                'main_training_allowed':False,'stage_only':not eligible[row['candidate_index']],
                'dataset_scope':'DEVELOPMENT_SPEED_SUPERVISION_ONLY',
                'L3_source_cnl_available':cnl is not None,
                'reference_reason_not_used_for_generation_or_target':True})
            del batch
    output.mkdir(parents=True,exist_ok=False,mode=0o700)
    for arm in ('L0','L3'):
        (output/(arm.lower()+'_staging.jsonl')).write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in staging if r['arm']==arm))
        (output/(arm.lower()+'_admitted_train.jsonl')).write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n'
            for r in staging if r['arm']==arm and r['training_allowed'] and not r['stage_only']))
    result={'scenes':len(inputs),'staged_arm_rows':len(staging),'processor_checked_rows':len(checks),
        'source_bound_cnl_scenes':sum(bool(r.get('accepted_stop_control')) for r in source),
        'training_allowed_scenes':sum(eligible.values()),'optimizer_updates':0,
        'admitted_train_arm_rows':sum(r['training_allowed'] and not r['stage_only'] for r in staging),
        'admitted_candidate_indices':sorted({r['candidate_index'] for r in staging if r['training_allowed']}),
        'masked_fields_per_arm':{a:sum(len(c['masked_fields']) for c in checks if c['arm']==a) for a in ('L0','L3')},
        'main_training_started':False,'split_reused_unchanged':True}
    for name,value in [('processor_checks.json',checks),('RESULT.json',result)]:
        (output/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
    (output/'RUN_MANIFEST.json').write_text(json.dumps({'project_id':'guardsynth-coc','run_id':output.name,
        'status':'COMPLETE','input_hashes':input_hashes,'code_sha256':real.digest(Path(__file__)),
        'output_hashes':{p.name:real.digest(p) for p in output.iterdir()}},indent=2)+'\n')
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run-id',required=True)
    p.add_argument('--admission-run-id',default='m18-cohort-feasibility-2026-09-29-004');a=p.parse_args()
    if any(not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*-[0-9]+',s) for s in (a.run_id,a.admission_run_id)):
        p.error('invalid run id')
    print(json.dumps(execute(real.BASE/a.run_id,a.admission_run_id),indent=2))
