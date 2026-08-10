#!/usr/bin/env python3
"""Re-load and render the exact multi-camera frames used by blind-review runs."""

from __future__ import annotations

import argparse
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import physical_ai_av
from PIL import Image, ImageDraw, ImageFont

from alpamayo_r1.load_physical_aiavdataset import load_physical_aiavdataset


ROOT = Path(__file__).resolve().parents[2]
REVIEW_ROOT = (
    ROOT
    / "artifacts/results/restricted/alp-exp-005"
    / "feasibility-batch-v0/blind-review-v0"
)
COHORT_PATH = (
    ROOT
    / "data/restricted/nvidia_physicalai/internal-derived/cohort-10"
    / "cohort-conformance.json"
)
DATASET_REVISION = "b719eea7f0a63619ef51ec7f54178af0937ef050"
CAMERA_NAMES = ["cross-left 120°", "front-wide 120°", "cross-right 120°", "front-tele 30°"]
TIME_NAMES = ["t0-0.3 s", "t0-0.2 s", "t0-0.1 s", "t0"]
CELL_SIZE = (480, 270)
HEADER_HEIGHT = 34
ROW_LABEL_WIDTH = 150


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--all-cohort",
        action="store_true",
        help="Extract all ten cohort scenes rather than only current blind-review scenes",
    )
    return parser.parse_args()


def render_episode(episode_name: str, episode: dict[str, object], output: Path) -> dict[str, object]:
    avdi = physical_ai_av.PhysicalAIAVDatasetInterface(revision=DATASET_REVISION)
    event = episode["events"][0]  # type: ignore[index]
    data = load_physical_aiavdataset(
        episode["clip_id"],  # type: ignore[arg-type]
        t0_us=int(event["timestamp_us"]),  # type: ignore[index]
        avdi=avdi,
        maybe_stream=True,
        num_history_steps=16,
        num_future_steps=64,
        num_frames=4,
    )
    frames = data["image_frames"].permute(0, 1, 3, 4, 2).cpu().numpy()
    timestamps = data["absolute_timestamps"].cpu().numpy().tolist()
    if tuple(frames.shape[:2]) != (4, 4):
        raise ValueError(f"Unexpected frame grid for {episode_name}: {frames.shape}")

    width = ROW_LABEL_WIDTH + CELL_SIZE[0] * 4
    height = HEADER_HEIGHT + (CELL_SIZE[1] + HEADER_HEIGHT) * 4
    canvas = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.load_default(size=18)
    small_font = ImageFont.load_default(size=15)

    for column, name in enumerate(TIME_NAMES):
        x = ROW_LABEL_WIDTH + column * CELL_SIZE[0] + 10
        draw.text((x, 7), name, fill="black", font=font)
    for camera, camera_name in enumerate(CAMERA_NAMES):
        y0 = HEADER_HEIGHT + camera * (CELL_SIZE[1] + HEADER_HEIGHT)
        draw.multiline_text((8, y0 + 95), camera_name.replace(" ", "\n", 1), fill="black", font=small_font)
        for time_index in range(4):
            frame = Image.fromarray(frames[camera, time_index]).resize(CELL_SIZE, Image.Resampling.LANCZOS)
            x0 = ROW_LABEL_WIDTH + time_index * CELL_SIZE[0]
            canvas.paste(frame, (x0, y0))
            draw.rectangle((x0, y0, x0 + CELL_SIZE[0] - 1, y0 + CELL_SIZE[1] - 1), outline="#555", width=1)
        draw.text(
            (ROW_LABEL_WIDTH + 8, y0 + CELL_SIZE[1] + 6),
            f"Model-input camera row {camera + 1}/4",
            fill="#333",
            font=small_font,
        )

    output.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    output.parent.chmod(0o700)
    canvas.save(output, format="JPEG", quality=88, optimize=True)
    output.chmod(0o600)
    return {
        "episode": episode_name,
        "dataset_revision": DATASET_REVISION,
        "source": "exact Alpamayo model input reloaded from pinned dataset revision",
        "camera_order": CAMERA_NAMES,
        "relative_times_s": [-0.3, -0.2, -0.1, 0.0],
        "absolute_timestamps_us": timestamps,
        "image": output.name,
        "publication_control": "LICENSE_RESTRICTED_INTERNAL_RESULT",
    }


def main() -> int:
    args = parse_args()
    cohort = json.loads(COHORT_PATH.read_text(encoding="utf-8"))
    mapping = json.loads(
        (REVIEW_ROOT / "adjudication-only/blind-mapping.json").read_text(encoding="utf-8")
    )
    selected_names = (
        [f"episode-{index:02d}" for index in range(len(cohort["episodes"]))]
        if args.all_cohort
        else sorted({row["episode"] for row in mapping})
    )
    selected = {
        f"episode-{index:02d}": cohort["episodes"][index]
        for index in range(len(cohort["episodes"]))
        if f"episode-{index:02d}" in selected_names
    }
    if selected.keys() != set(selected_names):
        raise ValueError("Blind mapping contains an episode outside the pinned cohort")

    output_dir = REVIEW_ROOT / "scene-inputs"
    records = []
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {
            executor.submit(
                render_episode,
                episode_name,
                episode,
                output_dir / f"{episode_name}-model-input.jpg",
            ): episode_name
            for episode_name, episode in selected.items()
        }
        for future in as_completed(futures):
            record = future.result()
            records.append(record)
            print(f"rendered {record['episode']}", flush=True)

    records.sort(key=lambda row: row["episode"])
    manifest = output_dir / "media-manifest.json"
    manifest.write_text(json.dumps(records, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    manifest.chmod(0o600)
    print(f"wrote {len(records)} scene inputs to {output_dir.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
