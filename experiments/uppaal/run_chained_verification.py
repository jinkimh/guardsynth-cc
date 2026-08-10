#!/usr/bin/env python3
"""Run verifyta on the chained multi-phase mutation models."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

from generate_chained_models import EXPECTED, MODEL_DIR, QUERIES, VARIANTS, write_models
from run_verification import ANSI_ESCAPE, DEFAULT_VERIFYTA, classify_output


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--verifyta", type=Path, default=DEFAULT_VERIFYTA)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    write_models()
    results = []
    for variant in VARIANTS:
        model = MODEL_DIR / f"scene-0001-chained-{variant.name}.xml"
        completed = subprocess.run(
            [str(args.verifyta), "-q", "-t1", str(model), str(MODEL_DIR / "scene-0001-chained.q")],
            capture_output=True,
            text=True,
            check=False,
        )
        output = ANSI_ESCAPE.sub("", completed.stdout + completed.stderr)
        status, verdicts = classify_output(output, len(QUERIES))
        expected = EXPECTED[variant.name]
        trace_path = None
        if args.output:
            trace_dir = args.output.parent / "uppaal-chained-traces"
            trace_dir.mkdir(parents=True, exist_ok=True)
            trace_path = trace_dir / f"{variant.name}.txt"
            trace_path.write_text(output, encoding="utf-8")
        results.append(
            {
                "variant": variant.name,
                "status": status,
                "verdicts": verdicts,
                "expected_verdicts": expected,
                "mutation_oracle_match": verdicts == expected if status == "EXECUTED" else None,
                "violated_queries": [
                    {"index": index + 1, "query": QUERIES[index]}
                    for index, verdict in enumerate(verdicts)
                    if not verdict
                ],
                "trace_path": None if trace_path is None else str(trace_path),
            }
        )
    report = {
        "checker": "UPPAAL_CHAINED_PROTOCOL_MUTATION_FEASIBILITY",
        "models": results,
        "overall": "PASS" if all(item["status"] == "EXECUTED" and item["mutation_oracle_match"] for item in results) else "FAIL_OR_PARTIAL",
    }
    profile = json.loads(
        (MODEL_DIR / "scene-0001-chained-profile.json").read_text(encoding="ascii")
    )
    provenance = profile["provenance"]
    report["provenance_assessment"] = {
        "source_artifact": provenance["source_artifact"],
        "source_reference_validation": provenance["source_reference_validation"],
        "chained_four_phase": {
            "traceability": provenance["chained_four_phase"]["traceability"],
            "gates": provenance["chained_four_phase"]["gates"],
        },
        "source_trace_episode": {
            "traceability": provenance["source_trace_episode"]["traceability"],
            "gates": provenance["source_trace_episode"]["gates"],
        },
        "policy": provenance["policy"],
    }
    rendered = json.dumps(report, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="ascii")
    print(rendered, end="")


if __name__ == "__main__":
    main()
