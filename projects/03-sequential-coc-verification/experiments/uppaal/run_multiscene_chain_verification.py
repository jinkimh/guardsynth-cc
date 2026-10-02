#!/usr/bin/env python3
"""Run verifyta for the generated multi-scene chain model."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

from generate_multiscene_chain_model import MODEL_DIR, QUERIES, write_model
from run_verification import ANSI_ESCAPE, DEFAULT_VERIFYTA, classify_output


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--verifyta", type=Path, default=DEFAULT_VERIFYTA)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("artifacts/results/public/multiscene-chain/uppaal-verification-result.json"),
    )
    args = parser.parse_args()

    profile = write_model()
    model = MODEL_DIR / profile["model"]
    query = MODEL_DIR / "multiscene-chain.q"
    completed = subprocess.run(
        [str(args.verifyta), "-q", "-t1", str(model), str(query)],
        capture_output=True,
        text=True,
        check=False,
    )
    output = ANSI_ESCAPE.sub("", completed.stdout + completed.stderr)
    status, verdicts = classify_output(output, len(QUERIES))
    trace_dir = args.output.parent / "uppaal-traces"
    trace_dir.mkdir(parents=True, exist_ok=True)
    trace_path = trace_dir / "scene-0130-to-scene-0133.txt"
    trace_path.write_text(output, encoding="utf-8")

    report = {
        "checker": "UPPAAL_MULTISCENE_CHAIN",
        "verifyta": str(args.verifyta),
        "model": str(model),
        "query_file": str(query),
        "status": status,
        "exit_code": completed.returncode,
        "queries": [
            {"index": index + 1, "query": query_text, "satisfied": verdict}
            for index, (query_text, verdict) in enumerate(zip(QUERIES, verdicts))
        ],
        "profile": profile,
        "interpretation": {
            "scene_boundary_policy": (
                "All three scene gaps are below MAX_BOUNDARY_GAP=1000ms, so the "
                "boundary property is expected to hold."
            ),
            "deadline_policy": (
                "The first trusted slow/yield obligation in scene-0130 has no derived "
                "ego-speed response witness within 3000ms, so the deadline property is "
                "expected to fail for this strict detector setting."
            ),
            "evidence_limit": (
                "The response is a weak speed/trajectory witness, not actuator-level "
                "brake or throttle supervision."
            ),
        },
        "trace_path": str(trace_path),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
