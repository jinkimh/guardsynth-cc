"""History-free baseline for explicit per-event CoC contradictions."""

from __future__ import annotations

from experiments.sequential_coc.contract_ir import (
    Action,
    CheckResult,
    ContractEvent,
    ContradictionType,
    ObligationState,
)


_CONTRADICTION_ORDER = (
    ContradictionType.HOLD_GO_CONFLICT,
    ContradictionType.PREMATURE_RELEASE,
    ContradictionType.ORDER_VIOLATION,
    ContradictionType.STALE_OBLIGATION,
)


def _validated_events(events: list[ContractEvent]) -> list[ContractEvent]:
    if not isinstance(events, list):
        raise TypeError("events must be a list")
    if any(not isinstance(item, ContractEvent) for item in events):
        raise TypeError("events must contain ContractEvent values")
    if not events:
        return events
    scene_id = events[0].scene_id
    if any(item.scene_id != scene_id for item in events):
        raise ValueError("events must belong to one scene")
    keys = [(item.timestamp_us, item.phase_index) for item in events]
    if keys != sorted(keys):
        raise ValueError("events must be in nondecreasing timestamp/phase order")
    return events


def _local_state(event: ContractEvent) -> ObligationState:
    if event.action in (Action.STOP_OR_HOLD, Action.YIELD_OR_DECELERATE):
        if event.release_known and event.release_value:
            return ObligationState.RELEASED
        if event.satisfaction_known and event.satisfaction_value:
            return ObligationState.SATISFIED_WAIT_RELEASE
        return ObligationState.ACTIVE
    return ObligationState.INACTIVE


def check_event_local(events: list[ContractEvent]) -> CheckResult:
    """Check only evidence carried by each current event, without history."""
    _validated_events(events)
    found: set[ContradictionType] = set()
    first_event_id: str | None = None
    unknown_reasons: list[str] = []
    state_trace = [ObligationState.INACTIVE]

    for event in events:
        event_flags: list[ContradictionType] = []
        parse_unknown = event.parse_status.startswith("UNKNOWN")
        if parse_unknown and "PARSE_STATUS_UNKNOWN" not in unknown_reasons:
            unknown_reasons.append("PARSE_STATUS_UNKNOWN")

        if event.action is Action.ACCELERATE_OR_PROCEED:
            if event.release_known and not event.release_value:
                event_flags.append(ContradictionType.PREMATURE_RELEASE)
            if event.satisfaction_known and not event.satisfaction_value:
                event_flags.append(ContradictionType.ORDER_VIOLATION)

        if event_flags and first_event_id is None:
            first_event_id = event.event_id
        found.update(event_flags)

        if found:
            state_trace.append(ObligationState.VIOLATED)
        elif parse_unknown:
            state_trace.append(ObligationState.UNKNOWN)
        else:
            state_trace.append(_local_state(event))

    ordered_flags = tuple(kind for kind in _CONTRADICTION_ORDER if kind in found)
    verdict = (
        "CONTRADICTION"
        if ordered_flags
        else "UNKNOWN"
        if unknown_reasons
        else "CONSISTENT"
    )
    return CheckResult(
        verdict=verdict,
        contradiction_types=ordered_flags,
        first_event_id=first_event_id,
        state_trace=tuple(state_trace),
        unknown_reasons=tuple(unknown_reasons),
    )
