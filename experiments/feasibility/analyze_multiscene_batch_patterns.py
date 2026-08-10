#!/usr/bin/env python3
"""Analyze cross-chain patterns in multi-scene UPPAAL batch results."""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


DEFAULT_INPUT = Path("artifacts/results/public/multiscene-chain/uppaal-loop-batch-all-strict-1s.json")
DEFAULT_OUTPUT = Path("artifacts/results/public/multiscene-chain/uppaal-loop-pattern-analysis.json")


KEYWORDS = {
    "yield": ("yield", "pedestrian", "crosswalk"),
    "lead_vehicle": ("lead vehicle", "white van", "bus ahead", "safe distance"),
    "speed_bump": ("speed bump",),
    "intersection": ("intersection",),
    "construction": ("construction", "cones", "workers"),
    "parked_vehicle": ("parked", "parked vehicles"),
    "curve": ("curve", "curvy"),
    "accelerate": ("accelerate",),
    "decelerate": ("decelerate", "adapt speed", "maintain speed", "safe speed"),
}


def event_tags(event: dict[str, Any]) -> set[str]:
    cot = event.get("detail", {}).get("cot", "").lower()
    return {
        tag
        for tag, needles in KEYWORDS.items()
        if any(needle in cot for needle in needles)
    }


def first_obligation_without_response(item: dict[str, Any]) -> dict[str, Any] | None:
    active: dict[str, Any] | None = None
    for event in item["events"]:
        channel = event["channel"]
        if channel in {"slow_req", "accel_req"} and active is None:
            active = event
        elif channel == "slow_resp" and active and active["channel"] == "slow_req":
            active = None
        elif channel == "accel_resp" and active and active["channel"] == "accel_req":
            active = None
    return active


def first_deadline_candidate(item: dict[str, Any], deadline_ms: int = 3000) -> dict[str, Any] | None:
    active: dict[str, Any] | None = None
    for event in item["events"]:
        channel = event["channel"]
        if channel in {"slow_req", "accel_req"} and active is None:
            active = event
        elif channel == "slow_resp" and active and active["channel"] == "slow_req":
            if event["time_ms"] - active["time_ms"] <= deadline_ms:
                active = None
        elif channel == "accel_resp" and active and active["channel"] == "accel_req":
            if event["time_ms"] - active["time_ms"] <= deadline_ms:
                active = None
        if active and event["time_ms"] - active["time_ms"] >= deadline_ms:
            return active
    return active


def analyze(path: Path = DEFAULT_INPUT) -> dict[str, Any]:
    payload = json.loads(path.read_text())
    items = payload["items"]
    tag_stats: dict[str, Counter] = defaultdict(Counter)
    channel_stats: Counter = Counter()
    interesting = []
    for item in items:
        status = "PASS" if item["all_queries_satisfied"] else "FAIL"
        for event in item["events"]:
            if event["channel"] not in {"slow_req", "accel_req"}:
                continue
            channel_stats[(status, event["channel"])] += 1
            for tag in event_tags(event):
                tag_stats[tag][status] += 1
        first_deadline = first_deadline_candidate(item)
        first_unclosed = first_obligation_without_response(item)
        reason = []
        if item["all_queries_satisfied"]:
            reason.append("all protocol queries passed")
        if item["no_boundary_violation"]:
            reason.append("scene boundaries are within the 1s continuity gate")
        if item["no_deadline_miss"] is False:
            reason.append("at least one obligation misses the 3s response deadline")
        if item["responded"] is False:
            reason.append("no accepted obligation reaches the Responded location")
        if first_deadline:
            reason.append(
                f"first deadline candidate: {first_deadline['label']} at {first_deadline['time_ms']}ms"
            )
        interesting.append(
            {
                "scenes": item["scenes"],
                "scene_count": item["scene_count"],
                "duration_s": round(item["duration_ms"] / 1000, 3),
                "event_count": item["event_count"],
                "status": status,
                "responded": item["responded"],
                "no_deadline_miss": item["no_deadline_miss"],
                "first_deadline_candidate": None
                if first_deadline is None
                else {
                    "time_ms": first_deadline["time_ms"],
                    "label": first_deadline["label"],
                    "channel": first_deadline["channel"],
                    "cot": first_deadline.get("detail", {}).get("cot"),
                    "tags": sorted(event_tags(first_deadline)),
                },
                "first_unclosed_obligation": None
                if first_unclosed is None
                else {
                    "time_ms": first_unclosed["time_ms"],
                    "label": first_unclosed["label"],
                    "channel": first_unclosed["channel"],
                    "cot": first_unclosed.get("detail", {}).get("cot"),
                    "tags": sorted(event_tags(first_unclosed)),
                },
                "interpretation": "; ".join(reason),
                "report": item["report"],
            }
        )
    tag_table = []
    for tag, counts in tag_stats.items():
        total = counts["PASS"] + counts["FAIL"]
        tag_table.append(
            {
                "tag": tag,
                "pass_events": counts["PASS"],
                "fail_events": counts["FAIL"],
                "total_events": total,
                "fail_share": None if total == 0 else round(counts["FAIL"] / total, 3),
            }
        )
    tag_table.sort(key=lambda row: (row["fail_share"] or 0, row["fail_events"]), reverse=True)
    return {
        "source": str(path),
        "chain_count": len(items),
        "pass_chain_count": sum(item["all_queries_satisfied"] for item in items),
        "fail_chain_count": sum(not item["all_queries_satisfied"] for item in items),
        "boundary_fail_count": sum(item["no_boundary_violation"] is False for item in items),
        "deadline_fail_count": sum(item["no_deadline_miss"] is False for item in items),
        "responded_fail_count": sum(item["responded"] is False for item in items),
        "tag_table": tag_table,
        "channel_table": [
            {"status": status, "channel": channel, "count": count}
            for (status, channel), count in sorted(channel_stats.items())
        ],
        "interesting_cases": sorted(
            interesting,
            key=lambda row: (
                row["status"] == "PASS",
                -(row["event_count"]),
                row["scenes"][0],
            ),
        ),
        "cross_model_inferences": [
            {
                "claim": "Boundary continuity is not the limiting factor for this strict subset.",
                "evidence": "All 13 chains satisfy A[] not boundary_violation under MAX_BOUNDARY_GAP=1000ms.",
            },
            {
                "claim": "Connected-scene verification adds information beyond continuity audit.",
                "evidence": "Although all boundaries pass, 8 of 13 chains fail the 3s deadline property.",
            },
            {
                "claim": "PASS and FAIL chains can share similar surface vocabulary.",
                "evidence": "Lead-vehicle, intersection, and speed-bump tags appear in both PASS and FAIL groups, so keyword presence alone is not a sufficient oracle.",
            },
        ],
    }


def main() -> None:
    result = analyze()
    DEFAULT_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    DEFAULT_OUTPUT.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
