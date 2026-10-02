"""Exact-time CASCADE source witnesses, not inferred hazards or action gold."""

from __future__ import annotations

from decimal import Decimal
import math
import re
from typing import Any


BINDING_VERSION = "guardsynth-event-source-binding-v0.1"


def timestamp_us(value: Any) -> int | None:
    if value is None or value == "":
        return None
    if not isinstance(value, str) or not re.fullmatch(r"(?:[0-9]+:)?[0-9]+(?:\.[0-9]+)?", value):
        raise ValueError("invalid annotation timestamp")
    parts = value.split(":")
    seconds = Decimal(parts[-1])
    if len(parts) == 2:
        if seconds >= 60:
            raise ValueError("invalid seconds component")
        seconds += Decimal(parts[0]) * 60
    micros = seconds * 1_000_000
    if micros != micros.to_integral_value():
        raise ValueError("sub-microsecond annotation timestamp")
    return int(micros)


def interval(item: dict, event_us: int) -> dict:
    start = timestamp_us(item.get("start_timestamp", item.get("visibility_start_timestamp")))
    end = timestamp_us(item.get("end_timestamp", item.get("visibility_end_timestamp")))
    if start is not None and end is not None and end < start:
        raise ValueError("reversed annotation interval")
    available = start is not None and end is not None
    return {"start_us": start, "end_us": end,
            "contains_event": available and start <= event_us <= end,
            "event_on_boundary": available and event_us in (start, end),
            "status": "AVAILABLE" if available else "MISSING_INTERVAL"}


def source_index(annotation: dict, sha256: str, event_us: int) -> dict:
    result = {}

    def visit(value, path, owner, category, ancestors):
        if isinstance(value, dict):
            times = ancestors
            if any(k in value for k in ("start_timestamp", "end_timestamp", "visibility_start_timestamp", "visibility_end_timestamp")):
                times = ancestors + [interval(value, event_us)]
            identifier = value.get("id")
            if identifier:
                if identifier in result:
                    raise ValueError("duplicate source ID")
                result[identifier] = {"source_ref_id": identifier, "parent_entity_id": owner,
                    "source_category": category, "evidence_ref": f"sha256:{sha256}#{path}",
                    "interval": interval(value, event_us), "ancestor_intervals": times,
                    "active_at_event": bool(times) and all(t["contains_event"] for t in times)
                    and interval(value, event_us)["contains_event"], "value": value}
            for key, child in value.items():
                visit(child, f"{path}/{key}", owner, category, times)
        elif isinstance(value, list):
            for i, child in enumerate(value):
                visit(child, f"{path}/{i}", owner, category, ancestors)

    visit(annotation.get("ego_vehicle", {}), "/annotation/ego_vehicle", "EgoVehicle", "EGO", [])
    for key, category in (("agents", "ACTOR"), ("traffic_objects", "CONTROL"),
                          ("traffic_lights", "CONTROL"), ("environments", "ENVIRONMENT")):
        for i, entity in enumerate(annotation.get(key, [])):
            if not entity.get("id"):
                raise ValueError("source entity ID missing")
            visit(entity, f"/annotation/{key}/{i}", entity["id"], category, [])
    # A timed child alone cannot establish visibility of an untimed parent.
    for entry in result.values():
        if entry["source_category"] != "EGO":
            entry["active_at_event"] = entry["active_at_event"] and result[entry["parent_entity_id"]]["interval"]["contains_event"]
    return result


def witness(entry: dict) -> dict:
    return {k: v for k, v in entry.items() if k != "value"}


def bind_event(row: dict, payload: dict, annotation_sha256: str) -> dict:
    """Retain declared source intervals; no 500 ms widening or clock shifting."""
    t = row["event_timestamp_us"]
    if type(t) is not int or t < 0 or re.fullmatch(r"[0-9a-f]{64}", annotation_sha256) is None:
        raise ValueError("invalid binding input")
    if payload["video"]["clip_id"] != row["group_id"]:
        raise ValueError("annotation clip mismatch")
    duration = payload["video"]["duration_s"]
    if not math.isfinite(duration) or not 0 <= t <= duration * 1_000_000:
        raise ValueError("event outside annotation video")
    annotation = payload["annotation"]
    index = source_index(annotation, annotation_sha256, t)
    ego_actions, links, future_actions = [], [], []
    for action in annotation["ego_vehicle"].get("actions", []):
        entry = index[action["id"]]
        summary = {**witness(entry), "action_type": action.get("type"),
                   "source_illegal_flag": action.get("illegal_flag"), "action_gold": False}
        if not entry["active_at_event"]:
            if entry["interval"]["start_us"] is not None and entry["interval"]["start_us"] > t:
                future_actions.append({**summary, "offset_us": entry["interval"]["start_us"] - t,
                                       "usable_as_event_input": False})
            continue
        ego_actions.append(summary)
        for relation in ("because_of", "action_target"):
            refs = action.get(relation) or []
            if isinstance(refs, str):
                refs = [refs]
            for ref in dict.fromkeys(refs):
                target = index.get(ref)
                links.append({"ego_action_id": action["id"], "relation": relation,
                    "source_ref_id": ref, "relation_evidence_ref": entry["evidence_ref"] + "/" + relation,
                    "status": "UNRESOLVED" if target is None else
                        "ACTIVE_AT_DECLARED_EVENT" if target["active_at_event"] else "OUTSIDE_OR_MISSING_INTERVAL",
                    "target": None if target is None else witness(target)})
    targets = {link["source_ref_id"]: link["target"] for link in links
               if link["status"] == "ACTIVE_AT_DECLARED_EVENT"
               and link["target"]["source_category"] in {"ACTOR", "CONTROL"}}
    actors, controls, shared = [], [], []
    ego_containment = annotation["ego_vehicle"].get("containment") or []
    if isinstance(ego_containment, dict):
        ego_containment = [ego_containment]
    for entity in annotation.get("agents", []):
        owner = index[entity["id"]]
        if not owner["active_at_event"]:
            continue
        active_items = [e for e in index.values() if e["parent_entity_id"] == entity["id"] and e["active_at_event"]]
        actions = [{**witness(e), "action_type": e["value"]["action_type"]}
                   for e in active_items if "action_type" in e["value"]]
        signals = [{**witness(e), "signaling_details": e["value"]["signaling_details"],
                    "applicability_to_ego": "NOT_INDEPENDENTLY_CONFIRMED"}
                   for e in active_items if e["value"].get("property_type") == "Signal"
                   and e["value"].get("signaling_details")]
        controls.extend(signals)
        points = []
        for i, point in enumerate(entity.get("keypoints", [])):
            time = timestamp_us(point.get("timestamp"))
            x, y = point.get("x"), point.get("y")
            if time is None or any(type(v) not in (int, float) or not math.isfinite(v) or not 0 <= v <= 1 for v in (x, y)):
                raise ValueError("invalid normalized source keypoint")
            points.append({"timestamp_us": time, "offset_us": time - t, "x": x, "y": y,
                "evidence_ref": owner["evidence_ref"] + f"/keypoints/{i}",
                "event_time_location_available": time == t, "used_as_polygon_or_track": False,
                "usable_as_event_input": time == t})
        person = "pedestrian" in entity.get("type", "").lower() or "cycl" in entity.get("type", "").lower()
        actors.append({**witness(owner), "entity_type": entity.get("type"), "person_or_cyclist": person,
            "active_actions": actions, "active_signals": signals, "keypoints": points,
            "causally_linked_at_event": any(e["parent_entity_id"] == entity["id"] for e in targets.values()),
            "reviewer_identity_confirmed": False})
        containment = entity.get("containment") or []
        if isinstance(containment, dict):
            containment = [containment]
        for target_c in containment:
            for ego_c in ego_containment:
                env = index.get(target_c.get("env_id"))
                lane = str(target_c.get("lane_number") or "")
                if (interval(target_c, t)["contains_event"] and interval(ego_c, t)["contains_event"]
                    and env and env["active_at_event"] and env["source_category"] == "ENVIRONMENT"
                    and target_c.get("env_id") == ego_c.get("env_id")
                    and lane.lower() not in {"", "none", "unknown"} and lane == str(ego_c.get("lane_number"))):
                    shared.append({"target_entity_id": entity["id"], "environment_id": target_c["env_id"],
                        "lane_number": lane, "target_containment": target_c, "ego_containment": ego_c,
                        "conflict_geometry_established": False})
    for entry in index.values():
        value = entry["value"]
        if entry["source_category"] == "CONTROL" and entry["active_at_event"] and "color" in value:
            controls.append({**witness(entry), "color": value["color"],
                             "applicability_to_ego": "NOT_INDEPENDENTLY_CONFIRMED"})
    person_ids = [a["parent_entity_id"] for a in actors if a["person_or_cyclist"]]
    linked_person_ids = [a["parent_entity_id"] for a in actors if a["person_or_cyclist"] and a["causally_linked_at_event"]]
    transition = row["observation"]["visual_temporal_observation"] == "STATE_TRANSITION_VISIBLE"
    restrictive = [c for c in controls if c.get("color", "").lower() in {"red", "yellow"}
                   or c.get("signaling_details", {}).get("intent") in {"Stop", "Slow Down"}]
    if transition:
        route = "RELEASE_WITH_OTHER_CONTROL_CHECK" if restrictive else "RELEASE_TIME_BINDING_REQUIRED"
    elif controls or row["coc"]["mixed_work_or_control_context"]:
        route = "MIXED_CONTROL_OR_WORK_CONTEXT"
    elif person_ids:
        route = "PERSON_INTERACTION_CONFLICT_UNCONFIRMED"
    else:
        route = "NO_ACTIVE_PERSON_SOURCE"
    return {
        "binding_version": BINDING_VERSION, "candidate_digest": row["candidate_digest"],
        "review_index": row["review_index"], "group_id": row["group_id"], "upstream_split": row["upstream_split"],
        "event_timestamp_us": t, "annotation_sha256": annotation_sha256,
        "annotation_provenance": payload.get("provenance"), "annotation_status": payload.get("status"),
        "coc": row["coc"], "prior_observation": row["observation"], "prior_evidence_refs": row["evidence_refs"],
        "time_policy": "DECLARED_CLOSED_INTERVAL_ZERO_TOLERANCE_NO_SHIFT_NO_INTERPOLATION",
        "cross_dataset_clock_alignment": "EXISTING_EVENT_ANCHOR_NOT_INDEPENDENTLY_REVALIDATED",
        "active_ego_actions": ego_actions, "event_causal_links": links,
        "active_source_targets": list(targets.values()), "active_actors": actors,
        "active_control_annotations": controls, "shared_lane_relations": shared,
        "future_ego_actions_context_only": sorted(future_actions, key=lambda a: a["offset_us"]),
        "source_linked_person_ids": linked_person_ids, "visible_person_source_ids": person_ids,
        "unique_source_linked_person_id": linked_person_ids[0] if len(linked_person_ids) == 1 else None,
        "previous_window_target_ids": sorted({r["source_ref_id"] for r in row["structured_target_candidates"]}),
        "clause_route": route, "release_control_check_required": transition and bool(restrictive),
        "event_hazard_truth": "UNKNOWN", "selected_action_gold": None,
        "semantic_conflict_zone": None, "metric_parameters": None,
        "eblc_status": "NOT_GENERATED_SOURCE_AND_OPERATIONAL_CLAUSE_PENDING", "sat_status": "NOT_RUN",
        "learning_export_allowed": False, "repeat_existing_survey_requested": False,
        "claim_scope": "PINNED_ANNOTATION_WITNESSES_NOT_INDEPENDENT_TRUTH_OR_NORMATIVE_ACTION_GOLD",
    }
