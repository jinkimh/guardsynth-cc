from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


COMPARISONS = (
    ("A_STATE", "C_CONTRACT"),
    ("B_COC", "C_CONTRACT"),
    ("C_CONTRACT", "C2_PHASE_CONTRACT"),
    ("C2_PHASE_CONTRACT", "D_CORRECT_CONTRACT"),
    ("D_CORRECT_CONTRACT", "D_ORACLE_LOOKAHEAD_0P8"),
    ("D_ORACLE_LOOKAHEAD_0P8", "D_ORACLE_LOOKAHEAD_1P2"),
    ("C_CONTRACT", "C_STALE_CONTRACT_0P4"),
    ("D_CORRECT_CONTRACT", "D_STALE_CONTRACT_0P4"),
)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("run_dir", type=Path)
    args = parser.parse_args()
    with (args.run_dir / "episode_metrics.csv").open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    index = {(r["seed"], r["case_id"], r["variant"]): r["unsafe"] == "True" for r in rows}
    keys = sorted({(r["seed"], r["case_id"]) for r in rows})
    result = []
    for left, right in COMPARISONS:
        counts = {"fixed": 0, "harmed": 0, "same_bad": 0, "same_good": 0}
        for seed, case_id in keys:
            before, after = index[(seed, case_id, left)], index[(seed, case_id, right)]
            if before and not after:
                counts["fixed"] += 1
            elif not before and after:
                counts["harmed"] += 1
            elif before and after:
                counts["same_bad"] += 1
            else:
                counts["same_good"] += 1
        result.append({"left": left, "right": right, **counts})
    output = args.run_dir / "paired_effects.json"
    output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()

