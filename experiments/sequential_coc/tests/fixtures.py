"""Real, deterministic IR fixtures shared by sequential CoC tests."""

from __future__ import annotations

from experiments.sequential_coc.contract_ir import (
    Action,
    CheckResult,
    ContractEvent,
    ContradictionType,
    EvidenceValue,
    EventWindow,
    ObligationState,
)


def _evidence_pair(value: EvidenceValue) -> tuple[bool, bool]:
    if not isinstance(value, EvidenceValue):
        raise TypeError("release evidence must be an EvidenceValue")
    if value is EvidenceValue.UNKNOWN:
        return False, False
    return True, value is EvidenceValue.TRUE


def event(
    timestamp_us: int = 0,
    *,
    event_id: str | None = None,
    scene_id: str = "scene-a",
    action: Action = Action.MAINTAIN_SPEED,
    phase_index: int = 0,
) -> ContractEvent:
    return ContractEvent(
        scene_id=scene_id,
        event_id=event_id or f"event-{timestamp_us}-{phase_index}",
        timestamp_us=timestamp_us,
        action=action,
        phase_index=phase_index,
        provenance="FIXTURE",
        parse_status="PARSED",
    )


def hold_event(
    *,
    timestamp_us: int = 0,
    event_id: str = "hold",
    scene_id: str = "scene-a",
    release: EvidenceValue = EvidenceValue.UNKNOWN,
) -> ContractEvent:
    release_known, release_value = _evidence_pair(release)
    return ContractEvent(
        scene_id=scene_id,
        event_id=event_id,
        timestamp_us=timestamp_us,
        action=Action.STOP_OR_HOLD,
        release_known=release_known,
        release_value=release_value,
        release_condition="clearance confirmed",
        permitted_next_action=Action.ACCELERATE_OR_PROCEED,
        provenance="FIXTURE",
        parse_status="PARSED",
    )


def proceed_event(
    *, timestamp_us: int = 1, event_id: str = "proceed", scene_id: str = "scene-a"
) -> ContractEvent:
    return ContractEvent(
        scene_id=scene_id,
        event_id=event_id,
        timestamp_us=timestamp_us,
        action=Action.ACCELERATE_OR_PROCEED,
        provenance="FIXTURE",
        parse_status="PARSED",
    )


def clear_then_go_window() -> EventWindow:
    hold = hold_event(timestamp_us=0, event_id="hold-clear", release=EvidenceValue.FALSE)
    go = ContractEvent(
        scene_id="scene-a",
        event_id="go-after-clear",
        timestamp_us=1,
        action=Action.ACCELERATE_OR_PROCEED,
        release_known=True,
        release_value=True,
        release_condition="clearance confirmed",
        provenance="FIXTURE",
        parse_status="PARSED",
    )
    return EventWindow("fixture-clear-then-go", "scene-a", (hold, go))


def conflict_then_valid_release() -> tuple[ContractEvent, ...]:
    return (
        hold_event(timestamp_us=0, event_id="hold-unreleased", release=EvidenceValue.FALSE),
        proceed_event(timestamp_us=1, event_id="premature-go"),
        hold_event(timestamp_us=2, event_id="hold-released", release=EvidenceValue.TRUE),
    )


def known_hold() -> tuple[ContractEvent, ...]:
    return (hold_event(release=EvidenceValue.FALSE),)


def unknown_release() -> tuple[ContractEvent, ...]:
    return (hold_event(release=EvidenceValue.UNKNOWN),)


def accelerating_trace() -> tuple[dict[str, float], ...]:
    return (
        {"timestamp_s": 0.0, "speed_mps": 0.0},
        {"timestamp_s": 1.0, "speed_mps": 2.0},
    )


def fixture_results() -> tuple[CheckResult, ...]:
    return (
        CheckResult(verdict="CONSISTENT"),
        CheckResult(
            verdict="CONTRADICTION",
            contradiction_types=(ContradictionType.HOLD_GO_CONFLICT,),
            first_event_id="premature-go",
            state_trace=(ObligationState.ACTIVE,),
        ),
        CheckResult(
            verdict="UNKNOWN",
            state_trace=(ObligationState.UNKNOWN,),
            unknown_reasons=("release evidence unavailable",),
        ),
    )
