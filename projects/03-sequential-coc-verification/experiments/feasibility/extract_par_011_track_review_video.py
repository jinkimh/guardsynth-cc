#!/usr/bin/env python3
"""Render PAR-011 front-camera evidence with obstacle track 122 highlighted."""

from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path

import av
import numpy as np
import pandas as pd
import physical_ai_av
from PIL import Image, ImageDraw, ImageFont
from scipy.spatial.transform import Rotation


ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "PROJECT_REGISTRY.json").is_file())
BATCH = ROOT / "artifacts/results/restricted/alp-exp-005/feasibility-batch-v0"
RUN = BATCH / "episode-05/seed-44"
OUTPUT = BATCH / "safety-acceleration-focus-v1/par-011-counterfactual-fragility-v0"
TRACK_ID = "122"
FPS = 10
START_S = 0.0
END_S = 6.4
VIDEO_SIZE = (1280, 720)
BOX_EDGES = (
    (0, 1), (1, 2), (2, 3), (3, 0), (4, 5), (5, 6), (6, 7), (7, 4),
    (0, 4), (1, 5), (2, 6), (3, 7),
)


def load_track(interface: object, clip_id: str) -> pd.DataFrame:
    feature = interface.features.LABELS.OBSTACLE_OFFLINE
    chunk = int(interface.get_clip_chunk(clip_id))
    archive_path = interface.features.get_chunk_feature_filename(chunk, feature)
    member = interface.features.get_clip_files_in_zip(clip_id, feature)[feature]
    with interface.open_file(archive_path, maybe_stream=True) as source:
        with zipfile.ZipFile(source) as archive:
            data = pd.read_parquet(io.BytesIO(archive.read(member)))
    return data[data.track_id.astype(str) == TRACK_ID].sort_values("timestamp_us").copy()


def box_corners(row: pd.Series) -> np.ndarray:
    half = row[["size_x", "size_y", "size_z"]].to_numpy(dtype=float) / 2
    signs = np.array([
        [-1, -1, -1], [-1, 1, -1], [1, 1, -1], [1, -1, -1],
        [-1, -1, 1], [-1, 1, 1], [1, 1, 1], [1, -1, 1],
    ])
    local = signs * half
    quaternion = row[["orientation_x", "orientation_y", "orientation_z", "orientation_w"]].to_numpy(dtype=float)
    center = row[["center_x", "center_y", "center_z"]].to_numpy(dtype=float)
    return Rotation.from_quat(quaternion).apply(local) + center


def project_track_box(
    row: pd.Series,
    frame_timestamp_us: int,
    egomotion: object,
    camera_pose: object,
    camera_model: object,
) -> np.ndarray | None:
    reference_us = int(row.reference_frame_timestamp_us)
    corners_reference = box_corners(row)
    corners_anchor = egomotion(reference_us).pose.apply(corners_reference)
    corners_rig = egomotion(frame_timestamp_us).pose.inv().apply(corners_anchor)
    corners_camera = camera_pose.inv().apply(corners_rig)
    if np.any(corners_camera[:, 2] <= 0):
        return None
    pixels = camera_model.ray2pixel(corners_camera)
    if not np.all(np.isfinite(pixels)):
        return None
    return pixels


def annotate(image_array: np.ndarray, pixels: np.ndarray | None, relative_s: float) -> Image.Image:
    raw_height, raw_width = image_array.shape[:2]
    image = Image.fromarray(image_array).resize(VIDEO_SIZE, Image.Resampling.LANCZOS)
    draw = ImageDraw.Draw(image, "RGBA")
    font = ImageFont.load_default(size=24)
    scale = np.array([VIDEO_SIZE[0] / raw_width, VIDEO_SIZE[1] / raw_height])
    draw.rectangle((0, 0, VIDEO_SIZE[0], 92), fill=(0, 0, 0, 205))
    draw.text((16, 10), f"PAR-011 | recorded future | t={relative_s:.1f}s", fill="white", font=font)
    draw.text((16, 48), "MAGENTA = obstacle.offline person track 122", fill=(255, 80, 255), font=font)
    if pixels is not None:
        scaled = pixels * scale
        for start, end in BOX_EDGES:
            draw.line((*scaled[start], *scaled[end]), fill=(255, 0, 255, 255), width=5)
        anchor = scaled[np.argmin(scaled[:, 1])]
        draw.text((float(anchor[0] + 8), float(max(96, anchor[1] - 28))), "track 122", fill=(255, 0, 255), font=font)
    else:
        draw.text((900, 48), "track not projectable", fill=(255, 190, 190), font=font)
    return image


def encode(images: list[Image.Image], output: Path) -> None:
    container = av.open(str(output), mode="w")
    stream = container.add_stream("libx264", rate=FPS)
    stream.width, stream.height = VIDEO_SIZE
    stream.pix_fmt = "yuv420p"
    stream.options = {"crf": "20", "preset": "medium"}
    try:
        for image in images:
            frame = av.VideoFrame.from_image(image)
            for packet in stream.encode(frame):
                container.mux(packet)
        for packet in stream.encode():
            container.mux(packet)
    finally:
        container.close()


def contact_sheet(images: list[Image.Image], output: Path) -> None:
    indices = np.linspace(0, len(images) - 1, 10).round().astype(int)
    cell = (640, 360)
    sheet = Image.new("RGB", (cell[0] * 5, cell[1] * 2), "white")
    for slot, index in enumerate(indices):
        row, column = divmod(slot, 5)
        sheet.paste(images[index].resize(cell, Image.Resampling.LANCZOS), (column * cell[0], row * cell[1]))
    sheet.save(output, quality=91)


def main() -> int:
    manifest = json.loads((RUN / "manifest.json").read_text(encoding="utf-8"))
    interface = physical_ai_av.PhysicalAIAVDatasetInterface(revision=manifest["dataset_revision"])
    clip_id, t0_us = manifest["clip_id"], int(manifest["t0_us"])
    camera_id = interface.features.CAMERA.CAMERA_FRONT_WIDE_120FOV
    camera = interface.get_clip_feature(clip_id, camera_id, maybe_stream=True)
    egomotion = interface.get_clip_feature(clip_id, interface.features.LABELS.EGOMOTION, maybe_stream=True)
    extrinsics = interface.get_clip_feature(clip_id, "sensor_extrinsics", maybe_stream=True)
    intrinsics = interface.get_clip_feature(clip_id, "camera_intrinsics", maybe_stream=True)
    track = load_track(interface, clip_id)

    requested = t0_us + np.arange(int(START_S * 1e6), int(END_S * 1e6) + 1, int(1e6 / FPS), dtype=np.int64)
    frames, actual = camera.decode_images_from_timestamps(requested)
    images: list[Image.Image] = []
    projected = 0
    for image_array, timestamp in zip(frames, actual, strict=True):
        index = int(np.argmin(np.abs(track.timestamp_us.to_numpy(dtype=np.int64) - timestamp)))
        row = track.iloc[index]
        pixels = None
        if abs(int(row.timestamp_us) - int(timestamp)) <= 100_000:
            pixels = project_track_box(row, int(timestamp), egomotion, extrinsics.sensor_poses[camera_id], intrinsics.camera_models[camera_id])
        projected += pixels is not None
        images.append(annotate(image_array, pixels, (int(timestamp) - t0_us) / 1e6))

    OUTPUT.mkdir(parents=True, exist_ok=True, mode=0o700)
    video_path = OUTPUT / "PAR-011-track-122-front-wide.mp4"
    sheet_path = OUTPUT / "PAR-011-track-122-contact-sheet.jpg"
    encode(images, video_path)
    contact_sheet(images, sheet_path)
    report = {"track_id": TRACK_ID, "frame_count": len(images), "projected_frame_count": projected,
              "max_timestamp_error_us": int(np.max(np.abs(actual - requested))),
              "warning": "Recorded human future; not execution of any model trajectory."}
    (OUTPUT / "track-review-manifest.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    for path in (video_path, sheet_path, OUTPUT / "track-review-manifest.json"):
        path.chmod(0o600)
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
