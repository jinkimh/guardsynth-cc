#!/usr/bin/env python3
"""Run the internal candidate-conformance check on ten licensed episodes."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

import pandas as pd

from analyze_nvidia_official_episode import (
    DEADLINE_US,
    ROOT,
    add_motion_signals,
    detect_response,
    event_contract,
    load_egomotion,
    nearest_value,
    sha256_file,
)


DEFAULT_CLIPS = (
    "caf6ea10-fc2b-47d1-814c-67c73b6cea9f",
    "b868def5-dbe3-433b-be90-651bf5347c90",
    "13f0af4c-2565-4a4d-b765-7f397f1d1684",
    "61d3622b-c307-4b02-a85d-697f9c82c52b",
    "cd9f6406-f776-4d21-8cc0-ac9b9bd2ddf9",
    "d50948f9-0017-4847-a280-1bed65d706b0",
    "3b19a8c2-46fb-4fc6-b031-b3270998040d",
    "25c50d83-f845-427a-ab32-b6b599161553",
    "5aebbdbb-3249-4abb-b51f-fb433f6f5f87",
    "dc23f1e7-9b8b-4e44-a986-606122aaeb92",
)


def is_compound(text: str) -> bool:
    lowered = text.lower()
    longitudinal_terms = sum(
        term in lowered
        for term in (
            "decelerat",
            "slow down",
            "stop",
            "yield",
            "accelerat",
            "resume speed",
        )
    )
    return " then " in lowered and longitudinal_terms >= 2


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--clip-id", action="append", dest="clip_ids")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    clip_ids = tuple(args.clip_ids or DEFAULT_CLIPS)

    reasoning_path = args.root / "reasoning/ood_reasoning.parquet"
    index_path = args.root / "clip_index.parquet"
    feature_path = args.root / "metadata/feature_presence.parquet"
    reasoning = pd.read_parquet(reasoning_path)
    clip_index = pd.read_parquet(index_path)
    feature_presence = pd.read_parquet(feature_path)

    episodes = []
    verdicts: Counter[str] = Counter()
    clusters: Counter[str] = Counter()
    for clip_id in clip_ids:
        if clip_id not in reasoning.index or clip_id not in clip_index.index:
            raise SystemExit(f"untraceable clip: {clip_id}")
        row = reasoning.loc[clip_id]
        if row["split"] != "val":
            raise SystemExit(f"cohort must remain validation-only: {clip_id}")
        raw_events = json.loads(row["events"])
        if len(raw_events) < 2:
            raise SystemExit(f"cohort clip is not a multi-event episode: {clip_id}")
        egomotion, archive = load_egomotion(clip_id, args.root)
        egomotion = add_motion_signals(egomotion)
        events = []
        for source_index, event in enumerate(raw_events):
            text = event["coc"]
            base = {
                "source_index": source_index,
                "source_json_pointer": f"/{clip_id}/events/{source_index}",
                "timestamp_us": int(event["event_start_timestamp"]),
                "event_start_frame": int(event["event_start_frame"]),
                "coc": text,
            }
            if is_compound(text):
                base.update({"intent": "COMPOUND", "verdict": "EXCLUDED_COMPOUND"})
                verdicts["EXCLUDED_COMPOUND"] += 1
                events.append(base)
                continue
            try:
                signal, sign, threshold, intent = event_contract(text)
            except ValueError:
                base.update({"intent": "UNSUPPORTED", "verdict": "EXCLUDED_UNSUPPORTED"})
                verdicts["EXCLUDED_UNSUPPORTED"] += 1
                events.append(base)
                continue
            timestamp_us = int(event["event_start_timestamp"])
            signal_at_event = nearest_value(egomotion, timestamp_us, signal)
            if text.lower().startswith(("stop", "yield")) and signal_at_event <= 0.5:
                response = {
                    "verdict": "PASS_ALREADY_SATISFIED",
                    "response_onset_us": timestamp_us,
                    "response_latency_s": 0.0,
                }
            else:
                response = detect_response(egomotion, timestamp_us, signal, sign, threshold)
            verdicts[response["verdict"]] += 1
            base.update(
                {
                    "intent": intent,
                    "signal": signal,
                    "signal_at_event": round(signal_at_event, 6),
                    "candidate_deadline_s": DEADLINE_US / 1e6,
                    "verdict": response["verdict"],
                    "response": response,
                }
            )
            events.append(base)
        cluster = str(row["event_cluster"])
        clusters[cluster] += 1
        episodes.append(
            {
                "clip_id": clip_id,
                "split": "val",
                "event_cluster": cluster,
                "chunk": int(clip_index.at[clip_id, "chunk"]),
                "feature_presence": {
                    name: bool(feature_presence.at[clip_id, name])
                    for name in ("egomotion", "obstacle.offline", "camera_front_wide_120fov")
                },
                "archive": archive,
                "events": events,
            }
        )

    applicable = sum(
        verdicts[key]
        for key in (
            "PASS_CANDIDATE_CONFORMANCE",
            "PASS_ALREADY_SATISFIED",
            "NO_RESPONSE_UNDER_CANDIDATE_HEURISTIC",
        )
    )
    report = {
        "checker": "OFFICIAL_NVIDIA_VALIDATION_MULTI_EVENT_COHORT",
        "publication_control": {
            "classification": "LICENSE_RESTRICTED_INTERNAL_RESULT",
            "reason": "NVIDIA AV Dataset License sections 3 and 4.6",
        },
        "selection": {
            "method": "PURPOSIVE_DIVERSE_VALIDATION_MULTI_EVENT_COHORT",
            "episode_count": len(episodes),
            "event_cluster_counts": dict(sorted(clusters.items())),
            "not_statistically_representative": True,
        },
        "source_hashes": {
            "reasoning": sha256_file(reasoning_path),
            "clip_index": sha256_file(index_path),
            "feature_presence": sha256_file(feature_path),
        },
        "summary": {
            "event_count": sum(len(episode["events"]) for episode in episodes),
            "applicable_event_count": applicable,
            "verdict_counts": dict(sorted(verdicts.items())),
            "candidate_deadline_s": DEADLINE_US / 1e6,
            "deadline_status": "FEASIBILITY_PARAMETER_NOT_SAFETY_JUSTIFIED",
            "physical_safety": "UNKNOWN",
        },
        "episodes": episodes,
    }
    output = args.output or args.root / "internal-derived/cohort-10/cohort-conformance.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["summary"], indent=2))


if __name__ == "__main__":
    main()
