"""M16 review-event anchor binding and offline egomotion transform audit."""

from __future__ import annotations

from copy import deepcopy
from math import isfinite
import re
from typing import Any, Mapping, Sequence

import numpy as np
from scipy.spatial.transform import Rotation, Slerp


EVENT_ANCHOR_POLICY_VERSION = "guardsynth-m16-review-event-anchor-v0.1"
TRANSFORM_AUDIT_VERSION = "guardsynth-m16-event-anchor-transform-v0.1"
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def _pose_at(
    rows: Sequence[Mapping[str, Any]], timestamp_us: int
) -> tuple[np.ndarray, list[int]]:
    required = ("timestamp", "qx", "qy", "qz", "qw", "x", "y", "z")
    if len(rows) < 2:
        raise ValueError("OFFLINE_EGOMOTION_REQUIRES_AT_LEAST_TWO_ROWS")
    parsed: list[tuple[int, list[float], list[float]]] = []
    for row in rows:
        if any(key not in row for key in required):
            raise ValueError("OFFLINE_EGOMOTION_SCHEMA_INVALID")
        timestamp = row["timestamp"]
        if isinstance(timestamp, bool) or not isinstance(timestamp, int):
            raise ValueError("OFFLINE_EGOMOTION_TIMESTAMP_INVALID")
        quaternion = [float(row[key]) for key in ("qx", "qy", "qz", "qw")]
        translation = [float(row[key]) for key in ("x", "y", "z")]
        if not all(isfinite(value) for value in quaternion + translation):
            raise ValueError("OFFLINE_EGOMOTION_NONFINITE_VALUE")
        norm = float(np.linalg.norm(quaternion))
        if abs(norm - 1.0) > 1e-5:
            raise ValueError("OFFLINE_EGOMOTION_QUATERNION_NOT_NORMALIZED")
        parsed.append((timestamp, quaternion, translation))
    if any(right[0] <= left[0] for left, right in zip(parsed, parsed[1:])):
        raise ValueError("OFFLINE_EGOMOTION_TIMESTAMPS_NOT_STRICTLY_INCREASING")
    if timestamp_us < parsed[0][0] or timestamp_us > parsed[-1][0]:
        raise ValueError("EVENT_NOT_BRACKETED_BY_OFFLINE_EGOMOTION")

    right_index = next(
        index for index, item in enumerate(parsed) if item[0] >= timestamp_us
    )
    if parsed[right_index][0] == timestamp_us:
        left_index = right_index
        quaternion = np.asarray(parsed[right_index][1])
        translation = np.asarray(parsed[right_index][2])
    else:
        left_index = right_index - 1
        left, right = parsed[left_index], parsed[right_index]
        fraction = (timestamp_us - left[0]) / (right[0] - left[0])
        quaternion = Slerp(
            [float(left[0]), float(right[0])],
            Rotation.from_quat([left[1], right[1]]),
        )([float(timestamp_us)]).as_quat()[0]
        translation = (
            np.asarray(left[2])
            + fraction * (np.asarray(right[2]) - np.asarray(left[2]))
        )

    matrix = np.eye(4, dtype=float)
    matrix[:3, :3] = Rotation.from_quat(quaternion).as_matrix()
    matrix[:3, 3] = translation
    return matrix, [parsed[left_index][0], parsed[right_index][0]]


def verify_event_anchor_transform(
    *,
    egomotion_rows: Sequence[Mapping[str, Any]],
    event_timestamp_us: int,
    egomotion_sha256: str,
    offline_extrinsics_sha256: str,
) -> dict[str, Any]:
    """Bind the reviewed M16 event itself as t0 and verify numeric closure."""
    if (
        isinstance(event_timestamp_us, bool)
        or not isinstance(event_timestamp_us, int)
        or _SHA256_RE.fullmatch(egomotion_sha256) is None
        or _SHA256_RE.fullmatch(offline_extrinsics_sha256) is None
    ):
        raise ValueError("EVENT_ANCHOR_TRANSFORM_INPUT_INVALID")

    event_pose, bracket = _pose_at(egomotion_rows, event_timestamp_us)
    t0_pose = event_pose.copy()
    event_to_t0 = np.linalg.inv(t0_pose) @ event_pose
    inverse = np.linalg.inv(event_to_t0)
    closure_error = float(np.max(np.abs(event_to_t0 @ inverse - np.eye(4))))
    identity_error = float(np.max(np.abs(event_to_t0 - np.eye(4))))
    if closure_error > 1e-12 or identity_error > 1e-12:
        raise ValueError("EVENT_ANCHOR_TRANSFORM_NUMERIC_CLOSURE_FAILED")
    return {
        "transform_audit_version": TRANSFORM_AUDIT_VERSION,
        "status": "AVAILABLE_SOURCE_LINKED",
        "source_frame": "dataset_rig_at_event",
        "target_frame": "ego_at_model_t0",
        "event_timestamp_us": event_timestamp_us,
        "t0_us": event_timestamp_us,
        "t0_binding": "M16_REVIEW_EVENT_TIMESTAMP",
        "t0_policy_version": EVENT_ANCHOR_POLICY_VERSION,
        "bracketing_timestamp_us": bracket,
        "matrix_4x4": event_to_t0.tolist(),
        "inverse_closure_max_abs_error": closure_error,
        "event_to_t0_identity_max_abs_error": identity_error,
        "evidence": {
            "offline_egomotion_sha256": egomotion_sha256,
            "offline_sensor_extrinsics_sha256": offline_extrinsics_sha256,
        },
        "derivation": "INVERSE_EVENT_ANCHOR_POSE_COMPOSED_WITH_EVENT_POSE",
        "claim_scope": (
            "M16_REVIEW_EVENT_FRAME_TRANSFORM_NOT_GEOMETRIC_ASSOCIATION_OR_VEHICLE_SAFETY"
        ),
    }


def apply_verified_event_anchor_transforms(
    audit: dict[str, Any], transforms: Mapping[str, dict[str, Any]]
) -> dict[str, Any]:
    """Close only the coordinate-transform field for the exact audited event set."""
    result = deepcopy(audit)
    records = result.get("records")
    if not isinstance(records, list):
        raise ValueError("POST_REVIEW_AUDIT_RECORDS_INVALID")
    expected = [item.get("candidate_digest") for item in records]
    if (
        len(expected) != result.get("classified_event_count")
        or len(expected) != len(set(expected))
        or set(expected) != set(transforms)
    ):
        raise ValueError("EVENT_ANCHOR_TRANSFORM_EVENT_SET_MISMATCH")
    if any(item.get("status") != "AVAILABLE_SOURCE_LINKED" for item in transforms.values()):
        raise ValueError("EVENT_ANCHOR_TRANSFORM_NOT_VERIFIED")

    for record in records:
        transform = transforms[record["candidate_digest"]]
        record["coordinate_transform_status"] = "AVAILABLE_SOURCE_LINKED"
        record["coordinate_transform"] = transform
        record["field_status"]["verified_coordinate_transform"] = (
            "AVAILABLE_SOURCE_LINKED"
        )
        record["source_complete"] = False
        record["eligible"] = False
    result["status"] = "CURATOR_TRANSFORM_CLOSED_REMAINING_SOURCE_EVIDENCE_REQUIRED"
    result["verified_coordinate_transform_count"] = len(records)
    result["source_complete_8_of_8_count"] = 0
    result["newly_eligible_scene_count"] = 0
    remaining = dict(result["remaining_field_event_counts"])
    if remaining.pop("verified_coordinate_transform", None) != len(records):
        raise ValueError("PRIOR_TRANSFORM_REMAINING_COUNT_INVALID")
    result["remaining_field_event_counts"] = remaining
    return result


def public_event_anchor_transform_summary(audit: dict[str, Any]) -> dict[str, Any]:
    """Return a public aggregate without per-event identifiers or matrices."""
    return {key: value for key, value in audit.items() if key != "records"}
