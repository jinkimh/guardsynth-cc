"""Aggregate contracts for event-level M16 attrition reserve auditing."""

from __future__ import annotations

from collections import Counter
from typing import Any, Iterable


def public_attrition_reserve_summary(
    records: Iterable[dict[str, Any]],
) -> dict[str, Any]:
    """Return a deidentified summary without promoting candidates to eligible scenes."""
    items = list(records)
    tiers = Counter(str(item["reserve_tier"]) for item in items)
    associations = Counter(str(item["association_review_status"]) for item in items)
    return {
        "audit_version": "guardsynth-m16-attrition-reserve-event-audit-v0.1",
        "audited_reserve_event_count": len(items),
        "temporal_closure_event_count": sum(item["temporal_closure"] for item in items),
        "calibration_5_of_5_event_count": sum(
            item["calibration_closure"] == "5_OF_5" for item in items
        ),
        "recorded_rig_binding_available_event_count": sum(
            item["recorded_rig_binding_status"] == "AVAILABLE_SOURCE_LINKED"
            for item in items
        ),
        "verified_coordinate_transform_event_count": sum(
            item["coordinate_transform_status"] == "AVAILABLE_SOURCE_LINKED"
            for item in items
        ),
        "reserve_tier_counts": dict(sorted(tiers.items())),
        "association_review_status_counts": dict(sorted(associations.items())),
        "source_complete_8_of_8_event_count": 0,
        "final_outcome_assigned_count": 0,
        "newly_eligible_scene_count": 0,
        "claim_scope": "ATTRITION_RESERVE_EVENT_EVIDENCE_NOT_SCENE_ELIGIBILITY_OR_SAFETY",
    }
