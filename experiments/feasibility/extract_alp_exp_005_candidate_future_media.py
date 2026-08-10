#!/usr/bin/env python3
"""Extract restricted front-wide future media for surviving UOM candidates."""

from __future__ import annotations

import json
from pathlib import Path

import av
import numpy as np
import physical_ai_av
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[2]
BATCH_ROOT = (
    ROOT
    / "artifacts/results/restricted/alp-exp-005"
    / "feasibility-batch-v0"
)
OMISSION_ROOT = BATCH_ROOT / "omission-addendum-v1"
OUTPUT_ROOT = BATCH_ROOT / "candidate-adjudication-v1"
DATASET_REVISION = "b719eea7f0a63619ef51ec7f54178af0937ef050"
CANDIDATES = ("UOM-001", "UOM-003", "UOM-006")
START_OFFSET_S = -0.5
END_OFFSET_S = 6.4
FPS = 10
VIDEO_SIZE = (960, 540)


def encode_video(frames: np.ndarray, review_id: str, output: Path) -> None:
    container = av.open(str(output), mode="w")
    stream = container.add_stream("libx264", rate=FPS)
    stream.width, stream.height = VIDEO_SIZE
    stream.pix_fmt = "yuv420p"
    stream.options = {"crf": "22", "preset": "medium"}
    font = ImageFont.load_default(size=22)
    try:
        for index, array in enumerate(frames):
            image = Image.fromarray(array).resize(VIDEO_SIZE, Image.Resampling.LANCZOS)
            draw = ImageDraw.Draw(image)
            relative_s = START_OFFSET_S + index / FPS
            label = f"{review_id}  front-wide  t={relative_s:+.1f}s"
            draw.rectangle((8, 8, 390, 42), fill=(0, 0, 0))
            draw.text((15, 13), label, fill="white", font=font)
            frame = av.VideoFrame.from_image(image)
            for packet in stream.encode(frame):
                container.mux(packet)
        for packet in stream.encode():
            container.mux(packet)
    finally:
        container.close()
    output.chmod(0o600)


def write_contact_sheet(frames: np.ndarray, review_id: str, output: Path) -> None:
    indices = [0, 5, 10, 15, 25, 35, 45, 55, 65, len(frames) - 1]
    cell = (480, 270)
    header = 30
    canvas = Image.new("RGB", (cell[0] * 5, (cell[1] + header) * 2), "white")
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.load_default(size=18)
    for slot, index in enumerate(indices):
        row, column = divmod(slot, 5)
        x, y = column * cell[0], row * (cell[1] + header)
        image = Image.fromarray(frames[index]).resize(cell, Image.Resampling.LANCZOS)
        canvas.paste(image, (x, y + header))
        relative_s = START_OFFSET_S + index / FPS
        draw.text((x + 8, y + 5), f"{review_id}  t={relative_s:+.1f}s", fill="black", font=font)
    canvas.save(output, format="JPEG", quality=88, optimize=True)
    output.chmod(0o600)


def main() -> int:
    mapping = json.loads(
        (OMISSION_ROOT / "adjudication-only/blind-mapping.json").read_text(encoding="utf-8")
    )
    by_id = {row["review_id"]: row for row in mapping}
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True, mode=0o700)
    OUTPUT_ROOT.chmod(0o700)
    interface = physical_ai_av.PhysicalAIAVDatasetInterface(revision=DATASET_REVISION)
    records = []
    for review_id in CANDIDATES:
        row = by_id[review_id]
        run_root = BATCH_ROOT / row["episode"] / f"seed-{row['seed']}"
        run_manifest = json.loads((run_root / "manifest.json").read_text(encoding="utf-8"))
        t0_us = int(run_manifest["t0_us"])
        clip_id = run_manifest["clip_id"]
        camera = interface.get_clip_feature(
            clip_id,
            interface.features.CAMERA.CAMERA_FRONT_WIDE_120FOV,
            maybe_stream=True,
        )
        offsets_us = np.arange(
            int(START_OFFSET_S * 1_000_000),
            int(END_OFFSET_S * 1_000_000) + 1,
            int(1_000_000 / FPS),
            dtype=np.int64,
        )
        requested = t0_us + offsets_us
        frames, actual = camera.decode_images_from_timestamps(requested)
        if len(frames) != len(requested):
            raise ValueError(f"Unexpected frame count for {review_id}: {len(frames)}")
        video_name = f"{review_id}-front-wide-t0-minus0.5-to-plus6.4.mp4"
        sheet_name = f"{review_id}-front-wide-future-contact-sheet.jpg"
        encode_video(frames, review_id, OUTPUT_ROOT / video_name)
        write_contact_sheet(frames, review_id, OUTPUT_ROOT / sheet_name)
        records.append(
            {
                "review_id": review_id,
                "source_episode": row["episode"],
                "seed": row["seed"],
                "dataset_revision": DATASET_REVISION,
                "camera": "camera_front_wide_120fov",
                "relative_window_s": [START_OFFSET_S, END_OFFSET_S],
                "fps": FPS,
                "frame_count": len(frames),
                "max_timestamp_error_us": int(np.max(np.abs(actual - requested))),
                "video": video_name,
                "contact_sheet": sheet_name,
                "publication_control": "LICENSE_RESTRICTED_INTERNAL_RESULT",
            }
        )
        print(f"extracted {review_id}: {len(frames)} frames", flush=True)
    manifest = OUTPUT_ROOT / "media-manifest.json"
    manifest.write_text(json.dumps(records, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    manifest.chmod(0o600)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
