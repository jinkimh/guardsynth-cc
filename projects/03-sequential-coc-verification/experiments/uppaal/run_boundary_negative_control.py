#!/usr/bin/env python3
"""Dedicated UPPAAL negative-control for unverified scene-boundary carry-over."""

from __future__ import annotations

import argparse
import json
import subprocess
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

from generate_models import add_location, add_template, add_transition
from run_verification import ANSI_ESCAPE, DEFAULT_VERIFYTA, classify_output


ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "PROJECT_REGISTRY.json").is_file())
MODEL_DIR = ROOT / "artifacts/intermediate/uppaal-models/boundary-negative-control"
QUERIES = (
    "E<> Source.Done",
    "E<> Monitor.Discarded",
    "A[] not cross_boundary_completion",
    "A[] not boundary_carryover",
    "A[] not deadlock",
)


@dataclass(frozen=True)
class Variant:
    name: str
    discard_on_boundary: bool
    expected: tuple[bool, ...]


VARIANTS = (
    Variant("correct_discard", True, (True, True, True, True, True)),
    Variant("buggy_carryover", False, (True, False, False, False, True)),
)


def build_model(variant: Variant) -> ET.ElementTree:
    nta = ET.Element("nta")
    ET.SubElement(nta, "declaration").text = """
// Negative-control timeline in ms.
// A trusted request appears in scene A, an unverified boundary appears before
// the deadline, and a response witness appears only in scene B.
const int REQ_AT = 0;
const int BOUNDARY_AT = 1000;
const int RESP_AT = 1500;
const int DEADLINE = 3000;
clock t;
clock age;
broadcast chan req, scene_boundary, resp;
bool boundary_seen = false;
bool discarded_at_boundary = false;
bool boundary_carryover = false;
bool cross_boundary_completion = false;
""".strip()

    source = add_template(nta, "SourceProc")
    add_location(source, "s0", "BeforeReq", 0, 0, "t <= REQ_AT")
    add_location(source, "s1", "BeforeBoundary", 180, 0, "t <= BOUNDARY_AT")
    add_location(source, "s2", "BeforeResp", 390, 0, "t <= RESP_AT")
    add_location(source, "s3", "Done", 600, 0)
    ET.SubElement(source, "init", {"ref": "s0"})
    add_transition(source, "s0", "s1", "t == REQ_AT", "req!")
    add_transition(source, "s1", "s2", "t == BOUNDARY_AT", "scene_boundary!")
    add_transition(source, "s2", "s3", "t == RESP_AT", "resp!")
    add_transition(source, "s3", "s3")

    monitor = add_template(nta, "BoundaryMonitor")
    add_location(monitor, "m0", "Idle", 0, 260)
    add_location(monitor, "m1", "Active", 220, 260, "age <= DEADLINE")
    add_location(monitor, "m2", "Responded", 450, 200)
    add_location(monitor, "m3", "Discarded", 450, 330)
    add_location(monitor, "m4", "Miss", 670, 260)
    ET.SubElement(monitor, "init", {"ref": "m0"})
    add_transition(monitor, "m0", "m1", sync="req?", assignment="age = 0")
    if variant.discard_on_boundary:
        add_transition(
            monitor,
            "m1",
            "m3",
            sync="scene_boundary?",
            assignment="boundary_seen = true, discarded_at_boundary = true",
        )
    else:
        add_transition(
            monitor,
            "m1",
            "m1",
            sync="scene_boundary?",
            assignment="boundary_seen = true, boundary_carryover = true",
        )
    add_transition(
        monitor,
        "m1",
        "m2",
        sync="resp?",
        assignment="cross_boundary_completion = boundary_seen",
    )
    add_transition(monitor, "m1", "m4", "age >= DEADLINE")
    add_transition(monitor, "m2", "m2")
    add_transition(monitor, "m3", "m3")
    add_transition(monitor, "m4", "m4")

    ET.SubElement(nta, "system").text = """
Source = SourceProc();
Monitor = BoundaryMonitor();
system Source, Monitor;
""".strip()
    return ET.ElementTree(nta)


def write_model(variant: Variant) -> Path:
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    tree = build_model(variant)
    ET.indent(tree, space="  ")
    model_path = MODEL_DIR / f"{variant.name}.xml"
    xml_bytes = ET.tostring(tree.getroot(), encoding="utf-8", xml_declaration=True)
    declaration, body = xml_bytes.split(b"\n", 1)
    doctype = (
        b"<!DOCTYPE nta PUBLIC '-//Uppaal Team//DTD Flat System 1.1//EN' "
        b"'http://www.it.uu.se/research/group/darts/uppaal/flat-1_2.dtd'>"
    )
    model_path.write_bytes(declaration + b"\n" + doctype + b"\n" + body + b"\n")
    (MODEL_DIR / "boundary-negative-control.q").write_text(
        "\n".join(QUERIES) + "\n", encoding="ascii"
    )
    return model_path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--verifyta", type=Path, default=DEFAULT_VERIFYTA)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("artifacts/results/public/workshop-boost/boundary-negative-control-result.json"),
    )
    args = parser.parse_args()

    results = []
    trace_dir = args.output.parent / "uppaal-traces"
    trace_dir.mkdir(parents=True, exist_ok=True)
    query_path = MODEL_DIR / "boundary-negative-control.q"
    for variant in VARIANTS:
        model_path = write_model(variant)
        completed = subprocess.run(
            [str(args.verifyta), "-q", "-t1", str(model_path), str(query_path)],
            capture_output=True,
            text=True,
            check=False,
        )
        cleaned = ANSI_ESCAPE.sub("", completed.stdout + completed.stderr)
        status, verdicts = classify_output(cleaned, len(QUERIES))
        trace_path = trace_dir / f"boundary-{variant.name}.txt"
        trace_path.write_text(cleaned, encoding="utf-8")
        results.append(
            {
                "variant": variant.name,
                "status": status,
                "exit_code": completed.returncode,
                "verdicts": verdicts,
                "expected_verdicts": list(variant.expected),
                "oracle_match": verdicts == list(variant.expected)
                if status == "EXECUTED"
                else None,
                "violated_queries": [
                    QUERIES[index] for index, verdict in enumerate(verdicts) if not verdict
                ],
                "model": str(model_path),
                "trace_path": str(trace_path),
            }
        )

    report = {
        "checker": "UPPAAL_BOUNDARY_NEGATIVE_CONTROL",
        "purpose": (
            "Verify that an obligation opened in an unverified scene is discarded "
            "at the scene boundary and cannot be completed by a response witness "
            "from the next scene."
        ),
        "timeline_ms": {"request": 0, "unverified_boundary": 1000, "response": 1500},
        "queries": list(QUERIES),
        "results": results,
        "overall": (
            "PASS"
            if all(item["status"] == "EXECUTED" and item["oracle_match"] for item in results)
            else "FAIL_OR_PARTIAL"
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
