#!/usr/bin/env python3
"""Generate and verify a licensed NVIDIA multi-event episode internally."""

from __future__ import annotations

import argparse
import json
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

from generate_models import add_location, add_template, add_transition
from run_verification import ANSI_ESCAPE, DEFAULT_VERIFYTA, classify_output


ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "PROJECT_REGISTRY.json").is_file())
DEFAULT_ANALYSIS = ROOT / (
    "data/restricted/nvidia_physicalai/internal-derived/"
    "caf6ea10-fc2b-47d1-814c-67c73b6cea9f/episode-conformance.json"
)
VARIANTS = ("baseline", "late_first_response", "missing_left_response")
QUERIES = (
    "E<> Monitor.Done",
    "A[] not deadline_violation",
    "A[] not order_violation",
    "A[] not deadlock",
)
EXPECTED = {
    "baseline": [True, True, True, True],
    "late_first_response": [False, False, True, True],
    "missing_left_response": [False, True, False, True],
}
DEADLINE_MS = 1000


def schedule(report: dict, variant: str) -> list[tuple[int, str]]:
    events = report["events"]
    origin_us = int(events[0]["timestamp_us"])
    scheduled = []
    for index, event in enumerate(events):
        request_ms = round((int(event["timestamp_us"]) - origin_us) / 1000)
        response_us = event["response"]["response_onset_us"]
        if response_us is None:
            raise ValueError(f"event {index} has no observed response")
        response_ms = round((int(response_us) - origin_us) / 1000)
        if variant == "late_first_response" and index == 0:
            response_ms = request_ms + DEADLINE_MS + 100
        scheduled.append((request_ms, f"req{index}"))
        if not (variant == "missing_left_response" and index == 1):
            scheduled.append((response_ms, f"ack{index}"))
    return sorted(scheduled, key=lambda item: (item[0], item[1].startswith("req")))


def build_model(report: dict, variant: str) -> ET.ElementTree:
    nta = ET.Element("nta")
    ET.SubElement(nta, "declaration").text = f"""
// Candidate deadline for mutation testing; not a justified physical-safety bound.
const int D = {DEADLINE_MS};
clock episode;
broadcast chan req0, ack0, req1, ack1, req2, ack2;
bool deadline_violation = false;
bool order_violation = false;
""".strip()

    source_events = schedule(report, variant)
    source = add_template(nta, "EpisodeSource")
    for index in range(len(source_events) + 1):
        name = "Done" if index == len(source_events) else f"Before{index}"
        invariant = None if index == len(source_events) else f"episode <= {source_events[index][0]}"
        add_location(source, f"s{index}", name, index * 130, 0, invariant)
    ET.SubElement(source, "init", {"ref": "s0"})
    for index, (at_ms, channel) in enumerate(source_events):
        add_transition(
            source,
            f"s{index}",
            f"s{index + 1}",
            guard=f"episode == {at_ms}",
            sync=f"{channel}!",
        )
    add_transition(source, f"s{len(source_events)}", f"s{len(source_events)}")

    monitor = add_template(nta, "ContractMonitor", "clock response;")
    locations = (
        ("w0", "WaitReq0", None),
        ("a0", "WaitAck0", "response <= D"),
        ("w1", "WaitReq1", None),
        ("a1", "WaitAck1", "response <= D"),
        ("w2", "WaitReq2", None),
        ("a2", "WaitAck2", "response <= D"),
        ("done", "Done", None),
        ("miss", "DeadlineMiss", None),
        ("order", "OrderViolation", None),
    )
    for index, (identifier, name, invariant) in enumerate(locations):
        add_location(monitor, identifier, name, index * 130, 220, invariant)
    ET.SubElement(monitor, "init", {"ref": "w0"})
    for index in range(3):
        target = "done" if index == 2 else f"w{index + 1}"
        add_transition(monitor, f"w{index}", f"a{index}", sync=f"req{index}?", assignment="response = 0")
        add_transition(monitor, f"a{index}", target, sync=f"ack{index}?")
        add_transition(
            monitor,
            f"a{index}",
            "miss",
            guard="response == D",
            assignment="deadline_violation = true",
        )
        for future in range(index + 1, 3):
            add_transition(
                monitor,
                f"a{index}",
                "order",
                sync=f"req{future}?",
                assignment="order_violation = true",
            )
    for terminal in ("done", "miss", "order"):
        add_transition(monitor, terminal, terminal)

    ET.SubElement(nta, "system").text = """
Source = EpisodeSource();
Monitor = ContractMonitor();
system Source, Monitor;
""".strip()
    return ET.ElementTree(nta)


def write_model(tree: ET.ElementTree, path: Path) -> None:
    ET.indent(tree, space="  ")
    xml = ET.tostring(tree.getroot(), encoding="utf-8", xml_declaration=True)
    declaration, body = xml.split(b"\n", 1)
    doctype = (
        b"<!DOCTYPE nta PUBLIC '-//Uppaal Team//DTD Flat System 1.1//EN' "
        b"'http://www.it.uu.se/research/group/darts/uppaal/flat-1_2.dtd'>"
    )
    path.write_bytes(declaration + b"\n" + doctype + b"\n" + body + b"\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--analysis", type=Path, default=DEFAULT_ANALYSIS)
    parser.add_argument("--verifyta", type=Path, default=DEFAULT_VERIFYTA)
    args = parser.parse_args()
    report = json.loads(args.analysis.read_text(encoding="utf-8"))
    output_dir = args.analysis.parent / "uppaal"
    output_dir.mkdir(parents=True, exist_ok=True)
    query_path = output_dir / "episode.q"
    query_path.write_text("\n".join(QUERIES) + "\n", encoding="ascii")

    results = []
    for variant in VARIANTS:
        model_path = output_dir / f"{variant}.xml"
        write_model(build_model(report, variant), model_path)
        completed = subprocess.run(
            [str(args.verifyta), "-q", "-t1", str(model_path), str(query_path)],
            capture_output=True,
            text=True,
            check=False,
        )
        output = ANSI_ESCAPE.sub("", completed.stdout + completed.stderr)
        status, verdicts = classify_output(output, len(QUERIES))
        (output_dir / f"{variant}.trace.txt").write_text(output, encoding="utf-8")
        results.append(
            {
                "variant": variant,
                "status": status,
                "verdicts": verdicts,
                "expected_verdicts": EXPECTED[variant],
                "mutation_oracle_match": status == "EXECUTED" and verdicts == EXPECTED[variant],
            }
        )
    verification = {
        "checker": "UPPAAL_OFFICIAL_NVIDIA_EPISODE_INTERNAL_FEASIBILITY",
        "publication_control": report["publication_control"],
        "candidate_deadline_ms": DEADLINE_MS,
        "deadline_status": "FEASIBILITY_PARAMETER_NOT_SAFETY_JUSTIFIED",
        "query_order": list(QUERIES),
        "models": results,
        "overall": "PASS" if all(item["mutation_oracle_match"] for item in results) else "FAIL",
        "physical_safety": "UNKNOWN",
    }
    path = output_dir / "verification-result.json"
    path.write_text(json.dumps(verification, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(verification, indent=2))


if __name__ == "__main__":
    main()
