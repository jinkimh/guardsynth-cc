from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable

import numpy as np


DT = 0.2
HORIZON_STEPS = 60
CRUISE_SPEED = 8.0
MAX_ACCEL = 1.5
MAX_BRAKE = 5.0
COMFORT_BRAKE = 2.5
STOP_MARGIN = 1.25
MIN_LEAD_GAP = 2.0
TIME_HEADWAY = 1.25

KINDS = ("crosswalk", "stop_intersection", "lead_brake")
STATE_DIM = 10
COC_DIM = 3
CONTRACT_DIM = 6


@dataclass(frozen=True)
class Scenario:
    kind: str
    initial_distance: float
    ego_speed: float
    hazard_clear_time: float = 0.0
    occlusion_start: float = 99.0
    occlusion_end: float = 99.0
    lead_speed: float = 0.0
    lead_brake_time: float = 99.0
    lead_decel: float = 0.0
    hazard_intervals: tuple[tuple[float, float], ...] = ()
    occlusion_intervals: tuple[tuple[float, float], ...] = ()


@dataclass(frozen=True)
class WorldState:
    scenario: Scenario
    t: float
    ego_x: float
    ego_v: float
    lead_x: float
    lead_v: float
    stopped_steps: int = 0
    has_stopped: bool = False
    done: bool = False


@dataclass(frozen=True)
class ContractStatus:
    hold_required: bool
    release_allowed: bool
    uncertainty_requires_stop: bool
    stop_completion_required: bool
    safe_margin: float
    max_safe_speed: float


@dataclass
class EpisodeMetrics:
    forbidden_entry: bool = False
    collision: bool = False
    safe_gap_violation: bool = False
    interventions: int = 0
    released_stop_steps: int = 0
    progress: float = 0.0
    mean_abs_jerk: float = 0.0
    completed: bool = False

    @property
    def unsafe(self) -> bool:
        return self.forbidden_entry or self.collision


def sample_scenario(kind: str, rng: np.random.Generator, split: str) -> Scenario:
    if kind not in KINDS:
        raise ValueError(f"unknown scenario kind: {kind}")
    if split not in {"train", "ood"}:
        raise ValueError(f"unknown split: {split}")

    if kind == "crosswalk":
        if split == "train":
            return Scenario(
                kind=kind,
                initial_distance=float(rng.uniform(18.0, 30.0)),
                ego_speed=float(rng.uniform(4.0, 7.0)),
                hazard_clear_time=float(rng.uniform(1.2, 2.8)),
            )
        occluded = bool(rng.random() < 0.65)
        occ_start = float(rng.uniform(0.4, 1.5)) if occluded else 99.0
        occ_end = float(rng.uniform(2.5, 4.5)) if occluded else 99.0
        return Scenario(
            kind=kind,
            initial_distance=float(rng.uniform(12.0, 23.0)),
            ego_speed=float(rng.uniform(5.0, 8.0)),
            hazard_clear_time=float(rng.uniform(3.8, 6.0)),
            occlusion_start=occ_start,
            occlusion_end=occ_end,
        )

    if kind == "stop_intersection":
        if split == "train":
            return Scenario(
                kind=kind,
                initial_distance=float(rng.uniform(18.0, 30.0)),
                ego_speed=float(rng.uniform(4.0, 7.0)),
                hazard_clear_time=float(rng.uniform(1.0, 2.6)),
            )
        occluded = bool(rng.random() < 0.5)
        occ_start = float(rng.uniform(0.5, 1.8)) if occluded else 99.0
        occ_end = float(rng.uniform(2.5, 4.5)) if occluded else 99.0
        return Scenario(
            kind=kind,
            initial_distance=float(rng.uniform(12.0, 23.0)),
            ego_speed=float(rng.uniform(5.0, 8.0)),
            hazard_clear_time=float(rng.uniform(3.5, 5.8)),
            occlusion_start=occ_start,
            occlusion_end=occ_end,
        )

    if split == "train":
        lead_v = float(rng.uniform(4.5, 7.5))
        ego_v = float(np.clip(lead_v + rng.uniform(-0.5, 1.5), 4.0, 8.0))
        return Scenario(
            kind=kind,
            initial_distance=float(rng.uniform(24.0, 38.0)),
            ego_speed=ego_v,
            lead_speed=lead_v,
            lead_brake_time=float(rng.uniform(2.5, 4.8)),
            lead_decel=float(rng.uniform(0.0, 1.2)),
        )
    lead_v = float(rng.uniform(4.0, 7.0))
    ego_v = float(np.clip(lead_v + rng.uniform(0.0, 2.5), 5.0, 8.0))
    return Scenario(
        kind=kind,
        initial_distance=float(rng.uniform(16.0, 27.0)),
        ego_speed=ego_v,
        lead_speed=lead_v,
        lead_brake_time=float(rng.uniform(0.5, 2.2)),
        lead_decel=float(rng.uniform(2.2, 4.2)),
    )


def initial_state(scenario: Scenario) -> WorldState:
    if scenario.kind == "lead_brake":
        return WorldState(scenario, 0.0, 0.0, scenario.ego_speed, scenario.initial_distance, scenario.lead_speed)
    return WorldState(scenario, 0.0, -scenario.initial_distance, scenario.ego_speed, 0.0, 0.0)


def is_visible(state: WorldState) -> bool:
    s = state.scenario
    if s.occlusion_intervals:
        return not any(start <= state.t < end for start, end in s.occlusion_intervals)
    return not (s.occlusion_start <= state.t < s.occlusion_end)


def hazard_active(state: WorldState) -> bool:
    if state.scenario.kind == "lead_brake":
        return True
    if state.scenario.hazard_intervals:
        return any(start <= state.t < end for start, end in state.scenario.hazard_intervals)
    return state.t < state.scenario.hazard_clear_time


def distance_measure(state: WorldState) -> float:
    if state.scenario.kind == "lead_brake":
        return state.lead_x - state.ego_x
    return -state.ego_x


def lead_safe_gap(state: WorldState) -> float:
    closing = max(0.0, state.ego_v - state.lead_v)
    return MIN_LEAD_GAP + TIME_HEADWAY * state.ego_v + (closing * closing) / (2.0 * COMFORT_BRAKE)


def contract_status(state: WorldState) -> ContractStatus:
    kind = state.scenario.kind
    visible = is_visible(state)
    active = hazard_active(state)
    distance = max(0.0, distance_measure(state))

    if kind == "crosswalk":
        hold = active or not visible
        max_v = np.sqrt(max(0.0, 2.0 * COMFORT_BRAKE * max(0.0, distance - STOP_MARGIN))) if hold else CRUISE_SPEED
        return ContractStatus(hold, not hold, not visible, False, STOP_MARGIN, float(max_v))

    if kind == "stop_intersection":
        incomplete_stop = not state.has_stopped
        hold = incomplete_stop or active or not visible
        max_v = np.sqrt(max(0.0, 2.0 * COMFORT_BRAKE * max(0.0, distance - STOP_MARGIN))) if hold else CRUISE_SPEED
        return ContractStatus(hold, not hold, not visible, incomplete_stop, STOP_MARGIN, float(max_v))

    gap = distance_measure(state)
    safe_gap = lead_safe_gap(state)
    closing = max(0.0, state.ego_v - state.lead_v)
    ttc = gap / closing if closing > 1e-6 else 99.0
    hold = gap < 1.25 * safe_gap or ttc < 4.0
    max_v = max(0.0, state.lead_v + (gap - safe_gap) / TIME_HEADWAY)
    return ContractStatus(hold, not hold, False, False, safe_gap, min(CRUISE_SPEED, max_v))


def base_observation(state: WorldState) -> np.ndarray:
    kind_index = KINDS.index(state.scenario.kind)
    one_hot = np.zeros(3, dtype=np.float32)
    one_hot[kind_index] = 1.0
    distance = float(np.clip(distance_measure(state), -5.0, 45.0)) / 40.0
    rel_speed = (state.ego_v - state.lead_v) / 10.0 if state.scenario.kind == "lead_brake" else 0.0
    fields = np.asarray(
        [
            state.ego_v / 10.0,
            distance,
            rel_speed,
            float(hazard_active(state)),
            float(is_visible(state)),
            float(state.has_stopped),
            state.t / (DT * HORIZON_STEPS),
        ],
        dtype=np.float32,
    )
    result = np.concatenate([one_hot, fields])
    assert result.shape == (STATE_DIM,)
    return result


def coc_features(state: WorldState) -> np.ndarray:
    # YIELD / STOP / DECELERATE: action intent only, with no hold/release semantics.
    result = np.zeros(COC_DIM, dtype=np.float32)
    result[KINDS.index(state.scenario.kind)] = 1.0
    return result


def contract_features(state: WorldState) -> np.ndarray:
    c = contract_status(state)
    return np.asarray(
        [
            float(c.hold_required),
            float(c.release_allowed),
            float(c.uncertainty_requires_stop),
            float(c.stop_completion_required),
            min(c.safe_margin, 40.0) / 40.0,
            min(c.max_safe_speed, 10.0) / 10.0,
        ],
        dtype=np.float32,
    )


def featurize(state: WorldState, variant: str) -> np.ndarray:
    base = base_observation(state)
    if variant == "A_STATE":
        return base
    if variant == "B_COC":
        return np.concatenate([base, coc_features(state)])
    if variant == "C_CONTRACT":
        return np.concatenate([base, coc_features(state), contract_features(state)])
    raise ValueError(f"unknown model variant: {variant}")


def clip_action(action: float) -> float:
    return float(np.clip(action, -MAX_BRAKE, MAX_ACCEL))


def expert_action(state: WorldState) -> float:
    if state.scenario.kind != "lead_brake":
        status = contract_status(state)
        target_v = min(CRUISE_SPEED, status.max_safe_speed) if status.hold_required else CRUISE_SPEED
        return clip_action((target_v - state.ego_v) / DT)

    gap = max(distance_measure(state), 0.1)
    closing = state.ego_v - state.lead_v
    desired_gap = lead_safe_gap(state)
    desired_v = min(CRUISE_SPEED, max(0.0, state.lead_v + 0.55 * (gap - desired_gap)))
    action = (desired_v - state.ego_v) / DT
    if closing > 0.0 and gap / closing < 3.5:
        action = min(action, -min(MAX_BRAKE, 1.2 * closing))
    return clip_action(action)


def _next_speed_position(x: float, v: float, action: float) -> tuple[float, float]:
    new_x = x + v * DT + 0.5 * action * DT * DT
    new_v = max(0.0, v + action * DT)
    return new_x, new_v


def lead_acceleration(state: WorldState) -> float:
    if state.t < state.scenario.lead_brake_time or state.lead_v <= 0.0:
        return 0.0
    return -state.scenario.lead_decel


def step(state: WorldState, action: float) -> WorldState:
    action = clip_action(action)
    ego_x, ego_v = _next_speed_position(state.ego_x, state.ego_v, action)
    lead_x, lead_v = state.lead_x, state.lead_v
    if state.scenario.kind == "lead_brake":
        lead_x, lead_v = _next_speed_position(state.lead_x, state.lead_v, lead_acceleration(state))

    stopped_steps = state.stopped_steps
    has_stopped = state.has_stopped
    if state.scenario.kind == "stop_intersection" and not has_stopped:
        near_line = -2.5 <= ego_x <= -0.2
        stopped_steps = stopped_steps + 1 if near_line and ego_v <= 0.2 else 0
        has_stopped = stopped_steps >= 2

    new_t = state.t + DT
    done = new_t >= DT * HORIZON_STEPS
    if state.scenario.kind != "lead_brake" and ego_x >= 8.0:
        done = True
    if state.scenario.kind == "lead_brake" and lead_x - ego_x <= 0.0:
        done = True
    return replace(
        state,
        t=new_t,
        ego_x=ego_x,
        ego_v=ego_v,
        lead_x=lead_x,
        lead_v=lead_v,
        stopped_steps=stopped_steps,
        has_stopped=has_stopped,
        done=done,
    )


def _candidate_actions(proposed: float) -> Iterable[float]:
    upper = clip_action(proposed)
    return np.linspace(-MAX_BRAKE, upper, 121)[::-1]


def apply_contract_shield(state: WorldState, proposed: float) -> tuple[float, bool]:
    proposed = clip_action(proposed)
    status = contract_status(state)
    if not status.hold_required:
        return proposed, False

    if state.scenario.kind != "lead_brake":
        for candidate in _candidate_actions(proposed):
            x_next, v_next = _next_speed_position(state.ego_x, state.ego_v, float(candidate))
            stopping_x = x_next + (v_next * v_next) / (2.0 * MAX_BRAKE)
            if stopping_x <= -STOP_MARGIN + 1e-6:
                chosen = float(candidate)
                return chosen, abs(chosen - proposed) > 1e-5
        return -MAX_BRAKE, proposed > -MAX_BRAKE + 1e-5

    lead_a = min(lead_acceleration(state), -2.0 if state.lead_v > 0.0 else 0.0)
    for candidate in _candidate_actions(proposed):
        ego_x, ego_v = _next_speed_position(state.ego_x, state.ego_v, float(candidate))
        lead_x, lead_v = _next_speed_position(state.lead_x, state.lead_v, lead_a)
        gap_next = lead_x - ego_x
        ego_stop = (ego_v * ego_v) / (2.0 * MAX_BRAKE)
        lead_stop = (lead_v * lead_v) / (2.0 * max(state.scenario.lead_decel, 2.0))
        if gap_next - MIN_LEAD_GAP + lead_stop >= ego_stop - 1e-6:
            chosen = float(candidate)
            return chosen, abs(chosen - proposed) > 1e-5
    return -MAX_BRAKE, proposed > -MAX_BRAKE + 1e-5


def evaluate_transition(before: WorldState, after: WorldState, metrics: EpisodeMetrics) -> None:
    status = contract_status(before)
    if before.scenario.kind != "lead_brake":
        crossed = before.ego_x < 0.0 <= after.ego_x
        if crossed and status.hold_required:
            metrics.forbidden_entry = True
        if crossed and before.scenario.kind == "stop_intersection" and not before.has_stopped:
            metrics.forbidden_entry = True
        in_conflict_zone = -0.5 <= after.ego_x <= 4.0
        if in_conflict_zone and (hazard_active(after) or not is_visible(after)):
            metrics.collision = True
        if status.release_allowed and after.ego_v < 0.5:
            metrics.released_stop_steps += 1
        return

    gap = after.lead_x - after.ego_x
    if gap <= 0.0:
        metrics.collision = True
    if gap < lead_safe_gap(after):
        metrics.safe_gap_violation = True


def rollout_policy(scenario: Scenario, policy, variant: str, shield: bool = False) -> EpisodeMetrics:
    state = initial_state(scenario)
    initial_x = state.ego_x
    actions: list[float] = []
    metrics = EpisodeMetrics()
    while not state.done:
        proposed = float(policy(featurize(state, variant)))
        action, intervened = apply_contract_shield(state, proposed) if shield else (clip_action(proposed), False)
        metrics.interventions += int(intervened)
        new_state = step(state, action)
        evaluate_transition(state, new_state, metrics)
        actions.append(action)
        state = new_state
    metrics.progress = state.ego_x - initial_x
    metrics.completed = (scenario.kind == "lead_brake" and not metrics.collision) or state.ego_x >= 8.0
    if len(actions) > 1:
        metrics.mean_abs_jerk = float(np.mean(np.abs(np.diff(actions))) / DT)
    return metrics


def rollout_expert(scenario: Scenario) -> EpisodeMetrics:
    state = initial_state(scenario)
    initial_x = state.ego_x
    actions: list[float] = []
    metrics = EpisodeMetrics()
    while not state.done:
        action = expert_action(state)
        new_state = step(state, action)
        evaluate_transition(state, new_state, metrics)
        actions.append(action)
        state = new_state
    metrics.progress = state.ego_x - initial_x
    metrics.completed = (scenario.kind == "lead_brake" and not metrics.collision) or state.ego_x >= 8.0
    if len(actions) > 1:
        metrics.mean_abs_jerk = float(np.mean(np.abs(np.diff(actions))) / DT)
    return metrics


def collect_expert_transitions(scenarios: Iterable[Scenario]) -> list[tuple[WorldState, float]]:
    records: list[tuple[WorldState, float]] = []
    for scenario in scenarios:
        state = initial_state(scenario)
        while not state.done:
            action = expert_action(state)
            records.append((state, action))
            state = step(state, action)
    return records
