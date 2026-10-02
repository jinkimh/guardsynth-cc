"""Source-separated M14 proposal to existing GuardSynth generation handoff."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from math import isfinite
from pathlib import Path
from typing import Any

from .simulated_scene_dry_run import (
    SimulatedAssuranceModel,
    load_simulated_assurance_model,
    simulation_registry,
    simulation_semantics,
)
from .source_authoring import author_generation_request
from .source_aware_generator import (
    SourceAwareGenerationRequest,
    SourceAwareGenerationResult,
    generate_from_request,
    parse_generation_request,
)


SUPPORTED_OPERATIONAL_POLICY_BINDINGS = {
    "KR-RTA-27-1-CROSSWALK-STOP": "GS-SIM-PED-CORRIDOR-001",
}


@dataclass(frozen=True, slots=True)
class MaterializedProposal:
    proposal_rule_id: str
    executable_system_requirement_rule_id: str
    request: SourceAwareGenerationRequest
    generated: SourceAwareGenerationResult
    numeric_evidence_refs: tuple[str, ...]
    legal_proposal_refs: tuple[str, ...]
    recorded_vehicle_binding_key: str
    simulation_vehicle_binding_key: str
    claim_scope: str


def _validated_context(context: dict[str, Any], proposal: dict[str, Any]) -> None:
    required_strings = (
        "scene_ref", "hazard_evidence_ref", "geometry_evidence_ref",
        "transform_evidence_ref", "recorded_vehicle_binding_key",
    )
    if any(not isinstance(context.get(key), str) or not context[key] for key in required_strings):
        raise ValueError("MISSING_MATERIALIZATION_SOURCE_REF")
    numeric = (context.get("timestamp_s"), context.get("zone_entry_x_m"))
    if any(
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not isfinite(value)
        for value in numeric
    ):
        raise ValueError("MISSING_MATERIALIZATION_NUMERIC_SCENE_INPUT")
    if context["timestamp_s"] < 0:
        raise ValueError("INVALID_MATERIALIZATION_TIMESTAMP")
    if context.get("coordinate_frame") != "dataset_rig" or context.get("distance_unit") != "m":
        raise ValueError("MATERIALIZATION_UNIT_OR_FRAME_MISMATCH")
    if context.get("transform_verified") is not True:
        raise ValueError("MATERIALIZATION_TRANSFORM_NOT_VERIFIED")
    if (
        context.get("target_entity_id") != proposal.get("target_id")
        or context.get("zone_id") != proposal.get("zone_id")
    ):
        raise ValueError("MATERIALIZATION_PROPOSAL_BINDING_MISMATCH")
    association_refs = context.get("association_evidence_refs")
    if not isinstance(association_refs, list) or not association_refs or any(
        not isinstance(item, str) or not item for item in association_refs
    ):
        raise ValueError("MISSING_MATERIALIZATION_ASSOCIATION_EVIDENCE")


def materialize_simulated_proposal(
    *,
    proposal_bundle: dict[str, Any],
    proposal_rule_id: str,
    scene_context: dict[str, Any],
    model_source: Path | dict[str, Any],
    base_request: dict[str, Any],
    request_id: str,
) -> MaterializedProposal:
    """Use explicit system/vehicle sources; never treat legal text as numeric policy."""
    proposals = {
        item["rule_id"]: item for item in proposal_bundle.get("proposals", ())
    }
    proposal = proposals.get(proposal_rule_id)
    if proposal is None or proposal.get("verdict") != "PROPOSED":
        raise ValueError("FRONTEND_PROPOSAL_NOT_MATERIALIZABLE")
    expected_system_rule = SUPPORTED_OPERATIONAL_POLICY_BINDINGS.get(proposal_rule_id)
    if expected_system_rule is None:
        raise ValueError("NO_OPERATIONAL_POLICY_BINDING_FOR_PROPOSAL")
    _validated_context(scene_context, proposal)

    model: SimulatedAssuranceModel = load_simulated_assurance_model(model_source)
    if model.simulation_vehicle_binding_key == scene_context["recorded_vehicle_binding_key"]:
        raise ValueError("SIMULATION_BINDING_MUST_DIFFER_FROM_RECORDED_RIG")
    system_rule, predicate, requirement_ref = simulation_semantics()
    if system_rule.rule_id != expected_system_rule:
        raise ValueError("OPERATIONAL_POLICY_BINDING_VERSION_MISMATCH")

    grounded_scene = {
        "instance_id": "frontend_scene_0",
        "contract_id": "C0",
        "timestamp_s": float(scene_context["timestamp_s"]),
        "hazard": {
            "truth": "TRUE",
            "epistemic_kind": "DERIVED",
            "evidence_ref": scene_context["hazard_evidence_ref"],
            "timestamp_s": float(scene_context["timestamp_s"]),
            "maximum_age_s": predicate.maximum_age_s,
        },
        "association": {
            "target_entity_id": scene_context["target_entity_id"],
            "zone_id": scene_context["zone_id"],
            "evidence_ref": scene_context["association_evidence_refs"][0],
            "evidence_refs": list(scene_context["association_evidence_refs"]),
        },
        "zone_geometry": {
            "entry_x_m": float(scene_context["zone_entry_x_m"]),
            "frame": scene_context["coordinate_frame"],
            "evidence_ref": scene_context["geometry_evidence_ref"],
        },
        "coordinate_transform": {
            "verified": True,
            "evidence_ref": scene_context["transform_evidence_ref"],
        },
        "vehicle_binding_key": model.simulation_vehicle_binding_key,
        "assurance_scope": model.scope,
        "reason_codes": [],
    }
    raw_base = deepcopy(base_request)
    raw_base["rule_template_ref"] = system_rule.rule_id
    raw_base["predicate_spec_ref"] = predicate.predicate_id
    raw_base["claim_scope"] = (
        "COC_CONDITIONED_LEGAL_PROPOSAL_WITH_SEPARATE_SIMULATION_POLICY_"
        "NOT_LEGAL_DECISION_OR_REAL_VEHICLE_SAFETY"
    )
    raw_base["policy"]["predicate_evidence_ref"] = requirement_ref
    raw_base["source_refs"] = sorted(set((
        *raw_base["source_refs"],
        requirement_ref,
    )))
    authored = author_generation_request(
        base_request=raw_base,
        grounded_scenes=[grounded_scene],
        registry=simulation_registry(model),
        request_id=request_id,
        rule_catalog={system_rule.rule_id: system_rule},
        predicate_catalog={predicate.predicate_id: predicate},
    )
    legal_refs = tuple(sorted(set((
        *proposal["source_claim_refs"],
        *proposal["source_record_refs"],
    ))))
    coc_ref = proposal_bundle["coc_parse"]["evidence_ref"]
    authored["source_refs"] = sorted(set((*authored["source_refs"], *legal_refs, coc_ref)))
    authored["context_graph"]["coc_claims"] = [{
        "claim_id": "frontend_coc_claim",
        "epistemic_kind": "CLAIMED",
        "evidence_ref": coc_ref,
    }]
    parsed = parse_generation_request(
        authored,
        rule_catalog={system_rule.rule_id: system_rule},
        predicate_catalog={predicate.predicate_id: predicate},
    )
    generated = generate_from_request(parsed)
    if generated.verdict != "VALIDATED" or generated.collection is None:
        raise ValueError(
            "MATERIALIZED_GUARDSYNTH_REQUEST_REJECTED:"
            + generated.verdict
            + ":"
            + ",".join(generated.reason_codes)
        )
    numeric_refs = tuple(sorted({
        evidence_ref
        for symbol in generated.program_template.raw["typed_derivation"]["symbols"]
        if symbol["symbol_id"] in {"stop_margin", "response_time", "deceleration"}
        for evidence_ref in symbol["evidence_refs"]
    }))
    if set(numeric_refs).intersection(legal_refs):
        raise ValueError("LEGAL_PROPOSAL_USED_AS_NUMERIC_POLICY_SOURCE")
    return MaterializedProposal(
        proposal_rule_id=proposal_rule_id,
        executable_system_requirement_rule_id=system_rule.rule_id,
        request=parsed,
        generated=generated,
        numeric_evidence_refs=numeric_refs,
        legal_proposal_refs=legal_refs,
        recorded_vehicle_binding_key=scene_context["recorded_vehicle_binding_key"],
        simulation_vehicle_binding_key=model.simulation_vehicle_binding_key,
        claim_scope=raw_base["claim_scope"],
    )
