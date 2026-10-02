"""Source closure for one derived scene projected onto a simulation requirement."""

from __future__ import annotations

import hashlib
import json
from math import isfinite
from pathlib import Path
from typing import Any

from .dry_run_readiness import REQUIRED_SCENE_FIELDS
from .geometric_association import GEOMETRIC_ASSOCIATION_VERSION
from .nvidia_source_bundle import SOURCE_BUNDLE_VERSION


SYSTEM_REQUIREMENT_APPLICABILITY_VERSION = (
    "guardsynth-system-requirement-applicability-v0.1"
)
SCENE_EVIDENCE_CLOSURE_VERSION = "guardsynth-derived-event-source-closure-v0.1"


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _valid_sha256(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _source_ref(digest: str, pointer: str) -> str:
    if not _valid_sha256(digest):
        raise ValueError("INVALID_EVIDENCE_DOCUMENT_SHA256")
    return f"restricted-sha256:{digest}#{pointer}"


def build_system_requirement_applicability(
    *,
    scene_ref: str,
    association: dict[str, Any],
    requirement_path: Path,
) -> dict[str, Any]:
    """Bind the simulation-only corridor requirement to geometric evidence."""
    if not isinstance(scene_ref, str) or not scene_ref:
        raise ValueError("INVALID_SCENE_REF")
    track_ids = association.get("associated_track_id_sha256")
    if (
        association.get("association_version") != GEOMETRIC_ASSOCIATION_VERSION
        or association.get("scene_ref") != scene_ref
        or association.get("status") != "AVAILABLE_SOURCE_LINKED"
        or association.get("target_kind") != "SET"
        or not isinstance(track_ids, list)
        or not track_ids
        or len(track_ids) != association.get("association_cardinality")
        or association.get("collision_prediction_claimed") is not False
        or association.get("crosswalk_or_legal_zone_claimed") is not False
    ):
        raise ValueError("ASSOCIATION_NOT_ELIGIBLE_FOR_SYSTEM_REQUIREMENT")

    payload = requirement_path.read_bytes()
    requirement = json.loads(payload)
    required = (
        "requirement_version",
        "evidence_id",
        "rule_id",
        "predicate_id",
        "scope",
        "activation",
        "invariant",
        "claim_boundary",
    )
    if any(not isinstance(requirement.get(name), str) or not requirement[name] for name in required):
        raise ValueError("INVALID_SIMULATION_SYSTEM_REQUIREMENT")
    if requirement["claim_boundary"] != (
        "SYSTEM_REQUIREMENT_FOR_SIMULATION_NOT_LEGAL_INTERPRETATION_OR_REAL_VEHICLE_SAFETY"
    ):
        raise ValueError("INVALID_SIMULATION_REQUIREMENT_CLAIM_BOUNDARY")

    return {
        "system_requirement_applicability_version": (
            SYSTEM_REQUIREMENT_APPLICABILITY_VERSION
        ),
        "scene_ref": scene_ref,
        "status": "AVAILABLE_SOURCE_LINKED",
        "reason_code": None,
        "applicability_verdict": "CONDITIONALLY_APPLICABLE",
        "primary_rule_source_id": requirement["evidence_id"],
        "rule_source_refs": [{
            "source_id": requirement["evidence_id"],
            "source_class": "SYSTEM_REQUIREMENT",
            "uri": requirement_path.resolve().as_uri(),
            "version": requirement["requirement_version"],
            "scope": requirement["scope"],
            "snapshot_sha256": _sha256_bytes(payload),
        }],
        "observed_applicability_conditions": [
            "SOURCE_LINKED_ACTOR_SET_IN_EGO_CORRIDOR"
        ],
        "association_id": association.get("association_id"),
        "associated_track_id_sha256": list(track_ids),
        "coc_used_as_observed_or_normative_fact": False,
        "legal_authority_claimed": False,
        "numeric_vehicle_bound_derived": False,
        "unsourced_normative_or_numeric_value_count": 0,
        "vehicle_safety_validated": False,
        "claim_scope": (
            "SOURCE_LINKED_SIMULATION_SYSTEM_REQUIREMENT_APPLICABILITY_"
            "NOT_LEGAL_RULE_COLLISION_PREDICTION_OR_VEHICLE_SAFETY"
        ),
    }


def build_event_scene_source_closure(
    *,
    scene_ref: str,
    adapter_candidate: dict[str, Any],
    adapter_candidate_index: int,
    adapter_sha256: str,
    source_bundle: dict[str, Any],
    source_bundle_sha256: str,
    association: dict[str, Any],
    association_sha256: str,
    applicability: dict[str, Any],
    applicability_sha256: str,
) -> dict[str, Any]:
    """Validate eight recorded-scene fields while preserving vehicle assurance as missing."""
    for digest in (
        adapter_sha256,
        source_bundle_sha256,
        association_sha256,
        applicability_sha256,
    ):
        if not _valid_sha256(digest):
            raise ValueError("INVALID_EVIDENCE_DOCUMENT_SHA256")
    if (
        adapter_candidate.get("candidate_id") != scene_ref
        or adapter_candidate.get("context_schema_valid") is not True
        or adapter_candidate.get("raw_clip_id_included") is not False
    ):
        raise ValueError("ADAPTER_SCENE_MISMATCH")
    graph = adapter_candidate.get("context_graph")
    ego = adapter_candidate.get("ego_state")
    actors = adapter_candidate.get("association_candidates")
    if not isinstance(graph, dict) or not isinstance(ego, dict) or not isinstance(actors, list):
        raise ValueError("INVALID_ADAPTER_SCENE")
    timestamp_s = graph.get("timestamp_s")
    pose = ego.get("pose_relative_t0_m")
    speed = ego.get("speed_mps")
    if (
        not isinstance(timestamp_s, (int, float))
        or not isfinite(float(timestamp_s))
        or not isinstance(pose, list)
        or len(pose) != 3
        or any(not isinstance(value, (int, float)) or not isfinite(float(value)) for value in pose)
        or not isinstance(speed, (int, float))
        or not isfinite(float(speed))
        or not actors
        or any(not isinstance(actor.get("track_samples"), list) or not actor["track_samples"] for actor in actors)
    ):
        raise ValueError("INCOMPLETE_ADAPTER_TIMESTAMP_EGO_OR_TRACKS")

    event_timestamp_us = association.get("event_timestamp_us")
    candidate_track_ids = {actor.get("track_id_sha256") for actor in actors}
    associated_track_ids = association.get("associated_track_id_sha256")
    zone = association.get("zone")
    if (
        association.get("association_version") != GEOMETRIC_ASSOCIATION_VERSION
        or association.get("scene_ref") != scene_ref
        or association.get("status") != "AVAILABLE_SOURCE_LINKED"
        or not isinstance(event_timestamp_us, int)
        or abs(float(timestamp_s) - event_timestamp_us / 1_000_000.0) > 1e-9
        or not isinstance(associated_track_ids, list)
        or not associated_track_ids
        or not set(associated_track_ids).issubset(candidate_track_ids)
        or not isinstance(zone, dict)
        or zone.get("coordinate_frame") != "dataset_rig"
    ):
        raise ValueError("ASSOCIATION_SCENE_OR_TRACK_SET_MISMATCH")
    x_interval = zone.get("x_interval_m")
    if (
        not isinstance(x_interval, list)
        or len(x_interval) != 2
        or any(not isinstance(value, (int, float)) or not isfinite(float(value)) for value in x_interval)
    ):
        raise ValueError("INVALID_ASSOCIATION_ZONE_GEOMETRY")

    transform = source_bundle.get("coordinate_transform")
    binding = source_bundle.get("vehicle_binding")
    matrix = transform.get("matrix_4x4") if isinstance(transform, dict) else None
    matrix_valid = (
        isinstance(matrix, list)
        and len(matrix) == 4
        and all(isinstance(row, list) and len(row) == 4 for row in matrix)
        and all(
            isinstance(value, (int, float)) and isfinite(float(value))
            for row in matrix
            for value in row
        )
    )
    closure_error = (
        transform.get("inverse_closure_max_abs_error")
        if isinstance(transform, dict)
        else None
    )
    binding_key = binding.get("vehicle_binding_key") if isinstance(binding, dict) else None
    if (
        source_bundle.get("source_bundle_version") != SOURCE_BUNDLE_VERSION
        or source_bundle.get("scene_ref") != scene_ref
        or source_bundle.get("clip_id_sha256") != adapter_candidate.get("clip_id_sha256")
        or not isinstance(transform, dict)
        or transform.get("status") != "AVAILABLE_SOURCE_LINKED"
        or transform.get("source_frame") != "dataset_rig_at_event"
        or transform.get("target_frame") != "ego_at_model_t0"
        or transform.get("event_timestamp_us") != event_timestamp_us
        or not matrix_valid
        or not isinstance(closure_error, (int, float))
        or not isfinite(float(closure_error))
        or not 0 <= float(closure_error) <= 1e-9
        or not isinstance(binding, dict)
        or binding.get("status") != "AVAILABLE_SOURCE_LINKED"
        or not isinstance(binding_key, str)
        or not binding_key.startswith("nvidia-rig-config-sha256:")
        or not _valid_sha256(binding_key.removeprefix("nvidia-rig-config-sha256:"))
        or binding.get("binding_scope") != "DATASET_CLIP_RIG_CONFIGURATION_NOT_VIN"
        or binding.get("components", {}).get("clip_id_sha256") != adapter_candidate.get("clip_id_sha256")
    ):
        raise ValueError("SOURCE_BUNDLE_SCENE_OR_CLIP_MISMATCH")

    sources = applicability.get("rule_source_refs")
    if (
        applicability.get("system_requirement_applicability_version")
        != SYSTEM_REQUIREMENT_APPLICABILITY_VERSION
        or applicability.get("scene_ref") != scene_ref
        or applicability.get("status") != "AVAILABLE_SOURCE_LINKED"
        or applicability.get("applicability_verdict") != "CONDITIONALLY_APPLICABLE"
        or applicability.get("association_id") != association.get("association_id")
        or applicability.get("associated_track_id_sha256") != associated_track_ids
        or applicability.get("legal_authority_claimed") is not False
        or applicability.get("numeric_vehicle_bound_derived") is not False
        or not isinstance(sources, list)
        or not sources
    ):
        raise ValueError("SYSTEM_REQUIREMENT_APPLICABILITY_MISMATCH")

    adapter_prefix = f"/candidates/{adapter_candidate_index}"
    field_status = {
        "timestamps": {
            "status": "AVAILABLE_SOURCE_LINKED",
            "evidence_ref": _source_ref(adapter_sha256, adapter_prefix + "/context_graph/timestamp_s"),
            "timestamp_s": float(timestamp_s),
            "event_timestamp_us": event_timestamp_us,
        },
        "ego_pose_and_speed": {
            "status": "AVAILABLE_SOURCE_LINKED",
            "evidence_ref": _source_ref(adapter_sha256, adapter_prefix + "/ego_state"),
            "pose_relative_t0_m": [float(value) for value in pose],
            "speed_mps": float(speed),
            "relative_time_s": float(ego["relative_time_s"]),
            "derivation": str(ego.get("derivation", "")),
        },
        "relevant_actor_tracks": {
            "status": "AVAILABLE_SOURCE_LINKED",
            "evidence_ref": _source_ref(adapter_sha256, adapter_prefix + "/association_candidates"),
            "candidate_count": len(actors),
            "time_series_preserved": True,
        },
        "target_zone_or_lane_association": {
            "status": "AVAILABLE_SOURCE_LINKED",
            "evidence_ref": _source_ref(association_sha256, "/"),
            "target_kind": "SET",
            "track_id_sha256": list(associated_track_ids),
            "association_cardinality": len(associated_track_ids),
            "zone": dict(zone),
        },
        "conflict_or_stop_geometry": {
            "status": "AVAILABLE_SOURCE_LINKED",
            "evidence_ref": _source_ref(association_sha256, "/zone"),
            "kind": str(zone.get("kind", "")),
            "entry_x_m": float(x_interval[0]),
            "coordinate_frame": "dataset_rig",
            "crosswalk_or_legal_zone_claimed": False,
        },
        "verified_coordinate_transform": {
            "status": "AVAILABLE_SOURCE_LINKED",
            "evidence_ref": _source_ref(source_bundle_sha256, "/coordinate_transform"),
            "source_frame": transform["source_frame"],
            "target_frame": transform["target_frame"],
            "inverse_closure_max_abs_error": float(transform["inverse_closure_max_abs_error"]),
        },
        "applicable_rule_source_refs": {
            "status": "AVAILABLE_SOURCE_LINKED",
            "evidence_ref": _source_ref(applicability_sha256, "/"),
            "applicability_verdict": "CONDITIONALLY_APPLICABLE",
            "primary_rule_source_id": applicability["primary_rule_source_id"],
            "rule_source_refs": [dict(source) for source in sources],
            "legal_authority_claimed": False,
        },
        "exact_vehicle_binding": {
            "status": "AVAILABLE_SOURCE_LINKED",
            "evidence_ref": _source_ref(source_bundle_sha256, "/vehicle_binding"),
            "vehicle_binding_key": binding["vehicle_binding_key"],
            "binding_scope": binding["binding_scope"],
        },
        "source_bearing_vehicle_assurance_profile": {
            "status": "REVIEW_REQUIRED",
            "reason_code": "MISSING_VEHICLE_ASSURANCE_PROFILE_DEFERRED_TO_M21",
        },
    }
    available = [
        field for field in REQUIRED_SCENE_FIELDS
        if field_status[field]["status"] == "AVAILABLE_SOURCE_LINKED"
    ]
    missing = [field for field in REQUIRED_SCENE_FIELDS if field not in available]
    return {
        "closure_version": SCENE_EVIDENCE_CLOSURE_VERSION,
        "scene_ref": scene_ref,
        "adapter_candidate_index": adapter_candidate_index,
        "input_class": "LICENSE_RESTRICTED",
        "field_status": field_status,
        "available_fields": available,
        "missing_fields": missing,
        "reason_codes": [field_status[field]["reason_code"] for field in missing],
        "source_complete": False,
        "contract_generation_allowed": False,
        "simulation_projection_allowed": len(available) == 8 and missing == [
            "source_bearing_vehicle_assurance_profile"
        ],
        "synthesized_required_values": [],
        "raw_identifiers_included": False,
        "legal_authority_claimed": False,
        "vehicle_safety_validated": False,
        "claim_scope": (
            "EIGHT_RECORDED_SCENE_FIELDS_FOR_SIMULATION_PROJECTION_"
            "NOT_REAL_VEHICLE_SOURCE_CLOSURE_OR_SAFETY"
        ),
    }
