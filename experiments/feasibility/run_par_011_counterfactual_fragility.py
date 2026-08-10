#!/usr/bin/env python3
"""Minimal PAR-011 test: pedestrian-delay fragility of human/model plans.

This is a candidate feasibility analysis, not a collision-probability estimate.
Obstacle tracks are converted from their timestamped rig frames into the planning
frame at t0.  A counterfactual delay holds each pedestrian at its t0 position
and then replays the recorded track after the requested delay.
"""

from __future__ import annotations

import argparse
import io
import json
import math
import os
import zipfile
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from physical_ai_av import PhysicalAIAVDatasetInterface

os.environ.setdefault("MPLCONFIGDIR", "/tmp/coc-matplotlib")
import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parents[2]
BATCH = ROOT / "artifacts/results/restricted/alp-exp-005/feasibility-batch-v0"
RUN_ROOT = BATCH / "episode-05"
DEFAULT_OUTPUT = BATCH / "safety-acceleration-focus-v1/par-011-counterfactual-fragility-v0"
CLIP_ID = "d50948f9-0017-4847-a280-1bed65d706b0"
T0_US = 8_506_674
DATASET_REVISION = "b719eea7f0a63619ef51ec7f54178af0937ef050"
TIMES_S = np.arange(1, 65, dtype=float) / 10.0
DELAYS_S = np.arange(0, 21, dtype=float) / 10.0
MARGINS_M = (0.0, 0.25, 0.5)


@dataclass(frozen=True)
class VehicleGeometry:
    length: float
    width: float
    rear_axle_to_center: float


def load_obstacles(interface: PhysicalAIAVDatasetInterface) -> pd.DataFrame:
    feature = interface.features.LABELS.OBSTACLE_OFFLINE
    chunk = int(interface.get_clip_chunk(CLIP_ID))
    filename = interface.features.get_chunk_feature_filename(chunk, feature)
    member = interface.features.get_clip_files_in_zip(CLIP_ID, feature)[feature]
    with interface.open_file(filename, maybe_stream=True) as source:
        with zipfile.ZipFile(source) as archive:
            raw = archive.read(member)
    frame = pd.read_parquet(io.BytesIO(raw)).copy()
    frame["timestamp_us"] = frame["timestamp_us"].astype("int64")
    return frame


def plan_from_npz(path: Path, key: str) -> tuple[np.ndarray, np.ndarray]:
    data = np.load(path)
    xyz = np.asarray(data[key]).reshape(-1, 64, 3)[0]
    rot_key = "gt_rot" if key == "gt_xyz" else "pred_rot"
    rotations = np.asarray(data[rot_key]).reshape(-1, 64, 3, 3)[0]
    yaw = np.arctan2(rotations[:, 1, 0], rotations[:, 0, 0])
    return xyz[:, :2], yaw


def transform_track_to_t0(
    track: pd.DataFrame, egomotion: object, pose0: object
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    times = track["reference_frame_timestamp_us"].to_numpy(dtype=np.int64)
    local = track[["center_x", "center_y", "center_z"]].to_numpy(dtype=float)
    points = np.empty_like(local)
    for index, (timestamp, point) in enumerate(zip(times, local, strict=True)):
        points[index] = (pose0.inv() * egomotion(int(timestamp)).pose).apply(point)
    sizes = track[["size_x", "size_y"]].to_numpy(dtype=float)
    radius = np.nanmax(sizes, axis=1) / 2.0
    return times, points[:, :2], radius


def interpolate_track(
    times_us: np.ndarray,
    points: np.ndarray,
    radius: np.ndarray,
    query_s: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    relative_s = (times_us - T0_US) / 1e6
    result = np.column_stack(
        [np.interp(query_s, relative_s, points[:, axis]) for axis in range(2)]
    )
    radii = np.interp(query_s, relative_s, radius)
    return result, radii


def signed_clearance_to_ego(
    plan_xy: np.ndarray,
    plan_yaw: np.ndarray,
    pedestrian_xy: np.ndarray,
    pedestrian_radius: np.ndarray,
    geometry: VehicleGeometry,
    margin_m: float,
) -> np.ndarray:
    delta = pedestrian_xy - plan_xy
    cosine, sine = np.cos(plan_yaw), np.sin(plan_yaw)
    local_x = cosine * delta[:, 0] + sine * delta[:, 1]
    local_y = -sine * delta[:, 0] + cosine * delta[:, 1]
    qx = np.abs(local_x - geometry.rear_axle_to_center) - geometry.length / 2
    qy = np.abs(local_y) - geometry.width / 2
    outside = np.hypot(np.maximum(qx, 0), np.maximum(qy, 0))
    inside = np.minimum(np.maximum(qx, qy), 0)
    return outside + inside - pedestrian_radius - margin_m


def candidate_tracks(
    obstacles: pd.DataFrame, egomotion: object, pose0: object
) -> dict[str, dict[str, np.ndarray]]:
    people = obstacles[obstacles["label_class"].astype(str).str.lower() == "person"].copy()
    people = people.sort_values(["track_id", "timestamp_us"])
    output: dict[str, dict[str, np.ndarray]] = {}
    for track_id, track in people.groupby("track_id", sort=True):
        reference_times = track["reference_frame_timestamp_us"].to_numpy(dtype=np.int64)
        if reference_times.min() > T0_US or reference_times.max() < T0_US + int(TIMES_S[-1] * 1e6):
            continue
        times, points, radius = transform_track_to_t0(track, egomotion, pose0)
        baseline, baseline_radius = interpolate_track(times, points, radius, TIMES_S)
        # Retain only pedestrians that approach the union of the two plan corridors.
        if np.min(np.abs(baseline[:, 1])) > 8.0 or np.min(baseline[:, 0]) > 25.0:
            continue
        output[str(track_id)] = {
            "times_us": times,
            "points": points,
            "radius": radius,
            "baseline": baseline,
            "baseline_radius": baseline_radius,
        }
    return output


def analyze_plan(
    name: str,
    plan_xy: np.ndarray,
    plan_yaw: np.ndarray,
    tracks: dict[str, dict[str, np.ndarray]],
    geometry: VehicleGeometry,
) -> tuple[list[dict[str, object]], dict[tuple[float, float], dict[str, object]]]:
    rows: list[dict[str, object]] = []
    details: dict[tuple[float, float], dict[str, object]] = {}
    for delay_s in DELAYS_S:
        query_s = np.maximum(0.0, TIMES_S - delay_s)
        for margin_m in MARGINS_M:
            worst: dict[str, object] | None = None
            for track_id, track in tracks.items():
                pedestrian_xy, radius = interpolate_track(
                    track["times_us"], track["points"], track["radius"], query_s
                )
                clearance = signed_clearance_to_ego(
                    plan_xy, plan_yaw, pedestrian_xy, radius, geometry, margin_m
                )
                index = int(np.argmin(clearance))
                item = {
                    "track_id": track_id,
                    "index": index,
                    "time_s": float(TIMES_S[index]),
                    "clearance_m": float(clearance[index]),
                    "pedestrian_xy": pedestrian_xy,
                    "clearance_series": clearance,
                }
                if worst is None or item["clearance_m"] < worst["clearance_m"]:
                    worst = item
            assert worst is not None
            row = {
                "plan": name,
                "delay_s": float(delay_s),
                "margin_m": float(margin_m),
                "minimum_signed_clearance_m": round(float(worst["clearance_m"]), 6),
                "overlap_candidate": bool(worst["clearance_m"] <= 0),
                "worst_track_id": worst["track_id"],
                "worst_time_s": worst["time_s"],
            }
            rows.append(row)
            details[(float(delay_s), float(margin_m))] = worst
    return rows, details


def plot_bev(
    output: Path,
    plans: dict[str, tuple[np.ndarray, np.ndarray]],
    rows: pd.DataFrame,
    details: dict[str, dict[tuple[float, float], dict[str, object]]],
) -> None:
    figure, axes = plt.subplots(1, len(plans), figsize=(16, 5.5), sharex=True, sharey=True)
    colors = {"human_recorded": "#333333", "model_seed_42": "#1565c0", "model_seed_43": "#ef6c00", "model_seed_44": "#c62828"}
    for axis, (name, (plan_xy, _)) in zip(axes, plans.items(), strict=True):
        subset = rows[(rows.plan == name) & (rows.margin_m == 0.25)]
        failures = subset[subset.overlap_candidate]
        chosen = failures.iloc[0] if not failures.empty else subset.sort_values("minimum_signed_clearance_m").iloc[0]
        delay = float(chosen.delay_s)
        detail = details[name][(delay, 0.25)]
        pedestrian = detail["pedestrian_xy"]
        index = int(detail["index"])
        axis.plot(plan_xy[:, 0], plan_xy[:, 1], color=colors[name], linewidth=2.5, label="ego plan")
        axis.plot(pedestrian[:, 0], pedestrian[:, 1], color="#7b1fa2", linewidth=2, marker=".", label=f"person {detail['track_id']}")
        axis.scatter(plan_xy[index, 0], plan_xy[index, 1], s=80, color=colors[name], edgecolor="white", zorder=4)
        axis.scatter(pedestrian[index, 0], pedestrian[index, 1], s=80, color="#7b1fa2", edgecolor="white", zorder=4)
        axis.set_title(f"{name}\ndelay={delay:.1f}s, min={detail['clearance_m']:.2f}m")
        axis.set_aspect("equal", adjustable="box")
        axis.grid(alpha=0.25)
        axis.set_xlabel("forward x in t0 rig (m)")
    axes[0].set_ylabel("left y in t0 rig (m)")
    axes[0].legend(loc="best", fontsize=8)
    figure.suptitle("PAR-011 candidate pedestrian-delay fragility (0.25 m added margin)")
    figure.tight_layout()
    figure.savefig(output, dpi=180)
    plt.close(figure)


def make_review_html(output: Path, summary: dict[str, object]) -> None:
    records = "".join(
        f"<tr><td>{item['plan']}</td><td>{item['first_overlap_delay_s']}</td>"
        f"<td>{item['worst_track_id']}</td><td>{item['minimum_clearance_m']}</td></tr>"
        for item in summary["margin_0.25m_summary"]
    )
    contrasts = "".join(
        f"<tr><td>{item['model_plan']}</td><td>{item['same_track_id']}</td>"
        f"<td>{item['same_delay_s']}</td><td>{item['human_minimum_clearance_m']}</td>"
        f"<td>{item['model_minimum_clearance_m']}</td>"
        f"<td>{item['model_excess_clearance_loss_m']}</td></tr>"
        for item in summary["paired_same_counterfactual_contrasts"]
    )
    html = f"""<!doctype html><meta charset=\"utf-8\"><title>PAR-011 minimal review</title>
<style>body{{font:16px sans-serif;max-width:1200px;margin:2rem auto;line-height:1.5}} video,img{{max-width:100%}} table{{border-collapse:collapse}}td,th{{border:1px solid #bbb;padding:.5rem}}</style>
<h1>PAR-011 최소 반사실 취약성 검토</h1>
<p><b>candidate 결과입니다. 사고 확률이나 실제 모델 실행 결과가 아닙니다.</b></p>
<p>질문 1: 아래 worst-risk track이 영상의 횡단 보행자와 일치하는가? 질문 2: 보행자가 0–2초 멈췄다가 기록된 움직임을 이어가는 변화가 물리적으로 상식적인가?</p>
<video controls src=\"PAR-011-track-122-front-wide.mp4\"></video>
<p>자홍색 상자가 자동 선택된 worst-risk pedestrian track 122입니다.</p>
<img src=\"PAR-011-counterfactual-BEV.png\" alt=\"counterfactual BEV\">
<table><tr><th>plan</th><th>first overlap delay (s)</th><th>worst track</th><th>minimum clearance (m)</th></tr>{records}</table>
<h2>동일 반사실에서 human–model 대응 비교</h2>
<table><tr><th>model</th><th>track</th><th>delay (s)</th><th>human clearance (m)</th><th>model clearance (m)</th><th>model excess loss (m)</th></tr>{contrasts}</table>
<p>주의: 영상은 기록된 human future이며 model plan을 실행한 영상이 아닙니다. 다른 행위자의 반응도 재시뮬레이션하지 않았습니다.</p>"""
    output.write_text(html, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--data-root", type=Path, default=ROOT / "data/restricted/nvidia_physicalai")
    args = parser.parse_args()
    interface = PhysicalAIAVDatasetInterface(
        local_dir=args.data_root.resolve(), revision=DATASET_REVISION,
        confirm_download_threshold_gb=float("inf")
    )
    egomotion = interface.get_clip_feature(CLIP_ID, interface.features.LABELS.EGOMOTION, maybe_stream=True)
    pose0 = egomotion(T0_US).pose
    obstacles = load_obstacles(interface)
    dimensions = interface.get_clip_feature(CLIP_ID, "vehicle_dimensions", maybe_stream=True)
    geometry = VehicleGeometry(float(dimensions.length), float(dimensions.width), float(dimensions.rear_axle_to_bbox_center))

    human_xy, human_yaw = plan_from_npz(RUN_ROOT / "seed-44/ground_truth_trajectory.npz", "gt_xyz")
    plans: dict[str, tuple[np.ndarray, np.ndarray]] = {"human_recorded": (human_xy, human_yaw)}
    for seed in (42, 43, 44):
        plans[f"model_seed_{seed}"] = plan_from_npz(RUN_ROOT / f"seed-{seed}/predicted_trajectory.npz", "pred_xyz")

    # Independent coordinate check: dataset egomotion must reconstruct the saved human path.
    reconstructed = np.stack([(pose0.inv() * egomotion(T0_US + int(t * 1e6)).pose).translation[:2] for t in TIMES_S])
    coordinate_rmse = np.sqrt(np.mean((reconstructed - human_xy) ** 2, axis=0))
    if float(np.max(coordinate_rmse)) > 1e-4:
        raise RuntimeError(f"coordinate validation failed: {coordinate_rmse}")

    tracks = candidate_tracks(obstacles, egomotion, pose0)
    if not tracks:
        raise RuntimeError("no full-horizon pedestrian tracks passed the broad spatial filter")
    all_rows: list[dict[str, object]] = []
    all_details: dict[str, dict[tuple[float, float], dict[str, object]]] = {}
    for name, (xy, yaw) in plans.items():
        rows, detail = analyze_plan(name, xy, yaw, tracks, geometry)
        all_rows.extend(rows)
        all_details[name] = detail
    frame = pd.DataFrame(all_rows)

    args.output.mkdir(parents=True, exist_ok=True, mode=0o700)
    csv_path = args.output / "clearance_grid.csv"
    frame.to_csv(csv_path, index=False)
    summary_rows = []
    for name in plans:
        subset = frame[(frame.plan == name) & (frame.margin_m == 0.25)]
        overlaps = subset[subset.overlap_candidate]
        first = None if overlaps.empty else float(overlaps.iloc[0].delay_s)
        worst = subset.sort_values("minimum_signed_clearance_m").iloc[0]
        summary_rows.append({
            "plan": name,
            "first_overlap_delay_s": first,
            "worst_track_id": str(worst.worst_track_id),
            "minimum_clearance_m": float(worst.minimum_signed_clearance_m),
            "worst_delay_s": float(worst.delay_s),
            "worst_time_s": float(worst.worst_time_s),
        })
    paired_contrasts = []
    human_plan_xy, human_plan_yaw = plans["human_recorded"]
    for model_name in ("model_seed_42", "model_seed_43", "model_seed_44"):
        subset = frame[(frame.plan == model_name) & (frame.margin_m == 0.25)]
        model_worst = subset.sort_values("minimum_signed_clearance_m").iloc[0]
        delay_s = float(model_worst.delay_s)
        track_id = str(model_worst.worst_track_id)
        track = tracks[track_id]
        pedestrian_xy, radius = interpolate_track(
            track["times_us"], track["points"], track["radius"],
            np.maximum(0.0, TIMES_S - delay_s),
        )
        human_clearance = signed_clearance_to_ego(
            human_plan_xy, human_plan_yaw, pedestrian_xy, radius, geometry, 0.25
        )
        human_minimum = float(np.min(human_clearance))
        model_minimum = float(model_worst.minimum_signed_clearance_m)
        paired_contrasts.append({
            "model_plan": model_name,
            "same_track_id": track_id,
            "same_delay_s": delay_s,
            "human_minimum_clearance_m": round(human_minimum, 6),
            "model_minimum_clearance_m": round(model_minimum, 6),
            "model_excess_clearance_loss_m": round(human_minimum - model_minimum, 6),
        })
    summary = {
        "status": "ENGINEERING_CANDIDATE_REQUIRES_HUMAN_TRACK_AND_PLAUSIBILITY_CHECK",
        "question": "Does a small plausible pedestrian delay expose more fragility in model plans than in the recorded human plan?",
        "clip_id": CLIP_ID,
        "t0_us": T0_US,
        "coordinate_validation_rmse_m": coordinate_rmse.tolist(),
        "candidate_track_ids": sorted(tracks),
        "delay_grid_s": [float(DELAYS_S[0]), float(DELAYS_S[-1]), 0.1],
        "margins_m": list(MARGINS_M),
        "margin_0.25m_summary": summary_rows,
        "paired_same_counterfactual_contrasts": paired_contrasts,
        "candidate_interpretation": (
            "A positive model_excess_clearance_loss_m means that the model plan leaves less "
            "geometric buffer than the recorded human plan under exactly the same delayed track. "
            "It is not by itself an unsafe-control verdict."
        ),
        "limitations": [
            "The delayed pedestrian future is a deterministic stress test, not a calibrated probability model.",
            "Other agents do not react to the counterfactual ego plan.",
            "Obstacle-track identity and delay plausibility require one human review.",
            "Signed geometric overlap is not equivalent to a crash or a safety-rate estimate.",
        ],
    }
    (args.output / "result.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    plot_bev(args.output / "PAR-011-counterfactual-BEV.png", plans, frame, all_details)
    make_review_html(args.output / "REVIEW.html", summary)
    for path in args.output.iterdir():
        path.chmod(0o600)
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
