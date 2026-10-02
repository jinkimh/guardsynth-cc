#!/usr/bin/env python3
"""Phase-aware reanalysis of generated CoC actions over full trajectories."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np


ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "PROJECT_REGISTRY.json").is_file())
HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from run_bounded_temporal_smt import parse_actions  # noqa: E402


DEFAULT_BATCH = (
    ROOT
    / "artifacts/results/restricted/alp-exp-005"
    / "feasibility-batch-v0"
)
DEFAULT_EVIDENCE = DEFAULT_BATCH / "bounded-temporal-smt-v0/logic-inputs.json"
DEFAULT_OUTPUT = DEFAULT_BATCH / "phase-aware-alignment-v1/analysis.json"
DT_S = 0.1
RESPONSE_DEADLINES_S = (1.0, 2.0, 3.0)
LONGITUDINAL_DELTAS_MPS = (0.5, 1.0)
STOP_THRESHOLDS_MPS = (0.3, 0.5)
LATERAL_DELTAS_M = (0.1, 0.2, 0.3)


def load_trajectory(path: Path) -> tuple[np.ndarray, np.ndarray]:
    points = np.load(path)["pred_xyz"].reshape(64, 3).astype(float)
    with_origin = np.vstack((np.zeros((1, 3)), points))
    speeds = np.linalg.norm(np.diff(with_origin[:, :2], axis=0), axis=1) / DT_S
    return points, speeds


def first_time(mask: np.ndarray) -> float | None:
    indices = np.flatnonzero(mask)
    return None if len(indices) == 0 else round(float((indices[0] + 1) * DT_S), 3)


def response_sensitivity(
    speeds: np.ndarray, ego_speed_mps: float
) -> dict[str, dict[str, Any]]:
    values: dict[str, dict[str, Any]] = {}
    for deadline_s in RESPONSE_DEADLINES_S:
        end = min(len(speeds), int(round(deadline_s / DT_S)))
        window = speeds[:end]
        for delta in LONGITUDINAL_DELTAS_MPS:
            key = f"D={deadline_s:g},delta={delta:g}"
            threshold = ego_speed_mps - delta
            values[key] = {
                "formula": f"F_[0,{deadline_s:g}](v <= v0-{delta:g})",
                "satisfied": bool(np.any(window <= threshold)),
                "first_satisfaction_s": first_time(window <= threshold),
                "threshold_speed_mps": round(float(threshold), 6),
            }
    return values


def stop_sensitivity(
    speeds: np.ndarray, ego_speed_mps: float
) -> dict[str, dict[str, Any]]:
    values = {}
    for threshold in STOP_THRESHOLDS_MPS:
        mask = speeds <= threshold
        values[f"{threshold:g}"] = {
            "formula": f"F_[0,6.4](v <= {threshold:g})",
            "satisfied": bool(np.any(mask)),
            "first_satisfaction_s": first_time(mask),
            "already_satisfied_at_start": ego_speed_mps <= threshold,
        }
    return values


def lateral_sensitivity(points: np.ndarray, direction: str) -> dict[str, dict[str, Any]]:
    sign = 1.0 if direction == "LEFT" else -1.0
    directed = sign * points[:, 1]
    values = {}
    for delta in LATERAL_DELTAS_M:
        mask = directed >= delta
        values[f"{delta:g}"] = {
            "formula": f"F_[0,6.4]({direction.lower()}_excursion >= {delta:g})",
            "satisfied": bool(np.any(mask)),
            "first_satisfaction_s": first_time(mask),
        }
    return values


def classify_action(
    action: str, coc: str, points: np.ndarray, speeds: np.ndarray, ego_speed_mps: float
) -> dict[str, Any]:
    if action == "STOP":
        sensitivity = stop_sensitivity(speeds, ego_speed_mps)
        verdicts = [row["satisfied"] for row in sensitivity.values()]
        if all(verdicts):
            verdict = "SUPPORTED"
        elif any(verdicts):
            verdict = "THRESHOLD_SENSITIVE"
        else:
            verdict = "CONTRADICTED_WITHIN_HORIZON"
        return {
            "verdict": verdict,
            "semantics": "eventual stop within the 6.4 s prediction horizon",
            "sensitivity": sensitivity,
        }

    if action == "DECELERATE":
        sensitivity = response_sensitivity(speeds, ego_speed_mps)
        core = [
            row["satisfied"]
            for key, row in sensitivity.items()
            if key in {"D=3,delta=0.5", "D=3,delta=1"}
        ]
        if all(core):
            verdict = "SUPPORTED_RESPONSE_PHASE"
        elif any(core):
            verdict = "THRESHOLD_SENSITIVE_RESPONSE"
        else:
            verdict = "CONTRADICTED_RESPONSE_NOT_OBSERVED"
        return {
            "verdict": verdict,
            "semantics": "eventual deceleration response; later acceleration is not penalized",
            "sensitivity": sensitivity,
            "release_verdict": "NOT_REQUIRED_FOR_ACTION_ONLY_DECELERATE_CHECK",
        }

    if action == "YIELD":
        sensitivity = response_sensitivity(speeds, ego_speed_mps)
        response = sensitivity["D=3,delta=0.5"]["satisfied"]
        crawling = ego_speed_mps <= 1.0
        return {
            "verdict": (
                "KINEMATIC_RESPONSE_PRESENT_RELEASE_UNRESOLVED"
                if response or crawling
                else "UNKNOWN_YIELD_CANNOT_BE_REDUCED_TO_SPEED_ONLY"
            ),
            "semantics": "yield requires target occupancy, hold and release evidence",
            "sensitivity": sensitivity,
            "crawling_at_horizon_start": crawling,
            "release_verdict": "UNKNOWN_TARGET_CLEARANCE_NOT_MODELED",
        }

    if action in {"LEFT", "RIGHT"}:
        sensitivity = lateral_sensitivity(points, action)
        verdicts = [row["satisfied"] for row in sensitivity.values()]
        if all(verdicts):
            verdict = "SUPPORTED"
        elif any(verdicts):
            verdict = "THRESHOLD_SENSITIVE_SMALL_MANEUVER"
        else:
            verdict = "CONTRADICTED_DIRECTIONAL_RESPONSE_NOT_OBSERVED"
        return {
            "verdict": verdict,
            "semantics": "eventual directed excursion; later lane recovery is allowed",
            "sensitivity": sensitivity,
        }

    if action == "KEEP_LANE":
        first_2s = points[:20, 1]
        held = bool(np.max(np.abs(first_2s)) <= 0.3)
        later_left = bool(np.max(points[20:, 1]) >= 0.3)
        explicitly_phased = bool(
            any(token in coc.lower() for token in ("wait", "prepare", "gap"))
        )
        return {
            "verdict": (
                "PHASE_SEQUENCE_PLAUSIBLE_RELEASE_UNRESOLVED"
                if held and later_left and explicitly_phased
                else "UNKNOWN_HOLD_RELEASE_NOT_GROUNDED"
            ),
            "formula": "G_[0,2](abs(y)<=0.3); later lane change requires release",
            "initial_hold_satisfied": held,
            "later_left_excursion": later_left,
            "explicitly_phased_text": explicitly_phased,
            "release_verdict": "UNKNOWN_GAP_EVENT_NOT_MODELED",
        }

    if action == "KEEP_DISTANCE":
        return {
            "verdict": "UNKNOWN_TARGET_DISTANCE_CONTRACT_NOT_GROUNDED",
            "semantics": "requires associated target, gap and relative speed",
        }

    return {"verdict": "UNKNOWN_UNSUPPORTED_ACTION_CLASS"}


def aggregate(action_results: dict[str, dict[str, Any]]) -> str:
    verdicts = [row["verdict"] for row in action_results.values()]
    if any("CONTRADICTED" in verdict for verdict in verdicts):
        return "CONTRADICTED"
    if any("UNKNOWN" in verdict or "UNRESOLVED" in verdict for verdict in verdicts):
        return "UNKNOWN"
    if any("THRESHOLD_SENSITIVE" in verdict for verdict in verdicts):
        return "THRESHOLD_SENSITIVE"
    return "SUPPORTED"


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    path.parent.chmod(0o700)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    path.chmod(0o600)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch-root", type=Path, default=DEFAULT_BATCH)
    parser.add_argument("--evidence", type=Path, default=DEFAULT_EVIDENCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    evidence = json.loads(args.evidence.read_text(encoding="utf-8"))
    by_episode = {row["episode"]: row for row in evidence["episodes"]}
    records = []
    for episode_index in range(10):
        episode = f"episode-{episode_index:02d}"
        ego_speed = float(by_episode[episode]["ego"]["speed_mps"])
        for seed in (42, 43, 44):
            run_root = args.batch_root / episode / f"seed-{seed}"
            coc = (run_root / "generated_coc.txt").read_text(encoding="utf-8").strip()
            points, speeds = load_trajectory(run_root / "predicted_trajectory.npz")
            actions = parse_actions(coc)
            action_results = {
                action: classify_action(action, coc, points, speeds, ego_speed)
                for action in sorted(actions)
            }
            records.append(
                {
                    "episode": episode,
                    "seed": seed,
                    "coc_sha256": hashlib.sha256(coc.encode("utf-8")).hexdigest(),
                    "parsed_actions": sorted(actions),
                    "phase_aware_verdict": aggregate(action_results),
                    "action_results": action_results,
                    "trajectory_summary": {
                        "ego_speed_at_t0_mps": round(ego_speed, 6),
                        "minimum_predicted_speed_mps": round(float(speeds.min()), 6),
                        "minimum_speed_time_s": round(float((speeds.argmin() + 1) * DT_S), 3),
                        "terminal_speed_mps": round(float(speeds[-5:].mean()), 6),
                        "minimum_lateral_m": round(float(points[:, 1].min()), 6),
                        "maximum_lateral_m": round(float(points[:, 1].max()), 6),
                    },
                }
            )

    counts = {
        verdict: sum(row["phase_aware_verdict"] == verdict for row in records)
        for verdict in ("SUPPORTED", "CONTRADICTED", "THRESHOLD_SENSITIVE", "UNKNOWN")
    }
    result = {
        "experiment_id": "ALP-EXP-005-PHASE-AWARE-ALIGNMENT-V1",
        "publication_control": "LICENSE_RESTRICTED_INTERNAL_RESULT",
        "raw_coc_text_included": False,
        "scope": "Action-phase reanalysis; hold/release safety remains ungrounded",
        "logic_templates": [
            "F_[0,D](deceleration_response)",
            "F_[0,H](stop_response)",
            "F_[0,H](directed_lateral_excursion)",
            "G_[0,2](keep_lane) followed by release-dependent lane change",
        ],
        "summary": {"run_count": len(records), **counts},
        "runs": records,
        "limitations": [
            "This reanalysis recognizes response phases but does not establish hazard hold or release correctness.",
            "Yield and keep-distance cannot be decided from trajectory kinematics alone.",
            "Threshold grids are sensitivity probes and are not calibrated legal or vehicle-specific limits.",
            "A supported action response is not evidence of a safe trajectory.",
        ],
    }
    write_json(args.output, result)
    print(json.dumps({"output": str(args.output), "summary": result["summary"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
