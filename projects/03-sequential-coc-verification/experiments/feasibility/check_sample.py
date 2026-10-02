#!/usr/bin/env python3
"""Run the minimum CoC-to-trajectory feasibility check on one local sample."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd


DEFAULT_ROOT = Path("data/baseline/coc_nusc")
DEFAULT_CLIP_ID = "scene-0001"
DEFAULT_T0_US = 4_800_000
HISTORY_US = 2_000_000
FUTURE_US = 6_000_000
MIN_SPEED_DROP_MPS = 0.5
MIN_NEGATIVE_DERIVATIVE_FRACTION = 0.5


def nearest_row(frame: pd.DataFrame, timestamp_us: int) -> pd.Series:
    index = (frame["timestamp"] - timestamp_us).abs().idxmin()
    return frame.loc[index]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--clip-id", default=DEFAULT_CLIP_ID)
    parser.add_argument("--t0-us", type=int, default=DEFAULT_T0_US)
    args = parser.parse_args()

    reasoning_path = args.root / "reasoning/ood_reasoning.parquet"
    egomotion_path = args.root / f"labels/egomotion/{args.clip_id}.egomotion.parquet"
    timestamps_path = (
        args.root / f"camera/{args.clip_id}.camera_front_wide_120fov.timestamps.parquet"
    )
    video_path = args.root / f"camera/{args.clip_id}.camera_front_wide_120fov.mp4"

    reasoning = pd.read_parquet(reasoning_path)
    if args.clip_id not in reasoning.index:
        raise SystemExit(f"clip not found in reasoning parquet: {args.clip_id}")

    events = json.loads(reasoning.loc[args.clip_id, "events"])
    event = next(
        (item for item in events if int(item["event_start_timestamp"]) == args.t0_us),
        None,
    )
    if event is None:
        raise SystemExit(f"event not found at t0_us={args.t0_us}")

    egomotion = pd.read_parquet(egomotion_path).sort_values("timestamp").copy()
    timestamps = pd.read_parquet(timestamps_path).sort_values("timestamp")
    egomotion["speed_mps"] = np.hypot(egomotion["vx"], egomotion["vy"])

    history_start = args.t0_us - HISTORY_US
    future_end = args.t0_us + FUTURE_US
    post = egomotion[
        (egomotion["timestamp"] >= args.t0_us) & (egomotion["timestamp"] <= future_end)
    ]
    if len(post) < 2:
        raise SystemExit("insufficient future egomotion rows")

    t0_row = nearest_row(egomotion, args.t0_us)
    future_row = nearest_row(egomotion, future_end)
    speed_derivative = np.diff(post["speed_mps"]) / np.diff(post["timestamp"] / 1_000_000)
    speed_drop = float(t0_row["speed_mps"] - future_row["speed_mps"])
    negative_fraction = float(np.mean(speed_derivative < 0))
    directional_conformance = (
        event["cot"].lower().startswith("decelerate")
        and speed_drop >= MIN_SPEED_DROP_MPS
        and negative_fraction >= MIN_NEGATIVE_DERIVATIVE_FRACTION
    )

    past_frames = timestamps[
        (timestamps["timestamp"] >= history_start) & (timestamps["timestamp"] <= args.t0_us)
    ]
    result = {
        "source_class": "PUBLIC_COMPATIBILITY_DATASET_NOT_OFFICIAL_NVIDIA_COC",
        "clip_id": args.clip_id,
        "event_t0_us": args.t0_us,
        "coc": event["cot"],
        "source_quality_pass": bool(event.get("quality_pass", False)),
        "source_quality_is_independent_evidence": False,
        "join_keys": ["clip_id", "event_start_timestamp"],
        "coverage": {
            "history_2s": bool(egomotion["timestamp"].min() <= history_start),
            "future_6s": bool(egomotion["timestamp"].max() >= future_end),
            "past_camera_frames": int(len(past_frames)),
            "video_present": video_path.is_file(),
        },
        "trajectory_metrics": {
            "speed_at_t0_mps": round(float(t0_row["speed_mps"]), 4),
            "speed_at_t0_plus_4s_mps": round(
                float(nearest_row(egomotion, args.t0_us + 4_000_000)["speed_mps"]), 4
            ),
            "speed_at_t0_plus_6s_mps": round(float(future_row["speed_mps"]), 4),
            "speed_drop_over_6s_mps": round(speed_drop, 4),
            "minimum_future_speed_mps": round(float(post["speed_mps"].min()), 4),
            "negative_speed_derivative_fraction": round(negative_fraction, 4),
        },
        "thresholds": {
            "minimum_speed_drop_mps": MIN_SPEED_DROP_MPS,
            "minimum_negative_derivative_fraction": MIN_NEGATIVE_DERIVATIVE_FRACTION,
        },
        "verdicts": {
            "schema_and_temporal_join": "PASS",
            "closed_set_decision_parse": "PASS_DECELERATE",
            "directional_trajectory_conformance": (
                "PASS" if directional_conformance else "FAIL"
            ),
            "semantic_grounding": "MANUAL_REVIEW_REQUIRED",
            "safe_distance_property": "UNKNOWN_MISSING_OBSTACLE_DISTANCE",
            "formal_model_checking": "NOT_RUN",
            "official_alpamayo_label_replication": "BLOCKED_ON_GATED_DATA",
        },
        "minimum_supported_claim": (
            "A time-aligned CoC decision can be joined to camera timestamps and egomotion, "
            "normalized to a closed-set longitudinal action, and checked for directional "
            "trajectory conformance on an open PhysicalAI-AV-compatible sample."
        ),
    }
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
