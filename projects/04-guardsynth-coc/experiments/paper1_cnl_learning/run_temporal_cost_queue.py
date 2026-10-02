"""Run the approved cost comparison only after all upstream fits are complete."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time

import train_temporal_expansion as parent

UPSTREAM = parent.d.t.BASE / 'temporal-expansion-learning-2026-09-29-001'
SCRIPT = Path(__file__).with_name('train_temporal_cost.py')


def upstream_state(run):
    """A scientific negative verdict is not an execution failure."""
    try:
        result = json.loads((run / 'RESULT.json').read_text())
        manifest = json.loads((run / 'RUN_MANIFEST.json').read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return 'WAITING_UPSTREAM_SNAPSHOT'
    if result.get('status') == 'FAILED' or manifest.get('status') == 'FAILED':
        raise RuntimeError('Upstream execution failed; no replacement or automatic retraining.')
    if result.get('status') != 'COMPLETE' or manifest.get('status') != 'COMPLETE':
        return 'WAITING_UPSTREAM_COMPLETION'
    if result.get('fits') != 18 or result.get('optimizer_updates') != 3240:
        raise ValueError('Upstream completed with unexpected fit/update counts.')
    return 'READY'


def verify_parent():
    manifest = json.loads((UPSTREAM / 'RUN_MANIFEST.json').read_text())
    parent.verify_hashes(UPSTREAM, manifest)
    inputs = {'parent_manifest_sha256': parent.d.t.sha(UPSTREAM / 'RUN_MANIFEST.json'), 'adapters': {}}
    for seed in parent.SEEDS:
        fit = UPSTREAM / f'p2-seed{seed}'
        record = json.loads((fit / 'training.json').read_text())
        if record['optimizer_updates'] != 180:
            raise ValueError('P2 source checkpoint has wrong budget')
        inputs['adapters'][str(seed)] = {name: parent.d.t.sha(fit / 'adapter' / name)
            for name in ('adapter_config.json', 'adapter_model.safetensors')}
    return inputs


def run_queue(protocol, output, queue):
    if output.exists() or queue.exists():
        raise FileExistsError('Run/queue already exists; refusing duplicate launch.')
    protocol_manifest = json.loads((protocol / 'RUN_MANIFEST.json').read_text())
    parent.verify_hashes(protocol, protocol_manifest)
    queue.mkdir(parents=True)
    manifest = {'project_id': 'guardsynth-coc', 'pid': os.getpid(),
        'started_at_utc': datetime.now(timezone.utc).isoformat(),
        'upstream_run': str(UPSTREAM.relative_to(parent.d.t.ROOT)),
        'input_hashes': {str(p.relative_to(parent.d.t.ROOT)): parent.d.t.sha(p) for p in
                        (Path(__file__), SCRIPT, protocol / 'RUN_MANIFEST.json')}}
    parent.d.dump(queue / 'RUN_MANIFEST.json', manifest)
    verified_parent = False
    try:
        while True:
            state = upstream_state(UPSTREAM)
            detail = []
            if state == 'READY':
                if not verified_parent:
                    parent.d.dump(queue / 'parent_binding.json', verify_parent())
                    verified_parent = True
                for gpu in (2, 4):
                    try:
                        resource = parent.idle_gpu(gpu)
                    except RuntimeError as exc:
                        detail.append(str(exc))
                        continue
                    parent.verify_hashes(protocol, protocol_manifest)
                    if parent.d.t.sha(SCRIPT) != manifest['input_hashes'][str(SCRIPT.relative_to(parent.d.t.ROOT))]:
                        raise ValueError('Cost learner changed after queue admission')
                    parent.d.dump(queue / 'RESULT.json', {'status': 'RUNNING_CHILD',
                        'run_id': output.name, 'resource': resource})
                    process = subprocess.run([sys.executable, '-u', str(SCRIPT),
                        '--protocol-id', protocol.name, '--run-id', output.name, '--gpu', str(gpu)],
                        cwd=parent.d.t.ROOT, check=False)
                    if process.returncode:
                        # A race for idle resource is retried only before any run output exists.
                        try:
                            parent.idle_gpu(gpu)
                        except RuntimeError:
                            if not output.exists():
                                state = 'WAITING_FOR_IDLE_GPU'; break
                        raise RuntimeError(f'Cost learner exited with code{process.returncode}; outputs preserved.')
                    final = json.loads((output / 'RESULT.json').read_text())
                    if final.get('status') != 'COMPLETE':
                        raise RuntimeError('Child exited without a complete result.')
                    parent.d.dump(queue / 'RESULT.json', {'status': 'COMPLETE', 'run_id': output.name})
                    return
                else:
                    state = 'WAITING_FOR_IDLE_GPU'
            parent.d.dump(queue / 'RESULT.json', {'status': state, 'run_id': output.name,
                'last_checked_utc': datetime.now(timezone.utc).isoformat(), 'details': detail,
                'cost_training_updates': 0})
            print(state + ': existing SFT workload unchanged; retry in30seconds.', flush=True)
            time.sleep(30)
    except Exception as exc:
        parent.d.dump(queue / 'RESULT.json', {'status': 'FAILED', 'error': str(exc), 'run_id': output.name})
        raise
    finally:
        manifest['output_hashes'] = {p.name: parent.d.t.sha(p) for p in queue.iterdir()
                                     if p.is_file() and p.name != 'RUN_MANIFEST.json'}
        parent.d.dump(queue / 'RUN_MANIFEST.json', manifest)


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--protocol-id', required=True)
    p.add_argument('--run-id', required=True)
    p.add_argument('--queue-id', required=True)
    args = p.parse_args()
    for value, kind in ((args.protocol_id, 'protocol'), (args.run_id, 'learning'), (args.queue_id, 'queue')):
        if not re.fullmatch(r'temporal-cost-' + kind + r'-\d{4}-\d{2}-\d{2}-\d{3}', value):
            p.error('Invalid owner-scoped run identifier.')
    run_queue(parent.d.t.BASE / args.protocol_id, parent.d.t.BASE / args.run_id, parent.d.t.BASE / args.queue_id)
