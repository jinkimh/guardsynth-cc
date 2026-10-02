#!/usr/bin/env python3
"""Build bounded-SMT inputs with one short-lived extraction worker per episode."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "PROJECT_REGISTRY.json").is_file())
DEFAULT_COHORT = (
    ROOT
    / "data/restricted/nvidia_physicalai/internal-derived/cohort-10"
    / "cohort-conformance.json"
)
DEFAULT_OUTPUT = (
    ROOT
    / "artifacts/results/restricted/alp-exp-005/feasibility-batch-v0"
    / "bounded-temporal-smt-v0/logic-inputs.json"
)
WORKER = Path(__file__).with_name("extract_logic_input_episode.py")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cohort", type=Path, default=DEFAULT_COHORT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    cohort = json.loads(args.cohort.read_text(encoding="utf-8"))
    args.output.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fragment_dir = args.output.parent / "input-fragments"
    fragment_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    env = os.environ.copy()
    required_paths = [
        str(ROOT / "third_party/physical_ai_av/src"),
        str(ROOT / "projects/03-sequential-coc-verification/experiments/feasibility"),
    ]
    env["PYTHONPATH"] = os.pathsep.join(
        required_paths + ([env["PYTHONPATH"]] if env.get("PYTHONPATH") else [])
    )
    records = []
    for index in range(len(cohort["episodes"])):
        fragment = fragment_dir / f"episode-{index:02d}.json"
        if not fragment.exists():
            subprocess.run(
                [
                    sys.executable,
                    str(WORKER),
                    "--episode-index",
                    str(index),
                    "--cohort",
                    str(args.cohort),
                    "--output",
                    str(fragment),
                ],
                check=True,
                env=env,
            )
        else:
            print(f"reused episode-{index:02d}", flush=True)
        records.append(json.loads(fragment.read_text(encoding="utf-8")))
        print(f"extracted episode-{index:02d}", flush=True)
    result = {
        "experiment_input": "ALP-EXP-005-BOUNDED-TEMPORAL-SMT-V0",
        "publication_control": "LICENSE_RESTRICTED_INTERNAL_DERIVED_INPUT",
        "episode_count": len(records),
        "episodes": records,
    }
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    args.output.chmod(0o600)
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
