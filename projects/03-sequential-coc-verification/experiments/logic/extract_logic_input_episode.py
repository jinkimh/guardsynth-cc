#!/usr/bin/env python3
"""Extract one episode's restricted numeric evidence in a short-lived process."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np


ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "PROJECT_REGISTRY.json").is_file())
FEASIBILITY_DIR = ROOT / "projects/03-sequential-coc-verification/experiments/feasibility"
if str(FEASIBILITY_DIR) not in sys.path:
    sys.path.insert(0, str(FEASIBILITY_DIR))

from analyze_nvidia_obstacle_feasibility import (  # noqa: E402
    add_oriented_extents,
    corridor_snapshot,
    load_obstacles,
)
from physical_ai_av import PhysicalAIAVDatasetInterface  # noqa: E402


DEFAULT_COHORT = (
    ROOT
    / "data/restricted/nvidia_physicalai/internal-derived/cohort-10"
    / "cohort-conformance.json"
)
DEFAULT_DATA_ROOT = ROOT / "data/restricted/nvidia_physicalai"


def estimate_obstacle_speed_mps(obstacles, track_id, timestamp_us, ego_speed_mps):
    track = obstacles[
        (obstacles["track_id"] == track_id)
        & (obstacles["timestamp_us"] >= timestamp_us - 500_000)
        & (obstacles["timestamp_us"] <= timestamp_us + 500_000)
    ].sort_values("timestamp_us")
    if len(track) < 3:
        return None, len(track)
    seconds = (track["timestamp_us"].to_numpy() - timestamp_us) / 1e6
    relative_rate = float(np.polyfit(seconds, track["center_x"].to_numpy(), 1)[0])
    return max(0.0, ego_speed_mps + relative_rate), len(track)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--episode-index", type=int, required=True)
    parser.add_argument("--cohort", type=Path, default=DEFAULT_COHORT)
    parser.add_argument("--data-root", type=Path, default=DEFAULT_DATA_ROOT)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    cohort = json.loads(args.cohort.read_text(encoding="utf-8"))
    episode = cohort["episodes"][args.episode_index]
    clip_id = episode["clip_id"]
    timestamp_us = int(episode["events"][0]["timestamp_us"])
    interface = PhysicalAIAVDatasetInterface(
        local_dir=args.data_root.resolve(), confirm_download_threshold_gb=float("inf")
    )
    obstacles, _ = load_obstacles(interface, clip_id)
    obstacles = add_oriented_extents(obstacles)
    dimensions = interface.get_clip_feature(clip_id, "vehicle_dimensions", maybe_stream=True)
    ego_front = float(dimensions.rear_axle_to_bbox_center + dimensions.length / 2)
    ego_rear = float(dimensions.length - ego_front)
    ego_half_width = float(dimensions.width / 2)
    candidates = corridor_snapshot(obstacles, timestamp_us, ego_front, ego_half_width)
    ego_history = interface.get_clip_feature(
        clip_id, interface.features.LABELS.EGOMOTION, maybe_stream=True
    )
    ego_state = ego_history(timestamp_us)
    ego_speed = float(np.linalg.norm(ego_state.velocity[:2]))

    obstacle_record = None
    if not candidates.empty:
        obstacle = candidates.iloc[0]
        obstacle_speed, sample_count = estimate_obstacle_speed_mps(
            obstacles, obstacle["track_id"], timestamp_us, ego_speed
        )
        obstacle_record = {
            "track_id_hash": hashlib.sha256(
                str(obstacle["track_id"]).encode("utf-8")
            ).hexdigest(),
            "label_class": str(obstacle["label_class"]),
            "center_x": float(obstacle["center_x"]),
            "center_y": float(obstacle["center_y"]),
            "half_extent_x": float(obstacle["half_extent_x"]),
            "half_extent_y": float(obstacle["half_extent_y"]),
            "initial_longitudinal_gap_m": float(obstacle["longitudinal_gap_m"]),
            "constant_world_speed_estimate_mps": obstacle_speed,
            "speed_fit_sample_count": sample_count,
        }

    history_record = None
    if args.episode_index == 6:
        history_start_us = max(int(ego_history.timestamps[0]), timestamp_us - 11_000_000)
        history_timestamps = np.arange(
            history_start_us, timestamp_us + 1, 100_000, dtype=np.int64
        )
        history_speeds = [
            float(np.linalg.norm(ego_history(int(value)).velocity[:2]))
            for value in history_timestamps
        ]
        history_record = {
            "start_us": int(history_start_us),
            "end_us": timestamp_us,
            "timestamps_us": [int(value) for value in history_timestamps],
            "speeds_mps": history_speeds,
        }

    result = {
        "episode_index": args.episode_index,
        "episode": f"episode-{args.episode_index:02d}",
        "clip_id_hash": hashlib.sha256(clip_id.encode("utf-8")).hexdigest(),
        "timestamp_us": timestamp_us,
        "ego": {
            "front_extent_m": ego_front,
            "rear_extent_m": ego_rear,
            "half_width_m": ego_half_width,
            "speed_mps": ego_speed,
        },
        "nearest_forward_corridor_obstacle": obstacle_record,
        "stop_history": history_record,
        "publication_control": "LICENSE_RESTRICTED_INTERNAL_DERIVED_INPUT",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    args.output.chmod(0o600)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
