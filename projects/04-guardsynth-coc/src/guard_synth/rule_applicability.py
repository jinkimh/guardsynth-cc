"""Bind official rule sources to observed scene conditions without using CoC as fact."""

from __future__ import annotations

from typing import Any
from urllib.parse import urlparse


RULE_APPLICABILITY_VERSION = "guardsynth-rule-applicability-v0.1"
LOCALIZATION_STATUS = "INFERRED_HIGH_CONFIDENCE_NOT_DATASET_GPS"


def _review_required(scene_ref: str, reason_code: str) -> dict[str, Any]:
    return {
        "rule_applicability_version": RULE_APPLICABILITY_VERSION,
        "scene_ref": scene_ref,
        "status": "REVIEW_REQUIRED",
        "reason_code": reason_code,
        "applicability_verdict": "NOT_ESTABLISHED",
        "unsourced_normative_or_numeric_value_count": 0,
        "vehicle_safety_validated": False,
    }


def _valid_sha256(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _validate_rule_sources(rule_sources: list[dict[str, Any]]) -> None:
    if not rule_sources:
        raise ValueError("MISSING_RULE_SOURCES")
    source_ids: set[str] = set()
    for source in rule_sources:
        source_id = source.get("source_id")
        url = source.get("official_url")
        if not isinstance(source_id, str) or not source_id or source_id in source_ids:
            raise ValueError("INVALID_RULE_SOURCE_ID")
        source_ids.add(source_id)
        if not (
            isinstance(url, str)
            and urlparse(url).scheme == "https"
            and urlparse(url).hostname == "leginfo.legislature.ca.gov"
            and _valid_sha256(source.get("snapshot_sha256"))
            and source.get("authority") == "California Legislature"
            and source.get("jurisdiction") == "California"
            and isinstance(source.get("section"), str)
            and isinstance(source.get("role"), str)
        ):
            raise ValueError("INVALID_OR_NONOFFICIAL_RULE_SOURCE")
    if "CA-VEH-21950" not in source_ids:
        raise ValueError("MISSING_PRIMARY_CROSSWALK_RULE")


def build_rule_applicability_evidence(
    *,
    scene_ref: str,
    dataset_country: str,
    packet: dict[str, Any],
    association: dict[str, Any],
    localization: dict[str, Any],
    rule_sources: list[dict[str, Any]],
) -> dict[str, Any]:
    """Create conditional applicability evidence for California crosswalk rules."""
    if not isinstance(scene_ref, str) or not scene_ref:
        raise ValueError("INVALID_SCENE_REF")
    if packet.get("scene_ref") != scene_ref or association.get("scene_ref") != scene_ref:
        raise ValueError("SCENE_EVIDENCE_MISMATCH")
    _validate_rule_sources(rule_sources)
    if dataset_country != "United States" or localization.get("country") != dataset_country:
        raise ValueError("DATASET_LOCALIZATION_COUNTRY_MISMATCH")

    if (
        localization.get("status") != LOCALIZATION_STATUS
        or localization.get("administrative_area") != "California"
        or localization.get("locality") != "San Francisco"
        or not isinstance(localization.get("evidence_refs"), list)
        or not localization["evidence_refs"]
    ):
        return _review_required(scene_ref, "INSUFFICIENT_JURISDICTION_LOCALIZATION")

    observations = packet.get("observations")
    review = packet.get("review_evidence")
    if not isinstance(observations, dict) or not isinstance(review, dict):
        return _review_required(scene_ref, "MISSING_HUMAN_SCENE_REVIEW")
    if (
        review.get("evidence_kind") != "HUMAN_REVIEWED_IMAGE_CLAIM"
        or observations.get("review_confidence") != "HIGH"
        or observations.get("candidate_region") != "CROSSWALK_VISIBLE"
        or observations.get("primary_situation") != "ROAD_USER_IN_EGO_PATH"
        or observations.get("subject_region_relation") != "IN_CONFLICT_REGION"
    ):
        return _review_required(scene_ref, "CROSSWALK_APPLICABILITY_NOT_OBSERVED")
    track_ids = association.get("associated_track_id_sha256")
    if not (
        association.get("status") == "AVAILABLE_SOURCE_LINKED"
        and association.get("target_kind") == "SET"
        and isinstance(track_ids, list)
        and len(track_ids) == association.get("association_cardinality")
        and bool(track_ids)
    ):
        return _review_required(scene_ref, "MISSING_SOURCE_LINKED_ACTOR_ASSOCIATION")

    return {
        "rule_applicability_version": RULE_APPLICABILITY_VERSION,
        "scene_ref": scene_ref,
        "status": "AVAILABLE_SOURCE_LINKED",
        "reason_code": None,
        "applicability_verdict": "CONDITIONALLY_APPLICABLE",
        "primary_rule_source_id": "CA-VEH-21950",
        "jurisdiction_binding": {
            "country": dataset_country,
            "administrative_area": "California",
            "locality": "San Francisco",
            "intersection_hypothesis": str(
                localization.get("intersection_hypothesis", "")
            ),
            "status": LOCALIZATION_STATUS,
            "method": str(localization.get("method", "")),
            "evidence_refs": list(localization["evidence_refs"]),
            "independent_dataset_gps_confirmation": bool(
                localization.get("independent_dataset_gps_confirmation", False)
            ),
        },
        "rule_source_refs": [dict(source) for source in rule_sources],
        "observed_applicability_conditions": [
            "HUMAN_REVIEWED_CROSSWALK_VISIBLE",
            "HUMAN_REVIEWED_ROAD_USER_IN_CONFLICT_REGION",
            "SOURCE_LINKED_ACTOR_SET_IN_EGO_CORRIDOR",
        ],
        "exception_handling": {
            "source_id": "CA-VEH-21954",
            "status": "NOT_ACTIVATED_BY_CURRENT_CROSSWALK_VISIBLE_EVIDENCE",
            "unknown_crosswalk_policy": "REVIEW_REQUIRED",
        },
        "coc_used_as_observed_or_normative_fact": False,
        "numeric_vehicle_bound_derived": False,
        "unsourced_normative_or_numeric_value_count": 0,
        "vehicle_safety_validated": False,
        "claim_scope": "OFFICIAL_RULE_SOURCE_AND_CONDITIONAL_SCENE_APPLICABILITY_WITH_IMAGE_CUE_LOCALIZATION_NOT_GPS_LEGAL_ADVICE_NUMERIC_BOUND_OR_VEHICLE_SAFETY",
    }
