#!/usr/bin/env python3
"""Check a sequence of CoC events against one continuous egomotion trace."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd


DEFAULT_ROOT = Path("data/baseline/coc_nusc")
DEFAULT_CLIP_ID = "scene-0001"
HISTORY_US = 2_000_000
FUTURE_US = 6_000_000


@dataclass(frozen=True)
class NormalizedDecision:
    longitudinal: str | None
    lateral: str | None
    hazards: tuple[str, ...]


def nearest_row(frame: pd.DataFrame, timestamp_us: int) -> pd.Series:
    index = (frame["timestamp"] - timestamp_us).abs().idxmin()
    return frame.loc[index]


def normalize_coc(text: str) -> NormalizedDecision:
    lowered = text.lower()

    longitudinal = None
    if lowered.startswith("decelerate") or lowered.startswith("slow down"):
        longitudinal = "DECELERATE"
    elif lowered.startswith("accelerate"):
        longitudinal = "ACCELERATE"
    elif lowered.startswith("resume"):
        longitudinal = "RESUME_SPEED"
    elif "adapt speed" in lowered or "adapting speed" in lowered:
        longitudinal = "ADAPT_SPEED"
    elif "maintain a safe distance" in lowered or "maintaining a safe distance" in lowered:
        longitudinal = "MAINTAIN_SAFE_DISTANCE"

    lateral = None
    if lowered.startswith("nudge left"):
        lateral = "NUDGE_LEFT"
    elif lowered.startswith("nudge right"):
        lateral = "NUDGE_RIGHT"

    hazards = []
    if "truck" in lowered:
        hazards.append("TRUCK")
    if "lead vehicle" in lowered:
        hazards.append("LEAD_VEHICLE")
    if "construction" in lowered:
        hazards.append("CONSTRUCTION_ZONE")
    if "worker" in lowered:
        hazards.append("WORKER")

    return NormalizedDecision(longitudinal, lateral, tuple(hazards))


def detect_sustained_deceleration(
    egomotion: pd.DataFrame,
    search_start_us: int,
    search_end_us: int,
    window_us: int,
    minimum_drop_mps: float,
    minimum_negative_fraction: float,
) -> int | None:
    candidates = egomotion[
        (egomotion["timestamp"] >= search_start_us)
        & (egomotion["timestamp"] <= search_end_us)
    ]
    for row in candidates.itertuples(index=False):
        start_us = int(row.timestamp)
        window = egomotion[
            (egomotion["timestamp"] >= start_us)
            & (egomotion["timestamp"] <= start_us + window_us)
        ]
        if len(window) < 2:
            continue
        speed_drop = float(window["speed_mps"].iloc[0] - window["speed_mps"].iloc[-1])
        derivatives = np.diff(window["speed_mps"]) / np.diff(
            window["timestamp"] / 1_000_000
        )
        negative_fraction = float(np.mean(derivatives < 0))
        if (
            speed_drop >= minimum_drop_mps
            and negative_fraction >= minimum_negative_fraction
        ):
            return start_us
    return None


def parse_deadlines(value: str) -> list[float]:
    deadlines = sorted({float(item.strip()) for item in value.split(",") if item.strip()})
    if not deadlines or any(deadline <= 0 for deadline in deadlines):
        raise argparse.ArgumentTypeError("deadlines must be positive comma-separated seconds")
    return deadlines


def select_obligation_anchor(trigger_times_us: list[int]) -> int:
    if not trigger_times_us:
        raise ValueError("at least one trigger is required")
    return min(trigger_times_us)


def analyze_deceleration_sensitivity(
    egomotion: pd.DataFrame,
    search_start_us: int,
    search_end_us: int,
    windows_s: list[float],
    minimum_drops_mps: list[float],
    negative_fractions: list[float],
) -> dict[str, object]:
    profiles = []
    for window_s in windows_s:
        for minimum_drop_mps in minimum_drops_mps:
            for negative_fraction in negative_fractions:
                onset_us = detect_sustained_deceleration(
                    egomotion,
                    search_start_us,
                    search_end_us,
                    int(window_s * 1_000_000),
                    minimum_drop_mps,
                    negative_fraction,
                )
                profiles.append(
                    {
                        "window_s": window_s,
                        "minimum_drop_mps": minimum_drop_mps,
                        "minimum_negative_fraction": negative_fraction,
                        "onset_us": onset_us,
                        "latency_s": (
                            None
                            if onset_us is None
                            else round((onset_us - search_start_us) / 1_000_000, 4)
                        ),
                    }
                )
    detected_latencies = [
        profile["latency_s"]
        for profile in profiles
        if profile["latency_s"] is not None
    ]
    return {
        "profile_count": len(profiles),
        "detected_profile_count": len(detected_latencies),
        "no_response_profile_count": len(profiles) - len(detected_latencies),
        "minimum_detected_latency_s": (
            min(detected_latencies) if detected_latencies else None
        ),
        "maximum_detected_latency_s": (
            max(detected_latencies) if detected_latencies else None
        ),
        "profiles": profiles,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--clip-id", default=DEFAULT_CLIP_ID)
    parser.add_argument("--deadlines-s", type=parse_deadlines, default=parse_deadlines("1,2,3"))
    parser.add_argument("--deceleration-window-s", type=float, default=0.5)
    parser.add_argument("--minimum-window-drop-mps", type=float, default=0.1)
    parser.add_argument("--minimum-negative-fraction", type=float, default=0.7)
    parser.add_argument(
        "--sensitivity-windows-s",
        type=parse_deadlines,
        default=parse_deadlines("0.25,0.5,1"),
    )
    parser.add_argument(
        "--sensitivity-drops-mps",
        type=parse_deadlines,
        default=parse_deadlines("0.05,0.1,0.2,0.5"),
    )
    parser.add_argument(
        "--sensitivity-negative-fractions",
        type=parse_deadlines,
        default=parse_deadlines("0.5,0.7,0.9"),
    )
    args = parser.parse_args()

    reasoning_path = args.root / "reasoning/ood_reasoning.parquet"
    egomotion_path = args.root / f"labels/egomotion/{args.clip_id}.egomotion.parquet"
    timestamps_path = (
        args.root / f"camera/{args.clip_id}.camera_front_wide_120fov.timestamps.parquet"
    )

    reasoning = pd.read_parquet(reasoning_path)
    if args.clip_id not in reasoning.index:
        raise SystemExit(f"clip not found in reasoning parquet: {args.clip_id}")

    raw_events = json.loads(reasoning.loc[args.clip_id, "events"])
    raw_events.sort(key=lambda item: int(item["event_start_timestamp"]))
    if not raw_events:
        raise SystemExit("episode has no CoC events")

    egomotion = pd.read_parquet(egomotion_path).sort_values("timestamp").copy()
    timestamps = pd.read_parquet(timestamps_path).sort_values("timestamp")
    egomotion["speed_mps"] = np.hypot(egomotion["vx"], egomotion["vy"])

    events = []
    trusted_longitudinal = None
    trusted_lateral = None
    ignored_low_quality_overwrites = 0
    contradictory_transitions = []
    for index, event in enumerate(raw_events):
        t0_us = int(event["event_start_timestamp"])
        decision = normalize_coc(event["cot"])
        quality_pass = bool(event.get("quality_pass", False))

        if quality_pass:
            if {
                trusted_longitudinal,
                decision.longitudinal,
            } == {"DECELERATE", "ACCELERATE"}:
                contradictory_transitions.append(t0_us)
            trusted_longitudinal = decision.longitudinal or trusted_longitudinal
            trusted_lateral = decision.lateral or trusted_lateral
        elif decision.longitudinal or decision.lateral:
            ignored_low_quality_overwrites += 1

        interval_end_us = (
            int(raw_events[index + 1]["event_start_timestamp"])
            if index + 1 < len(raw_events)
            else t0_us + FUTURE_US
        )
        events.append(
            {
                "t0_us": t0_us,
                "valid_until_us": interval_end_us,
                "coc": event["cot"],
                "quality_pass": quality_pass,
                "longitudinal": decision.longitudinal,
                "lateral": decision.lateral,
                "hazards": list(decision.hazards),
                "speed_at_t0_mps": round(
                    float(nearest_row(egomotion, t0_us)["speed_mps"]), 4
                ),
            }
        )

    deceleration_events = [
        event
        for event in events
        if event["quality_pass"]
        and event["longitudinal"] == "DECELERATE"
        and "TRUCK" in event["hazards"]
    ]
    if not deceleration_events:
        raise SystemExit("no trusted truck-related DECELERATE event found")

    trigger_times_us = [int(event["t0_us"]) for event in deceleration_events]
    obligation_start_us = select_obligation_anchor(trigger_times_us)
    repeated_trigger_times = [time_us for time_us in trigger_times_us if time_us != obligation_start_us]
    response_onset_us = detect_sustained_deceleration(
        egomotion,
        obligation_start_us,
        obligation_start_us + FUTURE_US,
        int(args.deceleration_window_s * 1_000_000),
        args.minimum_window_drop_mps,
        args.minimum_negative_fraction,
    )
    latency_s = (
        None
        if response_onset_us is None
        else (response_onset_us - obligation_start_us) / 1_000_000
    )
    deadline_results = {
        f"{deadline:g}s": (
            "FAIL"
            if latency_s is None or latency_s > deadline
            else "PASS"
        )
        for deadline in args.deadlines_s
    }
    sensitivity = analyze_deceleration_sensitivity(
        egomotion,
        obligation_start_us,
        obligation_start_us + FUTURE_US,
        args.sensitivity_windows_s,
        args.sensitivity_drops_mps,
        args.sensitivity_negative_fractions,
    )
    clock_preserved = bool(
        obligation_start_us == min(trigger_times_us)
        and all(time_us > obligation_start_us for time_us in repeated_trigger_times)
    )

    episode_start_us = obligation_start_us - HISTORY_US
    episode_end_us = int(events[-1]["t0_us"]) + FUTURE_US
    timestamps_monotonic = all(
        events[index]["t0_us"] < events[index + 1]["t0_us"]
        for index in range(len(events) - 1)
    )
    coverage_pass = bool(
        egomotion["timestamp"].min() <= episode_start_us
        and egomotion["timestamp"].max() >= episode_end_us
        and timestamps["timestamp"].min() <= episode_start_us
        and timestamps["timestamp"].max() >= episode_end_us
    )

    result = {
        "checker_type": "STATEFUL_EPISODE_TRACE_CHECKER",
        "observed_control_proxy": "EGOMOTION_SPEED_NOT_RAW_ACTUATOR_COMMAND",
        "source_class": "PUBLIC_COMPATIBILITY_DATASET_NOT_OFFICIAL_NVIDIA_COC",
        "clip_id": args.clip_id,
        "episode": {
            "event_count": len(events),
            "history_start_us": episode_start_us,
            "last_event_t0_us": int(events[-1]["t0_us"]),
            "future_end_us": episode_end_us,
            "events": events,
        },
        "obligations": {
            "SAFE_DISTANCE_TRUCK": {
                "triggered_at_us": obligation_start_us,
                "repeated_without_clock_reset_at_us": repeated_trigger_times,
                "response_definition": {
                    "type": "SUSTAINED_SPEED_DECREASE",
                    "window_s": args.deceleration_window_s,
                    "minimum_drop_mps": args.minimum_window_drop_mps,
                    "minimum_negative_derivative_fraction": args.minimum_negative_fraction,
                },
                "response_onset_us": response_onset_us,
                "response_latency_s": None if latency_s is None else round(latency_s, 4),
                "response_measurement_quality": "HEURISTIC_SPEED_TRACE_NOT_ACTIVE_BRAKE_DETECTION",
                "threshold_sensitivity": sensitivity,
                "deadline_sensitivity": deadline_results,
            }
        },
        "verdicts": {
            "event_timestamps_monotonic": "PASS" if timestamps_monotonic else "FAIL",
            "episode_trace_coverage": "PASS" if coverage_pass else "FAIL",
            "obligation_clock_preservation": "PASS" if clock_preserved else "FAIL",
            "trusted_control_transition_consistency": (
                "PASS" if not contradictory_transitions else "FAIL"
            ),
            "low_quality_event_policy": (
                f"PASS_IGNORED_{ignored_low_quality_overwrites}_OVERWRITES"
            ),
            "bounded_deceleration_response": deadline_results,
            "longitudinal_episode_conformance": "CONTRACT_DEPENDENT",
            "lateral_episode_conformance": "UNKNOWN_MISSING_LANE_AND_OBSTACLE_REFERENCE",
            "safe_distance_property": "UNKNOWN_MISSING_OBSTACLE_DISTANCE",
            "symbolic_model_checking": "NOT_RUN",
        },
        "interpretation": (
            "Repeated CoC updates do not restart the truck-related response clock. "
            "The observed response latency is checked against explicit candidate deadlines; "
            "a deadline must come from a safety or service contract before a final verdict."
        ),
    }
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
