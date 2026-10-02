"""Convert fully grounded scene records into GuardSynth generation requests.

Partial derived scenes are assessed, not repaired. Missing associations,
transforms, vehicle assurance or source references produce reason codes and no
executable EBLC request.
"""

from __future__ import annotations

from copy import deepcopy
from math import isfinite
from typing import Any, Iterable, Mapping

from .assurance_registry import AssuranceProfile, AssuranceRegistry
from guard_synth_eblc.catalog import SCHEMA_ROOT
from guard_synth_eblc.program import EBLCProgram
from guard_synth_eblc.schema_validation import SchemaValidationError, load_json, validate
from guard_synth_eblc.types import PredicateSpec, RuleTemplate


class GroundedSceneValidationError(ValueError):
    pass


def _scene_reasons(scene: dict[str, Any], registry: AssuranceRegistry) -> tuple[str, ...]:
    reasons = list(scene.get("reason_codes", ()))
    hazard = scene.get("hazard")
    association = scene.get("association")
    geometry = scene.get("zone_geometry")
    transform = scene.get("coordinate_transform")
    binding_key = scene.get("vehicle_binding_key")
    if not isinstance(hazard, dict) or not hazard.get("evidence_ref"):
        reasons.append("MISSING_HAZARD_EVIDENCE")
    if not isinstance(association, dict) or not all(
        association.get(key) for key in ("target_entity_id", "zone_id", "evidence_ref")
    ):
        reasons.append("MISSING_OR_AMBIGUOUS_TARGET_ZONE_ASSOCIATION")
    elif any(
        not isinstance(ref, str) or not ref.strip()
        for ref in association.get("evidence_refs", ())
    ):
        reasons.append("INVALID_ASSOCIATION_EVIDENCE")
    if not isinstance(geometry, dict) or not geometry.get("evidence_ref"):
        reasons.append("MISSING_CONFLICT_ZONE_GEOMETRY")
    if not isinstance(transform, dict) or not transform.get("evidence_ref"):
        reasons.append("MISSING_COORDINATE_TRANSFORM")
    elif not transform.get("verified", False):
        reasons.append("UNVERIFIED_COORDINATE_TRANSFORM")
    profile = registry.resolve(binding_key) if binding_key else None
    if profile is None:
        reasons.append("MISSING_VEHICLE_ASSURANCE_PROFILE")
    elif scene.get("assurance_scope") != profile.evidence.scope:
        reasons.append("ASSURANCE_SCOPE_MISMATCH")
    return tuple(dict.fromkeys(reasons))


def _profile_for_scenes(
    scenes: tuple[dict[str, Any], ...], registry: AssuranceRegistry
) -> AssuranceProfile:
    keys = {scene.get("vehicle_binding_key") for scene in scenes}
    if len(keys) != 1:
        raise GroundedSceneValidationError("MIXED_OR_MISSING_VEHICLE_BINDING")
    profile = registry.resolve(next(iter(keys)))
    if profile is None:
        raise GroundedSceneValidationError("MISSING_VEHICLE_ASSURANCE_PROFILE")
    return profile


def author_generation_request(
    *,
    base_request: dict[str, Any],
    grounded_scenes: Iterable[dict[str, Any]],
    registry: AssuranceRegistry,
    request_id: str,
    rule_catalog: Mapping[str, RuleTemplate] | None = None,
    predicate_catalog: Mapping[str, PredicateSpec] | None = None,
    template_catalog: Mapping[str, EBLCProgram] | None = None,
) -> dict[str, Any]:
    """Author one multi-contract request; never infer or default missing data."""
    scenes = tuple(deepcopy(tuple(grounded_scenes)))
    if not scenes:
        raise GroundedSceneValidationError("AT_LEAST_ONE_GROUNDED_SCENE_REQUIRED")
    for scene in scenes:
        reasons = _scene_reasons(scene, registry)
        if reasons:
            raise GroundedSceneValidationError(",".join(reasons))
    profile = _profile_for_scenes(scenes, registry)

    raw = deepcopy(base_request)
    raw["request_id"] = request_id
    old_profile_ref = raw["vehicle_profile"]["evidence_ref"] if raw["vehicle_profile"] else None
    replaced_refs = set(raw["context_graph"].get("source_refs", ()))
    if old_profile_ref:
        replaced_refs.add(old_profile_ref)
    raw["source_refs"] = [item for item in raw["source_refs"] if item not in replaced_refs]
    raw["vehicle_profile"] = {
        "profile_id": profile.profile_id,
        "maximum_service_deceleration_mps2": profile.maximum_service_deceleration_mps2,
        "response_time_s": profile.response_time_s,
        "position_uncertainty_m": profile.position_uncertainty_m,
        "evidence_ref": profile.evidence.evidence_ref,
    }

    instances: list[dict[str, Any]] = []
    source_refs = set(raw["source_refs"])
    context_refs: list[str] = []
    for scene in scenes:
        hazard = scene["hazard"]
        association = scene["association"]
        geometry = scene["zone_geometry"]
        transform = scene["coordinate_transform"]
        association_refs = list(dict.fromkeys([
            association["evidence_ref"],
            *association.get("evidence_refs", ()),
        ]))
        refs = [
            hazard["evidence_ref"], *association_refs,
            geometry["evidence_ref"], transform["evidence_ref"],
        ]
        source_refs.update(refs)
        context_refs.extend(refs)
        instances.append({
            "instance_id": scene["instance_id"],
            "contract_id": scene["contract_id"],
            "hazard_fact": {
                "truth": hazard["truth"],
                "epistemic_kind": hazard["epistemic_kind"],
                "source_ref": hazard["evidence_ref"],
                "timestamp_s": hazard["timestamp_s"],
                "maximum_age_s": hazard["maximum_age_s"],
            },
            "association": {
                "selected_target_entity_id": association["target_entity_id"],
                "selected_zone_id": association["zone_id"],
                "candidate_target_entity_ids": [association["target_entity_id"]],
                "candidate_zone_ids": [association["zone_id"]],
                "zone_geometry_ref": geometry["evidence_ref"],
                "coordinate_transform_ref": transform["evidence_ref"],
                "evidence_refs": list(dict.fromkeys([
                    *association_refs, geometry["evidence_ref"], transform["evidence_ref"],
                ])),
            },
            "zone_entry": {
                "value": geometry["entry_x_m"], "unit": "m", "frame": geometry["frame"],
                "evidence_refs": [geometry["evidence_ref"]],
            },
            "overrides_contracts": scene.get("overrides_contracts", []),
        })
    source_refs.add(profile.evidence.evidence_ref)
    raw["source_refs"] = sorted(source_refs)
    raw["context_graph"] = {
        "graph_id": f"{request_id}__context_graph",
        "timestamp_s": max(float(scene["timestamp_s"]) for scene in scenes),
        "source_refs": sorted(set(context_refs)),
        "coc_claims": [],
        "instances": instances,
    }
    # Do not let a schema-valid but semantically rejected request escape this
    # boundary.  The generator remains the authority for source/freshness,
    # epistemic, binding and unit/frame acceptance.
    from .source_aware_generator import generate_from_request, parse_generation_request
    try:
        generated = generate_from_request(parse_generation_request(
            raw,
            rule_catalog=rule_catalog,
            predicate_catalog=predicate_catalog,
            template_catalog=template_catalog,
        ))
    except ValueError as exc:
        raise GroundedSceneValidationError(f"GENERATOR_VALIDATION_FAILED:{exc}") from exc
    if generated.verdict != "VALIDATED" or generated.collection is None:
        reasons = ",".join(generated.reason_codes)
        raise GroundedSceneValidationError(f"GENERATOR_REJECTED:{generated.verdict}:{reasons}")
    return raw


def _candidate_readiness_reasons(
    candidate: dict[str, Any], registry: AssuranceRegistry
) -> tuple[str, ...]:
    reasons = list(candidate.get("contract_binding", {}).get("reason_codes", ()))
    context = candidate.get("context_graph")
    if candidate.get("context_schema_valid") is not True or not isinstance(context, dict):
        reasons.append("INVALID_OR_UNVALIDATED_CONTEXT_GRAPH")
        context = {}
    else:
        try:
            validate(context, load_json(SCHEMA_ROOT / "context_graph.schema.json"))
        except SchemaValidationError:
            reasons.append("INVALID_OR_UNVALIDATED_CONTEXT_GRAPH")
    hazard = context.get("hazard_fact")
    if not isinstance(hazard, dict) or not (
        hazard.get("source") or hazard.get("source_ref")
    ) or hazard.get("timestamp_s") is None or hazard.get("maximum_age_s") is None:
        reasons.append("MISSING_HAZARD_EVIDENCE")
    elif hazard.get("epistemic_kind") == "CLAIMED":
        reasons.append("COC_CLAIM_NOT_OBSERVED_FACT")
    numeric_context = (
        context.get("ego_front_x_m"), context.get("ego_speed_mps"),
        context.get("zone_entry_x_m"),
    )
    if any(
        not isinstance(value, (int, float)) or isinstance(value, bool) or not isfinite(value)
        for value in numeric_context
    ):
        reasons.append("MISSING_TIME_ALIGNED_EGO_OR_ZONE_STATE")
    if context.get("distance_unit") != "m" or not context.get("coordinate_frame"):
        reasons.append("MISSING_OR_INVALID_CONTEXT_UNIT_FRAME")
    if not context.get("target_entity_id") or not context.get("zone_id"):
        reasons.append("MISSING_TARGET_OR_ZONE_IDENTIFIER")

    target_binding = candidate.get("target_binding", {})
    if target_binding.get("verdict") != "VALIDATED":
        reasons.append("MISSING_OR_AMBIGUOUS_TARGET_ZONE_ASSOCIATION")
    if not target_binding.get("association_evidence_refs"):
        reasons.append("MISSING_ASSOCIATION_EVIDENCE")
    zone = candidate.get("conflict_zone", {})
    if not zone.get("source_fields"):
        reasons.append("MISSING_CONFLICT_ZONE_GEOMETRY")
    transform = candidate.get("coordinate_transform", {})
    if not transform.get("verified", False) or not transform.get("evidence_ref"):
        reasons.append("UNVERIFIED_COORDINATE_TRANSFORM")

    binding_key = candidate.get("vehicle_binding_key")
    profile = registry.resolve(binding_key) if binding_key else None
    if profile is None:
        reasons.append("MISSING_VEHICLE_ASSURANCE_PROFILE")
    elif candidate.get("assurance_scope") != profile.evidence.scope:
        reasons.append("ASSURANCE_SCOPE_MISMATCH")
    return tuple(dict.fromkeys(str(item) for item in reasons if str(item).strip()))


def assess_scene_readiness(
    adapter_result: dict[str, Any],
    registry: AssuranceRegistry,
    *,
    target_slots: int = 24,
) -> dict[str, Any]:
    """Produce an identifier-free readiness matrix; absent slots stay absent."""
    if not isinstance(target_slots, int) or isinstance(target_slots, bool) or target_slots < 1:
        raise ValueError("target_slots must be positive")
    candidates = list(adapter_result.get("candidates", ()))
    gaps = list(adapter_result.get("data_gaps", ()))
    declared = adapter_result.get("vru_event_count", len(candidates) + len(gaps))
    if not isinstance(declared, int) or isinstance(declared, bool) or declared < 0:
        raise ValueError("invalid candidate event accounting")
    actual_count = declared
    if actual_count != len(candidates) + len(gaps):
        raise ValueError("candidate event accounting mismatch")
    if actual_count > target_slots:
        raise ValueError("actual candidate events exceed target slots")

    slots: list[dict[str, Any]] = []
    complete = 0
    reason_counts: dict[str, int] = {}
    for candidate in candidates:
        reasons = list(_candidate_readiness_reasons(candidate, registry))
        is_complete = not reasons
        complete += int(is_complete)
        for reason in reasons:
            reason_counts[reason] = reason_counts.get(reason, 0) + 1
        slots.append({
            "slot": len(slots) + 1,
            "input_kind": "DERIVED_SCENE_CANDIDATE",
            "source_complete": is_complete,
            "reason_codes": reasons,
        })
    for gap in gaps:
        reason = str(gap.get("reason_code") or "UNSPECIFIED_DERIVATION_GAP").strip()
        if not reason:
            reason = "UNSPECIFIED_DERIVATION_GAP"
        reason_counts[reason] = reason_counts.get(reason, 0) + 1
        slots.append({
            "slot": len(slots) + 1,
            "input_kind": "DERIVATION_GAP",
            "source_complete": False,
            "reason_codes": [reason],
        })
    missing = target_slots - actual_count
    if missing:
        reason_counts["MISSING_SCENE_INPUT"] = missing
    for _ in range(missing):
        slots.append({
            "slot": len(slots) + 1,
            "input_kind": "NO_SCENE_INPUT",
            "source_complete": False,
            "reason_codes": ["MISSING_SCENE_INPUT"],
        })
    readiness_gate_passed = actual_count == target_slots and complete == target_slots
    return {
        "status": "EXECUTED_READINESS_AUDIT",
        "slot_count": target_slots,
        "actual_candidate_event_count": actual_count,
        "adapted_candidate_count": len(candidates),
        "derivation_gap_count": len(gaps),
        "missing_scene_input_slot_count": missing,
        "source_complete_scene_count": complete,
        "executable_scene_count": complete,
        "twenty_four_scene_readiness_gate_passed": readiness_gate_passed,
        "twenty_four_scene_execution_completed": False,
        "synthetic_scene_fill_performed": False,
        "raw_identifiers_included": False,
        "reason_code_counts": dict(sorted(reason_counts.items())),
        "slots": slots,
        "decision": "P0B_GO" if readiness_gate_passed else "DATA_GAP_PIVOT",
        "claim_scope": "SOURCE_READINESS_AND_ABSTENTION_NOT_REAL_SCENE_CONTRACT_OR_VEHICLE_SAFETY",
    }
