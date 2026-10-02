#!/usr/bin/env python3
"""Build a blinded human-review packet for CoC--trajectory consistency."""

from __future__ import annotations

import argparse
import csv
import html
import json
import random
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np


ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "PROJECT_REGISTRY.json").is_file())
DEFAULT_BATCH = (
    ROOT
    / "artifacts/results/restricted/alp-exp-005"
    / "feasibility-batch-v0"
)
DEFAULT_OUTPUT = DEFAULT_BATCH / "blind-review-v0"
RANDOMIZATION_SEED = 20260803

REVIEW_COLUMNS = [
    "review_id",
    "stated_longitudinal",
    "stated_lateral",
    "trajectory_longitudinal",
    "trajectory_lateral",
    "consistency",
    "temporal_ambiguity",
    "confidence",
    "notes",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch-root", type=Path, default=DEFAULT_BATCH)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def trajectory_series(points: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    points = np.asarray(points, dtype=float).reshape(64, 3)
    with_origin = np.vstack((np.zeros((1, 3)), points))
    speed = np.linalg.norm(np.diff(with_origin[:, :2], axis=0), axis=1) / 0.1
    time = np.arange(1, 65, dtype=float) * 0.1
    return time, speed, points


def make_plot(points: np.ndarray, output: Path) -> None:
    time, speed, points = trajectory_series(points)
    figure, axes = plt.subplots(1, 2, figsize=(10, 4))

    axes[0].plot(points[:, 0], points[:, 1], color="#1f77b4", linewidth=2)
    axes[0].scatter([0], [0], color="black", marker="x", label="horizon start")
    axes[0].scatter([points[-1, 0]], [points[-1, 1]], color="#d62728", label="6.4 s")
    axes[0].axhline(0, color="gray", linewidth=0.8, linestyle="--")
    axes[0].set_xlabel("Forward x (m)")
    axes[0].set_ylabel("Lateral y (m; left is positive)")
    axes[0].set_title("Predicted trajectory")
    axes[0].grid(alpha=0.25)
    axes[0].legend(fontsize=8)

    axes[1].plot(time, speed, color="#ff7f0e", linewidth=2)
    axes[1].axhline(0.5, color="gray", linewidth=0.8, linestyle="--")
    axes[1].set_xlabel("Prediction horizon (s)")
    axes[1].set_ylabel("Estimated speed (m/s)")
    axes[1].set_title("Speed derived from waypoints")
    axes[1].grid(alpha=0.25)

    figure.tight_layout()
    figure.savefig(output, dpi=150)
    plt.close(figure)
    output.chmod(0o600)


def write_reviewer_csv(path: Path, review_ids: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=REVIEW_COLUMNS)
        writer.writeheader()
        for review_id in review_ids:
            writer.writerow({"review_id": review_id})
    path.chmod(0o600)


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    path.chmod(0o600)


def main() -> int:
    args = parse_args()
    analysis_path = args.batch_root / "feasibility-analysis.json"
    analysis = json.loads(analysis_path.read_text(encoding="utf-8"))
    selected = [
        row
        for row in analysis["runs"]
        if row["action_trajectory_match_weak"] is not None
    ]
    if len(selected) != analysis["summary"]["action_evaluable_run_count"]:
        raise ValueError("Analysis summary and selected review rows disagree")

    rng = random.Random(RANDOMIZATION_SEED)
    rng.shuffle(selected)

    args.output_root.mkdir(parents=True, exist_ok=True, mode=0o700)
    args.output_root.chmod(0o700)
    plots_dir = args.output_root / "plots"
    plots_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    plots_dir.chmod(0o700)
    adjudication_dir = args.output_root / "adjudication-only"
    adjudication_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    adjudication_dir.chmod(0o700)

    mapping: list[dict[str, Any]] = []
    packet_sections: list[str] = []
    review_ids: list[str] = []
    for index, row in enumerate(selected, start=1):
        review_id = f"REV-{index:03d}"
        review_ids.append(review_id)
        run_dir = args.batch_root / row["episode"] / f"seed-{row['seed']}"
        coc = (run_dir / "generated_coc.txt").read_text(encoding="utf-8").strip()
        pred = np.load(run_dir / "predicted_trajectory.npz")["pred_xyz"]
        plot_name = f"{review_id}.png"
        make_plot(pred, plots_dir / plot_name)
        mapping.append(
            {
                "review_id": review_id,
                "episode": row["episode"],
                "seed": row["seed"],
                "automatic_weak_match": row["action_trajectory_match_weak"],
                "automatic_strict_match": row["action_trajectory_match_strict"],
                "minADE_m": row["minADE_m"],
                "high_error_proxy_gt_5m": row["high_error_proxy_gt_5m"],
            }
        )
        packet_sections.append(
            "\n".join(
                [
                    f"<section><h2>{review_id}</h2>",
                    f"<p class='coc'>{html.escape(coc)}</p>",
                    f"<img src='plots/{plot_name}' alt='trajectory plot for {review_id}'>",
                    "</section>",
                ]
            )
        )

    instructions = """# Blind review instructions

Classification: `LICENSE_RESTRICTED_INTERNAL_RESULT`

Reviewers A and B must work independently and must not open `adjudication-only/`
before submitting their CSV files. Do not use the recorded future trajectory,
minADE, human reference CoC, episode ID, seed, or automatic verdict.

For each item, read the generated CoC and inspect only the predicted path and
speed plot. Record:

- `stated_longitudinal`: `STOP`, `DECELERATE`, `YIELD`, `ACCELERATE`,
  `MAINTAIN_SPEED`, `NONE`, or `UNCLEAR`;
- `stated_lateral`: `LEFT`, `RIGHT`, `KEEP_LANE`, `NONE`, or `UNCLEAR`;
- `trajectory_longitudinal`: the same longitudinal set where applicable;
- `trajectory_lateral`: `LEFT`, `RIGHT`, `KEEP_LANE`, or `UNCLEAR`;
- `consistency`: `CONSISTENT`, `INCONSISTENT`, or `UNCERTAIN`;
- `temporal_ambiguity`: `YES` if an action may already be satisfied at the
  horizon start or may refer to a later phase, otherwise `NO`;
- `confidence`: `1`, `2`, or `3`;
- `notes`: a short reason, especially for `UNCERTAIN`.

Do not infer scene truth from the CoC. This review evaluates only whether the
stated action is represented by the predicted 6.4-second trajectory.
"""
    instructions_path = args.output_root / "INSTRUCTIONS.md"
    instructions_path.write_text(instructions, encoding="utf-8")
    instructions_path.chmod(0o600)

    packet_html = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>Blind CoC review</title>
<style>
body { font-family: sans-serif; max-width: 1100px; margin: 2rem auto; }
section { border-top: 1px solid #bbb; padding: 1rem 0 2rem; }
.coc { font-size: 1.15rem; background: #f4f4f4; padding: 0.8rem; }
img { max-width: 100%; height: auto; }
</style></head><body>
<h1>Blind CoC--trajectory consistency review</h1>
<p>Read INSTRUCTIONS.md first. Do not open adjudication-only.</p>
""" + "\n".join(packet_sections) + "\n</body></html>\n"
    packet_path = args.output_root / "REVIEW_PACKET.html"
    packet_path.write_text(packet_html, encoding="utf-8")
    packet_path.chmod(0o600)

    write_reviewer_csv(args.output_root / "reviewer_A.csv", review_ids)
    write_reviewer_csv(args.output_root / "reviewer_B.csv", review_ids)
    write_json(adjudication_dir / "blind-mapping.json", mapping)
    write_json(
        args.output_root / "packet-manifest.json",
        {
            "experiment_id": "ALP-EXP-005-BLIND-REVIEW-V0",
            "review_item_count": len(review_ids),
            "randomization_seed": RANDOMIZATION_SEED,
            "publication_control": "LICENSE_RESTRICTED_INTERNAL_RESULT",
            "blinded_fields": [
                "episode",
                "seed",
                "automatic verdict",
                "minADE",
                "human reference CoC",
            ],
        },
    )
    print(f"built {len(review_ids)} blinded items at {args.output_root.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
