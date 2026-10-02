#!/usr/bin/env python3
"""Analyze the restricted Alpamayo feasibility batch without emitting raw CoC text."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from statistics import mean, median
from typing import Any

import numpy as np


ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "PROJECT_REGISTRY.json").is_file())
DEFAULT_BATCH = (
    ROOT
    / "artifacts/results/restricted/alp-exp-005"
    / "feasibility-batch-v0"
)
DEFAULT_COHORT = (
    ROOT
    / "data/restricted/nvidia_physicalai/internal-derived/cohort-10"
    / "cohort-conformance.json"
)

ACTION_PATTERNS = {
    "STOP": (
        r"(?<!bus )\bstop(?:ping)?\b(?! sign)",
        r"\bhalt\b",
        r"\bcome to a stop\b",
    ),
    "DECELERATE": (
        r"\bdecelerat\w*\b",
        r"\bslow(?:ing)? down\b",
        r"\breduc(?:e|ing) (?:the )?speed\b",
        r"\blower(?:ing)? (?:the )?speed\b",
    ),
    "YIELD": (r"\byield(?:ing)?\b",),
    "ACCELERATE": (
        r"\baccelerat\w*\b",
        r"\bspeed(?:ing)? up\b",
        r"\bincreas(?:e|ing) (?:the )?speed\b",
        r"\bresume (?:the )?(?:speed|motion|driving)\b",
    ),
    "MAINTAIN_SPEED": (
        r"\bmaintain(?:ing)? (?:the )?(?:current )?speed\b",
        r"\bcontinue (?:forward|straight|driving|at)\b",
        r"\bproceed(?:ing)? (?:forward|straight|through)\b",
        r"\bkeep(?:ing)? (?:the )?(?:current )?speed\b",
    ),
    "KEEP_LANE": (
        r"\bmaintain(?:ing)? (?:the )?(?:current )?(?:course|lane)\b",
        r"\bkeep(?:ing)? (?:the )?(?:current )?(?:course|lane)\b",
    ),
}

LATERAL_VERBS = r"(?:nudge|steer|shift|move|veer|turn|adjust|drift)\w*"
LATERAL_PATTERNS = {
    "LEFT": (
        rf"\b{LATERAL_VERBS}\b.{{0,30}}\bleft(?:ward)?\b",
        rf"\bleftward\b.{{0,30}}\b{LATERAL_VERBS}\b",
    ),
    "RIGHT": (
        rf"\b{LATERAL_VERBS}\b.{{0,30}}\bright(?:ward)?\b",
        rf"\brightward\b.{{0,30}}\b{LATERAL_VERBS}\b",
    ),
}

ENTITY_PATTERNS = {
    "PEDESTRIAN": (r"\bpedestrian\w*\b", r"\bperson\b", r"\bpeople\b"),
    "CYCLIST": (r"\bcyclist\w*\b", r"\bbicycl\w*\b", r"\bbike\b"),
    "VEHICLE": (r"\bvehicle\w*\b", r"\bcar\b", r"\btraffic\b"),
    "TRUCK_TRAILER": (r"\btruck\b", r"\btrailer\b"),
    "EMERGENCY_VEHICLE": (r"\bambulance\b", r"\bfire truck\b", r"\bpolice car\b"),
    "WORK_ZONE": (r"\bconstruction\b", r"\bwork zone\b", r"\broadwork\b"),
    "CONE_BARRIER": (r"\bcone\w*\b", r"\bbarrier\w*\b", r"\bbarricade\w*\b"),
    "TRAFFIC_CONTROL": (r"\btraffic light\b", r"\bsignal\b", r"\bstop sign\b"),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch-root", type=Path, default=DEFAULT_BATCH)
    parser.add_argument("--cohort", type=Path, default=DEFAULT_COHORT)
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def matching_categories(text: str, patterns: dict[str, tuple[str, ...]]) -> set[str]:
    lowered = text.lower()
    return {
        category
        for category, category_patterns in patterns.items()
        if any(re.search(pattern, lowered) for pattern in category_patterns)
    }


def parse_actions(text: str) -> set[str]:
    actions = matching_categories(text, ACTION_PATTERNS)
    actions.update(matching_categories(text, LATERAL_PATTERNS))
    return actions


def parse_entities(text: str) -> set[str]:
    return matching_categories(text, ENTITY_PATTERNS)


def trajectory_features(points: np.ndarray) -> dict[str, float | bool]:
    points = np.asarray(points, dtype=float).reshape(64, 3)
    with_origin = np.vstack((np.zeros((1, 3)), points))
    speeds = np.linalg.norm(np.diff(with_origin[:, :2], axis=0), axis=1) / 0.1
    initial_speed = float(speeds[:5].mean())
    terminal_speed = float(speeds[-5:].mean())
    lateral_delta = float(points[-1, 1])
    return {
        "initial_speed_mps": initial_speed,
        "terminal_speed_mps": terminal_speed,
        "speed_delta_mps": terminal_speed - initial_speed,
        "final_lateral_delta_m": lateral_delta,
        "final_forward_displacement_m": float(points[-1, 0]),
        "stops": terminal_speed < 0.5,
        "decelerates": terminal_speed - initial_speed <= -1.0,
        "accelerates": terminal_speed - initial_speed >= 1.0,
        "left_weak": lateral_delta >= 0.3,
        "right_weak": lateral_delta <= -0.3,
        "left_strict": lateral_delta >= 1.0,
        "right_strict": lateral_delta <= -1.0,
        "maintains_speed": abs(terminal_speed - initial_speed) < 1.0,
    }


def action_matches(
    actions: set[str], trajectory: dict[str, float | bool], *, strict_lateral: bool
) -> bool | None:
    if not actions:
        return None
    remaining_actions = set(actions)
    if float(trajectory["initial_speed_mps"]) < 0.5:
        remaining_actions.difference_update({"STOP", "YIELD"})
    if not remaining_actions:
        return None
    checks: list[bool] = []
    for action in remaining_actions:
        if action == "STOP":
            checks.append(bool(trajectory["stops"]))
        elif action == "DECELERATE":
            if strict_lateral:
                checks.append(bool(trajectory["decelerates"] or trajectory["stops"]))
            else:
                checks.append(
                    float(trajectory["speed_delta_mps"]) <= -0.1
                    or bool(trajectory["stops"])
                )
        elif action == "YIELD":
            if strict_lateral:
                checks.append(bool(trajectory["decelerates"] or trajectory["stops"]))
            else:
                checks.append(
                    float(trajectory["speed_delta_mps"]) <= -0.1
                    or bool(trajectory["stops"])
                )
        elif action == "ACCELERATE":
            if strict_lateral:
                checks.append(bool(trajectory["accelerates"]))
            else:
                checks.append(float(trajectory["speed_delta_mps"]) >= 0.1)
        elif action == "MAINTAIN_SPEED":
            checks.append(bool(trajectory["maintains_speed"]))
        elif action == "LEFT":
            key = "left_strict" if strict_lateral else "left_weak"
            checks.append(bool(trajectory[key]))
        elif action == "RIGHT":
            key = "right_strict" if strict_lateral else "right_weak"
            checks.append(bool(trajectory[key]))
    return all(checks) if checks else None


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    path.parent.chmod(0o700)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    path.chmod(0o600)


def main() -> int:
    args = parse_args()
    output = args.output or (args.batch_root / "feasibility-analysis.json")
    cohort = json.loads(args.cohort.read_text(encoding="utf-8"))
    episodes = cohort["episodes"]

    run_rows: list[dict[str, Any]] = []
    episode_rows: list[dict[str, Any]] = []
    for episode_index, episode in enumerate(episodes):
        episode_name = f"episode-{episode_index:02d}"
        human_coc = episode["events"][0]["coc"]
        human_actions = parse_actions(human_coc)
        human_entities = parse_entities(human_coc)
        episode_run_rows: list[dict[str, Any]] = []

        for run_dir in sorted((args.batch_root / episode_name).glob("seed-*")):
            manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
            if manifest.get("clip_id") != episode["clip_id"]:
                raise ValueError(f"Restricted provenance mismatch in {episode_name}")
            model_coc = (run_dir / "generated_coc.txt").read_text(encoding="utf-8").strip()
            model_actions = parse_actions(model_coc)
            model_entities = parse_entities(model_coc)
            pred = np.load(run_dir / "predicted_trajectory.npz")["pred_xyz"]
            trajectory = trajectory_features(pred)
            metrics = json.loads((run_dir / "metrics.json").read_text(encoding="utf-8"))
            row = {
                "episode": episode_name,
                "seed": int(manifest["seed"]),
                "coc_sha256": hashlib.sha256(model_coc.encode("utf-8")).hexdigest(),
                "model_actions": sorted(model_actions),
                "model_entities": sorted(model_entities),
                "human_reference_actions": sorted(human_actions),
                "human_reference_entities": sorted(human_entities),
                "model_human_action_overlap": bool(model_actions & human_actions),
                "model_human_entity_overlap": bool(model_entities & human_entities),
                "action_already_satisfied_at_horizon_start": bool(
                    model_actions & {"STOP", "YIELD"}
                    and float(trajectory["initial_speed_mps"]) < 0.5
                ),
                "action_trajectory_match_weak": action_matches(
                    model_actions, trajectory, strict_lateral=False
                ),
                "action_trajectory_match_strict": action_matches(
                    model_actions, trajectory, strict_lateral=True
                ),
                "minADE_m": float(metrics["minADE_m"]),
                "high_error_proxy_gt_5m": float(metrics["minADE_m"]) > 5.0,
                "trajectory": trajectory,
            }
            run_rows.append(row)
            episode_run_rows.append(row)

        signatures = {
            (tuple(row["model_actions"]), tuple(row["model_entities"]))
            for row in episode_run_rows
        }
        episode_rows.append(
            {
                "episode": episode_name,
                "event_cluster": episode["event_cluster"],
                "run_count": len(episode_run_rows),
                "unique_coc_text_count": len(
                    {row["coc_sha256"] for row in episode_run_rows}
                ),
                "unique_action_entity_signature_count": len(signatures),
                "semantic_signature_varies_across_seeds": len(signatures) > 1,
                "minADE_range_m": (
                    max(row["minADE_m"] for row in episode_run_rows)
                    - min(row["minADE_m"] for row in episode_run_rows)
                ),
            }
        )

    minades = [row["minADE_m"] for row in run_rows]
    evaluable = [row for row in run_rows if row["action_trajectory_match_weak"] is not None]
    weak_mismatches = [
        row for row in evaluable if row["action_trajectory_match_weak"] is False
    ]
    strict_mismatches = [
        row for row in evaluable if row["action_trajectory_match_strict"] is False
    ]
    high_error = [row for row in run_rows if row["high_error_proxy_gt_5m"]]
    varying_episodes = [
        row for row in episode_rows if row["semantic_signature_varies_across_seeds"]
    ]

    result = {
        "experiment_id": "ALP-EXP-005-FEASIBILITY-ANALYSIS-V0",
        "publication_control": "LICENSE_RESTRICTED_INTERNAL_RESULT",
        "raw_coc_text_included": False,
        "scope": "Exploratory offline fidelity proxies; not a safety evaluation",
        "thresholds": {
            "stop_terminal_speed_mps": 0.5,
            "longitudinal_speed_delta_mps": 1.0,
            "weak_lateral_displacement_m": 0.3,
            "strict_lateral_displacement_m": 1.0,
            "high_error_minADE_m": 5.0,
        },
        "summary": {
            "episode_count": len(episode_rows),
            "run_count": len(run_rows),
            "action_evaluable_run_count": len(evaluable),
            "weak_action_trajectory_mismatch_count": len(weak_mismatches),
            "strict_action_trajectory_mismatch_count": len(strict_mismatches),
            "high_error_proxy_run_count": len(high_error),
            "episodes_with_seed_semantic_variation": len(varying_episodes),
            "model_human_action_overlap_count": sum(
                row["model_human_action_overlap"] for row in run_rows
            ),
            "model_human_entity_overlap_count": sum(
                row["model_human_entity_overlap"] for row in run_rows
            ),
            "minADE_mean_m": mean(minades),
            "minADE_median_m": median(minades),
            "minADE_min_m": min(minades),
            "minADE_max_m": max(minades),
        },
        "episodes": episode_rows,
        "runs": run_rows,
        "limitations": [
            "Keyword parsing is a baseline proxy and has not been independently human-validated.",
            "Human-refined event CoC is a reference, not an exhaustive scene-level gold description.",
            "minADE and kinematic alignment are not physical safety metrics.",
            "Ten purpose-sampled episodes cannot estimate population prevalence.",
            "No camera or obstacle grounding judgment is made in this analysis.",
        ],
    }
    write_json(output, result)
    print(
        json.dumps(
            {
                "output": str(output.relative_to(ROOT)),
                "summary": result["summary"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
