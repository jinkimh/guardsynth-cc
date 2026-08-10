#!/usr/bin/env python3
"""Search for longitudinal collision witnesses on a finite parameter grid."""

from __future__ import annotations

import argparse
import itertools
import json
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from check_episode import (
    DEFAULT_CLIP_ID,
    DEFAULT_ROOT,
    FUTURE_US,
    detect_sustained_deceleration,
    nearest_row,
    normalize_coc,
)


@dataclass(frozen=True)
class Scenario:
    initial_gap_m: float
    ego_speed_mps: float
    lead_speed_mps: float
    ego_max_decel_mps2: float
    lead_decel_mps2: float
    response_delay_s: float
    brake_build_up_s: float


@dataclass(frozen=True)
class SimulationResult:
    collision: bool
    collision_time_s: float | None
    minimum_gap_m: float
    final_gap_m: float
    final_ego_speed_mps: float
    final_lead_speed_mps: float


def parse_float_grid(value: str) -> list[float]:
    values = sorted({float(item.strip()) for item in value.split(",") if item.strip()})
    if not values:
        raise argparse.ArgumentTypeError("expected a comma-separated numeric grid")
    return values


def motion_step(speed_mps: float, acceleration_mps2: float, dt_s: float) -> tuple[float, float]:
    """Return distance and non-negative final speed for constant acceleration."""
    if acceleration_mps2 < 0 and speed_mps + acceleration_mps2 * dt_s < 0:
        stop_time_s = -speed_mps / acceleration_mps2
        distance_m = speed_mps * stop_time_s + 0.5 * acceleration_mps2 * stop_time_s**2
        return distance_m, 0.0
    distance_m = speed_mps * dt_s + 0.5 * acceleration_mps2 * dt_s**2
    return distance_m, max(0.0, speed_mps + acceleration_mps2 * dt_s)


def simulate_scenario(
    scenario: Scenario,
    horizon_s: float,
    dt_s: float,
    minimum_clearance_m: float = 0.0,
) -> SimulationResult:
    gap_m = scenario.initial_gap_m
    ego_speed_mps = scenario.ego_speed_mps
    lead_speed_mps = scenario.lead_speed_mps
    minimum_gap_m = gap_m
    collision_time_s = None

    steps = int(np.ceil(horizon_s / dt_s))
    for step in range(steps):
        time_s = step * dt_s
        if time_s < scenario.response_delay_s:
            ego_acceleration_mps2 = 0.0
        elif scenario.brake_build_up_s == 0:
            ego_acceleration_mps2 = -scenario.ego_max_decel_mps2
        else:
            build_up_fraction = min(
                1.0,
                (time_s - scenario.response_delay_s + dt_s) / scenario.brake_build_up_s,
            )
            ego_acceleration_mps2 = -scenario.ego_max_decel_mps2 * build_up_fraction

        lead_acceleration_mps2 = (
            -scenario.lead_decel_mps2 if lead_speed_mps > 0 else 0.0
        )
        ego_distance_m, ego_speed_mps = motion_step(
            ego_speed_mps, ego_acceleration_mps2, dt_s
        )
        lead_distance_m, lead_speed_mps = motion_step(
            lead_speed_mps, lead_acceleration_mps2, dt_s
        )
        gap_m += lead_distance_m - ego_distance_m
        minimum_gap_m = min(minimum_gap_m, gap_m)
        if gap_m <= minimum_clearance_m:
            collision_time_s = min(horizon_s, (step + 1) * dt_s)
            break

    return SimulationResult(
        collision=collision_time_s is not None,
        collision_time_s=collision_time_s,
        minimum_gap_m=minimum_gap_m,
        final_gap_m=gap_m,
        final_ego_speed_mps=ego_speed_mps,
        final_lead_speed_mps=lead_speed_mps,
    )


def load_scene_seed(root: Path, clip_id: str) -> tuple[int, float, float | None]:
    reasoning = pd.read_parquet(root / "reasoning/ood_reasoning.parquet")
    events = json.loads(reasoning.loc[clip_id, "events"])
    trusted = [
        event
        for event in events
        if bool(event.get("quality_pass", False))
        and normalize_coc(event["cot"]).longitudinal == "DECELERATE"
        and "TRUCK" in normalize_coc(event["cot"]).hazards
    ]
    if not trusted:
        raise ValueError("no trusted truck-related DECELERATE event found")
    trigger_us = min(int(event["event_start_timestamp"]) for event in trusted)
    egomotion = pd.read_parquet(
        root / f"labels/egomotion/{clip_id}.egomotion.parquet"
    ).copy()
    egomotion["speed_mps"] = np.hypot(egomotion["vx"], egomotion["vy"])
    ego_speed_mps = float(nearest_row(egomotion, trigger_us)["speed_mps"])
    onset_us = detect_sustained_deceleration(
        egomotion, trigger_us, trigger_us + FUTURE_US, 500_000, 0.1, 0.7
    )
    heuristic_delay_s = (
        None if onset_us is None else (onset_us - trigger_us) / 1_000_000
    )
    return trigger_us, ego_speed_mps, heuristic_delay_s


def check_grid(
    ego_speed_mps: float,
    gaps_m: list[float],
    lead_speeds_mps: list[float],
    ego_decels_mps2: list[float],
    lead_decels_mps2: list[float],
    response_delays_s: list[float],
    brake_build_ups_s: list[float],
    horizon_s: float,
    dt_s: float,
    minimum_clearance_m: float,
) -> dict[str, object]:
    delay_results = {}
    for response_delay_s in response_delays_s:
        outcomes = []
        for values in itertools.product(
            gaps_m,
            lead_speeds_mps,
            ego_decels_mps2,
            lead_decels_mps2,
            brake_build_ups_s,
        ):
            scenario = Scenario(
                initial_gap_m=values[0],
                ego_speed_mps=ego_speed_mps,
                lead_speed_mps=values[1],
                ego_max_decel_mps2=values[2],
                lead_decel_mps2=values[3],
                response_delay_s=response_delay_s,
                brake_build_up_s=values[4],
            )
            result = simulate_scenario(
                scenario, horizon_s, dt_s, minimum_clearance_m
            )
            outcomes.append((scenario, result))

        robust_safe_gaps = []
        for gap_m in gaps_m:
            same_gap = [result for scenario, result in outcomes if scenario.initial_gap_m == gap_m]
            if same_gap and all(not result.collision for result in same_gap):
                robust_safe_gaps.append(gap_m)

        counterexamples = [item for item in outcomes if item[1].collision]
        earliest = min(
            counterexamples,
            key=lambda item: (item[1].collision_time_s or float("inf"), item[0].initial_gap_m),
            default=None,
        )
        delay_results[f"{response_delay_s:g}s"] = {
            "scenarios_explored": len(outcomes),
            "collision_witness_found": bool(counterexamples),
            "collision_scenarios": len(counterexamples),
            "minimum_tested_gap_without_witness_m": (
                min(robust_safe_gaps) if robust_safe_gaps else None
            ),
            "counterexample": (
                None
                if earliest is None
                else {
                    "scenario": asdict(earliest[0]),
                    "result": asdict(earliest[1]),
                }
            ),
        }
    return delay_results


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--clip-id", default=DEFAULT_CLIP_ID)
    parser.add_argument("--gaps-m", type=parse_float_grid, default=parse_float_grid("5,10,15,20,25,30"))
    parser.add_argument("--lead-speeds-mps", type=parse_float_grid, default=parse_float_grid("0"))
    parser.add_argument("--ego-decels-mps2", type=parse_float_grid, default=parse_float_grid("3,5,7"))
    parser.add_argument("--lead-decels-mps2", type=parse_float_grid, default=parse_float_grid("0"))
    parser.add_argument("--response-delays-s", type=parse_float_grid)
    parser.add_argument("--brake-build-ups-s", type=parse_float_grid, default=parse_float_grid("0.2,0.5"))
    parser.add_argument("--horizon-s", type=float, default=5.0)
    parser.add_argument("--dt-s", type=float, default=0.1)
    parser.add_argument("--minimum-clearance-m", type=float, default=0.0)
    args = parser.parse_args()

    trigger_us, ego_speed_mps, heuristic_delay_s = load_scene_seed(args.root, args.clip_id)
    response_delays_s = args.response_delays_s or sorted(
        {0.5, 1.0, 2.0, *([] if heuristic_delay_s is None else [heuristic_delay_s])}
    )
    results = check_grid(
        ego_speed_mps,
        args.gaps_m,
        args.lead_speeds_mps,
        args.ego_decels_mps2,
        args.lead_decels_mps2,
        response_delays_s,
        args.brake_build_ups_s,
        args.horizon_s,
        args.dt_s,
        args.minimum_clearance_m,
    )
    output = {
        "checker_type": "PARAMETER_GRID_FALSIFICATION",
        "certificate_kind": "DETERMINISTIC_SCENARIO_SWEEP",
        "soundness_scope": "NOT_A_CONTINUOUS_OR_REAL_VEHICLE_SAFETY_PROOF",
        "source_class": "SCENE_EGO_SPEED_WITH_SYNTHETIC_UNCALIBRATED_PHYSICS_GRID",
        "clip_id": args.clip_id,
        "seed": {
            "trigger_us": trigger_us,
            "ego_speed_mps": ego_speed_mps,
            "heuristic_response_delay_s": heuristic_delay_s,
            "response_measurement_quality": "SPEED_TRACE_HEURISTIC_NOT_ACTIVE_BRAKE_DETECTION",
        },
        "model": {
            "horizon_s": args.horizon_s,
            "dt_s": args.dt_s,
            "minimum_clearance_m": args.minimum_clearance_m,
            "gap_semantics": "SYNTHETIC_BUMPER_TO_BUMPER_CLEARANCE",
            "initial_gaps_m": args.gaps_m,
            "lead_speeds_mps": args.lead_speeds_mps,
            "ego_max_decels_mps2": args.ego_decels_mps2,
            "lead_decels_mps2": args.lead_decels_mps2,
            "brake_build_ups_s": args.brake_build_ups_s,
            "response_delays_s": response_delays_s,
            "time_discretization": (
                "Controls change only on dt boundaries; a non-aligned response delay is "
                "activated at the first boundary at or after that delay."
            ),
        },
        "results_by_response_delay": results,
        "interpretation": (
            "Collision witnesses are valid only for an enumerated deterministic synthetic scenario. "
            "Absence of a witness covers only this finite grid and bounded horizon. Actual scene "
            "safety remains UNKNOWN until obstacle state and vehicle envelopes are calibrated."
        ),
    }
    print(json.dumps(output, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
