#!/usr/bin/env python3
"""Generate a repeated-obligation semantics model for scene-0074."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

from generate_models import add_location, add_template, add_transition


ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "PROJECT_REGISTRY.json").is_file())
MODEL_DIR = ROOT / "artifacts/intermediate/uppaal-models/scene-0074-protocol"
MODEL_PATH = MODEL_DIR / "scene-0074-repeated-acceleration.xml"
QUERY_PATH = MODEL_DIR / "scene-0074-repeated-acceleration.q"

# Milliseconds relative to the first CoC at 3.4 s. Response times use the
# cohort checker's default profile: 0.5 s window, 0.1 m/s delta, 0.7 fraction.
TRACE_EVENTS = (
    (0, "accelerate"),
    (2500, "accelerate"),
    (3360, "speed_response"),
    (3800, "accelerate"),
    (3820, "speed_response"),
    (8200, "accelerate"),
    (8201, "speed_response"),
)
DEADLINE_MS = 3000
QUERIES = (
    "E<> strict_deadline_miss",
    "A[] not strict_deadline_miss",
    "A[] not reset_deadline_miss",
    "E<> strict_response_count == 3",
    "E<> reset_response_count == 3",
    "A[] provenance_valid",
    "A[] not deadlock",
)
EXPECTED = (True, False, True, True, True, True, True)


def _add_monitor(
    nta: ET.Element,
    name: str,
    reset_on_repeat: bool,
    miss_variable: str,
    response_count: str,
) -> None:
    monitor = add_template(nta, name, "clock obligation;")
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
        sync="accelerate?",
        assignment="obligation = 0",
    )
    add_transition(
        monitor,
        "pending",
        "pending",
        sync="accelerate?",
        assignment="obligation = 0" if reset_on_repeat else None,
    )
    add_transition(
        monitor,
        "pending",
        "idle",
        sync="speed_response?",
        assignment=f"{response_count}++",
    )
    add_transition(
        monitor,
        "pending",
        "late",
        guard="obligation == RESPONSE_DEADLINE",
        assignment=f"{miss_variable} = true",
    )
    add_transition(
        monitor,
        "late",
        "late",
        sync="accelerate?",
        assignment="obligation = 0" if reset_on_repeat else None,
    )
    add_transition(
        monitor,
        "late",
        "idle",
        sync="speed_response?",
        assignment=f"{response_count}++",
    )


def build_model() -> ET.ElementTree:
    nta = ET.Element("nta")
    ET.SubElement(nta, "declaration").text = f"""
// scene-0074; milliseconds relative to the first observed CoC at 3.4 s.
const int RESPONSE_DEADLINE = {DEADLINE_MS};
clock episode;
broadcast chan accelerate, speed_response;
bool strict_deadline_miss = false;
bool reset_deadline_miss = false;
bool provenance_valid = true;
int[0, 3] strict_response_count = 0;
int[0, 3] reset_response_count = 0;
""".strip()

    source = add_template(nta, "ObservedTrace")
    for index in range(len(TRACE_EVENTS) + 1):
        name = "Done" if index == len(TRACE_EVENTS) else f"Before{index + 1}"
        invariant = (
            None
            if index == len(TRACE_EVENTS)
            else f"episode <= {TRACE_EVENTS[index][0]}"
        )
        add_location(source, f"s{index}", name, index * 130, 0, invariant)
    ET.SubElement(source, "init", {"ref": "s0"})
    for index, (at_ms, channel) in enumerate(TRACE_EVENTS):
        add_transition(
            source,
            f"s{index}",
            f"s{index + 1}",
            guard=f"episode == {at_ms}",
            sync=f"{channel}!",
        )
    add_transition(source, f"s{len(TRACE_EVENTS)}", f"s{len(TRACE_EVENTS)}")

    _add_monitor(
        nta,
        "PreserveFirstDeadline",
        reset_on_repeat=False,
        miss_variable="strict_deadline_miss",
        response_count="strict_response_count",
    )
    _add_monitor(
        nta,
        "ResetOnRepeat",
        reset_on_repeat=True,
        miss_variable="reset_deadline_miss",
        response_count="reset_response_count",
    )
    ET.SubElement(nta, "system").text = """
Trace = ObservedTrace();
Strict = PreserveFirstDeadline();
Reset = ResetOnRepeat();
system Trace, Strict, Reset;
""".strip()
    return ET.ElementTree(nta)


def write_model(output_dir: Path = MODEL_DIR) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    tree = build_model()
    ET.indent(tree, space="  ")
    xml_bytes = ET.tostring(tree.getroot(), encoding="utf-8", xml_declaration=True)
    declaration, body = xml_bytes.split(b"\n", 1)
    doctype = (
        b"<!DOCTYPE nta PUBLIC '-//Uppaal Team//DTD Flat System 1.1//EN' "
        b"'http://www.it.uu.se/research/group/darts/uppaal/flat-1_2.dtd'>"
    )
    model_path = output_dir / MODEL_PATH.name
    query_path = output_dir / QUERY_PATH.name
    model_path.write_bytes(declaration + b"\n" + doctype + b"\n" + body + b"\n")
    query_path.write_text("\n".join(QUERIES) + "\n", encoding="ascii")
    return model_path, query_path


if __name__ == "__main__":
    write_model()
