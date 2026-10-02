"""Representation types for EBLC v0.

This module deliberately contains no lifecycle transition implementation.
Operational meaning lives in :mod:`guard_synth_eblc.semantics`.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class Truth(str, Enum):
    TRUE = "TRUE"
    FALSE = "FALSE"
    UNKNOWN = "UNKNOWN"
    CONFLICT = "CONFLICT"


class EpistemicKind(str, Enum):
    OBSERVED = "OBSERVED"
    PREDICTED = "PREDICTED"
    DERIVED = "DERIVED"
    CLAIMED = "CLAIMED"


class Verdict(str, Enum):
    VALIDATED = "VALIDATED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    UNSUPPORTED = "UNSUPPORTED"
    CONFLICT = "CONFLICT"


class Lifecycle(str, Enum):
    INACTIVE = "INACTIVE"
    CANDIDATE = "CANDIDATE"
    ACTIVE = "ACTIVE"
    MAINTAINED = "MAINTAINED"
    RELEASED = "RELEASED"
    REACTIVATED = "REACTIVATED"
    EXPIRED = "EXPIRED"


class SourceClass(str, Enum):
    LEGAL = "LEGAL"
    PHYSICS_DERIVED = "PHYSICS_DERIVED"
    SYSTEM_REQUIREMENT = "SYSTEM_REQUIREMENT"
    ODD_REQUIREMENT = "ODD_REQUIREMENT"
    HUMAN_CONVENTION = "HUMAN_CONVENTION"
    STATISTICAL_HEURISTIC = "STATISTICAL_HEURISTIC"
    COMFORT_SERVICE = "COMFORT_SERVICE"
    UNKNOWN = "UNKNOWN"


class PriorityClass(str, Enum):
    HARD_PHYSICAL = "HARD_PHYSICAL"
    ODD_FALLBACK = "ODD_FALLBACK"
    MANDATORY_SYSTEM = "MANDATORY_SYSTEM"
    ROUTE_PROGRESS = "ROUTE_PROGRESS"
    HUMAN_CONVENTION = "HUMAN_CONVENTION"
    COMFORT_SERVICE = "COMFORT_SERVICE"
    STATISTICAL_HEURISTIC = "STATISTICAL_HEURISTIC"


@dataclass(frozen=True, slots=True)
class Fact:
    truth: Truth
    epistemic_kind: EpistemicKind
    source: str
    timestamp_s: float
    maximum_age_s: float

    def __post_init__(self) -> None:
        if not self.source:
            raise ValueError("fact source must be non-empty")
        if self.timestamp_s < 0 or self.maximum_age_s < 0:
            raise ValueError("fact timestamps and maximum age must be non-negative")


@dataclass(frozen=True, slots=True)
class PredicateSpec:
    predicate_id: str
    argument_types: tuple[str, ...]
    measurement_or_derivation_fn: str
    allowed_sources: tuple[EpistemicKind, ...]
    coordinate_frame: str
    update_rate_hz: float
    maximum_latency_s: float
    maximum_age_s: float
    uncertainty_model: str
    monitorability: str
    calibration_id: str
    failure_value: Truth


@dataclass(frozen=True, slots=True)
class EvidenceRecord:
    evidence_id: str
    source_class: SourceClass
    uri: str
    version: str
    scope: str
    section: str
    content_hash: str


@dataclass(frozen=True, slots=True)
class Priority:
    priority_class: PriorityClass
    overrides: tuple[PriorityClass, ...]


@dataclass(frozen=True, slots=True)
class RuleTemplate:
    rule_id: str
    source: EvidenceRecord
    scope: str
    precondition: str
    exception: str
    subject_role: str
    target_role: str
    zone_role: str
    binder_id: str
    activation: str
    invariant: str
    bound: str
    release: str
    reactivation: str
    expiry: str
    fallback: str
    fallback_approved: bool
    observability: tuple[str, ...]
    priority: Priority
    stop_margin_m: float
    release_clear_frames: int


@dataclass(frozen=True, slots=True)
class TargetBinding:
    entity_id: str | None
    zone_id: str | None
    ambiguity_reason: str | None = None

    @property
    def complete(self) -> bool:
        return bool(self.entity_id and self.zone_id and not self.ambiguity_reason)


@dataclass(frozen=True, slots=True)
class ValueBinding:
    value: float
    unit: str
    source_refs: tuple[str, ...]
    derivation_node_id: str
    kind: str = "Value"


@dataclass(frozen=True, slots=True)
class IntervalBinding:
    lower: float
    upper: float
    unit: str
    source_refs: tuple[str, ...]
    derivation_node_id: str
    kind: str = "Interval"


@dataclass(frozen=True, slots=True)
class SetBinding:
    values: tuple[str, ...]
    source_refs: tuple[str, ...]
    derivation_node_id: str
    kind: str = "Set"


@dataclass(frozen=True, slots=True)
class UnsupportedBinding:
    reason_code: str
    missing_inputs: tuple[str, ...]
    kind: str = "Unsupported"


BindingResult = ValueBinding | IntervalBinding | SetBinding | UnsupportedBinding


@dataclass(frozen=True, slots=True)
class DerivationNode:
    node_id: str
    operation: str
    inputs: tuple[str, ...]
    output: str


@dataclass(frozen=True, slots=True)
class VehicleProfile:
    profile_id: str
    maximum_service_deceleration_mps2: float
    response_time_s: float
    position_uncertainty_m: float
    evidence_ref: str


@dataclass(frozen=True, slots=True)
class BoundContract:
    contract_id: str
    rule_id: str
    subject_id: str
    target_entity_id: str
    zone_id: str
    zone_entry_x_m: float
    stop_position_x_m: float
    stop_margin_m: float
    release_clear_frames: int
    fallback: str
    fallback_approved: bool
    evidence_refs: tuple[str, ...]
    derivation_dag: tuple[DerivationNode, ...]
    coordinate_frame: str
    distance_unit: str
    predicate_maximum_age_s: float
    maximum_service_deceleration_mps2: float
    response_time_s: float
    position_uncertainty_m: float
    priority: Priority
    expiry_timestamp_s: float | None = None
    mutation_id: str | None = None
    enforce_invariant: bool = True
    reactivation_enabled: bool = True
    release_enabled: bool = True
    unknown_policy: str = "APPROVED_HOLD"
    always_active: bool = False
    force_deadlock: bool = False


@dataclass(frozen=True, slots=True)
class ContextFrame:
    timestamp_s: float
    hazard: Fact
    ego_front_x_m: float
    ego_speed_mps: float
    zone_entry_x_m: float
    target_entity_id: str
    zone_id: str
    coordinate_frame: str = "ego_path_s"
    distance_unit: str = "m"
    scope_valid: bool = True
    safe_progress_available: bool = False


@dataclass(frozen=True, slots=True)
class BindingOutcome:
    verdict: Verdict
    reason_codes: tuple[str, ...]
    target: TargetBinding
    parameter_results: tuple[BindingResult, ...]
    contract: BoundContract | None


@dataclass(frozen=True, slots=True)
class MonitorStep:
    timestamp_s: float
    lifecycle: Lifecycle
    verdict: Verdict
    maximum_safe_speed_mps: float | None
    progress_allowed: bool
    violations: tuple[str, ...]
    diagnostics: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class TraceResult:
    accepted: bool
    verdict: Verdict
    steps: tuple[MonitorStep, ...]
    violations: tuple[str, ...]
    diagnostics: tuple[str, ...]


def enum_value(value: Any) -> Any:
    """Convert nested Enum values for JSON artifacts without changing semantics."""
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, tuple):
        return [enum_value(item) for item in value]
    if isinstance(value, list):
        return [enum_value(item) for item in value]
    if isinstance(value, dict):
        return {key: enum_value(item) for key, item in value.items()}
    return value
