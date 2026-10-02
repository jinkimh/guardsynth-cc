"""Small executable EBLC/BCV pilot with no external dependencies.

This module intentionally uses a synthetic crosswalk scene and a pilot system
requirement.  It tests contract instantiation and execution mechanics; it does
not claim that the requirement is traffic law or that the model is sufficient
for real-vehicle safety.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import math
from typing import Iterable


class Truth(str, Enum):
    TRUE = "TRUE"
    FALSE = "FALSE"
    UNKNOWN = "UNKNOWN"
    CONFLICT = "CONFLICT"


class Verdict(str, Enum):
    VALIDATED = "VALIDATED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    UNSUPPORTED = "UNSUPPORTED"
    CONFLICT = "CONFLICT"


class Lifecycle(str, Enum):
    INACTIVE = "INACTIVE"
    ACTIVE = "ACTIVE"
    MAINTAINED = "MAINTAINED"
    RELEASED = "RELEASED"
    REACTIVATED = "REACTIVATED"
    CONFLICT = "CONFLICT"


@dataclass(frozen=True, slots=True)
class Evidence:
    evidence_id: str
    evidence_class: str
    source_version: str


@dataclass(frozen=True, slots=True)
class RuleTemplate:
    rule_id: str
    hazard_tag: str
    zone_type: str
    stop_margin_m: float
    release_clear_frames: int
    fallback: str
    evidence: Evidence


@dataclass(frozen=True, slots=True)
class VehicleProfile:
    profile_id: str
    max_service_decel_mps2: float
    response_time_s: float
    position_uncertainty_m: float


@dataclass(frozen=True, slots=True)
class SceneFrame:
    timestamp_s: float
    ego_front_x_m: float
    ego_speed_mps: float
    conflict_zone_entry_x_m: float
    pedestrian_conflict: Truth
    zone_type: str = "crosswalk"


@dataclass(frozen=True, slots=True)
class BoundContract:
    contract_id: str
    rule_id: str
    target: str
    stop_position_x_m: float
    release_clear_frames: int
    fallback: str
    vehicle_profile: VehicleProfile
    evidence_refs: tuple[str, ...]
    derivation: str

    def maximum_safe_speed_mps(self, frame: SceneFrame) -> float:
        """Solve d >= v*rho + v^2/(2b) for the maximum admissible v."""
        profile = self.vehicle_profile
        available = (
            self.stop_position_x_m
            - frame.ego_front_x_m
            - profile.position_uncertainty_m
        )
        if available <= 0.0:
            return 0.0
        braking = profile.max_service_decel_mps2
        response = profile.response_time_s
        return max(
            0.0,
            -braking * response
            + math.sqrt((braking * response) ** 2 + 2.0 * braking * available),
        )


@dataclass(frozen=True, slots=True)
class SynthesisResult:
    verdict: Verdict
    reason: str
    candidates: tuple[str, ...]
    contract: BoundContract | None


@dataclass(frozen=True, slots=True)
class MonitorStep:
    timestamp_s: float
    lifecycle: Lifecycle
    max_safe_speed_mps: float | None
    violations: tuple[str, ...]
    diagnostics: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class TraceResult:
    accepted: bool
    steps: tuple[MonitorStep, ...]
    violations: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class BCVResult:
    correct_accepts_safe_trace: bool
    correct_rejects_unsafe_trace: bool
    underconstraint_witness_found: bool
    overconstraint_witness_found: bool

    @property
    def passed(self) -> bool:
        return all(
            (
                self.correct_accepts_safe_trace,
                self.correct_rejects_unsafe_trace,
                self.underconstraint_witness_found,
                self.overconstraint_witness_found,
            )
        )


PILOT_RULE = RuleTemplate(
    rule_id="PILOT-SYS-PED-CZ-001",
    hazard_tag="pedestrian_conflict",
    zone_type="crosswalk",
    stop_margin_m=1.5,
    release_clear_frames=2,
    fallback="HOLD_BEFORE_CONFLICT_ZONE_WHILE_OBSERVATION_UNKNOWN",
    evidence=Evidence(
        evidence_id="PILOT-SYSTEM-REQUIREMENT-PED-YIELD-v0",
        evidence_class="SYSTEM_REQUIREMENT",
        source_version="v0-synthetic-pilot",
    ),
)

PILOT_PROFILE = VehicleProfile(
    profile_id="PILOT-VEHICLE-PROFILE-v0",
    max_service_decel_mps2=3.0,
    response_time_s=0.5,
    position_uncertainty_m=0.5,
)


def retrieve_candidates(
    coc_text: str, frame: SceneFrame, catalog: Iterable[RuleTemplate]
) -> tuple[RuleTemplate, ...]:
    clue = coc_text.lower()
    mentions_pedestrian_yield = any(
        token in clue for token in ("보행", "양보", "pedestrian", "yield")
    )
    return tuple(
        rule
        for rule in catalog
        if rule.zone_type == frame.zone_type
        and (mentions_pedestrian_yield or frame.pedestrian_conflict is Truth.TRUE)
    )


def synthesize_contract(
    coc_text: str,
    frame: SceneFrame,
    vehicle_profile: VehicleProfile | None,
    catalog: Iterable[RuleTemplate] = (PILOT_RULE,),
) -> SynthesisResult:
    candidates = retrieve_candidates(coc_text, frame, catalog)
    candidate_ids = tuple(rule.rule_id for rule in candidates)
    if not candidates:
        return SynthesisResult(
            Verdict.UNSUPPORTED,
            "UNSUPPORTED_RULE_COVERAGE",
            candidate_ids,
            None,
        )
    if frame.pedestrian_conflict is Truth.UNKNOWN:
        return SynthesisResult(
            Verdict.REVIEW_REQUIRED,
            "COC_CLUE_WITHOUT_OBSERVED_APPLICABILITY",
            candidate_ids,
            None,
        )
    if frame.pedestrian_conflict is Truth.CONFLICT:
        return SynthesisResult(
            Verdict.CONFLICT,
            "CONFLICTING_SCENE_EVIDENCE",
            candidate_ids,
            None,
        )
    if frame.pedestrian_conflict is Truth.FALSE:
        return SynthesisResult(
            Verdict.REVIEW_REQUIRED,
            "RULE_RETRIEVED_BUT_PRECONDITION_FALSE",
            candidate_ids,
            None,
        )
    if vehicle_profile is None:
        return SynthesisResult(
            Verdict.UNSUPPORTED,
            "MISSING_VEHICLE_PROFILE_FOR_NUMERIC_BINDING",
            candidate_ids,
            None,
        )
    if (
        vehicle_profile.max_service_decel_mps2 <= 0.0
        or vehicle_profile.response_time_s < 0.0
        or vehicle_profile.position_uncertainty_m < 0.0
    ):
        return SynthesisResult(
            Verdict.UNSUPPORTED,
            "INVALID_VEHICLE_PROFILE",
            candidate_ids,
            None,
        )

    rule = candidates[0]
    stop_position = frame.conflict_zone_entry_x_m - rule.stop_margin_m
    contract = BoundContract(
        contract_id="EBLC-PILOT-PED-CZ-0001",
        rule_id=rule.rule_id,
        target="pedestrian-track:P17/conflict-zone:CZ4",
        stop_position_x_m=stop_position,
        release_clear_frames=rule.release_clear_frames,
        fallback=rule.fallback,
        vehicle_profile=vehicle_profile,
        evidence_refs=(rule.evidence.evidence_id, vehicle_profile.profile_id),
        derivation=(
            "stop_position=zone_entry-stop_margin; "
            "v_max solves d>=v*response_time+v^2/(2*max_service_decel) "
            "after subtracting position_uncertainty"
        ),
    )
    return SynthesisResult(Verdict.VALIDATED, "BOUND_AND_MONITORABLE", candidate_ids, contract)


class ContractMonitor:
    def __init__(
        self,
        contract: BoundContract,
        *,
        enforce_invariants: bool = True,
        release_enabled: bool = True,
    ) -> None:
        self.contract = contract
        self.enforce_invariants = enforce_invariants
        self.release_enabled = release_enabled
        self.lifecycle = Lifecycle.INACTIVE
        self.clear_frames = 0

    def step(self, frame: SceneFrame) -> MonitorStep:
        diagnostics: list[str] = []
        truth = frame.pedestrian_conflict

        if truth is Truth.CONFLICT:
            self.lifecycle = Lifecycle.CONFLICT
            diagnostics.append("CONFLICTING_SCENE_EVIDENCE")
        elif self.lifecycle is Lifecycle.INACTIVE:
            if truth is Truth.TRUE:
                self.lifecycle = Lifecycle.ACTIVE
            elif truth is Truth.UNKNOWN:
                self.lifecycle = Lifecycle.ACTIVE
                diagnostics.append("UNKNOWN_HOLD_FALLBACK")
        elif self.lifecycle is Lifecycle.RELEASED:
            if truth is Truth.TRUE:
                self.lifecycle = Lifecycle.REACTIVATED
                self.clear_frames = 0
            elif truth is Truth.UNKNOWN:
                self.lifecycle = Lifecycle.REACTIVATED
                self.clear_frames = 0
                diagnostics.append("UNKNOWN_HOLD_FALLBACK")
        else:
            if truth is Truth.TRUE:
                self.lifecycle = Lifecycle.MAINTAINED
                self.clear_frames = 0
            elif truth is Truth.UNKNOWN:
                self.lifecycle = Lifecycle.MAINTAINED
                self.clear_frames = 0
                diagnostics.append("UNKNOWN_HOLD_FALLBACK")
            elif truth is Truth.FALSE:
                self.clear_frames += 1
                if (
                    self.release_enabled
                    and self.clear_frames >= self.contract.release_clear_frames
                ):
                    self.lifecycle = Lifecycle.RELEASED
                else:
                    self.lifecycle = Lifecycle.MAINTAINED

        live = self.lifecycle in {
            Lifecycle.ACTIVE,
            Lifecycle.MAINTAINED,
            Lifecycle.REACTIVATED,
        }
        maximum_speed = self.contract.maximum_safe_speed_mps(frame) if live else None
        violations: list[str] = []
        if live and self.enforce_invariants:
            if frame.ego_front_x_m > self.contract.stop_position_x_m + 1e-9:
                violations.append("CONFLICT_ZONE_ENTRY_WHILE_OBLIGATION_ACTIVE")
            if frame.ego_speed_mps > (maximum_speed or 0.0) + 1e-9:
                violations.append("ROBUST_STOPPING_SPEED_BOUND_EXCEEDED")
        return MonitorStep(
            timestamp_s=frame.timestamp_s,
            lifecycle=self.lifecycle,
            max_safe_speed_mps=maximum_speed,
            violations=tuple(violations),
            diagnostics=tuple(diagnostics),
        )


def run_trace(
    contract: BoundContract,
    frames: Iterable[SceneFrame],
    *,
    enforce_invariants: bool = True,
    release_enabled: bool = True,
) -> TraceResult:
    monitor = ContractMonitor(
        contract,
        enforce_invariants=enforce_invariants,
        release_enabled=release_enabled,
    )
    steps = tuple(monitor.step(frame) for frame in frames)
    violations = tuple(
        violation for step in steps for violation in step.violations
    )
    has_conflict = any(step.lifecycle is Lifecycle.CONFLICT for step in steps)
    return TraceResult(not violations and not has_conflict, steps, violations)


def safe_release_reactivation_trace() -> tuple[SceneFrame, ...]:
    return (
        SceneFrame(0.0, -12.0, 6.0, 0.0, Truth.TRUE),
        SceneFrame(0.5, -7.0, 4.0, 0.0, Truth.TRUE),
        SceneFrame(1.0, -2.2, 0.0, 0.0, Truth.TRUE),
        SceneFrame(1.5, -2.2, 0.0, 0.0, Truth.FALSE),
        SceneFrame(2.0, -2.2, 0.0, 0.0, Truth.FALSE),
        SceneFrame(2.5, -2.2, 0.1, 0.0, Truth.TRUE),
        SceneFrame(3.0, -2.2, 0.0, 0.0, Truth.FALSE),
        SceneFrame(3.5, -2.2, 0.0, 0.0, Truth.FALSE),
        SceneFrame(4.0, 1.0, 2.0, 0.0, Truth.FALSE),
    )


def unsafe_entry_trace() -> tuple[SceneFrame, ...]:
    return (
        SceneFrame(0.0, -12.0, 6.0, 0.0, Truth.TRUE),
        SceneFrame(0.5, -1.0, 3.0, 0.0, Truth.TRUE),
    )


def unknown_fallback_trace() -> tuple[SceneFrame, ...]:
    return (
        SceneFrame(0.0, -12.0, 6.0, 0.0, Truth.TRUE),
        SceneFrame(0.5, -4.0, 2.0, 0.0, Truth.UNKNOWN),
        SceneFrame(1.0, -2.2, 0.0, 0.0, Truth.TRUE),
    )


def run_bcv_mutation_pilot(contract: BoundContract) -> BCVResult:
    safe_trace = safe_release_reactivation_trace()
    unsafe_trace = unsafe_entry_trace()
    correct_safe = run_trace(contract, safe_trace)
    correct_unsafe = run_trace(contract, unsafe_trace)

    # Missing invariant: an independently unsafe trace becomes accepted.
    missing_invariant = run_trace(
        contract, unsafe_trace, enforce_invariants=False
    )
    # Missing release: an independently safe progress trace is rejected.
    missing_release = run_trace(
        contract, safe_trace, release_enabled=False
    )
    return BCVResult(
        correct_accepts_safe_trace=correct_safe.accepted,
        correct_rejects_unsafe_trace=not correct_unsafe.accepted,
        underconstraint_witness_found=missing_invariant.accepted,
        overconstraint_witness_found=not missing_release.accepted,
    )

