"""Fail-closed audit of hash-linked evidence for one calibration scene."""

from __future__ import annotations

import hashlib
import json
from math import isfinite
from pathlib import Path
from typing import Any

from .dry_run_readiness import REQUIRED_SCENE_FIELDS
from .nvidia_source_bundle import SOURCE_BUNDLE_VERSION
from .geometric_association import (
    ASSOCIATION_METHOD,
    GEOMETRIC_ASSOCIATION_VERSION,
)
from .rule_applicability import (
    LOCALIZATION_STATUS,
    RULE_APPLICABILITY_VERSION,
)


SCENE_SOURCE_AUDIT_VERSION = "guardsynth-calibration-scene-source-audit-v0.6"
_IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png"}
_MISSING_REASON_BY_FIELD = {
    "timestamps": "MISSING_VALID_TIMESTAMP_SIDECAR",
    "ego_pose_and_speed": "MISSING_TIME_ALIGNED_EGO_POSE_AND_SPEED",
    "relevant_actor_tracks": "MISSING_RELEVANT_ACTOR_TRACKS",
    "target_zone_or_lane_association": "MISSING_OR_AMBIGUOUS_TARGET_ZONE_ASSOCIATION",
    "conflict_or_stop_geometry": "MISSING_CONFLICT_OR_STOP_GEOMETRY",
    "verified_coordinate_transform": "UNVERIFIED_COORDINATE_TRANSFORM",
    "applicable_rule_source_refs": "MISSING_APPLICABLE_RULE_SOURCE_REFS",
    "exact_vehicle_binding": "MISSING_EXACT_VEHICLE_BINDING",
    "source_bearing_vehicle_assurance_profile": "MISSING_VEHICLE_ASSURANCE_PROFILE",
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _missing_field_status() -> dict[str, dict[str, str]]:
    return {
        field: {
            "status": "REVIEW_REQUIRED",
            "reason_code": _MISSING_REASON_BY_FIELD[field],
        }
        for field in REQUIRED_SCENE_FIELDS
    }


def _base_audit(packet: dict[str, Any]) -> dict[str, Any]:
    return {
        "audit_version": SCENE_SOURCE_AUDIT_VERSION,
        "packet_id": packet["packet_id"],
        "scene_ref": packet["scene_ref"],
        "input_class": "LICENSE_RESTRICTED",
        "field_status": _missing_field_status(),
        "available_fields": [],
        "missing_fields": list(REQUIRED_SCENE_FIELDS),
        "reason_codes": [],
        "source_complete": False,
        "contract_generation_allowed": False,
        "synthesized_required_values": [],
        "raw_source_paths_included": False,
        "association_readiness": {
            "adapter_event_match_count": 0,
            "declared_candidate_count": 0,
            "serialized_candidate_record_count": 0,
            "candidate_track_samples_preserved": False,
            "all_candidates_preserved": False,
            "review_ui_allowed": False,
            "reason_code": "NO_UNIQUE_DERIVED_ADAPTER_EVENT",
        },
        "claim_scope": "HASH_LINKED_SOURCE_DISCOVERY_NOT_ASSOCIATION_ACCURACY_SOURCE_CLOSURE_OR_VEHICLE_SAFETY",
    }


def _finish(audit: dict[str, Any]) -> dict[str, Any]:
    audit["available_fields"] = [
        field for field in REQUIRED_SCENE_FIELDS
        if audit["field_status"][field]["status"] == "AVAILABLE_SOURCE_LINKED"
    ]
    audit["missing_fields"] = [
        field for field in REQUIRED_SCENE_FIELDS
        if audit["field_status"][field]["status"] != "AVAILABLE_SOURCE_LINKED"
    ]
    reasons = [
        audit["field_status"][field]["reason_code"]
        for field in audit["missing_fields"]
    ]
    audit["reason_codes"] = list(dict.fromkeys([*audit["reason_codes"], *reasons]))
    return audit


def _timestamp_layout(entry: dict[str, Any]) -> str | None:
    timestamps = entry.get("absolute_timestamps_us")
    relative = entry.get("relative_times_s")
    cameras = entry.get("camera_order")
    if not isinstance(timestamps, list) or not timestamps:
        return None
    if not isinstance(relative, list) or not isinstance(cameras, list):
        return None
    if not relative or not cameras:
        return None

    scalar_timestamps = all(
        isinstance(value, int) and not isinstance(value, bool) for value in timestamps
    )
    if scalar_timestamps:
        if (
            len(relative) == len(timestamps)
            and all(right > left for left, right in zip(timestamps, timestamps[1:]))
        ):
            return "TIME_SEQUENCE"
        return None

    if not all(
        isinstance(row, list)
        and all(isinstance(value, int) and not isinstance(value, bool) for value in row)
        for row in timestamps
    ):
        return None
    camera_by_time = (
        len(timestamps) == len(cameras)
        and all(len(row) == len(relative) for row in timestamps)
        and all(
            right > left
            for row in timestamps
            for left, right in zip(row, row[1:])
        )
    )
    if camera_by_time:
        return "CAMERA_BY_TIME"
    time_by_camera = (
        len(timestamps) == len(relative)
        and all(len(row) == len(cameras) for row in timestamps)
        and all(
        timestamps[row_index + 1][camera_index] > timestamps[row_index][camera_index]
        for row_index in range(len(timestamps) - 1)
        for camera_index in range(len(cameras))
        )
    )
    return "TIME_BY_CAMERA" if time_by_camera else None


def _source_refs(value: Any) -> bool:
    return (
        isinstance(value, list)
        and bool(value)
        and all(isinstance(item, str) and bool(item) for item in value)
    )


def _apply_scene_source_bundle(
    audit: dict[str, Any],
    bundle: dict[str, Any] | None,
    document_sha256: str | None,
) -> None:
    if bundle is None:
        return
    if (
        bundle.get("source_bundle_version") != SOURCE_BUNDLE_VERSION
        or bundle.get("scene_ref") != audit["scene_ref"]
        or not isinstance(document_sha256, str)
        or len(document_sha256) != 64
    ):
        audit["reason_codes"].append("INVALID_OR_MISMATCHED_SCENE_SOURCE_BUNDLE")
        return

    transform = bundle.get("coordinate_transform")
    matrix = transform.get("matrix_4x4") if isinstance(transform, dict) else None
    flat_matrix = [value for row in matrix for value in row] if (
        isinstance(matrix, list)
        and len(matrix) == 4
        and all(isinstance(row, list) and len(row) == 4 for row in matrix)
    ) else []
    if (
        isinstance(transform, dict)
        and transform.get("status") == "AVAILABLE_SOURCE_LINKED"
        and transform.get("source_frame") == "dataset_rig_at_event"
        and transform.get("target_frame") == "ego_at_model_t0"
        and len(flat_matrix) == 16
        and all(isinstance(value, (int, float)) and isfinite(value) for value in flat_matrix)
        and isinstance(transform.get("inverse_closure_max_abs_error"), (int, float))
        and 0 <= float(transform["inverse_closure_max_abs_error"]) <= 1e-9
        and _source_refs(transform.get("evidence_refs"))
    ):
        audit["field_status"]["verified_coordinate_transform"] = {
            "status": "AVAILABLE_SOURCE_LINKED",
            "evidence_ref": (
                f"restricted-sha256:{document_sha256}#/coordinate_transform"
            ),
            "source_frame": transform["source_frame"],
            "target_frame": transform["target_frame"],
            "inverse_closure_max_abs_error": float(
                transform["inverse_closure_max_abs_error"]
            ),
            "source_refs": list(transform["evidence_refs"]),
        }
    else:
        audit["reason_codes"].append("INVALID_SOURCE_BEARING_COORDINATE_TRANSFORM")

    binding = bundle.get("vehicle_binding")
    binding_key = binding.get("vehicle_binding_key") if isinstance(binding, dict) else None
    if (
        isinstance(binding, dict)
        and binding.get("status") == "AVAILABLE_SOURCE_LINKED"
        and isinstance(binding_key, str)
        and binding_key.startswith("nvidia-rig-config-sha256:")
        and len(binding_key.removeprefix("nvidia-rig-config-sha256:")) == 64
        and binding.get("binding_scope") == "DATASET_CLIP_RIG_CONFIGURATION_NOT_VIN"
        and _source_refs(binding.get("evidence_refs"))
    ):
        audit["field_status"]["exact_vehicle_binding"] = {
            "status": "AVAILABLE_SOURCE_LINKED",
            "evidence_ref": f"restricted-sha256:{document_sha256}#/vehicle_binding",
            "vehicle_binding_key": binding_key,
            "binding_scope": binding["binding_scope"],
            "source_refs": list(binding["evidence_refs"]),
        }
    else:
        audit["reason_codes"].append("INVALID_DATASET_RIG_CONFIGURATION_BINDING")


def _apply_association_evidence(
    audit: dict[str, Any],
    evidence: dict[str, Any] | None,
    document_sha256: str | None,
) -> None:
    if evidence is None:
        return
    zone = evidence.get("zone")
    track_ids = evidence.get("associated_track_id_sha256")
    intervals = (
        zone.get("x_interval_m"),
        zone.get("y_interval_m"),
        zone.get("time_interval_us"),
    ) if isinstance(zone, dict) else (None, None, None)
    valid_intervals = all(
        isinstance(interval, list)
        and len(interval) == 2
        and all(isinstance(value, (int, float)) and isfinite(value) for value in interval)
        and interval[0] <= interval[1]
        for interval in intervals
    )
    valid_tracks = (
        isinstance(track_ids, list)
        and bool(track_ids)
        and len(track_ids) == evidence.get("association_cardinality")
        and len(set(track_ids)) == len(track_ids)
        and all(
            isinstance(track_id, str)
            and len(track_id) == 64
            and all(character in "0123456789abcdef" for character in track_id)
            for track_id in track_ids
        )
    )
    if (
        evidence.get("association_version") == GEOMETRIC_ASSOCIATION_VERSION
        and evidence.get("scene_ref") == audit["scene_ref"]
        and evidence.get("status") == "AVAILABLE_SOURCE_LINKED"
        and evidence.get("target_kind") == "SET"
        and evidence.get("association_method") == ASSOCIATION_METHOD
        and valid_tracks
        and isinstance(zone, dict)
        and zone.get("kind") == "DYNAMIC_MULTI_ACTOR_EGO_CORRIDOR_OVERLAP"
        and zone.get("coordinate_frame") == "dataset_rig"
        and valid_intervals
        and _source_refs(evidence.get("evidence_refs"))
        and evidence.get("crosswalk_or_legal_zone_claimed") is False
        and evidence.get("collision_prediction_claimed") is False
        and isinstance(document_sha256, str)
        and len(document_sha256) == 64
    ):
        audit["field_status"]["target_zone_or_lane_association"] = {
            "status": "AVAILABLE_SOURCE_LINKED",
            "evidence_ref": f"restricted-sha256:{document_sha256}#/",
            "target_kind": "SET",
            "association_cardinality": len(track_ids),
            "track_id_sha256": list(track_ids),
            "association_method": ASSOCIATION_METHOD,
            "zone": dict(zone),
            "claim_boundary": "GEOMETRIC_CORRIDOR_ASSOCIATION_NOT_SEMANTIC_COC_REFERENT_OR_COLLISION_PREDICTION",
        }
    else:
        audit["reason_codes"].append("INVALID_OR_MISMATCHED_ASSOCIATION_EVIDENCE")


def _apply_rule_applicability_evidence(
    audit: dict[str, Any],
    evidence: dict[str, Any] | None,
    document_sha256: str | None,
) -> None:
    if evidence is None:
        return
    jurisdiction = evidence.get("jurisdiction_binding")
    sources = evidence.get("rule_source_refs")
    valid_sources = (
        isinstance(sources, list)
        and bool(sources)
        and all(
            isinstance(source, dict)
            and isinstance(source.get("source_id"), str)
            and source.get("authority") == "California Legislature"
            and source.get("jurisdiction") == "California"
            and isinstance(source.get("official_url"), str)
            and source["official_url"].startswith(
                "https://leginfo.legislature.ca.gov/"
            )
            and isinstance(source.get("snapshot_sha256"), str)
            and len(source["snapshot_sha256"]) == 64
            for source in sources
        )
    )
    if (
        evidence.get("rule_applicability_version") == RULE_APPLICABILITY_VERSION
        and evidence.get("scene_ref") == audit["scene_ref"]
        and evidence.get("status") == "AVAILABLE_SOURCE_LINKED"
        and evidence.get("applicability_verdict") == "CONDITIONALLY_APPLICABLE"
        and evidence.get("primary_rule_source_id") == "CA-VEH-21950"
        and isinstance(jurisdiction, dict)
        and jurisdiction.get("country") == "United States"
        and jurisdiction.get("administrative_area") == "California"
        and jurisdiction.get("locality") == "San Francisco"
        and jurisdiction.get("status") == LOCALIZATION_STATUS
        and valid_sources
        and evidence.get("unsourced_normative_or_numeric_value_count") == 0
        and evidence.get("vehicle_safety_validated") is False
        and isinstance(document_sha256, str)
        and len(document_sha256) == 64
    ):
        audit["field_status"]["applicable_rule_source_refs"] = {
            "status": "AVAILABLE_SOURCE_LINKED",
            "evidence_ref": f"restricted-sha256:{document_sha256}#/",
            "applicability_verdict": "CONDITIONALLY_APPLICABLE",
            "primary_rule_source_id": "CA-VEH-21950",
            "rule_source_refs": [dict(source) for source in sources],
            "jurisdiction_binding_status": LOCALIZATION_STATUS,
            "independent_dataset_gps_confirmation": bool(
                jurisdiction.get("independent_dataset_gps_confirmation", False)
            ),
            "claim_boundary": "OFFICIAL_SOURCE_WITH_IMAGE_CUE_LOCALIZATION_NOT_GPS_LEGAL_ADVICE_OR_VEHICLE_SAFETY",
        }
    else:
        audit["reason_codes"].append("INVALID_OR_MISMATCHED_RULE_APPLICABILITY_EVIDENCE")


def audit_calibration_scene_source(
    packet: dict[str, Any],
    embedded_manifest: dict[str, Any],
    source_root: Path,
    *,
    adapter_result: dict[str, Any] | None = None,
    adapter_document_sha256: str | None = None,
    scene_source_bundle: dict[str, Any] | None = None,
    scene_source_bundle_sha256: str | None = None,
    association_evidence: dict[str, Any] | None = None,
    association_evidence_sha256: str | None = None,
    rule_applicability_evidence: dict[str, Any] | None = None,
    rule_applicability_evidence_sha256: str | None = None,
) -> dict[str, Any]:
    """Recover only evidence that is uniquely linked by image content hash."""
    audit = _base_audit(packet)
    filename = packet["source_review"]["image_filename"]
    manifest_matches = [
        item for item in embedded_manifest.get("images", ())
        if isinstance(item, dict) and item.get("filename") == filename
    ]
    if len(manifest_matches) != 1:
        audit["reason_codes"].append("MISSING_EMBEDDED_IMAGE_PROVENANCE")
        return _finish(audit)
    image_sha = manifest_matches[0].get("sha256")
    if not isinstance(image_sha, str) or len(image_sha) != 64:
        audit["reason_codes"].append("INVALID_EMBEDDED_IMAGE_SHA256")
        return _finish(audit)

    source_matches = [
        path for path in source_root.rglob("*")
        if path.is_file()
        and path.suffix.lower() in _IMAGE_SUFFIXES
        and _sha256(path) == image_sha
    ]
    if len(source_matches) != 1:
        audit["reason_codes"].append(
            "MISSING_HASH_LINKED_IMAGE_SOURCE"
            if not source_matches else "AMBIGUOUS_HASH_LINKED_IMAGE_SOURCE"
        )
        return _finish(audit)

    image_path = source_matches[0]
    sidecar_path = image_path.parent / "media-manifest.json"
    if not sidecar_path.is_file():
        audit["reason_codes"].append("MISSING_VALID_TIMESTAMP_SIDECAR")
        return _finish(audit)
    try:
        sidecar = json.loads(sidecar_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        audit["reason_codes"].append("MISSING_VALID_TIMESTAMP_SIDECAR")
        return _finish(audit)
    entries = [
        (index, item) for index, item in enumerate(sidecar)
        if isinstance(item, dict) and item.get("image") == image_path.name
    ] if isinstance(sidecar, list) else []
    layout = _timestamp_layout(entries[0][1]) if len(entries) == 1 else None
    if layout is None:
        audit["reason_codes"].append("MISSING_VALID_TIMESTAMP_SIDECAR")
        return _finish(audit)

    index, entry = entries[0]
    sidecar_sha = _sha256(sidecar_path)
    audit["field_status"]["timestamps"] = {
        "status": "AVAILABLE_SOURCE_LINKED",
        "evidence_ref": f"restricted-sha256:{sidecar_sha}#/{index}/absolute_timestamps_us",
        "values_us": list(entry["absolute_timestamps_us"]),
        "relative_times_s": list(entry["relative_times_s"]),
        "camera_order": list(entry["camera_order"]),
        "layout": layout,
        "dataset_revision": str(entry.get("dataset_revision", "")),
        "image_sha256": image_sha,
    }
    if adapter_result is not None:
        episode = entry.get("episode")
        candidates = list(adapter_result.get("candidates", ()))
        matches = [
            (candidate_index, candidate)
            for candidate_index, candidate in enumerate(candidates)
            if isinstance(candidate, dict)
            and isinstance(candidate.get("candidate_id"), str)
            and isinstance(episode, str)
            and candidate["candidate_id"].startswith(f"{episode}-")
        ]
        if len(matches) > 1:
            audit["association_readiness"]["adapter_event_match_count"] = len(matches)
            audit["reason_codes"].append("AMBIGUOUS_DERIVED_ADAPTER_EVENT")
        elif not matches:
            audit["reason_codes"].append("NO_DERIVED_ADAPTER_EVENT_FOR_SCENE")
        elif (
            not isinstance(adapter_document_sha256, str)
            or len(adapter_document_sha256) != 64
        ):
            audit["reason_codes"].append("INVALID_DERIVED_ADAPTER_PROVENANCE")
        else:
            candidate_index, candidate = matches[0]
            target_binding = candidate.get("target_binding")
            target_binding = target_binding if isinstance(target_binding, dict) else {}
            declared_count = target_binding.get("candidate_count", 0)
            if isinstance(declared_count, bool) or not isinstance(declared_count, int):
                declared_count = 0
            candidate_records = candidate.get("association_candidates")
            candidate_records = candidate_records if isinstance(candidate_records, list) else []
            if candidate_records:
                serialized_count = len(candidate_records)
                samples_preserved = all(
                    isinstance(item, dict)
                    and isinstance(item.get("track_id_sha256"), str)
                    and len(item["track_id_sha256"]) == 64
                    and all(
                        character in "0123456789abcdef"
                        for character in item["track_id_sha256"]
                    )
                    and isinstance(item.get("track_samples"), list)
                    and bool(item["track_samples"])
                    for item in candidate_records
                )
            else:
                serialized_count = int(
                    isinstance(target_binding.get("track_id_sha256"), str)
                )
                samples_preserved = False
            all_preserved = (
                declared_count > 0
                and serialized_count == declared_count
                and samples_preserved
            )
            audit["association_readiness"] = {
                "adapter_event_match_count": 1,
                "declared_candidate_count": declared_count,
                "serialized_candidate_record_count": serialized_count,
                "candidate_track_samples_preserved": samples_preserved,
                "all_candidates_preserved": all_preserved,
                "review_ui_allowed": all_preserved,
                "reason_code": (
                    None if all_preserved else "ALL_ACTOR_CANDIDATES_NOT_PRESERVED"
                ),
            }
            if not all_preserved:
                audit["reason_codes"].append("ALL_ACTOR_CANDIDATES_NOT_PRESERVED")
            else:
                audit["field_status"]["relevant_actor_tracks"] = {
                    "status": "AVAILABLE_SOURCE_LINKED",
                    "evidence_ref": (
                        f"restricted-sha256:{adapter_document_sha256}"
                        f"#/candidates/{candidate_index}/association_candidates"
                    ),
                    "candidate_count": serialized_count,
                    "identity_form": "SHA256",
                    "time_series_preserved": True,
                }
            ego = candidate.get("ego_state")
            pose = ego.get("pose_relative_t0_m") if isinstance(ego, dict) else None
            speed = ego.get("speed_mps") if isinstance(ego, dict) else None
            relative_time = ego.get("relative_time_s") if isinstance(ego, dict) else None
            if (
                candidate.get("context_schema_valid") is True
                and isinstance(pose, list)
                and len(pose) == 3
                and all(isinstance(value, (int, float)) and isfinite(value) for value in pose)
                and isinstance(speed, (int, float))
                and isfinite(speed)
                and isinstance(relative_time, (int, float))
                and isfinite(relative_time)
            ):
                audit["field_status"]["ego_pose_and_speed"] = {
                    "status": "AVAILABLE_SOURCE_LINKED",
                    "evidence_ref": (
                        f"restricted-sha256:{adapter_document_sha256}"
                        f"#/candidates/{candidate_index}/ego_state"
                    ),
                    "pose_relative_t0_m": list(pose),
                    "speed_mps": float(speed),
                    "relative_time_s": float(relative_time),
                    "derivation": str(ego.get("derivation", "")),
                }
            else:
                audit["reason_codes"].append("INVALID_DERIVED_ADAPTER_EGO_STATE")

            geometry = candidate.get("conflict_zone")
            entry_x = geometry.get("entry_x_m") if isinstance(geometry, dict) else None
            lateral = geometry.get("lateral_center_m") if isinstance(geometry, dict) else None
            source_fields = geometry.get("source_fields") if isinstance(geometry, dict) else None
            if (
                candidate.get("context_schema_valid") is True
                and isinstance(entry_x, (int, float))
                and isfinite(entry_x)
                and isinstance(lateral, (int, float))
                and isfinite(lateral)
                and isinstance(source_fields, list)
                and bool(source_fields)
            ):
                audit["field_status"]["conflict_or_stop_geometry"] = {
                    "status": "AVAILABLE_SOURCE_LINKED",
                    "evidence_ref": (
                        f"restricted-sha256:{adapter_document_sha256}"
                        f"#/candidates/{candidate_index}/conflict_zone"
                    ),
                    "kind": str(geometry.get("kind", "")),
                    "entry_x_m": float(entry_x),
                    "lateral_center_m": float(lateral),
                    "source_fields": list(source_fields),
                    "crosswalk_or_legal_zone_claimed": bool(
                        geometry.get("crosswalk_or_legal_zone_claimed", False)
                    ),
                }
            else:
                audit["reason_codes"].append("INVALID_DERIVED_ADAPTER_GEOMETRY")
    _apply_scene_source_bundle(
        audit, scene_source_bundle, scene_source_bundle_sha256
    )
    _apply_association_evidence(
        audit, association_evidence, association_evidence_sha256
    )
    _apply_rule_applicability_evidence(
        audit, rule_applicability_evidence, rule_applicability_evidence_sha256
    )
    return _finish(audit)
