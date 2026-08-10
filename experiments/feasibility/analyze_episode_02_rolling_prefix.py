#!/usr/bin/env python3
"""Analyze executable 0.5 s segments from episode-02 rolling inference."""

from __future__ import annotations

import io
import json
import math
import os
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
from physical_ai_av import PhysicalAIAVDatasetInterface

os.environ.setdefault("MPLCONFIGDIR", "/tmp/coc-matplotlib")
import matplotlib.pyplot as plt

from run_multiscene_future_delay_screen import (
    BATCH,
    DATA_ROOT,
    interpolate_actor,
    plan_from_npz,
    point_segment_distance,
    polygon_signed_distance,
    rectangle,
    transform_track,
)


EPISODE = BATCH / "episode-02"
ROLLING = BATCH / "episode-02-rolling-prefix-v0"
OUTPUT = ROLLING / "analysis-v0"
CLIP_ID = "13f0af4c-2565-4a4d-b765-7f397f1d1684"
BASE_T0_US = 5_148_839
OFFSETS_US = tuple(range(0, 3_000_001, 500_000))
SEEDS = (42, 43, 44)
TRACK_ID = "18"
EXECUTABLE_STEPS = 5
STEP_S = 0.1
MARGIN_M = 0.25


def load_track(interface: object) -> pd.DataFrame:
    feature = interface.features.LABELS.OBSTACLE_OFFLINE
    chunk = int(interface.get_clip_chunk(CLIP_ID))
    archive_path = interface.features.get_chunk_feature_filename(chunk, feature)
    member = interface.features.get_clip_files_in_zip(CLIP_ID, feature)[feature]
    with interface.open_file(archive_path, maybe_stream=True) as source:
        with zipfile.ZipFile(source) as archive:
            frame = pd.read_parquet(io.BytesIO(archive.read(member)))
    track = frame[frame.track_id.astype(str) == TRACK_ID].sort_values("timestamp_us").copy()
    if track.empty:
        raise RuntimeError("person track 18 is missing")
    return track


def run_dir(offset_us: int, seed: int) -> Path:
    if offset_us == 0:
        return EPISODE / f"seed-{seed}"
    return ROLLING / f"prefix-{offset_us // 1000:04d}ms/seed-{seed}"


def trajectory(path: Path, predicted: bool) -> tuple[np.ndarray, np.ndarray]:
    key = "pred_xyz" if predicted else "gt_xyz"
    return plan_from_npz(path, key)


def to_base_frame(
    local_xy: np.ndarray,
    local_yaw: np.ndarray,
    relative_pose: object,
) -> tuple[np.ndarray, np.ndarray]:
    local_xyz = np.column_stack([local_xy, np.zeros(len(local_xy))])
    base_xyz = relative_pose.apply(local_xyz)
    relative_matrix = relative_pose.rotation.as_matrix()
    relative_yaw = math.atan2(relative_matrix[1, 0], relative_matrix[0, 0])
    return base_xyz[:, :2], np.unwrap(local_yaw + relative_yaw)


def signed_clearance(
    plan_xy: np.ndarray,
    plan_yaw: np.ndarray,
    actor: object,
    dimensions: object,
) -> np.ndarray:
    output = np.empty(len(plan_xy))
    for index in range(len(plan_xy)):
        heading = np.array([math.cos(plan_yaw[index]), math.sin(plan_yaw[index])])
        ego_center = plan_xy[index] + float(dimensions.rear_axle_to_bbox_center) * heading
        ego_box = rectangle(
            ego_center, float(plan_yaw[index]),
            float(dimensions.length), float(dimensions.width),
        )
        actor_box = rectangle(
            actor.center[index], float(actor.yaw[index]),
            float(actor.length[index]), float(actor.width[index]),
        )
        output[index] = polygon_signed_distance(ego_box, actor_box) - MARGIN_M
    return output


def speed_metrics(local_xy: np.ndarray, current_speed: float) -> dict[str, float]:
    points = np.vstack([np.zeros((1, 2)), local_xy])
    speeds = np.linalg.norm(np.diff(points, axis=0), axis=1) / STEP_S
    return {
        "current_speed_mps": current_speed,
        "mean_executable_speed_mps": float(np.mean(speeds)),
        "end_executable_speed_mps": float(speeds[-1]),
        "end_minus_current_speed_mps": float(speeds[-1] - current_speed),
        "executable_forward_progress_m": float(local_xy[-1, 0]),
        "executable_lateral_progress_m": float(local_xy[-1, 1]),
    }


def actor_phase(
    actor_at_prefix: object,
    ego_pose_base: object,
    dimensions: object,
    entry_side_sign: float,
) -> tuple[str, float, float]:
    point_base = np.array([*actor_at_prefix.center[0], 0.0])
    point_prefix = ego_pose_base.inv().apply(point_base)
    half_corridor = float(dimensions.width) / 2 + float(actor_at_prefix.width[0]) / 2 + MARGIN_M
    lateral = float(point_prefix[1])
    signed_from_entry_side = lateral * entry_side_sign
    if signed_from_entry_side > half_corridor:
        phase = "APPROACHING_EGO_CORRIDOR"
    elif signed_from_entry_side < -half_corridor:
        phase = "CLEARED_EGO_CORRIDOR"
    else:
        phase = "OCCUPYING_EGO_CORRIDOR"
    return phase, float(point_prefix[0]), lateral


def classify_coc(text: str) -> str:
    lowered = text.lower()
    if any(token in lowered for token in ("yield", "stop", "slow", "decel")):
        return "HOLD_OR_YIELD"
    if any(token in lowered for token in ("resume", "acceler", "proceed")):
        return "RELEASE_OR_PROCEED"
    return "UNSPECIFIED"


def make_plots(frame: pd.DataFrame, stitched: dict[str, np.ndarray], actor: object) -> None:
    colors = {
        "human_recorded": "#222222",
        "model_seed_42": "#1565c0",
        "model_seed_43": "#ef6c00",
        "model_seed_44": "#c62828",
    }
    figure, axes = plt.subplots(1, 3, figsize=(17, 5.5))
    for plan, color in colors.items():
        subset = frame[frame.plan == plan].sort_values("prefix_offset_s")
        axes[0].plot(
            subset.prefix_offset_s, subset.end_executable_speed_mps,
            marker="o", color=color, label=plan,
        )
        axes[1].plot(
            subset.prefix_offset_s, subset.minimum_executable_clearance_m,
            marker="o", color=color, label=plan,
        )
        path = stitched[plan]
        axes[2].plot(path[:, 0], path[:, 1], color=color, linewidth=2.3, label=plan)
    axes[0].set_title("End speed of each executable 0.5 s segment")
    axes[0].set_xlabel("prefix offset (s)")
    axes[0].set_ylabel("speed (m/s)")
    axes[0].grid(alpha=0.25)
    axes[1].axhline(0, color="#777777", linestyle="--")
    axes[1].set_title("Track-18 clearance in executable segment")
    axes[1].set_xlabel("prefix offset (s)")
    axes[1].set_ylabel("minimum signed clearance (m)")
    axes[1].grid(alpha=0.25)
    axes[2].plot(
        actor.center[:, 0], actor.center[:, 1],
        color="#8e24aa", linewidth=2.5, marker=".", label="recorded person 18",
    )
    axes[2].set_title("Stitched rolling executable paths")
    axes[2].set_xlabel("forward x in base t0 rig (m)")
    axes[2].set_ylabel("left y in base t0 rig (m)")
    axes[2].set_aspect("equal", adjustable="box")
    axes[2].grid(alpha=0.25)
    for axis in axes:
        axis.legend(fontsize=8)
    figure.tight_layout()
    figure.savefig(OUTPUT / "rolling-executable-summary.png", dpi=180)
    plt.close(figure)


def make_html(records: list[dict[str, object]], summary: dict[str, object]) -> None:
    rows = "".join(
        f"<tr><td>{record['prefix_offset_s']:.1f}</td><td>{record['seed']}</td>"
        f"<td>{record['actor_phase']}</td><td>{record['coc']}</td>"
        f"<td>{record['end_executable_speed_mps']:.2f}</td>"
        f"<td>{record['minimum_executable_clearance_m']:.2f}</td></tr>"
        for record in records if record["plan"].startswith("model_")
    )
    html = f"""<!doctype html><meta charset=\"utf-8\"><title>episode-02 rolling-prefix review</title>
<style>body{{font:15px sans-serif;max-width:1300px;margin:2rem auto;line-height:1.45}}img,video{{max-width:100%}}table{{border-collapse:collapse}}td,th{{border:1px solid #bbb;padding:.4rem}}</style>
<h1>episode-02 rolling-prefix executable analysis</h1>
<p><b>{summary['gate_decision']}</b></p>
<p>각 prefix에서 새로 생성한 6.4초 plan 중 첫 0.5초만 연결했습니다. 영상은 recorded human future이며 model 실행 영상이 아닙니다.</p>
<img src=\"rolling-executable-summary.png\">
<video controls src=\"../../pedestrian-delay-replication-v0/episode-02-track-18-review/episode-02-track-18-front-wide.mp4\"></video>
<table><tr><th>prefix (s)</th><th>seed</th><th>actor phase</th><th>CoC</th><th>end speed</th><th>min clearance</th></tr>{rows}</table>
"""
    (OUTPUT / "REVIEW.html").write_text(html, encoding="utf-8")


def main() -> int:
    OUTPUT.mkdir(parents=True, exist_ok=True, mode=0o700)
    manifest = json.loads((EPISODE / "seed-44/manifest.json").read_text(encoding="utf-8"))
    interface = PhysicalAIAVDatasetInterface(
        local_dir=DATA_ROOT.resolve(), revision=manifest["dataset_revision"],
        confirm_download_threshold_gb=float("inf"),
    )
    egomotion = interface.get_clip_feature(
        CLIP_ID, interface.features.LABELS.EGOMOTION, maybe_stream=True
    )
    dimensions = interface.get_clip_feature(CLIP_ID, "vehicle_dimensions", maybe_stream=True)
    base_pose = egomotion(BASE_T0_US).pose
    track = transform_track(load_track(interface), egomotion, base_pose, BASE_T0_US)
    actor_at_base = interpolate_actor(track, np.array([0.0]))
    entry_side_sign = float(np.sign(actor_at_base.center[0, 1]))
    if entry_side_sign == 0:
        raise RuntimeError("cannot infer pedestrian entry side from zero initial lateral position")

    records: list[dict[str, object]] = []
    stitched_parts: dict[str, list[np.ndarray]] = {
        "human_recorded": [], "model_seed_42": [], "model_seed_43": [], "model_seed_44": []
    }
    for offset_us in OFFSETS_US:
        prefix_us = BASE_T0_US + offset_us
        relative_pose = base_pose.inv() * egomotion(prefix_us).pose
        current_speed = float(np.linalg.norm(egomotion(prefix_us).velocity))
        actor_now = interpolate_actor(track, np.array([offset_us / 1e6]))
        phase, actor_x, actor_y = actor_phase(
            actor_now, relative_pose, dimensions, entry_side_sign
        )
        query_s = offset_us / 1e6 + np.arange(1, EXECUTABLE_STEPS + 1) * STEP_S
        actor_segment = interpolate_actor(track, query_s)

        human_local_xy, human_local_yaw = trajectory(
            run_dir(offset_us, 44) / "ground_truth_trajectory.npz", predicted=False
        )
        human_local_xy, human_local_yaw = human_local_xy[:EXECUTABLE_STEPS], human_local_yaw[:EXECUTABLE_STEPS]
        human_base_xy, human_base_yaw = to_base_frame(human_local_xy, human_local_yaw, relative_pose)
        human_clearance = signed_clearance(human_base_xy, human_base_yaw, actor_segment, dimensions)
        human_record = {
            "prefix_offset_s": offset_us / 1e6, "seed": None, "plan": "human_recorded",
            "actor_phase": phase, "actor_x_prefix_m": actor_x, "actor_y_prefix_m": actor_y,
            "coc": "RECORDED_HUMAN_TRAJECTORY", "coc_phase": "NOT_APPLICABLE",
            "minimum_executable_clearance_m": float(np.min(human_clearance)),
            **speed_metrics(human_local_xy, current_speed),
        }
        records.append(human_record)
        stitched_parts["human_recorded"].append(human_base_xy)

        for seed in SEEDS:
            directory = run_dir(offset_us, seed)
            local_xy, local_yaw = trajectory(directory / "predicted_trajectory.npz", predicted=True)
            local_xy, local_yaw = local_xy[:EXECUTABLE_STEPS], local_yaw[:EXECUTABLE_STEPS]
            base_xy, base_yaw = to_base_frame(local_xy, local_yaw, relative_pose)
            clearance = signed_clearance(base_xy, base_yaw, actor_segment, dimensions)
            coc = (directory / "generated_coc.txt").read_text(encoding="utf-8").strip()
            record = {
                "prefix_offset_s": offset_us / 1e6, "seed": seed, "plan": f"model_seed_{seed}",
                "actor_phase": phase, "actor_x_prefix_m": actor_x, "actor_y_prefix_m": actor_y,
                "coc": coc, "coc_phase": classify_coc(coc),
                "minimum_executable_clearance_m": float(np.min(clearance)),
                **speed_metrics(local_xy, current_speed),
            }
            records.append(record)
            stitched_parts[f"model_seed_{seed}"].append(base_xy)

    frame = pd.DataFrame(records)
    stitched = {name: np.vstack(parts) for name, parts in stitched_parts.items()}
    stitched_times = np.arange(1, len(next(iter(stitched.values()))) + 1) * STEP_S
    actor_stitched = interpolate_actor(track, stitched_times)
    stitched_clearance = {}
    for plan, xy in stitched.items():
        # Recover yaw from successive points for a conservative stitched-path diagnostic.
        delta = np.diff(np.vstack([np.zeros((1, 2)), xy]), axis=0)
        yaw = np.unwrap(np.arctan2(delta[:, 1], delta[:, 0]))
        clearance = signed_clearance(xy, yaw, actor_stitched, dimensions)
        stitched_clearance[plan] = {
            "minimum_m": float(np.min(clearance)),
            "overlap_candidate": bool(np.any(clearance <= 0)),
            "time_at_minimum_s": float(stitched_times[int(np.argmin(clearance))]),
        }

    model_rows = frame[frame.plan.str.startswith("model_")]
    summary = {
        "status": "ROLLING_EXECUTABLE_ANALYSIS_COMPLETE",
        "prefix_count": len(OFFSETS_US),
        "new_model_inference_count": (len(OFFSETS_US) - 1) * len(SEEDS),
        "executable_horizon_s": EXECUTABLE_STEPS * STEP_S,
        "all_model_cocs_hold_or_yield": bool((model_rows.coc_phase == "HOLD_OR_YIELD").all()),
        "model_coc_release_count": int((model_rows.coc_phase == "RELEASE_OR_PROCEED").sum()),
        "minimum_executable_clearance_by_plan_m": frame.groupby("plan").minimum_executable_clearance_m.min().to_dict(),
        "executable_overlap_count_by_plan": frame.assign(
            overlap=frame.minimum_executable_clearance_m <= 0
        ).groupby("plan").overlap.sum().astype(int).to_dict(),
        "stitched_clearance": stitched_clearance,
        "actor_phase_by_prefix": frame[frame.plan == "human_recorded"][[
            "prefix_offset_s", "actor_phase", "actor_x_prefix_m", "actor_y_prefix_m"
        ]].to_dict(orient="records"),
        "gate_decision": "NO_PREMATURE_RELEASE_OR_EXECUTABLE_OVERLAP_IN_RECORDED_ROLLING_PREFIX",
        "claim_boundary": [
            "This evaluates rolling inference on the recorded future, not the synthetic delayed future.",
            "Only the first 0.5 s of each plan is treated as executable.",
            "Yield semantics do not by themselves require a full stop.",
            "No closed-loop vehicle execution was performed.",
        ],
    }
    frame.to_csv(OUTPUT / "rolling-prefix-segments.csv", index=False)
    (OUTPUT / "result.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    make_plots(frame, stitched, actor_stitched)
    make_html(records, summary)
    for path in OUTPUT.iterdir():
        path.chmod(0o600)
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
