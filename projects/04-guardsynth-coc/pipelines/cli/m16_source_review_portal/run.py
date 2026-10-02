#!/usr/bin/env python3
"""Build the restricted image-embedded M16 60-event source-review workbench."""

from __future__ import annotations

import argparse
import base64
from collections import Counter
from datetime import date
import hashlib
from io import BytesIO
import json
from pathlib import Path
import sys
from typing import Any


if __package__ in {None, ""}:
    ROOT_BOOTSTRAP = next(
        parent
        for parent in Path(__file__).resolve().parents
        if (parent / "PROJECT_REGISTRY.json").is_file()
    )
    sys.path.insert(0, str(ROOT_BOOTSTRAP))

from cli.project_paths import project_root


ROOT = project_root(__file__)
HERE = Path(__file__).resolve().parent
TEMPLATE = HERE / "source_review_workbench.html"
M16_RUN = ROOT / (
    "artifacts/projects/guardsynth-coc/restricted/"
    "guardsynth-m16-scene-acquisition-001/"
    "m16-source-acquisition-2026-08-14-v18"
)
PACKET = M16_RUN / "HUMAN_SOURCE_REVIEW_PACKET.json"
PRIMARY = M16_RUN / "SENSOR_MATERIALIZATION_SHORTLIST.json"
RESERVE = M16_RUN / "ATTRITION_RESERVE_COHORT.json"
PRIMARY_ASSETS = ROOT / (
    "data/restricted/nvidia_physicalai/internal-derived/m16-shortlist-v1"
)
RESERVE_ASSETS = ROOT / (
    "data/restricted/nvidia_physicalai/internal-derived/m16-reserve-v1"
)
OUTPUT_ROOT = ROOT / (
    "artifacts/projects/guardsynth-coc/restricted/"
    "guardsynth-m16-source-review-001"
)
FRAME_OFFSETS_S = (-1.0, -0.5, 0.0, 0.5, 1.0)
HTML_NAME = "source_review_with_images.html"


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    path.chmod(0o600)


def validate_output_dir(output_dir: Path) -> None:
    resolved = output_dir.resolve()
    if not resolved.is_relative_to(OUTPUT_ROOT.resolve()):
        raise ValueError("RESTRICTED_OWNER_SCOPED_OUTPUT_REQUIRED")
    if resolved == OUTPUT_ROOT.resolve():
        raise ValueError("RESTRICTED_OWNER_SCOPED_RUN_ID_REQUIRED")
    if output_dir.exists():
        raise FileExistsError("refusing to overwrite existing M16 source-review package")


def resolve_review_records(
    packet: dict[str, Any],
    primary: dict[str, Any],
    reserve: dict[str, Any],
) -> list[dict[str, Any]]:
    primary_by_digest = {
        item["candidate_digest"]: item for item in primary.get("records", ())
    }
    reserve_by_digest = {
        item["candidate_digest"]: item for item in reserve.get("records", ())
    }
    records = []
    for index, item in enumerate(packet.get("records", ()), start=1):
        source = primary_by_digest.get(item["candidate_digest"])
        asset_class = "PRIMARY"
        if source is None:
            source = reserve_by_digest.get(item["candidate_digest"])
            asset_class = "RESERVE"
        if source is None:
            raise ValueError("REVIEW_CANDIDATE_SOURCE_MISSING")
        asset_digest = source.get(
            "asset_candidate_digest", source["candidate_digest"]
        )
        records.append({
            "review_index": index,
            "candidate_digest": item["candidate_digest"],
            "slice": item["slice"],
            "event_timestamp_us": int(source["event_timestamp_us"]),
            "asset_digest": asset_digest,
            "asset_class": asset_class,
        })
    if len(records) != packet.get("record_count") or len(records) != 60:
        raise ValueError("M16_HUMAN_REVIEW_RECORD_COUNT_INVALID")
    if len({item["candidate_digest"] for item in records}) != len(records):
        raise ValueError("M16_HUMAN_REVIEW_CANDIDATE_DUPLICATE")
    return records


def _asset_dir(record: dict[str, Any]) -> Path:
    digest = record["asset_digest"].split(":")[-1]
    relative = Path(f"event-{digest}") / "camera_front_wide_120fov"
    candidates = [PRIMARY_ASSETS / relative, RESERVE_ASSETS / relative]
    found = [
        path
        for path in candidates
        if (path / "video.mp4").is_file()
        and (path / "frame_timestamps.parquet").is_file()
    ]
    if len(found) != 1:
        raise ValueError("M16_REVIEW_SENSOR_ASSET_NOT_UNIQUE")
    return found[0]


def _target_frame_indices(record: dict[str, Any], asset_dir: Path) -> list[int]:
    import pyarrow.compute as compute
    import pyarrow.parquet as parquet

    table = parquet.read_table(
        asset_dir / "frame_timestamps.parquet",
        columns=["timestamp", "frame_index"],
    )
    timestamps = table["timestamp"]
    indices = table["frame_index"]
    result = []
    for offset in FRAME_OFFSETS_S:
        target = record["event_timestamp_us"] + round(offset * 1_000_000)
        delta = compute.abs(compute.subtract(timestamps, target))
        position = int(compute.index(delta, compute.min(delta)).as_py())
        result.append(int(indices[position].as_py()))
    return result


def _decode_frames(video_path: Path, frame_indices: list[int]) -> list[Any]:
    import av

    images = []
    with av.open(str(video_path)) as container:
        stream = container.streams.video[0]
        stream.thread_type = "AUTO"
        fps = float(stream.average_rate)
        time_base = float(stream.time_base)
        for target_index in frame_indices:
            target_time = target_index / fps
            seek_time = max(0.0, target_time - 0.35)
            container.seek(
                int(seek_time / time_base),
                stream=stream,
                backward=True,
                any_frame=False,
            )
            best = None
            best_delta = float("inf")
            for frame in container.decode(stream):
                frame_time = frame.time
                if frame_time is None:
                    continue
                delta = abs(frame_time - target_time)
                if delta < best_delta:
                    best = frame
                    best_delta = delta
                if frame_time > target_time and delta > best_delta:
                    break
                if frame_time > target_time + 0.2:
                    break
            if best is None:
                raise ValueError("M16_REVIEW_FRAME_DECODE_FAILED")
            images.append(best.to_image())
    return images


def _contact_sheet(record: dict[str, Any]) -> tuple[bytes, list[int]]:
    from PIL import Image, ImageDraw

    asset_dir = _asset_dir(record)
    frame_indices = _target_frame_indices(record, asset_dir)
    frames = _decode_frames(asset_dir / "video.mp4", frame_indices)
    cell_width, cell_height = 512, 288
    header_height = 56
    sheet = Image.new("RGB", (cell_width * 3, header_height + cell_height * 2), "#102a43")
    draw = ImageDraw.Draw(sheet)
    digest_short = record["candidate_digest"].split(":")[-1][:12]
    draw.text(
        (14, 10),
        f"#{record['review_index']:02d}  {record['slice']}  {digest_short}",
        fill="white",
    )
    for index, (frame, offset, frame_index) in enumerate(
        zip(frames, FRAME_OFFSETS_S, frame_indices)
    ):
        image = frame.resize((cell_width, cell_height), Image.Resampling.LANCZOS)
        x = (index % 3) * cell_width
        y = header_height + (index // 3) * cell_height
        sheet.paste(image, (x, y))
        draw.rectangle((x + 7, y + 7, x + 128, y + 35), fill="#102a43")
        draw.text(
            (x + 13, y + 12),
            f"t{offset:+.1f}s  f{frame_index}",
            fill="white",
        )
    x, y = cell_width * 2, header_height + cell_height
    draw.text((x + 18, y + 18), "VIDEO OBSERVATION", fill="white")
    draw.text((x + 18, y + 48), "Answer only what is visible.", fill="#dff3f6")
    draw.text((x + 18, y + 74), "Source closure is handled", fill="#dff3f6")
    draw.text((x + 18, y + 98), "separately by curators.", fill="#dff3f6")
    buffer = BytesIO()
    sheet.save(buffer, format="JPEG", quality=82, optimize=True)
    return buffer.getvalue(), frame_indices


def render_workbench(records: list[dict[str, Any]], packet_sha256: str) -> str:
    reviewer_keys = {
        "review_index",
        "candidate_digest",
        "slice",
        "image_data_url",
        "image_sha256",
        "frame_offsets_s",
    }
    payload = {
        "workbench_version": "guardsynth-m16-video-observation-workbench-v0.5",
        "packet_sha256": packet_sha256,
        "image_bytes_in_export": False,
        "records": [
            {key: value for key, value in record.items() if key in reviewer_keys}
            for record in records
        ],
    }
    encoded = json.dumps(
        payload, ensure_ascii=False, separators=(",", ":")
    ).replace("<", "\\u003c")
    template = TEMPLATE.read_text(encoding="utf-8")
    if template.count("__REVIEW_DATA_JSON__") != 1:
        raise RuntimeError("M16_REVIEW_TEMPLATE_MARKER_INVALID")
    return template.replace("__REVIEW_DATA_JSON__", encoded)


def build(output_dir: Path) -> dict[str, Any]:
    validate_output_dir(output_dir)
    required = (TEMPLATE, PACKET, PRIMARY, RESERVE)
    if any(not path.is_file() for path in required):
        raise FileNotFoundError("M16_SOURCE_REVIEW_INPUT_MISSING")
    packet = _load(PACKET)
    records = resolve_review_records(packet, _load(PRIMARY), _load(RESERVE))
    image_manifest = []
    rendered_records = []
    for record in records:
        image_bytes, frame_indices = _contact_sheet(record)
        image_sha256 = _sha256_bytes(image_bytes)
        rendered_records.append({
            key: value
            for key, value in record.items()
            if key not in {"asset_digest", "asset_class"}
        } | {
            "image_data_url": (
                "data:image/jpeg;base64," + base64.b64encode(image_bytes).decode("ascii")
            ),
            "image_sha256": image_sha256,
            "frame_offsets_s": list(FRAME_OFFSETS_S),
        })
        image_manifest.append({
            "review_index": record["review_index"],
            "image_sha256": image_sha256,
            "image_byte_count": len(image_bytes),
            "frame_count": len(frame_indices),
            "frame_offsets_s": list(FRAME_OFFSETS_S),
        })
    packet_sha256 = _sha256(PACKET)
    rendered = render_workbench(rendered_records, packet_sha256)
    if any(marker in rendered.lower() for marker in ("/home/", "file://", "clip_id")):
        raise ValueError("M16_REVIEW_HTML_RAW_PATH_OR_CLIP_ID_LEAKAGE")

    output_dir.mkdir(parents=True)
    output_dir.chmod(0o700)
    html_path = output_dir / HTML_NAME
    html_path.write_text(rendered, encoding="utf-8")
    html_path.chmod(0o600)
    slice_counts = Counter(item["slice"] for item in records)
    result = {
        "experiment_id": "GUARDSYNTH-M16-SOURCE-REVIEW-001",
        "run_id": output_dir.name,
        "status": "VIDEO_OBSERVATION_UI_READY_HUMAN_REVIEW_NOT_STARTED",
        "review_record_count": len(records),
        "embedded_contact_sheet_count": len(image_manifest),
        "embedded_frame_count": sum(item["frame_count"] for item in image_manifest),
        "slice_counts": dict(sorted(slice_counts.items())),
        "human_review_completed_count": 0,
        "image_bytes_in_html": True,
        "image_bytes_in_export": False,
        "network_access_blocked_by_csp": True,
        "annotation_start_allowed": False,
        "eligible_scene_count": 1,
        "claim_scope": "VIDEO_OBSERVATION_ONLY_NOT_SOURCE_CLOSURE_OR_SAFETY",
    }
    manifest = {
        **result,
        "run_date": date.today().isoformat(),
        "input_class": "NVIDIA_LICENSE_RESTRICTED_INTERNAL_DERIVATIVES",
        "source_hashes": {
            "human_source_review_packet": packet_sha256,
            "primary_shortlist": _sha256(PRIMARY),
            "attrition_reserve_cohort": _sha256(RESERVE),
            "html_template": _sha256(TEMPLATE),
        },
        "html_sha256": _sha256(html_path),
        "embedded_image_bytes": sum(
            item["image_byte_count"] for item in image_manifest
        ),
        "images": image_manifest,
        "raw_source_paths_included": False,
        "raw_clip_ids_included": False,
    }
    _write_json(output_dir / "RESULT.json", result)
    _write_json(output_dir / "RUN_MANIFEST.json", manifest)
    (output_dir / "REPORT_KO.md").write_text(
        "# M16 이미지 내장 영상 관찰 패키지\n\n"
        f"- 상태: **{result['status']}**\n"
        f"- 검토 record/contact sheet: **{len(records)}/{len(image_manifest)}**\n"
        f"- 내장 frame: **{result['embedded_frame_count']}개**\n"
        "- 실제 human review 완료: **0/60**\n"
        "- annotation start: **금지**\n\n"
        f"`{HTML_NAME}`을 제한 로컬 포털에서 연다. 이미지 bytes는 HTML에만 포함되고 "
        "review JSON/CSV export에는 포함되지 않는다. 검토자는 영상에서 관찰 가능한 association과 "
        "시간 상태만 기록한다. 국가·법규·geometry·transform·authority와 source ref는 별도 curator "
        "단계에서 관리하며, 이 패키지는 source closure 또는 차량 안전성의 완료 근거가 아니다.\n",
        encoding="utf-8",
    )
    (output_dir / "REPORT_KO.md").chmod(0o600)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    result = build(args.output_dir)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
