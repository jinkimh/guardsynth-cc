from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path


COMPARISONS = (
    ("A_STATE", "C_CONTRACT"),
    ("B_COC", "C_CONTRACT"),
    ("C_CONTRACT", "D_CONTRACT_SHIELD"),
)


def as_bool(value: str) -> bool:
    return value.lower() == "true"


def comparison_counts(index, keys, left, right, metric):
    counts = defaultdict(int)
    for key in keys:
        before = as_bool(index[(*key, left)][metric])
        after = as_bool(index[(*key, right)][metric])
        if before and not after:
            counts["fixed"] += 1
        elif not before and after:
            counts["harmed"] += 1
        elif before and after:
            counts["same_bad"] += 1
        else:
            counts["same_good"] += 1
    return dict(counts)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("run_dir", type=Path)
    args = parser.parse_args()
    with (args.run_dir / "episode_metrics.csv").open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    index = {
        (row["seed"], row["split"], row["kind"], row["episode"], row["variant"]): row
        for row in rows
    }
    result = {"scope": "paired episodes within the fixed OOD bank", "comparisons": []}
    for left, right in COMPARISONS:
        entry = {"left": left, "right": right, "unsafe": {}, "safe_gap_violation": {}}
        for kind in ("crosswalk", "stop_intersection", "lead_brake", "ALL"):
            keys = sorted(
                {
                    (row["seed"], row["split"], row["kind"], row["episode"])
                    for row in rows
                    if row["split"] == "OOD" and (kind == "ALL" or row["kind"] == kind)
                }
            )
            entry["unsafe"][kind] = comparison_counts(index, keys, left, right, "unsafe")
            entry["safe_gap_violation"][kind] = comparison_counts(index, keys, left, right, "safe_gap_violation")
        result["comparisons"].append(entry)
    output = args.run_dir / "paired_effects.json"
    output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()

