"""Fail-closed M16 source-closure audit after human video observation."""

from __future__ import annotations

from collections import Counter
import re
from typing import Any


POST_REVIEW_AUDIT_VERSION = "guardsynth-m16-post-review-source-closure-v0.1"
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
_REQUIRED_OFFLINE_FEATURES = (
    "egomotion",
    "sensor_extrinsics",
    "camera_intrinsics",
    "lidar_intrinsics",
)
_INTEGRITY_KEYS = (
    "packet_hash_match",
    "candidate_order_match",
    "image_hash_match",
    "json_csv_match",
)


def audit_ncore_offline_variant_rule(
    source_text: str,
    *,
    commit_sha: str,
    source_sha256: str,
    source_url: str,
) -> dict[str, Any]:
    """Recognize NVIDIA's pinned, explicit PhysicalAI offline-feature rule."""
    pinned_prefix = f"https://github.com/NVIDIA/ncore/blob/{commit_sha}/"
    if (
        _COMMIT_RE.fullmatch(commit_sha) is None
        or _SHA256_RE.fullmatch(source_sha256) is None
        or not source_url.startswith(pinned_prefix)
    ):
        raise ValueError("PINNED_OFFICIAL_NCORE_SOURCE_REQUIRED")

    required_anchors = (
        "REQUIRED_OFFLINE_FEATURES",
        "non-offline (raw) variants of these features are currently not supported",
        "_prefer_offline_feature",
        *[f'"{feature}"' for feature in _REQUIRED_OFFLINE_FEATURES],
    )
    if any(anchor not in source_text for anchor in required_anchors):
        raise ValueError("OFFLINE_VARIANT_RULE_ANCHORS_INCOMPLETE")
    return {
        "audit_version": "guardsynth-nvidia-ncore-offline-variant-rule-v0.1",
        "authority": "NVIDIA",
        "repository": "NVIDIA/ncore",
        "commit_sha": commit_sha,
        "source_url": source_url,
        "source_sha256": source_sha256,
        "required_offline_features": list(_REQUIRED_OFFLINE_FEATURES),
        "selected_variant": "offline",
        "decision": "OFFLINE_VARIANT_RULE_SOURCE_LINKED",
        "coordinate_transform_verified": False,
        "claim_scope": (
            "OFFICIAL_VARIANT_SELECTION_RULE_NOT_PER_EVENT_TRANSFORM_OR_VEHICLE_SAFETY"
        ),
    }


def _records(payload: dict[str, Any], label: str) -> list[dict[str, Any]]:
    records = payload.get("records")
    if not isinstance(records, list):
        raise ValueError(f"{label}_RECORDS_INVALID")
    return records


def _association_status(observation: str | None) -> str:
    return {
        "CLEAR_VISIBLE": "SOURCE_GEOMETRY_REQUIRED_AFTER_CLEAR_VISUAL_OBSERVATION",
        "AMBIGUOUS_VISIBLE": "SOURCE_GEOMETRY_AND_CURATOR_DISAMBIGUATION_REQUIRED",
        "NOT_OBSERVABLE": "SOURCE_GEOMETRY_REQUIRED_VISUAL_OBSERVATION_UNRESOLVED",
        None: "SOURCE_GEOMETRY_REQUIRED_BEFORE_HUMAN_OBSERVATION",
    }.get(observation, "INVALID_HUMAN_ASSOCIATION_OBSERVATION")


def _outcome_status(observation: str | None) -> str:
    if observation in {
        "HAZARD_VISIBLE",
        "NO_HAZARD_VISIBLE",
        "STATE_TRANSITION_VISIBLE",
    }:
        return "SOURCE_LIFECYCLE_WITNESS_REQUIRED_AFTER_VISUAL_OBSERVATION"
    if observation == "NOT_OBSERVABLE":
        return "SOURCE_LIFECYCLE_WITNESS_REQUIRED_VISUAL_OBSERVATION_UNRESOLVED"
    if observation is None:
        return "SOURCE_LIFECYCLE_WITNESS_REQUIRED_BEFORE_HUMAN_OBSERVATION"
    return "INVALID_HUMAN_TEMPORAL_OBSERVATION"


def build_post_review_source_closure(
    *,
    precheck: dict[str, Any],
    review_export: dict[str, Any],
    review_summary: dict[str, Any],
    variant_rule: dict[str, Any],
    evidence_counts: dict[str, int],
) -> dict[str, Any]:
    """Join 60 observations to 98 events without promoting non-source answers."""
    precheck_records = _records(precheck, "PRECHECK")
    review_records = _records(review_export, "HUMAN_REVIEW")
    classified_count = precheck.get("classified_event_count")
    human_packet_count = precheck.get("human_review_packet_count")
    if classified_count != len(precheck_records):
        raise ValueError("PRECHECK_CLASSIFIED_EVENT_COUNT_MISMATCH")
    if human_packet_count != sum(
        item.get("human_review_packet_ready") is True for item in precheck_records
    ):
        raise ValueError("PRECHECK_HUMAN_PACKET_COUNT_MISMATCH")
    digests = [item.get("candidate_digest") for item in precheck_records]
    if (
        any(not isinstance(item, str) or not item for item in digests)
        or len(set(digests)) != len(digests)
    ):
        raise ValueError("PRECHECK_CANDIDATE_DIGEST_INVALID_OR_DUPLICATE")

    if (
        review_summary.get("status") != "HUMAN_VIDEO_OBSERVATION_COMPLETE"
        or review_summary.get("review_record_count") != len(review_records)
        or review_summary.get("human_review_completed_count") != len(review_records)
        or any(review_summary.get(key) is not True for key in _INTEGRITY_KEYS)
    ):
        raise ValueError("HUMAN_REVIEW_INTEGRITY_NOT_COMPLETE")
    expected_reviewed = {
        item["candidate_digest"]
        for item in precheck_records
        if item.get("human_review_packet_ready") is True
    }
    actual_reviewed = [item.get("candidate_digest") for item in review_records]
    if (
        len(actual_reviewed) != len(set(actual_reviewed))
        or set(actual_reviewed) != expected_reviewed
        or len(actual_reviewed) != human_packet_count
    ):
        raise ValueError("HUMAN_REVIEW_CANDIDATE_SET_MISMATCH")
    review_by_digest = {item["candidate_digest"]: item for item in review_records}

    if (
        variant_rule.get("decision") != "OFFLINE_VARIANT_RULE_SOURCE_LINKED"
        or variant_rule.get("selected_variant") != "offline"
    ):
        raise ValueError("CALIBRATION_VARIANT_RULE_NOT_SOURCE_LINKED")
    for key in ("temporal_closure", "calibration_5_of_5", "recorded_rig_binding"):
        if evidence_counts.get(key) != classified_count:
            raise ValueError(f"CLASSIFIED_EVIDENCE_COUNT_MISMATCH:{key}")

    records: list[dict[str, Any]] = []
    for item in precheck_records:
        observation = review_by_digest.get(item["candidate_digest"])
        association = (
            observation.get("visual_association_observation")
            if observation is not None
            else None
        )
        temporal = (
            observation.get("visual_temporal_observation")
            if observation is not None
            else None
        )
        records.append({
            "candidate_digest": item["candidate_digest"],
            "cohort_role": item.get("cohort_role"),
            "slice": item.get("slice"),
            "country": item.get("country"),
            "human_observation_status": (
                "COMPLETED" if observation is not None
                else "NOT_REQUESTED_SOURCE_GEOMETRY_FIRST"
            ),
            "visual_association_observation": association,
            "visual_temporal_observation": temporal,
            "association_source_status": _association_status(association),
            "outcome_source_status": _outcome_status(temporal),
            "calibration_variant_status": "OFFLINE_VARIANT_SOURCE_LINKED",
            "coordinate_transform_status": "REVIEW_REQUIRED_MODEL_T0_BINDING_AND_NUMERIC_CLOSURE",
            "rule_scope_status": "REVIEW_REQUIRED_JURISDICTION_MATCHED_AUTHORITY",
            "field_status": {
                "timestamps": "AVAILABLE_SOURCE_LINKED",
                "ego_pose_and_speed": "AVAILABLE_SOURCE_LINKED",
                "relevant_actor_or_control_state": "REVIEW_REQUIRED_SOURCE_ASSOCIATION",
                "target_zone_or_lane_association": "REVIEW_REQUIRED_SOURCE_GEOMETRY",
                "conflict_stop_or_following_geometry": "REVIEW_REQUIRED_SOURCE_GEOMETRY",
                "verified_coordinate_transform": "REVIEW_REQUIRED_MODEL_T0_BINDING_AND_NUMERIC_CLOSURE",
                "applicable_rule_scope": "REVIEW_REQUIRED_JURISDICTION_MATCHED_AUTHORITY",
                "recorded_rig_binding": "AVAILABLE_SOURCE_LINKED",
            },
            "final_outcome_assigned": False,
            "source_complete": False,
            "eligible": False,
            "synthetic_required_field_fill": False,
        })

    association_counts = Counter(
        item["visual_association_observation"]
        for item in records
        if item["visual_association_observation"] is not None
    )
    temporal_counts = Counter(
        item["visual_temporal_observation"]
        for item in records
        if item["visual_temporal_observation"] is not None
    )
    slice_counts = Counter(str(item["slice"]) for item in records)
    return {
        "audit_version": POST_REVIEW_AUDIT_VERSION,
        "status": "CURATOR_SOURCE_CLOSURE_AUDITED_REMAINING_EVIDENCE_REQUIRED",
        "classified_event_count": classified_count,
        "human_observation_completed_count": len(review_records),
        "human_observation_deferred_source_first_count": classified_count - len(review_records),
        "human_observation_integrity_verified": True,
        "association_observation_counts": dict(sorted(association_counts.items())),
        "temporal_observation_counts": dict(sorted(temporal_counts.items())),
        "slice_candidate_counts": dict(sorted(slice_counts.items())),
        "temporal_closure_count": classified_count,
        "calibration_5_of_5_count": classified_count,
        "recorded_rig_binding_count": classified_count,
        "calibration_variant_selection_closed_count": classified_count,
        "selected_calibration_variant": "offline",
        "verified_coordinate_transform_count": 0,
        "source_complete_8_of_8_count": 0,
        "final_outcome_assigned_count": 0,
        "newly_eligible_scene_count": 0,
        "remaining_field_event_counts": {
            "relevant_actor_or_control_state": classified_count,
            "target_zone_or_lane_association": classified_count,
            "conflict_stop_or_following_geometry": classified_count,
            "verified_coordinate_transform": classified_count,
            "applicable_rule_scope": classified_count,
            "outcome_lifecycle_witness": classified_count,
        },
        "annotation_start_allowed": False,
        "synthetic_required_field_fill_count": 0,
        "records": records,
        "claim_scope": (
            "POST_REVIEW_SOURCE_CLOSURE_AUDIT_NOT_FINAL_ASSOCIATION_EXPERT_EFFECT_OR_VEHICLE_SAFETY"
        ),
    }


def public_post_review_source_closure_summary(audit: dict[str, Any]) -> dict[str, Any]:
    """Remove restricted per-event and human identity details."""
    return {
        key: value
        for key, value in audit.items()
        if key != "records"
    }
