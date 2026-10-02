"""Project recorded scene evidence onto an explicitly simulated vehicle.

This module deliberately creates a second vehicle binding.  It never fills the
missing assurance field of the vehicle that recorded the scene.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import hashlib
import json
from math import isfinite
from pathlib import Path
from typing import Any

from guard_synth_eblc.schema_validation import load_json, validate
from guard_synth_eblc.binders import bind_pedestrian_contract
from guard_synth_eblc.translation_validator import validate_translation
from guard_synth_eblc.types import (
    ContextFrame,
    EpistemicKind,
    EvidenceRecord,
    Fact,
    PredicateSpec,
    Priority,
    PriorityClass,
    RuleTemplate,
    SourceClass,
    Truth,
    VehicleProfile,
)

from .assurance_registry import parse_assurance_registry
from .source_authoring import author_generation_request
from .source_aware_generator import SourceAwareGenerationRequest, parse_generation_request


PACKAGE_ROOT = Path(__file__).resolve().parent
MODEL_SCHEMA = PACKAGE_ROOT / "schemas/simulated_assurance_profile.schema.json"
REQUIREMENT_PATH = PACKAGE_ROOT / "fixtures/simulated_corridor_requirement_v0_1.json"
SIMULATION_SCOPE = "SIMULATOR_ONLY_NOT_REAL_VEHICLE_ASSURANCE"
REQUIRED_RECORDED_FIELDS = frozenset({
    "timestamps",
    "ego_pose_and_speed",
    "relevant_actor_tracks",
    "target_zone_or_lane_association",
    "conflict_or_stop_geometry",
    "verified_coordinate_transform",
    "applicable_rule_source_refs",
    "exact_vehicle_binding",
})


class SimulationProjectionError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class SimulatedAssuranceModel:
    profile_id: str
    profile_class: str
    simulation_vehicle_binding_key: str
    scope: str
    maximum_service_deceleration_mps2: float
    response_time_s: float
    position_uncertainty_m: float
    integration_step_s: float
    evidence_ref: str
    source_sha256: str
    source_uri: str
    limitations: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class SimulatedGenerationRequest:
    request: SourceAwareGenerationRequest
    real_vehicle_source_complete: bool
    simulation_projection_source_complete: bool
    recorded_vehicle_binding_key: str
    simulation_vehicle_binding_key: str
    simulation_evidence_ref: str
    profile_source_class: str
    remaining_real_vehicle_gaps: tuple[str, ...]
    coc_claim_evidence_ref: str
    conditional_rule_source_refs: tuple[str, ...]


def _model_bytes(source: Path | dict[str, Any]) -> tuple[dict[str, Any], bytes, str]:
    if isinstance(source, Path):
        payload = source.read_bytes()
        return json.loads(payload), payload, source.resolve().as_uri()
    payload = (json.dumps(source, sort_keys=True, separators=(",", ":")) + "\n").encode()
    return deepcopy(source), payload, "urn:guardsynth:simulated-assurance:inline"


def load_simulated_assurance_model(
    source: Path | dict[str, Any],
) -> SimulatedAssuranceModel:
    raw, payload, source_uri = _model_bytes(source)
    validate(raw, load_json(MODEL_SCHEMA))
    parameters = raw["parameters"]
    deceleration = float(parameters["maximum_service_deceleration_mps2"])
    response = float(parameters["response_time_s"])
    uncertainty = float(parameters["position_uncertainty_m"])
    step = float(parameters["integration_step_s"])
    if not isfinite(deceleration) or deceleration <= 0:
        raise ValueError("deceleration must be finite and positive")
    if not isfinite(response) or response < 0:
        raise ValueError("response time must be finite and non-negative")
    if not isfinite(uncertainty) or uncertainty < 0:
        raise ValueError("position uncertainty must be finite and non-negative")
    if not isfinite(step) or step <= 0:
        raise ValueError("integration step must be finite and positive")
    digest = hashlib.sha256(payload).hexdigest()
    return SimulatedAssuranceModel(
        profile_id=raw["profile_id"],
        profile_class=raw["profile_class"],
        simulation_vehicle_binding_key=raw["simulation_vehicle_binding_key"],
        scope=raw["scope"],
        maximum_service_deceleration_mps2=deceleration,
        response_time_s=response,
        position_uncertainty_m=uncertainty,
        integration_step_s=step,
        evidence_ref=f"simulated-model-sha256:{digest}",
        source_sha256=digest,
        source_uri=source_uri,
        limitations=tuple(raw["limitations"]),
    )


def simulate_full_stop(
    model: SimulatedAssuranceModel,
    *,
    initial_speed_mps: float,
) -> tuple[dict[str, float], ...]:
    """Integrate the model exactly over fixed-size time segments."""
    if (
        isinstance(initial_speed_mps, bool)
        or not isinstance(initial_speed_mps, (int, float))
        or not isfinite(initial_speed_mps)
        or initial_speed_mps < 0
    ):
        raise ValueError("initial speed must be finite and non-negative")
    speed = float(initial_speed_mps)
    position = 0.0
    time_s = 0.0
    trace = [{"time_s": 0.0, "position_m": 0.0, "speed_mps": speed}]
    while time_s < model.response_time_s:
        duration = min(model.integration_step_s, model.response_time_s - time_s)
        position += speed * duration
        time_s += duration
        trace.append({
            "time_s": round(time_s, 12),
            "position_m": position,
            "speed_mps": speed,
        })
    while speed > 0:
        duration = min(
            model.integration_step_s,
            speed / model.maximum_service_deceleration_mps2,
        )
        position += speed * duration - (
            0.5 * model.maximum_service_deceleration_mps2 * duration**2
        )
        speed = max(0.0, speed - model.maximum_service_deceleration_mps2 * duration)
        time_s += duration
        trace.append({
            "time_s": round(time_s, 12),
            "position_m": position,
            "speed_mps": speed,
        })
    return tuple(trace)


def concrete_scene_t0_assignments(
    source_audit: dict[str, Any],
    association_evidence: dict[str, Any],
    *,
    contract_count: int,
) -> dict[tuple[str, int | None], bool | int | float | str]:
    """Return the complete source-backed frame-0 input assignment."""
    if contract_count < 1:
        raise ValueError("contract count must be positive")
    ego = _require_status(source_audit, "ego_pose_and_speed")
    front_extent = association_evidence.get("vehicle_geometry", {}).get(
        "ego_front_extent_m"
    )
    timestamp_us = association_evidence.get("event_timestamp_us")
    if (
        isinstance(front_extent, bool)
        or not isinstance(front_extent, (int, float))
        or not isfinite(front_extent)
        or isinstance(timestamp_us, bool)
        or not isinstance(timestamp_us, int)
    ):
        raise SimulationProjectionError("MISSING_CONCRETE_T0_EGO_OR_TIMESTAMP")
    timestamp_s = timestamp_us / 1_000_000.0
    assignments: dict[tuple[str, int | None], bool | int | float | str] = {}
    for index in range(contract_count):
        prefix = f"c{index}__"
        values: dict[str, bool | int | float | str] = {
            "raw_truth": "TRUE",
            "epistemic": "DERIVED",
            "timestamp": timestamp_s,
            "fact_timestamp": timestamp_s,
            "fact_maximum_age": 0.2,
            "scope_valid": True,
            "unit_ok": True,
            "coordinate_ok": True,
            "target_ok": True,
            "ego_front_x": float(front_extent),
            "ego_speed": float(ego["speed_mps"]),
            "safe_progress": False,
        }
        assignments.update({(f"{prefix}{name}", 0): value for name, value in values.items()})
    assignments[("safe_progress_action_exists", 0)] = False
    return assignments


def build_reference_translation_cases(
    *,
    source_audit: dict[str, Any],
    association_evidence: dict[str, Any],
    model_source: Path | dict[str, Any],
    collection: dict[str, Any],
) -> dict[str, Any]:
    """Replay generated instances in the three independent EBLC v0 targets."""
    instances = collection.get("instances")
    if not isinstance(instances, list) or not instances:
        raise SimulationProjectionError("MISSING_GENERATED_CONTRACT_INSTANCES")
    model = load_simulated_assurance_model(model_source)
    rule, predicate, _ = simulation_semantics()
    profile = VehicleProfile(
        profile_id=model.profile_id,
        maximum_service_deceleration_mps2=model.maximum_service_deceleration_mps2,
        response_time_s=model.response_time_s,
        position_uncertainty_m=model.position_uncertainty_m,
        evidence_ref=model.evidence_ref,
    )
    ego = _require_status(source_audit, "ego_pose_and_speed")
    timestamp_us = association_evidence.get("event_timestamp_us")
    front_extent = association_evidence.get("vehicle_geometry", {}).get(
        "ego_front_extent_m"
    )
    if (
        isinstance(timestamp_us, bool)
        or not isinstance(timestamp_us, int)
        or isinstance(front_extent, bool)
        or not isinstance(front_extent, (int, float))
        or not isfinite(front_extent)
    ):
        raise SimulationProjectionError("MISSING_REFERENCE_TRANSLATION_INPUT")
    timestamp_s = timestamp_us / 1_000_000.0
    records: list[dict[str, Any]] = []
    engine: str | None = None
    engine_version: str | None = None
    for instance in instances:
        association = instance.get("association", {})
        zone_entry = instance.get("zone_entry", {})
        frame = ContextFrame(
            timestamp_s=timestamp_s,
            hazard=Fact(
                Truth.TRUE,
                EpistemicKind.DERIVED,
                str(association_evidence.get("association_id", "")),
                timestamp_s,
                predicate.maximum_age_s,
            ),
            ego_front_x_m=float(front_extent),
            ego_speed_mps=float(ego["speed_mps"]),
            zone_entry_x_m=float(zone_entry["value"]),
            target_entity_id=str(association["target_entity_id"]),
            zone_id=str(association["zone_id"]),
            coordinate_frame=str(zone_entry["frame"]),
            distance_unit=str(zone_entry["unit"]),
        )
        outcome = bind_pedestrian_contract(rule, predicate, frame, profile)
        if outcome.contract is None:
            raise SimulationProjectionError(
                "REFERENCE_CONTRACT_BINDING_FAILED:" + ",".join(outcome.reason_codes)
            )
        comparison = validate_translation(
            outcome.contract,
            {f"{instance['contract_id']}:recorded-frame-0": (frame,)},
        )
        engine = str(comparison["engine"])
        engine_version = str(comparison["engine_version"])
        record = dict(comparison["records"][0])
        record["contract_id"] = instance["contract_id"]
        records.append(record)
    count = len(records)
    runtime_matches = sum(record["canonical_runtime_agree"] for record in records)
    bounded_matches = sum(
        record["canonical_bounded_target_agree"] for record in records
    )
    return {
        "engine": engine,
        "engine_version": engine_version,
        "contract_count": count,
        "trace_count": count,
        "canonical_runtime_matches": runtime_matches,
        "canonical_runtime_agreement": runtime_matches / count,
        "canonical_bounded_target_matches": bounded_matches,
        "canonical_bounded_target_agreement": bounded_matches / count,
        "records": records,
        "claim_boundary": (
            "RECORDED_FRAME_TRANSLATION_AGREEMENT_NOT_INDEPENDENT_"
            "VEHICLE_SAFETY_VERIFICATION"
        ),
    }


def simulation_registry(model: SimulatedAssuranceModel):
    return parse_assurance_registry({
        "registry_version": "guardsynth-vehicle-assurance-registry-v0.1",
        "registry_id": "guardsynth-simulation-registry-v0.1",
        "profiles": [{
            "profile_id": model.profile_id,
            "vehicle_binding_key": model.simulation_vehicle_binding_key,
            "maximum_service_deceleration_mps2": model.maximum_service_deceleration_mps2,
            "response_time_s": model.response_time_s,
            "position_uncertainty_m": model.position_uncertainty_m,
            "evidence": {
                "evidence_ref": model.evidence_ref,
                "source_class": "SIMULATION_MODEL_SPECIFICATION",
                "uri": model.source_uri,
                "version": "guardsynth-simulated-longitudinal-model-v0.1",
                "sha256": model.source_sha256,
                "scope": model.scope,
            },
        }],
    })


def simulation_semantics() -> tuple[RuleTemplate, PredicateSpec, str]:
    raw = load_json(REQUIREMENT_PATH)
    digest = hashlib.sha256(REQUIREMENT_PATH.read_bytes()).hexdigest()
    evidence = raw["evidence_id"]
    rule = RuleTemplate(
        rule_id=raw["rule_id"],
        source=EvidenceRecord(
            evidence_id=evidence,
            source_class=SourceClass.SYSTEM_REQUIREMENT,
            uri=REQUIREMENT_PATH.resolve().as_uri(),
            version=raw["requirement_version"],
            scope=raw["scope"],
            section="SIMULATED-CORRIDOR-STOP",
            content_hash=digest,
        ),
        scope=raw["scope"],
        precondition="geometric_pedestrian_corridor_overlap == TRUE",
        exception="scope_exception == TRUE",
        subject_role="EgoVehicle",
        target_role="PedestrianTrack",
        zone_role="DynamicEgoCorridorOverlapZone",
        binder_id="source_linked_geometric_set_binder",
        activation=raw["activation"],
        invariant=raw["invariant"],
        bound="simulated delayed constant-deceleration stopping bound",
        release="two consecutive fresh FALSE observations",
        reactivation="fresh TRUE after RELEASED",
        expiry="scope invalid or explicit expiry time reached",
        fallback=raw["fallback"],
        fallback_approved=bool(raw["fallback_approved"]),
        observability=(raw["predicate_id"],),
        priority=Priority(PriorityClass.MANDATORY_SYSTEM, ()),
        stop_margin_m=float(raw["stop_margin_m"]),
        release_clear_frames=int(raw["release_clear_frames"]),
    )
    predicate = PredicateSpec(
        predicate_id=raw["predicate_id"],
        argument_types=("PedestrianTrack", "DynamicEgoCorridorOverlapZone"),
        measurement_or_derivation_fn="observed_oriented_bbox_ego_corridor_overlap",
        allowed_sources=(EpistemicKind.DERIVED,),
        coordinate_frame=raw["coordinate_frame"],
        update_rate_hz=10.0,
        maximum_latency_s=0.1,
        maximum_age_s=float(raw["maximum_age_s"]),
        uncertainty_model="four_valued_with_explicit_conflict",
        monitorability="NOW",
        calibration_id="SOURCE_LINKED_DATASET_TRACKS_NOT_REALTIME_SENSOR",
        failure_value=Truth.UNKNOWN,
    )
    return rule, predicate, evidence


def _require_status(container: dict[str, Any], field: str) -> dict[str, Any]:
    value = container.get("field_status", {}).get(field)
    if not isinstance(value, dict) or value.get("status") != "AVAILABLE_SOURCE_LINKED":
        raise SimulationProjectionError(f"SCENE_FIELDS_INCOMPLETE:{field}")
    return value


def build_simulated_generation_request(
    *,
    base_request: dict[str, Any],
    source_audit: dict[str, Any],
    association_evidence: dict[str, Any],
    rule_evidence: dict[str, Any],
    coc_claim_evidence: dict[str, Any],
    model_source: Path | dict[str, Any],
    request_id: str,
) -> SimulatedGenerationRequest:
    """Build an executable request without changing recorded-vehicle closure."""
    scene_ref = source_audit.get("scene_ref")
    if not scene_ref or any(
        item.get("scene_ref") != scene_ref
        for item in (association_evidence, rule_evidence)
    ):
        raise SimulationProjectionError("SCENE_REF_MISMATCH")
    missing = tuple(source_audit.get("missing_fields", ()))
    if (
        set(source_audit.get("available_fields", ())) != REQUIRED_RECORDED_FIELDS
        or missing != ("source_bearing_vehicle_assurance_profile",)
        or source_audit.get("synthesized_required_values")
    ):
        raise SimulationProjectionError("SCENE_FIELDS_INCOMPLETE")
    if source_audit.get("source_complete") is not False:
        raise SimulationProjectionError("RECORDED_SOURCE_COMPLETENESS_MUST_REMAIN_FALSE")
    if association_evidence.get("status") != "AVAILABLE_SOURCE_LINKED":
        raise SimulationProjectionError("ASSOCIATION_NOT_SOURCE_LINKED")
    if association_evidence.get("collision_prediction_claimed") is not False:
        raise SimulationProjectionError("ASSOCIATION_CLAIM_BOUNDARY_MISSING")
    if (
        rule_evidence.get("status") != "AVAILABLE_SOURCE_LINKED"
        or rule_evidence.get("applicability_verdict") != "CONDITIONALLY_APPLICABLE"
        or rule_evidence.get("numeric_vehicle_bound_derived") is not False
    ):
        raise SimulationProjectionError("RULE_EVIDENCE_NOT_CONDITIONALLY_SOURCE_LINKED")
    coc_digest = coc_claim_evidence.get("text_sha256")
    if not (
        coc_claim_evidence.get("present") is True
        and coc_claim_evidence.get("epistemic_kind") == "CLAIMED"
        and coc_claim_evidence.get("text_included") is False
        and isinstance(coc_digest, str)
        and len(coc_digest) == 64
        and all(character in "0123456789abcdef" for character in coc_digest)
    ):
        raise SimulationProjectionError("INVALID_OR_EXPOSED_COC_CLAIM_EVIDENCE")

    association_field = _require_status(source_audit, "target_zone_or_lane_association")
    geometry = _require_status(source_audit, "conflict_or_stop_geometry")
    transform = _require_status(source_audit, "verified_coordinate_transform")
    recorded_binding = _require_status(source_audit, "exact_vehicle_binding")
    _require_status(source_audit, "ego_pose_and_speed")
    model = load_simulated_assurance_model(model_source)
    if model.simulation_vehicle_binding_key == recorded_binding["vehicle_binding_key"]:
        raise SimulationProjectionError("SIMULATION_BINDING_MUST_DIFFER_FROM_RECORDED_RIG")

    tracks = tuple(association_evidence.get("associated_track_id_sha256", ()))
    if (
        len(tracks) < 2
        or tuple(association_field.get("track_id_sha256", ())) != tracks
        or len(set(tracks)) != len(tracks)
    ):
        raise SimulationProjectionError("ASSOCIATION_SET_MISMATCH")
    timestamp_s = float(association_evidence["event_timestamp_us"]) / 1_000_000.0
    zone_identity = str(association_evidence["association_id"]).removeprefix("sha256:")[:16]
    association_ref = association_field["evidence_ref"]
    association_refs = list(dict.fromkeys([
        association_ref,
        *association_evidence.get("evidence_refs", ()),
    ]))
    grounded_scenes = []
    for index, track_hash in enumerate(tracks):
        grounded_scenes.append({
            "instance_id": f"scene_{index}_track_{track_hash[:12]}",
            "contract_id": f"C{index}",
            "timestamp_s": timestamp_s,
            "hazard": {
                "truth": "TRUE",
                "epistemic_kind": "DERIVED",
                "evidence_ref": association_ref,
                "timestamp_s": timestamp_s,
                "maximum_age_s": 0.2,
            },
            "association": {
                "target_entity_id": f"track_{track_hash}",
                "zone_id": f"dynamic_corridor_{zone_identity}",
                "evidence_ref": association_ref,
                "evidence_refs": association_refs,
            },
            "zone_geometry": {
                "entry_x_m": float(geometry["entry_x_m"]),
                "frame": association_field["zone"]["coordinate_frame"],
                "evidence_ref": geometry["evidence_ref"],
            },
            "coordinate_transform": {
                "verified": True,
                "evidence_ref": transform["evidence_ref"],
            },
            "vehicle_binding_key": model.simulation_vehicle_binding_key,
            "assurance_scope": model.scope,
            "reason_codes": [],
        })

    rule, predicate, requirement_ref = simulation_semantics()
    raw_base = deepcopy(base_request)
    raw_base["rule_template_ref"] = rule.rule_id
    raw_base["predicate_spec_ref"] = predicate.predicate_id
    raw_base["claim_scope"] = (
        "RECORDED_SCENE_EVIDENCE_PROJECTED_ON_SIMULATED_VEHICLE_NOT_REAL_VEHICLE_SAFETY"
    )
    raw_base["policy"]["predicate_evidence_ref"] = requirement_ref
    if requirement_ref not in raw_base["source_refs"]:
        raw_base["source_refs"].append(requirement_ref)
    registry = simulation_registry(model)
    authored = author_generation_request(
        base_request=raw_base,
        grounded_scenes=grounded_scenes,
        registry=registry,
        request_id=request_id,
        rule_catalog={rule.rule_id: rule},
        predicate_catalog={predicate.predicate_id: predicate},
    )

    coc_ref = f"coc-sha256:{coc_digest}"
    authored["source_refs"].append(coc_ref)
    authored["source_refs"] = sorted(authored["source_refs"])
    authored["context_graph"]["coc_claims"] = [{
        "claim_id": "alpamayo_coc_claim",
        "epistemic_kind": "CLAIMED",
        "evidence_ref": coc_ref,
    }]
    request = parse_generation_request(
        authored,
        rule_catalog={rule.rule_id: rule},
        predicate_catalog={predicate.predicate_id: predicate},
    )
    return SimulatedGenerationRequest(
        request=request,
        real_vehicle_source_complete=False,
        simulation_projection_source_complete=True,
        recorded_vehicle_binding_key=recorded_binding["vehicle_binding_key"],
        simulation_vehicle_binding_key=model.simulation_vehicle_binding_key,
        simulation_evidence_ref=model.evidence_ref,
        profile_source_class="SIMULATION_MODEL_SPECIFICATION",
        remaining_real_vehicle_gaps=missing,
        coc_claim_evidence_ref=coc_ref,
        conditional_rule_source_refs=tuple(
            item["source_id"] for item in rule_evidence["rule_source_refs"]
        ),
    )
