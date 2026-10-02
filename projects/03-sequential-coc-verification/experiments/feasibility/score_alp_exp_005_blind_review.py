#!/usr/bin/env python3
"""Score two completed blind CoC--trajectory consistency reviews."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path
from typing import Iterable


ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "PROJECT_REGISTRY.json").is_file())
DEFAULT_REVIEW_ROOT = (
    ROOT
    / "artifacts/results/restricted/alp-exp-005"
    / "feasibility-batch-v0/blind-review-v0"
)

ALLOWED = {
    "stated_longitudinal": {
        "STOP", "DECELERATE", "YIELD", "ACCELERATE", "MAINTAIN_SPEED", "NONE", "UNCLEAR"
    },
    "stated_lateral": {"LEFT", "RIGHT", "KEEP_LANE", "NONE", "UNCLEAR"},
    "trajectory_longitudinal": {
        "STOP", "DECELERATE", "YIELD", "ACCELERATE", "MAINTAIN_SPEED", "NONE", "UNCLEAR"
    },
    "trajectory_lateral": {"LEFT", "RIGHT", "KEEP_LANE", "UNCLEAR"},
    "consistency": {"CONSISTENT", "INCONSISTENT", "UNCERTAIN"},
    "temporal_ambiguity": {"YES", "NO"},
    "confidence": {"1", "2", "3"},
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--review-root", type=Path, default=DEFAULT_REVIEW_ROOT)
    return parser.parse_args()


def read_review(path: Path) -> dict[str, dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    if not rows:
        raise ValueError(f"No review rows in {path}")
    result: dict[str, dict[str, str]] = {}
    for row_number, row in enumerate(rows, start=2):
        review_id = (row.get("review_id") or "").strip()
        if not review_id or review_id in result:
            raise ValueError(f"Missing or duplicate review_id at {path}:{row_number}")
        normalized = {key: (value or "").strip().upper() for key, value in row.items()}
        normalized["notes"] = (row.get("notes") or "").strip()
        for field, choices in ALLOWED.items():
            if normalized.get(field) not in choices:
                options = ", ".join(sorted(choices))
                raise ValueError(
                    f"Invalid or blank {field} for {review_id} in {path}; use one of: {options}"
                )
        result[review_id] = normalized
    return result


def exact_agreement(left: Iterable[str], right: Iterable[str]) -> float:
    pairs = list(zip(left, right, strict=True))
    return sum(a == b for a, b in pairs) / len(pairs)


def cohen_kappa(left: Iterable[str], right: Iterable[str]) -> float | None:
    pairs = list(zip(left, right, strict=True))
    n = len(pairs)
    observed = sum(a == b for a, b in pairs) / n
    left_counts = Counter(a for a, _ in pairs)
    right_counts = Counter(b for _, b in pairs)
    expected = sum(left_counts[label] * right_counts[label] for label in set(left_counts) | set(right_counts)) / n**2
    if expected == 1.0:
        return None
    return (observed - expected) / (1.0 - expected)


def rounded(value: float | None) -> float | None:
    return None if value is None else round(value, 4)


def main() -> int:
    args = parse_args()
    reviewer_a = read_review(args.review_root / "reviewer_A.csv")
    reviewer_b = read_review(args.review_root / "reviewer_B.csv")
    if reviewer_a.keys() != reviewer_b.keys():
        raise ValueError("Reviewer A and B have different review_id sets")

    review_ids = sorted(reviewer_a)
    agreement: dict[str, dict[str, float | None]] = {}
    for field in ALLOWED:
        left = [reviewer_a[item][field] for item in review_ids]
        right = [reviewer_b[item][field] for item in review_ids]
        agreement[field] = {
            "raw_agreement": rounded(exact_agreement(left, right)),
            "cohen_kappa": rounded(cohen_kappa(left, right)),
        }

    consensus_mismatches = [
        item
        for item in review_ids
        if reviewer_a[item]["consistency"] == "INCONSISTENT"
        and reviewer_b[item]["consistency"] == "INCONSISTENT"
        and int(reviewer_a[item]["confidence"]) >= 2
        and int(reviewer_b[item]["confidence"]) >= 2
    ]

    mapping = json.loads(
        (args.review_root / "adjudication-only/blind-mapping.json").read_text(encoding="utf-8")
    )
    mapping_by_id = {row["review_id"]: row for row in mapping}
    distinct_episodes = sorted({mapping_by_id[item]["episode"] for item in consensus_mismatches})
    raw_consistency_agreement = agreement["consistency"]["raw_agreement"]
    gate_pass = (
        len(consensus_mismatches) >= 3
        and len(distinct_episodes) >= 2
        and raw_consistency_agreement is not None
        and raw_consistency_agreement >= 0.8
    )

    report = {
        "experiment_id": "ALP-EXP-005-BLIND-REVIEW-V0",
        "review_item_count": len(review_ids),
        "agreement": agreement,
        "consensus_mismatch_review_ids": consensus_mismatches,
        "consensus_mismatch_count": len(consensus_mismatches),
        "consensus_mismatch_distinct_episode_count": len(distinct_episodes),
        "internal_gate": {
            "criteria": {
                "consensus_mismatches_at_least": 3,
                "distinct_episodes_at_least": 2,
                "raw_consistency_agreement_at_least": 0.8,
            },
            "verdict": "PASS_TO_GROUNDING" if gate_pass else "STOP_OR_REVISE",
            "note": "An internal feasibility gate, not a statistical or publication claim.",
        },
    }
    output = args.review_root / "adjudication-only/inter-review-agreement.json"
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    output.chmod(0o600)
    print(json.dumps(report, indent=2, sort_keys=True))
    print(f"wrote {output.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
