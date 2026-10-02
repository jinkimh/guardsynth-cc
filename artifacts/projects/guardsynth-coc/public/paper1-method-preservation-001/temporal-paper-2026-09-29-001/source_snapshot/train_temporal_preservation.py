"""Matched Project04 VLM updates using attributed read-only Project01 trainer."""
import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import gc
import json
import os
from pathlib import Path
import time
from types import SimpleNamespace

from temporal_preservation import BASE, ROOT, PRIOR, CONFIG, examples, independent_score, sha
from run_real_development import idle_gpu


def execute(run_id,protocol_id,gpu):
    output=BASE/run_id;protocol=BASE/protocol_id
    if output.exists(): raise FileExistsError(output)
    manifest=json.loads((protocol/'RUN_MANIFEST.json').read_text())
    for name,digest in manifest['output_hashes'].items():
        if sha(protocol/name)!=digest: raise ValueError('frozen protocol output drift')
    for name,digest in manifest['input_hashes'].items():
        if sha(ROOT/name)!=digest: raise ValueError('frozen protocol source drift')
    cfg=json.loads((protocol/'protocol.json').read_text())
    resource=idle_gpu(gpu)
    os.environ['CUDA_VISIBLE_DEVICES']=resource['uuid']
    os.environ['HF_HUB_OFFLINE']='1';os.environ['TOKENIZERS_PARALLELISM']='false'
    import torch
    from peft import LoraConfig,TaskType,get_peft_model
    from transformers import AutoProcessor,Qwen3VLForConditionalGeneration
    from vlm_guard_learning import train_qwen_temporal_guard_lora as prior
    from vlm_guard_learning.train_qwen_guard_lora import language_attention_targets,seed_all
    torch.set_num_threads(4)
    model_path=Path.home()/'.cache/huggingface/hub/models--Qwen--Qwen3-VL-2B-Instruct/snapshots'/cfg['model_revision']
    output.mkdir(parents=True)
    inputs={str(protocol.relative_to(ROOT)/'RUN_MANIFEST.json'):sha(protocol/'RUN_MANIFEST.json'),
            str(Path(__file__).relative_to(ROOT)):sha(Path(__file__))}
    (output/'RUN_MANIFEST.json').write_text(json.dumps({'project_id':'guardsynth-coc','protocol_id':cfg['protocol_id'],
        'status':'RUNNING','input_hashes':inputs,'resource':resource,
        'started_at_utc':datetime.now(timezone.utc).isoformat()},indent=2)+'\n')
    processor=AutoProcessor.from_pretrained(model_path,local_files_only=True)
    processor.tokenizer.padding_side='right'
    total=0
    for seed in cfg['seeds']:
        for arm in cfg['arms']:
            started=time.monotonic();seed_all(seed)
            target=output/f'{arm.lower()}-seed{seed}';target.mkdir()
            mode='COC_ONLY' if arm=='P0' else 'RICH_COC'
            model=Qwen3VLForConditionalGeneration.from_pretrained(model_path,local_files_only=True,
                dtype=torch.bfloat16,attn_implementation='sdpa').to('cuda:0')
            model.config.use_cache=False
            model=get_peft_model(model,LoraConfig(r=8,lora_alpha=16,lora_dropout=.05,bias='none',
                task_type=TaskType.CAUSAL_LM,target_modules=language_attention_targets(model)))
            model.enable_input_require_grads()
            training=examples(seed,'train',cfg['train_scenes'],arm)
            args=SimpleNamespace(**{k:cfg[k] for k in ('batch_size','gradient_accumulation','epochs','learning_rate')},
                                 seed=seed,device='cuda:0')
            # Verify actual visual processor and assistant-only loss masking before updates.
            encoded=prior.TemporalCollator(processor,mode)._encode(training[0])
            if not (encoded['labels']==-100).any() or not (encoded['labels']!=-100).any() or encoded['pixel_values'].numel()==0:
                raise ValueError('processor/loss mask failure')
            print(f'START {arm} seed={seed} rows={len(training)}',flush=True)
            history=prior.train(model,processor,training,mode,args)
            updates=sum(h['optimizer_steps'] for h in history)
            if updates!=cfg['optimizer_updates_per_arm_seed']: raise ValueError('update budget mismatch')
            total+=updates
            model.save_pretrained(target/'adapter')
            # Checkpoint and losses survive even if evaluation is interrupted.
            (target/'training.json').write_text(json.dumps({'arm':arm,'seed':seed,'history':history,
                'updates':updates,'elapsed_seconds':time.monotonic()-started},indent=2)+'\n')
            print(f'CHECKPOINT {arm} seed={seed} updates={updates}',flush=True)
            results={}
            groups=[('benchmark_regression',seed,'test'),('new_seed_confirmation',cfg['new_holdout_seed'],'test'),
                    ('unseen_time',cfg['unseen_holdout_seed'],'test_unseen')]
            for group,gseed,split in groups:
                data=examples(gseed,split,cfg['test_scenes'],arm)
                rows=[];model.eval()
                with (target/(group+'.jsonl')).open('w') as f:
                    for e in data:
                        prediction,raw=prior.generate_choice(model,processor,e,mode,'cuda:0')
                        row={'scene_id':e.scene.scene_id,'contract_level':e.contract_level,'prediction':prediction,
                             'raw':raw,**independent_score(e,prediction)}
                        f.write(json.dumps(row)+'\n');f.flush();rows.append(row)
                metrics={key:sum(r[field] for r in rows)/len(rows) for key,field in
                    [('guard_violation_rate','guard_violation'),('safe_goal_completion_rate','safe_goal_complete'),
                     ('deadlock_rate','deadlock'),('accuracy','correct'),('coverage','valid')]}
                pairs=[rows[i:i+2] for i in range(0,len(rows),2)]
                metrics['contract_swap_pair_accuracy']=sum(all(r['correct'] for r in pair) for pair in pairs)/len(pairs)
                results[group]={'metrics':metrics,'rows':len(rows)}
                print(f'EVAL {arm} {seed} {group} {metrics}',flush=True)
            (target/'RESULT.json').write_text(json.dumps({'arm':arm,'seed':seed,'updates':updates,
                'evaluation':results,'elapsed_seconds':time.monotonic()-started},indent=2)+'\n')
            (target/'RUN_MANIFEST.json').write_text(json.dumps({'output_hashes':{
                str(p.relative_to(target)):sha(p) for p in target.rglob('*') if p.is_file()}},indent=2)+'\n')
            del model;gc.collect();torch.cuda.empty_cache()
    (output/'RESULT.json').write_text(json.dumps({'status':'COMPLETE','optimizer_updates':total,
        'arm_seed_runs':9,'prediction_count':9*3*cfg['test_scenes']*2},indent=2)+'\n')
    m=json.loads((output/'RUN_MANIFEST.json').read_text());m['status']='COMPLETE'
    m['output_hashes']={str(p.relative_to(output)):sha(p) for p in output.rglob('*') if p.is_file() and p!=output/'RUN_MANIFEST.json'}
    (output/'RUN_MANIFEST.json').write_text(json.dumps(m,indent=2)+'\n')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--run-id',required=True);p.add_argument('--protocol-id',required=True)
    p.add_argument('--gpu',type=int,default=4);a=p.parse_args();execute(a.run_id,a.protocol_id,a.gpu)
