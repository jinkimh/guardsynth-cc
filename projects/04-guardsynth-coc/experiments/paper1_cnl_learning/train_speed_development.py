"""Bounded two-scene L0/L3 development learning, never main-study execution."""
import argparse
import base64
import hashlib
import io
import json
import os
from pathlib import Path
import re
import time

import package_speed_development as packaging
import run_real_development as real
from score_speed_development import score

CONFIG=Path(__file__).with_name('real_speed_development_config.json')


def validated_data():
    config=json.loads(CONFIG.read_text());rows={};hashes={str(CONFIG.relative_to(real.ROOT)):real.digest(CONFIG)}
    for arm in ('L0','L3'):
        path=real.ROOT/config['arms'][arm]['dataset']
        manifest=json.loads((path.parent/'RUN_MANIFEST.json').read_text())
        if real.digest(path)!=manifest['output_hashes'][path.name]:raise ValueError('admitted dataset drift')
        hashes[str(path.relative_to(real.ROOT))]=real.digest(path)
        rows[arm]=[json.loads(s) for s in path.read_text().splitlines()]
        if [r['candidate_index'] for r in rows[arm]]!=[7,68]:raise ValueError('two-scene scope changed')
        if any(r['arm']!=arm or not r['training_allowed'] or r['stage_only'] or r['main_training_allowed']
               or r['partition']!='train' or r['dataset_scope']!='DEVELOPMENT_SPEED_SUPERVISION_ONLY' for r in rows[arm]):
            raise ValueError('development authority/split mismatch')
    for l0,l3 in zip(rows['L0'],rows['L3'],strict=True):
        if l0['input']!=l3['input'] or l0['target_segments']!=l3['target_segments'][:-1]:
            raise ValueError('unmatched base input/CoC/action supervision')
        if l3['target_segments'][-1]['kind']!='CNL':raise ValueError('missing CNL supervision')
    if (config['model_revision']!=real.learning.REVISION or config['inference_gold_CNL']
            or not config['main_four_arm_gate_unchanged']):raise ValueError('model/protocol scope drift')
    return config,rows,hashes


def execute(output,gpu):
    if output.exists():raise FileExistsError(output)
    config,rows,hashes=validated_data()
    resource=real.idle_gpu(gpu)  # No output directory or model allocation if another user occupies GPU.
    os.environ['CUDA_VISIBLE_DEVICES']=resource['uuid'];os.environ['HF_HUB_OFFLINE']='1'
    os.environ['TOKENIZERS_PARALLELISM']='false'
    import torch
    from PIL import Image
    from peft import LoraConfig,TaskType,get_peft_model
    from transformers import AutoProcessor,Qwen3VLForConditionalGeneration
    torch.set_num_threads(4)
    processor=AutoProcessor.from_pretrained(real.learning.MODEL_PATH,local_files_only=True)
    baseline=real.BASE/'pretrained-speed-development-2026-09-29-002'
    baseline_manifest=json.loads((baseline/'RUN_MANIFEST.json').read_text())
    for name in ('protocol_lock.json','blind_inputs.json'):
        if real.digest(baseline/name)!=baseline_manifest['output_hashes'][name]:raise ValueError('blind protocol drift')
        hashes[str((baseline/name).relative_to(real.ROOT))]=real.digest(baseline/name)
    blind=json.loads((baseline/'blind_inputs.json').read_text());by_id={r['sample_id']:r for r in blind}
    eval_protocol=json.loads((baseline/'protocol_lock.json').read_text())
    split_path=real.ROOT/config['split_lock'];split=json.loads(split_path.read_text())
    split_manifest=json.loads((split_path.parent/'RUN_MANIFEST.json').read_text())
    if real.digest(split_path)!=split_manifest['output_hashes'][split_path.name]:raise ValueError('split drift')
    hashes[str(split_path.relative_to(real.ROOT))]=real.digest(split_path)
    eval_ids={r['sample_id'] for r in split['records'] if r['partition']=='evaluation'}
    if any(r['sample_id'] in eval_ids for r in rows['L0']):raise ValueError('train/eval leakage')
    batches={}
    for arm in ('L0','L3'):
        batches[arm]=[]
        for row in rows[arm]:
            prompt=row['input']['question_ko']+'\n'+json.dumps(row['input']['actions'],ensure_ascii=False)
            batch,_=packaging.encode(processor,by_id[row['sample_id']]['frames'],row['target_segments'],prompt)
            batches[arm].append(batch)
    output.mkdir(parents=True,exist_ok=False,mode=0o700)
    def write(name,value):(output/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
    write('protocol_lock.json',{'scope':'TWO_TRAIN_SCENE_DEVELOPMENT_EXPLORATORY_NOT_MAIN',
        'config':config,'training_candidates':[7,68],'evaluation_ids':sorted(eval_ids),
        'inference_protocol':eval_protocol,'training_selection_not_based_on_predictions':True,
        'training_output':'UNCHANGED_COC_AND_FOUR_ASSESSMENTS_PLUS_L3_CNL',
        'evaluation_output':'FROZEN_SINGLE_ACTION_DIAGNOSTIC_NOT_TRAINING_FORMAT_REPRODUCTION',
        'main_four_arm_gate_unchanged':True,'main_training_allowed':False,'resource':resource})
    logs=[];predictions=[];initial_by_seed={}
    for seed in config['paired_seeds']:
        for arm in ('L0','L3'):
            model=Qwen3VLForConditionalGeneration.from_pretrained(real.learning.MODEL_PATH,
                local_files_only=True,dtype=torch.bfloat16,attn_implementation='sdpa').to('cuda:0')
            targets=[n for n,m in model.named_modules() if isinstance(m,torch.nn.Linear)
                and 'language_model' in n and n.rsplit('.',1)[-1] in {'q_proj','k_proj','v_proj','o_proj'}]
            torch.manual_seed(seed);torch.cuda.manual_seed_all(seed)
            model=get_peft_model(model,LoraConfig(r=config['lora_rank'],lora_alpha=config['lora_alpha'],
                lora_dropout=config['lora_dropout'],bias='none',task_type=TaskType.CAUSAL_LM,target_modules=targets))
            params={n:p for n,p in model.named_parameters() if p.requires_grad}
            if not params or any('lora_' not in n or 'language_model' not in n for n in params):raise ValueError('trainable scope escaped')
            initial=hashlib.sha256(b''.join(p.detach().float().cpu().numpy().tobytes() for p in params.values())).hexdigest()
            if seed in initial_by_seed and initial_by_seed[seed]!=initial:raise ValueError('unpaired initialization')
            initial_by_seed[seed]=initial
            optimizer=torch.optim.AdamW(params.values(),lr=config['learning_rate'],weight_decay=config['weight_decay'])
            model.train();losses=[];started=time.monotonic()
            for step in range(config['proposed_optimizer_steps_per_arm_seed']):
                batch={k:v.to('cuda:0') for k,v in batches[arm][step%len(batches[arm])].items()}
                optimizer.zero_grad(set_to_none=True)
                with torch.autocast('cuda',dtype=torch.bfloat16):loss=model(**batch,use_cache=False).loss
                if not torch.isfinite(loss):raise ValueError('nonfinite loss')
                loss.backward();norm=torch.nn.utils.clip_grad_norm_(params.values(),1.)
                if not torch.isfinite(norm):raise ValueError('nonfinite gradient')
                optimizer.step();losses.append(float(loss.detach()))
            after=hashlib.sha256(b''.join(p.detach().float().cpu().numpy().tobytes() for p in params.values())).hexdigest()
            if after==initial:raise ValueError('no weight update')
            checkpoint=output/f'seed-{seed}-{arm.lower()}';model.save_pretrained(checkpoint)
            record={'seed':seed,'arm':arm,'optimizer_updates':len(losses),'losses':losses,
                'initial_adapter_sha256':initial,'updated_adapter_sha256':after,
                'trainable_parameters':sum(p.numel() for p in params.values()),'training_seconds':time.monotonic()-started}
            logs.append(record);write('training_logs.json',logs)
            model.eval()
            for row in blind:
                if row['sample_id'] not in eval_ids:continue
                images=[]
                for frame in row['frames']:
                    image=Image.open(io.BytesIO(base64.b64decode(frame['data_url'].split(',',1)[1]))).convert('RGB')
                    image.thumbnail((640,640),Image.Resampling.LANCZOS);images.append(image)
                content=[{'type':'image'} for _ in images]+[{'type':'text','text':eval_protocol['prompt']}]
                text=processor.apply_chat_template([{'role':'user','content':content}],tokenize=False,add_generation_prompt=True)
                batch=processor(text=[text],images=images,return_tensors='pt').to('cuda:0')
                with torch.inference_mode():tokens=model.generate(**batch,do_sample=False,max_new_tokens=eval_protocol['max_new_tokens'])
                raw=processor.decode(tokens[0,batch['input_ids'].shape[1]:],skip_special_tokens=True).strip()
                predictions.append({'seed':seed,'arm':arm,'sample_id':row['sample_id'],'action':raw,'raw_output':raw})
            write('predictions.json',predictions)
            del model,optimizer,params,batch,loss,tokens;torch.cuda.empty_cache()
    # Score only after all checkpoints and predictions; reference answers never enter inference.
    target_path=real.READINESS/'speed-action-intake-2026-09-29-001/development_action_targets.jsonl'
    m=json.loads((target_path.parent/'RUN_MANIFEST.json').read_text())
    if real.digest(target_path)!=m['output_hashes'][target_path.name]:raise ValueError('reference drift')
    references=[json.loads(s) for s in target_path.read_text().splitlines() if json.loads(s)['sample_id'] in eval_ids]
    results=[{'seed':seed,'arm':arm,'score':score(references,[p for p in predictions if p['seed']==seed and p['arm']==arm])}
        for seed in config['paired_seeds'] for arm in ('L0','L3')]
    write('RESULT.json',{'label':'TWO_SCENE_DEVELOPMENT_LEARNING_NOT_MAIN_EFFECT','training_scenes':2,
        'evaluation_scenes':len(eval_ids),'optimizer_updates':sum(r['optimizer_updates'] for r in logs),
        'results':results,'main_study_complete':False,'EBLC_superiority_claim':False})
    write('RUN_MANIFEST.json',{'project_id':'guardsynth-coc','run_id':output.name,'status':'COMPLETE',
        'input_hashes':hashes,'code_sha256':real.digest(Path(__file__)),
        'output_hashes':{str(p.relative_to(output)):real.digest(p) for p in output.rglob('*') if p.is_file()}})
    return {'updates':sum(r['optimizer_updates'] for r in logs),'checkpoints':len(logs)}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run-id',required=True)
    p.add_argument('--gpu',type=int,default=4);a=p.parse_args()
    if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*-[0-9]+',a.run_id):p.error('invalid run id')
    print(json.dumps(execute(real.BASE/a.run_id,a.gpu),indent=2))
