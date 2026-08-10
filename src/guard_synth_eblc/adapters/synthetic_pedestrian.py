"""Public synthetic traces for the pedestrian conflict-zone vertical slice."""

from __future__ import annotations

from ..types import ContextFrame, EpistemicKind, Fact, Truth, VehicleProfile


TARGET = "synthetic-pedestrian:P17"
ZONE = "synthetic-zone:CZ4"

PILOT_PROFILE = VehicleProfile(
    profile_id="P0B-SYNTHETIC-VEHICLE-PROFILE-v0",
    maximum_service_deceleration_mps2=3.0,
    response_time_s=0.5,
    position_uncertainty_m=0.5,
    evidence_ref="P0B-SYNTHETIC-VEHICLE-PROFILE-v0",
)


def frame(
    timestamp_s: float,
    truth: Truth,
    *,
    x: float = -2.2,
    speed: float = 0.0,
    fact_timestamp_s: float | None = None,
    epistemic: EpistemicKind = EpistemicKind.OBSERVED,
    coordinate_frame: str = "ego_path_s",
    distance_unit: str = "m",
    target: str = TARGET,
    zone: str = ZONE,
    scope_valid: bool = True,
    safe_progress: bool = False,
) -> ContextFrame:
    return ContextFrame(
        timestamp_s=timestamp_s,
        hazard=Fact(
            truth,
            epistemic,
            "SYNTHETIC-P0B-SENSOR" if epistemic is not EpistemicKind.CLAIMED else "SYNTHETIC-COC-CLAIM",
            timestamp_s if fact_timestamp_s is None else fact_timestamp_s,
            0.2,
        ),
        ego_front_x_m=x,
        ego_speed_mps=speed,
        zone_entry_x_m=0.0,
        target_entity_id=target,
        zone_id=zone,
        coordinate_frame=coordinate_frame,
        distance_unit=distance_unit,
        scope_valid=scope_valid,
        safe_progress_available=safe_progress,
    )


def initial_frame() -> ContextFrame:
    return frame(0.0, Truth.TRUE, x=-12.0, speed=6.0)


def safe_release_reactivation_trace() -> tuple[ContextFrame, ...]:
    return (
        frame(0.0, Truth.TRUE, x=-12.0, speed=6.0),
        frame(0.1, Truth.TRUE, x=-7.0, speed=4.0),
        frame(0.2, Truth.FALSE),
        frame(0.3, Truth.FALSE),
        frame(0.4, Truth.TRUE, speed=0.1),
        frame(0.5, Truth.FALSE),
        frame(0.6, Truth.FALSE),
        frame(0.7, Truth.FALSE, x=1.0, speed=2.0, safe_progress=True),
    )


def locked_translation_traces() -> dict[str, tuple[ContextFrame, ...]]:
    return {
        "safe_release_reactivation": safe_release_reactivation_trace(),
        "one_frame_false_no_release": (frame(0.0, Truth.TRUE), frame(0.1, Truth.FALSE)),
        "unknown_active_fallback": (frame(0.0, Truth.TRUE), frame(0.1, Truth.UNKNOWN)),
        "conflicting_evidence": (frame(0.0, Truth.CONFLICT),),
        "active_zone_entry_violation": (frame(0.0, Truth.TRUE, x=-1.49, speed=0.0),),
        "dynamic_speed_violation": (frame(0.0, Truth.TRUE, x=-12.0, speed=20.0),),
        "stale_fact": (frame(0.5, Truth.TRUE, fact_timestamp_s=0.0),),
        "safe_progress": (frame(0.0, Truth.FALSE, x=1.0, speed=2.0, safe_progress=True),),
    }
