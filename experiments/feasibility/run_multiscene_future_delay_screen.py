#!/usr/bin/env python3
"""Screen ten Alpamayo episodes for excess fragility under actor delay.

The screen time-shifts sufficiently moving obstacle tracks and compares each
model plan with the recorded human plan under the identical actor future.  It
is an exploratory ranking tool, not a collision probability or safety proof.
"""

from __future__ import annotations

import argparse
import io
import json
import math
import zipfile
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from physical_ai_av import PhysicalAIAVDatasetInterface
from scipy.spatial.transform import Rotation


ROOT = Path(__file__).resolve().parents[2]
BATCH = ROOT / "artifacts/results/restricted/alp-exp-005/feasibility-batch-v0"
DEFAULT_OUTPUT = BATCH / "multiscene-future-delay-screen-v0"
DATA_ROOT = ROOT / "data/restricted/nvidia_physicalai"
TIMES_S = np.arange(1, 65, dtype=float) / 10.0
DELAYS_S = np.arange(0, 21, dtype=float) / 10.0
MARGIN_M = 0.25
MIN_ACTOR_MOTION_M = 0.5
MAX_SYNCHRONIZED_CENTER_DISTANCE_M = 20.0


@dataclass(frozen=True)
class RectangleSeries:
    center: np.ndarray
    yaw: np.ndarray
    length: np.ndarray
    width: np.ndarray


def load_obstacles(interface: PhysicalAIAVDatasetInterface, clip_id: str) -> pd.DataFrame:
    feature = interface.features.LABELS.OBSTACLE_OFFLINE
    chunk = int(interface.get_clip_chunk(clip_id))
    filename = interface.features.get_chunk_feature_filename(chunk, feature)
    member = interface.features.get_clip_files_in_zip(clip_id, feature)[feature]
    with interface.open_file(filename, maybe_stream=True) as source:
        with zipfile.ZipFile(source) as archive:
            raw = archive.read(member)
    frame = pd.read_parquet(io.BytesIO(raw)).copy()
    frame["timestamp_us"] = frame["timestamp_us"].astype("int64")
    return frame


def plan_from_npz(path: Path, key: str) -> tuple[np.ndarray, np.ndarray]:
    data = np.load(path)
    xyz = np.asarray(data[key]).reshape(-1, 64, 3)[0]
    rotation_key = "gt_rot" if key == "gt_xyz" else "pred_rot"
    matrices = np.asarray(data[rotation_key]).reshape(-1, 64, 3, 3)[0]
    yaw = np.arctan2(matrices[:, 1, 0], matrices[:, 0, 0])
    return xyz[:, :2], yaw


def transform_track(track: pd.DataFrame, egomotion: object, pose0: object, t0_us: int) -> dict[str, np.ndarray | str]:
    times = track["reference_frame_timestamp_us"].to_numpy(dtype=np.int64)
    local = track[["center_x", "center_y", "center_z"]].to_numpy(dtype=float)
    relative_pose = pose0.inv() * egomotion(times).pose
    centers = relative_pose.apply(local)
    local_rotation = Rotation.from_quat(
        track[["orientation_x", "orientation_y", "orientation_z", "orientation_w"]].to_numpy(dtype=float)
    )
    rotation_t0 = relative_pose.rotation * local_rotation
    matrices = rotation_t0.as_matrix()
    yaw = np.unwrap(np.arctan2(matrices[:, 1, 0], matrices[:, 0, 0]))
    return {
        "relative_s": (times - t0_us) / 1e6,
        "center": centers[:, :2],
        "yaw": yaw,
        "length": track["size_x"].to_numpy(dtype=float),
        "width": track["size_y"].to_numpy(dtype=float),
        "label_class": str(track.iloc[0].label_class),
    }


def interpolate_actor(track: dict[str, np.ndarray | str], query_s: np.ndarray) -> RectangleSeries:
    relative = np.asarray(track["relative_s"])
    return RectangleSeries(
        center=np.column_stack([
            np.interp(query_s, relative, np.asarray(track["center"])[:, axis]) for axis in range(2)
        ]),
        yaw=np.interp(query_s, relative, np.asarray(track["yaw"])),
        length=np.interp(query_s, relative, np.asarray(track["length"])),
        width=np.interp(query_s, relative, np.asarray(track["width"])),
    )


def rectangle(center: np.ndarray, yaw: float, length: float, width: float) -> np.ndarray:
    local = np.array([
        [length / 2, width / 2], [-length / 2, width / 2],
        [-length / 2, -width / 2], [length / 2, -width / 2],
    ])
    cosine, sine = math.cos(yaw), math.sin(yaw)
    rotation = np.array([[cosine, -sine], [sine, cosine]])
    return local @ rotation.T + center


def point_segment_distance(point: np.ndarray, start: np.ndarray, end: np.ndarray) -> float:
    segment = end - start
    denominator = float(segment @ segment)
    if denominator == 0:
        return float(np.linalg.norm(point - start))
    fraction = float(np.clip((point - start) @ segment / denominator, 0, 1))
    return float(np.linalg.norm(point - (start + fraction * segment)))


def polygon_signed_distance(first: np.ndarray, second: np.ndarray) -> float:
    axes = []
    for polygon in (first, second):
        edges = np.roll(polygon, -1, axis=0) - polygon
        normals = np.column_stack([-edges[:, 1], edges[:, 0]])
        axes.extend(normals / np.linalg.norm(normals, axis=1, keepdims=True))
    overlaps = []
    separated = False
    for axis in axes:
        first_projection, second_projection = first @ axis, second @ axis
        overlap = min(first_projection.max(), second_projection.max()) - max(first_projection.min(), second_projection.min())
        overlaps.append(float(overlap))
        separated |= overlap < 0
    if not separated:
        return -min(overlaps)
    distances = []
    for polygon_a, polygon_b in ((first, second), (second, first)):
        for point in polygon_a:
            for index in range(4):
                distances.append(point_segment_distance(point, polygon_b[index], polygon_b[(index + 1) % 4]))
    return min(distances)


def clearance_series(
    plan_xy: np.ndarray,
    plan_yaw: np.ndarray,
    actor: RectangleSeries,
    vehicle_length: float,
    vehicle_width: float,
    rear_axle_to_center: float,
) -> np.ndarray:
    output = np.empty(len(TIMES_S))
    for index in range(len(TIMES_S)):
        heading = np.array([math.cos(plan_yaw[index]), math.sin(plan_yaw[index])])
        ego_center = plan_xy[index] + rear_axle_to_center * heading
        ego_box = rectangle(ego_center, float(plan_yaw[index]), vehicle_length, vehicle_width)
        actor_box = rectangle(
            actor.center[index], float(actor.yaw[index]),
            float(actor.length[index]), float(actor.width[index]),
        )
        output[index] = polygon_signed_distance(ego_box, actor_box) - MARGIN_M
    return output


def candidate_tracks(
    obstacles: pd.DataFrame,
    egomotion: object,
    pose0: object,
    t0_us: int,
    plan_paths: list[np.ndarray],
) -> dict[str, dict[str, np.ndarray | str]]:
    output = {}
    ordered = obstacles.sort_values(["track_id", "timestamp_us"])
    for track_id, frame in ordered.groupby("track_id", sort=True):
        times = frame["reference_frame_timestamp_us"].to_numpy(dtype=np.int64)
        if times.min() > t0_us or times.max() < t0_us + int(TIMES_S[-1] * 1e6):
            continue
        track = transform_track(frame, egomotion, pose0, t0_us)
        baseline = interpolate_actor(track, TIMES_S)
        motion = float(np.linalg.norm(baseline.center[-1] - baseline.center[0]))
        if motion < MIN_ACTOR_MOTION_M:
            continue
        synchronized_distance = min(
            float(np.min(np.linalg.norm(baseline.center - path, axis=1))) for path in plan_paths
        )
        if synchronized_distance > MAX_SYNCHRONIZED_CENTER_DISTANCE_M:
            continue
        track["baseline_motion_m"] = np.array([motion])
        track["synchronized_center_distance_m"] = np.array([synchronized_distance])
        output[str(track_id)] = track
    return output


def analyze_model(
    plan_xy: np.ndarray,
    plan_yaw: np.ndarray,
    human_xy: np.ndarray,
    human_yaw: np.ndarray,
    tracks: dict[str, dict[str, np.ndarray | str]],
    dimensions: object,
) -> dict[str, object]:
    best = None
    for track_id, track in tracks.items():
        baseline_model_clearance = None
        for delay_s in DELAYS_S:
            actor = interpolate_actor(track, np.maximum(0.0, TIMES_S - delay_s))
            model_clearance = clearance_series(
                plan_xy, plan_yaw, actor, float(dimensions.length), float(dimensions.width),
                float(dimensions.rear_axle_to_bbox_center),
            )
            if delay_s == 0:
                baseline_model_clearance = float(np.min(model_clearance))
            index = int(np.argmin(model_clearance))
            record = {
                "track_id": track_id,
                "label_class": track["label_class"],
                "delay_s": float(delay_s),
                "model_minimum_clearance_m": float(model_clearance[index]),
                "model_worst_time_s": float(TIMES_S[index]),
                "model_baseline_same_track_clearance_m": baseline_model_clearance,
                "actor_motion_m": float(np.asarray(track["baseline_motion_m"])[0]),
                "baseline_synchronized_center_distance_m": float(np.asarray(track["synchronized_center_distance_m"])[0]),
            }
            if best is None or record["model_minimum_clearance_m"] < best["model_minimum_clearance_m"]:
                best = record
    assert best is not None
    selected_track = tracks[str(best["track_id"])]
    selected_actor = interpolate_actor(selected_track, np.maximum(0.0, TIMES_S - float(best["delay_s"])))
    human_clearance = clearance_series(
        human_xy, human_yaw, selected_actor, float(dimensions.length), float(dimensions.width),
        float(dimensions.rear_axle_to_bbox_center),
    )
    human_index = int(np.argmin(human_clearance))
    best["human_minimum_same_counterfactual_m"] = float(human_clearance[human_index])
    best["human_worst_time_s"] = float(TIMES_S[human_index])
    best["model_excess_clearance_loss_m"] = (
        best["human_minimum_same_counterfactual_m"] - best["model_minimum_clearance_m"]
    )
    best["model_overlap_candidate"] = best["model_minimum_clearance_m"] <= 0
    best["human_overlap_same_counterfactual"] = best["human_minimum_same_counterfactual_m"] <= 0
    best["counterfactual_induced_model_overlap"] = (
        best["model_baseline_same_track_clearance_m"] > 0 and best["model_minimum_clearance_m"] <= 0
    )
    return best


def priority(record: dict[str, object]) -> str:
    if record["counterfactual_induced_model_overlap"] and not record["human_overlap_same_counterfactual"]:
        return "P1_COUNTERFACTUAL_MODEL_ONLY_OVERLAP"
    if record["model_overlap_candidate"] and not record["human_overlap_same_counterfactual"]:
        return "P1_MODEL_ONLY_OVERLAP"
    loss = float(record["model_excess_clearance_loss_m"])
    if loss >= 2.0:
        return "P2_EXCESS_LOSS_GE_2M"
    if loss >= 0.5:
        return "P3_EXCESS_LOSS_GE_0.5M"
    return "P4_NO_STRONG_DIFFERENTIAL"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--data-root", type=Path, default=DATA_ROOT)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True, mode=0o700)

    rows = []
    episode_summaries = []
    for episode_dir in sorted(BATCH.glob("episode-*")):
        manifest = json.loads((episode_dir / "seed-44/manifest.json").read_text(encoding="utf-8"))
        clip_id, t0_us = manifest["clip_id"], int(manifest["t0_us"])
        interface = PhysicalAIAVDatasetInterface(
            local_dir=args.data_root.resolve(), revision=manifest["dataset_revision"],
            confirm_download_threshold_gb=float("inf"),
        )
        egomotion = interface.get_clip_feature(clip_id, interface.features.LABELS.EGOMOTION, maybe_stream=True)
        pose0 = egomotion(t0_us).pose
        obstacles = load_obstacles(interface, clip_id)
        dimensions = interface.get_clip_feature(clip_id, "vehicle_dimensions", maybe_stream=True)
        human_xy, human_yaw = plan_from_npz(episode_dir / "seed-44/ground_truth_trajectory.npz", "gt_xyz")
        reconstructed = np.stack([
            (pose0.inv() * egomotion(t0_us + int(t * 1e6)).pose).translation[:2] for t in TIMES_S
        ])
        coordinate_rmse = np.sqrt(np.mean((reconstructed - human_xy) ** 2, axis=0))
        if float(np.max(coordinate_rmse)) > 1e-4:
            raise RuntimeError(f"{episode_dir.name}: coordinate validation failed {coordinate_rmse}")
        model_plans = {
            seed: plan_from_npz(episode_dir / f"seed-{seed}/predicted_trajectory.npz", "pred_xyz")
            for seed in (42, 43, 44)
        }
        tracks = candidate_tracks(
            obstacles, egomotion, pose0, t0_us,
            [human_xy] + [model_plans[seed][0] for seed in (42, 43, 44)],
        )
        episode_record = {
            "episode": episode_dir.name,
            "clip_id": clip_id,
            "t0_us": t0_us,
            "coordinate_rmse_m": coordinate_rmse.tolist(),
            "candidate_moving_track_count": len(tracks),
            "status": "ANALYZED" if tracks else "NO_ELIGIBLE_FULL_HORIZON_MOVING_TRACK",
        }
        episode_summaries.append(episode_record)
        if not tracks:
            continue
        for seed, (plan_xy, plan_yaw) in model_plans.items():
            result = analyze_model(plan_xy, plan_yaw, human_xy, human_yaw, tracks, dimensions)
            coc = (episode_dir / f"seed-{seed}/generated_coc.txt").read_text(encoding="utf-8").strip()
            row = {"episode": episode_dir.name, "seed": seed, "clip_id": clip_id, "coc": coc, **result}
            row["review_priority"] = priority(row)
            rows.append(row)
        print(json.dumps({"episode": episode_dir.name, "tracks": len(tracks), "rows": 3}), flush=True)

    frame = pd.DataFrame(rows).sort_values(
        ["review_priority", "model_excess_clearance_loss_m"], ascending=[True, False]
    )
    frame.to_csv(args.output / "ranked_candidates.csv", index=False)
    records = frame.to_dict(orient="records")
    summary = {
        "status": "EXPLORATORY_MULTISCENE_SCREEN_REQUIRES_TARGETED_HUMAN_REVIEW",
        "episode_count": len(episode_summaries),
        "analyzed_model_plan_count": len(records),
        "parameters": {
            "actor_delay_s": [0.0, 2.0, 0.1], "margin_m": MARGIN_M,
            "minimum_actor_motion_m": MIN_ACTOR_MOTION_M,
            "maximum_synchronized_center_distance_m": MAX_SYNCHRONIZED_CENTER_DISTANCE_M,
        },
        "priority_counts": frame.review_priority.value_counts().to_dict(),
        "top_candidates": records[:10],
        "episodes": episode_summaries,
        "claim_boundary": [
            "Actor delay is a deterministic plausibility stress test, not a calibrated future distribution.",
            "Worst-track selection is scene-level and does not establish that the CoC refers to that actor.",
            "Oriented-box overlap with a 0.25 m margin is a review candidate, not a crash claim.",
            "Other-agent reactions to a model plan are not resimulated.",
        ],
    }
    (args.output / "result.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    for path in args.output.iterdir():
        path.chmod(0o600)
    print(json.dumps({"priority_counts": summary["priority_counts"], "top": records[:3]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
