#!/usr/bin/env python3
"""Run UPPAAL over the four remaining chunk-0 review candidates."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

from generate_remaining_candidate_models import (
    CANDIDATES,
    COHORT_RESULT,
    DEADLINES_MS,
    MODEL_DIR,
    QUERIES,
    SEMANTICS,
    write_models,
)
from run_verification import ANSI_ESCAPE, DEFAULT_VERIFYTA, classify_output


ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "PROJECT_REGISTRY.json").is_file())
DEFAULT_OUTPUT = (
    ROOT
    / "artifacts/results/public/remaining-candidates"
    / "uppaal-multi-property-verification-result.json"
)


def _robustness_by_scene() -> dict:
    cohort = json.loads(COHORT_RESULT.read_text(encoding="utf-8"))
    target_ids = {candidate.target_event_id for candidate in CANDIDATES}
    result = {}
    for episode in cohort["episodes"]:
        for event in episode["events"]:
            if event["event_id"] in target_ids:
                result[episode["clip_id"]] = {
                    "target_event_id": event["event_id"],
                    "coc": event["coc"],
                    "three_second_robustness": event["three_second_robustness"],
                    "deadline_sensitivity": event["failure_sensitivity"]["by_deadline"],
                }
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--verifyta", type=Path, default=DEFAULT_VERIFYTA)
    parser.add_argument("--model-dir", type=Path, default=MODEL_DIR)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    oracle = write_models(args.model_dir)
    query_path = args.model_dir / "remaining-candidates.q"
    results = []
    for candidate in CANDIDATES:
        for semantics in SEMANTICS:
            for deadline_ms in DEADLINES_MS:
                name = f"{candidate.scene}-{semantics}-d{deadline_ms // 1000}"
                completed = subprocess.run(
                    [
                        str(args.verifyta),
                        "-q",
                        str(args.model_dir / f"{name}.xml"),
                        str(query_path),
                    ],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                output = ANSI_ESCAPE.sub("", completed.stdout + completed.stderr)
                status, verdicts = classify_output(output, len(QUERIES))
                expected = oracle["expected_satisfaction"][candidate.scene][semantics][
                    str(deadline_ms)
                ]
                results.append(
                    {
                        "scene": candidate.scene,
                        "semantics": semantics,
                        "deadline_s": deadline_ms // 1000,
                        "status": status,
                        "verdicts": verdicts,
                        "expected_verdicts": expected,
                        "oracle_match": status == "EXECUTED" and verdicts == expected,
                    }
                )

    summary = {}
    classifications = {
        "scene-0019": {
            "classification": "DUPLICATE_COC_POLICY_SENSITIVE",
            "training_use": "REVIEW_ONLY_UNTIL_DUPLICATE_POLICY_IS_FIXED",
        },
        "scene-0028": {
            "classification": "RESET_POLICY_FLIPS_D3_AND_DEDUP_BREAKS_PAIRING",
            "training_use": "CONDITIONAL_HARD_NEGATIVE_UNDER_PRESERVE_D3",
        },
        "scene-0042": {
            "classification": "D3_BOUNDARY_NOT_REPEAT_SEMANTICS_SENSITIVE",
            "training_use": "LOW_CONFIDENCE_D3_HARD_NEGATIVE",
        },
        "scene-0065": {
            "classification": "D3_BOUNDARY_WITH_INCONCLUSIVE_CAUSAL_GROUNDING",
            "training_use": "REVIEW_ONLY_UNTIL_SEMANTIC_GROUNDING_IS_CONFIRMED",
        },
    }
    for candidate in CANDIDATES:
        scene_results = [item for item in results if item["scene"] == candidate.scene]
        summary[candidate.scene] = {
            "target_event_id": candidate.target_event_id,
            "visual_grounding": candidate.visual_grounding,
            "deadline_pass_by_semantics": {
                semantics: [
                    item["deadline_s"]
                    for item in scene_results
                    if item["semantics"] == semantics and item["verdicts"][1]
                ]
                for semantics in SEMANTICS
            },
            "target_response_observed": scene_results[0]["verdicts"][2],
            "orphan_response_free_by_semantics": {
                semantics: all(
                    item["verdicts"][3]
                    for item in scene_results
                    if item["semantics"] == semantics
                )
                for semantics in SEMANTICS
            },
            "safety_status": "UNKNOWN",
            **classifications[candidate.scene],
        }

    report = {
        "checker": "UPPAAL_REMAINING_CANDIDATES_MULTI_PROPERTY_TRACE_REPLAY",
        "scene_count": len(CANDIDATES),
        "model_count": len(results),
        "query_evaluation_count": len(results) * len(QUERIES),
        "semantics": {
            "preserve": "A repeat does not reset a pending deadline.",
            "reset": "A repeat resets a pending deadline.",
            "deduplicate_1s": (
                "Equivalent commands within 1 s are suppressed; this is a sensitivity "
                "assumption, not a source contract."
            ),
        },
        "all_oracles_match": all(item["oracle_match"] for item in results),
        "summary": summary,
        "source_robustness": _robustness_by_scene(),
        "claim_limit": (
            "The models check timed protocol properties over derived speed responses. "
            "They do not establish actuator behavior, collision risk, or physical safety."
        ),
        "results": results,
    }
    rendered = json.dumps(report, indent=2) + "\n"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(rendered, encoding="ascii")
    print(rendered, end="")


if __name__ == "__main__":
    main()
