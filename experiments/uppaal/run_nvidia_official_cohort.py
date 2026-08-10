#!/usr/bin/env python3
"""Generate and verify internal UPPAAL models for the licensed cohort."""

from __future__ import annotations

import argparse
import json
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

from generate_models import add_location, add_template, add_transition
from run_verification import ANSI_ESCAPE, DEFAULT_VERIFYTA, classify_output


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_COHORT = ROOT / "data/restricted/nvidia_physicalai/internal-derived/cohort-10/cohort-conformance.json"
VARIANTS = ("baseline", "provenance_mutation", "response_mutation", "order_mutation")
QUERIES = (
    "E<> Source.Done",
    "A[] not candidate_response_violation",
    "A[] not order_violation",
    "A[] not provenance_violation",
    "A[] not deadlock",
)
DEADLINE_MS = 1000


def applicable_events(episode: dict) -> list[dict]:
    return [event for event in episode["events"] if event.get("response") is not None]


def event_schedule(events: list[dict], variant: str) -> list[tuple[int, str]]:
    origin_us = min(int(event["timestamp_us"]) for event in events)
    schedule = []
    mutation_target = next(
        (index for index, event in enumerate(events) if event["response"]["response_onset_us"] is not None),
        None,
    )
    for index, event in enumerate(events):
        request_index = index
        if variant == "order_mutation" and len(events) > 1:
            request_index = 1 if index == 0 else 0 if index == 1 else index
        request_ms = round((int(event["timestamp_us"]) - origin_us) / 1000)
        schedule.append((request_ms, f"req{request_index}"))
        response_us = event["response"]["response_onset_us"]
        if response_us is None or (variant == "response_mutation" and index == mutation_target):
            continue
        response_ms = round((int(response_us) - origin_us) / 1000)
        schedule.append((response_ms, f"ack{index}"))
    return sorted(schedule, key=lambda item: (item[0], 0 if item[1].startswith("req") else 1))


def build_model(episode: dict, variant: str) -> ET.ElementTree:
    events = applicable_events(episode)
    if not events:
        raise ValueError(f"episode has no applicable event: {episode['clip_id']}")
    channels = ", ".join(
        channel for index in range(len(events)) for channel in (f"req{index}", f"ack{index}")
    )
    nta = ET.Element("nta")
    ET.SubElement(nta, "declaration").text = f"""
const int D = {DEADLINE_MS};
clock episode;
broadcast chan {channels};
bool candidate_response_violation = false;
bool order_violation = false;
bool provenance_violation = {'true' if variant == 'provenance_mutation' else 'false'};
""".strip()

    schedule = event_schedule(events, variant)
    source = add_template(nta, "EpisodeSource")
    for index in range(len(schedule) + 1):
        name = "Done" if index == len(schedule) else f"Before{index}"
        invariant = None if index == len(schedule) else f"episode <= {schedule[index][0]}"
        add_location(source, f"s{index}", name, index * 115, 0, invariant)
    ET.SubElement(source, "init", {"ref": "s0"})
    for index, (at_ms, channel) in enumerate(schedule):
        add_transition(source, f"s{index}", f"s{index + 1}", guard=f"episode == {at_ms}", sync=f"{channel}!")
    add_transition(source, f"s{len(schedule)}", f"s{len(schedule)}")

    systems = ["Source = EpisodeSource();"]
    instances = ["Source"]
    for index in range(len(events)):
        template_name = f"ResponseMonitor{index}"
        monitor = add_template(nta, template_name, "clock response;")
        add_location(monitor, "wait", "WaitRequest", 0, 180)
        add_location(monitor, "ack", "WaitResponse", 150, 180, "response <= D")
        add_location(monitor, "done", "Done", 300, 180)
        add_location(monitor, "miss", "Miss", 300, 280)
        ET.SubElement(monitor, "init", {"ref": "wait"})
        add_transition(monitor, "wait", "ack", sync=f"req{index}?", assignment="response = 0")
        add_transition(monitor, "ack", "done", sync=f"ack{index}?")
        add_transition(
            monitor,
            "ack",
            "miss",
            guard="response == D",
            assignment="candidate_response_violation = true",
        )
        add_transition(monitor, "done", "done")
        add_transition(monitor, "miss", "miss")
        instance = f"R{index}"
        systems.append(f"{instance} = {template_name}();")
        instances.append(instance)

    order = add_template(nta, "OrderMonitor")
    for index in range(len(events) + 1):
        add_location(order, f"o{index}", "Done" if index == len(events) else f"Expect{index}", index * 130, 420)
    add_location(order, "bad", "OrderViolation", 0, 540)
    ET.SubElement(order, "init", {"ref": "o0"})
    for expected in range(len(events)):
        add_transition(order, f"o{expected}", f"o{expected + 1}", sync=f"req{expected}?")
        for received in range(len(events)):
            if received != expected:
                add_transition(order, f"o{expected}", "bad", sync=f"req{received}?", assignment="order_violation = true")
    add_transition(order, f"o{len(events)}", f"o{len(events)}")
    add_transition(order, "bad", "bad")
    systems.append("Order = OrderMonitor();")
    instances.append("Order")
    ET.SubElement(nta, "system").text = "\n".join(systems) + "\nsystem " + ", ".join(instances) + ";"
    return ET.ElementTree(nta)


def write_model(tree: ET.ElementTree, path: Path) -> None:
    ET.indent(tree, space="  ")
    xml = ET.tostring(tree.getroot(), encoding="utf-8", xml_declaration=True)
    declaration, body = xml.split(b"\n", 1)
    doctype = b"<!DOCTYPE nta PUBLIC '-//Uppaal Team//DTD Flat System 1.1//EN' 'http://www.it.uu.se/research/group/darts/uppaal/flat-1_2.dtd'>"
    path.write_bytes(declaration + b"\n" + doctype + b"\n" + body + b"\n")


def expected(episode: dict, variant: str) -> list[bool]:
    events = applicable_events(episode)
    baseline_response = all(event["response"]["response_onset_us"] is not None for event in events)
    order_mutated = variant == "order_mutation" and len(events) > 1
    return [
        True,
        baseline_response and variant != "response_mutation" and not order_mutated,
        not order_mutated,
        variant != "provenance_mutation",
        True,
    ]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cohort", type=Path, default=DEFAULT_COHORT)
    parser.add_argument("--verifyta", type=Path, default=DEFAULT_VERIFYTA)
    args = parser.parse_args()
    cohort = json.loads(args.cohort.read_text(encoding="utf-8"))
    output_dir = args.cohort.parent / "uppaal"
    output_dir.mkdir(parents=True, exist_ok=True)
    query_path = output_dir / "cohort.q"
    query_path.write_text("\n".join(QUERIES) + "\n", encoding="ascii")

    models = []
    for episode in cohort["episodes"]:
        for variant in VARIANTS:
            model_path = output_dir / f"{episode['clip_id']}-{variant}.xml"
            write_model(build_model(episode, variant), model_path)
            completed = subprocess.run(
                [str(args.verifyta), "-q", "-t1", str(model_path), str(query_path)],
                capture_output=True,
                text=True,
                check=False,
            )
            output = ANSI_ESCAPE.sub("", completed.stdout + completed.stderr)
            status, verdicts = classify_output(output, len(QUERIES))
            oracle = expected(episode, variant)
            models.append(
                {
                    "clip_id": episode["clip_id"],
                    "variant": variant,
                    "status": status,
                    "verdicts": verdicts,
                    "expected_verdicts": oracle,
                    "mutation_oracle_match": status == "EXECUTED" and verdicts == oracle,
                }
            )
    report = {
        "checker": "UPPAAL_OFFICIAL_NVIDIA_COHORT_INTERNAL_FEASIBILITY",
        "publication_control": cohort["publication_control"],
        "candidate_deadline_ms": DEADLINE_MS,
        "deadline_status": "FEASIBILITY_PARAMETER_NOT_SAFETY_JUSTIFIED",
        "query_order": list(QUERIES),
        "model_count": len(models),
        "query_count": len(models) * len(QUERIES),
        "mutation_oracle_matches": sum(model["mutation_oracle_match"] for model in models),
        "models": models,
        "overall": "PASS" if all(model["mutation_oracle_match"] for model in models) else "FAIL",
        "physical_safety": "UNKNOWN",
    }
    (output_dir / "verification-result.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: report[key] for key in ("model_count", "query_count", "mutation_oracle_matches", "overall", "physical_safety")}, indent=2))


if __name__ == "__main__":
    main()
