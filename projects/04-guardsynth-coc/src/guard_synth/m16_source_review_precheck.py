"""Prepare the M16 source-review boundary without upgrading missing evidence."""

from __future__ import annotations

from collections import Counter
from typing import Any, Iterable


_NO_SELECTION_RULE = "NO_GENERAL_SELECTION_RULE_FAIL_CLOSED"


def audit_calibration_variant_sources(
    observations: Iterable[dict[str, Any]],
) -> dict[str, Any]:
    records = list(observations)
    if not records or not all(item.get("official_source") is True for item in records):
        raise ValueError("OFFICIAL_CALIBRATION_SOURCE_OBSERVATIONS_REQUIRED")
    general_rule = any(
        item.get("general_variant_selection_rule_documented") is True
        for item in records
    )
    return {
        "audit_version": "guardsynth-m16-calibration-variant-source-audit-v0.1",
        "official_source_count": len(records),
        "offline_optimized_feature_documented": any(
            item.get("offline_optimized_feature_documented") is True
            for item in records
        ),
        "general_variant_selection_rule_documented": general_rule,
        "offline_calibration_reader_supported_by_audited_devkit": any(
            item.get("offline_calibration_reader_supported") is True
            for item in records
        ),
        "open_maps_explicitly_absent": any(
            item.get("maps_included") is False for item in records
        ),
        "decision": (
            "DOCUMENTED_RULE_REQUIRES_PER_CLIP_VALIDATION"
            if general_rule
            else _NO_SELECTION_RULE
        ),
        "auto_closable_transform_count": 0,
        "records": records,
        "claim_scope": (
            "UPSTREAM_SOURCE_AUDIT_NOT_TRANSFORM_VALIDATION_OR_VEHICLE_SAFETY"
        ),
    }


def _records(queue: dict[str, Any], label: str) -> list[dict[str, Any]]:
    records = queue.get("records")
    if not isinstance(records, list):
        raise ValueError(f"{label}_RECORDS_INVALID")
    return records


def build_source_review_precheck(
    primary_queue: dict[str, Any],
    reserve_queue: dict[str, Any],
    calibration_source_audit: dict[str, Any],
) -> dict[str, Any]:
    if calibration_source_audit.get("decision") != _NO_SELECTION_RULE:
        raise ValueError("CALIBRATION_VARIANT_DECISION_NOT_FAIL_CLOSED")
    combined = [
        *(
            dict(
                item,
                cohort_role="PRIMARY",
                source_queue_artifact="ASSOCIATION_REVIEW_QUEUE.json",
                source_queue_record_index=index,
            )
            for index, item in enumerate(_records(primary_queue, "PRIMARY"))
        ),
        *(
            dict(
                item,
                cohort_role="RESERVE",
                source_queue_artifact="ATTRITION_RESERVE_REVIEW_QUEUE.json",
                source_queue_record_index=index,
            )
            for index, item in enumerate(_records(reserve_queue, "RESERVE"))
        ),
    ]
    digests = [item.get("candidate_digest") for item in combined]
    if any(not isinstance(digest, str) or not digest for digest in digests):
        raise ValueError("CANDIDATE_DIGEST_REQUIRED")
    if len(set(digests)) != len(digests):
        raise ValueError("DUPLICATE_CANDIDATE_DIGEST")

    records: list[dict[str, Any]] = []
    for item in sorted(combined, key=lambda record: record["candidate_digest"]):
        association_status = item.get("association_review_status", "")
        human_review_ready = association_status.startswith("REVIEWABLE_")
        geometry_source_required = (
            association_status == "INSUFFICIENT_SOURCE_GEOMETRY_FOR_ASSOCIATION"
            or association_status.endswith("_MISSING")
        )
        slice_name = item.get("shortlist_slice") or item.get("reserve_slice")
        if not slice_name:
            raise ValueError("CANDIDATE_SLICE_REQUIRED")
        records.append({
            "candidate_digest": item["candidate_digest"],
            "cohort_role": item["cohort_role"],
            "source_queue_artifact": item["source_queue_artifact"],
            "source_queue_record_index": item["source_queue_record_index"],
            "slice": slice_name,
            "country": item.get("country", "UNKNOWN"),
            "source_observation_counts": {
                key: int(item.get(key, 0))
                for key in (
                    "relevant_agent_keypoint_count",
                    "zone_keypoint_count",
                    "control_keypoint_count",
                    "obstacle_track_count_within_500ms",
                )
            },
            "association_precheck_status": association_status,
            "human_review_packet_ready": human_review_ready,
            "geometry_source_required": geometry_source_required,
            "coordinate_transform_status": (
                "REVIEW_REQUIRED_UPSTREAM_VARIANT_SELECTION_RULE"
            ),
            "rule_scope_status": (
                "REVIEW_REQUIRED_JURISDICTION_MATCHED_AUTHORITY"
            ),
            "outcome_status": "REVIEW_REQUIRED_LIFECYCLE_WITNESS",
            "human_review_tasks": (
                [
                    "OBSERVE_ACTOR_OR_CONTROL_ASSOCIATION_FROM_PROVIDED_FRAMES",
                    "OBSERVE_EVENT_TEMPORAL_STATE_FROM_PROVIDED_FRAMES",
                ]
                if human_review_ready
                else []
            ),
            "external_source_tasks": [
                "OBTAIN_UPSTREAM_CALIBRATION_VARIANT_SELECTION_RULE",
                "ACQUIRE_SOURCE_LINKED_LANE_OR_ZONE_GEOMETRY"
                if geometry_source_required
                else "VERIFY_EXISTING_SOURCE_LINKED_ZONE_GEOMETRY",
                "BIND_VERSIONED_JURISDICTION_MATCHED_OFFICIAL_AUTHORITY",
            ],
            "source_complete": False,
            "eligible": False,
            "final_outcome_assigned": False,
            "synthetic_required_field_fill": False,
        })

    statuses = Counter(item["association_precheck_status"] for item in records)
    return {
        "precheck_version": "guardsynth-m16-source-review-precheck-v0.1",
        "classified_event_count": len(records),
        "human_review_packet_count": sum(
            item["human_review_packet_ready"] for item in records
        ),
        "association_source_acquisition_required_count": sum(
            not item["human_review_packet_ready"] for item in records
        ),
        "geometry_source_required_count": sum(
            item["geometry_source_required"] for item in records
        ),
        "calibration_variant_decision": calibration_source_audit["decision"],
        "coordinate_transform_auto_closable_count": 0,
        "jurisdiction_authority_auto_closable_count": 0,
        "final_outcome_auto_closable_count": 0,
        "source_complete_8_of_8_count": 0,
        "final_outcome_assigned_count": 0,
        "newly_eligible_scene_count": 0,
        "association_precheck_status_counts": dict(sorted(statuses.items())),
        "records": records,
        "claim_scope": "SOURCE_REVIEW_PRECHECK_NOT_FINAL_ASSOCIATION_OR_SAFETY",
    }


def build_human_source_review_packet(precheck: dict[str, Any]) -> dict[str, Any]:
    records = [
        {
            "candidate_digest": item["candidate_digest"],
            "cohort_role": item["cohort_role"],
            "source_queue_artifact": item["source_queue_artifact"],
            "source_queue_record_index": item["source_queue_record_index"],
            "slice": item["slice"],
            "country": item["country"],
            "association_precheck_status": item["association_precheck_status"],
            "geometry_source_required": item["geometry_source_required"],
            "source_observation_counts": item["source_observation_counts"],
            "required_review_fields": {
                "visual_association_observation": None,
                "visual_temporal_observation": None,
                "reviewer_id": None,
                "notes": None,
            },
            "human_review_completed": False,
            "source_complete": False,
            "eligible": False,
        }
        for item in precheck.get("records", ())
        if item.get("human_review_packet_ready") is True
    ]
    if len(records) != precheck.get("human_review_packet_count"):
        raise ValueError("HUMAN_REVIEW_PACKET_COUNT_MISMATCH")
    return {
        "packet_version": "guardsynth-m16-human-source-review-packet-v0.2",
        "record_count": len(records),
        "review_completion_status": "NOT_STARTED",
        "human_review_completed_count": 0,
        "records": records,
        "claim_scope": "HUMAN_REVIEW_INPUT_NOT_COMPLETED_REVIEW_OR_SAFETY",
    }


def public_source_review_precheck_summary(precheck: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "precheck_version",
        "classified_event_count",
        "human_review_packet_count",
        "association_source_acquisition_required_count",
        "geometry_source_required_count",
        "calibration_variant_decision",
        "coordinate_transform_auto_closable_count",
        "jurisdiction_authority_auto_closable_count",
        "final_outcome_auto_closable_count",
        "source_complete_8_of_8_count",
        "final_outcome_assigned_count",
        "newly_eligible_scene_count",
        "association_precheck_status_counts",
        "claim_scope",
    )
    return {key: precheck[key] for key in keys}
