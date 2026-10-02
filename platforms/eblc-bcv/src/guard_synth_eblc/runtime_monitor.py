"""Public independent runtime-monitor compiler target.

This target imports representation types only.  It does not import or call the
canonical interpreter or its helpers; translation tests compare the two.
"""

from __future__ import annotations

from math import isfinite, sqrt
from typing import Iterable

from .types import (
    BoundContract,
    ContextFrame,
    EpistemicKind,
    Lifecycle,
    MonitorStep,
    TraceResult,
    Truth,
    Verdict,
)


_LIVE = (Lifecycle.ACTIVE, Lifecycle.MAINTAINED, Lifecycle.REACTIVATED)
_TOL = 0.000000001
# Independent runtime implementation of the canonical real-boundary policy:
# ignore only binary-float roundoff, never a meaningful fraction of _TOL.
_FLOAT_ROUNDOFF = 0.000000000000001


def _runtime_contract_error(spec: BoundContract) -> str | None:
    numeric = (
        spec.zone_entry_x_m,
        spec.stop_position_x_m,
        spec.stop_margin_m,
        spec.predicate_maximum_age_s,
        spec.maximum_service_deceleration_mps2,
        spec.response_time_s,
        spec.position_uncertainty_m,
    )
    if not all(isfinite(value) for value in numeric):
        return "NONFINITE_BOUND_CONTRACT"
    if (
        spec.stop_margin_m < 0
        or spec.predicate_maximum_age_s < 0
        or spec.maximum_service_deceleration_mps2 <= 0
        or spec.response_time_s < 0
        or spec.position_uncertainty_m < 0
        or spec.release_clear_frames < 1
    ):
        return "INVALID_BOUND_CONTRACT_RANGE"
    if spec.expiry_timestamp_s is not None and not isfinite(spec.expiry_timestamp_s):
        return "NONFINITE_BOUND_CONTRACT"
    return None


def _runtime_trace_error(samples: tuple[ContextFrame, ...]) -> str | None:
    if not samples:
        return "EMPTY_TRACE"
    previous: float | None = None
    for sample in samples:
        values = (
            sample.timestamp_s,
            sample.hazard.timestamp_s,
            sample.hazard.maximum_age_s,
            sample.ego_front_x_m,
            sample.ego_speed_mps,
            sample.zone_entry_x_m,
        )
        if not all(isfinite(value) for value in values):
            return "NONFINITE_SCENE_VALUE"
        if (
            sample.timestamp_s < 0
            or sample.hazard.timestamp_s < 0
            or sample.hazard.maximum_age_s < 0
            or sample.ego_speed_mps < 0
        ):
            return "INVALID_SCENE_NUMERIC_RANGE"
        if previous is not None and sample.timestamp_s < previous - _TOL - _FLOAT_ROUNDOFF:
            return "NONMONOTONIC_TIMESTAMPS"
        previous = sample.timestamp_s
    return None


class RuntimeMonitorTarget:
    def __init__(self, contract: BoundContract) -> None:
        self.spec = contract
        self.mode = Lifecycle.INACTIVE
        self.clear_count = 0

    def tick(self, sample: ContextFrame) -> MonitorStep:
        notes: list[str] = []
        faults: list[str] = []
        if not sample.scope_valid or (
            self.spec.expiry_timestamp_s is not None
            and sample.timestamp_s >= self.spec.expiry_timestamp_s
        ):
            self.mode = Lifecycle.EXPIRED
            self.clear_count = 0

        if sample.distance_unit != self.spec.distance_unit:
            return MonitorStep(sample.timestamp_s, self.mode, Verdict.UNSUPPORTED, None, False, (), ("UNIT_MISMATCH",))
        if sample.coordinate_frame != self.spec.coordinate_frame:
            return MonitorStep(sample.timestamp_s, self.mode, Verdict.UNSUPPORTED, None, False, (), ("COORDINATE_FRAME_MISMATCH",))

        observed = sample.hazard.truth
        age = sample.timestamp_s - sample.hazard.timestamp_s
        age_limit = min(sample.hazard.maximum_age_s, self.spec.predicate_maximum_age_s)
        if age < -_TOL - _FLOAT_ROUNDOFF:
            observed = Truth.UNKNOWN
            notes.append("FACT_TIMESTAMP_IN_FUTURE")
        elif age > age_limit + _TOL + _FLOAT_ROUNDOFF:
            observed = Truth.UNKNOWN
            notes.append("STALE_PREDICATE_FAILURE_TO_UNKNOWN")
        if sample.hazard.epistemic_kind == EpistemicKind.CLAIMED:
            observed = Truth.UNKNOWN
            notes.append("COC_CLAIM_NOT_OBSERVED_FACT")

        if self.mode is not Lifecycle.EXPIRED:
            if self.spec.always_active and self.mode not in _LIVE:
                self.mode = Lifecycle.ACTIVE
                self.clear_count = 0
            if observed is Truth.CONFLICT:
                notes.append("CONFLICTING_SCENE_EVIDENCE")
            else:
                signal = observed
                if observed is Truth.UNKNOWN and self.spec.unknown_policy == "AS_FALSE":
                    signal = Truth.FALSE
                    notes.append("MUTATION_UNKNOWN_AS_FALSE")
                elif observed is Truth.UNKNOWN and self.spec.unknown_policy == "AS_TRUE":
                    signal = Truth.TRUE
                    notes.append("UNKNOWN_AS_TRUE_WITHOUT_APPROVED_FALLBACK")

                if self.mode in (Lifecycle.INACTIVE, Lifecycle.CANDIDATE):
                    if signal is Truth.TRUE:
                        self.mode = Lifecycle.ACTIVE
                        self.clear_count = 0
                    elif signal is Truth.FALSE:
                        self.mode = Lifecycle.INACTIVE
                        self.clear_count = 0
                    else:
                        self.mode = Lifecycle.CANDIDATE
                        notes.append("UNKNOWN_PRECONDITION_REVIEW")
                elif self.mode is Lifecycle.RELEASED:
                    if signal is Truth.TRUE:
                        if self.spec.reactivation_enabled:
                            self.mode = Lifecycle.REACTIVATED
                            self.clear_count = 0
                        else:
                            notes.append("MISSING_REACTIVATION")
                elif self.mode in _LIVE:
                    if signal is Truth.TRUE:
                        self.mode = Lifecycle.MAINTAINED
                        self.clear_count = 0
                    elif signal is Truth.FALSE:
                        self.clear_count += 1
                        if self.spec.release_enabled and self.clear_count >= self.spec.release_clear_frames:
                            self.mode = Lifecycle.RELEASED
                        else:
                            self.mode = Lifecycle.MAINTAINED
                    else:
                        self.clear_count = 0
                        if self.spec.fallback_approved:
                            self.mode = Lifecycle.MAINTAINED
                            notes.append("APPROVED_UNKNOWN_HOLD_FALLBACK")
                        else:
                            notes.append("UNKNOWN_WITHOUT_APPROVED_FALLBACK")

        status = Verdict.VALIDATED
        if observed is Truth.CONFLICT:
            status = Verdict.CONFLICT
        elif any(note in {
            "STALE_PREDICATE_FAILURE_TO_UNKNOWN", "FACT_TIMESTAMP_IN_FUTURE",
            "COC_CLAIM_NOT_OBSERVED_FACT", "UNKNOWN_PRECONDITION_REVIEW",
            "UNKNOWN_WITHOUT_APPROVED_FALLBACK", "UNKNOWN_AS_TRUE_WITHOUT_APPROVED_FALLBACK",
        } for note in notes):
            status = Verdict.REVIEW_REQUIRED

        bound: float | None = None
        live = self.mode in _LIVE
        same_target = sample.target_entity_id == self.spec.target_entity_id and sample.zone_id == self.spec.zone_id
        if not same_target:
            notes.append("TARGET_BINDING_MISMATCH")
            if status is Verdict.VALIDATED:
                status = Verdict.REVIEW_REQUIRED
        if live:
            distance = self.spec.stop_position_x_m - sample.ego_front_x_m - self.spec.position_uncertainty_m
            if distance <= 0:
                bound = 0.0
            else:
                braking = self.spec.maximum_service_deceleration_mps2
                delay = self.spec.response_time_s
                bound = max(0.0, -braking * delay + sqrt(braking * braking * delay * delay + 2 * braking * distance))
            if self.spec.enforce_invariant and same_target:
                if sample.ego_front_x_m > self.spec.stop_position_x_m + _TOL + _FLOAT_ROUNDOFF:
                    faults.append("CONFLICT_ZONE_ENTRY_WHILE_OBLIGATION_ACTIVE")
                if sample.ego_speed_mps > bound + _TOL + _FLOAT_ROUNDOFF:
                    faults.append("DYNAMIC_STOPPING_SPEED_BOUND_EXCEEDED")
        may_progress = not live
        if self.spec.force_deadlock and sample.safe_progress_available:
            may_progress = False
            faults.append("FALSE_DEADLOCK_NO_ADMISSIBLE_ACTION")
        return MonitorStep(sample.timestamp_s, self.mode, status, bound, may_progress, tuple(faults), tuple(notes))


def run_runtime(contract: BoundContract, frames: Iterable[ContextFrame]) -> TraceResult:
    samples = tuple(frames)
    input_error = _runtime_contract_error(contract) or _runtime_trace_error(samples)
    if input_error is not None:
        return TraceResult(False, Verdict.UNSUPPORTED, (), (), (input_error,))
    target = RuntimeMonitorTarget(contract)
    steps = tuple(target.tick(frame) for frame in samples)
    failures = tuple(item for step in steps for item in step.violations)
    notes = tuple(item for step in steps for item in step.diagnostics)
    statuses = {step.verdict for step in steps}
    if Verdict.CONFLICT in statuses:
        status = Verdict.CONFLICT
    elif Verdict.UNSUPPORTED in statuses:
        status = Verdict.UNSUPPORTED
    elif Verdict.REVIEW_REQUIRED in statuses:
        status = Verdict.REVIEW_REQUIRED
    else:
        status = Verdict.VALIDATED
    return TraceResult(not failures and status not in (Verdict.CONFLICT, Verdict.UNSUPPORTED), status, steps, failures, notes)
