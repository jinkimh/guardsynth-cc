#!/usr/bin/env python3
"""Assess whether official obstacle tracks can parameterize distance contracts."""

from __future__ import annotations

import argparse
import io
import json
import math
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
from physical_ai_av import PhysicalAIAVDatasetInterface


ROOT = Path("data/restricted/nvidia_physicalai")
DEFAULT_COHORT = ROOT / "internal-derived/cohort-10/cohort-conformance.json"
SNAPSHOT_TOLERANCE_US = 50_000
RATE_WINDOW_US = 500_000


def load_obstacles(
    interface: PhysicalAIAVDatasetInterface, clip_id: str
) -> tuple[pd.DataFrame, dict[str, object]]:
    feature = interface.features.LABELS.OBSTACLE_OFFLINE
    chunk = int(interface.get_clip_chunk(clip_id))
    chunk_file = interface.features.get_chunk_feature_filename(chunk, feature)
    member = interface.features.get_clip_files_in_zip(clip_id, feature)[feature]
    with interface.open_file(chunk_file, maybe_stream=True) as source:
        with zipfile.ZipFile(source) as archive:
            raw = archive.read(member)
    frame = pd.read_parquet(io.BytesIO(raw)).copy()
    frame["timestamp_us"] = frame["timestamp_us"].astype("int64")
    return frame, {
        "chunk_file": chunk_file,
        "archive_member": member,
        "extracted_bytes": len(raw),
    }


def add_oriented_extents(frame: pd.DataFrame) -> pd.DataFrame:
    qx, qy, qz, qw = (frame[column].to_numpy() for column in (
        "orientation_x", "orientation_y", "orientation_z", "orientation_w"
    ))
    yaw = np.arctan2(2 * (qw * qz + qx * qy), 1 - 2 * (qy * qy + qz * qz))
    cosine, sine = np.abs(np.cos(yaw)), np.abs(np.sin(yaw))
    frame["half_extent_x"] = cosine * frame["size_x"] / 2 + sine * frame["size_y"] / 2
    frame["half_extent_y"] = sine * frame["size_x"] / 2 + cosine * frame["size_y"] / 2
    return frame


def corridor_snapshot(
    obstacles: pd.DataFrame,
    timestamp_us: int,
    ego_front_extent: float,
    ego_half_width: float,
) -> pd.DataFrame:
    snapshot = obstacles[
        (obstacles["timestamp_us"] >= timestamp_us - SNAPSHOT_TOLERANCE_US)
        & (obstacles["timestamp_us"] <= timestamp_us + SNAPSHOT_TOLERANCE_US)
    ].copy()
    snapshot["timestamp_error_us"] = (snapshot["timestamp_us"] - timestamp_us).abs()
    snapshot = snapshot.sort_values("timestamp_error_us").drop_duplicates("track_id")
    snapshot["longitudinal_gap_m"] = (
        snapshot["center_x"] - snapshot["half_extent_x"] - ego_front_extent
    )
    snapshot["corridor_overlap"] = (
        snapshot["center_y"].abs() <= ego_half_width + snapshot["half_extent_y"]
    )
    return snapshot[
        (snapshot["longitudinal_gap_m"] >= 0) & snapshot["corridor_overlap"]
    ].sort_values("longitudinal_gap_m")


def gap_rate(
    obstacles: pd.DataFrame,
    track_id: object,
    timestamp_us: int,
    ego_front_extent: float,
) -> dict[str, float | int | None]:
    track = obstacles[
        (obstacles["track_id"] == track_id)
        & (obstacles["timestamp_us"] >= timestamp_us - RATE_WINDOW_US)
        & (obstacles["timestamp_us"] <= timestamp_us + RATE_WINDOW_US)
    ].sort_values("timestamp_us")
    if len(track) < 3:
        return {"sample_count": len(track), "gap_rate_mps": None, "closing_speed_mps": None}
    seconds = (track["timestamp_us"].to_numpy() - timestamp_us) / 1e6
    gaps = track["center_x"].to_numpy() - track["half_extent_x"].to_numpy() - ego_front_extent
    rate = float(np.polyfit(seconds, gaps, 1)[0])
    return {
        "sample_count": len(track),
        "gap_rate_mps": round(rate, 6),
        "closing_speed_mps": round(max(0.0, -rate), 6),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--cohort", type=Path, default=DEFAULT_COHORT)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    cohort = json.loads(args.cohort.read_text(encoding="utf-8"))
    interface = PhysicalAIAVDatasetInterface(
        local_dir=args.root.resolve(), confirm_download_threshold_gb=float("inf")
    )

    episodes = []
    candidate_count = 0
    rate_count = 0
    for episode in cohort["episodes"]:
        clip_id = episode["clip_id"]
        obstacles, archive = load_obstacles(interface, clip_id)
        obstacles = add_oriented_extents(obstacles)
        dimensions = interface.get_clip_feature(clip_id, "vehicle_dimensions", maybe_stream=True)
        ego_front_extent = float(
            dimensions.rear_axle_to_bbox_center + dimensions.length / 2
        )
        ego_half_width = float(dimensions.width / 2)
        events = []
        for event in episode["events"]:
            timestamp_us = int(event["timestamp_us"])
            candidates = corridor_snapshot(
                obstacles, timestamp_us, ego_front_extent, ego_half_width
            )
            record = {
                "source_index": event["source_index"],
                "timestamp_us": timestamp_us,
                "candidate_count": len(candidates),
                "association_status": "NO_FORWARD_CORRIDOR_CANDIDATE",
                "nearest_candidate": None,
            }
            if not candidates.empty:
                nearest = candidates.iloc[0]
                rates = gap_rate(
                    obstacles, nearest["track_id"], timestamp_us, ego_front_extent
                )
                gap = float(nearest["longitudinal_gap_m"])
                closing = rates["closing_speed_mps"]
                ttc = None if not closing else gap / float(closing)
                record.update(
                    {
                        "association_status": "GEOMETRIC_CANDIDATE_SEMANTIC_MATCH_UNRESOLVED",
                        "nearest_candidate": {
                            "track_id": str(nearest["track_id"]),
                            "label_class": str(nearest["label_class"]),
                            "longitudinal_gap_m": round(gap, 6),
                            "lateral_center_m": round(float(nearest["center_y"]), 6),
                            "timestamp_error_us": int(nearest["timestamp_error_us"]),
                            **rates,
                            "candidate_ttc_s": None if ttc is None else round(ttc, 6),
                        },
                    }
                )
                candidate_count += 1
                rate_count += rates["gap_rate_mps"] is not None
            events.append(record)
        episodes.append(
            {
                "clip_id": clip_id,
                "event_cluster": episode["event_cluster"],
                "archive": archive,
                "vehicle_dimensions": {
                    "length_m": float(dimensions.length),
                    "width_m": float(dimensions.width),
                    "rear_axle_to_front_extent_m": ego_front_extent,
                },
                "obstacle_rows": len(obstacles),
                "events": events,
            }
        )

    event_count = sum(len(episode["events"]) for episode in episodes)
    report = {
        "checker": "OFFICIAL_NVIDIA_OBSTACLE_CONTRACT_INPUT_FEASIBILITY",
        "publication_control": cohort["publication_control"],
        "coordinate_convention": {
            "frame": "rig",
            "x": "forward",
            "y": "left",
            "source": "NVlabs physical_ai_av wiki revision 55104756a2ba5c7340dfe185cb7ae38d0991ff2d",
        },
        "method": {
            "snapshot_tolerance_us": SNAPSHOT_TOLERANCE_US,
            "gap_rate_window_us": RATE_WINDOW_US,
            "oriented_box_extent": True,
            "corridor_overlap": "ego and obstacle lateral projected half-extents overlap",
        },
        "summary": {
            "episode_count": len(episodes),
            "event_count": event_count,
            "events_with_geometric_candidate": candidate_count,
            "events_with_gap_rate": rate_count,
            "geometric_input_readiness": "PASS",
            "semantic_hazard_association": "UNRESOLVED",
            "safe_distance_contract": "NOT_JUSTIFIED",
            "physical_safety": "UNKNOWN",
        },
        "episodes": episodes,
    }
    output = args.output or args.root / "internal-derived/cohort-10/obstacle-feasibility.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["summary"], indent=2))


if __name__ == "__main__":
    main()
