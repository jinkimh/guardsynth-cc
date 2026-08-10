#!/usr/bin/env python3
"""Generate a UPPAAL model for an evidence-backed multi-scene chain."""

from __future__ import annotations

import json
import math
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from generate_models import add_location, add_template, add_transition


ROOT = Path(__file__).resolve().parents[2]
COC_ROOT = ROOT / "data/baseline/coc_nusc"
NUSC_ROOT = ROOT / "data/baseline/nuscenes_metadata/interp_12Hz_trainval"
MODEL_DIR = ROOT / "artifacts/intermediate/uppaal-models/multiscene-chain"
DEFAULT_SCENES = ("scene-0130", "scene-0131", "scene-0132", "scene-0133")

DEADLINE_MS = 3000
MAX_BOUNDARY_GAP_MS = 1000
WINDOW_US = 1_000_000
MIN_DELTA_MPS = 0.7

QUERIES = (
    "E<> Source.Done",
    "E<> MonitorProc.Responded",
    "A[] not deadline_miss",
    "A[] not contradiction",
    "A[] not boundary_violation",
    "A[] not deadlock",
)


@dataclass(frozen=True)
class SceneTime:
    name: str
    first_us: int
    last_us: int
    log_token: str


@dataclass(frozen=True)
class TimelineEvent:
    time_ms: int
    channel: str
    label: str
    scene: str
    provenance: str
    detail: dict[str, Any]


def load_scene_times() -> dict[str, SceneTime]:
    scenes = json.loads((NUSC_ROOT / "scene.json").read_text())
    samples = json.loads((NUSC_ROOT / "sample.json").read_text())
    bounds: dict[str, list[int]] = {}
    for sample in samples:
        token = sample["scene_token"]
        timestamp = int(sample["timestamp"])
        row = bounds.setdefault(token, [timestamp, timestamp])
        row[0] = min(row[0], timestamp)
        row[1] = max(row[1], timestamp)
    result = {}
    for scene in scenes:
        first, last = bounds[scene["token"]]
        result[scene["name"]] = SceneTime(scene["name"], first, last, scene["log_token"])
    return result


def speed(frame: pd.DataFrame) -> pd.Series:
    return (frame["vx"] ** 2 + frame["vy"] ** 2 + frame["vz"] ** 2).pow(0.5)


def classify_intent(text: str) -> str | None:
    lowered = text.lower()
    if any(token in lowered for token in ("decelerate", "stop", "yield", "slow", "adapt speed")):
        return "slow"
    if "accelerate" in lowered:
        return "accel"
    return None


def response_onset_ms(frame: pd.DataFrame, trigger_us: int, intent: str) -> int | None:
    values = frame.copy()
    values["speed"] = speed(values)
    candidates = values[
        (values["timestamp"] >= trigger_us)
        & (values["timestamp"] <= trigger_us + DEADLINE_MS * 1000)
    ]
    for row in candidates.itertuples(index=False):
        later = values[
            (values["timestamp"] >= row.timestamp)
            & (values["timestamp"] <= row.timestamp + WINDOW_US)
        ]
        if later.empty:
            continue
        delta = float(later["speed"].iloc[-1] - row.speed)
        if intent == "slow" and delta <= -MIN_DELTA_MPS:
            return round(row.timestamp / 1000)
        if intent == "accel" and delta >= MIN_DELTA_MPS:
            return round(row.timestamp / 1000)
    return None


def load_reasoning_events(scene: str) -> list[dict[str, Any]]:
    frame = pd.read_parquet(COC_ROOT / "reasoning/ood_reasoning.parquet")
    return json.loads(frame.loc[scene, "events"])


def build_timeline(scenes: tuple[str, ...]) -> tuple[list[TimelineEvent], dict[str, Any]]:
    scene_times = load_scene_times()
    origin_us = scene_times[scenes[0]].first_us
    timeline: list[TimelineEvent] = []
    scene_summary = []
    previous: SceneTime | None = None

    for scene in scenes:
        current = scene_times[scene]
        if previous is not None:
            gap_ms = round((current.first_us - previous.last_us) / 1000)
            boundary_time_ms = round((previous.last_us - origin_us) / 1000)
            timeline.append(
                TimelineEvent(
                    boundary_time_ms,
                    "scene_boundary",
                    f"{previous.name}->{scene}",
                    scene,
                    "DERIVED_NUSCENES_METADATA",
                    {"gap_ms": gap_ms, "from": previous.name, "to": scene},
                )
            )
        ego = pd.read_parquet(COC_ROOT / f"labels/egomotion/{scene}.egomotion.parquet")
        trusted_count = 0
        response_count = 0
        for index, event in enumerate(load_reasoning_events(scene)):
            if not event.get("quality_pass"):
                continue
            intent = classify_intent(event["cot"])
            if intent is None:
                continue
            trusted_count += 1
            local_us = int(event["event_start_timestamp"])
            global_ms = round((current.first_us + local_us - origin_us) / 1000)
            request_channel = "slow_req" if intent == "slow" else "accel_req"
            timeline.append(
                TimelineEvent(
                    global_ms,
                    request_channel,
                    f"{scene}:{index}:{intent}",
                    scene,
                    "OBSERVED_COC_REASONING",
                    {"cot": event["cot"], "local_timestamp_us": local_us},
                )
            )
            onset_ms = response_onset_ms(ego, local_us, intent)
            if onset_ms is not None:
                response_count += 1
                response_channel = "slow_resp" if intent == "slow" else "accel_resp"
                timeline.append(
                    TimelineEvent(
                        round((current.first_us + onset_ms * 1000 - origin_us) / 1000),
                        response_channel,
                        f"{scene}:{index}:{intent}:response",
                        scene,
                        "DERIVED_EGO_SPEED_WITNESS",
                        {
                            "request_local_timestamp_us": local_us,
                            "response_local_ms": onset_ms,
                            "detector": {
                                "window_us": WINDOW_US,
                                "min_delta_mps": MIN_DELTA_MPS,
                            },
                        },
                    )
                )
        scene_summary.append(
            {
                "scene": scene,
                "global_start_ms": round((current.first_us - origin_us) / 1000),
                "global_end_ms": round((current.last_us - origin_us) / 1000),
                "trusted_obligation_events": trusted_count,
                "derived_response_witnesses": response_count,
            }
        )
        previous = current

    timeline.sort(key=lambda item: (item.time_ms, item.channel, item.label))
    profile = {
        "scenes": list(scenes),
        "origin_scene": scenes[0],
        "origin_timestamp_us": origin_us,
        "duration_ms": max(event.time_ms for event in timeline) if timeline else 0,
        "deadline_ms": DEADLINE_MS,
        "max_boundary_gap_ms": MAX_BOUNDARY_GAP_MS,
        "scene_summary": scene_summary,
        "event_count": len(timeline),
        "channel_counts": {
            channel: sum(1 for event in timeline if event.channel == channel)
            for channel in sorted({event.channel for event in timeline})
        },
        "events": [event.__dict__ for event in timeline],
    }
    return timeline, profile


def build_model(timeline: list[TimelineEvent]) -> ET.ElementTree:
    nta = ET.Element("nta")
    declaration = f"""
clock t;
clock obligation_clock;
broadcast chan slow_req, accel_req, slow_resp, accel_resp, scene_boundary;
const int DEADLINE = {DEADLINE_MS};
const int MAX_BOUNDARY_GAP = {MAX_BOUNDARY_GAP_MS};
bool deadline_miss = false;
bool contradiction = false;
bool boundary_violation = false;
int active_intent = 0; // 0 none, 1 slow, 2 accel
""".strip()
    ET.SubElement(nta, "declaration").text = declaration

    source = add_template(nta, "ChainSource")
    for index, event in enumerate(timeline):
        add_location(
            source,
            f"s{index}",
            f"Before{index}",
            index * 90,
            0,
            f"t <= {event.time_ms}",
        )
    add_location(source, f"s{len(timeline)}", "Done", len(timeline) * 90, 0)
    ET.SubElement(source, "init", {"ref": "s0"})
    for index, event in enumerate(timeline):
        assignment = None
        if event.channel == "scene_boundary":
            gap_ms = int(event.detail["gap_ms"])
            assignment = f"boundary_violation = boundary_violation || ({gap_ms} > MAX_BOUNDARY_GAP)"
        add_transition(
            source,
            f"s{index}",
            f"s{index + 1}",
            guard=f"t == {event.time_ms}",
            sync=f"{event.channel}!",
            assignment=assignment,
        )
    add_transition(source, f"s{len(timeline)}", f"s{len(timeline)}")

    monitor = add_template(nta, "Monitor")
    add_location(monitor, "m0", "Idle", 0, 260)
    add_location(monitor, "m1", "ActiveSlow", 220, 200, "obligation_clock <= DEADLINE")
    add_location(monitor, "m2", "ActiveAccel", 220, 320, "obligation_clock <= DEADLINE")
    add_location(monitor, "m3", "Responded", 460, 260)
    add_location(monitor, "m4", "Miss", 460, 420)
    ET.SubElement(monitor, "init", {"ref": "m0"})
    add_transition(monitor, "m0", "m1", sync="slow_req?", assignment="active_intent = 1, obligation_clock = 0")
    add_transition(monitor, "m0", "m2", sync="accel_req?", assignment="active_intent = 2, obligation_clock = 0")
    add_transition(monitor, "m1", "m1", sync="slow_req?")
    add_transition(monitor, "m2", "m2", sync="accel_req?")
    add_transition(monitor, "m1", "m2", sync="accel_req?", assignment="contradiction = true, active_intent = 2, obligation_clock = 0")
    add_transition(monitor, "m2", "m1", sync="slow_req?", assignment="contradiction = true, active_intent = 1, obligation_clock = 0")
    add_transition(monitor, "m1", "m3", sync="slow_resp?", assignment="active_intent = 0")
    add_transition(monitor, "m2", "m3", sync="accel_resp?", assignment="active_intent = 0")
    add_transition(monitor, "m3", "m1", sync="slow_req?", assignment="active_intent = 1, obligation_clock = 0")
    add_transition(monitor, "m3", "m2", sync="accel_req?", assignment="active_intent = 2, obligation_clock = 0")
    add_transition(monitor, "m1", "m4", guard="obligation_clock >= DEADLINE", assignment="deadline_miss = true")
    add_transition(monitor, "m2", "m4", guard="obligation_clock >= DEADLINE", assignment="deadline_miss = true")
    add_transition(monitor, "m4", "m4")

    ET.SubElement(nta, "system").text = """
Source = ChainSource();
MonitorProc = Monitor();
system Source, MonitorProc;
""".strip()
    return ET.ElementTree(nta)


def write_model(
    scenes: tuple[str, ...] = DEFAULT_SCENES,
    output_dir: Path = MODEL_DIR,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    timeline, profile = build_timeline(scenes)
    tree = build_model(timeline)
    ET.indent(tree, space="  ")
    xml_bytes = ET.tostring(tree.getroot(), encoding="utf-8", xml_declaration=True)
    declaration, body = xml_bytes.split(b"\n", 1)
    doctype = (
        b"<!DOCTYPE nta PUBLIC '-//Uppaal Team//DTD Flat System 1.1//EN' "
        b"'http://www.it.uu.se/research/group/darts/uppaal/flat-1_2.dtd'>"
    )
    model_name = f"{scenes[0]}-to-{scenes[-1]}-connected.xml"
    (output_dir / model_name).write_bytes(declaration + b"\n" + doctype + b"\n" + body + b"\n")
    (output_dir / "multiscene-chain.q").write_text("\n".join(QUERIES) + "\n", encoding="ascii")
    profile["model"] = model_name
    profile["queries"] = list(QUERIES)
    (output_dir / f"{scenes[0]}-to-{scenes[-1]}-profile.json").write_text(
        json.dumps(profile, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return profile


if __name__ == "__main__":
    write_model()
