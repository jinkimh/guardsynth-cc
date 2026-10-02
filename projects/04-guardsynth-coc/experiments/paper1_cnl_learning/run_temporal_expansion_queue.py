"""Wait for an idle local GPU, then execute the frozen expansion exactly once."""
import argparse
from datetime import datetime, timezone
import os
from pathlib import Path
import re
import time

import train_temporal_expansion as training


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--protocol-id', required=True)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--queue-id', required=True)
    args = parser.parse_args()
    for value, kind in ((args.protocol_id, 'protocol'), (args.run_id, 'learning'), (args.queue_id, 'queue')):
        if not re.fullmatch(r'temporal-expansion-' + kind + r'-\d{4}-\d{2}-\d{2}-\d{3}', value):
            parser.error('invalid run identifier')
    base = training.d.t.BASE
    run, protocol, queue = base / args.run_id, base / args.protocol_id, base / args.queue_id
    if run.exists() or queue.exists():
        raise FileExistsError('run or queue already exists; no duplicate launch')
    queue.mkdir(parents=True)
    manifest = {'project_id': 'guardsynth-coc', 'pid': os.getpid(),
        'started_at_utc': datetime.now(timezone.utc).isoformat(), 'candidate_gpus': [2, 4],
        'input_hashes': {str(p.relative_to(training.d.t.ROOT)): training.d.t.sha(p) for p in
                        (Path(__file__), protocol / 'RUN_MANIFEST.json')}}
    training.d.dump(queue / 'RUN_MANIFEST.json', manifest)
    try:
        while True:
            snapshots = []
            for gpu in (2, 4):
                try:
                    resource = training.idle_gpu(gpu)
                except RuntimeError as exc:
                    snapshots.append(str(exc))
                    continue
                training.d.dump(queue / 'RESULT.json', {'status': 'LAUNCHING', 'gpu': gpu,
                    'run_id': args.run_id, 'resource': resource})
                try:
                    training.execute(run, protocol, gpu)
                except RuntimeError as exc:
                    # execute rechecks occupancy immediately before model allocation.
                    if not run.exists() and 'GPU is occupied' in str(exc):
                        snapshots.append(str(exc))
                        continue
                    raise
                training.d.dump(queue / 'RESULT.json', {'status': 'COMPLETE', 'run_id': args.run_id})
                return
            training.d.dump(queue / 'RESULT.json', {'status': 'WAITING_FOR_IDLE_GPU',
                'run_id': args.run_id, 'last_checked_utc': datetime.now(timezone.utc).isoformat(),
                'snapshots': snapshots, 'optimizer_updates': 0})
            print('WAITING_FOR_IDLE_GPU: retry in30seconds; no existing workloads interrupted.', flush=True)
            time.sleep(30)
    except Exception as exc:
        training.d.dump(queue / 'RESULT.json', {'status': 'FAILED', 'error': str(exc), 'run_id': args.run_id})
        raise
    finally:
        manifest['output_hashes'] = {p.name: training.d.t.sha(p) for p in queue.iterdir()
                                     if p.is_file() and p.name != 'RUN_MANIFEST.json'}
        training.d.dump(queue / 'RUN_MANIFEST.json', manifest)


if __name__ == '__main__':
    main()
