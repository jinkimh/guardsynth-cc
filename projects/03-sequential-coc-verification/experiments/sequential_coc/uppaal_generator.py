"""Generate deterministic UPPAAL observers from the common CoC IR."""

from __future__ import annotations

import os
from pathlib import Path
import xml.etree.ElementTree as ET

from experiments.sequential_coc.contract_ir import Action, ContractEvent
from experiments.sequential_coc.event_local_checker import (
    _CONTRADICTION_ORDER,
    _validated_events,
)
from experiments.sequential_coc.stateful_checker import (
    transition_rule_description,
    transition_table_sha256,
)


_ACTION_CODE = {
    Action.STOP_OR_HOLD: 0,
    Action.YIELD_OR_DECELERATE: 1,
    Action.ACCELERATE_OR_PROCEED: 2,
    Action.MAINTAIN_SPEED: 3,
}
_FLAG_NAME = {
    "HOLD_GO_CONFLICT": "sticky_hold_go_conflict",
    "PREMATURE_RELEASE": "sticky_premature_release",
    "ORDER_VIOLATION": "sticky_order_violation",
    "STALE_OBLIGATION": "sticky_stale_obligation",
}
_DOCTYPE = (
    b'<!DOCTYPE nta PUBLIC "-//Uppaal Team//DTD Flat System 1.1//EN" '
    b'"http://www.it.uu.se/research/group/darts/uppaal/flat-1_2.dtd">\n'
)


def _c_array(values: list[int | bool]) -> str:
    rendered = [
        "true" if value is True else "false" if value is False else str(value)
        for value in values
    ]
    return "{" + ", ".join(rendered) + "}"


def _padded(values: list[int | bool], fallback: int | bool) -> list[int | bool]:
    return values if values else [fallback]


def _target_codes(events: list[ContractEvent]) -> list[int]:
    identities: dict[str, int] = {}
    encoded: list[int] = []
    for item in events:
        if item.target is None:
            encoded.append(0)
        else:
            if item.target not in identities:
                identities[item.target] = len(identities) + 1
            encoded.append(identities[item.target])
    return encoded


def _declaration(events: list[ContractEvent]) -> str:
    count = len(events)
    capacity = max(1, count)
    description = transition_rule_description()
    actions = _padded([_ACTION_CODE[item.action] for item in events], 3)
    targets = _padded(_target_codes(events), 0)
    satisfaction_known = _padded(
        [item.satisfaction_known for item in events], False
    )
    satisfaction_value = _padded(
        [item.satisfaction_value for item in events], False
    )
    release_known = _padded([item.release_known for item in events], False)
    release_value = _padded([item.release_value for item in events], False)
    parse_unknown = _padded(
        [item.parse_status.startswith("UNKNOWN") for item in events], False
    )
    return f"""
// transition_contract_version={description['version']}
// transition_contract_sha256={transition_table_sha256()}
// UNKNOWN evidence is represented only by known=false,value=false.
const int STOP_OR_HOLD = 0;
const int YIELD_OR_DECELERATE = 1;
const int ACCELERATE_OR_PROCEED = 2;
const int MAINTAIN_SPEED = 3;
const int INACTIVE = 0;
const int ACTIVE = 1;
const int SATISFIED_WAIT_RELEASE = 2;
const int RELEASED = 3;
const int VIOLATED = 4;
const int UNKNOWN = 5;
const int EVENT_COUNT = {count};
const int event_action[{capacity}] = {_c_array(actions)};
const int event_target[{capacity}] = {_c_array(targets)};
const bool satisfaction_known[{capacity}] = {_c_array(satisfaction_known)};
const bool satisfaction_value[{capacity}] = {_c_array(satisfaction_value)};
const bool release_known[{capacity}] = {_c_array(release_known)};
const bool release_value[{capacity}] = {_c_array(release_value)};
const bool parse_unknown[{capacity}] = {_c_array(parse_unknown)};
int[0,{capacity}] idx = 0;
int[-1,{capacity}] first_violation_idx = -1;
int[0,5] observer_state = INACTIVE;
bool active = false;
int[0,3] active_action = MAINTAIN_SPEED;
int[0,{max(1, len(set(targets)))}] active_target = 0;
bool active_satisfaction_known = false;
bool active_satisfaction_value = false;
bool active_release_known = false;
bool active_release_value = false;
bool sticky_hold_go_conflict = false;
bool sticky_premature_release = false;
bool sticky_order_violation = false;
bool sticky_stale_obligation = false;
bool sticky_unknown = false;
bool sticky_parse_status_unknown = false;
bool sticky_overlapping_obligation = false;
bool sticky_stale_release_unknown = false;
bool sticky_active_release_unknown = false;
bool sticky_active_satisfaction_unknown = false;

void remember_first_violation() {{
  if (first_violation_idx == -1)
    first_violation_idx = idx;
}}

void step() {{
  bool event_violation = false;
  bool same_obligation = false;
  int action = event_action[idx];

  if (parse_unknown[idx]) {{
    sticky_unknown = true;
    sticky_parse_status_unknown = true;
    observer_state = UNKNOWN;
  }}

  if (action == STOP_OR_HOLD || action == YIELD_OR_DECELERATE) {{
    if (!active) {{
      if (release_known[idx] && release_value[idx]) {{
        observer_state = RELEASED;
      }} else {{
        active = true;
        active_action = action;
        active_target = event_target[idx];
        active_satisfaction_known = satisfaction_known[idx];
        active_satisfaction_value = satisfaction_value[idx];
        active_release_known = release_known[idx];
        active_release_value = release_value[idx];
        if (active_satisfaction_known && active_satisfaction_value)
          observer_state = SATISFIED_WAIT_RELEASE;
        else
          observer_state = ACTIVE;
      }}
    }} else {{
      same_obligation = active_action == action && active_target == event_target[idx];
      if (!same_obligation) {{
        sticky_unknown = true;
        sticky_overlapping_obligation = true;
        observer_state = UNKNOWN;
      }} else {{
        if (satisfaction_known[idx]) {{
          active_satisfaction_known = true;
          active_satisfaction_value = satisfaction_value[idx];
        }}
        if (release_known[idx]) {{
          active_release_known = true;
          active_release_value = release_value[idx];
        }}
        if (active_release_known && active_release_value) {{
          sticky_stale_obligation = true;
          event_violation = true;
          observer_state = VIOLATED;
        }} else if (!active_release_known) {{
          sticky_unknown = true;
          sticky_stale_release_unknown = true;
          observer_state = UNKNOWN;
        }} else if (active_satisfaction_known && active_satisfaction_value) {{
          observer_state = SATISFIED_WAIT_RELEASE;
        }} else {{
          observer_state = ACTIVE;
        }}
      }}
    }}
  }} else if (action == ACCELERATE_OR_PROCEED) {{
    if (!active) {{
      if (release_known[idx] && !release_value[idx]) {{
        sticky_premature_release = true;
        event_violation = true;
      }}
      if (satisfaction_known[idx] && !satisfaction_value[idx]) {{
        sticky_order_violation = true;
        event_violation = true;
      }}
      if (event_violation)
        observer_state = VIOLATED;
      else
        observer_state = INACTIVE;
    }} else {{
      if (satisfaction_known[idx]) {{
        active_satisfaction_known = true;
        active_satisfaction_value = satisfaction_value[idx];
      }}
      if (release_known[idx]) {{
        active_release_known = true;
        active_release_value = release_value[idx];
      }}
      if (release_known[idx] && !release_value[idx]) {{
        sticky_premature_release = true;
        event_violation = true;
      }} else if (active_release_known && !active_release_value) {{
        sticky_hold_go_conflict = true;
        event_violation = true;
      }}
      if (active_satisfaction_known && !active_satisfaction_value) {{
        sticky_order_violation = true;
        event_violation = true;
      }}
      if (event_violation) {{
        observer_state = VIOLATED;
      }} else if (!active_release_known || !active_satisfaction_known) {{
        sticky_unknown = true;
        if (!active_release_known)
          sticky_active_release_unknown = true;
        if (!active_satisfaction_known)
          sticky_active_satisfaction_unknown = true;
        observer_state = UNKNOWN;
      }} else {{
        active = false;
        observer_state = RELEASED;
      }}
    }}
  }} else {{
    if (!active) {{
      observer_state = INACTIVE;
    }} else {{
      if (satisfaction_known[idx]) {{
        active_satisfaction_known = true;
        active_satisfaction_value = satisfaction_value[idx];
      }}
      if (release_known[idx]) {{
        active_release_known = true;
        active_release_value = release_value[idx];
      }}
      if (active_release_known && active_release_value) {{
        active = false;
        observer_state = RELEASED;
      }} else if (!active_release_known) {{
        sticky_unknown = true;
        sticky_active_release_unknown = true;
        observer_state = UNKNOWN;
      }} else if (active_satisfaction_known && active_satisfaction_value) {{
        observer_state = SATISFIED_WAIT_RELEASE;
      }} else {{
        observer_state = ACTIVE;
      }}
    }}
  }}

  if (event_violation)
    remember_first_violation();
  if (sticky_hold_go_conflict || sticky_premature_release ||
      sticky_order_violation || sticky_stale_obligation)
    observer_state = VIOLATED;
  else if (parse_unknown[idx])
    observer_state = UNKNOWN;
}}
""".strip()


def _add_location(template: ET.Element, identifier: str, name: str, x: int) -> ET.Element:
    location = ET.SubElement(template, "location", {"id": identifier, "x": str(x), "y": "0"})
    ET.SubElement(location, "name", {"x": str(x), "y": "-30"}).text = name
    return location


def build_uppaal_model(
    events: list[ContractEvent],
) -> tuple[ET.ElementTree, list[str]]:
    """Build one finite observer after applying checker-identical validation."""
    _validated_events(events)
    root = ET.Element("nta")
    ET.SubElement(root, "declaration").text = _declaration(events)
    template = ET.SubElement(root, "template")
    ET.SubElement(template, "name").text = "ObserverTemplate"
    run = _add_location(template, "run", "Run", 0)
    for index, item in enumerate(events):
        ET.SubElement(
            run,
            "label",
            {"kind": "comments", "x": "0", "y": str(30 + index * 15)},
        ).text = f"event[{index}]={item.event_id}"
    ET.SubElement(run, "committed")
    _add_location(template, "done", "Done", 240)
    ET.SubElement(template, "init", {"ref": "run"})

    consume = ET.SubElement(template, "transition")
    ET.SubElement(consume, "source", {"ref": "run"})
    ET.SubElement(consume, "target", {"ref": "run"})
    ET.SubElement(consume, "label", {"kind": "guard", "x": "40", "y": "30"}).text = "idx < EVENT_COUNT"
    ET.SubElement(consume, "label", {"kind": "assignment", "x": "40", "y": "50"}).text = "step(), idx++"

    finish = ET.SubElement(template, "transition")
    ET.SubElement(finish, "source", {"ref": "run"})
    ET.SubElement(finish, "target", {"ref": "done"})
    ET.SubElement(finish, "label", {"kind": "guard", "x": "100", "y": "-20"}).text = "idx == EVENT_COUNT"

    ET.SubElement(root, "system").text = (
        "Observer = ObserverTemplate();\nsystem Observer;"
    )
    queries = [_FLAG_NAME[kind.value] for kind in _CONTRADICTION_ORDER]
    queries = [f"A[] not {flag}" for flag in queries]
    queries.extend(("A[] not sticky_unknown", "A<> Observer.Done"))
    return ET.ElementTree(root), queries


def serialize_uppaal_model(tree: ET.ElementTree) -> bytes:
    """Return a stable UTF-8 representation without mutating the input tree."""
    if not isinstance(tree, ET.ElementTree) or tree.getroot().tag != "nta":
        raise TypeError("tree must be an UPPAAL nta ElementTree")
    payload = ET.tostring(tree.getroot(), encoding="utf-8", xml_declaration=True)
    declaration_end = payload.find(b"?>") + 2
    return payload[:declaration_end] + b"\n" + _DOCTYPE + payload[declaration_end:] + b"\n"


def write_uppaal_artifacts(
    tree: ET.ElementTree,
    queries: list[str],
    model_path: Path,
    query_path: Path,
) -> None:
    """Write deterministic model/query artifacts to explicit caller paths."""
    model_path = Path(model_path)
    query_path = Path(query_path)
    if model_path == query_path:
        raise ValueError("model_path and query_path must differ")
    model_path.parent.mkdir(parents=True, exist_ok=True)
    query_path.parent.mkdir(parents=True, exist_ok=True)
    model_path.write_bytes(serialize_uppaal_model(tree))
    query_path.write_text("\n".join(queries) + "\n", encoding="utf-8")
    os.chmod(model_path, 0o600)
    os.chmod(query_path, 0o600)
