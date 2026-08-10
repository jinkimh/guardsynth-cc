#!/usr/bin/env python3
"""Extract recorded future video for PAR-011 with predicted-plan annotations."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import av
import numpy as np
import physical_ai_av
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[2]
LOGIC = ROOT / "experiments/logic"
if str(LOGIC) not in sys.path:
    sys.path.insert(0, str(LOGIC))

from build_phase_aware_alignment_review import temporal_series  # noqa: E402


BATCH = ROOT / "artifacts/results/restricted/alp-exp-005/feasibility-batch-v0"
RUN = BATCH / "episode-05/seed-44"
OUTPUT = BATCH / "safety-acceleration-focus-v1/par-011-recorded-future"
START_S = -0.5
END_S = 6.4
FPS = 10
VIDEO_SIZE = (1280, 720)


def annotate(
    array: np.ndarray,
    relative_s: float,
    pred_time: np.ndarray,
    pred_speed: np.ndarray,
    pred_points: np.ndarray,
) -> Image.Image:
    image = Image.fromarray(array).resize(VIDEO_SIZE, Image.Resampling.LANCZOS)
    draw = ImageDraw.Draw(image, "RGBA")
    font = ImageFont.load_default(size=25)
    small = ImageFont.load_default(size=21)
    draw.rectangle((0, 0, VIDEO_SIZE[0], 116), fill=(0, 0, 0, 205))
    draw.text(
        (18, 10),
        "PAR-011 | RECORDED FUTURE CAMERA — NOT EXECUTION OF PREDICTED TRAJECTORY",
        fill=(255, 235, 59, 255),
        font=font,
    )
    draw.text(
        (18, 46),
        "CoC: Stop to yield to the pedestrian in the crosswalk ahead",
        fill="white",
        font=small,
    )
    if relative_s <= 0:
        plan = "Predicted plan: horizon starts at t0"
    else:
        index = min(len(pred_time) - 1, max(0, int(round(relative_s * FPS)) - 1))
        plan = (
            f"t={relative_s:+.1f}s | predicted x={pred_points[index, 0]:.2f} m | "
            f"predicted signed speed={pred_speed[index]:.2f} m/s"
        )
    draw.text((18, 78), plan, fill=(190, 225, 255, 255), font=small)
    return image


def encode_video(images: list[Image.Image], output: Path) -> None:
    container = av.open(str(output), mode="w")
    stream = container.add_stream("libx264", rate=FPS)
    stream.width, stream.height = VIDEO_SIZE
    stream.pix_fmt = "yuv420p"
    stream.options = {"crf": "21", "preset": "medium"}
    try:
        for image in images:
            frame = av.VideoFrame.from_image(image)
            for packet in stream.encode(frame):
                container.mux(packet)
        for packet in stream.encode():
            container.mux(packet)
    finally:
        container.close()
    output.chmod(0o600)


def contact_sheet(images: list[Image.Image], output: Path) -> None:
    indices = [0, 5, 10, 15, 25, 35, 45, 55, 65, len(images) - 1]
    cell = (640, 360)
    canvas = Image.new("RGB", (cell[0] * 5, cell[1] * 2), "white")
    for slot, index in enumerate(indices):
        row, column = divmod(slot, 5)
        canvas.paste(images[index].resize(cell, Image.Resampling.LANCZOS), (column * cell[0], row * cell[1]))
    canvas.save(output, format="JPEG", quality=90, optimize=True)
    output.chmod(0o600)


def main() -> int:
    manifest = json.loads((RUN / "manifest.json").read_text(encoding="utf-8"))
    trajectory = np.load(RUN / "predicted_trajectory.npz")
    pred_time, pred_speed, pred_points = temporal_series(
        trajectory["pred_xyz"], trajectory["pred_rot"]
    )
    interface = physical_ai_av.PhysicalAIAVDatasetInterface(
        revision=manifest["dataset_revision"]
    )
    camera = interface.get_clip_feature(
        manifest["clip_id"],
        interface.features.CAMERA.CAMERA_FRONT_WIDE_120FOV,
        maybe_stream=True,
    )
    offsets_us = np.arange(
        int(START_S * 1_000_000),
        int(END_S * 1_000_000) + 1,
        int(1_000_000 / FPS),
        dtype=np.int64,
    )
    requested = int(manifest["t0_us"]) + offsets_us
    frames, actual = camera.decode_images_from_timestamps(requested)
    images = [
        annotate(frame, START_S + index / FPS, pred_time, pred_speed, pred_points)
        for index, frame in enumerate(frames)
    ]
    OUTPUT.mkdir(parents=True, exist_ok=True, mode=0o700)
    OUTPUT.chmod(0o700)
    video = OUTPUT / "PAR-011-recorded-front-wide-with-predicted-plan-overlay.mp4"
    sheet = OUTPUT / "PAR-011-recorded-front-wide-contact-sheet.jpg"
    encode_video(images, video)
    contact_sheet(images, sheet)
    evidence = {
        "review_id": "PAR-011",
        "source_episode": "episode-05",
        "seed": 44,
        "camera": "camera_front_wide_120fov",
        "relative_window_s": [START_S, END_S],
        "fps": FPS,
        "frame_count": len(images),
        "max_timestamp_error_us": int(np.max(np.abs(actual - requested))),
        "recorded_future_warning": (
            "Camera frames follow the recorded ego future and are not the result of "
            "executing Alpamayo's predicted trajectory. Overlay values are counterfactual plan values."
        ),
        "video": video.name,
        "contact_sheet": sheet.name,
        "publication_control": "LICENSE_RESTRICTED_INTERNAL_RESULT",
    }
    evidence_path = OUTPUT / "media-manifest.json"
    evidence_path.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n")
    evidence_path.chmod(0o600)
    print(json.dumps({"video": str(video), "contact_sheet": str(sheet), "frames": len(images)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
