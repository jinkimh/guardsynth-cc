#!/usr/bin/env python3
"""Launch resumable episode-02 rolling-prefix Alpamayo inference."""

from __future__ import annotations

import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
RUNNER = ROOT / "runtime/alpamayo/run_alp_exp_005.py"
PYTHON = ROOT / "runtime/alpamayo/ar1_venv/bin/python"
BATCH = ROOT / "artifacts/results/restricted/alp-exp-005/feasibility-batch-v0"
OUTPUT = BATCH / "episode-02-rolling-prefix-v0"
CLIP_ID = "13f0af4c-2565-4a4d-b765-7f397f1d1684"
BASE_T0_US = 5_148_839
MODEL_REVISION = "da911c5319ea5fd5c3de77f430f755f34ffd836e"
OFFSETS_US = tuple(range(500_000, 3_000_001, 500_000))
SEED_TO_PHYSICAL_GPU = {42: 1, 43: 4, 44: 5}


def now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def completed(output: Path) -> bool:
    manifest = output / "manifest.json"
    if not manifest.exists():
        return False
    data = json.loads(manifest.read_text(encoding="utf-8"))
    return data.get("status") == "EXECUTED" and data.get("exit_status") == 0


def command(offset_us: int, seed: int, output: Path) -> list[str]:
    return [
        str(PYTHON), str(RUNNER),
        "--clip-id", CLIP_ID,
        "--t0-us", str(BASE_T0_US + offset_us),
        "--seed", str(seed),
        "--output-dir", str(output),
        "--model-revision", MODEL_REVISION,
        "--attn-implementation", "sdpa",
    ]


def main() -> int:
    OUTPUT.mkdir(parents=True, exist_ok=True, mode=0o700)
    OUTPUT.chmod(0o700)
    records: list[dict[str, object]] = []
    for offset_us in OFFSETS_US:
        processes = []
        for seed, physical_gpu in SEED_TO_PHYSICAL_GPU.items():
            run_dir = OUTPUT / f"prefix-{offset_us // 1000:04d}ms/seed-{seed}"
            run_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
            run_dir.chmod(0o700)
            if completed(run_dir):
                print(json.dumps({"offset_us": offset_us, "seed": seed, "status": "SKIP_COMPLETED"}), flush=True)
                records.append({"offset_us": offset_us, "seed": seed, "physical_gpu": physical_gpu, "status": "SKIP_COMPLETED"})
                continue
            log_path = run_dir / "launcher-output.log"
            log = log_path.open("w", encoding="utf-8")
            env = os.environ.copy()
            env["CUDA_VISIBLE_DEVICES"] = str(physical_gpu)
            process = subprocess.Popen(
                command(offset_us, seed, run_dir),
                cwd=ROOT,
                env=env,
                stdout=log,
                stderr=subprocess.STDOUT,
                text=True,
            )
            processes.append((seed, physical_gpu, run_dir, log_path, log, process))
        for seed, physical_gpu, run_dir, log_path, log, process in processes:
            return_code = process.wait()
            log.close()
            log_path.chmod(0o600)
            status = "EXECUTED" if return_code == 0 and completed(run_dir) else "FAILED"
            record = {
                "offset_us": offset_us,
                "t0_us": BASE_T0_US + offset_us,
                "seed": seed,
                "physical_gpu": physical_gpu,
                "return_code": return_code,
                "status": status,
                "output": str(run_dir.relative_to(ROOT)),
            }
            records.append(record)
            print(json.dumps(record), flush=True)
            if status != "EXECUTED":
                raise RuntimeError(f"rolling inference failed: {record}")

    manifest = {
        "experiment": "EPISODE_02_ROLLING_PREFIX_V0",
        "created_at_utc": now(),
        "clip_id": CLIP_ID,
        "base_t0_us": BASE_T0_US,
        "prefix_offsets_us": [0, *OFFSETS_US],
        "seeds": sorted(SEED_TO_PHYSICAL_GPU),
        "physical_gpu_assignment": {str(k): v for k, v in SEED_TO_PHYSICAL_GPU.items()},
        "base_prefix_source": "artifacts/results/restricted/alp-exp-005/feasibility-batch-v0/episode-02",
        "new_run_count": len(OFFSETS_US) * len(SEED_TO_PHYSICAL_GPU),
        "records": records,
        "publication_control": "LICENSE_RESTRICTED_INTERNAL_RESULT",
    }
    path = OUTPUT / "rolling-run-manifest.json"
    path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    path.chmod(0o600)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
