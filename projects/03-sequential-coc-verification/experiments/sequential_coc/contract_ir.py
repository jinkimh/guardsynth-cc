"""Immutable, text-safe intermediate representation for sequential CoC checks."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
import json
from typing import Any, Iterable, Mapping


class Action(str, Enum):
    STOP_OR_HOLD = "STOP_OR_HOLD"
    YIELD_OR_DECELERATE = "YIELD_OR_DECELERATE"
    ACCELERATE_OR_PROCEED = "ACCELERATE_OR_PROCEED"
    MAINTAIN_SPEED = "MAINTAIN_SPEED"


class EvidenceValue(str, Enum):
    UNKNOWN = "UNKNOWN"
    FALSE = "FALSE"
    TRUE = "TRUE"

    @classmethod
    def from_known_value(cls, known: bool, value: bool) -> "EvidenceValue":
        _validate_evidence_pair("evidence", known, value)
        if not known:
            return cls.UNKNOWN
        return cls.TRUE if value else cls.FALSE


class ObligationState(str, Enum):
    INACTIVE = "INACTIVE"
    ACTIVE = "ACTIVE"
    SATISFIED_WAIT_RELEASE = "SATISFIED_WAIT_RELEASE"
    RELEASED = "RELEASED"
    VIOLATED = "VIOLATED"
    UNKNOWN = "UNKNOWN"


class ContradictionType(str, Enum):
    HOLD_GO_CONFLICT = "HOLD_GO_CONFLICT"
    PREMATURE_RELEASE = "PREMATURE_RELEASE"
    ORDER_VIOLATION = "ORDER_VIOLATION"
    STALE_OBLIGATION = "STALE_OBLIGATION"
    # This is deliberately a provenance-policy result, not a primary semantic type.
    UNSUPPORTED_CARRYOVER = "UNSUPPORTED_CARRYOVER"


def _validate_evidence_pair(name: str, known: bool, value: bool) -> None:
    if not isinstance(known, bool) or not isinstance(value, bool):
        raise TypeError(f"{name}_known and {name}_value must be bool")
    if not known and value:
        raise ValueError(f"{name}: unknown evidence must use (False, False)")


def _as_enum(enum_type: type[Enum], value: Any, name: str) -> Enum:
    if isinstance(value, enum_type):
        return value
    try:
        return enum_type(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} is not a valid {enum_type.__name__}: {value!r}") from exc


def _require_nonempty_string(name: str, value: Any) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{name} must be a non-empty string")
    return value


def _optional_string(name: str, value: Any) -> str | None:
    if value is not None and not isinstance(value, str):
        raise TypeError(f"{name} must be a string or None")
    return value


def _non_scalar_tuple(name: str, value: Any) -> tuple[Any, ...]:
    if isinstance(value, (str, bytes, Mapping)):
        raise TypeError(f"{name} must be a non-scalar iterable")
    try:
        return tuple(value)
    except TypeError as exc:
        raise TypeError(f"{name} must be a non-scalar iterable") from exc


def _evidence_pair_from_dict(value: Mapping[str, Any], prefix: str) -> tuple[bool, bool]:
    known_key = f"{prefix}_known"
    value_key = f"{prefix}_value"
    has_known = known_key in value
    has_value = value_key in value
    if not has_known and not has_value:
        return False, False
    if has_known != has_value:
        raise ValueError(f"{prefix} evidence requires both known and value fields")
    return value[known_key], value[value_key]


@dataclass(frozen=True, slots=True)
class ContractEvent:
    scene_id: str
    event_id: str
    timestamp_us: int
    action: Action
    trigger: str | None = None
    target: str | None = None
    satisfaction_known: bool = False
    satisfaction_value: bool = False
    release_known: bool = False
    release_value: bool = False
    permitted_next_action: Action | None = None
    phase_index: int = 0
    provenance: str = "UNSPECIFIED"
    parse_status: str = "UNKNOWN"
    source_text: str | None = None
    satisfaction_condition: str | None = None
    release_condition: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "scene_id", _require_nonempty_string("scene_id", self.scene_id))
        object.__setattr__(self, "event_id", _require_nonempty_string("event_id", self.event_id))
        if isinstance(self.timestamp_us, bool) or not isinstance(self.timestamp_us, int):
            raise TypeError("timestamp_us must be an int")
        if self.timestamp_us < 0:
            raise ValueError("timestamp_us must be non-negative")
        object.__setattr__(self, "action", _as_enum(Action, self.action, "action"))
        _validate_evidence_pair(
            "satisfaction", self.satisfaction_known, self.satisfaction_value
        )
        _validate_evidence_pair("release", self.release_known, self.release_value)
        if self.permitted_next_action is not None:
            object.__setattr__(
                self,
                "permitted_next_action",
                _as_enum(Action, self.permitted_next_action, "permitted_next_action"),
            )
        if isinstance(self.phase_index, bool) or not isinstance(self.phase_index, int):
            raise TypeError("phase_index must be an int")
        if self.phase_index < 0:
            raise ValueError("phase_index must be non-negative")
        object.__setattr__(self, "trigger", _optional_string("trigger", self.trigger))
        object.__setattr__(self, "target", _optional_string("target", self.target))
        object.__setattr__(self, "provenance", _require_nonempty_string("provenance", self.provenance))
        object.__setattr__(self, "parse_status", _require_nonempty_string("parse_status", self.parse_status))
        object.__setattr__(self, "source_text", _optional_string("source_text", self.source_text))
        object.__setattr__(
            self, "satisfaction_condition", _optional_string("satisfaction_condition", self.satisfaction_condition)
        )
        object.__setattr__(self, "release_condition", _optional_string("release_condition", self.release_condition))

    @property
    def satisfaction_evidence(self) -> EvidenceValue:
        return EvidenceValue.from_known_value(self.satisfaction_known, self.satisfaction_value)

    @property
    def release_evidence(self) -> EvidenceValue:
        return EvidenceValue.from_known_value(self.release_known, self.release_value)

    def to_dict(self, include_text: bool = False) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "scene_id": self.scene_id,
            "event_id": self.event_id,
            "timestamp_us": self.timestamp_us,
            "action": self.action.value,
            "trigger": self.trigger,
            "target": self.target,
            "satisfaction_known": self.satisfaction_known,
            "satisfaction_value": self.satisfaction_value,
            "release_known": self.release_known,
            "release_value": self.release_value,
            "permitted_next_action": (
                self.permitted_next_action.value if self.permitted_next_action is not None else None
            ),
            "phase_index": self.phase_index,
            "provenance": self.provenance,
            "parse_status": self.parse_status,
            "satisfaction_condition": self.satisfaction_condition,
            "release_condition": self.release_condition,
        }
        if include_text:
            payload["source_text"] = self.source_text
        return payload

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ContractEvent":
        if not isinstance(value, Mapping):
            raise TypeError("ContractEvent input must be a mapping")
        satisfaction_known, satisfaction_value = _evidence_pair_from_dict(value, "satisfaction")
        release_known, release_value = _evidence_pair_from_dict(value, "release")
        return cls(
            scene_id=value["scene_id"],
            event_id=value["event_id"],
            timestamp_us=value["timestamp_us"],
            action=value["action"],
            trigger=value.get("trigger"),
            target=value.get("target"),
            satisfaction_known=satisfaction_known,
            satisfaction_value=satisfaction_value,
            release_known=release_known,
            release_value=release_value,
            permitted_next_action=value.get("permitted_next_action"),
            phase_index=value.get("phase_index", 0),
            provenance=value.get("provenance", "UNSPECIFIED"),
            parse_status=value.get("parse_status", "UNKNOWN"),
            source_text=value.get("source_text"),
            satisfaction_condition=value.get("satisfaction_condition"),
            release_condition=value.get("release_condition"),
        )


@dataclass(frozen=True, slots=True)
class EventWindow:
    window_id: str
    cluster_id: str
    events: tuple[ContractEvent, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "window_id", _require_nonempty_string("window_id", self.window_id))
        object.__setattr__(self, "cluster_id", _require_nonempty_string("cluster_id", self.cluster_id))
        events = tuple(self.events)
        if not events:
            raise ValueError("events must be non-empty")
        if any(not isinstance(event, ContractEvent) for event in events):
            raise TypeError("events must contain ContractEvent values")
        scene_id = events[0].scene_id
        if self.cluster_id != scene_id:
            raise ValueError("cluster_id must match the events' scene identity")
        if any(event.scene_id != scene_id for event in events):
            raise ValueError("events must have a consistent scene identity")
        keys = [(event.timestamp_us, event.phase_index) for event in events]
        if keys != sorted(keys):
            raise ValueError("events must be in nondecreasing timestamp/phase order")
        object.__setattr__(self, "events", events)

    def _hash_payload(self) -> dict[str, Any]:
        return {
            "window_id": self.window_id,
            "cluster_id": self.cluster_id,
            "events": [event.to_dict(include_text=False) for event in self.events],
        }

    @property
    def content_hash(self) -> str:
        canonical = json.dumps(
            self._hash_payload(), ensure_ascii=True, sort_keys=True, separators=(",", ":")
        )
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def to_dict(self, include_text: bool = False) -> dict[str, Any]:
        return {
            "window_id": self.window_id,
            "cluster_id": self.cluster_id,
            "events": [event.to_dict(include_text=include_text) for event in self.events],
            "content_hash": self.content_hash,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "EventWindow":
        if not isinstance(value, Mapping):
            raise TypeError("EventWindow input must be a mapping")
        raw_events = value["events"]
        if not isinstance(raw_events, Iterable) or isinstance(raw_events, (str, bytes, Mapping)):
            raise TypeError("events must be an iterable of mappings")
        restored = cls(
            window_id=value["window_id"],
            cluster_id=value["cluster_id"],
            events=tuple(ContractEvent.from_dict(item) for item in raw_events),
        )
        expected_hash = value.get("content_hash")
        if expected_hash is not None and expected_hash != restored.content_hash:
            raise ValueError("content_hash does not match window content")
        return restored


@dataclass(frozen=True, slots=True)
class CheckResult:
    verdict: str
    contradiction_types: tuple[ContradictionType, ...] = ()
    first_event_id: str | None = None
    state_trace: tuple[ObligationState, ...] = ()
    unknown_reasons: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "verdict", _require_nonempty_string("verdict", self.verdict))
        contradiction_types = tuple(
            _as_enum(ContradictionType, kind, "contradiction type")
            for kind in self.contradiction_types
        )
        state_trace = tuple(
            _as_enum(ObligationState, state, "state_trace")
            for state in _non_scalar_tuple("state_trace", self.state_trace)
        )
        unknown_reasons = tuple(self.unknown_reasons)
        if any(not isinstance(reason, str) for reason in unknown_reasons):
            raise TypeError("unknown_reasons must contain strings")
        if self.first_event_id is not None:
            object.__setattr__(self, "first_event_id", _require_nonempty_string("first_event_id", self.first_event_id))
        object.__setattr__(self, "contradiction_types", contradiction_types)
        object.__setattr__(self, "state_trace", state_trace)
        object.__setattr__(self, "unknown_reasons", unknown_reasons)

    def to_dict(self) -> dict[str, Any]:
        return {
            "verdict": self.verdict,
            "contradiction_types": [kind.value for kind in self.contradiction_types],
            "first_event_id": self.first_event_id,
            "state_trace": [state.value for state in self.state_trace],
            "unknown_reasons": list(self.unknown_reasons),
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "CheckResult":
        if not isinstance(value, Mapping):
            raise TypeError("CheckResult input must be a mapping")
        return cls(
            verdict=value["verdict"],
            contradiction_types=tuple(value.get("contradiction_types", ())),
            first_event_id=value.get("first_event_id"),
            state_trace=value.get("state_trace", ()),
            unknown_reasons=tuple(value.get("unknown_reasons", ())),
        )
