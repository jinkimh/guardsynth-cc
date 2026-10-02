"""Public canonical EBLC v0 operational semantics.

This module is the sole semantic source of truth.  JSON Schema validates
syntax, ``types.py`` represents values, and compiler targets independently
reimplement this behavior for bounded translation comparison.
"""

from __future__ import annotations

import math
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


LIVE_STATES = {Lifecycle.ACTIVE, Lifecycle.MAINTAINED, Lifecycle.REACTIVATED}
EPSILON = 1e-9
# Input timestamps and quantities are binary floats, while the EBLC boundary
# semantics are defined over ideal real values.  This much smaller guard only
# absorbs arithmetic representation noise; it must not relax EPSILON itself.
_FLOAT_ROUNDOFF = 1e-15


def _contract_input_error(contract: BoundContract) -> str | None:
    numeric = (
        contract.zone_entry_x_m,
        contract.stop_position_x_m,
        contract.stop_margin_m,
        contract.predicate_maximum_age_s,
        contract.maximum_service_deceleration_mps2,
        contract.response_time_s,
        contract.position_uncertainty_m,
    )
    if not all(math.isfinite(value) for value in numeric):
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
    if contract.expiry_timestamp_s is not None and not math.isfinite(contract.expiry_timestamp_s):
        return "NONFINITE_BOUND_CONTRACT"
    return None


def _trace_input_error(frames: tuple[ContextFrame, ...]) -> str | None:
    if not frames:
        return "EMPTY_TRACE"
    previous_timestamp: float | None = None
    for frame in frames:
        numeric = (
            frame.timestamp_s,
            frame.hazard.timestamp_s,
            frame.hazard.maximum_age_s,
            frame.ego_front_x_m,
            frame.ego_speed_mps,
            frame.zone_entry_x_m,
        )
        if not all(math.isfinite(value) for value in numeric):
            return "NONFINITE_SCENE_VALUE"
        if (
            frame.timestamp_s < 0
            or frame.hazard.timestamp_s < 0
            or frame.hazard.maximum_age_s < 0
            or frame.ego_speed_mps < 0
        ):
            return "INVALID_SCENE_NUMERIC_RANGE"
        if previous_timestamp is not None and frame.timestamp_s < previous_timestamp - EPSILON - _FLOAT_ROUNDOFF:
            return "NONMONOTONIC_TIMESTAMPS"
        previous_timestamp = frame.timestamp_s
    return None


def _trace_verdict(steps: tuple[MonitorStep, ...]) -> Verdict:
    verdicts = {step.verdict for step in steps}
    for candidate in (Verdict.CONFLICT, Verdict.UNSUPPORTED, Verdict.REVIEW_REQUIRED):
        if candidate in verdicts:
            return candidate
    return Verdict.VALIDATED


class CanonicalInterpreter:
    """Reference interpreter for a single bound obligation ledger entry."""

    def __init__(self, contract: BoundContract) -> None:
        self.contract = contract
        self.lifecycle = Lifecycle.INACTIVE
        self.clear_frames = 0

    def _effective_truth(self, frame: ContextFrame, diagnostics: list[str]) -> Truth:
        fact = frame.hazard
        freshness_limit = min(fact.maximum_age_s, self.contract.predicate_maximum_age_s)
        age = frame.timestamp_s - fact.timestamp_s
        if age < -EPSILON - _FLOAT_ROUNDOFF:
            diagnostics.append("FACT_TIMESTAMP_IN_FUTURE")
            return Truth.UNKNOWN
        if age > freshness_limit + EPSILON + _FLOAT_ROUNDOFF:
            diagnostics.append("STALE_PREDICATE_FAILURE_TO_UNKNOWN")
            return Truth.UNKNOWN
        if fact.epistemic_kind is EpistemicKind.CLAIMED:
            diagnostics.append("COC_CLAIM_NOT_OBSERVED_FACT")
            return Truth.UNKNOWN
        return fact.truth

    def _advance(self, truth: Truth, diagnostics: list[str]) -> None:
        if self.contract.always_active and self.lifecycle not in LIVE_STATES:
            self.lifecycle = Lifecycle.ACTIVE
            self.clear_frames = 0

        if self.lifecycle is Lifecycle.EXPIRED:
            return
        if truth is Truth.CONFLICT:
            diagnostics.append("CONFLICTING_SCENE_EVIDENCE")
            return

        effective = truth
        if truth is Truth.UNKNOWN:
            if self.contract.unknown_policy == "AS_FALSE":
                effective = Truth.FALSE
                diagnostics.append("MUTATION_UNKNOWN_AS_FALSE")
            elif self.contract.unknown_policy == "AS_TRUE":
                effective = Truth.TRUE
                diagnostics.append("UNKNOWN_AS_TRUE_WITHOUT_APPROVED_FALLBACK")

        if self.lifecycle in {Lifecycle.INACTIVE, Lifecycle.CANDIDATE}:
            if effective is Truth.TRUE:
                self.lifecycle = Lifecycle.ACTIVE
                self.clear_frames = 0
            elif effective is Truth.FALSE:
                self.lifecycle = Lifecycle.INACTIVE
                self.clear_frames = 0
            else:
                self.lifecycle = Lifecycle.CANDIDATE
                diagnostics.append("UNKNOWN_PRECONDITION_REVIEW")
            return

        if self.lifecycle is Lifecycle.RELEASED:
            if effective is Truth.TRUE:
                if self.contract.reactivation_enabled:
                    self.lifecycle = Lifecycle.REACTIVATED
                    self.clear_frames = 0
                else:
                    diagnostics.append("MISSING_REACTIVATION")
            return

        if self.lifecycle in LIVE_STATES:
            if effective is Truth.TRUE:
                self.lifecycle = Lifecycle.MAINTAINED
                self.clear_frames = 0
            elif effective is Truth.FALSE:
                self.clear_frames += 1
                if (
                    self.contract.release_enabled
                    and self.clear_frames >= self.contract.release_clear_frames
                ):
                    self.lifecycle = Lifecycle.RELEASED
                else:
                    self.lifecycle = Lifecycle.MAINTAINED
            else:
                self.clear_frames = 0
                if self.contract.fallback_approved:
                    self.lifecycle = Lifecycle.MAINTAINED
                    diagnostics.append("APPROVED_UNKNOWN_HOLD_FALLBACK")
                else:
                    diagnostics.append("UNKNOWN_WITHOUT_APPROVED_FALLBACK")

    def step(self, frame: ContextFrame) -> MonitorStep:
        diagnostics: list[str] = []
        violations: list[str] = []

        if (
            not frame.scope_valid
            or (
                self.contract.expiry_timestamp_s is not None
                and frame.timestamp_s >= self.contract.expiry_timestamp_s
            )
        ):
            self.lifecycle = Lifecycle.EXPIRED
            self.clear_frames = 0

        if frame.distance_unit != self.contract.distance_unit:
            diagnostics.append("UNIT_MISMATCH")
            return MonitorStep(
                frame.timestamp_s,
                self.lifecycle,
                Verdict.UNSUPPORTED,
                None,
                False,
                (),
                tuple(diagnostics),
            )
        if frame.coordinate_frame != self.contract.coordinate_frame:
            diagnostics.append("COORDINATE_FRAME_MISMATCH")
            return MonitorStep(
                frame.timestamp_s,
                self.lifecycle,
                Verdict.UNSUPPORTED,
                None,
                False,
                (),
                tuple(diagnostics),
            )

        truth = self._effective_truth(frame, diagnostics)
        if self.lifecycle is not Lifecycle.EXPIRED:
            self._advance(truth, diagnostics)

        verdict = Verdict.VALIDATED
        if truth is Truth.CONFLICT:
            verdict = Verdict.CONFLICT
        elif diagnostics and any(
            code in diagnostics
            for code in (
                "STALE_PREDICATE_FAILURE_TO_UNKNOWN",
                "FACT_TIMESTAMP_IN_FUTURE",
                "COC_CLAIM_NOT_OBSERVED_FACT",
                "UNKNOWN_PRECONDITION_REVIEW",
                "UNKNOWN_WITHOUT_APPROVED_FALLBACK",
                "UNKNOWN_AS_TRUE_WITHOUT_APPROVED_FALLBACK",
            )
        ):
            verdict = Verdict.REVIEW_REQUIRED

        live = self.lifecycle in LIVE_STATES
        maximum_speed: float | None = None
        target_matches = (
            frame.target_entity_id == self.contract.target_entity_id
            and frame.zone_id == self.contract.zone_id
        )
        if not target_matches:
            diagnostics.append("TARGET_BINDING_MISMATCH")
            if verdict is Verdict.VALIDATED:
                verdict = Verdict.REVIEW_REQUIRED

        if live:
            available = (
                self.contract.stop_position_x_m
                - frame.ego_front_x_m
                - self.contract.position_uncertainty_m
            )
            if available <= 0:
                maximum_speed = 0.0
            else:
                deceleration = self.contract.maximum_service_deceleration_mps2
                response = self.contract.response_time_s
                maximum_speed = max(
                    0.0,
                    -deceleration * response
                    + math.sqrt(
                        (deceleration * response) ** 2
                        + 2.0 * deceleration * available
                    ),
                )
            if self.contract.enforce_invariant and target_matches:
                if frame.ego_front_x_m > self.contract.stop_position_x_m + EPSILON + _FLOAT_ROUNDOFF:
                    violations.append("CONFLICT_ZONE_ENTRY_WHILE_OBLIGATION_ACTIVE")
                if frame.ego_speed_mps > maximum_speed + EPSILON + _FLOAT_ROUNDOFF:
                    violations.append("DYNAMIC_STOPPING_SPEED_BOUND_EXCEEDED")

        progress_allowed = not live
        if self.contract.force_deadlock and frame.safe_progress_available:
            progress_allowed = False
            violations.append("FALSE_DEADLOCK_NO_ADMISSIBLE_ACTION")

        return MonitorStep(
            timestamp_s=frame.timestamp_s,
            lifecycle=self.lifecycle,
            verdict=verdict,
            maximum_safe_speed_mps=maximum_speed,
            progress_allowed=progress_allowed,
            violations=tuple(violations),
            diagnostics=tuple(diagnostics),
        )


def run_canonical(contract: BoundContract, frames: Iterable[ContextFrame]) -> TraceResult:
    samples = tuple(frames)
    input_error = _contract_input_error(contract) or _trace_input_error(samples)
    if input_error is not None:
        return TraceResult(False, Verdict.UNSUPPORTED, (), (), (input_error,))
    interpreter = CanonicalInterpreter(contract)
    steps = tuple(interpreter.step(frame) for frame in samples)
    violations = tuple(item for step in steps for item in step.violations)
    diagnostics = tuple(item for step in steps for item in step.diagnostics)
    verdict = _trace_verdict(steps)
    accepted = not violations and verdict not in {Verdict.CONFLICT, Verdict.UNSUPPORTED}
    return TraceResult(accepted, verdict, steps, violations, diagnostics)
