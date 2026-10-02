"""Fail-closed calibration and association review contracts for M16."""

from __future__ import annotations

from collections import Counter
import math
from typing import Any, Iterable


def extrinsics_variant_delta(online: dict[str, float], offline: dict[str, float]) -> dict[str, float]:
    translation_delta = math.sqrt(
        sum((float(online[key]) - float(offline[key])) ** 2 for key in ("x", "y", "z"))
    )
    first = [float(online[key]) for key in ("qx", "qy", "qz", "qw")]
    second = [float(offline[key]) for key in ("qx", "qy", "qz", "qw")]
    first_norm = math.sqrt(sum(value * value for value in first))
    second_norm = math.sqrt(sum(value * value for value in second))
    dot = abs(sum(a * b for a, b in zip(first, second)) / (first_norm * second_norm))
    rotation_delta = 2 * math.acos(min(1.0, dot))
    return {
        "translation_delta_m": translation_delta,
        "rotation_delta_rad": rotation_delta,
    }


def association_review_status(
    *,
    slice_name: str,
    relevant_agent_keypoints: int,
    zone_keypoints: int,
    control_keypoints: int,
    obstacle_tracks: int,
) -> str:
    if slice_name == "PEDESTRIAN_CYCLIST_YIELD":
        if relevant_agent_keypoints and zone_keypoints and obstacle_tracks:
            return "REVIEWABLE_ACTOR_ZONE_ASSOCIATION"
        if relevant_agent_keypoints and obstacle_tracks:
            return "REVIEWABLE_ACTOR_ASSOCIATION_ZONE_MISSING"
    if slice_name == "FOLLOWING_CUT_IN" and relevant_agent_keypoints and obstacle_tracks:
        return "REVIEWABLE_ACTOR_ASSOCIATION_LANE_MISSING"
    if slice_name == "STOP_SIGNALS" and control_keypoints:
        return "REVIEWABLE_CONTROL_ASSOCIATION_LANE_MISSING"
    return "INSUFFICIENT_SOURCE_GEOMETRY_FOR_ASSOCIATION"


def public_calibration_association_summary(
    calibration_records: Iterable[dict[str, Any]], queue_records: Iterable[dict[str, Any]]
) -> dict[str, Any]:
    calibration = list(calibration_records)
    queue = list(queue_records)
    statuses = Counter(item["association_review_status"] for item in queue)
    return {
        "audit_version": "guardsynth-m16-calibration-association-audit-v0.1",
        "calibration_candidate_count": len(calibration),
        "calibration_5_of_5_candidate_count": sum(
            item["calibration_closure"] == "5_OF_5" for item in calibration
        ),
        "recorded_rig_binding_available_count": sum(
            item["recorded_rig_binding_status"] == "AVAILABLE_SOURCE_LINKED"
            for item in calibration
        ),
        "verified_coordinate_transform_count": sum(
            item["coordinate_transform_status"] == "AVAILABLE_SOURCE_LINKED"
            for item in calibration
        ),
        "calibration_variant_review_count": sum(
            item["coordinate_transform_status"]
            == "REVIEW_REQUIRED_ONLINE_OFFLINE_VARIANT_SELECTION"
            for item in calibration
        ),
        "association_queue_candidate_count": len(queue),
        "association_review_status_counts": dict(sorted(statuses.items())),
        "source_complete_8_of_8_candidate_count": 0,
        "final_outcome_assigned_count": 0,
        "newly_eligible_candidate_count": 0,
        "claim_scope": "CALIBRATION_AND_ASSOCIATION_REVIEW_QUEUE_NOT_VEHICLE_SAFETY",
    }
