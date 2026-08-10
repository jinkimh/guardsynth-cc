#!/usr/bin/env python3
"""Generate a compact loop-based UPPAAL model for a multi-scene chain."""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from generate_models import add_location, add_template, add_transition
from generate_multiscene_chain_model import (
    DEADLINE_MS,
    DEFAULT_SCENES,
    MAX_BOUNDARY_GAP_MS,
    MODEL_DIR,
    QUERIES,
    build_timeline,
)


KIND = {
    "slow_req": 1,
    "accel_req": 2,
    "slow_resp": 3,
    "accel_resp": 4,
    "scene_boundary": 5,
}


def c_array(values: list[int]) -> str:
    return "{" + ", ".join(str(value) for value in values) + "}"


def build_loop_model(timeline) -> ET.ElementTree:
    nta = ET.Element("nta")
    event_count = len(timeline)
    event_times = [event.time_ms for event in timeline] + [
        timeline[-1].time_ms if timeline else 0
    ]
    event_kinds = [KIND[event.channel] for event in timeline] + [0]
    event_gaps = [
        int(event.detail["gap_ms"]) if event.channel == "scene_boundary" else 0
        for event in timeline
    ] + [0]

    declaration = f"""
clock t;
clock obligation_clock;
broadcast chan slow_req, accel_req, slow_resp, accel_resp, scene_boundary;
const int DEADLINE = {DEADLINE_MS};
const int MAX_BOUNDARY_GAP = {MAX_BOUNDARY_GAP_MS};
const int EVENT_COUNT = {event_count};
const int SLOW_REQ = 1;
const int ACCEL_REQ = 2;
const int SLOW_RESP = 3;
const int ACCEL_RESP = 4;
const int SCENE_BOUNDARY = 5;
const int event_time[{event_count + 1}] = {c_array(event_times)};
const int event_kind[{event_count + 1}] = {c_array(event_kinds)};
const int event_gap[{event_count + 1}] = {c_array(event_gaps)};
int[0,{event_count}] idx = 0;
bool deadline_miss = false;
bool contradiction = false;
bool boundary_violation = false;
int active_intent = 0; // 0 none, 1 slow, 2 accel
""".strip()
    ET.SubElement(nta, "declaration").text = declaration

    source = add_template(nta, "LoopSource")
    add_location(source, "s0", "Replay", 0, 0, "t <= event_time[idx]")
    add_location(source, "s1", "Done", 260, 0)
    ET.SubElement(source, "init", {"ref": "s0"})
    for channel, kind in KIND.items():
        assignment = "idx++"
        if channel == "scene_boundary":
            assignment = (
                "boundary_violation = boundary_violation || "
                "event_gap[idx] > MAX_BOUNDARY_GAP, idx++"
            )
        add_transition(
            source,
            "s0",
            "s0",
            guard=(
                f"idx < EVENT_COUNT && t == event_time[idx] && "
                f"event_kind[idx] == {kind}"
            ),
            sync=f"{channel}!",
            assignment=assignment,
        )
    add_transition(source, "s0", "s1", guard="idx == EVENT_COUNT")
    add_transition(source, "s1", "s1")

    monitor = add_template(nta, "Monitor")
    add_location(monitor, "m0", "Idle", 0, 260)
    add_location(monitor, "m1", "ActiveSlow", 220, 200, "obligation_clock <= DEADLINE")
    add_location(monitor, "m2", "ActiveAccel", 220, 320, "obligation_clock <= DEADLINE")
    add_location(monitor, "m3", "Responded", 460, 260)
    add_location(monitor, "m4", "Miss", 460, 420)
    ET.SubElement(monitor, "init", {"ref": "m0"})
    add_transition(
        monitor,
        "m0",
        "m1",
        sync="slow_req?",
        assignment="active_intent = 1, obligation_clock = 0",
    )
    add_transition(
        monitor,
        "m0",
        "m2",
        sync="accel_req?",
        assignment="active_intent = 2, obligation_clock = 0",
    )
    add_transition(monitor, "m1", "m1", sync="slow_req?")
    add_transition(monitor, "m2", "m2", sync="accel_req?")
    add_transition(
        monitor,
        "m1",
        "m2",
        sync="accel_req?",
        assignment="contradiction = true, active_intent = 2, obligation_clock = 0",
    )
    add_transition(
        monitor,
        "m2",
        "m1",
        sync="slow_req?",
        assignment="contradiction = true, active_intent = 1, obligation_clock = 0",
    )
    add_transition(monitor, "m1", "m3", sync="slow_resp?", assignment="active_intent = 0")
    add_transition(monitor, "m2", "m3", sync="accel_resp?", assignment="active_intent = 0")
    add_transition(
        monitor,
        "m3",
        "m1",
        sync="slow_req?",
        assignment="active_intent = 1, obligation_clock = 0",
    )
    add_transition(
        monitor,
        "m3",
        "m2",
        sync="accel_req?",
        assignment="active_intent = 2, obligation_clock = 0",
    )
    add_transition(
        monitor,
        "m1",
        "m4",
        guard="obligation_clock >= DEADLINE",
        assignment="deadline_miss = true",
    )
    add_transition(
        monitor,
        "m2",
        "m4",
        guard="obligation_clock >= DEADLINE",
        assignment="deadline_miss = true",
    )
    add_transition(monitor, "m4", "m4")

    ET.SubElement(nta, "system").text = """
Source = LoopSource();
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
    tree = build_loop_model(timeline)
    ET.indent(tree, space="  ")
    xml_bytes = ET.tostring(tree.getroot(), encoding="utf-8", xml_declaration=True)
    declaration, body = xml_bytes.split(b"\n", 1)
    doctype = (
        b"<!DOCTYPE nta PUBLIC '-//Uppaal Team//DTD Flat System 1.1//EN' "
        b"'http://www.it.uu.se/research/group/darts/uppaal/flat-1_2.dtd'>"
    )
    model_name = f"{scenes[0]}-to-{scenes[-1]}-loop.xml"
    (output_dir / model_name).write_bytes(declaration + b"\n" + doctype + b"\n" + body + b"\n")
    (output_dir / "multiscene-loop.q").write_text("\n".join(QUERIES) + "\n", encoding="ascii")
    profile["model"] = model_name
    profile["model_style"] = "LOOP_INDEXED_EVENT_REPLAY"
    profile["kind_encoding"] = KIND
    profile["queries"] = list(QUERIES)
    (output_dir / f"{scenes[0]}-to-{scenes[-1]}-loop-profile.json").write_text(
        json.dumps(profile, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return profile


if __name__ == "__main__":
    write_model()
