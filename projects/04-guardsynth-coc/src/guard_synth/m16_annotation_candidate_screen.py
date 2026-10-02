"""Deterministic, fail-closed M16 screening of CASCADE annotations."""

from __future__ import annotations

from collections import Counter
import hashlib
import re
from typing import Any, Iterable


SCREEN_VERSION = "guardsynth-m16-annotation-candidate-screen-v0.1"
SENSOR_REVIEW_STATUS = "REVIEW_REQUIRED_SENSOR_VALIDATION"
_SLICES = (
    "PEDESTRIAN_CYCLIST_YIELD",
    "STOP_SIGNALS",
    "FOLLOWING_CUT_IN",
)
_VULNERABLE_TOKENS = (
    "pedestrian",
    "bicycle",
    "cyclist",
    "wheelchair",
    "scooter",
)
_VEHICLE_TOKENS = (
    "car",
    "truck",
    "vehicle",
    "bus",
    "motorcycle",
)
_FOLLOWING_ACTION_TOKENS = (
    "followroaduser",
    "changelane",
    "nudge",
    "overtake",
    "enter",
)
_STOP_CONTROL_TOKENS = ("stopsign", "yieldsign")


def parse_cascade_timestamp_us(value: Any) -> int | None:
    """Parse CASCADE ``minutes:seconds`` timestamps into microseconds."""
    if value in {None, ""}:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return round(float(value) * 1_000_000)
    match = re.fullmatch(r"\s*(\d+):(\d+(?:\.\d+)?)\s*", str(value))
    if match is None:
        return None
    return round((int(match.group(1)) * 60 + float(match.group(2))) * 1_000_000)


def _normalized(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value).lower())


def _contains(value: Any, tokens: tuple[str, ...]) -> bool:
    normalized = _normalized(value)
    return any(token in normalized for token in tokens)


def _active(
    item: dict[str, Any],
    event_timestamp_us: int,
    *,
    start_key: str = "start_timestamp",
    end_key: str = "end_timestamp",
    tolerance_us: int = 500_000,
) -> bool:
    start = parse_cascade_timestamp_us(item.get(start_key))
    end = parse_cascade_timestamp_us(item.get(end_key))
    if start is None and end is None:
        return True
    if start is None:
        start = end
    if end is None:
        end = start
    assert start is not None and end is not None
    return start - tolerance_us <= event_timestamp_us <= end + tolerance_us


def _visible(item: dict[str, Any], event_timestamp_us: int) -> bool:
    return _active(
        item,
        event_timestamp_us,
        start_key="visibility_start_timestamp",
        end_key="visibility_end_timestamp",
    )


def classify_annotation_candidate(
    annotation: dict[str, Any], event_timestamp_us: int
) -> dict[str, Any]:
    """Classify one event without assigning a final M16 outcome."""
    evidence: dict[str, list[str]] = {slice_name: [] for slice_name in _SLICES}
    agents = [
        item
        for item in annotation.get("agents", ())
        if isinstance(item, dict) and _visible(item, event_timestamp_us)
    ]
    ego_actions = [
        item
        for item in (annotation.get("ego_vehicle") or {}).get("actions", ())
        if isinstance(item, dict) and _active(item, event_timestamp_us)
    ]

    if any(_contains(item.get("type"), _VULNERABLE_TOKENS) for item in agents):
        evidence["PEDESTRIAN_CYCLIST_YIELD"].append(
            "TIME_ALIGNED_VULNERABLE_ROAD_USER"
        )

    traffic_lights = [
        item
        for item in annotation.get("traffic_lights", ())
        if isinstance(item, dict) and _visible(item, event_timestamp_us)
    ]
    active_signal_colors = {
        _normalized(state.get("color"))
        for light in traffic_lights
        for head in light.get("signal_heads", ())
        if isinstance(head, dict)
        for state in head.get("state_sequence", ())
        if isinstance(state, dict) and _active(state, event_timestamp_us)
    }
    if active_signal_colors.intersection({"red", "yellow"}):
        evidence["STOP_SIGNALS"].append("TIME_ALIGNED_RESTRICTIVE_SIGNAL")
    if "green" in active_signal_colors:
        evidence["STOP_SIGNALS"].append("TIME_ALIGNED_PERMISSIVE_SIGNAL")

    controls = [
        item
        for item in annotation.get("traffic_objects", ())
        if isinstance(item, dict)
        and _visible(item, event_timestamp_us)
        and _contains(item.get("type"), _STOP_CONTROL_TOKENS)
    ]
    if controls:
        evidence["STOP_SIGNALS"].append("TIME_ALIGNED_STOP_OR_YIELD_CONTROL")

    vehicles = [
        item for item in agents if _contains(item.get("type"), _VEHICLE_TOKENS)
    ]
    vehicle_interaction = any(
        _contains(action.get("action_type"), _FOLLOWING_ACTION_TOKENS)
        for vehicle in vehicles
        for action in vehicle.get("actions", ())
        if isinstance(action, dict) and _active(action, event_timestamp_us)
    )
    ego_interaction = bool(vehicles) and any(
        _contains(action.get("type"), _FOLLOWING_ACTION_TOKENS)
        for action in ego_actions
    )
    if vehicle_interaction or ego_interaction:
        evidence["FOLLOWING_CUT_IN"].append(
            "TIME_ALIGNED_VEHICLE_INTERACTION"
        )

    candidate_slices = [slice_name for slice_name in _SLICES if evidence[slice_name]]
    return {
        "candidate_slices": candidate_slices,
        "slice_evidence": {
            slice_name: evidence[slice_name] for slice_name in candidate_slices
        },
        "classification_status": (
            "SLICE_CANDIDATE" if candidate_slices else "UNSUPPORTED_BY_ANNOTATION"
        ),
        "outcome_status": SENSOR_REVIEW_STATUS,
        "final_outcome_assigned": False,
    }


def select_sensor_shortlist(
    candidates: Iterable[dict[str, Any]],
    *,
    per_slice: int = 20,
    slice_targets: dict[str, int] | None = None,
) -> dict[str, Any]:
    """Select unique clips deterministically while preserving slice ambiguity."""
    targets = (
        {name: per_slice for name in _SLICES}
        if slice_targets is None
        else {name: int(slice_targets[name]) for name in _SLICES}
    )
    eligible = [
        dict(item)
        for item in candidates
        if item.get("sensor_feature_eligible") is True
        and item.get("candidate_slices")
    ]
    eligible.sort(
        key=lambda item: (
            len(item["candidate_slices"]),
            str(item["candidate_digest"]),
        )
    )
    selected: list[dict[str, Any]] = []
    selected_clips: set[str] = set()
    coverage = Counter()
    for slice_name in _SLICES:
        for item in eligible:
            if coverage[slice_name] >= targets[slice_name]:
                break
            if slice_name not in item["candidate_slices"]:
                continue
            clip_id = str(item["clip_id"])
            if clip_id in selected_clips:
                continue
            selected_clips.add(clip_id)
            coverage[slice_name] += 1
            selected.append({**item, "shortlist_slice": slice_name})
    return {
        "selection_version": "guardsynth-m16-sensor-shortlist-v0.1",
        "slice_targets": targets,
        "selected_event_count": len(selected),
        "selected_unique_clip_count": len(selected_clips),
        "slice_coverage": {name: coverage[name] for name in _SLICES},
        "slice_shortfall": {
            name: max(0, targets[name] - coverage[name]) for name in _SLICES
        },
        "outcome_status": SENSOR_REVIEW_STATUS,
        "final_outcome_assigned_count": 0,
        "records": selected,
    }


def build_attrition_reserve(
    candidates: Iterable[dict[str, Any]], primary_shortlist: dict[str, Any]
) -> dict[str, Any]:
    """Preserve all remaining events while materializing each new clip only once."""
    classified = [
        dict(item)
        for item in candidates
        if item.get("sensor_feature_eligible") is True
        and item.get("candidate_slices")
    ]
    classified.sort(key=lambda item: str(item["candidate_digest"]))
    digests = [str(item.get("candidate_digest")) for item in classified]
    if len(digests) != len(set(digests)):
        raise ValueError("ATTRITION_RESERVE_CANDIDATE_DIGEST_DUPLICATE")
    if any(not isinstance(item.get("clip_id"), str) or not item["clip_id"] for item in classified):
        raise ValueError("ATTRITION_RESERVE_CLIP_ID_INVALID")

    primary_records = primary_shortlist.get("records")
    if not isinstance(primary_records, list) or not primary_records:
        raise ValueError("ATTRITION_RESERVE_PRIMARY_SHORTLIST_INVALID")
    primary_digests = {str(item.get("candidate_digest")) for item in primary_records}
    primary_assets: dict[str, str] = {}
    for item in primary_records:
        clip_id = item.get("clip_id")
        digest = str(item.get("candidate_digest"))
        if (
            not isinstance(clip_id, str)
            or not clip_id
            or clip_id in primary_assets
            or digest not in digests
        ):
            raise ValueError("ATTRITION_RESERVE_PRIMARY_RECORD_INVALID")
        primary_assets[clip_id] = digest

    reserve = [item for item in classified if item["candidate_digest"] not in primary_digests]
    new_clip_records: dict[str, list[dict[str, Any]]] = {}
    for item in reserve:
        clip_id = str(item["clip_id"])
        if clip_id not in primary_assets:
            new_clip_records.setdefault(clip_id, []).append(item)
    new_clip_assets = {
        clip_id: min(
            records,
            key=lambda item: str(item["candidate_digest"]),
        )["candidate_digest"]
        for clip_id, records in new_clip_records.items()
    }

    coverage = Counter()
    for item in sorted(
        reserve,
        key=lambda record: (
            len(record["candidate_slices"]),
            str(record["candidate_digest"]),
        ),
    ):
        item["reserve_slice"] = min(
            item["candidate_slices"],
            key=lambda name: (coverage[name], _SLICES.index(name)),
        )
        coverage[item["reserve_slice"]] += 1
        clip_id = str(item["clip_id"])
        if clip_id in primary_assets:
            item["reserve_tier"] = "MATERIALIZED_CLIP_SECONDARY_EVENT"
            item["asset_candidate_digest"] = primary_assets[clip_id]
        elif item["candidate_digest"] == new_clip_assets[clip_id]:
            item["reserve_tier"] = "NEW_CLIP_PRIMARY"
            item["asset_candidate_digest"] = item["candidate_digest"]
        else:
            item["reserve_tier"] = "NEW_CLIP_SECONDARY_EVENT"
            item["asset_candidate_digest"] = new_clip_assets[clip_id]

    tier_order = {
        "NEW_CLIP_PRIMARY": 0,
        "NEW_CLIP_SECONDARY_EVENT": 1,
        "MATERIALIZED_CLIP_SECONDARY_EVENT": 2,
    }
    reserve.sort(
        key=lambda item: (
            tier_order[item["reserve_tier"]],
            str(item["candidate_digest"]),
        )
    )
    materialization_records = [
        {
            **item,
            "shortlist_slice": item["reserve_slice"],
        }
        for item in reserve
        if item["reserve_tier"] == "NEW_CLIP_PRIMARY"
    ]
    return {
        "selection_version": "guardsynth-m16-attrition-reserve-v0.1",
        "classified_event_count": len(classified),
        "classified_unique_clip_count": len({item["clip_id"] for item in classified}),
        "primary_shortlist_event_count": len(primary_records),
        "primary_shortlist_unique_clip_count": len(primary_assets),
        "reserve_event_count": len(reserve),
        "reserve_event_unique_clip_count": len({item["clip_id"] for item in reserve}),
        "new_clip_event_count": sum(
            item["reserve_tier"] != "MATERIALIZED_CLIP_SECONDARY_EVENT"
            for item in reserve
        ),
        "new_clip_materialization_count": len(materialization_records),
        "new_clip_secondary_event_count": sum(
            item["reserve_tier"] == "NEW_CLIP_SECONDARY_EVENT" for item in reserve
        ),
        "reused_materialized_clip_event_count": sum(
            item["reserve_tier"] == "MATERIALIZED_CLIP_SECONDARY_EVENT"
            for item in reserve
        ),
        "reserve_slice_routing_counts": {
            name: coverage[name] for name in _SLICES
        },
        "final_outcome_assigned_count": 0,
        "outcome_status": SENSOR_REVIEW_STATUS,
        "records": reserve,
        "materialization_records": materialization_records,
        "claim_scope": "ATTRITION_RESERVE_CANDIDATES_NOT_SCENE_ELIGIBILITY_OR_SAFETY",
    }


def deidentified_screen_summary(
    candidates: Iterable[dict[str, Any]], shortlist: dict[str, Any]
) -> dict[str, Any]:
    """Build aggregate-only output suitable for the public artifact boundary."""
    records = list(candidates)
    slice_counts = Counter(
        slice_name
        for item in records
        for slice_name in item.get("candidate_slices", ())
    )
    country_counts = Counter(str(item.get("country", "UNKNOWN")) for item in records)
    return {
        "screen_version": SCREEN_VERSION,
        "screened_event_count": len(records),
        "screened_unique_candidate_count": len(
            {str(item["candidate_digest"]) for item in records}
        ),
        "classified_event_count": sum(bool(item.get("candidate_slices")) for item in records),
        "unsupported_event_count": sum(not item.get("candidate_slices") for item in records),
        "ambiguous_multi_slice_event_count": sum(
            len(item.get("candidate_slices", ())) > 1 for item in records
        ),
        "sensor_feature_eligible_event_count": sum(
            item.get("sensor_feature_eligible") is True for item in records
        ),
        "slice_candidate_counts": {name: slice_counts[name] for name in _SLICES},
        "country_event_counts": dict(sorted(country_counts.items())),
        "shortlist_unique_clip_count": shortlist["selected_unique_clip_count"],
        "shortlist_slice_coverage": dict(shortlist["slice_coverage"]),
        "shortlist_slice_shortfall": dict(shortlist["slice_shortfall"]),
        "outcome_status": SENSOR_REVIEW_STATUS,
        "final_outcome_assigned_count": 0,
        "claim_scope": "ANNOTATION_FIRST_SCREEN_NOT_SCENE_ELIGIBILITY_OR_VEHICLE_SAFETY",
    }


def candidate_digest(clip_id: str, event_timestamp_us: int) -> str:
    payload = f"{clip_id}:{event_timestamp_us}".encode()
    return "candidate-sha256:" + hashlib.sha256(payload).hexdigest()
