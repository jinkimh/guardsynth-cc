#!/usr/bin/env python3
"""Generate source-bound M16 lane/drivable-area candidates for curator review."""

from __future__ import annotations

import argparse
import base64
from collections import Counter
from datetime import date
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
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
SRC = ROOT / "projects/04-guardsynth-coc/src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from guard_synth.m16_geometry_candidate import (
    FRAME_OFFSETS_S,
    build_geometry_candidate_record,
    public_geometry_candidate_summary,
    summarize_geometry_candidates,
)


EXPERIMENT_ID = "GUARDSYNTH-M16-SCENE-ACQUISITION-001"
RUN_STATUS = "M16_SOURCE_GEOMETRY_CANDIDATES_GENERATED_CURATOR_REVIEW_REQUIRED"
PRIOR_ROOT = ROOT / (
    "artifacts/projects/guardsynth-coc/restricted/"
    "guardsynth-m16-scene-acquisition-001/"
    "m16-cascade-structured-link-audit-2026-09-05-v1"
)
ACQUISITION_ROOT = ROOT / (
    "artifacts/projects/guardsynth-coc/restricted/"
    "guardsynth-m16-scene-acquisition-001/"
    "m16-source-acquisition-2026-08-14-v18"
)
PRIOR_AUDIT = PRIOR_ROOT / "CASCADE_STRUCTURED_LINK_AUDIT.json"
PRIMARY_MATERIALIZATION = ACQUISITION_ROOT / "SENSOR_MATERIALIZATION_AUDIT.json"
RESERVE_MATERIALIZATION = ACQUISITION_ROOT / "RESERVE_SENSOR_MATERIALIZATION_AUDIT.json"
VIDEO_ROOTS = (
    ROOT / "data/restricted/nvidia_physicalai/internal-derived/m16-shortlist-v1",
    ROOT / "data/restricted/nvidia_physicalai/internal-derived/m16-reserve-v1",
)
MODEL_SOURCE = ROOT / "third_party/twinlitenetplus"
MODEL_WEIGHT = ROOT / "runtime/geometry/twinlitenetplus-large/large.pth"
MODEL_REVISION = "90f1b8695ae311d5123b05f8534b2e11e42499d2"
MODEL_WEIGHT_SHA256 = "5605d1a8ce762c1b6f7d23f4c2e7ec9384bfd6e6887b040b43e1f8902a817e22"
MODEL_SOURCE_URL = "https://github.com/chequanghuy/TwinLiteNetPlus"
MODEL_WEIGHT_URL = (
    "https://drive.google.com/uc?id=1H8P-GrOUBOaVs5LEqXBfz0dC9gguUUio"
)
TEMPLATE = Path(__file__).resolve().parent / "geometry_candidate_workbench.html"
WORKBENCH_NAME = "geometry_candidate_workbench.html"
CLAIM_SCOPE = (
    "M16_MACHINE_GEOMETRY_CANDIDATES_FOR_CURATOR_REVIEW_NOT_MAP_GROUND_"
    "TRUTH_SOURCE_COMPLETE_EXPERT_EFFECT_OR_VEHICLE_SAFETY"
)


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _write_json(path: Path, value: Any, *, restricted: bool) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    path.chmod(0o600 if restricted else 0o644)


def _write_text(path: Path, value: str, *, restricted: bool) -> None:
    path.write_text(value, encoding="utf-8")
    path.chmod(0o600 if restricted else 0o644)


def _write_bytes(path: Path, value: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(value)
    path.chmod(0o600)


def _data_url(path: Path) -> str:
    return "data:image/jpeg;base64," + base64.b64encode(path.read_bytes()).decode("ascii")


def render_workbench(
    records: list[dict[str, Any]], *, manifest_sha256: str
) -> str:
    payload = {
        "workbench_version": "guardsynth-m16-geometry-curator-workbench-v0.5",
        "manifest_sha256": manifest_sha256,
        "records": records,
    }
    encoded = json.dumps(
        payload, ensure_ascii=False, separators=(",", ":")
    ).replace("<", "\\u003c")
    template = TEMPLATE.read_text(encoding="utf-8")
    if template.count("__GEOMETRY_REVIEW_DATA_JSON__") != 1:
        raise RuntimeError("M16_GEOMETRY_WORKBENCH_TEMPLATE_MARKER_INVALID")
    return template.replace("__GEOMETRY_REVIEW_DATA_JSON__", encoded)


def _model_revision() -> str:
    revision = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=MODEL_SOURCE,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if revision != MODEL_REVISION:
        raise ValueError("M16_GEOMETRY_MODEL_SOURCE_REVISION_CHANGED")
    return revision


def _repository_revision() -> tuple[str, str]:
    revision = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    ).stdout.strip() or "NO_GIT_METADATA"
    dirty = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    ).stdout
    return revision, "WORKSPACE_WITH_UNCOMMITTED_CHANGES" if dirty else "CLEAN"


def _video_materialization_records() -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for manifest_path in (PRIMARY_MATERIALIZATION, RESERVE_MATERIALIZATION):
        for record in _load(manifest_path)["records"]:
            if record.get("feature") != "camera_front_wide_120fov" or record.get("role") != "video":
                continue
            digest = record["candidate_digest"]
            if digest in result:
                raise ValueError("M16_GEOMETRY_VIDEO_MATERIALIZATION_DUPLICATE")
            result[digest] = record
    if len(result) != 81:
        raise ValueError("M16_GEOMETRY_VIDEO_MATERIALIZATION_COUNT_INVALID")
    return result


def _asset_dir(asset_candidate_digest: str) -> Path:
    digest = asset_candidate_digest.split(":")[-1]
    relative = Path(f"event-{digest}") / "camera_front_wide_120fov"
    matches = [
        root / relative
        for root in VIDEO_ROOTS
        if (root / relative / "video.mp4").is_file()
        and (root / relative / "frame_timestamps.parquet").is_file()
    ]
    if len(matches) != 1:
        raise ValueError("M16_GEOMETRY_SENSOR_ASSET_NOT_UNIQUE")
    return matches[0]


def _target_frame_records(
    event_timestamp_us: int, timestamp_path: Path
) -> list[dict[str, int | float]]:
    import numpy as np
    import pyarrow.parquet as parquet

    table = parquet.read_table(timestamp_path, columns=["timestamp", "frame_index"])
    timestamps = table["timestamp"].to_numpy(zero_copy_only=False).astype("int64")
    indices = table["frame_index"].to_numpy(zero_copy_only=False).astype("int64")
    records = []
    for offset in FRAME_OFFSETS_S:
        target = event_timestamp_us + round(offset * 1_000_000)
        position = int(np.abs(timestamps - target).argmin())
        records.append({
            "offset_s": offset,
            "frame_index": int(indices[position]),
            "timestamp_us": int(timestamps[position]),
        })
    return records


def _decode_frames(video_path: Path, frame_indices: list[int]) -> list[Any]:
    import cv2

    capture = cv2.VideoCapture(str(video_path))
    if not capture.isOpened():
        raise ValueError("M16_GEOMETRY_VIDEO_OPEN_FAILED")
    frames = []
    try:
        for frame_index in frame_indices:
            capture.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
            ok, frame = capture.read()
            if not ok or frame is None:
                raise ValueError("M16_GEOMETRY_FRAME_DECODE_FAILED")
            frames.append(frame)
    finally:
        capture.release()
    return frames


class TwinLiteNetPlusAdapter:
    """Small inference-only adapter around the pinned upstream checkout."""

    def __init__(self, device: str) -> None:
        import torch

        if _sha256(MODEL_WEIGHT) != MODEL_WEIGHT_SHA256:
            raise ValueError("M16_GEOMETRY_MODEL_WEIGHT_HASH_CHANGED")
        if str(MODEL_SOURCE) not in sys.path:
            sys.path.insert(0, str(MODEL_SOURCE))
        from model.model import TwinLiteNetPlus

        if device.startswith("cuda") and not torch.cuda.is_available():
            raise RuntimeError("M16_GEOMETRY_CUDA_UNAVAILABLE")
        self.torch = torch
        self.device = torch.device(device)
        self.half = self.device.type == "cuda"
        self.model = TwinLiteNetPlus(SimpleNamespace(config="large")).to(self.device)
        state = torch.load(
            MODEL_WEIGHT,
            map_location=self.device,
            weights_only=True,
        )
        self.model.load_state_dict(state)
        if self.half:
            self.model.half()
        self.model.eval()

    @staticmethod
    def _letterbox(frame: Any, size: int = 640) -> tuple[Any, tuple[int, int, int, int]]:
        import cv2
        import numpy as np

        height, width = frame.shape[:2]
        ratio = min(size / height, size / width)
        resized = (int(round(width * ratio)), int(round(height * ratio)))
        image = cv2.resize(frame, resized, interpolation=cv2.INTER_AREA)
        dw, dh = size - resized[0], size - resized[1]
        dw, dh = np.mod(dw, 32), np.mod(dh, 32)
        left, right = int(round(dw / 2 - 0.1)), int(round(dw / 2 + 0.1))
        top, bottom = int(round(dh / 2 - 0.1)), int(round(dh / 2 + 0.1))
        image = cv2.copyMakeBorder(
            image, top, bottom, left, right, cv2.BORDER_CONSTANT, value=(114, 114, 114)
        )
        return image, (top, bottom, left, right)

    def infer(self, frames: list[Any]) -> list[tuple[Any, Any]]:
        import numpy as np

        prepared = [self._letterbox(frame) for frame in frames]
        shapes = {item[0].shape for item in prepared}
        if len(shapes) != 1:
            raise ValueError("M16_GEOMETRY_BATCH_IMAGE_SHAPE_MISMATCH")
        array = np.stack(
            [item[0][:, :, ::-1].transpose(2, 0, 1) for item in prepared]
        ).copy()
        tensor = self.torch.from_numpy(array).to(self.device)
        tensor = tensor.half() if self.half else tensor.float()
        tensor /= 255.0
        with self.torch.inference_mode():
            drivable_logits, lane_logits = self.model(tensor)
        result = []
        for index, frame in enumerate(frames):
            top, bottom, left, right = prepared[index][1]
            height, width = drivable_logits.shape[-2:]
            masks = []
            for logits in (drivable_logits[index:index + 1], lane_logits[index:index + 1]):
                cropped = logits[
                    :,
                    :,
                    top:height - bottom if bottom else height,
                    left:width - right if right else width,
                ]
                resized = self.torch.nn.functional.interpolate(
                    cropped,
                    size=frame.shape[:2],
                    mode="bilinear",
                    align_corners=False,
                )
                masks.append(
                    resized.argmax(1).squeeze().byte().cpu().numpy()
                )
            result.append((masks[0], masks[1]))
        return result


def _encode_png(mask: Any) -> bytes:
    import cv2

    ok, encoded = cv2.imencode(".png", mask * 255, [cv2.IMWRITE_PNG_COMPRESSION, 9])
    if not ok:
        raise ValueError("M16_GEOMETRY_MASK_ENCODING_FAILED")
    return encoded.tobytes()


def _overlay(frame: Any, drivable: Any, lane: Any) -> Any:
    import numpy as np

    color = np.zeros_like(frame)
    color[drivable == 1] = (0, 255, 0)
    color[lane == 1] = (0, 0, 255)
    result = frame.copy()
    selected = color.any(axis=2)
    result[selected] = (result[selected] * 0.52 + color[selected] * 0.48).astype("uint8")
    return result


def _encode_review_jpeg(image: Any, *, width: int, quality: int = 78) -> bytes:
    import cv2

    height = round(image.shape[0] * width / image.shape[1])
    resized = cv2.resize(image, (width, height), interpolation=cv2.INTER_AREA)
    ok, encoded = cv2.imencode(".jpg", resized, [cv2.IMWRITE_JPEG_QUALITY, quality])
    if not ok:
        raise ValueError("M16_GEOMETRY_REVIEW_IMAGE_ENCODING_FAILED")
    return encoded.tobytes()


def _contact_sheet(overlays: list[Any], frame_records: list[dict[str, Any]]) -> bytes:
    import cv2
    import numpy as np

    cell_width, cell_height, header = 480, 270, 42
    sheet = np.full((header + cell_height * 2, cell_width * 3, 3), (43, 35, 21), dtype="uint8")
    for index, (overlay, record) in enumerate(zip(overlays, frame_records)):
        cell = cv2.resize(overlay, (cell_width, cell_height), interpolation=cv2.INTER_AREA)
        x, y = index % 3 * cell_width, header + index // 3 * cell_height
        sheet[y:y + cell_height, x:x + cell_width] = cell
        label = f"t{record['offset_s']:+.1f}s  f{record['frame_index']}"
        cv2.rectangle(sheet, (x + 7, y + 7), (x + 155, y + 34), (43, 35, 21), -1)
        cv2.putText(sheet, label, (x + 12, y + 27), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1, cv2.LINE_AA)
    cv2.putText(sheet, "TwinLiteNet+ candidate overlay", (14, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.72, (255, 255, 255), 2, cv2.LINE_AA)
    ok, encoded = cv2.imencode(".jpg", sheet, [cv2.IMWRITE_JPEG_QUALITY, 74])
    if not ok:
        raise ValueError("M16_GEOMETRY_CONTACT_SHEET_ENCODING_FAILED")
    return encoded.tobytes()


def _process_event(
    *,
    record: dict[str, Any],
    review_index: int,
    video_metadata: dict[str, dict[str, Any]],
    adapter: TwinLiteNetPlusAdapter,
    output_dir: Path,
    verified_video_hashes: dict[Path, str],
) -> tuple[dict[str, Any], dict[str, Any]]:
    asset_digest = record["coordinate_transform"]["asset_candidate_digest"]
    metadata = video_metadata.get(asset_digest)
    if metadata is None:
        raise ValueError("M16_GEOMETRY_VIDEO_METADATA_MISSING")
    asset_dir = _asset_dir(asset_digest)
    video_path = asset_dir / "video.mp4"
    video_hash = verified_video_hashes.setdefault(video_path, _sha256(video_path))
    if video_hash != metadata["sha256"]:
        raise ValueError("M16_GEOMETRY_SOURCE_VIDEO_HASH_CHANGED")
    frames_meta = _target_frame_records(
        int(record["event_timestamp_us"]), asset_dir / "frame_timestamps.parquet"
    )
    frames = _decode_frames(video_path, [item["frame_index"] for item in frames_meta])
    masks = adapter.infer(frames)
    overlays = []
    event_root = output_dir / "geometry" / f"event-{review_index:03d}"
    frame_evidence = []
    for frame, (drivable, lane), metadata_row in zip(frames, masks, frames_meta):
        offset_ms = round(float(metadata_row["offset_s"]) * 1000)
        offset_label = f"m{abs(offset_ms):04d}" if offset_ms < 0 else f"p{offset_ms:04d}"
        drivable_bytes = _encode_png(drivable)
        lane_bytes = _encode_png(lane)
        overlay = _overlay(frame, drivable, lane)
        overlay_bytes = _encode_review_jpeg(overlay, width=1280)
        drivable_path = event_root / f"frame-{offset_label}-drivable-mask.png"
        lane_path = event_root / f"frame-{offset_label}-lane-mask.png"
        overlay_path = event_root / f"frame-{offset_label}-overlay.jpg"
        _write_bytes(drivable_path, drivable_bytes)
        _write_bytes(lane_path, lane_bytes)
        _write_bytes(overlay_path, overlay_bytes)
        frame_evidence.append({
            **metadata_row,
            "source_pixel_sha256": _sha256_bytes(frame.tobytes()),
            "drivable_mask_sha256": _sha256_bytes(drivable_bytes),
            "lane_mask_sha256": _sha256_bytes(lane_bytes),
            "overlay_sha256": _sha256_bytes(overlay_bytes),
            "width_px": int(frame.shape[1]),
            "height_px": int(frame.shape[0]),
            "drivable_mask_path": drivable_path.relative_to(output_dir).as_posix(),
            "lane_mask_path": lane_path.relative_to(output_dir).as_posix(),
            "overlay_path": overlay_path.relative_to(output_dir).as_posix(),
        })
        overlays.append(overlay)
    contact_bytes = _contact_sheet(overlays, frame_evidence)
    contact_path = event_root / "contact-sheet.jpg"
    _write_bytes(contact_path, contact_bytes)
    candidate = build_geometry_candidate_record(
        candidate_digest=record["candidate_digest"],
        asset_candidate_digest=asset_digest,
        scene_slice=record["slice"],
        event_timestamp_us=int(record["event_timestamp_us"]),
        source_video_sha256=video_hash,
        model_source_revision=MODEL_REVISION,
        model_weight_sha256=MODEL_WEIGHT_SHA256,
        frame_records=frame_evidence,
    )
    candidate.update({
        "review_index": review_index,
        "contact_sheet_path": contact_path.relative_to(output_dir).as_posix(),
        "contact_sheet_sha256": _sha256_bytes(contact_bytes),
    })
    t0 = frame_evidence[2]
    review = {
        "review_index": review_index,
        "candidate_digest": record["candidate_digest"],
        "slice": record["slice"],
        "event_timestamp_us": int(record["event_timestamp_us"]),
        "source_video_sha256": video_hash,
        "t0_source_pixel_sha256": t0["source_pixel_sha256"],
        "t0_overlay_sha256": t0["overlay_sha256"],
        "contact_sheet_data_url": "data:image/jpeg;base64," + base64.b64encode(contact_bytes).decode("ascii"),
        "t0_overlay_data_url": _data_url(output_dir / t0["overlay_path"]),
    }
    return candidate, review


def _report(result: dict[str, Any]) -> str:
    return f"""# M16 source geometry 후보 생성 결과

- 상태: `{result['status']}`
- 대상 이벤트: {result['classified_event_count']}
- source-bound 기계 후보: {result['source_bound_machine_candidate_count']}
- curator 확인 대기: {result['curator_pending_count']}
- 신규 source-complete/eligible: {result['new_source_complete_count']}/{result['new_eligible_count']}
- 기존 pilot eligible: {result['eligible_scene_count']}/60

TwinLiteNet+ large의 차선 및 주행 가능 영역 출력을 98개 이벤트의 다섯 시점에 생성했다. 각 출력은 원본 영상 해시, 실제 frame index와 timestamp, 원본 pixel hash, 모델 source revision과 weight hash에 연결했다.

이 결과는 지도 ground truth가 아니라 curator용 machine candidate이다. curator 확인 전에는 lane/zone·conflict geometry field를 닫지 않으며, source-complete·pilot eligibility·차량 안전성 주장을 새로 생성하지 않는다.

검토 화면은 기계 표시 품질 확인과 영상 위 normalized pixel polygon 보정만 받는다. 국가·관할, 법규 적용, calibration, evidence reference와 source-complete 판정은 묻지 않는다.
"""


def execute(
    *,
    restricted_output_dir: Path,
    public_output_dir: Path | None,
    run_id: str,
    device: str = "cuda",
) -> dict[str, Any]:
    if restricted_output_dir.exists() or (
        public_output_dir is not None and public_output_dir.exists()
    ):
        raise FileExistsError("refusing to overwrite M16 geometry candidate run")
    required = (
        PRIOR_AUDIT,
        PRIMARY_MATERIALIZATION,
        RESERVE_MATERIALIZATION,
        MODEL_SOURCE / "LICENSE",
        MODEL_WEIGHT,
        TEMPLATE,
    )
    if any(not path.is_file() for path in required):
        raise FileNotFoundError("M16_GEOMETRY_CANDIDATE_INPUT_MISSING")
    _model_revision()
    if _sha256(MODEL_WEIGHT) != MODEL_WEIGHT_SHA256:
        raise ValueError("M16_GEOMETRY_MODEL_WEIGHT_HASH_CHANGED")
    prior = _load(PRIOR_AUDIT)
    records = [
        {
            **item,
            "event_timestamp_us": int(
                item["cascade_structured_link_audit"]["event_timestamp_us"]
            ),
        }
        for item in prior.get("records", [])
    ]
    if len(records) != 98 or len({item["candidate_digest"] for item in records}) != 98:
        raise ValueError("M16_GEOMETRY_PRIOR_EVENT_SET_INVALID")
    if prior.get("verified_coordinate_transform_count") != 98:
        raise ValueError("M16_GEOMETRY_PRIOR_TRANSFORM_BASELINE_CHANGED")

    restricted_output_dir.mkdir(parents=True)
    restricted_output_dir.chmod(0o700)
    video_metadata = _video_materialization_records()
    adapter = TwinLiteNetPlusAdapter(device)
    candidates = []
    review_records = []
    video_hashes: dict[Path, str] = {}
    for review_index, record in enumerate(records, start=1):
        candidate, review = _process_event(
            record=record,
            review_index=review_index,
            video_metadata=video_metadata,
            adapter=adapter,
            output_dir=restricted_output_dir,
            verified_video_hashes=video_hashes,
        )
        candidates.append(candidate)
        review_records.append(review)

    summary = summarize_geometry_candidates(candidates)
    if summary["classified_event_count"] != 98:
        raise ValueError("M16_GEOMETRY_GENERATED_EVENT_COUNT_INVALID")
    audit = {
        "audit_version": "guardsynth-m16-geometry-candidate-v0.1",
        "status": RUN_STATUS,
        **summary,
        "unique_source_video_count": len(video_hashes),
        "frame_candidate_count": len(candidates) * len(FRAME_OFFSETS_S),
        "model": {
            "name": "TwinLiteNetPlus_Large",
            "task": ["drivable_area_segmentation", "lane_segmentation"],
            "training_domain": "BDD100K",
            "source_url": MODEL_SOURCE_URL,
            "source_revision": MODEL_REVISION,
            "source_license": "MIT",
            "source_license_sha256": _sha256(MODEL_SOURCE / "LICENSE"),
            "weight_url": MODEL_WEIGHT_URL,
            "weight_sha256": MODEL_WEIGHT_SHA256,
        },
        "coordinate_frame": "camera_front_wide_120fov_pixel",
        "unit": "pixel",
        "curator_review_screen_generated": True,
        "curator_review_screen_scope": "VISIBLE_GEOMETRY_CONFIRMATION_AND_PIXEL_POLYGON_CORRECTION_ONLY",
        "human_video_observation_promoted_to_geometry": False,
        "machine_candidate_promoted_to_ground_truth": False,
        "source_field_updates_before_curator_review": 0,
        "records": candidates,
        "claim_scope": CLAIM_SCOPE,
    }
    candidate_manifest = restricted_output_dir / "GEOMETRY_CANDIDATE_MANIFEST.json"
    _write_json(candidate_manifest, audit, restricted=True)
    manifest_hash = _sha256(candidate_manifest)
    workbench = render_workbench(review_records, manifest_sha256=manifest_hash)
    workbench_path = restricted_output_dir / WORKBENCH_NAME
    _write_text(workbench_path, workbench, restricted=True)

    result = {
        "experiment_id": EXPERIMENT_ID,
        "run_id": run_id,
        "run_date": date.today().isoformat(),
        "status": RUN_STATUS,
        **summary,
        "unique_source_video_count": len(video_hashes),
        "frame_candidate_count": len(candidates) * len(FRAME_OFFSETS_S),
        "curator_review_screen_generated": True,
        "curator_review_completed_count": 0,
        "source_field_updates_before_curator_review": 0,
        "eligible_scene_count": 1,
        "target_scene_count": 60,
        "annotation_started": False,
        "machine_candidate_promoted_to_ground_truth": False,
        "actual_vehicle_validation_deferred_to_m21": True,
        "claim_scope": CLAIM_SCOPE,
    }
    revision, workspace_state = _repository_revision()
    manifest = {
        **result,
        "code_revision": revision,
        "workspace_state": workspace_state,
        "input_hashes": {
            "prior_cascade_structured_link_audit": _sha256(PRIOR_AUDIT),
            "primary_sensor_materialization": _sha256(PRIMARY_MATERIALIZATION),
            "reserve_sensor_materialization": _sha256(RESERVE_MATERIALIZATION),
            "model_source_license": _sha256(MODEL_SOURCE / "LICENSE"),
            "model_weight": MODEL_WEIGHT_SHA256,
        },
        "output_hashes": {
            "geometry_candidate_manifest": manifest_hash,
            "geometry_candidate_workbench": _sha256(workbench_path),
        },
        "model_source_revision": MODEL_REVISION,
        "model_weight_sha256": MODEL_WEIGHT_SHA256,
        "network_use_performed": True,
        "gpu_inference_performed": device.startswith("cuda"),
    }
    _write_json(restricted_output_dir / "RESULT.json", result, restricted=True)
    _write_json(restricted_output_dir / "RUN_MANIFEST.json", manifest, restricted=True)
    _write_text(restricted_output_dir / "REPORT_KO.md", _report(result), restricted=True)

    if public_output_dir is not None:
        public_output_dir.mkdir(parents=True)
        public_audit = public_geometry_candidate_summary(audit)
        public_result = public_geometry_candidate_summary(result)
        public_manifest = public_geometry_candidate_summary(manifest)
        _write_json(public_output_dir / "GEOMETRY_CANDIDATE_SUMMARY.json", public_audit, restricted=False)
        _write_json(public_output_dir / "RESULT.json", public_result, restricted=False)
        _write_json(public_output_dir / "RUN_MANIFEST.json", public_manifest, restricted=False)
        _write_text(public_output_dir / "REPORT_KO.md", _report(public_result), restricted=False)
        public_text = "\n".join(
            path.read_text(encoding="utf-8")
            for path in public_output_dir.iterdir()
            if path.suffix in {".json", ".md"}
        )
        for forbidden in ("candidate-sha256", "clip_id", "/home/", "data:image"):
            if forbidden in public_text:
                raise ValueError("M16_GEOMETRY_RESTRICTED_IDENTIFIER_LEAK")
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--restricted-output-dir", type=Path, required=True)
    parser.add_argument("--public-output-dir", type=Path)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--device", default="cuda")
    args = parser.parse_args()
    result = execute(
        restricted_output_dir=args.restricted_output_dir,
        public_output_dir=args.public_output_dir,
        run_id=args.run_id,
        device=args.device,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
