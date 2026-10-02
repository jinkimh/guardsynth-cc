"""Fail-closed audit for source-bearing vehicle assurance candidates."""

from __future__ import annotations

from math import isfinite
from typing import Any


VEHICLE_ASSURANCE_AUDIT_VERSION = "guardsynth-vehicle-assurance-audit-v0.1"
_VALIDATED_SOURCE_KINDS = {"CONTROL_STACK_VALIDATED", "OEM_VALIDATED"}
_REJECTION_BY_KIND = {
    "OBSERVED_EGOMOTION": "OBSERVATION_NOT_GUARANTEE",
    "DERIVED_COC_RESPONSE_LATENCY": "BEHAVIOR_RESPONSE_NOT_ACTUATOR_ASSURANCE",
    "PLATFORM_INTERFACE_DOCUMENTATION": "INTERFACE_DOCUMENTATION_NOT_BOUND_ASSURANCE",
}


def _positive_number(value: Any) -> bool:
    return (
        not isinstance(value, bool)
        and isinstance(value, (int, float))
        and isfinite(value)
        and value > 0
    )


def _nonnegative_number(value: Any) -> bool:
    return (
        not isinstance(value, bool)
        and isinstance(value, (int, float))
        and isfinite(value)
        and value >= 0
    )


def _valid_sha256(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _validated_profile_reason(
    candidate: dict[str, Any], vehicle_binding_key: str
) -> str | None:
    if candidate.get("vehicle_binding_key") != vehicle_binding_key:
        return "VEHICLE_BINDING_MISMATCH"
    required_text = ("candidate_id", "source_ref", "validation_method")
    if not all(isinstance(candidate.get(field), str) and candidate[field] for field in required_text):
        return "INCOMPLETE_ASSURANCE_PROVENANCE"
    if not _valid_sha256(candidate.get("source_sha256")):
        return "INCOMPLETE_ASSURANCE_PROVENANCE"
    if not (
        _positive_number(candidate.get("minimum_guaranteed_deceleration_mps2"))
        and _nonnegative_number(
            candidate.get("maximum_command_to_deceleration_latency_s")
        )
        and _positive_number(candidate.get("maximum_abs_jerk_mps3"))
        and isinstance(candidate.get("operating_conditions"), dict)
        and bool(candidate["operating_conditions"])
        and isinstance(candidate.get("uncertainty_model"), dict)
        and bool(candidate["uncertainty_model"])
    ):
        return "INCOMPLETE_ASSURANCE_BOUNDS"
    return None


def audit_vehicle_assurance_candidates(
    *, vehicle_binding_key: str, candidates: list[dict[str, Any]]
) -> dict[str, Any]:
    """Accept only a complete validated profile bound to the exact vehicle key."""
    if not isinstance(vehicle_binding_key, str) or not vehicle_binding_key:
        raise ValueError("INVALID_VEHICLE_BINDING_KEY")
    if not isinstance(candidates, list):
        raise ValueError("INVALID_ASSURANCE_CANDIDATES")

    accepted: list[dict[str, Any]] = []
    rejected: list[dict[str, str]] = []
    for candidate in candidates:
        if not isinstance(candidate, dict):
            raise ValueError("INVALID_ASSURANCE_CANDIDATE")
        candidate_id = str(candidate.get("candidate_id", ""))
        source_kind = str(candidate.get("source_kind", ""))
        reason = _REJECTION_BY_KIND.get(source_kind)
        if reason is None and source_kind in _VALIDATED_SOURCE_KINDS:
            reason = _validated_profile_reason(candidate, vehicle_binding_key)
        elif reason is None:
            reason = "UNAPPROVED_ASSURANCE_SOURCE_KIND"
        if reason is None:
            accepted.append(dict(candidate))
        else:
            rejected.append({
                "candidate_id": candidate_id,
                "source_kind": source_kind,
                "reason_code": reason,
            })

    base = {
        "audit_version": VEHICLE_ASSURANCE_AUDIT_VERSION,
        "vehicle_binding_key": vehicle_binding_key,
        "rejected_candidates": rejected,
        "synthetic_value_fill_performed": False,
        "observed_performance_promoted_to_guarantee": False,
        "vehicle_safety_validated": False,
    }
    if len(accepted) == 1:
        profile = accepted[0]
        return {
            **base,
            "status": "AVAILABLE_SOURCE_LINKED",
            "reason_code": None,
            "accepted_candidate_id": profile["candidate_id"],
            "assurance_profile": profile,
            "contract_generation_allowed": True,
            "claim_scope": "SOURCE_BOUND_VALIDATED_ASSURANCE_PROFILE_NOT_VEHICLE_SAFETY_PROOF",
        }
    if len(accepted) > 1:
        return {
            **base,
            "status": "CONFLICT",
            "reason_code": "MULTIPLE_VALIDATED_ASSURANCE_PROFILES",
            "accepted_candidate_ids": [item["candidate_id"] for item in accepted],
            "contract_generation_allowed": False,
            "claim_scope": "ASSURANCE_PROFILE_CONFLICT_NOT_VEHICLE_SAFETY_PROOF",
        }
    return {
        **base,
        "status": "REVIEW_REQUIRED",
        "reason_code": "MISSING_SOURCE_BEARING_VEHICLE_ASSURANCE_PROFILE",
        "contract_generation_allowed": False,
        "required_evidence_manifest": {
            "accepted_source_kind": sorted(_VALIDATED_SOURCE_KINDS),
            "required_fields": [
                "vehicle_binding_key",
                "source_ref",
                "source_sha256",
                "validation_method",
                "minimum_guaranteed_deceleration_mps2",
                "maximum_command_to_deceleration_latency_s",
                "maximum_abs_jerk_mps3",
                "operating_conditions",
                "uncertainty_model",
            ],
            "runtime_evidence": [
                "vehicle_or_dbw_identity",
                "actuation_interface_capabilities",
                "controlled_brake_test_or_oem_validation",
            ],
        },
        "claim_scope": "ASSURANCE_SOURCE_GAP_AUDIT_NOT_NUMERIC_BOUND_OR_VEHICLE_SAFETY",
    }
