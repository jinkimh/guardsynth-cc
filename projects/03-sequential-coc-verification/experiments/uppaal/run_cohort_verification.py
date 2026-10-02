#!/usr/bin/env python3
"""Run UPPAAL over every episode and mutation in the CoC cohort."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

from generate_cohort_models import (
    COHORT_RESULT,
    MODEL_DIR,
    QUERIES,
    VARIANTS,
    write_models,
)
from run_verification import ANSI_ESCAPE, DEFAULT_VERIFYTA, classify_output


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--verifyta", type=Path, default=DEFAULT_VERIFYTA)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--cohort-result", type=Path, default=COHORT_RESULT)
    parser.add_argument("--model-dir", type=Path, default=MODEL_DIR)
    args = parser.parse_args()
    oracle = write_models(args.model_dir, args.cohort_result)
    results = []
    for clip_id, variants in oracle["expected_satisfaction"].items():
        for variant in VARIANTS:
            model = args.model_dir / f"{clip_id}-{variant}.xml"
            completed = subprocess.run(
                [str(args.verifyta), "-q", str(model), str(args.model_dir / "cohort.q")],
                capture_output=True,
                text=True,
                check=False,
            )
            output = ANSI_ESCAPE.sub("", completed.stdout + completed.stderr)
            status, verdicts = classify_output(output, len(QUERIES))
            expected = variants[variant]
            results.append(
                {
                    "clip_id": clip_id,
                    "variant": variant,
                    "status": status,
                    "verdicts": verdicts,
                    "expected_verdicts": expected,
                    "oracle_match": status == "EXECUTED" and verdicts == expected,
                    "violated_queries": [
                        QUERIES[index]
                        for index, verdict in enumerate(verdicts)
                        if not verdict
                    ],
                }
            )
    baselines = [item for item in results if item["variant"] == "baseline"]
    report = {
        "checker": "UPPAAL_MULTI_SCENE_TRACE_REPLAY_MUTATION",
        "scene_count": len(baselines),
        "model_count": len(results),
        "query_evaluation_count": len(results) * len(QUERIES),
        "baseline_weak_response_violations": [
            item["clip_id"]
            for item in baselines
            if "A[] not weak_response_violation" in item["violated_queries"]
        ],
        "all_mutation_oracles_match": all(item["oracle_match"] for item in results),
        "overall": "PASS" if all(item["oracle_match"] for item in results) else "FAIL",
        "results": results,
    }
    rendered = json.dumps(report, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="ascii")
    print(rendered, end="")


if __name__ == "__main__":
    main()
