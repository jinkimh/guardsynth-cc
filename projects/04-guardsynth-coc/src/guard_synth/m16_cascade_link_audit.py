"""Audit source-linked CASCADE relations and optional containment for M16."""

from __future__ import annotations

from collections import Counter
from copy import deepcopy
import re
from typing import Any, Mapping


CASCADE_LINK_AUDIT_VERSION = "guardsynth-m16-cascade-structured-link-audit-v0.1"
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_SLICES = {
    "PEDESTRIAN_CYCLIST_YIELD",
    "STOP_SIGNALS",
    "FOLLOWING_CUT_IN",
}


def _timestamp_us(value: Any) -> int | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        if ":" in value:
            minutes, seconds = value.split(":", 1)
            return round((int(minutes) * 60 + float(seconds)) * 1_000_000)
        return round(float(value) * 1_000_000)
    except ValueError:
        return None


def _active(item: Mapping[str, Any], event_timestamp_us: int) -> bool:
    start = _timestamp_us(
        item.get("start_timestamp", item.get("visibility_start_timestamp"))
    )
    end = _timestamp_us(
        item.get("end_timestamp", item.get("visibility_end_timestamp"))
    )
    return (
        start is not None
        and end is not None
        and start - 500_000 <= event_timestamp_us <= end + 500_000
    )


def _index_source_ids(
    annotation: Mapping[str, Any],
) -> tuple[dict[str, Mapping[str, Any]], dict[str, tuple[str, str]]]:
    index: dict[str, Mapping[str, Any]] = {}
    parent: dict[str, tuple[str, str]] = {}

    def visit(value: Any, category: str, parent_id: str) -> None:
        if isinstance(value, Mapping):
            identifier = value.get("id")
            current_parent = parent_id
            if isinstance(identifier, str) and identifier:
                if identifier in index:
                    raise ValueError("CASCADE_DUPLICATE_SOURCE_ID")
                index[identifier] = value
                parent[identifier] = (category, parent_id or identifier)
                if not parent_id:
                    current_parent = identifier
            for child in value.values():
                visit(child, category, current_parent)
        elif isinstance(value, list):
            for child in value:
                visit(child, category, parent_id)

    for key, category in (
        ("agents", "ACTOR"),
        ("traffic_objects", "CONTROL"),
        ("traffic_lights", "CONTROL"),
        ("environments", "ENVIRONMENT"),
    ):
        for entity in annotation.get(key, ()):
            if isinstance(entity, Mapping):
                identifier = entity.get("id")
                visit(
                    entity,
                    category,
                    identifier if isinstance(identifier, str) else "",
                )
    return index, parent


def _active_containment(
    owner: Mapping[str, Any],
    event_timestamp_us: int,
    active_environment_ids: set[str],
) -> set[tuple[str, str]]:
    items = owner.get("containment") or ()
    if isinstance(items, Mapping):
        items = (items,)
    result: set[tuple[str, str]] = set()
    for item in items:
        if not isinstance(item, Mapping) or not _active(item, event_timestamp_us):
            continue
        environment = item.get("env_id")
        lane = str(item.get("lane_number", ""))
        if (
            isinstance(environment, str)
            and environment in active_environment_ids
            and lane.lower() not in {"", "none", "unknown"}
        ):
            result.add((environment, lane))
    return result


def audit_cascade_event_links(
    *,
    annotation: Mapping[str, Any],
    event_timestamp_us: int,
    scene_slice: str,
    annotation_sha256: str,
) -> dict[str, Any]:
    """Use only schema-defined causal/target and containment links at one event."""
    if (
        isinstance(event_timestamp_us, bool)
        or not isinstance(event_timestamp_us, int)
        or scene_slice not in _SLICES
        or _SHA256_RE.fullmatch(annotation_sha256) is None
    ):
        raise ValueError("CASCADE_LINK_AUDIT_INPUT_INVALID")
    ego = annotation.get("ego_vehicle")
    if not isinstance(ego, Mapping):
        raise ValueError("CASCADE_EGO_VEHICLE_MISSING")

    source_index, source_parent = _index_source_ids(annotation)
    active_ego_actions = [
        item
        for item in ego.get("actions", ())
        if isinstance(item, Mapping) and _active(item, event_timestamp_us)
    ]
    direct_links: list[tuple[str, str, str]] = []
    for action in active_ego_actions:
        action_id = str(action.get("id", ""))
        for relation in ("action_target", "because_of"):
            references = action.get(relation) or ()
            if isinstance(references, str):
                references = (references,)
            for reference in references:
                if isinstance(reference, str) and reference:
                    direct_links.append((action_id, relation, reference))
    direct_links = list(dict.fromkeys(direct_links))
    unresolved = sorted({reference for _, _, reference in direct_links if reference not in source_index})
    active_references = sorted({
        reference
        for _, _, reference in direct_links
        if reference in source_index and _active(source_index[reference], event_timestamp_us)
    })
    active_targets = [
        {
            "source_ref_id": reference,
            "source_category": source_parent[reference][0],
            "parent_entity_id": source_parent[reference][1],
        }
        for reference in active_references
        if source_parent[reference][0] in {"ACTOR", "CONTROL"}
    ]
    if unresolved:
        state_status = "CONFLICT_UNRESOLVED_SOURCE_LINK"
    elif active_targets:
        state_status = "AVAILABLE_SOURCE_LINKED_SET"
    elif direct_links:
        state_status = "REVIEW_REQUIRED_CAUSAL_REFS_OUTSIDE_EVENT_WINDOW"
    else:
        state_status = "REVIEW_REQUIRED_NO_ACTIVE_EGO_RELATION_LINK"

    environments = {
        item.get("id"): item
        for item in annotation.get("environments", ())
        if isinstance(item, Mapping)
        and isinstance(item.get("id"), str)
        and _active(item, event_timestamp_us)
    }
    containment_by_owner: dict[str, set[tuple[str, str]]] = {
        "EgoVehicle": _active_containment(
            ego, event_timestamp_us, set(environments)
        )
    }
    for key in ("agents", "traffic_objects", "traffic_lights"):
        for entity in annotation.get(key, ()):
            if not isinstance(entity, Mapping) or not isinstance(entity.get("id"), str):
                continue
            containment_by_owner[entity["id"]] = _active_containment(
                entity, event_timestamp_us, set(environments)
            )
    target_ids = sorted({item["parent_entity_id"] for item in active_targets})
    shared = {
        target: sorted(
            containment_by_owner.get("EgoVehicle", set())
            & containment_by_owner.get(target, set())
        )
        for target in target_ids
    }
    shared = {key: value for key, value in shared.items() if value}
    containment_complete = (
        state_status == "AVAILABLE_SOURCE_LINKED_SET"
        and bool(target_ids)
        and set(shared) == set(target_ids)
    )
    association_status = (
        "AVAILABLE_SOURCE_LINKED_CONTAINMENT_SET"
        if containment_complete
        else "REVIEW_REQUIRED_SOURCE_GEOMETRY"
    )
    return {
        "audit_version": CASCADE_LINK_AUDIT_VERSION,
        "annotation_sha256": annotation_sha256,
        "event_timestamp_us": event_timestamp_us,
        "slice": scene_slice,
        "active_ego_action_ids": [str(item.get("id", "")) for item in active_ego_actions],
        "direct_source_links": [
            {"ego_action_id": action, "relation": relation, "source_ref_id": reference}
            for action, relation, reference in direct_links
        ],
        "active_source_targets": active_targets,
        "unresolved_source_link_ids": unresolved,
        "unresolved_source_link_count": len(unresolved),
        "active_source_target_count": len(active_targets),
        "active_environment_count": len(environments),
        "valid_ego_containment_count": len(containment_by_owner["EgoVehicle"]),
        "shared_lane_or_zone_target_count": len(shared),
        "shared_lane_or_zone_relations": shared,
        "relevant_actor_or_control_state_status": state_status,
        "target_zone_or_lane_association_status": association_status,
        "conflict_stop_or_following_geometry_status": "REVIEW_REQUIRED_SOURCE_GEOMETRY",
        "source_interpretation": (
            "CASCADE_SCHEMA_DEFINED_EGO_RELATION_AND_OPTIONAL_CONTAINMENT_ONLY"
        ),
        "human_video_observation_used_as_source": False,
        "claim_scope": (
            "STRUCTURED_ANNOTATION_LINK_AUDIT_NOT_UNANNOTATED_GEOMETRY_RULE_OR_SAFETY"
        ),
    }


def apply_cascade_link_audit(
    prior_audit: dict[str, Any], event_audits: Mapping[str, dict[str, Any]]
) -> dict[str, Any]:
    """Apply exact structured-link closures without changing unrelated fields."""
    result = deepcopy(prior_audit)
    records = result.get("records")
    if not isinstance(records, list):
        raise ValueError("PRIOR_EVENT_ANCHOR_AUDIT_RECORDS_INVALID")
    expected = [item.get("candidate_digest") for item in records]
    if (
        len(expected) != result.get("classified_event_count")
        or len(expected) != len(set(expected))
        or set(expected) != set(event_audits)
    ):
        raise ValueError("CASCADE_LINK_AUDIT_EVENT_SET_MISMATCH")

    state_closed = 0
    association_closed = 0
    status_counts: Counter[str] = Counter()
    for record in records:
        audit = event_audits[record["candidate_digest"]]
        record["cascade_structured_link_audit"] = audit
        state_status = audit["relevant_actor_or_control_state_status"]
        association_status = audit["target_zone_or_lane_association_status"]
        status_counts[state_status] += 1
        if state_status == "AVAILABLE_SOURCE_LINKED_SET":
            record["field_status"]["relevant_actor_or_control_state"] = (
                "AVAILABLE_SOURCE_LINKED"
            )
            state_closed += 1
        if association_status == "AVAILABLE_SOURCE_LINKED_CONTAINMENT_SET":
            record["field_status"]["target_zone_or_lane_association"] = (
                "AVAILABLE_SOURCE_LINKED"
            )
            association_closed += 1
        record["source_complete"] = False
        record["eligible"] = False
    total = len(records)
    remaining = dict(result["remaining_field_event_counts"])
    remaining["relevant_actor_or_control_state"] = total - state_closed
    remaining["target_zone_or_lane_association"] = total - association_closed
    result.update({
        "status": "CURATOR_STRUCTURED_LINKS_AUDITED_REMAINING_SOURCE_EVIDENCE_REQUIRED",
        "cascade_annotation_hash_verified_count": total,
        "relevant_actor_or_control_state_closed_count": state_closed,
        "target_zone_or_lane_association_closed_count": association_closed,
        "structured_link_status_counts": dict(sorted(status_counts.items())),
        "remaining_field_event_counts": remaining,
        "source_complete_8_of_8_count": 0,
        "newly_eligible_scene_count": 0,
        "records": records,
    })
    return result


def public_cascade_link_audit_summary(audit: dict[str, Any]) -> dict[str, Any]:
    """Remove restricted per-event source links and identifiers."""
    return {key: value for key, value in audit.items() if key != "records"}
