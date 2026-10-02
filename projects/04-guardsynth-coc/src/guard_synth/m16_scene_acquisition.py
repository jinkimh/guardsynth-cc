"""Fail-closed M16 per-scene eligibility, slot binding, and preflight."""

from __future__ import annotations

from collections import Counter
from copy import deepcopy
from math import isfinite
import re
from typing import Any, Iterable

from .expert_pilot_protocol import OUTCOMES, SLICES, pilot_design


ELIGIBILITY_VERSION = "guardsynth-m16-scene-eligibility-v0.2"
REQUIRED_EVIDENCE_FIELDS = (
    "timestamps",
    "ego_pose_and_speed",
    "relevant_actor_or_control_state",
    "target_zone_or_lane_association",
    "conflict_stop_or_following_geometry",
    "verified_coordinate_transform",
    "applicable_rule_scope",
    "recorded_rig_binding",
)
FIELD_STATUS_VALUES = {
    "AVAILABLE_SOURCE_LINKED",
    "REVIEW_REQUIRED",
    "UNSUPPORTED",
    "CONFLICT",
}
SCOPE_COMPATIBILITY_VALUES = {
    "JURISDICTION_SOURCE_COMPATIBLE",
    "TREATY_NORMATIVE_BASELINE_COMPATIBLE",
    "EXCLUDED_JURISDICTION_OR_ODD_MISMATCH",
    "REVIEW_REQUIRED_JURISDICTION_EVIDENCE",
}
_EXPECTED_FRAME_UNIT = {
    "timestamps": ("DATASET_TIME", "us"),
    "ego_pose_and_speed": ("EGO_AT_MODEL_T0", "m_and_mps"),
    "relevant_actor_or_control_state": ("DATASET_RIG", "m_and_us"),
    "target_zone_or_lane_association": ("DATASET_RIG", "set_membership"),
    "conflict_stop_or_following_geometry": ("DATASET_RIG", "m"),
    "verified_coordinate_transform": (
        "DATASET_RIG_TO_EGO_AT_MODEL_T0",
        "rigid_transform",
    ),
    "applicable_rule_scope": ("NORMATIVE_SCOPE", "not_applicable"),
    "recorded_rig_binding": ("RECORDED_RIG", "not_applicable"),
}
_HASH_RE = re.compile(r"^(scene|event|content|source)-sha256:[0-9a-f]{64}$")
_RESTRICTED_REF_RE = re.compile(r"^restricted-sha256:[0-9a-f]{64}(?:#.*)?$")
_FORBIDDEN_PUBLIC_KEYS = {
    "clip_id",
    "raw_identifier",
    "raw_path",
    "source_path",
    "coc",
    "coc_text",
    "coc_full_text",
}


def _source_ref(value: Any) -> bool:
    return isinstance(value, str) and _RESTRICTED_REF_RE.fullmatch(value) is not None


def _strictly_increasing(values: Any) -> bool:
    return (
        isinstance(values, list)
        and bool(values)
        and all(isinstance(value, int) and not isinstance(value, bool) for value in values)
        and all(right > left for left, right in zip(values, values[1:]))
    )


def _field_reasons(field_name: str, field: Any) -> list[str]:
    if not isinstance(field, dict):
        return [f"MISSING_REQUIRED_FIELD:{field_name}"]
    status = field.get("status")
    if status not in FIELD_STATUS_VALUES:
        return [f"INVALID_FIELD_STATUS:{field_name}"]
    if status != "AVAILABLE_SOURCE_LINKED":
        reason = field.get("reason_code")
        return [
            str(reason) if isinstance(reason, str) and reason else f"FIELD_NOT_SOURCE_LINKED:{field_name}"
        ]
    reasons: list[str] = []
    if not _source_ref(field.get("evidence_ref")):
        reasons.append(f"UNSOURCED_REQUIRED_FIELD:{field_name}")
    if field.get("freshness_status") not in {"CURRENT", "NOT_TIME_VARYING"}:
        reasons.append(f"INVALID_FRESHNESS:{field_name}")
    expected_frame, expected_unit = _EXPECTED_FRAME_UNIT[field_name]
    if field.get("frame") != expected_frame:
        reasons.append(f"INVALID_FRAME:{field_name}")
    if field.get("unit") != expected_unit:
        reasons.append(f"INVALID_UNIT:{field_name}")
    if field_name == "timestamps" and not _strictly_increasing(field.get("timestamps_us")):
        reasons.append("NON_MONOTONIC_OR_INVALID_TIMESTAMPS")
    if (
        field_name == "relevant_actor_or_control_state"
        and field.get("time_continuous") is not True
    ):
        reasons.append("ACTOR_OR_CONTROL_STATE_NOT_TIME_CONTINUOUS")
    if (
        field_name == "target_zone_or_lane_association"
        and field.get("ambiguity_status") != "UNAMBIGUOUS_SOURCE_LINKED"
    ):
        reasons.append(str(field.get("reason_code") or "TARGET_ZONE_AMBIGUOUS"))
    if field_name == "verified_coordinate_transform":
        error = field.get("inverse_closure_max_abs_error")
        if (
            isinstance(error, bool)
            or not isinstance(error, (int, float))
            or not isfinite(error)
            or not 0 <= float(error) <= 1e-9
        ):
            reasons.append("INVALID_COORDINATE_TRANSFORM_CLOSURE")
    if (
        field_name == "applicable_rule_scope"
        and field.get("scope_precondition_exception_status") != "SATISFIED"
    ):
        reasons.append("RULE_SCOPE_PRECONDITION_EXCEPTION_NOT_SATISFIED")
    return reasons


def _outcome_witness_valid(record: dict[str, Any]) -> bool:
    outcome = record.get("outcome")
    evidence = record.get("outcome_evidence")
    if not isinstance(evidence, dict):
        return False
    refs = evidence.get("evidence_refs")
    valid_refs = (
        isinstance(refs, list)
        and bool(refs)
        and len(refs) == len(set(refs))
        and all(_source_ref(ref) for ref in refs)
    )
    if not valid_refs or evidence.get("source_packet_complete") is not True:
        return False
    if outcome == "HAZARD_TRUE_ACTIVE":
        return (
            evidence.get("kind") == "ACTIVE_HAZARD_WITNESS"
            and evidence.get("time_continuous") is True
            and evidence.get("lifecycle_states") == ["ACTIVE"]
        )
    if outcome == "NOMINAL":
        return (
            evidence.get("kind") == "SAFE_PROGRESS_WITNESS"
            and evidence.get("relevant_scene_confirmed") is True
            and evidence.get("safe_progress_confirmed") is True
        )
    if outcome == "UNKNOWN":
        return (
            evidence.get("kind") == "APPROVED_OBSERVABILITY_RESULT"
            and evidence.get("freshness_result") == "STALE_APPROVED_UNKNOWN"
        )
    if outcome == "CONFLICT":
        return evidence.get("kind") == "SOURCE_CONFLICT" and len(refs) >= 2
    states = evidence.get("lifecycle_states")
    timestamps = evidence.get("lifecycle_timestamps_us")
    if evidence.get("kind") != "LIFECYCLE_WITNESS" or not _strictly_increasing(timestamps):
        return False
    if outcome == "RELEASE":
        return states == ["ACTIVE", "RELEASED"] and len(timestamps) == 2
    if outcome == "REACTIVATION":
        return (
            states == ["ACTIVE", "RELEASED", "REACTIVATED"]
            and len(timestamps) == 3
        )
    return False


def _scope_reasons(record: dict[str, Any]) -> list[str]:
    reasons: list[str] = []
    scope = record.get("scope_compatibility")
    if scope not in SCOPE_COMPATIBILITY_VALUES:
        reasons.append("INVALID_SCOPE_COMPATIBILITY_STATUS")
    jurisdiction = record.get("jurisdiction", {})
    odd = record.get("odd", {})
    catalog = record.get("rule_catalog", {})
    country = jurisdiction.get("country_code")
    subdivision = jurisdiction.get("subdivision_code")
    authority_class = catalog.get("authority_class")
    catalog_country = catalog.get("jurisdiction_country_code")
    legal_source_valid = (
        authority_class == "LEGAL"
        and catalog_country == country
        and catalog.get("source_status") == "OFFICIAL_SOURCE_LINKED"
    )
    system_source_valid = (
        authority_class == "VERIFIED_SYSTEM_REQUIREMENT"
        and catalog_country in {country, "ANY"}
        and catalog.get("source_status") == "VERIFIED_SOURCE_LINKED"
    )
    treaty_source_valid = (
        authority_class == "INTERNATIONAL_TREATY_NORMATIVE_BASELINE"
        and catalog_country == "MULTI"
        and country in set(catalog.get("treaty_participant_country_codes", ()))
        and catalog.get("source_status") == "OFFICIAL_TREATY_SOURCE_LINKED"
        and catalog.get("rule_strength")
        in {"DIRECT_TREATY_RULE", "GENERAL_DUE_CARE_FALLBACK"}
        and catalog.get("legal_compliance_claim") == "NOT_PERMITTED"
    )
    expected_scope = (
        "TREATY_NORMATIVE_BASELINE_COMPATIBLE"
        if treaty_source_valid
        else "JURISDICTION_SOURCE_COMPATIBLE"
    )
    if any((
        scope != expected_scope,
        not isinstance(country, str) or re.fullmatch(r"[A-Z]{2}", country) is None,
        subdivision is not None
        and (
            not isinstance(subdivision, str)
            or not subdivision.startswith(f"{country}-")
        ),
        odd.get("status") != "IN_SCOPE",
        not isinstance(odd.get("scope_id"), str)
        or odd.get("scope_id") in {"", "UNKNOWN", "REVIEW_REQUIRED"},
        not isinstance(catalog.get("catalog_id"), str)
        or not catalog.get("catalog_id"),
        not isinstance(catalog.get("version"), str)
        or not catalog.get("version"),
        not legal_source_valid and not system_source_valid and not treaty_source_valid,
    )):
        reasons.append("JURISDICTION_SOURCE_SCOPE_MISMATCH")
    for key in ("jurisdiction", "odd", "rule_catalog"):
        if not _source_ref(record.get(key, {}).get("source_ref")):
            reasons.append(f"UNSOURCED_SCOPE_FIELD:{key}")
    return reasons


def _binding_reasons(record: dict[str, Any]) -> list[str]:
    recorded = record.get("recorded_rig_binding")
    simulation = record.get("simulation_vehicle_binding")
    if not isinstance(recorded, dict) or not _source_ref(recorded.get("evidence_ref")):
        return ["INVALID_RECORDED_RIG_BINDING"]
    if not isinstance(simulation, dict) or not _source_ref(simulation.get("evidence_ref")):
        return ["INVALID_SIMULATION_VEHICLE_BINDING"]
    if simulation.get("assurance_class") != "SIMULATED_ASSURANCE":
        return ["SIMULATION_BINDING_CLASS_INVALID"]
    if (
        not recorded.get("binding_key")
        or not simulation.get("binding_key")
        or recorded["binding_key"] == simulation["binding_key"]
    ):
        return ["RECORDED_SIMULATION_BINDINGS_NOT_DISTINCT"]
    return []


def build_scene_eligibility_manifest(records: Iterable[dict[str, Any]]) -> dict[str, Any]:
    """Audit each record, then deterministically exclude duplicate event/content."""
    audited: list[dict[str, Any]] = []
    seen_event: set[str] = set()
    seen_content: set[str] = set()
    seen_source: set[str] = set()
    deduplicated = 0
    for supplied in sorted((deepcopy(item) for item in records), key=lambda item: str(item.get("scene_hash", ""))):
        reasons: list[str] = []
        for name in ("scene_hash", "event_hash", "content_hash", "source_hash"):
            value = supplied.get(name)
            if not isinstance(value, str) or _HASH_RE.fullmatch(value) is None or not value.startswith(name.removesuffix("_hash") + "-sha256:"):
                reasons.append(f"INVALID_{name.upper()}")
        if supplied.get("slice") not in SLICES:
            reasons.append("INVALID_SLICE")
        if supplied.get("outcome") not in OUTCOMES:
            reasons.append("INVALID_OUTCOME")
        fields = supplied.get("fields")
        if not isinstance(fields, dict):
            fields = {}
        field_reasons: list[str] = []
        for field_name in REQUIRED_EVIDENCE_FIELDS:
            field_reasons.extend(_field_reasons(field_name, fields.get(field_name)))
        if set(fields) - set(REQUIRED_EVIDENCE_FIELDS):
            reasons.append("UNDECLARED_REQUIRED_FIELD")
        synthetic = supplied.get("synthetic_required_field_fill")
        if synthetic is not False:
            field_reasons.append("SYNTHETIC_REQUIRED_FIELD_FILL_NOT_ALLOWED")
        source_complete = not field_reasons
        reasons.extend(field_reasons)
        reasons.extend(_scope_reasons(supplied))
        reasons.extend(_binding_reasons(supplied))
        if not _outcome_witness_valid(supplied):
            reasons.append("OUTCOME_WITNESS_INVALID")

        event_hash = supplied.get("event_hash")
        content_hash = supplied.get("content_hash")
        source_hash = supplied.get("source_hash")
        duplicate = any((
            event_hash in seen_event,
            content_hash in seen_content,
            source_hash in seen_source,
        ))
        if duplicate:
            reasons.append("DUPLICATE_EVENT_OR_CONTENT")
            deduplicated += 1
        else:
            if isinstance(event_hash, str):
                seen_event.add(event_hash)
            if isinstance(content_hash, str):
                seen_content.add(content_hash)
            if isinstance(source_hash, str):
                seen_source.add(source_hash)
        supplied["source_complete"] = source_complete
        supplied["eligible"] = source_complete and not reasons
        supplied["assigned_slot_id"] = None
        supplied["exclusion_reasons"] = list(dict.fromkeys(reasons))
        audited.append(supplied)

    eligible = [record for record in audited if record["eligible"]]
    return {
        "eligibility_version": ELIGIBILITY_VERSION,
        "required_evidence_fields": list(REQUIRED_EVIDENCE_FIELDS),
        "candidate_count": len(audited),
        "source_complete_count": sum(record["source_complete"] for record in audited),
        "eligible_scene_count": len(eligible),
        "newly_eligible_count": sum(
            record["eligible"] and not record.get("prior_eligible", False)
            for record in audited
        ),
        "prior_eligible_reaudited_count": sum(
            bool(record.get("prior_eligible")) for record in audited
        ),
        "prior_eligible_retained_count": sum(
            record["eligible"] and bool(record.get("prior_eligible"))
            for record in audited
        ),
        "deduplicated_count": deduplicated,
        "excluded_count": len(audited) - len(eligible),
        "synthetic_required_field_fill_count": sum(synthetic_fill_count(record) for record in audited),
        "records": audited,
        "claim_scope": "M16_SCENE_ELIGIBILITY_NOT_EXPERT_EFFECT_OR_VEHICLE_SAFETY",
    }


def synthetic_fill_count(record: dict[str, Any]) -> int:
    return int(record.get("synthetic_required_field_fill") is not False)


def bind_eligible_scenes_to_slots(
    eligibility_manifest: dict[str, Any],
    slot_manifest: dict[str, Any],
) -> dict[str, Any]:
    """Bind sorted eligible records only to slots in their exact joint cell."""
    slots = sorted(deepcopy(slot_manifest.get("slots", ())), key=lambda item: item["slot_id"])
    by_cell: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for record in eligibility_manifest.get("records", ()):
        if record.get("eligible") is True:
            by_cell.setdefault((record["slice"], record["outcome"]), []).append(record)
    for records in by_cell.values():
        records.sort(key=lambda item: item["scene_hash"])

    bound = 0
    assignments: list[dict[str, Any]] = []
    joint_shortfall: dict[str, int] = {}
    for slice_name in SLICES:
        for outcome in OUTCOMES:
            cell_slots = [
                slot for slot in slots
                if slot["slice"] == slice_name and slot["outcome"] == outcome
            ]
            candidates = by_cell.get((slice_name, outcome), ())
            for index, slot in enumerate(cell_slots):
                scene_hash = candidates[index]["scene_hash"] if index < len(candidates) else None
                slot["scene_hash"] = scene_hash
                slot["bound"] = scene_hash is not None
                if scene_hash is not None:
                    bound += 1
                    assignments.append({
                        "scene_hash": scene_hash,
                        "slot_id": slot["slot_id"],
                        "slice": slice_name,
                        "outcome": outcome,
                    })
            joint_shortfall[f"{slice_name}|{outcome}"] = max(0, len(cell_slots) - len(candidates))
    slice_coverage = Counter(item["slice"] for item in assignments)
    outcome_coverage = Counter(item["outcome"] for item in assignments)
    assignment_by_scene = {
        item["scene_hash"]: item["slot_id"] for item in assignments
    }
    for record in eligibility_manifest.get("records", ()):
        record["assigned_slot_id"] = assignment_by_scene.get(record.get("scene_hash"))
    design = pilot_design()
    return {
        "slot_binding_version": "guardsynth-m16-slot-binding-v0.1",
        "slot_count": len(slots),
        "bound_slot_count": bound,
        "unbound_slot_count": len(slots) - bound,
        "distinct_bound_scene_count": len({item["scene_hash"] for item in assignments}),
        "slice_coverage": {name: slice_coverage[name] for name in SLICES},
        "slice_shortfall": {
            name: max(0, design["slice_quota"][name] - slice_coverage[name])
            for name in SLICES
        },
        "outcome_coverage": {name: outcome_coverage[name] for name in OUTCOMES},
        "outcome_shortfall": {
            name: max(0, design["outcome_quota"][name] - outcome_coverage[name])
            for name in OUTCOMES
        },
        "joint_cell_shortfall": joint_shortfall,
        "scene_assignments": assignments,
        "slots": slots,
        "counts_derived_from_individual_records": True,
    }


def build_m16_scene_preflight(
    eligibility_manifest: dict[str, Any],
    slot_binding: dict[str, Any],
    *,
    asserted_aggregate: dict[str, int] | None = None,
    public_boundary_verified: bool = True,
) -> dict[str, Any]:
    """Calculate every M16 data gate from audited individual scene records."""
    eligible_count = sum(
        record.get("eligible") is True
        for record in eligibility_manifest.get("records", ())
    )
    if eligible_count != eligibility_manifest.get("eligible_scene_count"):
        raise ValueError("AGGREGATE_INDIVIDUAL_COUNT_MISMATCH")
    if asserted_aggregate is not None and asserted_aggregate.get("eligible_scene_count") != eligible_count:
        raise ValueError("AGGREGATE_INDIVIDUAL_COUNT_MISMATCH")
    design = pilot_design()
    data_gate = all((
        slot_binding.get("bound_slot_count") == design["target_scene_count"],
        slot_binding.get("distinct_bound_scene_count") == design["target_scene_count"],
        not any(slot_binding.get("joint_cell_shortfall", {}).values()),
        not any(slot_binding.get("slice_shortfall", {}).values()),
        not any(slot_binding.get("outcome_shortfall", {}).values()),
        eligibility_manifest.get("synthetic_required_field_fill_count") == 0,
        public_boundary_verified is True,
    ))
    prior_mismatches = [
        record for record in eligibility_manifest.get("records", ())
        if record.get("prior_eligible")
        and "JURISDICTION_SOURCE_SCOPE_MISMATCH"
        in record.get("exclusion_reasons", ())
    ]
    if data_gate:
        status = "READY_FOR_REVIEWER_CALIBRATION"
    elif eligible_count > 0:
        status = "PARTIAL_DATA_ACQUISITION"
    elif prior_mismatches:
        status = "SEMANTICS_OR_SCOPE_REWORK"
    else:
        status = "BLOCKED_DATA_SHORTFALL"
    return {
        "preflight_version": "guardsynth-m16-scene-preflight-v0.2",
        "status": status,
        "annotation_start_allowed": data_gate,
        "annotation_started": False,
        "reviewer_calibration_completed": False,
        "eligible_scene_count": eligible_count,
        "target_scene_count": design["target_scene_count"],
        "total_scene_shortfall": max(0, design["target_scene_count"] - slot_binding.get("bound_slot_count", 0)),
        "slice_coverage": dict(slot_binding.get("slice_coverage", {})),
        "slice_shortfall": dict(slot_binding.get("slice_shortfall", {})),
        "outcome_coverage": dict(slot_binding.get("outcome_coverage", {})),
        "outcome_shortfall": dict(slot_binding.get("outcome_shortfall", {})),
        "joint_cell_shortfall": dict(slot_binding.get("joint_cell_shortfall", {})),
        "source_complete_8_of_8_gate": all(
            record.get("source_complete") is True
            for record in eligibility_manifest.get("records", ())
            if record.get("eligible") is True
        ),
        "jurisdiction_source_scope_gate": not any(
            "JURISDICTION_SOURCE_SCOPE_MISMATCH"
            in record.get("exclusion_reasons", ())
            for record in eligibility_manifest.get("records", ())
            if record.get("eligible") is True
        ),
        "distinct_scene_content_gate": eligibility_manifest.get("deduplicated_count") == 0,
        "public_boundary_verified": public_boundary_verified,
        "synthetic_required_field_fill_count": eligibility_manifest.get(
            "synthetic_required_field_fill_count", 0
        ),
        "prior_eligible_jurisdiction_source_mismatch_count": len(prior_mismatches),
        "actual_vehicle_validation_deferred_to_m21": True,
        "claim_scope": "M16_SCENE_ELIGIBILITY_AND_ACQUISITION_NOT_EXPERT_EFFECT_OR_VEHICLE_SAFETY",
    }


def assert_public_export_safe(value: Any) -> None:
    """Reject raw identifiers, local paths, and full CoC text recursively."""
    if isinstance(value, dict):
        for key, item in value.items():
            if str(key).lower() in _FORBIDDEN_PUBLIC_KEYS:
                raise ValueError("RESTRICTED_IDENTIFIER_LEAK")
            assert_public_export_safe(item)
        return
    if isinstance(value, (list, tuple)):
        for item in value:
            assert_public_export_safe(item)
        return
    if isinstance(value, str) and any(token in value for token in ("/home/", "file://", "data/restricted/")):
        raise ValueError("RESTRICTED_IDENTIFIER_LEAK")
