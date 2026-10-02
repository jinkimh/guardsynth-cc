"""Read-only nine-adapter inference; no optimizer, new training or label feedback."""
import argparse
import gc
import hashlib
import json
import os
from pathlib import Path
from datetime import datetime,timezone
import temporal_diversity as d
from run_real_development import idle_gpu


def execute(output,protocol,gpu):
    if output.exists():raise FileExistsError(output)
    d.verify_manifest(protocol,inputs=True)
    config=json.loads((protocol/'protocol.json').read_text())
    cases=[json.loads(line) for line in (protocol/'cases.jsonl').read_text().splitlines()]
    resource=idle_gpu(gpu)
    os.environ['CUDA_VISIBLE_DEVICES']=resource['uuid'];os.environ['HF_HUB_OFFLINE']='1'
    os.environ['TOKENIZERS_PARALLELISM']='false'
    import torch
    from peft import PeftModel
    from transformers import AutoProcessor,Qwen3VLForConditionalGeneration
    from PIL import Image
    from vlm_guard_learning.train_qwen_temporal_guard_lora import parse_choice
    torch.set_num_threads(4)
    model_path=Path.home()/'.cache/huggingface/hub/models--Qwen--Qwen3-VL-2B-Instruct/snapshots'/config['model_revision']
    output.mkdir(parents=True)
    d.dump(output/'RUN_MANIFEST.json',{'project_id':'guardsynth-coc','status':'RUNNING',
        'resource':resource,'started_at_utc':datetime.now(timezone.utc).isoformat(),
        'input_hashes':{str(protocol/'RUN_MANIFEST.json'):d.primary.sha(protocol/'RUN_MANIFEST.json')}})
    processor=AutoProcessor.from_pretrained(model_path,local_files_only=True)
    processor.tokenizer.padding_side='right'
    physical=0
    for seed in d.SEEDS:
        for arm in d.ARMS:
            model=Qwen3VLForConditionalGeneration.from_pretrained(model_path,local_files_only=True,
                dtype=torch.bfloat16,attn_implementation='sdpa').to('cuda:0')
            model=PeftModel.from_pretrained(model,d.LEARNING/f'{arm.lower()}-seed{seed}'/'adapter',is_trainable=False)
            model.eval();cache={};count=0
            with (output/f'{arm.lower()}-seed{seed}.jsonl').open('w') as stream:
                for case in cases:
                    key=case['input_sha256'][arm];reused=key in cache
                    if not reused:
                        image=Image.open(protocol/case['image']).convert('RGB')
                        user={'role':'user','content':[{'type':'image','image':image},
                            {'type':'text','text':case['prompts'][arm]}]}
                        batch=processor.apply_chat_template([user],tokenize=True,add_generation_prompt=True,
                            return_dict=True,return_tensors='pt')
                        batch={k:v.to('cuda:0') for k,v in batch.items()}
                        length=batch['input_ids'].shape[1]
                        with torch.inference_mode(),torch.autocast('cuda',dtype=torch.bfloat16):
                            tokens=model.generate(**batch,do_sample=False,max_new_tokens=config['max_new_tokens'],
                                use_cache=True,pad_token_id=processor.tokenizer.pad_token_id)
                        raw=processor.tokenizer.decode(tokens[0,length:],skip_special_tokens=True).strip()
                        cache[key]=(parse_choice(raw),raw);physical+=1
                    prediction,raw=cache[key]
                    row={'case_id':case['case_id'],'arm':arm,'seed':seed,'prediction':prediction,'raw':raw,
                         'cached_identical_input':reused,'input_sha256':key,
                         'source_score':d.oracle(case,prediction),
                         'core_execution':d.execute_choice(case,prediction)}
                    if case['image_mode']=='swapped':
                        row['image_implied_score']=d.oracle(case,prediction,case['implied_clear_ms'])
                        row['image_implied_core']=d.execute_choice(case,prediction,case['implied_clear_ms'])
                    stream.write(json.dumps(row)+'\n');stream.flush();count+=1
            print(f'COMPLETE {arm} seed={seed}: rows={count}, unique model calls={len(cache)}',flush=True)
            del model;gc.collect();torch.cuda.empty_cache()
    d.dump(output/'RESULT.json',{'status':'COMPLETE','prediction_rows':len(cases)*9,
        'physical_model_calls':physical,'optimizer_updates':0,'reused_adapter_count':9})
    manifest=json.loads((output/'RUN_MANIFEST.json').read_text());manifest['status']='COMPLETE'
    manifest['output_hashes']={p.name:d.primary.sha(p) for p in output.iterdir() if p.is_file() and p.name!='RUN_MANIFEST.json'}
    d.dump(output/'RUN_MANIFEST.json',manifest)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--run-id',required=True);p.add_argument('--protocol-id',required=True)
    p.add_argument('--gpu',type=int,default=4);a=p.parse_args()
    execute(d.BASE/a.run_id,d.BASE/a.protocol_id,a.gpu)
