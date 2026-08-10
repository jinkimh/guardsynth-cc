#!/usr/bin/env python3
"""Generate a chained multi-phase UPPAAL feasibility scenario."""

from __future__ import annotations

import json
import hashlib
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

from generate_models import (
    DEFAULT_EPISODE_RESULT,
    MODEL_DIR,
    add_location,
    add_template,
    add_transition,
    load_scene_profile,
)


@dataclass(frozen=True)
class ChainVariant:
    name: str
    stop_ack_ms: int | None = 6400
    clearance_ms: int = 8000
    recover_req_ms: int = 8100
    recover_ack_ms: int | None = 9000


VARIANTS = (
    ChainVariant("normal"),
    ChainVariant("late_stop", stop_ack_ms=7200),
    ChainVariant("skip_hold", stop_ack_ms=None, clearance_ms=6800, recover_req_ms=7000),
    ChainVariant(
        "premature_recovery",
        clearance_ms=8000,
        recover_req_ms=7000,
        recover_ack_ms=7900,
    ),
    ChainVariant("no_recovery", recover_ack_ms=None),
)

QUERIES = (
    "E<> Protocol.Decelerating",
    "E<> Protocol.Hold",
    "E<> Protocol.Recovered",
    "A[] not Deadline.Miss",
    "A[] not Protocol.OrderViolation",
    "A[] not premature_recovery",
    "A[] not deadlock",
)

EXPECTED = {
    "normal": [True, True, True, True, True, True, True],
    "late_stop": [True, True, True, False, True, True, True],
    "skip_hold": [True, False, False, False, False, True, True],
    "premature_recovery": [True, True, True, True, True, False, True],
    "no_recovery": [True, True, False, False, True, True, True],
}

STOP_REQUEST_MS = 5000
DECEL_DEADLINE_MS = 3000
STOP_DEADLINE_MS = 1500
RECOVER_DEADLINE_MS = 1500


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def resolve_json_pointer(document, pointer: str):
    value = document
    for token in pointer.lstrip("/").split("/"):
        token = token.replace("~1", "/").replace("~0", "~")
        value = value[int(token)] if isinstance(value, list) else value[token]
    return value


def build_provenance(profile) -> dict:
    result = json.loads(DEFAULT_EPISODE_RESULT.read_text(encoding="utf-8"))
    workspace = Path(__file__).resolve().parents[2]
    source_path = str(DEFAULT_EPISODE_RESULT.relative_to(workspace))
    source = {
        "artifact": source_path,
        "sha256": sha256_file(DEFAULT_EPISODE_RESULT),
        "dataset_class": result["source_class"],
        "clip_id": result["clip_id"],
    }

    def observed(event_id: str, channel: str, event_index: int) -> dict:
        event = result["episode"]["events"][event_index]
        return {
            "event_id": event_id,
            "channel": channel,
            "time_ms": round((int(event["t0_us"]) - profile.trigger_us) / 1000),
            "provenance_class": "OBSERVED",
            "source_artifact": source_path,
            "json_pointer": f"/episode/events/{event_index}",
            "source_timestamp_us": int(event["t0_us"]),
            "quality_pass": bool(event["quality_pass"]),
            "training_role": "SEQUENCE_LABEL",
        }

    response = {
        "event_id": "speed_response_onset",
        "channel": "decel_ack",
        "time_ms": profile.response_ms,
        "provenance_class": "DERIVED",
        "source_artifact": source_path,
        "json_pointer": "/obligations/SAFE_DISTANCE_TRUCK/response_onset_us",
        "derivation": "round((response_onset_us-triggered_at_us)/1000)",
        "measurement_quality": "HEURISTIC_SPEED_TRACE_NOT_ACTIVE_BRAKE_DETECTION",
        "training_role": "WEAK_RESPONSE_LABEL",
    }
    chained = [
        observed("decelerate_request", "decel_req", 0),
        response,
        {
            "event_id": "stop_request",
            "channel": "stop_req",
            "time_ms": STOP_REQUEST_MS,
            "provenance_class": "SYNTHETIC_ASSUMPTION",
            "assumption_id": "A_STOP_REQUEST",
            "training_role": "MUTATION_EXPERIMENT_ONLY",
        },
        {
            "event_id": "stop_confirmation",
            "channel": "stop_ack",
            "time_ms": 6400,
            "provenance_class": "SYNTHETIC_ASSUMPTION",
            "assumption_id": "A_STOP_CONFIRMATION",
            "training_role": "MUTATION_EXPERIMENT_ONLY",
        },
        {
            "event_id": "clearance_granted",
            "channel": "clearance",
            "time_ms": 8000,
            "provenance_class": "SYNTHETIC_ASSUMPTION",
            "assumption_id": "A_CLEARANCE",
            "training_role": "MUTATION_EXPERIMENT_ONLY",
        },
        {
            "event_id": "recover_request",
            "channel": "recover_req",
            "time_ms": 8100,
            "provenance_class": "SYNTHETIC_ASSUMPTION",
            "assumption_id": "A_RECOVER_REQUEST",
            "training_role": "MUTATION_EXPERIMENT_ONLY",
        },
        {
            "event_id": "recover_confirmation",
            "channel": "recover_ack",
            "time_ms": 9000,
            "provenance_class": "SYNTHETIC_ASSUMPTION",
            "assumption_id": "A_RECOVER_CONFIRMATION",
            "training_role": "MUTATION_EXPERIMENT_ONLY",
        },
    ]
    trace_aligned = [
        observed("decelerate_initial", "trusted_decelerate", 0),
        observed("decelerate_repeat_1", "trusted_decelerate_repeat", 1),
        response,
        observed("decelerate_repeat_2", "trusted_decelerate_repeat", 2),
        observed("adapt_speed_nudge_left", "trusted_maneuver_transition", 3),
        observed("low_quality_event_1", "quarantine_candidate", 4),
        observed("low_quality_event_2", "quarantine_candidate", 5),
    ]
    trace_aligned.sort(key=lambda item: item["time_ms"])
    mutations = [
        {
            "variant": "late_stop",
            "operator": "DELAY_EVENT",
            "target_event_id": "stop_confirmation",
            "property": "A[] not Deadline.Miss",
            "provenance_class": "SYNTHETIC_MUTATION",
            "training_role": "HARD_NEGATIVE_ONLY",
        },
        {
            "variant": "skip_hold",
            "operator": "DELETE_EVENT",
            "target_event_id": "stop_confirmation",
            "property": "A[] not Protocol.OrderViolation",
            "provenance_class": "SYNTHETIC_MUTATION",
            "training_role": "HARD_NEGATIVE_ONLY",
        },
        {
            "variant": "premature_recovery",
            "operator": "REORDER_EVENTS",
            "target_event_id": "recover_request",
            "property": "A[] not premature_recovery",
            "provenance_class": "SYNTHETIC_MUTATION",
            "training_role": "HARD_NEGATIVE_ONLY",
        },
        {
            "variant": "no_recovery",
            "operator": "DELETE_EVENT",
            "target_event_id": "recover_confirmation",
            "property": "E<> Protocol.Recovered",
            "provenance_class": "SYNTHETIC_MUTATION",
            "training_role": "HARD_NEGATIVE_ONLY",
        },
    ]
    source_backed = [
        event
        for event in chained + trace_aligned
        if event["provenance_class"] in {"OBSERVED", "DERIVED"}
    ]
    for event in source_backed:
        resolve_json_pointer(result, event["json_pointer"])
    return {
        "schema_version": "1.0",
        "source_artifact": source,
        "source_reference_validation": {
            "status": "PASS",
            "validated_reference_count": len(source_backed),
            "note": "References shared by both model families are validated per use.",
        },
        "chained_four_phase": {
            "event_lineage": chained,
            "traceability": {
                "total_events": 7,
                "source_backed_events": 2,
                "source_coverage": 2 / 7,
                "observed": 1,
                "derived": 1,
                "synthetic": 5,
            },
            "gates": {
                "lineage_complete": "PASS",
                "mutation_verification_eligible": "PASS",
                "positive_sequence_training_eligible": "FAIL",
                "raw_control_supervision_eligible": "FAIL",
            },
            "mutation_lineage": mutations,
        },
        "source_trace_episode": {
            "scenario": (
                "DECELERATE repeats -> response -> ADAPT_SPEED+NUDGE_LEFT "
                "-> low-quality quarantine candidates"
            ),
            "event_lineage": trace_aligned,
            "traceability": {
                "total_events": 7,
                "source_backed_events": 7,
                "source_coverage": 1.0,
                "observed": 6,
                "derived": 1,
                "synthetic": 0,
            },
            "gates": {
                "lineage_complete": "PASS",
                "positive_sequence_training_eligible": "PASS_WITH_WEAK_RESPONSE_LABEL",
                "raw_control_supervision_eligible": "FAIL",
            },
        },
        "policy": {
            "synthetic_as_positive_training_label": "FORBIDDEN",
            "synthetic_mutation_as_hard_negative": "ALLOWED",
            "derived_response_label_requires_quality_weight": True,
        },
    }


def _events(variant: ChainVariant, response_ms: int) -> list[tuple[int, str]]:
    events = [
        (0, "decel_req"),
        (response_ms, "decel_ack"),
        (STOP_REQUEST_MS, "stop_req"),
    ]
    if variant.stop_ack_ms is not None:
        events.append((variant.stop_ack_ms, "stop_ack"))
    events.extend(
        [
            (variant.clearance_ms, "clearance"),
            (variant.recover_req_ms, "recover_req"),
        ]
    )
    if variant.recover_ack_ms is not None:
        events.append((variant.recover_ack_ms, "recover_ack"))
    return sorted(events, key=lambda item: item[0])


def build_model(variant: ChainVariant, response_ms: int) -> ET.ElementTree:
    nta = ET.Element("nta")
    ET.SubElement(nta, "declaration").text = f"""
// Milliseconds relative to the observed first trusted DECELERATE request.
const int DECEL_DEADLINE = {DECEL_DEADLINE_MS};
const int STOP_DEADLINE = {STOP_DEADLINE_MS};
const int RECOVER_DEADLINE = {RECOVER_DEADLINE_MS};
clock episode;
broadcast chan decel_req, decel_ack, stop_req, stop_ack;
broadcast chan clearance, recover_req, recover_ack;
bool clearance_granted = false;
bool premature_recovery = false;
""".strip()

    source = add_template(nta, "ScenarioSource")
    events = _events(variant, response_ms)
    for index in range(len(events) + 1):
        name = "Done" if index == len(events) else f"Before{index + 1}"
        invariant = None if index == len(events) else f"episode <= {events[index][0]}"
        add_location(source, f"s{index}", name, index * 150, 0, invariant)
    ET.SubElement(source, "init", {"ref": "s0"})
    for index, (at_ms, channel) in enumerate(events):
        add_transition(
            source,
            f"s{index}",
            f"s{index + 1}",
            guard=f"episode == {at_ms}",
            sync=f"{channel}!",
        )
    add_transition(source, f"s{len(events)}", f"s{len(events)}")

    protocol = add_template(nta, "ChainProtocol")
    states = (
        ("p0", "Follow"),
        ("p1", "DecelPending"),
        ("p2", "Decelerating"),
        ("p3", "StopPending"),
        ("p4", "Hold"),
        ("p5", "RecoverPending"),
        ("p6", "Recovered"),
        ("p7", "OrderViolation"),
    )
    for index, (location_id, name) in enumerate(states):
        add_location(protocol, location_id, name, (index % 4) * 220, 250 + (index // 4) * 150)
    ET.SubElement(protocol, "init", {"ref": "p0"})
    add_transition(protocol, "p0", "p1", sync="decel_req?")
    add_transition(protocol, "p1", "p2", sync="decel_ack?")
    add_transition(protocol, "p2", "p3", sync="stop_req?")
    add_transition(protocol, "p3", "p4", sync="stop_ack?")
    add_transition(protocol, "p4", "p5", sync="recover_req?")
    add_transition(protocol, "p5", "p6", sync="recover_ack?")
    add_transition(protocol, "p3", "p7", sync="recover_req?")
    add_transition(protocol, "p6", "p6")
    add_transition(protocol, "p7", "p7")

    deadline = add_template(nta, "DeadlineMonitor", "clock phase;")
    add_location(deadline, "d0", "Idle", 0, 560)
    add_location(deadline, "d1", "WaitDecel", 180, 560, "phase <= DECEL_DEADLINE")
    add_location(deadline, "d2", "DecelDone", 360, 560)
    add_location(deadline, "d3", "WaitStop", 540, 560, "phase <= STOP_DEADLINE")
    add_location(deadline, "d4", "Hold", 720, 560)
    add_location(deadline, "d5", "WaitRecover", 900, 560, "phase <= RECOVER_DEADLINE")
    add_location(deadline, "d6", "Done", 1080, 500)
    add_location(deadline, "d7", "Miss", 1080, 640)
    ET.SubElement(deadline, "init", {"ref": "d0"})
    add_transition(deadline, "d0", "d1", sync="decel_req?", assignment="phase = 0")
    add_transition(deadline, "d1", "d2", sync="decel_ack?")
    add_transition(deadline, "d1", "d7", "phase >= DECEL_DEADLINE")
    add_transition(deadline, "d2", "d3", sync="stop_req?", assignment="phase = 0")
    add_transition(deadline, "d3", "d4", sync="stop_ack?")
    add_transition(deadline, "d3", "d7", "phase >= STOP_DEADLINE")
    add_transition(deadline, "d4", "d5", sync="recover_req?", assignment="phase = 0")
    add_transition(deadline, "d5", "d6", sync="recover_ack?")
    add_transition(deadline, "d5", "d7", "phase >= RECOVER_DEADLINE")
    add_transition(deadline, "d6", "d6")
    add_transition(deadline, "d7", "d7")

    gate = add_template(nta, "SafetyGate")
    add_location(gate, "g0", "Blocked", 0, 760)
    add_location(gate, "g1", "Clear", 240, 760)
    ET.SubElement(gate, "init", {"ref": "g0"})
    add_transition(gate, "g0", "g1", sync="clearance?", assignment="clearance_granted = true")
    add_transition(
        gate,
        "g0",
        "g0",
        sync="recover_req?",
        assignment="premature_recovery = true",
    )
    add_transition(gate, "g1", "g1", sync="recover_req?")

    ET.SubElement(nta, "system").text = """
Source = ScenarioSource();
Protocol = ChainProtocol();
Deadline = DeadlineMonitor();
Gate = SafetyGate();
system Source, Protocol, Deadline, Gate;
""".strip()
    return ET.ElementTree(nta)


def write_models(output_dir: Path = MODEL_DIR) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    profile = load_scene_profile(DEFAULT_EPISODE_RESULT)
    (output_dir / "scene-0001-chained.q").write_text(
        "\n".join(QUERIES) + "\n", encoding="ascii"
    )
    for variant in VARIANTS:
        tree = build_model(variant, profile.response_ms)
        ET.indent(tree, space="  ")
        xml_bytes = ET.tostring(tree.getroot(), encoding="utf-8", xml_declaration=True)
        declaration, body = xml_bytes.split(b"\n", 1)
        doctype = (
            b"<!DOCTYPE nta PUBLIC '-//Uppaal Team//DTD Flat System 1.1//EN' "
            b"'http://www.it.uu.se/research/group/darts/uppaal/flat-1_2.dtd'>"
        )
        (output_dir / f"scene-0001-chained-{variant.name}.xml").write_bytes(
            declaration + b"\n" + doctype + b"\n" + body + b"\n"
        )
    lineage = build_provenance(profile)
    provenance = {
        "scenario": "FOLLOW -> DECELERATE -> STOP/HOLD -> RECOVER",
        "time_unit": "milliseconds relative to first trusted DECELERATE request",
        "observed": {
            "decelerate_request_ms": 0,
            "decelerate_response_ms": profile.response_ms,
            "source": str(DEFAULT_EPISODE_RESULT),
            "response_semantics": "HEURISTIC_SPEED_TRACE_NOT_ACTIVE_BRAKE_DETECTION",
        },
        "synthetic_feasibility_assumptions": {
            "stop_request_ms": STOP_REQUEST_MS,
            "normal_stop_ack_ms": 6400,
            "normal_clearance_ms": 8000,
            "normal_recover_request_ms": 8100,
            "normal_recover_ack_ms": 9000,
            "deadlines_ms": {
                "decelerate": DECEL_DEADLINE_MS,
                "stop": STOP_DEADLINE_MS,
                "recover": RECOVER_DEADLINE_MS,
            },
        },
        "claim_limit": (
            "Protocol model-checking feasibility only; synthetic phases are not "
            "evidence of vehicle-level safety or dataset behavior."
        ),
        "variants": [variant.__dict__ for variant in VARIANTS],
        "query_order": list(QUERIES),
        "expected_satisfaction": EXPECTED,
        "provenance": lineage,
    }
    (output_dir / "scene-0001-chained-profile.json").write_text(
        json.dumps(provenance, indent=2) + "\n", encoding="ascii"
    )
    training_manifest = {
        "schema_version": "1.0",
        "source_clip": "scene-0001",
        "policy": lineage["policy"],
        "positive_sequence_candidates": [
            {
                "sample_id": "scene-0001-source-trace-episode",
                "eligibility": "PASS_WITH_WEAK_RESPONSE_LABEL",
                "event_ids": [
                    event["event_id"]
                    for event in lineage["source_trace_episode"]["event_lineage"]
                ],
                "supervision": {
                    "sequence_order": "ENABLED",
                    "coc_decision_labels": "ENABLED",
                    "response_timing": "ENABLED_WITH_QUALITY_WEIGHT",
                    "raw_actuator_target": "DISABLED",
                },
                "source_coverage": 1.0,
            }
        ],
        "excluded_positive_sequences": [
            {
                "sample_id": "scene-0001-chained-four-phase",
                "eligibility": "FAIL",
                "source_coverage": 2 / 7,
                "reason": "Five of seven normal-path events are synthetic assumptions.",
                "allowed_role": "MODEL_CHECKING_AND_MUTATION_ONLY",
            }
        ],
        "hard_negative_templates": lineage["chained_four_phase"]["mutation_lineage"],
        "claim_limit": (
            "This manifest routes labels by provenance; it does not execute model "
            "fine-tuning or establish vehicle-level safety."
        ),
    }
    (output_dir / "scene-0001-training-manifest.json").write_text(
        json.dumps(training_manifest, indent=2) + "\n", encoding="ascii"
    )


if __name__ == "__main__":
    write_models()
