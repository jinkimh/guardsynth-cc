"""Explicit Python finite-state fallback for environments without Z3.

This module preserves the original bounded target implementation. Its output
must never be labelled SMT because it uses Python control flow and exhaustive
input enumeration rather than a solver encoding.
"""

from __future__ import annotations

from itertools import product
from math import isfinite, sqrt
from typing import Iterable

from .types import BoundContract, ContextFrame, Lifecycle, MonitorStep, TraceResult, Truth, Verdict


ENGINE = "EXHAUSTIVE_FINITE_STATE_ENUMERATOR"
ENGINE_VERSION = "deterministic-v0.1"
_LIVE_NAMES = {"ACTIVE", "MAINTAINED", "REACTIVATED"}
_E = 1e-9
_FLOAT_ROUNDOFF = 1e-15


def _enumerator_input_error(contract: BoundContract, samples: tuple[ContextFrame, ...]) -> str | None:
    contract_values = (
        contract.zone_entry_x_m,
        contract.stop_position_x_m,
        contract.stop_margin_m,
        contract.predicate_maximum_age_s,
        contract.maximum_service_deceleration_mps2,
        contract.response_time_s,
        contract.position_uncertainty_m,
    )
    if not all(isfinite(value) for value in contract_values):
        return "NONFINITE_BOUND_CONTRACT"
    if (
        contract.stop_margin_m < 0
        or contract.predicate_maximum_age_s < 0
        or contract.maximum_service_deceleration_mps2 <= 0
        or contract.response_time_s < 0
        or contract.position_uncertainty_m < 0
        or contract.release_clear_frames < 1
    ):
        return "INVALID_BOUND_CONTRACT_RANGE"
    if contract.expiry_timestamp_s is not None and not isfinite(contract.expiry_timestamp_s):
        return "NONFINITE_BOUND_CONTRACT"
    if not samples:
        return "EMPTY_TRACE"
    previous: float | None = None
    for frame in samples:
        values = (
            frame.timestamp_s,
            frame.hazard.timestamp_s,
            frame.hazard.maximum_age_s,
            frame.ego_front_x_m,
            frame.ego_speed_mps,
            frame.zone_entry_x_m,
        )
        if not all(isfinite(value) for value in values):
            return "NONFINITE_SCENE_VALUE"
        if (
            frame.timestamp_s < 0
            or frame.hazard.timestamp_s < 0
            or frame.hazard.maximum_age_s < 0
            or frame.ego_speed_mps < 0
        ):
            return "INVALID_SCENE_NUMERIC_RANGE"
        if previous is not None and frame.timestamp_s < previous - _E - _FLOAT_ROUNDOFF:
            return "NONMONOTONIC_TIMESTAMPS"
        previous = frame.timestamp_s
    return None


def run_enumerator_target(contract: BoundContract, frames: Iterable[ContextFrame]) -> TraceResult:
    samples = tuple(frames)
    input_error = _enumerator_input_error(contract, samples)
    if input_error is not None:
        return TraceResult(False, Verdict.UNSUPPORTED, (), (), (input_error,))
    state = "INACTIVE"
    clear = 0
    steps: list[MonitorStep] = []
    for frame in samples:
        diag: list[str] = []
        violations: list[str] = []
        if not frame.scope_valid or (contract.expiry_timestamp_s is not None and frame.timestamp_s >= contract.expiry_timestamp_s):
            state = "EXPIRED"
            clear = 0
        if frame.distance_unit != contract.distance_unit:
            steps.append(MonitorStep(frame.timestamp_s, Lifecycle(state), Verdict.UNSUPPORTED, None, False, (), ("UNIT_MISMATCH",)))
            continue
        if frame.coordinate_frame != contract.coordinate_frame:
            steps.append(MonitorStep(frame.timestamp_s, Lifecycle(state), Verdict.UNSUPPORTED, None, False, (), ("COORDINATE_FRAME_MISMATCH",)))
            continue

        signal = frame.hazard.truth.value
        age = frame.timestamp_s - frame.hazard.timestamp_s
        limit = min(frame.hazard.maximum_age_s, contract.predicate_maximum_age_s)
        if age < -_E - _FLOAT_ROUNDOFF:
            signal = "UNKNOWN"
            diag.append("FACT_TIMESTAMP_IN_FUTURE")
        elif age > limit + _E + _FLOAT_ROUNDOFF:
            signal = "UNKNOWN"
            diag.append("STALE_PREDICATE_FAILURE_TO_UNKNOWN")
        if frame.hazard.epistemic_kind.value == "CLAIMED":
            signal = "UNKNOWN"
            diag.append("COC_CLAIM_NOT_OBSERVED_FACT")

        if state != "EXPIRED":
            if contract.always_active and state not in _LIVE_NAMES:
                state, clear = "ACTIVE", 0
            if signal == "CONFLICT":
                diag.append("CONFLICTING_SCENE_EVIDENCE")
            else:
                reduced = signal
                if signal == "UNKNOWN" and contract.unknown_policy == "AS_FALSE":
                    reduced = "FALSE"
                    diag.append("MUTATION_UNKNOWN_AS_FALSE")
                elif signal == "UNKNOWN" and contract.unknown_policy == "AS_TRUE":
                    reduced = "TRUE"
                    diag.append("UNKNOWN_AS_TRUE_WITHOUT_APPROVED_FALLBACK")
                if state in {"INACTIVE", "CANDIDATE"}:
                    if reduced == "TRUE":
                        state, clear = "ACTIVE", 0
                    elif reduced == "FALSE":
                        state, clear = "INACTIVE", 0
                    else:
                        state = "CANDIDATE"
                        diag.append("UNKNOWN_PRECONDITION_REVIEW")
                elif state == "RELEASED":
                    if reduced == "TRUE":
                        if contract.reactivation_enabled:
                            state, clear = "REACTIVATED", 0
                        else:
                            diag.append("MISSING_REACTIVATION")
                elif state in _LIVE_NAMES:
                    if reduced == "TRUE":
                        state, clear = "MAINTAINED", 0
                    elif reduced == "FALSE":
                        clear += 1
                        state = "RELEASED" if contract.release_enabled and clear >= contract.release_clear_frames else "MAINTAINED"
                    else:
                        clear = 0
                        if contract.fallback_approved:
                            state = "MAINTAINED"
                            diag.append("APPROVED_UNKNOWN_HOLD_FALLBACK")
                        else:
                            diag.append("UNKNOWN_WITHOUT_APPROVED_FALLBACK")

        status = Verdict.CONFLICT if signal == "CONFLICT" else Verdict.VALIDATED
        review_codes = {"STALE_PREDICATE_FAILURE_TO_UNKNOWN", "FACT_TIMESTAMP_IN_FUTURE", "COC_CLAIM_NOT_OBSERVED_FACT", "UNKNOWN_PRECONDITION_REVIEW", "UNKNOWN_WITHOUT_APPROVED_FALLBACK", "UNKNOWN_AS_TRUE_WITHOUT_APPROVED_FALLBACK"}
        if status is not Verdict.CONFLICT and any(code in review_codes for code in diag):
            status = Verdict.REVIEW_REQUIRED
        bound = None
        live = state in _LIVE_NAMES
        target_ok = frame.target_entity_id == contract.target_entity_id and frame.zone_id == contract.zone_id
        if not target_ok:
            diag.append("TARGET_BINDING_MISMATCH")
            if status is Verdict.VALIDATED:
                status = Verdict.REVIEW_REQUIRED
        if live:
            available = contract.stop_position_x_m - frame.ego_front_x_m - contract.position_uncertainty_m
            if available <= 0:
                bound = 0.0
            else:
                b, r = contract.maximum_service_deceleration_mps2, contract.response_time_s
                bound = max(0.0, -b * r + sqrt((b * r) * (b * r) + 2 * b * available))
            if contract.enforce_invariant and target_ok:
                if frame.ego_front_x_m > contract.stop_position_x_m + _E + _FLOAT_ROUNDOFF:
                    violations.append("CONFLICT_ZONE_ENTRY_WHILE_OBLIGATION_ACTIVE")
                if frame.ego_speed_mps > bound + _E + _FLOAT_ROUNDOFF:
                    violations.append("DYNAMIC_STOPPING_SPEED_BOUND_EXCEEDED")
        progress = not live
        if contract.force_deadlock and frame.safe_progress_available:
            progress = False
            violations.append("FALSE_DEADLOCK_NO_ADMISSIBLE_ACTION")
        steps.append(MonitorStep(frame.timestamp_s, Lifecycle(state), status, bound, progress, tuple(violations), tuple(diag)))

    packed = tuple(steps)
    all_violations = tuple(item for step in packed for item in step.violations)
    all_diag = tuple(item for step in packed for item in step.diagnostics)
    statuses = {step.verdict for step in packed}
    verdict = Verdict.CONFLICT if Verdict.CONFLICT in statuses else Verdict.UNSUPPORTED if Verdict.UNSUPPORTED in statuses else Verdict.REVIEW_REQUIRED if Verdict.REVIEW_REQUIRED in statuses else Verdict.VALIDATED
    return TraceResult(not all_violations and verdict not in {Verdict.CONFLICT, Verdict.UNSUPPORTED}, verdict, packed, all_violations, all_diag)


def enumerator_queries(contract: BoundContract, frame_factory) -> dict[str, object]:
    allowed = {
        ("INACTIVE", "INACTIVE"), ("INACTIVE", "CANDIDATE"), ("INACTIVE", "ACTIVE"),
        ("CANDIDATE", "INACTIVE"), ("CANDIDATE", "CANDIDATE"), ("CANDIDATE", "ACTIVE"),
        ("ACTIVE", "MAINTAINED"), ("MAINTAINED", "MAINTAINED"),
        ("ACTIVE", "RELEASED"), ("MAINTAINED", "RELEASED"),
        ("RELEASED", "RELEASED"), ("RELEASED", "REACTIVATED"),
        ("REACTIVATED", "MAINTAINED"),
    }
    checked, invalid = 0, []
    for sequence in product((Truth.TRUE, Truth.FALSE, Truth.UNKNOWN), repeat=4):
        result = run_enumerator_target(contract, [frame_factory(i * 0.1, truth) for i, truth in enumerate(sequence)])
        states = ["INACTIVE"] + [step.lifecycle.value for step in result.steps]
        checked += 1
        invalid.extend(pair for pair in zip(states, states[1:]) if pair not in allowed)
    invariant = run_enumerator_target(contract, [frame_factory(0.0, Truth.TRUE, x=contract.stop_position_x_m + 0.01, speed=0.0)])
    reactivation = run_enumerator_target(contract, [
        frame_factory(0.0, Truth.TRUE), frame_factory(0.1, Truth.FALSE),
        frame_factory(0.2, Truth.FALSE), frame_factory(0.3, Truth.TRUE),
    ])
    deadlock = run_enumerator_target(contract, [frame_factory(0.0, Truth.FALSE, safe_progress=True)])
    return {
        "engine": ENGINE,
        "lifecycle_transition_consistency": {"sequences_checked": checked, "invalid_transition_count": len(invalid), "consistent": not invalid},
        "active_stop_position_invariant_violation_witness_exists": "CONFLICT_ZONE_ENTRY_WHILE_OBLIGATION_ACTIVE" in invariant.violations,
        "release_hazard_reappearance_missing_reactivation_witness_exists": reactivation.steps[-1].lifecycle is not Lifecycle.REACTIVATED,
        "safe_progress_false_deadlock_witness_exists": "FALSE_DEADLOCK_NO_ADMISSIBLE_ACTION" in deadlock.violations,
        "claim_boundary": "FINITE_STATE_ENUMERATION_NOT_SMT",
    }
