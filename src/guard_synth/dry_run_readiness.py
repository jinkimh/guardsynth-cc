"""Build and assess the locked 24-slot real-scene dry-run plan."""

from __future__ import annotations

from typing import Any

from .source_catalog import SourceCatalog, audit_source_catalog


DRY_RUN_READINESS_VERSION = "guardsynth-24-scene-readiness-v0.1"
SLICE_ORDER = (
    "PEDESTRIAN_CYCLIST_YIELD",
    "STOP_SIGNALS",
    "FOLLOWING_CUT_IN",
)
STRATA = (
    "HAZARD_VISIBLE",
    "HAZARD_OCCLUDED_OR_REAPPEARING",
    "NOMINAL_CLEAR",
    "RELEASE_OR_REACTIVATION",
)
REQUIRED_SCENE_FIELDS = (
    "timestamps",
    "ego_pose_and_speed",
    "relevant_actor_tracks",
    "target_zone_or_lane_association",
    "conflict_or_stop_geometry",
    "verified_coordinate_transform",
    "applicable_rule_source_refs",
    "exact_vehicle_binding",
    "source_bearing_vehicle_assurance_profile",
)


def build_twenty_four_slot_plan() -> list[dict[str, Any]]:
    slots: list[dict[str, Any]] = []
    for slice_index, slice_name in enumerate(SLICE_ORDER):
        for local_index in range(8):
            slots.append({
                "slot_id": f"S{slice_index + 1}-{local_index + 1:02d}",
                "slice": slice_name,
                "stratum": STRATA[local_index % len(STRATA)],
                "real_scene_ref": None,
                "source_complete": False,
                "synthetic_fill": False,
                "status": "UNASSIGNED_REAL_INPUT",
            })
    return slots


def assess_dry_run_readiness(
    catalog: SourceCatalog,
    legacy_public_aggregate: dict[str, Any],
) -> dict[str, Any]:
    catalog_audit = audit_source_catalog(catalog)
    previous = legacy_public_aggregate["readiness_summary"]
    slots = build_twenty_four_slot_plan()
    blockers = {
        "MISSING_SOURCE_COMPLETE_SCENE_SLOTS": len(slots),
        "MISSING_SCENE_INPUT": previous.get("missing_scene_input_slot_count", 0),
        "MISSING_OR_AMBIGUOUS_TARGET_ZONE_ASSOCIATION": previous.get(
            "reason_code_counts", {}
        ).get("MISSING_OR_AMBIGUOUS_TARGET_ZONE_ASSOCIATION", 0),
        "UNVERIFIED_COORDINATE_TRANSFORM": previous.get(
            "reason_code_counts", {}
        ).get("UNVERIFIED_COORDINATE_TRANSFORM", 0),
        "MISSING_VEHICLE_ASSURANCE_PROFILE": previous.get(
            "reason_code_counts", {}
        ).get("MISSING_VEHICLE_ASSURANCE_PROFILE", 0),
    }
    return {
        "readiness_version": DRY_RUN_READINESS_VERSION,
        "status": "BLOCKED_INPUT",
        "decision": "M13_BLOCKED_SOURCE_COMPLETE_SCENES",
        "slot_count": len(slots),
        "slots_per_slice": 8,
        "slot_plan": slots,
        "required_scene_fields": list(REQUIRED_SCENE_FIELDS),
        "catalog_gate": {
            "ready": (
                catalog_audit["rule_template_count"] >= 12
                and catalog_audit["family_coverage_count"] == 6
                and catalog_audit["unsourced_normative_or_numeric_value_count"] == 0
            ),
            "catalog_id": catalog_audit["catalog_id"],
            "rule_template_count": catalog_audit["rule_template_count"],
        },
        "input_readiness": {
            "actual_candidate_event_count": previous.get("actual_candidate_event_count", 0),
            "adapted_candidate_count": previous.get("adapted_candidate_count", 0),
            "source_complete_scene_count": previous.get("source_complete_scene_count", 0),
            "source_complete_required": len(slots),
            "synthetic_scene_fill_performed": False,
        },
        "blockers": blockers,
        "execution": {
            "guardsynth_eblc_core_z3_scene_runs": 0,
            "reason": "No source-complete real scene input; execution was not fabricated.",
        },
        "claim_scope": "M13_SLOT_AND_INPUT_READINESS_NOT_REAL_SCENE_EXECUTION_ASSOCIATION_ACCURACY_OR_VEHICLE_SAFETY",
    }

