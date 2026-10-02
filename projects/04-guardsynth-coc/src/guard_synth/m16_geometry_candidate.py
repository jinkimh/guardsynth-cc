"""Fail-closed contracts for source-bound M16 vision geometry candidates."""

from __future__ import annotations

from collections import Counter
import re
from typing import Any, Iterable, Mapping


FRAME_OFFSETS_S = (-1.0, -0.5, 0.0, 0.5, 1.0)
SLICES = {
    "PEDESTRIAN_CYCLIST_YIELD",
    "STOP_SIGNALS",
    "FOLLOWING_CUT_IN",
}
_DIGEST = re.compile(r"^candidate-sha256:[0-9a-f]{64}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_GIT_REVISION = re.compile(r"^[0-9a-f]{40}$")


def _require_sha256(value: Any, code: str) -> str:
    text = str(value)
    if not _SHA256.fullmatch(text):
        raise ValueError(code)
    return text


def build_geometry_candidate_record(
    *,
    candidate_digest: str,
    asset_candidate_digest: str,
    scene_slice: str,
    event_timestamp_us: int,
    source_video_sha256: str,
    model_source_revision: str,
    model_weight_sha256: str,
    frame_records: Iterable[Mapping[str, Any]],
) -> dict[str, Any]:
    """Bind machine masks to source frames without promoting them to scene truth."""

    if not _DIGEST.fullmatch(candidate_digest) or not _DIGEST.fullmatch(
        asset_candidate_digest
    ):
        raise ValueError("M16_GEOMETRY_CANDIDATE_DIGEST_INVALID")
    if scene_slice not in SLICES:
        raise ValueError("M16_GEOMETRY_SLICE_INVALID")
    if not isinstance(event_timestamp_us, int) or event_timestamp_us < 0:
        raise ValueError("M16_GEOMETRY_EVENT_TIMESTAMP_INVALID")
    _require_sha256(source_video_sha256, "M16_GEOMETRY_VIDEO_HASH_INVALID")
    if not _GIT_REVISION.fullmatch(model_source_revision):
        raise ValueError("M16_GEOMETRY_MODEL_REVISION_INVALID")
    _require_sha256(model_weight_sha256, "M16_GEOMETRY_WEIGHT_HASH_INVALID")

    frames = [dict(item) for item in frame_records]
    if len(frames) != len(FRAME_OFFSETS_S):
        raise ValueError("M16_GEOMETRY_FIVE_FRAME_CONTRACT_INVALID")
    if tuple(float(item.get("offset_s")) for item in frames) != FRAME_OFFSETS_S:
        raise ValueError("M16_GEOMETRY_FIVE_FRAME_OFFSETS_INVALID")
    for item in frames:
        if not isinstance(item.get("frame_index"), int) or item["frame_index"] < 0:
            raise ValueError("M16_GEOMETRY_FRAME_INDEX_INVALID")
        if not isinstance(item.get("timestamp_us"), int):
            raise ValueError("M16_GEOMETRY_FRAME_TIMESTAMP_INVALID")
        if int(item.get("width_px", 0)) <= 0 or int(item.get("height_px", 0)) <= 0:
            raise ValueError("M16_GEOMETRY_PIXEL_FRAME_INVALID")
        for field in (
            "source_pixel_sha256",
            "drivable_mask_sha256",
            "lane_mask_sha256",
            "overlay_sha256",
        ):
            _require_sha256(item.get(field), f"M16_GEOMETRY_{field.upper()}_INVALID")

    return {
        "candidate_digest": candidate_digest,
        "asset_candidate_digest": asset_candidate_digest,
        "slice": scene_slice,
        "event_timestamp_us": event_timestamp_us,
        "source_video_sha256": source_video_sha256,
        "model_source_revision": model_source_revision,
        "model_weight_sha256": model_weight_sha256,
        "coordinate_frame": "camera_front_wide_120fov_pixel",
        "unit": "pixel",
        "frame_offsets_s": list(FRAME_OFFSETS_S),
        "frames": frames,
        "machine_geometry_status": "SOURCE_BOUND_CANDIDATE",
        "curator_status": "PENDING",
        "source_field_updates": {},
        "source_complete": False,
        "eligible": False,
        "claim_scope": (
            "MACHINE_LANE_AND_DRIVABLE_AREA_CANDIDATE_FOR_CURATOR_REVIEW_"
            "NOT_MAP_GROUND_TRUTH_SOURCE_COMPLETE_OR_SAFETY"
        ),
    }


def summarize_geometry_candidates(
    records: Iterable[Mapping[str, Any]],
) -> dict[str, Any]:
    rows = [dict(record) for record in records]
    digests = [record.get("candidate_digest") for record in rows]
    if len(digests) != len(set(digests)):
        raise ValueError("M16_GEOMETRY_CANDIDATE_DUPLICATE")
    slices = Counter(str(record.get("slice")) for record in rows)
    return {
        "classified_event_count": len(rows),
        "source_bound_machine_candidate_count": sum(
            record.get("machine_geometry_status") == "SOURCE_BOUND_CANDIDATE"
            for record in rows
        ),
        "curator_pending_count": sum(
            record.get("curator_status") == "PENDING" for record in rows
        ),
        "slice_candidate_counts": dict(sorted(slices.items())),
        "new_source_complete_count": 0,
        "new_eligible_count": 0,
        "synthetic_required_field_fill_count": 0,
        "annotation_start_allowed": False,
    }


def public_geometry_candidate_summary(audit: Mapping[str, Any]) -> dict[str, Any]:
    """Return aggregate-only material suitable for the public artifact tree."""

    return {
        key: value
        for key, value in audit.items()
        if key
        not in {
            "records",
            "source_video_sha256",
            "model_weight_path",
            "restricted_workbench_path",
        }
    }
