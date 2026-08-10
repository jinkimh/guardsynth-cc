#!/usr/bin/env python3
"""Run verifyta over generated scene-0001 models and report exact execution status."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path

from generate_models import EXPECTED, MODEL_DIR, QUERIES, VARIANTS, write_models


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_VERIFYTA = ROOT / "runtime/solvers/uppaal-5.0.0-linux64/bin/verifyta"
ANSI_ESCAPE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")


def classify_output(
    output: str, expected_query_count: int = len(QUERIES)
) -> tuple[str, list[bool]]:
    lowered = output.lower()
    if "license does not cover verifier" in lowered or "license key is not set" in lowered:
        return "NOT_RUN_LICENSE_BLOCKED", []
    if "error" in lowered and "property is" not in lowered and "formula is" not in lowered:
        return "ERROR", []
    verdicts = []
    for match in re.finditer(r"(?:Property|Formula) is (NOT )?satisfied", output):
        verdicts.append(match.group(1) is None)
    if len(verdicts) != expected_query_count:
        return "ERROR_UNEXPECTED_QUERY_COUNT", verdicts
    return "EXECUTED", verdicts


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--verifyta", type=Path, default=DEFAULT_VERIFYTA)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    write_models()
    results = []
    for variant in VARIANTS:
        model_path = MODEL_DIR / f"scene-0001-{variant.name}.xml"
        completed = subprocess.run(
            [str(args.verifyta), "-q", "-t1", str(model_path), str(MODEL_DIR / "scene-0001.q")],
            capture_output=True,
            text=True,
            check=False,
        )
        combined = completed.stdout + completed.stderr
        cleaned_output = ANSI_ESCAPE.sub("", combined)
        status, verdicts = classify_output(combined)
        expected = EXPECTED[variant.name]
        trace_path = None
        if args.output:
            trace_dir = args.output.parent / "uppaal-traces"
            trace_dir.mkdir(parents=True, exist_ok=True)
            trace_path = trace_dir / f"{variant.name}.txt"
            trace_path.write_text(cleaned_output, encoding="utf-8")
        results.append(
            {
                "variant": variant.name,
                "status": status,
                "exit_code": completed.returncode,
                "verdicts": verdicts,
                "expected_verdicts": expected,
                "mutation_oracle_match": verdicts == expected if status == "EXECUTED" else None,
                "violated_queries": [
                    {"index": index + 1, "query": QUERIES[index]}
                    for index, verdict in enumerate(verdicts)
                    if not verdict
                ],
                "trace_path": None if trace_path is None else str(trace_path),
                "diagnostic_excerpt": cleaned_output.strip()[:1000],
            }
        )

    report = {
        "checker": "UPPAAL_VERIFYTA",
        "verifyta": str(args.verifyta),
        "models": results,
        "overall": (
            "PASS"
            if all(item["status"] == "EXECUTED" and item["mutation_oracle_match"] for item in results)
            else "NOT_RUN_LICENSE_BLOCKED"
            if all(item["status"] == "NOT_RUN_LICENSE_BLOCKED" for item in results)
            else "FAIL_OR_PARTIAL"
        ),
    }
    rendered = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")


if __name__ == "__main__":
    main()
