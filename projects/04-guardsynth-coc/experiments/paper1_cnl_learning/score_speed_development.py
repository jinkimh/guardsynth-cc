"""Independent ACTION-reference diagnostics, not certified safety-violation gold."""
import argparse
import json
from pathlib import Path
import random

ACTIONS = {'MAINTAIN_SPEED', 'DECELERATE', 'STOP_OR_WAIT', 'START_OR_ACCELERATE'}


def score(targets, predictions):
    ids = [r['sample_id'] for r in targets]
    if len(set(ids)) != len(ids) or [r['sample_id'] for r in predictions] != ids:
        raise ValueError('fixed target denominator/order mismatch')
    rows = []
    for target, prediction in zip(targets, predictions):
        action = prediction.get('action')
        labels = target['endpoint_assessments']  # Three masks are never converted into labels.
        valid = action in ACTIONS
        selected = labels.get(action) if valid else None
        progress = [a for a in ('MAINTAIN_SPEED', 'START_OR_ACCELERATE') if labels[a] == 'APPROPRIATE']
        rows.append({'sample_id': target['sample_id'], 'clip_group': target['clip_group'],
            'prediction': action, 'valid_output': valid, 'selected_reference': selected,
            'reference_inappropriate': int(selected == 'INAPPROPRIATE') if selected in ('APPROPRIATE','INAPPROPRIATE') else None,
            'normal_progress_reference': int(action in progress) if progress else None,
            'unnecessary_stop_reference': int(action == 'STOP_OR_WAIT') if labels['STOP_OR_WAIT'] == 'INAPPROPRIATE' else None})
    metrics = {}
    groups = sorted({r['clip_group'] for r in rows})
    rng = random.Random(20260929)
    draws = [rng.choices(groups, k=len(groups)) for _ in range(2000)]
    for name in ('reference_inappropriate','normal_progress_reference','unnecessary_stop_reference'):
        values = [r[name] for r in rows if r[name] is not None]
        samples = []
        for draw in draws:
            v = [r[name] for g in draw for r in rows if r['clip_group']==g and r[name] is not None]
            if v: samples.append(sum(v)/len(v))
        samples.sort()
        metrics[name] = {'numerator':sum(values),'denominator':len(values),
            'rate':sum(values)/len(values) if values else None,
            'clip_bootstrap_95_percentile': [samples[int(.025*(len(samples)-1))],samples[int(.975*(len(samples)-1))]] if samples else None}
    return {'rows':rows,'metrics':metrics,'scene_denominator':len(rows),'clip_groups':len(groups),
        'valid_output_count':sum(r['valid_output'] for r in rows),
        'known_selected_reference_count':sum(r['selected_reference'] in ('APPROPRIATE','INAPPROPRIATE') for r in rows),
        'safety_violation_rate':'NOT_IDENTIFIED_BY_APPROPRIATENESS_ONLY_REFERENCES',
        'physical_goal_completion':'NOT_EVALUATED', 'main_effect':'NOT_EVALUATED',
        'uncertainty_scope':'CLIP_RESAMPLING_NOT_REVIEWER_BIAS_OR_MAIN_POWER'}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--targets',type=Path,required=True)
    p.add_argument('--predictions',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    result=score([json.loads(x) for x in a.targets.read_text().splitlines()], [json.loads(x) for x in a.predictions.read_text().splitlines()])
    with a.output.open('x') as f:f.write(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
