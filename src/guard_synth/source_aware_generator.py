"""Fail-closed RuleTemplate + ContextGraph + profile to EBLC generation.

This is the first public GuardSynth generation boundary.  It does not parse
free-form natural language and never upgrades a CoC claim to observed evidence.
All generated executable values are copied from validated source-bearing input
or from an explicitly sourced compiler policy.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from math import isfinite
from pathlib import Path
import re
from typing import Any, Iterable, Mapping

from guard_synth_eblc.catalog import load_pilot_rule, load_predicate_spec
from guard_synth_eblc.indexed_collection import IndexedCollection, parse_indexed_collection
from guard_synth_eblc.program import EBLCProgram, load_program, parse_program
from guard_synth_eblc.schema_validation import load_json, validate
from guard_synth_eblc.types import (
    PredicateSpec, PriorityClass, RuleTemplate, SourceClass, VehicleProfile,
)


GENERATOR_VERSION = "guard-synth-source-aware-generator-v0.1"
PACKAGE_ROOT = Path(__file__).resolve().parent
EBLC_ROOT = PACKAGE_ROOT.parent / "guard_synth_eblc"
SCHEMA_PATH = PACKAGE_ROOT / "schemas/source_aware_generation_request.schema.json"
EBLC_FIXTURE_ROOT = EBLC_ROOT / "fixtures"
_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_.-]*$")


class SourceAwareGenerationValidationError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class SourceAwareGenerationRequest:
    raw: dict[str, Any]
    request_id: str
    rule: RuleTemplate
    predicate: PredicateSpec
    base_template: EBLCProgram
    claimed_evidence_refs: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class SourceAwareGenerationResult:
    request_id: str
    verdict: str
    reason_codes: tuple[str, ...]
    program_template: EBLCProgram | None
    collection: IndexedCollection | None
    claimed_evidence_refs: tuple[str, ...]
    generation_map: dict[str, Any]


def _duplicates(values: Iterable[str]) -> bool:
    items = tuple(values)
    return len(items) != len(set(items))


def _default_rule_catalog() -> dict[str, RuleTemplate]:
    rule = load_pilot_rule()
    return {rule.rule_id: rule}


def _default_predicate_catalog() -> dict[str, PredicateSpec]:
    predicate = load_predicate_spec()
    return {predicate.predicate_id: predicate}


def _default_template_catalog() -> dict[str, EBLCProgram]:
    template = load_program(EBLC_FIXTURE_ROOT / "eblc_program_p0b_v0_2.json")
    return {template.program_id: template}


def _refs_used(raw: dict[str, Any]) -> tuple[str, ...]:
    policy = raw["policy"]
    graph = raw["context_graph"]
    refs: list[str] = [
        policy["predicate_evidence_ref"],
        policy["compiler_policy_evidence_ref"],
        *policy["composition_evidence_refs"],
        *graph["source_refs"],
    ]
    if raw["vehicle_profile"] is not None:
        refs.append(raw["vehicle_profile"]["evidence_ref"])
    for claim in graph["coc_claims"]:
        refs.append(claim["evidence_ref"])
    for instance in graph["instances"]:
        refs.append(instance["hazard_fact"]["source_ref"])
        refs.extend(instance["association"]["evidence_refs"])
        if instance["zone_entry"] is not None:
            refs.extend(instance["zone_entry"]["evidence_refs"])
    return tuple(refs)


def parse_generation_request(
    raw: dict[str, Any],
    *,
    rule_catalog: Mapping[str, RuleTemplate] | None = None,
    predicate_catalog: Mapping[str, PredicateSpec] | None = None,
    template_catalog: Mapping[str, EBLCProgram] | None = None,
) -> SourceAwareGenerationRequest:
    validate(raw, load_json(SCHEMA_PATH))
    if raw["generator_version"] != GENERATOR_VERSION:
        raise SourceAwareGenerationValidationError(
            f"unsupported generator version: {raw['generator_version']}"
        )
    if not _IDENTIFIER.fullmatch(raw["request_id"]):
        raise SourceAwareGenerationValidationError(f"invalid request id: {raw['request_id']}")

    rules = dict(rule_catalog or _default_rule_catalog())
    predicates = dict(predicate_catalog or _default_predicate_catalog())
    templates = dict(template_catalog or _default_template_catalog())
    try:
        rule = rules[raw["rule_template_ref"]]
    except KeyError as exc:
        raise SourceAwareGenerationValidationError("unknown rule template ref") from exc
    try:
        predicate = predicates[raw["predicate_spec_ref"]]
    except KeyError as exc:
        raise SourceAwareGenerationValidationError("unknown predicate spec ref") from exc
    try:
        template = templates[raw["template_program_ref"]]
    except KeyError as exc:
        raise SourceAwareGenerationValidationError("unknown template program ref") from exc
    if template.raw["program_version"] != "eblc-program-v0.2":
        raise SourceAwareGenerationValidationError("source-aware generator requires program v0.2 template")

    known = tuple(raw["source_refs"])
    if _duplicates(known):
        raise SourceAwareGenerationValidationError("duplicate source_refs")
    required_refs = (rule.source.evidence_id, *_refs_used(raw))
    unknown = sorted(set(required_refs) - set(known))
    if unknown:
        raise SourceAwareGenerationValidationError(f"unknown evidence references: {unknown}")
    if not set(raw["context_graph"]["source_refs"]).issubset(known):
        raise SourceAwareGenerationValidationError("unknown context graph evidence")

    policy = raw["policy"]
    if _duplicates(policy["action_domain"]) or _duplicates(policy["allowed_actions"]):
        raise SourceAwareGenerationValidationError("duplicate action policy value")
    if not set(policy["allowed_actions"]).issubset(policy["action_domain"]):
        raise SourceAwareGenerationValidationError("allowed action is outside action domain")
    instances = raw["context_graph"]["instances"]
    instance_ids = tuple(item["instance_id"] for item in instances)
    contract_ids = tuple(item["contract_id"] for item in instances)
    if _duplicates(instance_ids) or _duplicates(contract_ids):
        raise SourceAwareGenerationValidationError("duplicate context instance or contract id")
    known_contracts = set(contract_ids)
    for item in instances:
        if not _IDENTIFIER.fullmatch(item["instance_id"]) or not _IDENTIFIER.fullmatch(item["contract_id"]):
            raise SourceAwareGenerationValidationError("invalid instance or contract identifier")
        association = item["association"]
        if any(_duplicates(association[name]) for name in (
            "candidate_target_entity_ids", "candidate_zone_ids", "evidence_refs"
        )):
            raise SourceAwareGenerationValidationError("duplicate association metadata")
        overrides = item["overrides_contracts"]
        if _duplicates(overrides) or item["contract_id"] in overrides or not set(overrides).issubset(known_contracts):
            raise SourceAwareGenerationValidationError("invalid contract override")

    claimed = tuple(dict.fromkeys(
        claim["evidence_ref"] for claim in raw["context_graph"]["coc_claims"]
    ))
    return SourceAwareGenerationRequest(raw, raw["request_id"], rule, predicate, template, claimed)


def load_generation_request(path: Path) -> SourceAwareGenerationRequest:
    return parse_generation_request(load_json(path))


def _priority_tier(priority: PriorityClass) -> str:
    if priority in {
        PriorityClass.HARD_PHYSICAL,
        PriorityClass.ODD_FALLBACK,
        PriorityClass.MANDATORY_SYSTEM,
    }:
        return "HARD"
    if priority in {PriorityClass.ROUTE_PROGRESS, PriorityClass.HUMAN_CONVENTION}:
        return "SERVICE"
    return "PREFERENCE"


def _vehicle_profile(raw: dict[str, Any] | None) -> VehicleProfile | None:
    if raw is None:
        return None
    return VehicleProfile(
        profile_id=raw["profile_id"],
        maximum_service_deceleration_mps2=float(raw["maximum_service_deceleration_mps2"]),
        response_time_s=float(raw["response_time_s"]),
        position_uncertainty_m=float(raw["position_uncertainty_m"]),
        evidence_ref=raw["evidence_ref"],
    )


def _profile_reason(profile: VehicleProfile | None) -> str | None:
    if profile is None:
        return "MISSING_VEHICLE_ASSURANCE_PROFILE"
    values = (
        profile.maximum_service_deceleration_mps2,
        profile.response_time_s,
        profile.position_uncertainty_m,
    )
    if not all(isfinite(value) for value in values):
        return "NONFINITE_VEHICLE_ASSURANCE_PROFILE"
    if (
        profile.maximum_service_deceleration_mps2 <= 0
        or profile.response_time_s < 0
        or profile.position_uncertainty_m < 0
        or not profile.evidence_ref
    ):
        return "INVALID_VEHICLE_ASSURANCE_PROFILE"
    return None


def _build_program(
    request: SourceAwareGenerationRequest,
    profile: VehicleProfile,
) -> EBLCProgram:
    raw = deepcopy(request.base_template.raw)
    source = request.rule.source.evidence_id
    policy = request.raw["policy"]
    predicate_ref = policy["predicate_evidence_ref"]
    compiler_ref = policy["compiler_policy_evidence_ref"]
    program_refs = list(dict.fromkeys((source, predicate_ref, profile.evidence_ref, compiler_ref)))
    frame = request.predicate.coordinate_frame

    raw.update({
        "program_id": f"{request.request_id}__program_template",
        "frames": request.raw["frames"],
        "claim_scope": request.raw["claim_scope"],
        "source_refs": program_refs,
    })
    raw["binding"] = {
        "contract_id": "TEMPLATE_CONTRACT",
        "rule_id": request.rule.rule_id,
        "subject_id": policy["subject_id"],
        "target_entity_id": "UNBOUND_TARGET",
        "zone_id": "UNBOUND_ZONE",
        "coordinate_frame": frame,
        "distance_unit": "m",
        "evidence_refs": [source],
    }
    raw["predicate"] = {
        "predicate_id": request.predicate.predicate_id,
        "allowed_epistemic": [item.value for item in request.predicate.allowed_sources],
        "maximum_age_s": request.predicate.maximum_age_s,
        "failure_value": request.predicate.failure_value.value,
        "evidence_refs": [predicate_ref],
    }
    raw["lifecycle"] = {
        "initial_state": "INACTIVE",
        "release_clear_frames": request.rule.release_clear_frames,
        "release_enabled": policy["release_enabled"],
        "reactivation_enabled": policy["reactivation_enabled"],
        "fallback_action": request.rule.fallback,
        "fallback_approved": request.rule.fallback_approved,
        "unknown_policy": policy["unknown_policy"],
        "always_active": policy["always_active"],
        "expiry_timestamp_s": policy["expiry_timestamp_s"],
        "evidence_refs": [source],
    }
    raw["constraints"] = {
        "position_uncertainty": {
            "value": profile.position_uncertainty_m, "unit": "m", "frame": frame,
            "evidence_refs": [profile.evidence_ref],
        },
        "response_time": {
            "value": profile.response_time_s, "unit": "s", "frame": None,
            "evidence_refs": [profile.evidence_ref],
        },
        "deceleration": {
            "value": profile.maximum_service_deceleration_mps2, "unit": "m/s^2", "frame": frame,
            "evidence_refs": [profile.evidence_ref],
        },
        "enforce_invariant": policy["enforce_invariant"],
        "position_epsilon": {
            "value": policy["position_epsilon_m"], "unit": "m", "frame": frame,
            "evidence_refs": [compiler_ref],
        },
        "speed_epsilon": {
            "value": policy["speed_epsilon_mps"], "unit": "m/s", "frame": frame,
            "evidence_refs": [compiler_ref],
        },
        "time_epsilon": {
            "value": policy["time_epsilon_s"], "unit": "s", "frame": None,
            "evidence_refs": [compiler_ref],
        },
        "force_deadlock": policy["force_deadlock"],
    }

    derivation = raw["typed_derivation"]
    derivation.update({
        "derivation_id": f"{request.request_id}_stopping_derivation",
        "horizon": request.raw["frames"] + 1,
        "claim_scope": request.raw["claim_scope"],
        "source_refs": [source, profile.evidence_ref, compiler_ref],
    })
    symbols = {item["symbol_id"]: item for item in derivation["symbols"]}
    symbol_values = {
        "zone_entry_x": (0.0, compiler_ref),
        "stop_margin": (request.rule.stop_margin_m, source),
        "factor_two": (2.0, compiler_ref),
        "zero_speed": (0.0, compiler_ref),
        "ego_speed": (None, compiler_ref),
        "speed_epsilon": (None, compiler_ref),
        "response_time": (None, profile.evidence_ref),
        "deceleration": (None, profile.evidence_ref),
    }
    for symbol_id, (value, evidence_ref) in symbol_values.items():
        symbols[symbol_id]["value"] = value
        symbols[symbol_id]["evidence_refs"] = [evidence_ref]
        if symbols[symbol_id]["frame"] is not None:
            symbols[symbol_id]["frame"] = frame

    node_refs = {
        "stop_position": [source, compiler_ref],
        "adjusted_speed": [compiler_ref],
        "effective_speed": [compiler_ref],
        "response_distance": [profile.evidence_ref, compiler_ref],
        "speed_squared": [compiler_ref],
        "twice_deceleration": [profile.evidence_ref, compiler_ref],
        "braking_distance": [profile.evidence_ref, compiler_ref],
        "stopping_distance": [profile.evidence_ref, compiler_ref],
    }
    for node in derivation["nodes"]:
        node["source_refs"] = node_refs[node["node_id"]]
    for output in derivation["outputs"]:
        output["frame"] = frame
        output["evidence_refs"] = (
            [source, compiler_ref] if output["output_id"] == "stop_position"
            else [profile.evidence_ref, compiler_ref]
        )
    raw["priority"] = {
        "class": request.rule.priority.priority_class.value,
        "overrides": [item.value for item in request.rule.priority.overrides],
        "evidence_refs": [source],
    }
    return parse_program(raw)


def _context_reasons(request: SourceAwareGenerationRequest) -> tuple[str, ...]:
    graph = request.raw["context_graph"]
    reasons: list[str] = []
    pairs: set[tuple[str, str]] = set()
    allowed_epistemic = {item.value for item in request.predicate.allowed_sources}
    expected_frame = request.predicate.coordinate_frame

    for instance in graph["instances"]:
        hazard = instance["hazard_fact"]
        association = instance["association"]
        zone_entry = instance["zone_entry"]
        epistemic = hazard["epistemic_kind"]
        truth = hazard["truth"]
        if truth == "CONFLICT":
            reasons.append("CONFLICTING_HAZARD_EVIDENCE")
        elif epistemic == "CLAIMED":
            reasons.append("COC_CLAIM_NOT_OBSERVED_FACT")
        elif epistemic not in allowed_epistemic:
            reasons.append("UNAPPROVED_EPISTEMIC_SOURCE")
        elif truth == "UNKNOWN":
            reasons.append("UNKNOWN_RULE_PRECONDITION")
        elif truth == "FALSE":
            reasons.append("RULE_PRECONDITION_FALSE")
        age = graph["timestamp_s"] - hazard["timestamp_s"]
        maximum_age = min(hazard["maximum_age_s"], request.predicate.maximum_age_s)
        if age < 0:
            reasons.append("FUTURE_HAZARD_EVIDENCE")
        elif age > maximum_age:
            reasons.append("STALE_HAZARD_EVIDENCE")

        target = association["selected_target_entity_id"]
        zone = association["selected_zone_id"]
        targets = association["candidate_target_entity_ids"]
        zones = association["candidate_zone_ids"]
        if target is None:
            reasons.append(
                "AMBIGUOUS_TARGET_ASSOCIATION" if len(targets) > 1
                else "MISSING_TARGET_ASSOCIATION"
            )
        elif target not in targets:
            reasons.append("SELECTED_TARGET_OUTSIDE_CANDIDATES")
        if zone is None:
            reasons.append(
                "AMBIGUOUS_ZONE_ASSOCIATION" if len(zones) > 1
                else "MISSING_ZONE_ASSOCIATION"
            )
        elif zone not in zones:
            reasons.append("SELECTED_ZONE_OUTSIDE_CANDIDATES")
        if association["zone_geometry_ref"] is None:
            reasons.append("MISSING_ZONE_GEOMETRY")
        elif association["zone_geometry_ref"] not in association["evidence_refs"]:
            reasons.append("UNGROUNDED_ZONE_GEOMETRY")
        if association["coordinate_transform_ref"] is None:
            reasons.append("MISSING_COORDINATE_TRANSFORM")
        elif association["coordinate_transform_ref"] not in association["evidence_refs"]:
            reasons.append("UNGROUNDED_COORDINATE_TRANSFORM")
        if zone_entry is None:
            reasons.append("MISSING_ZONE_ENTRY_VALUE")
        elif zone_entry["unit"] != "m" or zone_entry["frame"] != expected_frame:
            reasons.append("ZONE_ENTRY_UNIT_OR_FRAME_MISMATCH")
        if target is not None and zone is not None:
            pair = (target, zone)
            if pair in pairs:
                reasons.append("DUPLICATE_TARGET_ZONE_BINDING")
            pairs.add(pair)
    return tuple(dict.fromkeys(reasons))


def _verdict(reasons: tuple[str, ...]) -> str:
    conflict = {
        "CONFLICTING_HAZARD_EVIDENCE",
        "SELECTED_TARGET_OUTSIDE_CANDIDATES",
        "SELECTED_ZONE_OUTSIDE_CANDIDATES",
        "DUPLICATE_TARGET_ZONE_BINDING",
    }
    review = {
        "COC_CLAIM_NOT_OBSERVED_FACT",
        "UNAPPROVED_EPISTEMIC_SOURCE",
        "UNKNOWN_RULE_PRECONDITION",
        "RULE_PRECONDITION_FALSE",
        "FUTURE_HAZARD_EVIDENCE",
        "STALE_HAZARD_EVIDENCE",
        "AMBIGUOUS_TARGET_ASSOCIATION",
        "AMBIGUOUS_ZONE_ASSOCIATION",
    }
    if any(reason in conflict for reason in reasons):
        return "CONFLICT"
    if any(reason not in review for reason in reasons):
        return "UNSUPPORTED"
    return "REVIEW_REQUIRED"


def generate_from_request(request: SourceAwareGenerationRequest) -> SourceAwareGenerationResult:
    profile = _vehicle_profile(request.raw["vehicle_profile"])
    profile_reason = _profile_reason(profile)
    base_map = {
        "generator_version": GENERATOR_VERSION,
        "rule_template_ref": request.raw["rule_template_ref"],
        "predicate_spec_ref": request.raw["predicate_spec_ref"],
        "vehicle_profile_ref": None if profile is None else profile.evidence_ref,
        "claimed_evidence_refs": list(request.claimed_evidence_refs),
        "coc_used_as_activation_evidence": False,
        "template_zone_entry_policy": "TEMPLATE_PLACEHOLDER_NEVER_EXECUTED_OVERWRITTEN_BY_GROUNDED_INSTANCE",
    }
    if request.rule.source.source_class is SourceClass.UNKNOWN or not request.rule.source.uri:
        profile_reason = "UNSUPPORTED_RULE_SOURCE"
    if profile_reason is not None:
        return SourceAwareGenerationResult(
            request.request_id, "UNSUPPORTED", (profile_reason,), None, None,
            request.claimed_evidence_refs, base_map,
        )
    if not request.rule.fallback_approved:
        return SourceAwareGenerationResult(
            request.request_id, "UNSUPPORTED", ("UNAPPROVED_UNKNOWN_FALLBACK",), None, None,
            request.claimed_evidence_refs, base_map,
        )

    program = _build_program(request, profile)
    reasons = _context_reasons(request)
    if reasons:
        return SourceAwareGenerationResult(
            request.request_id, _verdict(reasons), reasons, program, None,
            request.claimed_evidence_refs, base_map,
        )

    graph = request.raw["context_graph"]
    policy = request.raw["policy"]
    tier = _priority_tier(request.rule.priority.priority_class)
    instances = []
    for item in graph["instances"]:
        association = item["association"]
        instances.append({
            "instance_id": item["instance_id"],
            "contract_id": item["contract_id"],
            "association": {
                "status": "BOUND",
                "target_entity_id": association["selected_target_entity_id"],
                "zone_id": association["selected_zone_id"],
                "zone_geometry_ref": association["zone_geometry_ref"],
                "coordinate_transform_ref": association["coordinate_transform_ref"],
                "candidate_target_entity_ids": association["candidate_target_entity_ids"],
                "candidate_zone_ids": association["candidate_zone_ids"],
                "evidence_refs": association["evidence_refs"],
                "reason_codes": [],
            },
            "zone_entry": item["zone_entry"],
            "priority_tier": tier,
            "allowed_actions": policy["allowed_actions"],
            "overrides_contracts": item["overrides_contracts"],
        })
    collection_raw = {
        "collection_version": "eblc-indexed-collection-v0.1",
        "collection_id": f"{request.request_id}__indexed_collection",
        "template_program_ref": program.program_id,
        "frames": request.raw["frames"],
        "claim_scope": request.raw["claim_scope"],
        "source_refs": list(request.raw["source_refs"]),
        "action_domain": policy["action_domain"],
        "instances": instances,
        "composition_evidence_refs": policy["composition_evidence_refs"],
    }
    collection = parse_indexed_collection(
        collection_raw, template_catalog={program.program_id: program}
    )
    base_map["generated_program_id"] = program.program_id
    base_map["generated_collection_id"] = collection.collection_id
    base_map["instance_count"] = len(collection.instances)
    return SourceAwareGenerationResult(
        request.request_id,
        "VALIDATED",
        ("SOURCE_AWARE_INDEXED_COLLECTION_GENERATED",),
        program,
        collection,
        request.claimed_evidence_refs,
        base_map,
    )
