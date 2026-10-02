#!/usr/bin/env python3
"""Generate UPPAAL trace models for the multi-scene CoC cohort."""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from pathlib import Path

from generate_models import add_location, add_template, add_transition


ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "PROJECT_REGISTRY.json").is_file())
MODEL_DIR = ROOT / "artifacts/intermediate/uppaal-models/cohort-13"
COHORT_RESULT = ROOT / "artifacts/results/public/cohort-13/weak-kinematic-cohort-result.json"
VARIANTS = ("baseline", "provenance_mutation", "response_mutation")
QUERIES = (
    "E<> Source.Done",
    "A[] not provenance_violation",
    "A[] not weak_response_violation",
    "A[] not deadlock",
)


def build_model(episode: dict, variant: str) -> ET.ElementTree:
    nta = ET.Element("nta")
    events = episode["events"]
    origin_us = min(event["timestamp_us"] for event in events)
    times_ms = [round((event["timestamp_us"] - origin_us) / 1000) for event in events]
    ET.SubElement(nta, "declaration").text = f"""
// {episode['clip_id']}; milliseconds relative to the first source CoC event.
clock episode;
broadcast chan coc_event;
bool provenance_violation = false;
bool weak_response_violation = false;
""".strip()
    source = add_template(nta, "EpisodeSource")
    for index in range(len(events) + 1):
        name = "Done" if index == len(events) else f"Before{index + 1}"
        invariant = None if index == len(events) else f"episode <= {times_ms[index]}"
        add_location(source, f"s{index}", name, index * 140, 0, invariant)
    ET.SubElement(source, "init", {"ref": "s0"})
    for index, at_ms in enumerate(times_ms):
        assignments = []
        if index == 0 and variant == "provenance_mutation":
            assignments.append("provenance_violation = true")
        if index == 0 and variant == "response_mutation":
            assignments.append("weak_response_violation = true")
        if (
            variant != "response_mutation"
            and events[index]["weak_kinematic_contract"] == "FAIL"
        ):
            assignments.append("weak_response_violation = true")
        add_transition(
            source,
            f"s{index}",
            f"s{index + 1}",
            guard=f"episode == {at_ms}",
            sync="coc_event!",
            assignment=", ".join(assignments) or None,
        )
    add_transition(source, f"s{len(events)}", f"s{len(events)}")

    monitor = add_template(nta, "LineageMonitor", "int[0, 100] seen = 0;")
    add_location(monitor, "m0", "Tracking", 0, 220)
    ET.SubElement(monitor, "init", {"ref": "m0"})
    add_transition(monitor, "m0", "m0", sync="coc_event?", assignment="seen++")

    ET.SubElement(nta, "system").text = """
Source = EpisodeSource();
Lineage = LineageMonitor();
system Source, Lineage;
""".strip()
    return ET.ElementTree(nta)


def expected_verdicts(episode: dict, variant: str) -> list[bool]:
    return [
        True,
        variant != "provenance_mutation",
        variant != "response_mutation" and episode["contract_fail_count"] == 0,
        True,
    ]


def write_models(
    output_dir: Path = MODEL_DIR, cohort_result: Path = COHORT_RESULT
) -> dict:
    result = json.loads(cohort_result.read_text(encoding="utf-8"))
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "cohort.q").write_text("\n".join(QUERIES) + "\n", encoding="ascii")
    expected = {}
    for episode in result["episodes"]:
        clip_id = episode["clip_id"]
        expected[clip_id] = {}
        for variant in VARIANTS:
            tree = build_model(episode, variant)
            ET.indent(tree, space="  ")
            xml_bytes = ET.tostring(tree.getroot(), encoding="utf-8", xml_declaration=True)
            declaration, body = xml_bytes.split(b"\n", 1)
            doctype = (
                b"<!DOCTYPE nta PUBLIC '-//Uppaal Team//DTD Flat System 1.1//EN' "
                b"'http://www.it.uu.se/research/group/darts/uppaal/flat-1_2.dtd'>"
            )
            (output_dir / f"{clip_id}-{variant}.xml").write_bytes(
                declaration + b"\n" + doctype + b"\n" + body + b"\n"
            )
            expected[clip_id][variant] = expected_verdicts(episode, variant)
    oracle = {
        "query_order": list(QUERIES),
        "expected_satisfaction": expected,
        "source": (
            str(cohort_result.relative_to(ROOT))
            if cohort_result.is_relative_to(ROOT)
            else str(cohort_result)
        ),
        "model_count": len(result["episodes"]) * len(VARIANTS),
    }
    (output_dir / "expected-results.json").write_text(
        json.dumps(oracle, indent=2) + "\n", encoding="ascii"
    )
    return oracle


if __name__ == "__main__":
    write_models()
