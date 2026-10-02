#!/usr/bin/env python3
"""Generate UPPAAL models for the four remaining chunk-0 review candidates."""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

from generate_models import add_location, add_template, add_transition


ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "PROJECT_REGISTRY.json").is_file())
MODEL_DIR = ROOT / "artifacts/intermediate/uppaal-models/remaining-candidates"
COHORT_RESULT = (
    ROOT / "artifacts/results/public/chunk-0000-94/weak-kinematic-cohort-result.json"
)
DEADLINES_MS = (1000, 2000, 3000, 4000, 5000)
SEMANTICS = ("preserve", "reset", "deduplicate_1s")
DEDUPLICATION_WINDOW_MS = 1000
QUERIES = (
    "E<> Trace.Done",
    "A[] not deadline_miss",
    "E<> target_response_observed",
    "A[] not orphan_response",
    "A[] provenance_valid",
    "A[] response_count <= accepted_command_count",
    "A[] not deadlock",
)


@dataclass(frozen=True)
class TraceEvent:
    at_ms: int
    kind: str
    target_response: bool = False


@dataclass(frozen=True)
class Candidate:
    scene: str
    target_event_id: str
    origin_scene_time_s: float
    events: tuple[TraceEvent, ...]
    visual_grounding: str


# Response timestamps use the default weak kinematic profile and a 5 s search
# horizon. They are DERIVED from the pinned egomotion trace, not actuator data.
CANDIDATES = (
    Candidate(
        "scene-0019",
        "scene-0019@10600000",
        9.9,
        (
            TraceEvent(0, "command"),
            TraceEvent(0, "response"),
            TraceEvent(700, "command"),
        ),
        "SUPPORTED_PEDESTRIAN_AND_SPEED_BUMP_VISIBLE",
    ),
    Candidate(
        "scene-0028",
        "scene-0028@6500000",
        6.5,
        (
            TraceEvent(0, "command"),
            TraceEvent(2000, "command"),
            TraceEvent(3240, "response", True),
            TraceEvent(4100, "command"),
            TraceEvent(4119, "response"),
            TraceEvent(4800, "command"),
            TraceEvent(4820, "response"),
        ),
        "PARTIAL_INTERSECTION_AND_SIGNAL_VISIBLE_LATER",
    ),
    Candidate(
        "scene-0042",
        "scene-0042@6500000",
        6.5,
        (
            TraceEvent(0, "command"),
            TraceEvent(3240, "response", True),
            TraceEvent(3500, "command"),
            TraceEvent(3520, "response"),
            TraceEvent(5000, "command"),
            TraceEvent(5019, "response"),
        ),
        "SUPPORTED_LEAD_VEHICLE_VISIBLE",
    ),
    Candidate(
        "scene-0065",
        "scene-0065@13200000",
        13.2,
        (
            TraceEvent(0, "command"),
            TraceEvent(3479, "response", True),
        ),
        "BUS_VISIBLE_BUT_CAUSAL_DIRECTION_INCONCLUSIVE",
    ),
)


def emitted_events(candidate: Candidate, semantics: str) -> tuple[TraceEvent, ...]:
    if semantics != "deduplicate_1s":
        return candidate.events
    emitted = []
    previous_command_ms = None
    for event in candidate.events:
        if event.kind != "command":
            emitted.append(event)
            continue
        duplicate = (
            previous_command_ms is not None
            and event.at_ms - previous_command_ms <= DEDUPLICATION_WINDOW_MS
        )
        emitted.append(
            TraceEvent(
                event.at_ms,
                "suppressed_command" if duplicate else "command",
                event.target_response,
            )
        )
        previous_command_ms = event.at_ms
    return tuple(emitted)


def expected_deadline_safety(
    candidate: Candidate, semantics: str, deadline_ms: int
) -> bool:
    pending_since = None
    missed = False
    for event in emitted_events(candidate, semantics):
        if pending_since is not None and event.at_ms - pending_since >= deadline_ms:
            missed = True
        if event.kind == "command":
            if pending_since is None or semantics == "reset":
                pending_since = event.at_ms
        elif event.kind == "response":
            pending_since = None
    if pending_since is not None:
        missed = True
    return not missed


def expected_orphan_response_free(candidate: Candidate, semantics: str) -> bool:
    pending = False
    orphan = False
    for event in emitted_events(candidate, semantics):
        if event.kind == "command":
            pending = True
        elif event.kind == "response":
            if not pending:
                orphan = True
            pending = False
    return not orphan


def expected_verdicts(
    candidate: Candidate, semantics: str, deadline_ms: int
) -> tuple[bool, ...]:
    return (
        True,
        expected_deadline_safety(candidate, semantics, deadline_ms),
        any(event.target_response for event in candidate.events),
        expected_orphan_response_free(candidate, semantics),
        True,
        True,
        True,
    )


def build_model(
    candidate: Candidate, semantics: str, deadline_ms: int
) -> ET.ElementTree:
    nta = ET.Element("nta")
    ET.SubElement(nta, "declaration").text = f"""
// {candidate.scene}; relative to scene time {candidate.origin_scene_time_s:.1f} s.
const int RESPONSE_DEADLINE = {deadline_ms};
const bool RESET_ON_REPEAT = {'true' if semantics == 'reset' else 'false'};
clock episode;
broadcast chan command, suppressed_command, response;
bool deadline_miss = false;
bool target_response_observed = false;
bool orphan_response = false;
bool provenance_valid = true;
bool suppressed_repeat_seen = false;
int[0, 10] accepted_command_count = 0;
int[0, 10] response_count = 0;
""".strip()

    events = emitted_events(candidate, semantics)
    source = add_template(nta, "ObservedTrace")
    for index in range(len(events) + 1):
        name = "Done" if index == len(events) else f"Before{index + 1}"
        invariant = None if index == len(events) else f"episode <= {events[index].at_ms}"
        add_location(source, f"s{index}", name, index * 130, 0, invariant)
    ET.SubElement(source, "init", {"ref": "s0"})
    for index, event in enumerate(events):
        assignment = None
        if event.target_response:
            assignment = "target_response_observed = true"
        add_transition(
            source,
            f"s{index}",
            f"s{index + 1}",
            guard=f"episode == {event.at_ms}",
            sync=f"{event.kind}!",
            assignment=assignment,
        )
    add_transition(source, f"s{len(events)}", f"s{len(events)}")

    monitor = add_template(nta, "ObligationMonitor", "clock obligation;")
    add_location(monitor, "idle", "Idle", 0, 220)
    add_location(
        monitor,
        "pending",
        "Pending",
        220,
        220,
        "obligation <= RESPONSE_DEADLINE",
    )
    add_location(monitor, "late", "Late", 440, 220)
    ET.SubElement(monitor, "init", {"ref": "idle"})
    add_transition(
        monitor,
        "idle",
        "pending",
        sync="command?",
        assignment="obligation = 0, accepted_command_count++",
    )
    add_transition(
        monitor,
        "pending",
        "pending",
        sync="command?",
        assignment=(
            "obligation = 0, accepted_command_count++"
            if semantics == "reset"
            else "accepted_command_count++"
        ),
    )
    add_transition(
        monitor,
        "late",
        "late",
        sync="command?",
        assignment="accepted_command_count++",
    )
    for state in ("idle", "pending", "late"):
        add_transition(
            monitor,
            state,
            state,
            sync="suppressed_command?",
            assignment="suppressed_repeat_seen = true",
        )
    add_transition(
        monitor,
        "pending",
        "late",
        guard="obligation == RESPONSE_DEADLINE",
        assignment="deadline_miss = true",
    )
    add_transition(
        monitor,
        "pending",
        "idle",
        sync="response?",
        assignment="response_count++",
    )
    add_transition(
        monitor,
        "late",
        "idle",
        sync="response?",
        assignment="response_count++",
    )
    add_transition(
        monitor,
        "idle",
        "idle",
        sync="response?",
        assignment="orphan_response = true",
    )

    ET.SubElement(nta, "system").text = """
Trace = ObservedTrace();
Monitor = ObligationMonitor();
system Trace, Monitor;
""".strip()
    return ET.ElementTree(nta)


def write_models(output_dir: Path = MODEL_DIR) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "remaining-candidates.q").write_text(
        "\n".join(QUERIES) + "\n", encoding="ascii"
    )
    expected = {}
    for candidate in CANDIDATES:
        expected[candidate.scene] = {}
        for semantics in SEMANTICS:
            expected[candidate.scene][semantics] = {}
            for deadline_ms in DEADLINES_MS:
                name = f"{candidate.scene}-{semantics}-d{deadline_ms // 1000}"
                tree = build_model(candidate, semantics, deadline_ms)
                ET.indent(tree, space="  ")
                xml_bytes = ET.tostring(
                    tree.getroot(), encoding="utf-8", xml_declaration=True
                )
                declaration, body = xml_bytes.split(b"\n", 1)
                doctype = (
                    b"<!DOCTYPE nta PUBLIC '-//Uppaal Team//DTD Flat System 1.1//EN' "
                    b"'http://www.it.uu.se/research/group/darts/uppaal/flat-1_2.dtd'>"
                )
                (output_dir / f"{name}.xml").write_bytes(
                    declaration + b"\n" + doctype + b"\n" + body + b"\n"
                )
                expected[candidate.scene][semantics][str(deadline_ms)] = list(
                    expected_verdicts(candidate, semantics, deadline_ms)
                )
    oracle = {
        "query_order": list(QUERIES),
        "expected_satisfaction": expected,
        "model_count": len(CANDIDATES) * len(SEMANTICS) * len(DEADLINES_MS),
        "source": str(COHORT_RESULT.relative_to(ROOT)),
    }
    (output_dir / "expected-results.json").write_text(
        json.dumps(oracle, indent=2) + "\n", encoding="ascii"
    )
    return oracle


if __name__ == "__main__":
    write_models()
