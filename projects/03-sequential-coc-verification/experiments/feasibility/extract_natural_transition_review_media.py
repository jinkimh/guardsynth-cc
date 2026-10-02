#!/usr/bin/env python3
"""Render episode-00 actors relevant to the natural HOLD -> RELEASE audit."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import physical_ai_av
from PIL import Image, ImageDraw, ImageFont

from extract_par_011_track_review_video import (
    BOX_EDGES,
    VIDEO_SIZE,
    box_corners,
    contact_sheet,
    encode,
)
from run_multiscene_future_delay_screen import BATCH, DATA_ROOT, load_obstacles


EPISODE = BATCH / "episode-00/seed-44"
ANALYSIS = BATCH / "episode-00-natural-transition-rolling-v0/analysis-v0"
OUTPUT = ANALYSIS / "grounding-review"
FPS = 10
END_S = 4.5
HUMAN_RELEASE_S = 3.0

# The closest stationary tracks expose why pure nearest-track selection is not
# semantic grounding.  Moving person/rider tracks cover both sides of the
# intersection and the agents named by the model CoCs.
TRACKS = {
    "84": ("person", (0, 220, 255), "closest/stationary"),
    "90": ("person", (0, 220, 255), "closest/stationary"),
    "102": ("rider", (255, 220, 0), "moving rider"),
    "133": ("rider", (255, 150, 0), "moving rider"),
    "132": ("person", (255, 0, 255), "moving person"),
    "138": ("person", (255, 0, 180), "moving person"),
    "150": ("person", (210, 0, 255), "moving person"),
    "91": ("person", (0, 255, 100), "moving person"),
    "99": ("person", (0, 220, 80), "moving person"),
    "113": ("person", (0, 180, 80), "moving person"),
    "126": ("person", (50, 255, 120), "moving person"),
}


def project_box(
    row: object,
    frame_us: int,
    egomotion: object,
    camera_pose: object,
    camera_model: object,
) -> np.ndarray | None:
    reference_us = int(row.reference_frame_timestamp_us)
    corners_anchor = egomotion(reference_us).pose.apply(box_corners(row))
    corners_rig = egomotion(frame_us).pose.inv().apply(corners_anchor)
    corners_camera = camera_pose.inv().apply(corners_rig)
    if np.any(corners_camera[:, 2] <= 0):
        return None
    pixels = camera_model.ray2pixel(corners_camera)
    return pixels if np.all(np.isfinite(pixels)) else None


def annotate(
    array: np.ndarray,
    projected: list[tuple[str, tuple[int, int, int], np.ndarray]],
    relative_s: float,
) -> Image.Image:
    raw_height, raw_width = array.shape[:2]
    image = Image.fromarray(array).resize(VIDEO_SIZE, Image.Resampling.LANCZOS)
    draw = ImageDraw.Draw(image, "RGBA")
    font = ImageFont.load_default(size=22)
    scale = np.array([VIDEO_SIZE[0] / raw_width, VIDEO_SIZE[1] / raw_height])
    phase = "human CoC: HOLD" if relative_s < HUMAN_RELEASE_S else "human CoC: RELEASE"
    draw.rectangle((0, 0, VIDEO_SIZE[0], 100), fill=(0, 0, 0, 210))
    draw.text((14, 8), f"episode-00 recorded future | t={relative_s:.1f}s | {phase}", fill="white", font=font)
    draw.text(
        (14, 45),
        "CYAN closest stationary | YELLOW/ORANGE riders | MAGENTA/GREEN moving persons",
        fill="white",
        font=font,
    )
    for track_id, color, pixels in projected:
        scaled = pixels * scale
        for start, end in BOX_EDGES:
            draw.line((*scaled[start], *scaled[end]), fill=(*color, 255), width=4)
        anchor = scaled[np.argmin(scaled[:, 1])]
        draw.text(
            (float(anchor[0] + 4), float(max(102, anchor[1] - 24))),
            track_id,
            fill=color,
            font=font,
            stroke_width=2,
            stroke_fill=(0, 0, 0),
        )
    return image


def write_html() -> None:
    (OUTPUT / "REVIEW.html").write_text(
        """<!doctype html><meta charset="utf-8"><title>episode-00 natural transition grounding</title>
<style>body{font:16px sans-serif;max-width:1300px;margin:2rem auto;line-height:1.5}video,img{max-width:100%}</style>
<h1>episode-00 natural HOLD→RELEASE grounding review</h1>
<p><b>Recorded human future이며 model trajectory 실행 영상이 아닙니다.</b></p>
<video controls src="episode-00-natural-transition-tracks.mp4"></video>
<img src="episode-00-natural-transition-contact-sheet.jpg">
<ol>
<li>human HOLD CoC의 “crossing pedestrians”는 어느 track인가?</li>
<li>seed 42/43/44가 초기에 언급한 cyclist는 rider 102 또는 133인가?</li>
<li>human RELEASE 시점 3.0초에 해당 보행자/자전거가 실제 conflict area를 벗어났는가?</li>
<li>cyan track 84/90은 횡단 주체가 아니라 단순히 ego path에 가까운 정지 보행자인가?</li>
</ol>
<p>track 84가 CoC 원인 객체가 아니면 기존 자동 primary-track phase는 semantic release 판정에 사용하지 않고,
영상으로 확인된 actor로 다시 계산해야 합니다. 모든 person track에 대한 executable minimum-clearance 0건 overlap 결과는 별도로 유지됩니다.</p>
""",
        encoding="utf-8",
    )


def main() -> int:
    manifest = json.loads((EPISODE / "manifest.json").read_text(encoding="utf-8"))
    clip_id, t0_us = manifest["clip_id"], int(manifest["t0_us"])
    interface = physical_ai_av.PhysicalAIAVDatasetInterface(
        local_dir=DATA_ROOT.resolve(),
        revision=manifest["dataset_revision"],
        confirm_download_threshold_gb=float("inf"),
    )
    camera_id = interface.features.CAMERA.CAMERA_FRONT_WIDE_120FOV
    camera = interface.get_clip_feature(clip_id, camera_id, maybe_stream=True)
    egomotion = interface.get_clip_feature(
        clip_id, interface.features.LABELS.EGOMOTION, maybe_stream=True
    )
    extrinsics = interface.get_clip_feature(clip_id, "sensor_extrinsics", maybe_stream=True)
    intrinsics = interface.get_clip_feature(clip_id, "camera_intrinsics", maybe_stream=True)
    obstacles = load_obstacles(interface, clip_id)
    tracks = {
        track_id: obstacles[obstacles.track_id.astype(str) == track_id]
        .sort_values("timestamp_us")
        .copy()
        for track_id in TRACKS
    }
    missing = [track_id for track_id, frame in tracks.items() if frame.empty]
    if missing:
        raise RuntimeError(f"missing selected tracks: {missing}")

    requested = t0_us + np.arange(0, int(END_S * 1e6) + 1, int(1e6 / FPS), dtype=np.int64)
    frames, actual = camera.decode_images_from_timestamps(requested)
    images = []
    projection_counts = {track_id: 0 for track_id in TRACKS}
    camera_pose = extrinsics.sensor_poses[camera_id]
    camera_model = intrinsics.camera_models[camera_id]
    for array, timestamp in zip(frames, actual, strict=True):
        projected = []
        for track_id, frame in tracks.items():
            index = int(np.argmin(np.abs(frame.timestamp_us.to_numpy(dtype=np.int64) - timestamp)))
            row = frame.iloc[index]
            if abs(int(row.timestamp_us) - int(timestamp)) > 100_000:
                continue
            pixels = project_box(row, int(timestamp), egomotion, camera_pose, camera_model)
            if pixels is None:
                continue
            projection_counts[track_id] += 1
            projected.append((track_id, TRACKS[track_id][1], pixels))
        images.append(annotate(array, projected, (int(timestamp) - t0_us) / 1e6))

    OUTPUT.mkdir(parents=True, exist_ok=True, mode=0o700)
    video = OUTPUT / "episode-00-natural-transition-tracks.mp4"
    sheet = OUTPUT / "episode-00-natural-transition-contact-sheet.jpg"
    encode(images, video)
    contact_sheet(images, sheet)
    write_html()
    report = {
        "episode": "episode-00",
        "frame_count": len(images),
        "human_release_s": HUMAN_RELEASE_S,
        "selected_tracks": {
            track_id: {"class": value[0], "role": value[2], "projected_frames": projection_counts[track_id]}
            for track_id, value in TRACKS.items()
        },
        "warning": "Recorded human future; not execution of model trajectories.",
    }
    (OUTPUT / "media-manifest.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    for path in OUTPUT.iterdir():
        path.chmod(0o600)
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
