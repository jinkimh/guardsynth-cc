"""Fail-closed evidence audit for materialized M16 sensor members."""

from __future__ import annotations

from collections import Counter
import math
from typing import Any, Iterable


TIME_STREAMS = (
    "camera_frame_timestamps",
    "egomotion",
    "egomotion_offline",
    "obstacle_offline",
)
FIELD_STATUS_TEMPLATE = {
    "relevant_actor_or_control_state": "REVIEW_REQUIRED_ANNOTATION_SENSOR_ASSOCIATION",
    "target_zone_or_lane_association": "REVIEW_REQUIRED_MAP_OR_LANE_ASSOCIATION",
    "conflict_stop_or_following_geometry": "REVIEW_REQUIRED_RELEVANT_ACTOR_GEOMETRY",
    "verified_coordinate_transform": "UNSUPPORTED_SENSOR_EXTRINSICS_NOT_MATERIALIZED",
    "applicable_rule_scope": "REVIEW_REQUIRED_JURISDICTION_MATCHED_RULE_SOURCE",
    "recorded_rig_binding": "UNSUPPORTED_CALIBRATION_RIG_BINDING_NOT_MATERIALIZED",
}


def audit_timestamp_series(values: Iterable[Any], event_timestamp_us: int) -> dict[str, Any]:
    timestamps = list(values)
    valid = (
        bool(timestamps)
        and all(isinstance(value, int) and not isinstance(value, bool) for value in timestamps)
        and all(right >= left for left, right in zip(timestamps, timestamps[1:]))
    )
    if not valid:
        return {
            "status": "INVALID_OR_NON_MONOTONIC",
            "row_count": len(timestamps),
            "event_covered": False,
        }
    start = timestamps[0]
    end = timestamps[-1]
    return {
        "status": "TIME_ALIGNED" if start <= event_timestamp_us <= end else "EVENT_OUT_OF_RANGE",
        "row_count": len(timestamps),
        "timestamp_min_us": start,
        "timestamp_max_us": end,
        "event_covered": start <= event_timestamp_us <= end,
        "nearest_event_delta_us": min(abs(value - event_timestamp_us) for value in timestamps),
    }


def field_status(*, temporal_closure: bool, ego_speed_finite: bool) -> dict[str, str]:
    statuses = dict(FIELD_STATUS_TEMPLATE)
    statuses["timestamps"] = (
        "AVAILABLE_SOURCE_LINKED" if temporal_closure else "UNSUPPORTED_TEMPORAL_CLOSURE"
    )
    statuses["ego_pose_and_speed"] = (
        "AVAILABLE_SOURCE_LINKED"
        if temporal_closure and ego_speed_finite
        else "UNSUPPORTED_EGOMOTION_AT_EVENT"
    )
    return statuses


def speed_norm(vx: Any, vy: Any, vz: Any) -> float | None:
    if not all(
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
        for value in (vx, vy, vz)
    ):
        return None
    return math.sqrt(float(vx) ** 2 + float(vy) ** 2 + float(vz) ** 2)


def public_sensor_audit_summary(records: Iterable[dict[str, Any]]) -> dict[str, Any]:
    items = list(records)
    field_counts: Counter[str] = Counter()
    for item in items:
        for field, status in item["field_status"].items():
            if status == "AVAILABLE_SOURCE_LINKED":
                field_counts[field] += 1
    return {
        "audit_version": "guardsynth-m16-materialized-sensor-evidence-audit-v0.1",
        "audited_candidate_count": len(items),
        "member_complete_candidate_count": sum(
            item["member_closure"] == "6_OF_6" for item in items
        ),
        "temporal_closure_candidate_count": sum(item["temporal_closure"] for item in items),
        "source_complete_8_of_8_candidate_count": sum(item["source_complete"] for item in items),
        "newly_eligible_candidate_count": 0,
        "final_outcome_assigned_count": 0,
        "available_field_candidate_counts": dict(sorted(field_counts.items())),
        "outcome_status": "REVIEW_REQUIRED_SENSOR_AND_NORMATIVE_CLOSURE",
        "claim_scope": "SENSOR_EVIDENCE_COVERAGE_NOT_SCENE_ELIGIBILITY_OR_VEHICLE_SAFETY",
    }
