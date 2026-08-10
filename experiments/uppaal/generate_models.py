#!/usr/bin/env python3
"""Generate scene-0001 UPPAAL timed-automata mutation models."""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODEL_DIR = PROJECT_ROOT / "artifacts/intermediate/uppaal-models"
DEFAULT_EPISODE_RESULT = (
    PROJECT_ROOT / "artifacts/results/public/scene-0001/episode-check-result.json"
)


@dataclass(frozen=True)
class Variant:
    name: str
    deadline_ms: int
    emit_response: bool = True
    reset_on_repeat: bool = False
    overwrite_on_untrusted: bool = False


@dataclass(frozen=True)
class SceneProfile:
    trigger_us: int
    repeat_1_ms: int
    repeat_2_ms: int
    response_ms: int
    untrusted_ms: int


VARIANTS = (
    Variant("normal", 3000),
    Variant("deadline_2s", 2000),
    Variant("clock_reset", 3000, reset_on_repeat=True),
    Variant("no_response", 3000, emit_response=False),
    Variant("untrusted_overwrite", 3000, overwrite_on_untrusted=True),
)

QUERIES = (
    "E<> Obligation.Active",
    "E<> Obligation.Responded",
    "A[] not Reaction.DeadlineMiss",
    "A[] not clock_reset_violation",
    "A[] not untrusted_overwrite",
    "A[] not deadlock",
)

EXPECTED = {
    "normal": [True, True, True, True, True, True],
    "deadline_2s": [True, True, False, True, True, True],
    "clock_reset": [True, True, True, False, True, True],
    "no_response": [True, False, False, True, True, True],
    "untrusted_overwrite": [True, True, True, True, False, True],
}


def add_location(
    template: ET.Element,
    location_id: str,
    name: str,
    x: int,
    y: int,
    invariant: str | None = None,
) -> None:
    location = ET.SubElement(template, "location", {"id": location_id, "x": str(x), "y": str(y)})
    ET.SubElement(location, "name", {"x": str(x - 20), "y": str(y - 30)}).text = name
    if invariant:
        ET.SubElement(
            location,
            "label",
            {"kind": "invariant", "x": str(x - 20), "y": str(y + 20)},
        ).text = invariant


def add_transition(
    template: ET.Element,
    source: str,
    target: str,
    guard: str | None = None,
    sync: str | None = None,
    assignment: str | None = None,
) -> None:
    transition = ET.SubElement(template, "transition")
    ET.SubElement(transition, "source", {"ref": source})
    ET.SubElement(transition, "target", {"ref": target})
    y = 0
    for kind, value in (
        ("guard", guard),
        ("synchronisation", sync),
        ("assignment", assignment),
    ):
        if value:
            ET.SubElement(
                transition, "label", {"kind": kind, "x": "0", "y": str(y)}
            ).text = value
            y += 20


def add_template(root: ET.Element, name: str, declaration: str = "") -> ET.Element:
    template = ET.SubElement(root, "template")
    ET.SubElement(template, "name").text = name
    ET.SubElement(template, "declaration").text = declaration
    return template


def relative_ms(timestamp_us: int, trigger_us: int) -> int:
    return round((timestamp_us - trigger_us) / 1000)


def load_scene_profile(path: Path = DEFAULT_EPISODE_RESULT) -> SceneProfile:
    result = json.loads(path.read_text(encoding="utf-8"))
    obligation = result["obligations"]["SAFE_DISTANCE_TRUCK"]
    trigger_us = int(obligation["triggered_at_us"])
    repeats = sorted(int(value) for value in obligation["repeated_without_clock_reset_at_us"])
    if len(repeats) < 2:
        raise ValueError("UPPAAL feasibility model requires at least two repeated triggers")
    response_us = obligation["response_onset_us"]
    if response_us is None:
        raise ValueError("UPPAAL trace-replay model requires a heuristic response onset")
    untrusted = sorted(
        int(event["t0_us"])
        for event in result["episode"]["events"]
        if not event["quality_pass"] and int(event["t0_us"]) > trigger_us
    )
    if not untrusted:
        raise ValueError("UPPAAL feasibility model requires a later low-quality event")
    return SceneProfile(
        trigger_us=trigger_us,
        repeat_1_ms=relative_ms(repeats[0], trigger_us),
        repeat_2_ms=relative_ms(repeats[1], trigger_us),
        response_ms=relative_ms(int(response_us), trigger_us),
        untrusted_ms=relative_ms(untrusted[0], trigger_us),
    )


def build_model(variant: Variant, profile: SceneProfile) -> ET.ElementTree:
    nta = ET.Element("nta")
    declarations = f"""
// Time unit: milliseconds relative to the first trusted truck DECELERATE event.
const int RESPONSE_AT = {profile.response_ms};
const int REPEAT_1_AT = {profile.repeat_1_ms};
const int REPEAT_2_AT = {profile.repeat_2_ms};
const int UNTRUSTED_AT = {profile.untrusted_ms};
const int RESPONSE_DEADLINE = {variant.deadline_ms};
const bool EMIT_RESPONSE = {'true' if variant.emit_response else 'false'};
const bool RESET_ON_REPEAT = {'true' if variant.reset_on_repeat else 'false'};
const bool OVERWRITE_ON_UNTRUSTED = {'true' if variant.overwrite_on_untrusted else 'false'};

clock episode;
broadcast chan first_trigger, repeat_trigger, response, untrusted_event;
bool obligation_active = false;
bool obligation_responded = false;
bool clock_reset_violation = false;
bool untrusted_overwrite = false;
""".strip()
    ET.SubElement(nta, "declaration").text = declarations

    coc = add_template(nta, "CoCSource")
    add_location(coc, "c0", "BeforeFirst", 0, 0, "episode <= 0")
    add_location(coc, "c1", "BeforeRepeat1", 180, 0, "episode <= REPEAT_1_AT")
    add_location(coc, "c2", "BeforeRepeat2", 360, 0, "episode <= REPEAT_2_AT")
    add_location(coc, "c3", "BeforeUntrusted", 540, 0, "episode <= UNTRUSTED_AT")
    add_location(coc, "c4", "Done", 720, 0)
    ET.SubElement(coc, "init", {"ref": "c0"})
    add_transition(coc, "c0", "c1", "episode == 0", "first_trigger!")
    add_transition(coc, "c1", "c2", "episode == REPEAT_1_AT", "repeat_trigger!")
    add_transition(coc, "c2", "c3", "episode == REPEAT_2_AT", "repeat_trigger!")
    add_transition(coc, "c3", "c4", "episode == UNTRUSTED_AT", "untrusted_event!")
    # Intentional episode termination is represented by stuttering, not deadlock.
    add_transition(coc, "c4", "c4")

    ego = add_template(nta, "EgoTrace")
    wait_invariant = "episode <= RESPONSE_AT" if variant.emit_response else None
    add_location(ego, "e0", "Waiting", 0, 150, wait_invariant)
    add_location(ego, "e1", "ResponseObserved", 220, 150)
    ET.SubElement(ego, "init", {"ref": "e0"})
    if variant.emit_response:
        add_transition(ego, "e0", "e1", "episode == RESPONSE_AT", "response!")

    obligation = add_template(nta, "ObligationManager")
    add_location(obligation, "o0", "Idle", 0, 300)
    add_location(obligation, "o1", "Active", 220, 300)
    add_location(obligation, "o2", "Responded", 440, 300)
    ET.SubElement(obligation, "init", {"ref": "o0"})
    add_transition(
        obligation,
        "o0",
        "o1",
        sync="first_trigger?",
        assignment="obligation_active = true",
    )
    add_transition(
        obligation,
        "o1",
        "o2",
        sync="response?",
        assignment="obligation_active = false, obligation_responded = true",
    )

    reaction = add_template(nta, "ReactionObserver", "clock reaction;")
    add_location(reaction, "r0", "Idle", 0, 450)
    add_location(reaction, "r1", "Armed", 220, 450, "reaction <= RESPONSE_DEADLINE")
    add_location(reaction, "r2", "Done", 440, 400)
    add_location(reaction, "r3", "DeadlineMiss", 440, 520)
    ET.SubElement(reaction, "init", {"ref": "r0"})
    add_transition(reaction, "r0", "r1", sync="first_trigger?", assignment="reaction = 0")
    repeat_assignment = (
        "reaction = 0, clock_reset_violation = true"
        if variant.reset_on_repeat
        else None
    )
    add_transition(reaction, "r1", "r1", sync="repeat_trigger?", assignment=repeat_assignment)
    add_transition(reaction, "r1", "r2", sync="response?")
    add_transition(reaction, "r1", "r3", "reaction >= RESPONSE_DEADLINE")

    decision = add_template(nta, "DecisionValidator")
    add_location(decision, "d0", "Clean", 0, 650)
    ET.SubElement(decision, "init", {"ref": "d0"})
    add_transition(
        decision,
        "d0",
        "d0",
        sync="untrusted_event?",
        assignment="untrusted_overwrite = OVERWRITE_ON_UNTRUSTED",
    )

    ET.SubElement(nta, "system").text = """
CoC = CoCSource();
Ego = EgoTrace();
Obligation = ObligationManager();
Reaction = ReactionObserver();
Decision = DecisionValidator();
system CoC, Ego, Obligation, Reaction, Decision;
""".strip()
    return ET.ElementTree(nta)


def write_models(
    output_dir: Path = MODEL_DIR,
    episode_result: Path = DEFAULT_EPISODE_RESULT,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    profile = load_scene_profile(episode_result)
    query_path = output_dir / "scene-0001.q"
    query_path.write_text("\n".join(QUERIES) + "\n", encoding="ascii")
    for variant in VARIANTS:
        tree = build_model(variant, profile)
        ET.indent(tree, space="  ")
        path = output_dir / f"scene-0001-{variant.name}.xml"
        xml_bytes = ET.tostring(tree.getroot(), encoding="utf-8", xml_declaration=True)
        declaration, body = xml_bytes.split(b"\n", 1)
        doctype = (
            b"<!DOCTYPE nta PUBLIC '-//Uppaal Team//DTD Flat System 1.1//EN' "
            b"'http://www.it.uu.se/research/group/darts/uppaal/flat-1_2.dtd'>"
        )
        path.write_bytes(declaration + b"\n" + doctype + b"\n" + body + b"\n")
    (output_dir / "scene-profile.json").write_text(
        json.dumps(
            {
                **profile.__dict__,
                "source": str(episode_result),
                "time_unit": "milliseconds relative to trigger_us",
                "quantization": "round((timestamp_us - trigger_us) / 1000)",
                "response_semantics": "HEURISTIC_SPEED_TRACE_NOT_ACTIVE_BRAKE_DETECTION",
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (output_dir / "expected-results.json").write_text(
        json.dumps(
            {
                "query_order": list(QUERIES),
                "expected_satisfaction": EXPECTED,
                "interpretation": (
                    "Expected results are mutation-oracle targets and remain unverified "
                    "until verifyta executes with a valid license."
                ),
            },
            indent=2,
        )
        + "\n",
        encoding="ascii",
    )


if __name__ == "__main__":
    write_models()
