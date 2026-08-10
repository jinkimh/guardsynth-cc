#!/usr/bin/env python3
"""Evaluate traceable CoC episodes with weak longitudinal response contracts."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path("data/baseline/coc_nusc")
DEFAULT_SCENES = (
    "scene-0001",
    "scene-0011",
    "scene-0027",
    "scene-0028",
    "scene-0055",
    "scene-0129",
    "scene-0133",
    "scene-0138",
    "scene-0151",
    "scene-0178",
    "scene-0180",
    "scene-0181",
    "scene-0183",
)
RESPONSE_DEADLINE_US = 3_000_000
WINDOW_US = 500_000
MINIMUM_DELTA_MPS = 0.1
MINIMUM_DIRECTION_FRACTION = 0.7
STOPPED_SPEED_THRESHOLD_MPS = 0.5
CAMERA_SOURCE_REVISION = (
    "YSHRobotics/CoC-Nusc@994bdd94fcf696b6289e2b2bac7fcbded47eed0a"
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def extract_intents(text: str) -> list[str]:
    patterns = {
        "STOP": r"(?:^stop\b|\bto stop\b|\bstop for\b|\bstop behind\b)",
        "DECELERATE": r"\bdecelerat\w*\b|\bslow down\b",
        "ACCELERATE": r"\baccelerat\w*\b|\bresume speed\b",
        "YIELD": r"\byield\w*\b",
        "ADAPT_SPEED": r"\badapt(?:ing)? speed\b",
        "NUDGE_LEFT": r"\bnudge left\b",
        "NUDGE_RIGHT": r"\bnudge right\b",
    }
    found = []
    lowered = text.lower()
    for intent, pattern in patterns.items():
        match = re.search(pattern, lowered)
        if match:
            found.append((match.start(), intent))
    return [intent for _, intent in sorted(found)]


def expected_longitudinal_direction(intents: list[str]) -> str | None:
    negative = bool({"STOP", "DECELERATE", "YIELD"}.intersection(intents))
    positive = "ACCELERATE" in intents
    if negative == positive:
        return None
    return "DECREASE" if negative else "INCREASE"


def nearest_speed(frame: pd.DataFrame, timestamp_us: int) -> float:
    index = (frame["timestamp"] - timestamp_us).abs().idxmin()
    return float(frame.loc[index, "speed_mps"])


def detect_directional_response(
    frame: pd.DataFrame,
    start_us: int,
    end_us: int,
    direction: str,
    window_us: int = WINDOW_US,
    minimum_delta_mps: float = MINIMUM_DELTA_MPS,
    minimum_direction_fraction: float = MINIMUM_DIRECTION_FRACTION,
) -> int | None:
    candidates = frame[
        (frame["timestamp"] >= start_us) & (frame["timestamp"] <= end_us)
    ]
    sign = -1 if direction == "DECREASE" else 1
    for row in candidates.itertuples(index=False):
        onset_us = int(row.timestamp)
        window = frame[
            (frame["timestamp"] >= onset_us)
            & (frame["timestamp"] <= onset_us + window_us)
        ]
        if len(window) < 2:
            continue
        signed_delta = sign * float(
            window["speed_mps"].iloc[-1] - window["speed_mps"].iloc[0]
        )
        signed_steps = sign * np.diff(window["speed_mps"].to_numpy())
        fraction = float(np.mean(signed_steps > 0))
        if signed_delta >= minimum_delta_mps and fraction >= minimum_direction_fraction:
            return onset_us
    return None


def response_sensitivity(
    frame: pd.DataFrame, timestamp_us: int, direction: str
) -> dict:
    profiles = []
    for deadline_s in (1, 2, 3, 4, 5):
        for window_s in (0.25, 0.5, 1.0):
            for minimum_delta_mps in (0.05, 0.1, 0.2):
                for minimum_fraction in (0.5, 0.7, 0.9):
                    onset = detect_directional_response(
                        frame,
                        timestamp_us,
                        timestamp_us + deadline_s * 1_000_000,
                        direction,
                        int(window_s * 1_000_000),
                        minimum_delta_mps,
                        minimum_fraction,
                    )
                    profiles.append(
                        {
                            "deadline_s": deadline_s,
                            "window_s": window_s,
                            "minimum_delta_mps": minimum_delta_mps,
                            "minimum_direction_fraction": minimum_fraction,
                            "response_latency_s": (
                                None
                                if onset is None
                                else round((onset - timestamp_us) / 1_000_000, 4)
                            ),
                        }
                    )
    by_deadline = {}
    for deadline_s in (1, 2, 3, 4, 5):
        selected = [item for item in profiles if item["deadline_s"] == deadline_s]
        detected = [
            item["response_latency_s"]
            for item in selected
            if item["response_latency_s"] is not None
        ]
        by_deadline[f"{deadline_s}s"] = {
            "profile_count": len(selected),
            "detected_profile_count": len(detected),
            "minimum_latency_s": min(detected) if detected else None,
            "maximum_latency_s": max(detected) if detected else None,
        }
    return {"by_deadline": by_deadline, "profiles": profiles}


def three_second_robustness(
    frame: pd.DataFrame, timestamp_us: int, direction: str
) -> dict:
    latencies = []
    for window_s in (0.25, 0.5, 1.0):
        for minimum_delta_mps in (0.05, 0.1, 0.2):
            for minimum_fraction in (0.5, 0.7, 0.9):
                onset = detect_directional_response(
                    frame,
                    timestamp_us,
                    timestamp_us + RESPONSE_DEADLINE_US,
                    direction,
                    int(window_s * 1_000_000),
                    minimum_delta_mps,
                    minimum_fraction,
                )
                if onset is not None:
                    latencies.append(round((onset - timestamp_us) / 1_000_000, 4))
    return {
        "profile_count": 27,
        "detected_profile_count": len(latencies),
        "detection_fraction": round(len(latencies) / 27, 4),
        "minimum_latency_s": min(latencies) if latencies else None,
        "maximum_latency_s": max(latencies) if latencies else None,
    }


def analyze_scene(
    clip_id: str, reasoning: pd.DataFrame, root: Path, reasoning_hash: str
) -> dict:
    ego_path = root / f"labels/egomotion/{clip_id}.egomotion.parquet"
    ego = pd.read_parquet(ego_path).sort_values("timestamp").copy()
    ego["speed_mps"] = np.hypot(ego["vx"], ego["vy"])
    raw_events = json.loads(reasoning.at[clip_id, "events"])
    indexed_events = sorted(
        enumerate(raw_events),
        key=lambda item: int(item[1]["event_start_timestamp"]),
    )
    events = []
    for source_index, event in indexed_events:
        timestamp_us = int(event["event_start_timestamp"])
        intents = extract_intents(event["cot"])
        direction = expected_longitudinal_direction(intents)
        quality_pass = bool(event.get("quality_pass", False))
        speed_at_event = nearest_speed(ego, timestamp_us)
        response_us = None
        verdict = "NOT_APPLICABLE"
        exclusion = None
        if not quality_pass:
            verdict = "EXCLUDED_LOW_QUALITY"
            exclusion = "quality_pass=false"
        elif direction is None:
            verdict = "EXCLUDED_AMBIGUOUS_OR_NON_DIRECTIONAL"
            exclusion = "compound or non-directional CoC"
        elif (
            direction == "DECREASE"
            and {"STOP", "YIELD"}.intersection(intents)
            and speed_at_event <= STOPPED_SPEED_THRESHOLD_MPS
        ):
            response_us = timestamp_us
            verdict = "PASS_ALREADY_SATISFIED"
        else:
            response_us = detect_directional_response(
                ego,
                timestamp_us,
                timestamp_us + RESPONSE_DEADLINE_US,
                direction,
            )
            verdict = "PASS" if response_us is not None else "FAIL"
        record = {
                "event_id": f"{clip_id}@{timestamp_us}",
                "source_json_pointer": f"/{clip_id}/events/{source_index}",
                "timestamp_us": timestamp_us,
                "quality_pass": quality_pass,
                "coc": event["cot"],
                "intents": intents,
                "expected_direction": direction,
                "speed_at_event_mps": round(speed_at_event, 4),
                "response_onset_us": response_us,
                "response_latency_s": (
                    None
                    if response_us is None
                    else round((response_us - timestamp_us) / 1_000_000, 4)
                ),
                "weak_kinematic_contract": verdict,
                "exclusion_reason": exclusion,
                "provenance_class": "OBSERVED",
            }
        if verdict == "FAIL":
            record["failure_sensitivity"] = response_sensitivity(
                ego, timestamp_us, direction
            )
            record["review_priority"] = "CAMERA_AND_RAW_ACTUATOR_CONFIRMATION_REQUIRED"
        if verdict in {"PASS", "FAIL"}:
            record["three_second_robustness"] = three_second_robustness(
                ego, timestamp_us, direction
            )
            if (
                verdict == "PASS"
                and record["three_second_robustness"]["detected_profile_count"] < 27
            ):
                record["review_priority"] = "THRESHOLD_SENSITIVE_CAMERA_REVIEW"
        events.append(record)
    evaluable = [
        event
        for event in events
        if event["weak_kinematic_contract"]
        in {"PASS", "PASS_ALREADY_SATISFIED", "FAIL"}
    ]
    camera_path = root / f"camera/{clip_id}.camera_front_wide_120fov.mp4"
    camera_timestamps_path = (
        root / f"camera/{clip_id}.camera_front_wide_120fov.timestamps.parquet"
    )
    provenance = {
        "reasoning_artifact": str(root / "reasoning/ood_reasoning.parquet"),
        "reasoning_sha256": reasoning_hash,
        "egomotion_artifact": str(ego_path),
        "egomotion_sha256": sha256_file(ego_path),
        "camera_available": camera_path.exists() and camera_timestamps_path.exists(),
    }
    if provenance["camera_available"]:
        provenance.update(
            {
                "camera_artifact": str(camera_path),
                "camera_sha256": sha256_file(camera_path),
                "camera_timestamps_artifact": str(camera_timestamps_path),
                "camera_timestamps_sha256": sha256_file(camera_timestamps_path),
                "camera_source_revision": CAMERA_SOURCE_REVISION,
            }
        )
    return {
        "clip_id": clip_id,
        "event_count": len(events),
        "trusted_event_count": sum(event["quality_pass"] for event in events),
        "timestamps_strictly_increasing": all(
            events[index]["timestamp_us"] < events[index + 1]["timestamp_us"]
            for index in range(len(events) - 1)
        ),
        "evaluable_contract_count": len(evaluable),
        "contract_pass_count": sum(
            event["weak_kinematic_contract"] in {"PASS", "PASS_ALREADY_SATISFIED"}
            for event in evaluable
        ),
        "contract_fail_count": sum(
            event["weak_kinematic_contract"] == "FAIL" for event in evaluable
        ),
        "provenance": provenance,
        "events": events,
    }


def analyze_cohort(root: Path = ROOT, scenes: tuple[str, ...] = DEFAULT_SCENES) -> dict:
    reasoning_path = root / "reasoning/ood_reasoning.parquet"
    reasoning = pd.read_parquet(reasoning_path)
    reasoning_hash = sha256_file(reasoning_path)
    episodes = [analyze_scene(scene, reasoning, root, reasoning_hash) for scene in scenes]
    review_events = []
    for episode in episodes:
        for event in episode["events"]:
            if "review_priority" not in event:
                continue
            robustness = event["three_second_robustness"]
            review_events.append(
                {
                    "clip_id": episode["clip_id"],
                    "event_id": event["event_id"],
                    "timestamp_us": event["timestamp_us"],
                    "priority": event["review_priority"],
                    "default_verdict": event["weak_kinematic_contract"],
                    "default_latency_s": event["response_latency_s"],
                    "detected_profiles": robustness["detected_profile_count"],
                    "profile_count": robustness["profile_count"],
                    "coc": event["coc"],
                }
            )
    review_events.sort(
        key=lambda item: (
            0 if item["default_verdict"] == "FAIL" else 1,
            item["detected_profiles"],
            -(item["default_latency_s"] or 0),
            item["event_id"],
        )
    )
    return {
        "checker_type": "MULTI_SCENE_TRACEABLE_WEAK_KINEMATIC_COHORT",
        "scenes_are_independent_episodes": True,
        "scene_concatenation_claim": "FORBIDDEN",
        "contract": {
            "deadline_s": RESPONSE_DEADLINE_US / 1_000_000,
            "window_s": WINDOW_US / 1_000_000,
            "minimum_speed_delta_mps": MINIMUM_DELTA_MPS,
            "minimum_direction_fraction": MINIMUM_DIRECTION_FRACTION,
            "stopped_speed_threshold_mps": STOPPED_SPEED_THRESHOLD_MPS,
            "response_semantics": "EGOMOTION_SPEED_HEURISTIC_NOT_RAW_ACTUATOR",
        },
        "cohort": {
            "scene_count": len(episodes),
            "event_count": sum(item["event_count"] for item in episodes),
            "trusted_event_count": sum(item["trusted_event_count"] for item in episodes),
            "evaluable_contract_count": sum(item["evaluable_contract_count"] for item in episodes),
            "contract_pass_count": sum(item["contract_pass_count"] for item in episodes),
            "contract_fail_count": sum(item["contract_fail_count"] for item in episodes),
            "camera_available_scene_count": sum(
                item["provenance"]["camera_available"] for item in episodes
            ),
        },
        "claim_limit": (
            "A FAIL is a weak trace inconsistency candidate, not proof of unsafe control. "
            "CoC labels are VLM-generated and response is inferred from ego speed."
        ),
        "video_review_queue": review_events,
        "episodes": episodes,
    }


def scenes_for_chunk(root: Path, chunk: int) -> tuple[str, ...]:
    index = pd.read_parquet(root / "clip_index.parquet")
    reasoning = pd.read_parquet(root / "reasoning/ood_reasoning.parquet")
    return tuple(
        sorted(
            clip_id
            for clip_id in set(index.index).intersection(reasoning.index)
            if int(index.at[clip_id, "chunk"]) == chunk
        )
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--scenes", nargs="*")
    parser.add_argument("--chunk", type=int)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    scenes = (
        scenes_for_chunk(args.root, args.chunk)
        if args.chunk is not None
        else tuple(args.scenes) if args.scenes else DEFAULT_SCENES
    )
    result = analyze_cohort(args.root, scenes)
    rendered = json.dumps(result, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")


if __name__ == "__main__":
    main()
