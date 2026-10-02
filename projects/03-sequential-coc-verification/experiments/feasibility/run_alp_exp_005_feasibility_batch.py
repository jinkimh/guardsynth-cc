#!/usr/bin/env python3
"""Run a small, access-controlled Alpamayo feasibility batch.

The launcher reads clip identifiers only from the restricted cohort artifact and
uses pseudonymous episode directories.  Raw identifiers remain inside each
restricted run manifest written by the pinned ALP-EXP-005 runner.
"""

from __future__ import annotations

import argparse
import json
import os
import queue
import subprocess
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "PROJECT_REGISTRY.json").is_file())
DEFAULT_COHORT = (
    ROOT
    / "data/restricted/nvidia_physicalai/internal-derived/cohort-10"
    / "cohort-conformance.json"
)
DEFAULT_OUTPUT = (
    ROOT
    / "artifacts/results/restricted/alp-exp-005"
    / "feasibility-batch-v0"
)
RUNNER = ROOT / "runtime/alpamayo/run_alp_exp_005.py"
PYTHON = ROOT / "runtime/alpamayo/ar1_venv/bin/python"
MODEL_REVISION = "da911c5319ea5fd5c3de77f430f755f34ffd836e"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cohort", type=Path, default=DEFAULT_COHORT)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--gpus", required=True, help="Comma-separated physical GPU IDs")
    parser.add_argument("--seeds", default="42,43,44")
    parser.add_argument("--max-episodes", type=int, default=10)
    return parser.parse_args()


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def read_status(path: Path) -> str | None:
    try:
        return json.loads(path.read_text(encoding="utf-8")).get("status")
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    path.chmod(0o600)


def main() -> int:
    args = parse_args()
    gpu_ids = [item.strip() for item in args.gpus.split(",") if item.strip()]
    seeds = [int(item) for item in args.seeds.split(",") if item.strip()]
    if not gpu_ids:
        raise ValueError("At least one GPU ID is required")
    if not seeds:
        raise ValueError("At least one seed is required")

    cohort = json.loads(args.cohort.read_text(encoding="utf-8"))
    episodes = cohort["episodes"][: args.max_episodes]
    if not episodes:
        raise ValueError("The selected cohort is empty")

    args.output_root.mkdir(parents=True, exist_ok=True, mode=0o700)
    args.output_root.chmod(0o700)

    jobs: queue.Queue[dict[str, Any]] = queue.Queue()
    for episode_index, episode in enumerate(episodes):
        timestamp_us = int(episode["events"][0]["timestamp_us"])
        for seed in seeds:
            jobs.put(
                {
                    "episode_index": episode_index,
                    "clip_id": episode["clip_id"],
                    "timestamp_us": timestamp_us,
                    "seed": seed,
                }
            )

    results: list[dict[str, Any]] = []
    results_lock = threading.Lock()

    def worker(gpu_id: str) -> None:
        while True:
            try:
                job = jobs.get_nowait()
            except queue.Empty:
                return

            episode_name = f"episode-{job['episode_index']:02d}"
            run_dir = args.output_root / episode_name / f"seed-{job['seed']}"
            run_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
            run_dir.chmod(0o700)
            manifest_path = run_dir / "manifest.json"

            if read_status(manifest_path) == "EXECUTED":
                result = {
                    "episode": episode_name,
                    "seed": job["seed"],
                    "status": "SKIPPED_ALREADY_EXECUTED",
                    "returncode": 0,
                }
            else:
                command = [
                    str(PYTHON),
                    str(RUNNER),
                    "--clip-id",
                    job["clip_id"],
                    "--t0-us",
                    str(job["timestamp_us"]),
                    "--seed",
                    str(job["seed"]),
                    "--output-dir",
                    str(run_dir),
                    "--model-revision",
                    MODEL_REVISION,
                    "--attn-implementation",
                    "sdpa",
                ]
                environment = os.environ.copy()
                environment["CUDA_VISIBLE_DEVICES"] = gpu_id
                completed = subprocess.run(
                    command,
                    cwd=RUNNER.parent,
                    env=environment,
                    capture_output=True,
                    text=True,
                    check=False,
                )
                launcher_log = run_dir / "launcher-output.log"
                launcher_log.write_text(
                    completed.stdout + completed.stderr,
                    encoding="utf-8",
                )
                launcher_log.chmod(0o600)
                result = {
                    "episode": episode_name,
                    "seed": job["seed"],
                    "status": "EXECUTED" if completed.returncode == 0 else "FAILED",
                    "returncode": completed.returncode,
                }

            with results_lock:
                results.append(result)
            jobs.task_done()

    started_at = now_utc()
    threads = [threading.Thread(target=worker, args=(gpu_id,)) for gpu_id in gpu_ids]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    results.sort(key=lambda item: (item["episode"], item["seed"]))
    failed = sum(item["returncode"] != 0 for item in results)
    write_json(
        args.output_root / "batch-summary.json",
        {
            "experiment_id": "ALP-EXP-005-FEASIBILITY-BATCH-V0",
            "started_at_utc": started_at,
            "completed_at_utc": now_utc(),
            "episode_count": len(episodes),
            "seed_count": len(seeds),
            "run_count": len(results),
            "failed_run_count": failed,
            "attention_implementation": "sdpa",
            "reference_class": "COMPATIBILITY_FALLBACK_SDPA",
            "publication_control": "LICENSE_RESTRICTED_INTERNAL_RESULT",
            "clip_ids_in_summary": False,
            "runs": results,
        },
    )
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
