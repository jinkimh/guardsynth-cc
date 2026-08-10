"""Conservative stateful checker for sequential CoC obligations."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import hashlib
import json

from experiments.sequential_coc.contract_ir import (
    Action,
    CheckResult,
    ContractEvent,
    ContradictionType,
    ObligationState,
)
from experiments.sequential_coc.event_local_checker import (
    _CONTRADICTION_ORDER,
    _validated_events,
)


_UNKNOWN_REASON_ORDER = (
    "PARSE_STATUS_UNKNOWN",
    "OVERLAPPING_OBLIGATION",
    "STALE_RELEASE_UNKNOWN",
    "ACTIVE_RELEASE_UNKNOWN",
    "ACTIVE_SATISFACTION_UNKNOWN",
)

_CONTRADICTION_RULES = [
    {"id": "PREMATURE_RELEASE", "action": "ACCELERATE_OR_PROCEED", "active": "ANY", "when": "CURRENT_RELEASE_FALSE", "flag": "PREMATURE_RELEASE"},
    {"id": "HOLD_GO_CONFLICT", "action": "ACCELERATE_OR_PROCEED", "active": "TRUE", "when": "CURRENT_RELEASE_NOT_FALSE_AND_EFFECTIVE_RELEASE_FALSE", "flag": "HOLD_GO_CONFLICT"},
    {"id": "ORDER_VIOLATION_NO_ACTIVE", "action": "ACCELERATE_OR_PROCEED", "active": "FALSE", "when": "CURRENT_SATISFACTION_FALSE", "flag": "ORDER_VIOLATION"},
    {"id": "ORDER_VIOLATION_ACTIVE", "action": "ACCELERATE_OR_PROCEED", "active": "TRUE", "when": "EFFECTIVE_SATISFACTION_FALSE", "flag": "ORDER_VIOLATION"},
    {"id": "STALE_OBLIGATION", "action": "STOP_OR_YIELD", "active": "SAME", "when": "EFFECTIVE_RELEASE_TRUE", "flag": "STALE_OBLIGATION"},
]

_TRANSITION_BRANCHES = [
    {"id": "HOLD_START_RELEASED", "action": "STOP_OR_YIELD", "active": "FALSE", "when": "CURRENT_RELEASE_TRUE", "active_after": "NONE", "state": "RELEASED", "unknown_reasons": []},
    {"id": "HOLD_START_SATISFIED", "action": "STOP_OR_YIELD", "active": "FALSE", "when": "CURRENT_RELEASE_NOT_TRUE_AND_CURRENT_SATISFACTION_TRUE", "active_after": "START", "state": "SATISFIED_WAIT_RELEASE", "unknown_reasons": []},
    {"id": "HOLD_START_ACTIVE", "action": "STOP_OR_YIELD", "active": "FALSE", "when": "CURRENT_RELEASE_NOT_TRUE_AND_CURRENT_SATISFACTION_NOT_TRUE", "active_after": "START", "state": "ACTIVE", "unknown_reasons": []},
    {"id": "HOLD_OVERLAP", "action": "STOP_OR_YIELD", "active": "DISTINCT", "when": "ANY", "active_after": "RETAIN", "state": "UNKNOWN", "unknown_reasons": ["OVERLAPPING_OBLIGATION"]},
    {"id": "HOLD_CONTINUE_STALE", "action": "STOP_OR_YIELD", "active": "SAME", "when": "EFFECTIVE_RELEASE_TRUE", "active_after": "RETAIN", "state": "VIOLATED", "unknown_reasons": []},
    {"id": "HOLD_CONTINUE_SATISFIED", "action": "STOP_OR_YIELD", "active": "SAME", "when": "EFFECTIVE_RELEASE_FALSE_AND_EFFECTIVE_SATISFACTION_TRUE", "active_after": "RETAIN", "state": "SATISFIED_WAIT_RELEASE", "unknown_reasons": []},
    {"id": "HOLD_CONTINUE_ACTIVE", "action": "STOP_OR_YIELD", "active": "SAME", "when": "EFFECTIVE_RELEASE_FALSE_AND_EFFECTIVE_SATISFACTION_NOT_TRUE", "active_after": "RETAIN", "state": "ACTIVE", "unknown_reasons": []},
    {"id": "HOLD_CONTINUE_UNKNOWN", "action": "STOP_OR_YIELD", "active": "SAME", "when": "EFFECTIVE_RELEASE_UNKNOWN", "active_after": "RETAIN", "state": "UNKNOWN", "unknown_reasons": ["STALE_RELEASE_UNKNOWN"]},
    {"id": "PROCEED_NO_ACTIVE_FLAGGED", "action": "ACCELERATE_OR_PROCEED", "active": "FALSE", "when": "ANY_CURRENT_CONTRADICTION_FLAG", "active_after": "NONE", "state": "VIOLATED", "unknown_reasons": []},
    {"id": "PROCEED_NO_ACTIVE_CLEAR", "action": "ACCELERATE_OR_PROCEED", "active": "FALSE", "when": "NO_CURRENT_CONTRADICTION_FLAG", "active_after": "NONE", "state": "INACTIVE", "unknown_reasons": []},
    {"id": "PROCEED_ACTIVE_FLAGGED", "action": "ACCELERATE_OR_PROCEED", "active": "TRUE", "when": "ANY_CURRENT_CONTRADICTION_FLAG", "active_after": "RETAIN", "state": "VIOLATED", "unknown_reasons": []},
    {"id": "PROCEED_ACTIVE_UNKNOWN", "action": "ACCELERATE_OR_PROCEED", "active": "TRUE", "when": "NO_FLAG_AND_ANY_REQUIRED_EFFECTIVE_EVIDENCE_UNKNOWN", "active_after": "RETAIN", "state": "UNKNOWN", "unknown_reasons": ["ACTIVE_RELEASE_UNKNOWN", "ACTIVE_SATISFACTION_UNKNOWN"], "unknown_reason_policy": "ADD_CODE_ONLY_FOR_CORRESPONDING_UNKNOWN_EVIDENCE"},
    {"id": "PROCEED_ACTIVE_RELEASED", "action": "ACCELERATE_OR_PROCEED", "active": "TRUE", "when": "NO_FLAG_AND_EFFECTIVE_RELEASE_TRUE_AND_EFFECTIVE_SATISFACTION_TRUE", "active_after": "NONE", "state": "RELEASED", "unknown_reasons": []},
    {"id": "MAINTAIN_NO_ACTIVE", "action": "MAINTAIN_SPEED", "active": "FALSE", "when": "ANY", "active_after": "NONE", "state": "INACTIVE", "unknown_reasons": []},
    {"id": "MAINTAIN_ACTIVE_RELEASED", "action": "MAINTAIN_SPEED", "active": "TRUE", "when": "EFFECTIVE_RELEASE_TRUE", "active_after": "NONE", "state": "RELEASED", "unknown_reasons": []},
    {"id": "MAINTAIN_ACTIVE_SATISFIED", "action": "MAINTAIN_SPEED", "active": "TRUE", "when": "EFFECTIVE_RELEASE_FALSE_AND_EFFECTIVE_SATISFACTION_TRUE", "active_after": "RETAIN", "state": "SATISFIED_WAIT_RELEASE", "unknown_reasons": []},
    {"id": "MAINTAIN_ACTIVE", "action": "MAINTAIN_SPEED", "active": "TRUE", "when": "EFFECTIVE_RELEASE_FALSE_AND_EFFECTIVE_SATISFACTION_NOT_TRUE", "active_after": "RETAIN", "state": "ACTIVE", "unknown_reasons": []},
    {"id": "MAINTAIN_ACTIVE_UNKNOWN", "action": "MAINTAIN_SPEED", "active": "TRUE", "when": "EFFECTIVE_RELEASE_UNKNOWN", "active_after": "RETAIN", "state": "UNKNOWN", "unknown_reasons": ["ACTIVE_RELEASE_UNKNOWN"]},
]

_TRANSITION_RULE_DESCRIPTION: dict[str, object] = {
    "version": "sequential-coc-transition-v2",
    "action_count": 4,
    "state_count": 6,
    "active_obligation_capacity": 1,
    "primary_contradiction_count": 4,
    "contradiction_order": [kind.value for kind in _CONTRADICTION_ORDER],
    "unknown_reason_order": list(_UNKNOWN_REASON_ORDER),
    "input_validation": {"container": "LIST", "scene_count": "ZERO_OR_ONE", "key_fields": ["timestamp_us", "phase_index"], "order": "NONDECREASING_REJECT_INVALID", "empty_state_trace": ["INACTIVE"]},
    "evidence_update": {"policy": "LATER_KNOWN_ONLY", "fields": ["release", "satisfaction"], "unknown_retains_prior": True, "applies_when": ["ACTIVE_SAME", "ACTIVE_PROCEED", "ACTIVE_MAINTAIN"], "distinct_overlap": "NO_UPDATE_RETAIN_ACTIVE"},
    "event_evaluation_order": ["PARSE_UNKNOWN_REASON", "KNOWN_EVIDENCE_UPDATE", "CONTRADICTION_RULES", "TRANSITION_BRANCH", "STICKY_TRACE_OVERLAY"],
    "contradiction_rules": _CONTRADICTION_RULES,
    "transition_branches": _TRANSITION_BRANCHES,
    "contradiction_rule_count": len(_CONTRADICTION_RULES),
    "transition_branch_count": len(_TRANSITION_BRANCHES),
    "result_policy": {"verdict_precedence": ["CONTRADICTION", "UNKNOWN", "CONSISTENT"], "contradictions_sticky": True, "first_event_id": "EARLIEST_CONTRADICTION", "consume_complete_sequence": True, "trace_initial_state": "INACTIVE", "trace_entries_per_event": 1, "parse_unknown_reason": "PARSE_STATUS_UNKNOWN", "parse_unknown_trace_overlay": "UNKNOWN_UNLESS_STICKY_CONTRADICTION", "contradiction_trace_overlay": "VIOLATED"},
}


def transition_rule_description() -> dict[str, object]:
    """Return the versioned, JSON-safe finite transition contract."""
    return deepcopy(_TRANSITION_RULE_DESCRIPTION)


def transition_table_sha256() -> str:
    """Hash the canonical transition contract used by executable observers."""
    canonical = json.dumps(
        _TRANSITION_RULE_DESCRIPTION,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


@dataclass(slots=True)
class _ActiveObligation:
    action: Action
    target: str | None
    satisfaction_known: bool
    satisfaction_value: bool
    release_known: bool
    release_value: bool

    @classmethod
    def from_event(cls, event: ContractEvent) -> "_ActiveObligation":
        return cls(
            action=event.action,
            target=event.target,
            satisfaction_known=event.satisfaction_known,
            satisfaction_value=event.satisfaction_value,
            release_known=event.release_known,
            release_value=event.release_value,
        )

    def same_as(self, event: ContractEvent) -> bool:
        return self.action is event.action and self.target == event.target

    def update_known_evidence(self, event: ContractEvent) -> None:
        if event.satisfaction_known:
            self.satisfaction_known = True
            self.satisfaction_value = event.satisfaction_value
        if event.release_known:
            self.release_known = True
            self.release_value = event.release_value


def _active_state(active: _ActiveObligation) -> ObligationState:
    if active.satisfaction_known and active.satisfaction_value:
        return ObligationState.SATISFIED_WAIT_RELEASE
    return ObligationState.ACTIVE


def _add_reason(reasons: set[str], reason: str) -> None:
    reasons.add(reason)


def check_stateful(events: list[ContractEvent]) -> CheckResult:
    """Consume a complete ordered event sequence with one longitudinal obligation."""
    _validated_events(events)
    active: _ActiveObligation | None = None
    found: set[ContradictionType] = set()
    first_event_id: str | None = None
    unknown_reasons: set[str] = set()
    state_trace = [ObligationState.INACTIVE]

    for event in events:
        event_flags: list[ContradictionType] = []
        event_unknown = False
        if event.parse_status.startswith("UNKNOWN"):
            _add_reason(unknown_reasons, "PARSE_STATUS_UNKNOWN")
            event_unknown = True

        if event.action in (Action.STOP_OR_HOLD, Action.YIELD_OR_DECELERATE):
            if active is None:
                if event.release_known and event.release_value:
                    visible_state = ObligationState.RELEASED
                else:
                    active = _ActiveObligation.from_event(event)
                    visible_state = _active_state(active)
            elif not active.same_as(event):
                _add_reason(unknown_reasons, "OVERLAPPING_OBLIGATION")
                event_unknown = True
                visible_state = ObligationState.UNKNOWN
            else:
                active.update_known_evidence(event)
                if active.release_known and active.release_value:
                    event_flags.append(ContradictionType.STALE_OBLIGATION)
                    visible_state = ObligationState.VIOLATED
                elif not active.release_known:
                    _add_reason(unknown_reasons, "STALE_RELEASE_UNKNOWN")
                    event_unknown = True
                    visible_state = ObligationState.UNKNOWN
                else:
                    visible_state = _active_state(active)

        elif event.action is Action.ACCELERATE_OR_PROCEED:
            if active is None:
                if event.release_known and not event.release_value:
                    event_flags.append(ContradictionType.PREMATURE_RELEASE)
                if event.satisfaction_known and not event.satisfaction_value:
                    event_flags.append(ContradictionType.ORDER_VIOLATION)
                visible_state = (
                    ObligationState.VIOLATED
                    if event_flags
                    else ObligationState.INACTIVE
                )
            else:
                active.update_known_evidence(event)
                if event.release_known and not event.release_value:
                    event_flags.append(ContradictionType.PREMATURE_RELEASE)
                elif active.release_known and not active.release_value:
                    event_flags.append(ContradictionType.HOLD_GO_CONFLICT)
                if active.satisfaction_known and not active.satisfaction_value:
                    event_flags.append(ContradictionType.ORDER_VIOLATION)

                if event_flags:
                    visible_state = ObligationState.VIOLATED
                elif not active.release_known or not active.satisfaction_known:
                    if not active.release_known:
                        _add_reason(unknown_reasons, "ACTIVE_RELEASE_UNKNOWN")
                    if not active.satisfaction_known:
                        _add_reason(
                            unknown_reasons, "ACTIVE_SATISFACTION_UNKNOWN"
                        )
                    event_unknown = True
                    visible_state = ObligationState.UNKNOWN
                else:
                    active = None
                    visible_state = ObligationState.RELEASED

        else:
            if active is None:
                visible_state = ObligationState.INACTIVE
            else:
                active.update_known_evidence(event)
                if active.release_known and active.release_value:
                    active = None
                    visible_state = ObligationState.RELEASED
                elif not active.release_known:
                    _add_reason(unknown_reasons, "ACTIVE_RELEASE_UNKNOWN")
                    event_unknown = True
                    visible_state = ObligationState.UNKNOWN
                else:
                    visible_state = _active_state(active)

        if event_flags and first_event_id is None:
            first_event_id = event.event_id
        found.update(event_flags)
        if found:
            state_trace.append(ObligationState.VIOLATED)
        elif event_unknown:
            state_trace.append(ObligationState.UNKNOWN)
        else:
            state_trace.append(visible_state)

    ordered_flags = tuple(kind for kind in _CONTRADICTION_ORDER if kind in found)
    ordered_reasons = tuple(
        reason for reason in _UNKNOWN_REASON_ORDER if reason in unknown_reasons
    )
    verdict = (
        "CONTRADICTION"
        if ordered_flags
        else "UNKNOWN"
        if ordered_reasons
        else "CONSISTENT"
    )
    return CheckResult(
        verdict=verdict,
        contradiction_types=ordered_flags,
        first_event_id=first_event_id,
        state_trace=tuple(state_trace),
        unknown_reasons=ordered_reasons,
    )
