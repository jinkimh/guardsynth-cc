#!/usr/bin/env python3
"""Run rolling Alpamayo inference around a natural human CoC transition.

The default candidate is episode-00, whose CASCADE CoC changes from pedestrian
HOLD to RELEASE after 3.0 s.  Existing t0 outputs are reused; shifted prefixes
are resumable.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path


ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "PROJECT_REGISTRY.json").is_file())
RUNNER = ROOT / "runtime/alpamayo/run_alp_exp_005.py"
PYTHON = ROOT / "runtime/alpamayo/ar1_venv/bin/python"
BATCH = ROOT / "artifacts/results/restricted/alp-exp-005/feasibility-batch-v0"
BASE_EPISODE = BATCH / "episode-00"
DEFAULT_OUTPUT = BATCH / "episode-00-natural-transition-rolling-v0"
CLIP_ID = "caf6ea10-fc2b-47d1-814c-67c73b6cea9f"
BASE_T0_US = 7_958_186
HUMAN_RELEASE_OFFSET_US = 3_000_000
MODEL_REVISION = "da911c5319ea5fd5c3de77f430f755f34ffd836e"


def now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def parse_gpu_map(value: str) -> dict[int, int]:
    result: dict[int, int] = {}
    for pair in value.split(","):
        seed, gpu = pair.split(":", 1)
        result[int(seed)] = int(gpu)
    if not result:
        raise ValueError("at least one seed:gpu mapping is required")
    return result


def completed(output: Path) -> bool:
    manifest = output / "manifest.json"
    if not manifest.exists():
        return False
    data = json.loads(manifest.read_text(encoding="utf-8"))
    return data.get("status") == "EXECUTED" and data.get("exit_status") == 0


def run_dir(output: Path, offset_us: int, seed: int) -> Path:
    if offset_us == 0:
        return BASE_EPISODE / f"seed-{seed}"
    return output / f"prefix-{offset_us // 1000:04d}ms/seed-{seed}"


def command(offset_us: int, seed: int, output: Path) -> list[str]:
    return [
        str(PYTHON),
        str(RUNNER),
        "--clip-id",
        CLIP_ID,
        "--t0-us",
        str(BASE_T0_US + offset_us),
        "--seed",
        str(seed),
        "--output-dir",
        str(output),
        "--model-revision",
        MODEL_REVISION,
        "--attn-implementation",
        "sdpa",
    ]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--seed-gpus", default="42:1,43:4,44:5")
    parser.add_argument("--step-ms", type=int, default=500)
    parser.add_argument("--end-ms", type=int, default=4000)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    seed_to_gpu = parse_gpu_map(args.seed_gpus)
    if args.step_ms <= 0 or args.end_ms < args.step_ms:
        raise ValueError("require 0 < step-ms <= end-ms")
    offsets_us = tuple(range(0, args.end_ms * 1000 + 1, args.step_ms * 1000))
    missing_base = [seed for seed in seed_to_gpu if not completed(run_dir(args.output, 0, seed))]
    if missing_base:
        raise RuntimeError(f"missing completed base t0 runs for seeds {missing_base}")

    plan = {
        "experiment": "EPISODE_00_NATURAL_TRANSITION_ROLLING_V0",
        "clip_id": CLIP_ID,
        "base_t0_us": BASE_T0_US,
        "human_release_offset_us": HUMAN_RELEASE_OFFSET_US,
        "prefix_offsets_us": list(offsets_us),
        "seeds": sorted(seed_to_gpu),
        "physical_gpu_assignment": {str(seed): gpu for seed, gpu in seed_to_gpu.items()},
        "new_run_count": (len(offsets_us) - 1) * len(seed_to_gpu),
    }
    if args.dry_run:
        plan["commands"] = [
            command(offset_us, seed, run_dir(args.output, offset_us, seed))
            for offset_us in offsets_us[1:]
            for seed in sorted(seed_to_gpu)
        ]
        print(json.dumps(plan, indent=2))
        return 0

    args.output.mkdir(parents=True, exist_ok=True, mode=0o700)
    args.output.chmod(0o700)
    records: list[dict[str, object]] = []
    for offset_us in offsets_us[1:]:
        processes = []
        for seed, physical_gpu in seed_to_gpu.items():
            directory = run_dir(args.output, offset_us, seed)
            directory.mkdir(parents=True, exist_ok=True, mode=0o700)
            directory.chmod(0o700)
            if completed(directory):
                record = {
                    "offset_us": offset_us,
                    "seed": seed,
                    "physical_gpu": physical_gpu,
                    "status": "SKIP_COMPLETED",
                }
                records.append(record)
                print(json.dumps(record), flush=True)
                continue
            log_path = directory / "launcher-output.log"
            log = log_path.open("w", encoding="utf-8")
            environment = os.environ.copy()
            environment["CUDA_VISIBLE_DEVICES"] = str(physical_gpu)
            process = subprocess.Popen(
                command(offset_us, seed, directory),
                cwd=ROOT,
                env=environment,
                stdout=log,
                stderr=subprocess.STDOUT,
                text=True,
            )
            processes.append((seed, physical_gpu, directory, log_path, log, process))
        for seed, physical_gpu, directory, log_path, log, process in processes:
            return_code = process.wait()
            log.close()
            log_path.chmod(0o600)
            status = "EXECUTED" if return_code == 0 and completed(directory) else "FAILED"
            record = {
                "offset_us": offset_us,
                "t0_us": BASE_T0_US + offset_us,
                "seed": seed,
                "physical_gpu": physical_gpu,
                "return_code": return_code,
                "status": status,
                "output": str(directory.relative_to(ROOT)),
            }
            records.append(record)
            print(json.dumps(record), flush=True)
            if status != "EXECUTED":
                raise RuntimeError(f"rolling inference failed: {record}")

    manifest = {
        **plan,
        "created_at_utc": now(),
        "base_prefix_source": str(BASE_EPISODE.relative_to(ROOT)),
        "records": records,
        "publication_control": "LICENSE_RESTRICTED_INTERNAL_RESULT",
    }
    path = args.output / "rolling-run-manifest.json"
    path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    path.chmod(0o600)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
