"""Source-linked set association from actor boxes and the ego corridor."""

from __future__ import annotations

import hashlib
import json
from math import isfinite
from typing import Any


GEOMETRIC_ASSOCIATION_VERSION = "guardsynth-geometric-set-association-v0.1"
ASSOCIATION_METHOD = "OBSERVED_ORIENTED_BBOX_EGO_CORRIDOR_OVERLAP"


def _finite(value: Any, reason: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(reason)
    result = float(value)
    if not isfinite(result):
        raise ValueError(reason)
    return result


def _track_hash(value: Any) -> str:
    if not (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    ):
        raise ValueError("INVALID_TRACK_ID_SHA256")
    return value


def build_geometric_set_association(
    *,
    scene_ref: str,
    event_timestamp_us: int,
    candidates: list[dict[str, Any]],
    ego_half_width_m: float,
    ego_front_extent_m: float,
    evidence_refs: list[str],
) -> dict[str, Any]:
    """Select every source track whose oriented 2-D box overlaps the ego corridor.

    Candidate box extents are expected to have already been projected onto the
    dataset rig axes.  The result associates a *set* of tracks; it never chooses
    the nearest candidate as a semantic referent.
    """
    if not isinstance(scene_ref, str) or not scene_ref:
        raise ValueError("INVALID_SCENE_REF")
    if isinstance(event_timestamp_us, bool) or not isinstance(event_timestamp_us, int):
        raise ValueError("INVALID_EVENT_TIMESTAMP")
    half_width = _finite(ego_half_width_m, "INVALID_EGO_HALF_WIDTH")
    front_extent = _finite(ego_front_extent_m, "INVALID_EGO_FRONT_EXTENT")
    if half_width <= 0 or front_extent <= 0:
        raise ValueError("INVALID_VEHICLE_GEOMETRY")
    if not candidates:
        raise ValueError("MISSING_ASSOCIATION_CANDIDATES")
    if not evidence_refs or not all(isinstance(ref, str) and ref for ref in evidence_refs):
        raise ValueError("MISSING_ASSOCIATION_EVIDENCE_REFS")

    associated: list[dict[str, Any]] = []
    excluded: list[str] = []
    overlap_boxes: list[tuple[float, float, int]] = []
    seen_hashes: set[str] = set()
    for candidate in candidates:
        track_id_sha256 = _track_hash(candidate.get("track_id_sha256"))
        if track_id_sha256 in seen_hashes:
            raise ValueError("DUPLICATE_TRACK_ID_SHA256")
        seen_hashes.add(track_id_sha256)
        samples = candidate.get("track_samples")
        if not isinstance(samples, list) or not samples:
            raise ValueError("MISSING_TRACK_SAMPLES")

        overlap_count = 0
        track_boxes: list[tuple[float, float, int]] = []
        previous_timestamp: int | None = None
        for sample in samples:
            timestamp = sample.get("timestamp_us")
            if (
                isinstance(timestamp, bool)
                or not isinstance(timestamp, int)
                or (previous_timestamp is not None and timestamp <= previous_timestamp)
            ):
                raise ValueError("INVALID_TRACK_TIMESTAMP_SEQUENCE")
            previous_timestamp = timestamp
            center_x = _finite(sample.get("center_x_m"), "INVALID_TRACK_CENTER")
            center_y = _finite(sample.get("center_y_m"), "INVALID_TRACK_CENTER")
            if "half_extent_x_m" not in sample or "half_extent_y_m" not in sample:
                raise ValueError("MISSING_TRACK_EXTENT")
            half_x = _finite(sample["half_extent_x_m"], "INVALID_TRACK_EXTENT")
            half_y = _finite(sample["half_extent_y_m"], "INVALID_TRACK_EXTENT")
            if half_x <= 0 or half_y <= 0:
                raise ValueError("INVALID_TRACK_EXTENT")
            lateral_overlap = abs(center_y) <= half_width + half_y
            longitudinally_relevant = center_x + half_x >= front_extent
            if lateral_overlap and longitudinally_relevant:
                overlap_count += 1
                track_boxes.append((center_x - half_x, center_x + half_x, timestamp))

        if overlap_count:
            overlap_boxes.extend(track_boxes)
            associated.append({
                "track_id_sha256": track_id_sha256,
                "label_class": str(candidate.get("label_class", "")),
                "overlap_sample_count": overlap_count,
                "track_sample_count": len(samples),
                "first_overlap_timestamp_us": min(item[2] for item in track_boxes),
                "last_overlap_timestamp_us": max(item[2] for item in track_boxes),
            })
        else:
            excluded.append(track_id_sha256)

    associated.sort(key=lambda item: item["track_id_sha256"])
    excluded.sort()
    if not associated:
        return {
            "association_version": GEOMETRIC_ASSOCIATION_VERSION,
            "scene_ref": scene_ref,
            "event_timestamp_us": event_timestamp_us,
            "status": "REVIEW_REQUIRED",
            "reason_code": "NO_GEOMETRIC_CORRIDOR_ASSOCIATION",
            "association_method": ASSOCIATION_METHOD,
            "associated_track_id_sha256": [],
            "excluded_track_id_sha256": excluded,
            "evidence_refs": list(evidence_refs),
            "synthetic_value_fill_performed": False,
        }

    track_ids = [item["track_id_sha256"] for item in associated]
    zone = {
        "kind": "DYNAMIC_MULTI_ACTOR_EGO_CORRIDOR_OVERLAP",
        "coordinate_frame": "dataset_rig",
        "x_interval_m": [
            round(min(item[0] for item in overlap_boxes), 6),
            round(max(item[1] for item in overlap_boxes), 6),
        ],
        "y_interval_m": [-round(half_width, 6), round(half_width, 6)],
        "time_interval_us": [
            min(item[2] for item in overlap_boxes),
            max(item[2] for item in overlap_boxes),
        ],
    }
    identity = json.dumps(
        {"scene_ref": scene_ref, "event_timestamp_us": event_timestamp_us,
         "track_ids": track_ids, "zone": zone},
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return {
        "association_version": GEOMETRIC_ASSOCIATION_VERSION,
        "association_id": "sha256:" + hashlib.sha256(identity).hexdigest(),
        "scene_ref": scene_ref,
        "event_timestamp_us": event_timestamp_us,
        "status": "AVAILABLE_SOURCE_LINKED",
        "reason_code": None,
        "target_kind": "SET",
        "association_cardinality": len(associated),
        "associated_track_id_sha256": track_ids,
        "excluded_track_id_sha256": excluded,
        "candidate_evaluations": associated,
        "association_method": ASSOCIATION_METHOD,
        "zone": zone,
        "vehicle_geometry": {
            "ego_half_width_m": round(half_width, 6),
            "ego_front_extent_m": round(front_extent, 6),
        },
        "evidence_refs": list(evidence_refs),
        "crosswalk_or_legal_zone_claimed": False,
        "collision_prediction_claimed": False,
        "semantic_coc_referent_claimed": False,
        "synthetic_value_fill_performed": False,
        "claim_scope": "GEOMETRIC_TRACK_SET_TO_EGO_CORRIDOR_ASSOCIATION_NOT_COC_REFERENT_CROSSWALK_COLLISION_PREDICTION_OR_VEHICLE_SAFETY",
    }
