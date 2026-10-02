"""Privacy-safe inventory for the scene-grounded simulation-24 work package."""

from __future__ import annotations

import hashlib
from typing import Any


REQUIRED_SCENE_FIELDS = (
    "timestamps",
    "ego_pose_and_speed",
    "relevant_actor_tracks",
    "target_zone_or_lane_association",
    "conflict_or_stop_geometry",
    "verified_coordinate_transform",
    "applicable_rule_source_refs",
    "exact_vehicle_binding",
)


def _private_ref(kind: str, value: object) -> str:
    digest = hashlib.sha256(f"{kind}:{value}".encode("utf-8")).hexdigest()
    return f"candidate-sha256:{digest}"


def _adapter_fields(candidate: dict[str, Any]) -> set[str]:
    fields: set[str] = set()
    graph = candidate.get("context_graph", {})
    if isinstance(graph.get("timestamp_s"), (int, float)):
        fields.add("timestamps")
    if candidate.get("ego_state") and isinstance(graph.get("ego_speed_mps"), (int, float)):
        fields.add("ego_pose_and_speed")
    actors = candidate.get("association_candidates", [])
    if actors and all(actor.get("track_samples") for actor in actors):
        fields.add("relevant_actor_tracks")
    if candidate.get("conflict_zone") and isinstance(graph.get("zone_entry_x_m"), (int, float)):
        fields.add("conflict_or_stop_geometry")
    return fields


def build_scene_candidate_inventory(
    partial_packets: dict[str, Any],
    adapter_result: dict[str, Any],
    calibration_audit: dict[str, Any],
    *,
    event_closures: list[dict[str, Any]] | tuple[dict[str, Any], ...] = (),
) -> dict[str, Any]:
    """Merge overlapping review/adapter evidence without exposing scene identifiers."""
    packets = partial_packets.get("packets")
    candidates = adapter_result.get("candidates")
    if not isinstance(packets, list) or not isinstance(candidates, list):
        raise ValueError("INVALID_CANDIDATE_COLLECTION")

    selected_packet = calibration_audit.get("packet_id")
    matching_packets = [packet for packet in packets if packet.get("packet_id") == selected_packet]
    if len(matching_packets) != 1:
        raise ValueError("CALIBRATION_PACKET_MATCH_NOT_UNIQUE")
    evidence_ref = calibration_audit.get("field_status", {}).get(
        "conflict_or_stop_geometry", {}
    ).get("evidence_ref", "")
    marker = "#/candidates/"
    if marker not in evidence_ref:
        raise ValueError("CALIBRATION_ADAPTER_CANDIDATE_NOT_IDENTIFIED")
    try:
        selected_index = int(evidence_ref.split(marker, 1)[1].split("/", 1)[0])
        candidates[selected_index]
    except (IndexError, TypeError, ValueError) as exc:
        raise ValueError("CALIBRATION_ADAPTER_CANDIDATE_INVALID") from exc

    required = set(REQUIRED_SCENE_FIELDS)
    closures_by_index: dict[int, dict[str, Any]] = {}
    for closure in event_closures:
        index = closure.get("adapter_candidate_index")
        if (
            isinstance(index, bool)
            or not isinstance(index, int)
            or index < 0
            or index >= len(candidates)
            or index in closures_by_index
        ):
            raise ValueError("EVENT_CLOSURE_ADAPTER_CANDIDATE_INVALID")
        if closure.get("synthesized_required_values"):
            raise ValueError("EVENT_CLOSURE_CONTAINS_SYNTHETIC_SCENE_FILL")
        closures_by_index[index] = closure
    entries: list[dict[str, Any]] = []
    for index, candidate in enumerate(candidates):
        available = _adapter_fields(candidate)
        evidence_classes = ["DERIVED_ADAPTER"]
        if index in closures_by_index:
            available = required.intersection(
                closures_by_index[index].get("available_fields", ())
            )
            evidence_classes.append("DERIVED_EVENT_SOURCE_CLOSURE")
        if index == selected_index:
            available = required.intersection(calibration_audit.get("available_fields", ()))
            evidence_classes.extend(("IMAGE_REVIEW", "CALIBRATION_SOURCE_AUDIT"))
        missing = required - available
        entries.append({
            "candidate_ref": _private_ref("adapter", candidate.get("candidate_id", index)),
            "evidence_classes": evidence_classes,
            "available_scene_fields": sorted(available),
            "missing_scene_fields": sorted(missing),
            "scene_field_count": len(available),
            "simulation_projection_ready": not missing,
            "candidate_slice_hints": ["PEDESTRIAN_CYCLIST_YIELD"],
        })

    for packet in packets:
        if packet.get("packet_id") == selected_packet:
            continue
        closure = packet.get("source_closure", {})
        missing_from_packet = set(closure.get("missing_fields", ()))
        available = required - missing_from_packet
        missing = required - available
        entries.append({
            "candidate_ref": _private_ref("review", packet.get("packet_id")),
            "evidence_classes": ["IMAGE_REVIEW"],
            "available_scene_fields": sorted(available),
            "missing_scene_fields": sorted(missing),
            "scene_field_count": len(available),
            "simulation_projection_ready": not missing,
            "candidate_slice_hints": list(
                packet.get("selection_hints", {}).get("candidate_slices", ())
            ),
        })

    entries.sort(key=lambda item: item["candidate_ref"])
    ready = sum(item["simulation_projection_ready"] for item in entries)
    return {
        "inventory_version": "guardsynth-sim24-candidate-inventory-v0.1",
        "required_scene_fields": list(REQUIRED_SCENE_FIELDS),
        "candidate_count": len(entries),
        "simulation_projection_ready_count": ready,
        "additional_ready_candidates_needed": max(0, 24 - ready),
        "raw_identifiers_included": False,
        "synthetic_scene_fill_performed": False,
        "candidates": entries,
        "decision": (
            "READY_FOR_24_SCENE_BATCH"
            if ready >= 24
            else "CONTINUE_SOURCE_AUTHORING"
        ),
        "claim_scope": "SCENE_SOURCE_INVENTORY_NOT_VEHICLE_SAFETY_OR_SCENE_ACCURACY",
    }
