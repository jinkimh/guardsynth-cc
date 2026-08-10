#!/usr/bin/env python3
"""Create targeted review media for episode-02 pedestrian track 18."""

from __future__ import annotations

import io
import json
import os
import zipfile
from pathlib import Path

import av
import numpy as np
import pandas as pd
import physical_ai_av
from PIL import Image, ImageDraw, ImageFont

os.environ.setdefault("MPLCONFIGDIR", "/tmp/coc-matplotlib")
import matplotlib.pyplot as plt

from extract_par_011_track_review_video import BOX_EDGES, VIDEO_SIZE, box_corners, encode
from run_multiscene_future_delay_screen import (
    BATCH,
    TIMES_S,
    clearance_series,
    interpolate_actor,
    plan_from_npz,
    transform_track,
)


EPISODE = BATCH / "episode-02"
OUTPUT = BATCH / "pedestrian-delay-replication-v0/episode-02-track-18-review"
TRACK_ID = "18"
DELAY_S = 2.0
FPS = 10


def load_track(interface: object, clip_id: str) -> pd.DataFrame:
    feature = interface.features.LABELS.OBSTACLE_OFFLINE
    chunk = int(interface.get_clip_chunk(clip_id))
    archive_path = interface.features.get_chunk_feature_filename(chunk, feature)
    member = interface.features.get_clip_files_in_zip(clip_id, feature)[feature]
    with interface.open_file(archive_path, maybe_stream=True) as source:
        with zipfile.ZipFile(source) as archive:
            data = pd.read_parquet(io.BytesIO(archive.read(member)))
    return data[data.track_id.astype(str) == TRACK_ID].sort_values("timestamp_us").copy()


def project_box(row: pd.Series, frame_us: int, egomotion: object, camera_pose: object, camera_model: object) -> np.ndarray | None:
    reference_us = int(row.reference_frame_timestamp_us)
    corners_anchor = egomotion(reference_us).pose.apply(box_corners(row))
    corners_rig = egomotion(frame_us).pose.inv().apply(corners_anchor)
    corners_camera = camera_pose.inv().apply(corners_rig)
    if np.any(corners_camera[:, 2] <= 0):
        return None
    pixels = camera_model.ray2pixel(corners_camera)
    return pixels if np.all(np.isfinite(pixels)) else None


def annotate(array: np.ndarray, pixels: np.ndarray | None, relative_s: float) -> Image.Image:
    raw_height, raw_width = array.shape[:2]
    image = Image.fromarray(array).resize(VIDEO_SIZE, Image.Resampling.LANCZOS)
    draw = ImageDraw.Draw(image, "RGBA")
    font = ImageFont.load_default(size=24)
    scale = np.array([VIDEO_SIZE[0] / raw_width, VIDEO_SIZE[1] / raw_height])
    draw.rectangle((0, 0, VIDEO_SIZE[0], 94), fill=(0, 0, 0, 210))
    draw.text((16, 10), f"episode-02 | recorded future | t={relative_s:.1f}s", fill="white", font=font)
    draw.text((16, 50), "MAGENTA = obstacle.offline person track 18", fill=(255, 60, 255), font=font)
    if pixels is not None:
        scaled = pixels * scale
        for start, end in BOX_EDGES:
            draw.line((*scaled[start], *scaled[end]), fill=(255, 0, 255, 255), width=5)
        anchor = scaled[np.argmin(scaled[:, 1])]
        draw.text((float(anchor[0] + 6), float(max(98, anchor[1] - 28))), "track 18", fill=(255, 0, 255), font=font)
    return image


def contact_sheet(images: list[Image.Image], output: Path) -> None:
    indices = np.linspace(0, len(images) - 1, 10).round().astype(int)
    cell = (640, 360)
    sheet = Image.new("RGB", (cell[0] * 5, cell[1] * 2), "white")
    for slot, index in enumerate(indices):
        row, column = divmod(slot, 5)
        sheet.paste(images[index].resize(cell, Image.Resampling.LANCZOS), (column * cell[0], row * cell[1]))
    sheet.save(output, quality=91)


def plot_bev(
    output: Path, track_state: dict[str, np.ndarray | str], plans: dict[str, tuple[np.ndarray, np.ndarray]], dimensions: object
) -> list[dict[str, object]]:
    actor = interpolate_actor(track_state, np.maximum(0.0, TIMES_S - DELAY_S))
    colors = {"human_recorded": "#222222", "model_seed_42": "#1565c0", "model_seed_43": "#ef6c00", "model_seed_44": "#c62828"}
    figure, axis = plt.subplots(figsize=(9, 7))
    axis.plot(actor.center[:, 0], actor.center[:, 1], color="#8e24aa", linewidth=3, marker=".", label="person 18, delayed 2.0 s")
    records = []
    for name, (xy, yaw) in plans.items():
        clearance = clearance_series(
            xy, yaw, actor, float(dimensions.length), float(dimensions.width),
            float(dimensions.rear_axle_to_bbox_center),
        )
        index = int(np.argmin(clearance))
        records.append({"plan": name, "minimum_clearance_m": float(clearance[index]), "worst_time_s": float(TIMES_S[index])})
        axis.plot(xy[:, 0], xy[:, 1], color=colors[name], linewidth=2.2, label=f"{name}: min {clearance[index]:.2f} m")
        axis.scatter(xy[index, 0], xy[index, 1], color=colors[name], s=70, edgecolor="white", zorder=5)
    axis.set_title("episode-02 | same pedestrian future for human and model plans")
    axis.set_xlabel("forward x in t0 rig (m)")
    axis.set_ylabel("left y in t0 rig (m)")
    axis.set_aspect("equal", adjustable="box")
    axis.grid(alpha=0.25)
    axis.legend(fontsize=8)
    figure.tight_layout()
    figure.savefig(output, dpi=180)
    plt.close(figure)
    return records


def review_html(output: Path) -> None:
    output.write_text("""<!doctype html><meta charset="utf-8"><title>episode-02 track 18 review</title>
<style>body{font:16px sans-serif;max-width:1200px;margin:2rem auto;line-height:1.5}video,img{max-width:100%}</style>
<h1>episode-02 보행자 지연 직접 반복 검토</h1>
<p><b>이것은 recorded future를 사용한 candidate stress test이며 model trajectory 실행 영상이 아닙니다.</b></p>
<ol><li>자홍색 track 18이 CoC가 지칭하는 횡단보도 보행자 중 하나인가?</li><li>이 보행자가 현재 위치/진행 과정에서 2초 더 늦게 횡단하는 미래가 충분히 가능한가?</li></ol>
<video controls src="episode-02-track-18-front-wide.mp4"></video>
<img src="episode-02-track-18-delay-2s-BEV.png" alt="BEV comparison">
<p>두 답이 모두 예인 경우: human trajectory도 이 가능한 미래에서는 중첩 후보이므로 human demonstration fragility 사례가 된다. 사고나 closed-loop 충돌을 뜻하지는 않는다.</p>
""", encoding="utf-8")


def main() -> int:
    manifest = json.loads((EPISODE / "seed-44/manifest.json").read_text(encoding="utf-8"))
    clip_id, t0_us = manifest["clip_id"], int(manifest["t0_us"])
    interface = physical_ai_av.PhysicalAIAVDatasetInterface(revision=manifest["dataset_revision"])
    camera_id = interface.features.CAMERA.CAMERA_FRONT_WIDE_120FOV
    camera = interface.get_clip_feature(clip_id, camera_id, maybe_stream=True)
    egomotion = interface.get_clip_feature(clip_id, interface.features.LABELS.EGOMOTION, maybe_stream=True)
    extrinsics = interface.get_clip_feature(clip_id, "sensor_extrinsics", maybe_stream=True)
    intrinsics = interface.get_clip_feature(clip_id, "camera_intrinsics", maybe_stream=True)
    dimensions = interface.get_clip_feature(clip_id, "vehicle_dimensions", maybe_stream=True)
    track = load_track(interface, clip_id)

    requested = t0_us + np.arange(0, 6_400_001, int(1e6 / FPS), dtype=np.int64)
    frames, actual = camera.decode_images_from_timestamps(requested)
    images = []
    projected = 0
    for array, timestamp in zip(frames, actual, strict=True):
        index = int(np.argmin(np.abs(track.timestamp_us.to_numpy(dtype=np.int64) - timestamp)))
        row = track.iloc[index]
        pixels = None
        if abs(int(row.timestamp_us) - int(timestamp)) <= 100_000:
            pixels = project_box(row, int(timestamp), egomotion, extrinsics.sensor_poses[camera_id], intrinsics.camera_models[camera_id])
        projected += pixels is not None
        images.append(annotate(array, pixels, (int(timestamp) - t0_us) / 1e6))

    OUTPUT.mkdir(parents=True, exist_ok=True, mode=0o700)
    video = OUTPUT / "episode-02-track-18-front-wide.mp4"
    sheet = OUTPUT / "episode-02-track-18-contact-sheet.jpg"
    bev = OUTPUT / "episode-02-track-18-delay-2s-BEV.png"
    encode(images, video)
    contact_sheet(images, sheet)
    track_state = transform_track(track, egomotion, egomotion(t0_us).pose, t0_us)
    plans = {"human_recorded": plan_from_npz(EPISODE / "seed-44/ground_truth_trajectory.npz", "gt_xyz")}
    for seed in (42, 43, 44):
        plans[f"model_seed_{seed}"] = plan_from_npz(EPISODE / f"seed-{seed}/predicted_trajectory.npz", "pred_xyz")
    plan_records = plot_bev(bev, track_state, plans, dimensions)
    review_html(OUTPUT / "REVIEW.html")
    report = {"episode": "episode-02", "track_id": TRACK_ID, "delay_s": DELAY_S,
              "frame_count": len(images), "projected_frame_count": projected,
              "plan_records": plan_records,
              "warning": "Recorded human future; not execution of model trajectories."}
    (OUTPUT / "media-manifest.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    for path in OUTPUT.iterdir():
        path.chmod(0o600)
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
