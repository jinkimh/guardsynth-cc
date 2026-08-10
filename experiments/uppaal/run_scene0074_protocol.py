#!/usr/bin/env python3
"""Verify the two repeated-CoC obligation semantics for scene-0074."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

from generate_scene0074_protocol import (
    DEADLINE_MS,
    EXPECTED,
    MODEL_DIR,
    QUERIES,
    TRACE_EVENTS,
    write_model,
)
from run_verification import ANSI_ESCAPE, DEFAULT_VERIFYTA, classify_output


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = (
    ROOT
    / "artifacts/results/public/scene-0074"
    / "uppaal-repeated-obligation-semantics-result.json"
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--verifyta", type=Path, default=DEFAULT_VERIFYTA)
    parser.add_argument("--model-dir", type=Path, default=MODEL_DIR)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    model_path, query_path = write_model(args.model_dir)
    completed = subprocess.run(
        [str(args.verifyta), "-q", str(model_path), str(query_path)],
        capture_output=True,
        text=True,
        check=False,
    )
    raw_output = ANSI_ESCAPE.sub("", completed.stdout + completed.stderr)
    status, verdicts = classify_output(raw_output, len(QUERIES))
    report = {
        "checker": "UPPAAL_SCENE_0074_REPEATED_OBLIGATION_SEMANTICS",
        "status": status,
        "deadline_ms": DEADLINE_MS,
        "trace_origin_scene_time_s": 3.4,
        "trace_events_relative_ms": [
            {"at_ms": at_ms, "type": event_type}
            for at_ms, event_type in TRACE_EVENTS
        ],
        "response_profile": {
            "window_s": 0.5,
            "minimum_delta_mps": 0.1,
            "minimum_direction_fraction": 0.7,
        },
        "queries": [
            {
                "query": query,
                "satisfied": verdict,
                "expected": expected,
            }
            for query, verdict, expected in zip(QUERIES, verdicts, EXPECTED)
        ],
        "oracle_match": status == "EXECUTED" and tuple(verdicts) == EXPECTED,
        "interpretation": {
            "preserve_first_deadline": "FAIL: first response occurs after 3 s",
            "reset_on_repeat": "PASS: repeat at 2.5 s refreshes the pending obligation",
            "protocol_ambiguity": (
                "The same observed trace changes verdict when repeat semantics change."
            ),
        },
        "claim_limit": (
            "This is a protocol-level timed-trace counterexample. It does not prove "
            "collision risk or physical vehicle unsafety."
        ),
        "source_evidence": {
            "cohort_result": (
                "artifacts/results/public/chunk-0000-94/weak-kinematic-cohort-result.json"
            ),
            "event": "scene-0074@3400000",
            "camera_review": (
                "artifacts/results/public/chunk-0000-94/video-review/"
                "scene-0074-t3_4-contact-sheet.jpg"
            ),
        },
    }
    rendered = json.dumps(report, indent=2) + "\n"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(rendered, encoding="ascii")
    print(rendered, end="")


if __name__ == "__main__":
    main()
