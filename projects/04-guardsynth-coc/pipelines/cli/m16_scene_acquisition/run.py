#!/usr/bin/env python3
"""Reaudit M16 scene eligibility from local restricted evidence, fail closed."""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import date
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
from typing import Any

if __package__ in {None, ""}:
    _BOOTSTRAP_ROOT = next(
        parent
        for parent in Path(__file__).resolve().parents
        if (parent / "PROJECT_REGISTRY.json").is_file()
    )
    sys.path.insert(0, str(_BOOTSTRAP_ROOT))

from cli.project_paths import project_root
from cli.solver_runtime import configure_project_z3


ROOT = project_root(__file__)
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from guard_synth.expert_pilot_protocol import build_pilot_slot_manifest
from guard_synth.m16_scene_acquisition import (
    REQUIRED_EVIDENCE_FIELDS,
    assert_public_export_safe,
    bind_eligible_scenes_to_slots,
    build_m16_scene_preflight,
    build_scene_eligibility_manifest,
)
from guard_synth.m16_annotation_candidate_screen import (
    build_attrition_reserve,
    candidate_digest,
    classify_annotation_candidate,
    deidentified_screen_summary,
    select_sensor_shortlist,
)
from guard_synth.m16_source_review_precheck import (
    audit_calibration_variant_sources,
    build_human_source_review_packet,
    build_source_review_precheck,
    public_source_review_precheck_summary,
)


EXPERIMENT_ID = "GUARDSYNTH-M16-SCENE-ACQUISITION-001"
CLAIM_SCOPE = "M16_SCENE_ELIGIBILITY_AND_ACQUISITION_NOT_EXPERT_EFFECT_OR_VEHICLE_SAFETY"
COHORT = ROOT / "data/restricted/nvidia_physicalai/internal-derived/cohort-10/cohort-conformance.json"
OBSTACLES = ROOT / (
    "data/restricted/nvidia_physicalai/internal-derived/cohort-10/"
    "obstacle-feasibility-v2-all-candidates.json"
)
PACKETS = ROOT / (
    "artifacts/results/restricted/guardsynth-image-review-partial-scene-001/"
    "alpamayo-image-review-2026-08-11-v2/PARTIAL_SCENE_PACKETS.json"
)
MEDIA_MANIFEST = ROOT / (
    "artifacts/results/restricted/alp-exp-005/feasibility-batch-v0/"
    "blind-review-v0/scene-inputs/media-manifest.json"
)
ADAPTER = ROOT / (
    "artifacts/results/restricted/eblc-p0b-001/"
    "p0b-data-adapter-2026-08-11-v2-all-candidates/ADAPTER_RESULT.json"
)
PRIOR_CLOSURES = (
    ROOT / (
        "artifacts/results/restricted/guardsynth-simulated-scene-evidence-001/"
        "alpamayo-episode-00-event-02-2026-08-12-v1/SCENE_SOURCE_CLOSURE.json"
    ),
    ROOT / (
        "artifacts/results/restricted/guardsynth-simulated-scene-evidence-001/"
        "alpamayo-episode-02-event-00-2026-08-12-v1/SCENE_SOURCE_CLOSURE.json"
    ),
    ROOT / (
        "artifacts/results/restricted/guardsynth-simulated-scene-evidence-001/"
        "alpamayo-episode-02-event-01-2026-08-12-v1/SCENE_SOURCE_CLOSURE.json"
    ),
    ROOT / (
        "artifacts/results/restricted/guardsynth-calibration-scene-source-audit-001/"
        "alpamayo-calibration-source-2026-08-11-v17-rule-applicability/"
        "CALIBRATION_SOURCE_AUDIT.json"
    ),
)
SOURCE_BUNDLE_ROOT = ROOT / "artifacts/results/restricted/guardsynth-scene-source-bundle-001"
SIMULATION_PROFILE = ROOT / (
    "projects/04-guardsynth-coc/src/guard_synth/fixtures/"
    "simulated_assurance_profile_v0_1.json"
)
KR_CATALOG = ROOT / (
    "projects/04-guardsynth-coc/src/guard_synth/fixtures/source_catalog_kr_v0_1.json"
)
CASCADE_ROOT = ROOT / "data/restricted/nvidia_cascade"
PHYSICALAI_ROOT = ROOT / "data/restricted/nvidia_physicalai"
CASCADE_ALIGNMENT_AUDIT = CASCADE_ROOT / "internal-derived/smoke-test-1/result.json"
SENSOR_MATERIALIZATION_ROOT = (
    PHYSICALAI_ROOT / "internal-derived/m16-shortlist-v1"
)
SENSOR_MATERIALIZATION_MANIFEST = SENSOR_MATERIALIZATION_ROOT / "MANIFEST.json"
SENSOR_EVIDENCE_AUDIT = SENSOR_MATERIALIZATION_ROOT / "SENSOR_EVIDENCE_AUDIT.json"
CALIBRATION_MANIFEST = SENSOR_MATERIALIZATION_ROOT / "CALIBRATION_MANIFEST.json"
CALIBRATION_ASSOCIATION_AUDIT = (
    SENSOR_MATERIALIZATION_ROOT / "CALIBRATION_ASSOCIATION_AUDIT.json"
)
ASSOCIATION_REVIEW_QUEUE = (
    SENSOR_MATERIALIZATION_ROOT / "ASSOCIATION_REVIEW_QUEUE.json"
)
RESERVE_MATERIALIZATION_ROOT = (
    PHYSICALAI_ROOT / "internal-derived/m16-reserve-v1"
)
RESERVE_SENSOR_MATERIALIZATION_MANIFEST = RESERVE_MATERIALIZATION_ROOT / "MANIFEST.json"
RESERVE_SENSOR_EVIDENCE_AUDIT = (
    RESERVE_MATERIALIZATION_ROOT / "SENSOR_EVIDENCE_AUDIT.json"
)
RESERVE_CALIBRATION_MANIFEST = (
    RESERVE_MATERIALIZATION_ROOT / "CALIBRATION_MANIFEST.json"
)
RESERVE_CALIBRATION_ASSOCIATION_AUDIT = (
    RESERVE_MATERIALIZATION_ROOT / "CALIBRATION_ASSOCIATION_AUDIT.json"
)
RESERVE_ASSOCIATION_REVIEW_QUEUE = (
    RESERVE_MATERIALIZATION_ROOT / "ASSOCIATION_REVIEW_QUEUE.json"
)
ATTRITION_RESERVE_EVIDENCE_AUDIT = (
    RESERVE_MATERIALIZATION_ROOT / "ATTRITION_RESERVE_EVIDENCE_AUDIT.json"
)
ATTRITION_RESERVE_REVIEW_QUEUE = (
    RESERVE_MATERIALIZATION_ROOT / "ATTRITION_RESERVE_REVIEW_QUEUE.json"
)
PHYSICAL_AI_AV_DEVKIT = (
    ROOT / "third_party/physical_ai_av/src/physical_ai_av/dataset.py"
)
PHYSICAL_AI_FEATURE_CATALOG = PHYSICALAI_ROOT / "features.csv"
REQUIRED_SENSOR_FEATURES = (
    "camera_front_wide_120fov",
    "egomotion",
    "egomotion.offline",
    "obstacle.offline",
)
_CANDIDATE_POINTER_RE = re.compile(r"#/candidates/(\d+)/")
_EPISODE_EVENT_RE = re.compile(r"^episode-(\d+)-event-(\d+)$")


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _digest(label: str, value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return f"{label}-sha256:{hashlib.sha256((label + ':' + payload).encode()).hexdigest()}"


def _ref(digest: str, pointer: str) -> str:
    return f"restricted-sha256:{digest}#{pointer}"


def _write_json(path: Path, value: Any, *, restricted: bool = True) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    path.chmod(0o600 if restricted else 0o644)


def _status(
    status: str,
    evidence_ref: str,
    freshness_status: str,
    frame: str,
    unit: str,
    reason_code: str,
    **extra: Any,
) -> dict[str, Any]:
    return {
        "status": status,
        "evidence_ref": evidence_ref,
        "freshness_status": freshness_status,
        "frame": frame,
        "unit": unit,
        "reason_code": reason_code,
        **extra,
    }


def _simulation_binding() -> dict[str, Any]:
    digest = _sha256(SIMULATION_PROFILE)
    return {
        "binding_key": _digest("simulation-vehicle", digest),
        "assurance_class": "SIMULATED_ASSURANCE",
        "evidence_ref": _ref(digest, "/"),
    }


def _base_hashes(
    episode_index: int,
    event_index: int,
    cohort_event: dict[str, Any],
    obstacle_event: dict[str, Any],
    clip_id: str,
    cohort_sha: str,
    obstacle_sha: str,
) -> dict[str, str]:
    locator = {
        "clip_digest": hashlib.sha256(clip_id.encode()).hexdigest(),
        "timestamp_us": cohort_event["timestamp_us"],
        "source_index": cohort_event.get("source_index"),
    }
    content = {
        "locator": locator,
        "intent": cohort_event.get("intent"),
        "verdict": cohort_event.get("verdict"),
        "obstacle_event": obstacle_event,
        "coc_digest": hashlib.sha256(str(cohort_event.get("coc", "")).encode()).hexdigest(),
    }
    source = {
        "cohort_sha256": cohort_sha,
        "obstacle_sha256": obstacle_sha,
        "pointer": f"/episodes/{episode_index}/events/{event_index}",
    }
    return {
        "scene_hash": _digest("scene", locator),
        "event_hash": _digest("event", locator),
        "content_hash": _digest("content", content),
        "source_hash": _digest("source", source),
    }


def _candidate_slice(obstacle_event: dict[str, Any]) -> str:
    labels = {str(item.get("label_class", "")) for item in obstacle_event.get("candidates", ())}
    if labels.intersection({"person", "rider"}):
        return "PEDESTRIAN_CYCLIST_YIELD"
    return "FOLLOWING_CUT_IN"


def _track_field(obstacle_event: dict[str, Any], obstacle_sha: str, pointer: str) -> dict[str, Any]:
    candidates = obstacle_event.get("candidates", ())
    continuous = bool(candidates) and all(
        isinstance(item.get("track_samples"), list)
        and len(item["track_samples"]) >= 2
        and all(
            right["timestamp_us"] > left["timestamp_us"]
            for left, right in zip(item["track_samples"], item["track_samples"][1:])
        )
        for item in candidates
    )
    if continuous:
        return _status(
            "AVAILABLE_SOURCE_LINKED",
            _ref(obstacle_sha, pointer + "/candidates"),
            "CURRENT",
            "DATASET_RIG",
            "m_and_us",
            "SOURCE_LINKED",
            time_continuous=True,
        )
    return _status(
        "UNSUPPORTED",
        _ref(obstacle_sha, pointer),
        "CURRENT",
        "DATASET_RIG",
        "m_and_us",
        "MISSING_RELEVANT_ACTOR_OR_TRAFFIC_CONTROL_STATE",
        time_continuous=False,
    )


def _incomplete_record(
    *,
    episode_index: int,
    event_index: int,
    cohort_event: dict[str, Any],
    obstacle_event: dict[str, Any],
    clip_id: str,
    cohort_sha: str,
    obstacle_sha: str,
    catalog_sha: str,
) -> dict[str, Any]:
    pointer = f"/episodes/{episode_index}/events/{event_index}"
    hashes = _base_hashes(
        episode_index,
        event_index,
        cohort_event,
        obstacle_event,
        clip_id,
        cohort_sha,
        obstacle_sha,
    )
    timestamp = int(cohort_event["timestamp_us"])
    candidate_ref = _ref(obstacle_sha, pointer)
    fields = {
        "timestamps": _status(
            "AVAILABLE_SOURCE_LINKED",
            _ref(cohort_sha, pointer + "/timestamp_us"),
            "CURRENT",
            "DATASET_TIME",
            "us",
            "SOURCE_LINKED",
            timestamps_us=[timestamp],
        ),
        "ego_pose_and_speed": _status(
            "REVIEW_REQUIRED",
            _ref(cohort_sha, pointer + "/signal_at_event"),
            "CURRENT",
            "EGO_AT_MODEL_T0",
            "m_and_mps",
            "MISSING_TIME_ALIGNED_EGO_POSE",
        ),
        "relevant_actor_or_control_state": _track_field(
            obstacle_event, obstacle_sha, pointer
        ),
        "target_zone_or_lane_association": _status(
            "REVIEW_REQUIRED",
            candidate_ref,
            "CURRENT",
            "DATASET_RIG",
            "set_membership",
            "MISSING_VERIFIED_TARGET_ZONE_OR_LANE_ASSOCIATION",
            ambiguity_status="AMBIGUOUS",
        ),
        "conflict_stop_or_following_geometry": _status(
            "REVIEW_REQUIRED",
            candidate_ref,
            "CURRENT",
            "DATASET_RIG",
            "m",
            "MISSING_SLICE_SPECIFIC_CONFLICT_STOP_OR_FOLLOWING_GEOMETRY",
        ),
        "verified_coordinate_transform": _status(
            "UNSUPPORTED",
            candidate_ref,
            "CURRENT",
            "DATASET_RIG_TO_EGO_AT_MODEL_T0",
            "rigid_transform",
            "MISSING_SOURCE_BEARING_COORDINATE_TRANSFORM",
        ),
        "applicable_rule_scope": _status(
            "REVIEW_REQUIRED",
            _ref(catalog_sha, "/"),
            "NOT_TIME_VARYING",
            "NORMATIVE_SCOPE",
            "not_applicable",
            "MISSING_SCENE_JURISDICTION_ODD_AND_RULE_APPLICABILITY",
            scope_precondition_exception_status="REVIEW_REQUIRED",
        ),
        "recorded_rig_binding": _status(
            "UNSUPPORTED",
            candidate_ref,
            "NOT_TIME_VARYING",
            "RECORDED_RIG",
            "not_applicable",
            "MISSING_RECORDED_RIG_BINDING",
        ),
    }
    return {
        **hashes,
        "slice": _candidate_slice(obstacle_event),
        "outcome": "UNKNOWN",
        "fields": fields,
        "jurisdiction": {
            "country_code": "UNKNOWN",
            "source_ref": _ref(cohort_sha, f"/episodes/{episode_index}"),
        },
        "odd": {
            "scope_id": "REVIEW_REQUIRED",
            "status": "REVIEW_REQUIRED",
            "source_ref": _ref(cohort_sha, f"/episodes/{episode_index}"),
        },
        "rule_catalog": {
            "catalog_id": "guardsynth-kr-structured-road-v0.1",
            "version": "guardsynth-source-catalog-v0.1",
            "authority_class": "LEGAL",
            "jurisdiction_country_code": "KR",
            "source_status": "OFFICIAL_SOURCE_LINKED",
            "source_ref": _ref(catalog_sha, "/"),
        },
        "scope_compatibility": "REVIEW_REQUIRED_JURISDICTION_EVIDENCE",
        "recorded_rig_binding": {
            "binding_key": "UNAVAILABLE",
            "evidence_ref": candidate_ref,
        },
        "simulation_vehicle_binding": _simulation_binding(),
        "outcome_evidence": {
            "kind": "INCOMPLETE_SOURCE_PACKET",
            "evidence_refs": [_ref(cohort_sha, pointer)],
            "source_packet_complete": False,
            "freshness_result": "NOT_AN_APPROVED_UNKNOWN_OUTCOME",
        },
        "synthetic_required_field_fill": False,
        "prior_eligible": False,
        "local_candidate_basis": "TIME_ALIGNED_EVENT_SIGNAL_AND_DERIVED_ACTOR_CANDIDATES",
    }


def _adapter_index(closure: dict[str, Any]) -> int:
    index = closure.get("adapter_candidate_index")
    if isinstance(index, int) and not isinstance(index, bool):
        return index
    evidence_ref = closure.get("field_status", {}).get("ego_pose_and_speed", {}).get("evidence_ref", "")
    match = _CANDIDATE_POINTER_RE.search(str(evidence_ref))
    if match is None:
        raise ValueError("PRIOR_CLOSURE_ADAPTER_CANDIDATE_NOT_FOUND")
    return int(match.group(1))


def _bundle_map() -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for path in SOURCE_BUNDLE_ROOT.rglob("SCENE_SOURCE_BUNDLE.json"):
        digest = _sha256(path)
        result[digest] = _load(path)
    return result


def _prior_fields(
    closure: dict[str, Any],
    *,
    adapter_timestamp_us: int,
    bundle: dict[str, Any],
) -> tuple[dict[str, Any], bool]:
    original = closure["field_status"]
    timestamp_source = original["timestamps"]
    if "event_timestamp_us" in timestamp_source:
        timestamps = [int(timestamp_source["event_timestamp_us"])]
        timestamp_anchor = timestamps[0]
    else:
        rows = timestamp_source.get("values_us", ())
        first_row = rows[0] if rows and isinstance(rows[0], list) else rows
        timestamps = [int(value) for value in first_row]
        timestamp_anchor = max(int(value) for row in rows for value in row)
    bundle_timestamp = bundle.get("coordinate_transform", {}).get("event_timestamp_us")
    temporal_consistent = (
        abs(timestamp_anchor - adapter_timestamp_us) <= 100_000
        and isinstance(bundle_timestamp, int)
        and abs(bundle_timestamp - adapter_timestamp_us) <= 100_000
    )
    timestamps_status = "AVAILABLE_SOURCE_LINKED" if temporal_consistent else "CONFLICT"
    timestamps_reason = "SOURCE_LINKED" if temporal_consistent else "CROSS_EVENT_TIMESTAMP_EVIDENCE_CONFLICT"

    mapping = {
        "timestamps": "timestamps",
        "ego_pose_and_speed": "ego_pose_and_speed",
        "relevant_actor_or_control_state": "relevant_actor_tracks",
        "target_zone_or_lane_association": "target_zone_or_lane_association",
        "conflict_stop_or_following_geometry": "conflict_or_stop_geometry",
        "verified_coordinate_transform": "verified_coordinate_transform",
        "applicable_rule_scope": "applicable_rule_source_refs",
        "recorded_rig_binding": "exact_vehicle_binding",
    }
    result: dict[str, Any] = {}
    for target, source in mapping.items():
        item = original[source]
        status = item.get("status", "REVIEW_REQUIRED")
        reason = item.get("reason_code", "SOURCE_LINKED" if status == "AVAILABLE_SOURCE_LINKED" else "REVIEW_REQUIRED")
        frame, unit = {
            "timestamps": ("DATASET_TIME", "us"),
            "ego_pose_and_speed": ("EGO_AT_MODEL_T0", "m_and_mps"),
            "relevant_actor_or_control_state": ("DATASET_RIG", "m_and_us"),
            "target_zone_or_lane_association": ("DATASET_RIG", "set_membership"),
            "conflict_stop_or_following_geometry": ("DATASET_RIG", "m"),
            "verified_coordinate_transform": ("DATASET_RIG_TO_EGO_AT_MODEL_T0", "rigid_transform"),
            "applicable_rule_scope": ("NORMATIVE_SCOPE", "not_applicable"),
            "recorded_rig_binding": ("RECORDED_RIG", "not_applicable"),
        }[target]
        result[target] = _status(
            status,
            str(item.get("evidence_ref", "")),
            "NOT_TIME_VARYING" if target in {"applicable_rule_scope", "recorded_rig_binding"} else "CURRENT",
            frame,
            unit,
            str(reason),
        )
    result["timestamps"].update({
        "status": timestamps_status,
        "reason_code": timestamps_reason,
        "timestamps_us": timestamps,
    })
    result["relevant_actor_or_control_state"]["time_continuous"] = bool(
        original["relevant_actor_tracks"].get("time_series_preserved")
    )
    association = original["target_zone_or_lane_association"]
    result["target_zone_or_lane_association"]["ambiguity_status"] = (
        "UNAMBIGUOUS_SOURCE_LINKED"
        if association.get("status") == "AVAILABLE_SOURCE_LINKED"
        and association.get("association_cardinality", 0) > 0
        else "AMBIGUOUS"
    )
    transform = original["verified_coordinate_transform"]
    result["verified_coordinate_transform"]["inverse_closure_max_abs_error"] = transform.get(
        "inverse_closure_max_abs_error"
    )
    result["applicable_rule_scope"]["scope_precondition_exception_status"] = (
        "SATISFIED"
        if original["applicable_rule_source_refs"].get("status") == "AVAILABLE_SOURCE_LINKED"
        else "REVIEW_REQUIRED"
    )
    return result, temporal_consistent


def _apply_prior_closures(
    records: dict[tuple[int, int], dict[str, Any]],
    adapter: dict[str, Any],
) -> None:
    bundles = _bundle_map()
    simulation = _simulation_binding()
    for path in PRIOR_CLOSURES:
        closure = _load(path)
        index = _adapter_index(closure)
        candidate = adapter["candidates"][index]
        match = _EPISODE_EVENT_RE.fullmatch(candidate["candidate_id"])
        if match is None:
            raise ValueError("PRIOR_CLOSURE_EVENT_ID_INVALID")
        key = (int(match.group(1)), int(match.group(2)))
        if key not in records:
            raise ValueError("PRIOR_CLOSURE_EVENT_NOT_IN_LOCAL_INDEX")
        transform_ref = closure["field_status"]["verified_coordinate_transform"]["evidence_ref"]
        bundle_digest = str(transform_ref).split(":", 1)[1].split("#", 1)[0]
        bundle = bundles.get(bundle_digest)
        if bundle is None:
            raise ValueError("PRIOR_CLOSURE_SOURCE_BUNDLE_NOT_FOUND")
        adapter_timestamp_us = round(float(candidate["context_graph"]["timestamp_s"]) * 1_000_000)
        fields, temporal_consistent = _prior_fields(
            closure,
            adapter_timestamp_us=adapter_timestamp_us,
            bundle=bundle,
        )
        record = records[key]
        rule = closure["field_status"]["applicable_rule_source_refs"]
        source_ref = fields["applicable_rule_scope"]["evidence_ref"]
        primary_rule = str(rule.get("primary_rule_source_id", ""))
        country = str(bundle.get("dataset", {}).get("country", "UNKNOWN"))
        country_code = "US" if country == "United States" else "UNKNOWN"
        legal_rule = primary_rule.startswith("CA-")
        recorded_key = closure["field_status"]["exact_vehicle_binding"].get(
            "vehicle_binding_key", "UNAVAILABLE"
        )
        record.update({
            "slice": "PEDESTRIAN_CYCLIST_YIELD",
            "outcome": "HAZARD_TRUE_ACTIVE",
            "fields": fields,
            "jurisdiction": {
                "country_code": country_code,
                "subdivision_code": "US-CA" if legal_rule else None,
                "source_ref": _ref(bundle_digest, "/dataset/country"),
            },
            "odd": {
                "scope_id": "URBAN_SUBURBAN_STRUCTURED_ROAD",
                "status": "IN_SCOPE",
                "source_ref": _ref(bundle_digest, "/dataset"),
            },
            "rule_catalog": {
                "catalog_id": (
                    "california-vehicle-code-conditional"
                    if legal_rule
                    else "simulation-corridor-system-requirement"
                ),
                "version": str(
                    rule.get("rule_source_refs", [{}])[0].get("version", "snapshot-bound")
                ),
                "authority_class": (
                    "LEGAL" if legal_rule else "VERIFIED_SYSTEM_REQUIREMENT"
                ),
                "jurisdiction_country_code": country_code if legal_rule else "ANY",
                "source_status": (
                    "OFFICIAL_SOURCE_LINKED"
                    if legal_rule
                    else "VERIFIED_SOURCE_LINKED"
                ),
                "source_ref": source_ref,
            },
            "scope_compatibility": (
                "JURISDICTION_SOURCE_COMPATIBLE"
                if country_code != "UNKNOWN"
                else "REVIEW_REQUIRED_JURISDICTION_EVIDENCE"
            ),
            "recorded_rig_binding": {
                "binding_key": str(recorded_key),
                "evidence_ref": fields["recorded_rig_binding"]["evidence_ref"],
            },
            "simulation_vehicle_binding": simulation,
            "outcome_evidence": {
                "kind": "ACTIVE_HAZARD_WITNESS",
                "evidence_refs": [
                    fields["target_zone_or_lane_association"]["evidence_ref"]
                ],
                "source_packet_complete": temporal_consistent,
                "time_continuous": True,
                "lifecycle_states": ["ACTIVE"],
            },
            "synthetic_required_field_fill": False,
            "prior_eligible": True,
            "local_candidate_basis": "PRIOR_M13_SOURCE_CLOSURE_REAUDITED",
            "cross_field_temporal_consistency": temporal_consistent,
        })


def _build_records() -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, str]]:
    required_inputs = (
        COHORT,
        OBSTACLES,
        PACKETS,
        MEDIA_MANIFEST,
        ADAPTER,
        SIMULATION_PROFILE,
        KR_CATALOG,
        CASCADE_ALIGNMENT_AUDIT,
        SENSOR_MATERIALIZATION_MANIFEST,
        SENSOR_EVIDENCE_AUDIT,
        CALIBRATION_MANIFEST,
        CALIBRATION_ASSOCIATION_AUDIT,
        ASSOCIATION_REVIEW_QUEUE,
        RESERVE_SENSOR_MATERIALIZATION_MANIFEST,
        RESERVE_SENSOR_EVIDENCE_AUDIT,
        RESERVE_CALIBRATION_MANIFEST,
        RESERVE_CALIBRATION_ASSOCIATION_AUDIT,
        RESERVE_ASSOCIATION_REVIEW_QUEUE,
        ATTRITION_RESERVE_EVIDENCE_AUDIT,
        ATTRITION_RESERVE_REVIEW_QUEUE,
        PHYSICAL_AI_AV_DEVKIT,
        PHYSICAL_AI_FEATURE_CATALOG,
        *PRIOR_CLOSURES,
    )
    if any(not path.is_file() for path in required_inputs):
        raise FileNotFoundError("M16_LOCAL_AUDIT_INPUT_MISSING")
    cohort = _load(COHORT)
    obstacles = _load(OBSTACLES)
    packets = _load(PACKETS)
    media = _load(MEDIA_MANIFEST)
    adapter = _load(ADAPTER)
    cohort_sha = _sha256(COHORT)
    obstacle_sha = _sha256(OBSTACLES)
    catalog_sha = _sha256(KR_CATALOG)
    records: dict[tuple[int, int], dict[str, Any]] = {}
    for episode_index, (cohort_episode, obstacle_episode) in enumerate(
        zip(cohort["episodes"], obstacles["episodes"])
    ):
        if cohort_episode["clip_id"] != obstacle_episode["clip_id"]:
            raise ValueError("COHORT_OBSTACLE_EPISODE_MISMATCH")
        if len(cohort_episode["events"]) != len(obstacle_episode["events"]):
            raise ValueError("COHORT_OBSTACLE_EVENT_COUNT_MISMATCH")
        for event_index, (cohort_event, obstacle_event) in enumerate(
            zip(cohort_episode["events"], obstacle_episode["events"])
        ):
            if int(cohort_event["timestamp_us"]) != int(obstacle_event["timestamp_us"]):
                raise ValueError("COHORT_OBSTACLE_EVENT_TIMESTAMP_MISMATCH")
            records[(episode_index, event_index)] = _incomplete_record(
                episode_index=episode_index,
                event_index=event_index,
                cohort_event=cohort_event,
                obstacle_event=obstacle_event,
                clip_id=cohort_episode["clip_id"],
                cohort_sha=cohort_sha,
                obstacle_sha=obstacle_sha,
                catalog_sha=catalog_sha,
            )
    _apply_prior_closures(records, adapter)

    media_by_name = {item["image"]: item for item in media}
    alias_count = 0
    for packet in packets["packets"]:
        item = media_by_name.get(packet["source_review"]["image_filename"])
        if item is None:
            raise ValueError("IMAGE_PACKET_MEDIA_PROVENANCE_MISSING")
        episode_match = re.search(r"(\d+)", str(item.get("episode", "")))
        if episode_match is None:
            raise ValueError("IMAGE_PACKET_EPISODE_INVALID")
        episode_index = int(episode_match.group(1))
        flattened = [
            int(value)
            for row in item["absolute_timestamps_us"]
            for value in (row if isinstance(row, list) else [row])
        ]
        anchor = max(flattened)
        candidates = [
            (abs(int(event["timestamp_us"]) - anchor), event_index)
            for event_index, event in enumerate(cohort["episodes"][episode_index]["events"])
        ]
        distance, event_index = min(candidates)
        if distance > 100_000 or (episode_index, event_index) not in records:
            raise ValueError("IMAGE_PACKET_EVENT_ALIAS_NOT_DETERMINISTIC")
        alias_count += 1
    input_hashes = {
        "cohort_conformance": cohort_sha,
        "obstacle_candidates": obstacle_sha,
        "partial_scene_packets": _sha256(PACKETS),
        "media_manifest": _sha256(MEDIA_MANIFEST),
        "adapter_result": _sha256(ADAPTER),
        "kr_catalog": catalog_sha,
        "simulation_assurance_profile": _sha256(SIMULATION_PROFILE),
        "cascade_alignment_audit": _sha256(CASCADE_ALIGNMENT_AUDIT),
        "sensor_materialization_manifest": _sha256(SENSOR_MATERIALIZATION_MANIFEST),
        "sensor_evidence_audit": _sha256(SENSOR_EVIDENCE_AUDIT),
        "calibration_manifest": _sha256(CALIBRATION_MANIFEST),
        "calibration_association_audit": _sha256(CALIBRATION_ASSOCIATION_AUDIT),
        "association_review_queue": _sha256(ASSOCIATION_REVIEW_QUEUE),
        "reserve_sensor_materialization_manifest": _sha256(
            RESERVE_SENSOR_MATERIALIZATION_MANIFEST
        ),
        "reserve_sensor_evidence_audit": _sha256(RESERVE_SENSOR_EVIDENCE_AUDIT),
        "reserve_calibration_manifest": _sha256(RESERVE_CALIBRATION_MANIFEST),
        "reserve_calibration_association_audit": _sha256(
            RESERVE_CALIBRATION_ASSOCIATION_AUDIT
        ),
        "attrition_reserve_evidence_audit": _sha256(
            ATTRITION_RESERVE_EVIDENCE_AUDIT
        ),
        "attrition_reserve_review_queue": _sha256(
            ATTRITION_RESERVE_REVIEW_QUEUE
        ),
        "physical_ai_av_devkit_dataset_module": _sha256(PHYSICAL_AI_AV_DEVKIT),
        "physical_ai_feature_catalog": _sha256(PHYSICAL_AI_FEATURE_CATALOG),
        "prior_closures_combined": hashlib.sha256(
            "".join(_sha256(path) for path in PRIOR_CLOSURES).encode()
        ).hexdigest(),
    }
    audit_stats = {
        "event_source_record_count": len(records),
        "image_source_alias_count": alias_count,
        "candidate_source_record_count": len(records) + alias_count,
        "source_alias_deduplicated_count": alias_count,
        "distinct_candidate_count": len(records),
        "local_cascade_annotation_file_count": len(list((CASCADE_ROOT / "data").rglob("*.json"))),
        "local_physicalai_materialized_event_count": len(records),
        "local_shortlisted_sensor_candidate_count": 59,
        "raw_video_copied": True,
        "network_or_credential_use_performed": True,
    }
    return list(records.values()), audit_stats, input_hashes


def _annotation_candidate_screen(
    slice_targets: dict[str, int],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Join local CASCADE annotations to OOD metadata and build a sensor shortlist."""
    import pyarrow.parquet as parquet

    annotations: dict[str, tuple[dict[str, Any], str]] = {}
    for path in sorted((CASCADE_ROOT / "data").rglob("*.json")):
        payload = _load(path)
        clip_id = payload.get("video", {}).get("clip_id")
        annotation = payload.get("annotation")
        if not isinstance(clip_id, str) or not isinstance(annotation, dict):
            raise ValueError("CASCADE_ANNOTATION_SCHEMA_INVALID")
        if clip_id in annotations:
            raise ValueError("CASCADE_ANNOTATION_CLIP_DUPLICATE")
        annotations[clip_id] = (annotation, _sha256(path))

    data_collection = {
        row["clip_id"]: row
        for row in parquet.read_table(
            PHYSICALAI_ROOT / "metadata/data_collection.parquet"
        ).to_pylist()
    }
    feature_presence = {
        row["clip_id"]: row
        for row in parquet.read_table(
            PHYSICALAI_ROOT / "metadata/feature_presence.parquet"
        ).to_pylist()
    }
    clip_index = {
        row["clip_id"]: row
        for row in parquet.read_table(
            PHYSICALAI_ROOT / "clip_index.parquet"
        ).to_pylist()
    }
    candidates: list[dict[str, Any]] = []
    for row in parquet.read_table(
        PHYSICALAI_ROOT / "reasoning/ood_reasoning.parquet"
    ).to_pylist():
        clip_id = row.get("clip_id")
        if clip_id not in annotations:
            continue
        events = json.loads(row["events"]) if row.get("events") else []
        if not isinstance(events, list):
            raise ValueError("OOD_REASONING_EVENTS_INVALID")
        annotation, annotation_sha = annotations[clip_id]
        metadata = data_collection.get(clip_id)
        features = feature_presence.get(clip_id)
        index = clip_index.get(clip_id)
        if metadata is None or features is None or index is None:
            raise ValueError("CASCADE_PHYSICALAI_METADATA_JOIN_INCOMPLETE")
        sensor_feature_eligible = all(
            features.get(feature) is True for feature in REQUIRED_SENSOR_FEATURES
        )
        for event in events:
            timestamp = event.get("event_start_timestamp")
            if isinstance(timestamp, bool) or not isinstance(timestamp, int):
                raise ValueError("OOD_EVENT_TIMESTAMP_INVALID")
            classification = classify_annotation_candidate(annotation, timestamp)
            candidates.append({
                "clip_id": clip_id,
                "candidate_digest": candidate_digest(clip_id, timestamp),
                "annotation_sha256": annotation_sha,
                "event_timestamp_us": timestamp,
                "country": str(metadata.get("country") or "UNKNOWN"),
                "chunk": int(index["chunk"]),
                "sensor_feature_eligible": sensor_feature_eligible,
                **classification,
            })
    if len(candidates) != 135:
        raise ValueError("ANNOTATION_OOD_EVENT_COUNT_MISMATCH")
    if len({item["clip_id"] for item in candidates}) != 107:
        raise ValueError("ANNOTATION_OOD_CLIP_COUNT_MISMATCH")
    if len({item["clip_id"] for item in candidates if item["sensor_feature_eligible"]}) != 106:
        raise ValueError("ANNOTATION_SENSOR_ELIGIBLE_CLIP_COUNT_MISMATCH")

    shortlist = select_sensor_shortlist(candidates, slice_targets=slice_targets)
    attrition_reserve = build_attrition_reserve(candidates, shortlist)
    annotation_collection_sha256 = hashlib.sha256(
        "".join(sorted(annotation_sha for _, annotation_sha in annotations.values())).encode()
    ).hexdigest()
    shortlisted_chunks = sorted({item["chunk"] for item in shortlist["records"]})
    sensor_materialized = SENSOR_MATERIALIZATION_MANIFEST.is_file()
    shortlist.update({
        "required_sensor_features": list(REQUIRED_SENSOR_FEATURES),
        "unique_chunk_count": len(shortlisted_chunks),
        "estimated_sensor_package_count": len(shortlisted_chunks)
        * len(REQUIRED_SENSOR_FEATURES),
        "download_status": (
            "MATERIALIZED_SELECTED_MEMBERS_ONLY"
            if sensor_materialized
            else "AWAITING_EXPLICIT_SENSOR_DOWNLOAD_AUTHORIZATION"
        ),
        "network_or_credential_use_performed_for_sensor_download": sensor_materialized,
        "full_package_download_performed": False,
        "claim_scope": "SENSOR_DOWNLOAD_WORK_ORDER_NOT_SCENE_ELIGIBILITY_OR_SAFETY",
    })
    reserve_materialization_records = attrition_reserve["materialization_records"]
    reserve_chunks = sorted({item["chunk"] for item in reserve_materialization_records})
    reserve_shortlist = {
        "selection_version": "guardsynth-m16-reserve-sensor-shortlist-v0.1",
        "required_sensor_features": list(REQUIRED_SENSOR_FEATURES),
        "selected_event_count": len(reserve_materialization_records),
        "selected_unique_clip_count": len(reserve_materialization_records),
        "unique_chunk_count": len(reserve_chunks),
        "estimated_sensor_package_count": len(reserve_chunks)
        * len(REQUIRED_SENSOR_FEATURES),
        "download_status": (
            "MATERIALIZED_SELECTED_MEMBERS_ONLY"
            if RESERVE_SENSOR_MATERIALIZATION_MANIFEST.is_file()
            else "AWAITING_SELECTED_MEMBER_MATERIALIZATION"
        ),
        "full_package_download_performed": False,
        "records": reserve_materialization_records,
        "claim_scope": "RESERVE_SENSOR_DOWNLOAD_WORK_ORDER_NOT_SCENE_ELIGIBILITY_OR_SAFETY",
    }
    attrition_reserve = {
        **attrition_reserve,
        "new_clip_unique_chunk_count": len(reserve_chunks),
        "estimated_additional_sensor_package_count": reserve_shortlist[
            "estimated_sensor_package_count"
        ],
    }
    public_summary = deidentified_screen_summary(candidates, shortlist)
    public_summary.update({
        "locally_materialized_annotation_count": len(annotations),
        "required_sensor_feature_count": len(REQUIRED_SENSOR_FEATURES),
        "shortlist_unique_chunk_count": len(shortlisted_chunks),
        "estimated_sensor_package_count": shortlist["estimated_sensor_package_count"],
        "sensor_download_status": shortlist["download_status"],
    })
    restricted_screen = {
        **public_summary,
        "annotation_collection_sha256": annotation_collection_sha256,
        "records": [
            {
                key: item[key]
                for key in (
                    "candidate_digest",
                    "annotation_sha256",
                    "event_timestamp_us",
                    "country",
                    "chunk",
                    "sensor_feature_eligible",
                    "candidate_slices",
                    "slice_evidence",
                    "classification_status",
                    "outcome_status",
                    "final_outcome_assigned",
                )
            }
            for item in candidates
        ],
    }
    return restricted_screen, shortlist, attrition_reserve, reserve_shortlist


def _licensed_candidate_screen(
    audit_stats: dict[str, Any], annotation_screen: dict[str, Any]
) -> dict[str, Any]:
    """Summarize licensed candidates without treating absent sensor assets as local evidence."""
    audit = _load(CASCADE_ALIGNMENT_AUDIT)
    mapping = audit.get("mapping", {})
    availability = audit.get("availability", {})
    candidate_clip_count = availability.get(
        "cascade_ood_human_coc_overlap_clip_count"
    )
    candidate_event_count = availability.get(
        "cascade_ood_human_coc_overlap_event_count"
    )
    sensor_eligible_clip_count = availability.get(
        "aligned_sensor_eligible_clip_count"
    )
    locally_selected_event_count = availability.get(
        "selected_human_coc_event_count"
    )
    expected = (
        mapping.get("annotation_json_count"),
        mapping.get("resolved_unique_reference_count"),
        candidate_clip_count,
        candidate_event_count,
        sensor_eligible_clip_count,
        locally_selected_event_count,
    )
    if not all(isinstance(value, int) and value >= 0 for value in expected):
        raise ValueError("LICENSED_CANDIDATE_AUDIT_COUNTS_INVALID")
    if sensor_eligible_clip_count > candidate_clip_count:
        raise ValueError("LICENSED_CANDIDATE_SENSOR_COUNT_INVALID")
    raw_sensor_package_count = sum(
        1
        for path in PHYSICALAI_ROOT.rglob("*")
        if path.is_file() and path.suffix.lower() in {".zip", ".tar"}
    )
    sensor_materialization = _load(SENSOR_MATERIALIZATION_MANIFEST)
    sensor_evidence_audit = _load(SENSOR_EVIDENCE_AUDIT)
    calibration_manifest = _load(CALIBRATION_MANIFEST)
    calibration_audit = _load(CALIBRATION_ASSOCIATION_AUDIT)
    reserve_sensor_materialization = _load(RESERVE_SENSOR_MATERIALIZATION_MANIFEST)
    reserve_sensor_audit = _load(RESERVE_SENSOR_EVIDENCE_AUDIT)
    reserve_calibration_manifest = _load(RESERVE_CALIBRATION_MANIFEST)
    reserve_calibration_audit = _load(RESERVE_CALIBRATION_ASSOCIATION_AUDIT)
    attrition_reserve_audit = _load(ATTRITION_RESERVE_EVIDENCE_AUDIT)
    if any((
        sensor_materialization.get("selected_candidate_count") != 59,
        sensor_materialization.get("materialized_member_count") != 354,
        sensor_evidence_audit.get("audited_candidate_count") != 59,
        sensor_evidence_audit.get("temporal_closure_candidate_count") != 59,
        sensor_evidence_audit.get("source_complete_8_of_8_candidate_count") != 0,
        sensor_evidence_audit.get("final_outcome_assigned_count") != 0,
        calibration_manifest.get("selected_candidate_count") != 59,
        calibration_manifest.get("materialized_candidate_feature_count") != 295,
        calibration_audit.get("calibration_5_of_5_candidate_count") != 59,
        calibration_audit.get("recorded_rig_binding_available_count") != 59,
        calibration_audit.get("verified_coordinate_transform_count") != 0,
        reserve_sensor_materialization.get("selected_candidate_count") != 22,
        reserve_sensor_materialization.get("materialized_member_count") != 132,
        reserve_sensor_audit.get("audited_candidate_count") != 22,
        reserve_sensor_audit.get("temporal_closure_candidate_count") != 22,
        reserve_calibration_manifest.get("selected_candidate_count") != 22,
        reserve_calibration_manifest.get("materialized_candidate_feature_count") != 110,
        reserve_calibration_audit.get("calibration_5_of_5_candidate_count") != 22,
        reserve_calibration_audit.get("recorded_rig_binding_available_count") != 22,
        reserve_calibration_audit.get("verified_coordinate_transform_count") != 0,
        attrition_reserve_audit.get("audited_reserve_event_count") != 39,
        attrition_reserve_audit.get("temporal_closure_event_count") != 39,
        attrition_reserve_audit.get("calibration_5_of_5_event_count") != 39,
        attrition_reserve_audit.get("recorded_rig_binding_available_event_count") != 39,
        attrition_reserve_audit.get("verified_coordinate_transform_event_count") != 0,
        attrition_reserve_audit.get("source_complete_8_of_8_event_count") != 0,
        attrition_reserve_audit.get("final_outcome_assigned_count") != 0,
    )):
        raise ValueError("M16_SENSOR_MATERIALIZATION_AUDIT_INVALID")
    locally_materialized_additional = 0
    return {
        "screen_version": "guardsynth-m16-licensed-candidate-screen-v0.1",
        "mapped_annotation_clip_count": mapping["resolved_unique_reference_count"],
        "licensed_candidate_clip_count": candidate_clip_count,
        "licensed_candidate_event_count": candidate_event_count,
        "sensor_eligible_candidate_clip_count": sensor_eligible_clip_count,
        "locally_selected_candidate_event_count": locally_selected_event_count,
        "locally_materialized_cascade_annotation_count": audit_stats[
            "local_cascade_annotation_file_count"
        ],
        "local_raw_sensor_package_count": raw_sensor_package_count,
        "materialized_sensor_candidate_count": sensor_materialization[
            "selected_candidate_count"
        ],
        "materialized_sensor_member_count": sensor_materialization[
            "materialized_member_count"
        ],
        "materialized_sensor_bytes": sensor_materialization["materialized_bytes"],
        "sensor_temporal_closure_candidate_count": sensor_evidence_audit[
            "temporal_closure_candidate_count"
        ],
        "sensor_source_complete_8_of_8_candidate_count": sensor_evidence_audit[
            "source_complete_8_of_8_candidate_count"
        ],
        "sensor_final_outcome_assigned_count": sensor_evidence_audit[
            "final_outcome_assigned_count"
        ],
        "calibration_candidate_count": calibration_manifest[
            "selected_candidate_count"
        ],
        "calibration_candidate_feature_count": calibration_manifest[
            "materialized_candidate_feature_count"
        ],
        "calibration_materialized_bytes": calibration_manifest["materialized_bytes"],
        "recorded_rig_binding_available_count": calibration_audit[
            "recorded_rig_binding_available_count"
        ],
        "verified_coordinate_transform_count": calibration_audit[
            "verified_coordinate_transform_count"
        ],
        "calibration_variant_review_count": calibration_audit[
            "calibration_variant_review_count"
        ],
        "association_review_status_counts": calibration_audit[
            "association_review_status_counts"
        ],
        "reserve_materialized_sensor_clip_count": reserve_sensor_materialization[
            "selected_candidate_count"
        ],
        "reserve_materialized_sensor_member_count": reserve_sensor_materialization[
            "materialized_member_count"
        ],
        "reserve_materialized_sensor_bytes": reserve_sensor_materialization[
            "materialized_bytes"
        ],
        "reserve_sensor_temporal_closure_candidate_count": reserve_sensor_audit[
            "temporal_closure_candidate_count"
        ],
        "reserve_calibration_candidate_count": reserve_calibration_manifest[
            "selected_candidate_count"
        ],
        "reserve_calibration_feature_count": reserve_calibration_manifest[
            "materialized_candidate_feature_count"
        ],
        "reserve_calibration_materialized_bytes": reserve_calibration_manifest[
            "materialized_bytes"
        ],
        "classified_event_temporal_closure_count": (
            sensor_evidence_audit["temporal_closure_candidate_count"]
            + attrition_reserve_audit["temporal_closure_event_count"]
        ),
        "classified_event_calibration_closure_count": (
            calibration_audit["calibration_5_of_5_candidate_count"]
            + attrition_reserve_audit["calibration_5_of_5_event_count"]
        ),
        "classified_event_recorded_rig_binding_count": (
            calibration_audit["recorded_rig_binding_available_count"]
            + attrition_reserve_audit["recorded_rig_binding_available_event_count"]
        ),
        "classified_event_verified_transform_count": 0,
        "classified_event_source_complete_8_of_8_count": 0,
        "classified_event_final_outcome_assigned_count": 0,
        "classified_event_association_review_status_counts": dict(sorted(
            (
                Counter(calibration_audit["association_review_status_counts"])
                + Counter(attrition_reserve_audit["association_review_status_counts"])
            ).items()
        )),
        "locally_materialized_additional_candidate_count": locally_materialized_additional,
        "annotation_screen": {
            key: value for key, value in annotation_screen.items() if key != "records"
        },
        "acquisition_session_status": "ATTRITION_RESERVE_MATERIALIZED_SOURCE_REVIEW_REQUIRED",
        "blocker": "CALIBRATION_VARIANT_ASSOCIATION_RULE_SCOPE_AND_OUTCOME_UNRESOLVED",
        "required_action": (
            "Obtain upstream basis for online/offline calibration selection and complete human "
            "actor/control-to-lane association review; then bind jurisdiction-matched authority "
            "and outcome lifecycle witnesses."
        ),
        "network_or_credential_use_performed": True,
        "synthetic_required_field_fill_count": 0,
        "claim_scope": "CANDIDATE_SCREEN_NOT_SCENE_ELIGIBILITY_OR_VEHICLE_SAFETY",
    }


def _source_closure(manifest: dict[str, Any]) -> dict[str, Any]:
    return {
        "closure_version": "guardsynth-m16-source-closure-v0.1",
        "required_field_count": len(REQUIRED_EVIDENCE_FIELDS),
        "required_fields": list(REQUIRED_EVIDENCE_FIELDS),
        "candidate_count": manifest["candidate_count"],
        "source_complete_8_of_8_count": manifest["source_complete_count"],
        "synthetic_required_field_fill_count": manifest["synthetic_required_field_fill_count"],
        "records": [
            {
                "scene_hash": record["scene_hash"],
                "source_complete": record["source_complete"],
                "field_status": {
                    name: record["fields"].get(name, {}).get("status", "UNSUPPORTED")
                    for name in REQUIRED_EVIDENCE_FIELDS
                },
                "exclusion_reasons": list(record["exclusion_reasons"]),
            }
            for record in manifest["records"]
        ],
        "claim_scope": CLAIM_SCOPE,
    }


def _scope_audit(manifest: dict[str, Any]) -> dict[str, Any]:
    prior = [record for record in manifest["records"] if record.get("prior_eligible")]
    return {
        "scope_audit_version": "guardsynth-m16-scope-audit-v0.2",
        "scope_policy": {
            "jurisdiction_allowlist": "ANY_COUNTRY",
            "country_quota": None,
            "scene_jurisdiction_source_required": True,
            "legal_rule_jurisdiction_match_required": True,
            "verified_system_requirement_may_be_jurisdiction_independent": True,
        },
        "prior_eligible_reaudited_count": len(prior),
        "jurisdiction_source_compatible_count": sum(
            record["scope_compatibility"] == "JURISDICTION_SOURCE_COMPATIBLE"
            for record in prior
        ),
        "excluded_jurisdiction_or_odd_mismatch_count": sum(
            record["scope_compatibility"] == "EXCLUDED_JURISDICTION_OR_ODD_MISMATCH"
            for record in prior
        ),
        "review_required_jurisdiction_evidence_count": sum(
            record["scope_compatibility"]
            == "REVIEW_REQUIRED_JURISDICTION_EVIDENCE"
            for record in prior
        ),
        "prior_records": [
            {
                "scene_hash": record["scene_hash"],
                "source_complete": record["source_complete"],
                "eligible": record["eligible"],
                "scope_compatibility": record["scope_compatibility"],
                "cross_field_temporal_consistency": record.get(
                    "cross_field_temporal_consistency"
                ),
                "exclusion_reasons": list(record["exclusion_reasons"]),
            }
            for record in prior
        ],
        "scope_change_performed": True,
        "scope_decision_required": False,
        "claim_scope": "MULTI_JURISDICTION_SOURCE_COMPATIBILITY_AUDIT_NOT_LEGAL_ADVICE",
    }


def _gap_manifest(
    manifest: dict[str, Any],
    binding: dict[str, Any],
    audit_stats: dict[str, Any],
    licensed_screen: dict[str, Any],
) -> dict[str, Any]:
    missing_counts: Counter[str] = Counter()
    for record in manifest["records"]:
        for name in REQUIRED_EVIDENCE_FIELDS:
            if record["fields"].get(name, {}).get("status") != "AVAILABLE_SOURCE_LINKED":
                missing_counts[name] += 1
    orders = {
        "ego_pose_and_speed": (
            "NVIDIA_PHYSICALAI_LICENSED_SOURCE_OWNER",
            "Materialize time-aligned egomotion pose and speed for each event without copying video.",
            "Verify monotonic timestamps, pose frame, speed unit, and event-to-model-t0 alignment.",
        ),
        "relevant_actor_or_control_state": (
            "NVIDIA_CASCADE_OR_PHYSICALAI_SOURCE_OWNER",
            "Materialize continuous actor tracks or traffic-control state for the event window.",
            "Verify source hash, temporal continuity, identity continuity, and state freshness.",
        ),
        "target_zone_or_lane_association": (
            "GUARDSYNTH_DATA_CURATOR_WITH_SOURCE_REVIEWER",
            "Bind the source-bearing actor/control to the applicable target zone or lane.",
            "Run slice-specific association and preserve ambiguity or conflicting sources.",
        ),
        "conflict_stop_or_following_geometry": (
            "GUARDSYNTH_SLICE_ADAPTER_OWNER",
            "Produce slice-specific conflict, stop-boundary, or following geometry from sourced tracks/map.",
            "Check unit/frame, recomputation, and boundary cases for the selected slice.",
        ),
        "verified_coordinate_transform": (
            "NVIDIA_PHYSICALAI_CALIBRATION_SOURCE_OWNER",
            "Materialize calibration and egomotion needed for event-to-model-t0 transform.",
            "Verify rigid-transform inverse closure at or below 1e-9 and source-frame identity.",
        ),
        "applicable_rule_scope": (
            "GUARDSYNTH_SCOPE_AND_RULE_CATALOG_OWNER",
            "Acquire scene jurisdiction/ODD evidence and evaluate the matching jurisdiction catalog or verified system requirement.",
            "Require scene-source jurisdiction compatibility, versioned authority, preconditions, and exceptions.",
        ),
        "recorded_rig_binding": (
            "NVIDIA_PHYSICALAI_CALIBRATION_SOURCE_OWNER",
            "Materialize source-bearing rig configuration for the exact recorded clip.",
            "Recompute the binding digest and keep it distinct from simulation assurance.",
        ),
    }
    return {
        "gap_manifest_version": "guardsynth-m16-acquisition-gap-v0.1",
        **audit_stats,
        "missing_field_candidate_counts": dict(sorted(missing_counts.items())),
        "acquisition_work_orders": [
            {
                "field": field,
                "affected_candidate_count": missing_counts[field],
                "required_source_owner": owner,
                "acquisition_method": method,
                "verification_method": verification,
            }
            for field, (owner, method, verification) in orders.items()
            if missing_counts[field]
        ],
        "scope_work_order": {
            "required_source_owner": "GUARDSYNTH_SCOPE_AND_RULE_CATALOG_OWNER",
            "gap": "REMAINING_SCENES_REQUIRE_JURISDICTION_MATCHED_RULE_SOURCE_AND_FIELD_CLOSURE",
            "acquisition_method": "Acquire source-complete scenes from any country and bind each to its matching official catalog or verified system requirement.",
            "verification_method": "Re-run per-scene jurisdiction, ODD, catalog, precondition, and exception audit.",
        },
        "licensed_materialization_work_order": {
            "candidate_event_count": licensed_screen["licensed_candidate_event_count"],
            "sensor_eligible_candidate_clip_count": licensed_screen[
                "sensor_eligible_candidate_clip_count"
            ],
            "locally_materialized_additional_candidate_count": licensed_screen[
                "locally_materialized_additional_candidate_count"
            ],
            "required_source_owner": "NVIDIA_LICENSED_DATA_OWNER",
            "acquisition_method": licensed_screen["required_action"],
            "verification_method": (
                "Hash every materialized member, rebuild per-event source bundles, and rerun "
                "the 8-field eligibility and joint-slot audit."
            ),
            "network_or_credential_use_performed": licensed_screen[
                "network_or_credential_use_performed"
            ],
        },
        "joint_cell_shortfall": dict(binding["joint_cell_shortfall"]),
        "slice_shortfall": dict(binding["slice_shortfall"]),
        "outcome_shortfall": dict(binding["outcome_shortfall"]),
        "synthetic_required_field_fill_count": 0,
        "claim_scope": CLAIM_SCOPE,
    }


def _git_revision() -> tuple[str, str]:
    revision = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    dirty = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    return revision, "WORKSPACE_WITH_UNCOMMITTED_CHANGES" if dirty else "CLEAN"


def execute(
    *,
    restricted_output_dir: Path,
    public_output_dir: Path | None,
    run_id: str,
    test_results: list[dict[str, Any]],
) -> dict[str, Any]:
    if restricted_output_dir.exists() or (
        public_output_dir is not None and public_output_dir.exists()
    ):
        raise FileExistsError("refusing to overwrite an existing M16 acquisition run")
    records, audit_stats, input_hashes = _build_records()
    eligibility = build_scene_eligibility_manifest(records)
    slot_binding = bind_eligible_scenes_to_slots(
        eligibility, build_pilot_slot_manifest()
    )
    (
        annotation_screen,
        sensor_shortlist,
        attrition_reserve,
        reserve_shortlist,
    ) = _annotation_candidate_screen(
        slot_binding["slice_shortfall"]
    )
    sensor_materialization = _load(SENSOR_MATERIALIZATION_MANIFEST)
    sensor_evidence_audit = _load(SENSOR_EVIDENCE_AUDIT)
    calibration_manifest = _load(CALIBRATION_MANIFEST)
    calibration_audit = _load(CALIBRATION_ASSOCIATION_AUDIT)
    association_queue = _load(ASSOCIATION_REVIEW_QUEUE)
    reserve_sensor_materialization = _load(RESERVE_SENSOR_MATERIALIZATION_MANIFEST)
    reserve_sensor_evidence_audit = _load(RESERVE_SENSOR_EVIDENCE_AUDIT)
    reserve_calibration_manifest = _load(RESERVE_CALIBRATION_MANIFEST)
    reserve_calibration_audit = _load(RESERVE_CALIBRATION_ASSOCIATION_AUDIT)
    reserve_association_queue = _load(RESERVE_ASSOCIATION_REVIEW_QUEUE)
    attrition_reserve_evidence_audit = _load(ATTRITION_RESERVE_EVIDENCE_AUDIT)
    attrition_reserve_review_queue = _load(ATTRITION_RESERVE_REVIEW_QUEUE)
    calibration_variant_source_audit = audit_calibration_variant_sources([
        {
            "source_id": "NVIDIA_PHYSICALAI_AV_DATASET_CARD_26_03",
            "source_ref": (
                "https://huggingface.co/datasets/nvidia/"
                "PhysicalAI-Autonomous-Vehicles"
            ),
            "official_source": True,
            "offline_optimized_feature_documented": True,
            "general_variant_selection_rule_documented": False,
            "maps_included": False,
        },
        {
            "source_id": "NVLABS_PHYSICAL_AI_AV_DEVKIT_DATASET_MODULE",
            "source_ref": (
                "https://github.com/NVlabs/physical_ai_av/blob/main/"
                "src/physical_ai_av/dataset.py"
            ),
            "official_source": True,
            "local_source_sha256": _sha256(PHYSICAL_AI_AV_DEVKIT),
            "offline_optimized_feature_documented": False,
            "general_variant_selection_rule_documented": False,
            "offline_calibration_reader_supported": False,
        },
        {
            "source_id": "NVIDIA_PHYSICALAI_AV_FEATURE_CATALOG",
            "source_ref": (
                "https://huggingface.co/datasets/nvidia/"
                "PhysicalAI-Autonomous-Vehicles/blob/main/features.csv"
            ),
            "official_source": True,
            "local_source_sha256": _sha256(PHYSICAL_AI_FEATURE_CATALOG),
            "offline_optimized_feature_documented": True,
            "general_variant_selection_rule_documented": False,
        },
    ])
    source_review_precheck = build_source_review_precheck(
        association_queue,
        attrition_reserve_review_queue,
        calibration_variant_source_audit,
    )
    human_source_review_packet = build_human_source_review_packet(
        source_review_precheck
    )
    licensed_screen = _licensed_candidate_screen(audit_stats, annotation_screen)
    preflight = build_m16_scene_preflight(eligibility, slot_binding)
    source_closure = _source_closure(eligibility)
    scope_audit = _scope_audit(eligibility)
    gaps = _gap_manifest(eligibility, slot_binding, audit_stats, licensed_screen)
    translation = {
        "translation_results_version": "guardsynth-m16-translation-results-v0.1",
        "newly_eligible_scene_count": eligibility["newly_eligible_count"],
        "executed_scene_count": 0,
        "status": "NOT_RUN_NO_NEWLY_ELIGIBLE_SCENES",
        "canonical_runtime_bounded_z3_core_direct_replay_agreement": "NOT_APPLICABLE",
        "actual_vehicle_safety_claimed": False,
        "claim_scope": "NO_NEW_ELIGIBLE_EXECUTION_NOT_A_SAFETY_RESULT",
    }
    result = {
        "experiment_id": EXPERIMENT_ID,
        "run_id": run_id,
        "run_date": date.today().isoformat(),
        "status": preflight["status"],
        **audit_stats,
        "prior_eligible_reaudited_count": eligibility["prior_eligible_reaudited_count"],
        "prior_eligible_retained_count": eligibility["prior_eligible_retained_count"],
        "source_complete_8_of_8_count": eligibility["source_complete_count"],
        "eligible_scene_count": eligibility["eligible_scene_count"],
        "newly_eligible_count": eligibility["newly_eligible_count"],
        "licensed_candidate_event_count": licensed_screen[
            "licensed_candidate_event_count"
        ],
        "sensor_eligible_candidate_clip_count": licensed_screen[
            "sensor_eligible_candidate_clip_count"
        ],
        "locally_materialized_additional_candidate_count": licensed_screen[
            "locally_materialized_additional_candidate_count"
        ],
        "acquisition_session_status": licensed_screen[
            "acquisition_session_status"
        ],
        "annotation_classified_event_count": annotation_screen[
            "classified_event_count"
        ],
        "annotation_unsupported_event_count": annotation_screen[
            "unsupported_event_count"
        ],
        "sensor_shortlist_unique_clip_count": annotation_screen[
            "shortlist_unique_clip_count"
        ],
        "sensor_shortlist_unique_chunk_count": annotation_screen[
            "shortlist_unique_chunk_count"
        ],
        "classified_unique_clip_count": attrition_reserve[
            "classified_unique_clip_count"
        ],
        "attrition_reserve_event_count": attrition_reserve[
            "reserve_event_count"
        ],
        "attrition_reserve_new_clip_count": attrition_reserve[
            "new_clip_materialization_count"
        ],
        "attrition_reserve_reused_clip_event_count": attrition_reserve[
            "reused_materialized_clip_event_count"
        ],
        "attrition_reserve_new_clip_secondary_event_count": attrition_reserve[
            "new_clip_secondary_event_count"
        ],
        "attrition_reserve_unique_chunk_count": attrition_reserve[
            "new_clip_unique_chunk_count"
        ],
        "estimated_additional_sensor_package_count": attrition_reserve[
            "estimated_additional_sensor_package_count"
        ],
        "estimated_sensor_package_count": annotation_screen[
            "estimated_sensor_package_count"
        ],
        "materialized_sensor_candidate_count": licensed_screen[
            "materialized_sensor_candidate_count"
        ],
        "materialized_sensor_member_count": licensed_screen[
            "materialized_sensor_member_count"
        ],
        "materialized_sensor_bytes": licensed_screen["materialized_sensor_bytes"],
        "sensor_temporal_closure_candidate_count": licensed_screen[
            "sensor_temporal_closure_candidate_count"
        ],
        "sensor_source_complete_8_of_8_candidate_count": licensed_screen[
            "sensor_source_complete_8_of_8_candidate_count"
        ],
        "sensor_final_outcome_assigned_count": licensed_screen[
            "sensor_final_outcome_assigned_count"
        ],
        "calibration_candidate_count": licensed_screen[
            "calibration_candidate_count"
        ],
        "calibration_candidate_feature_count": licensed_screen[
            "calibration_candidate_feature_count"
        ],
        "calibration_materialized_bytes": licensed_screen[
            "calibration_materialized_bytes"
        ],
        "recorded_rig_binding_available_count": licensed_screen[
            "recorded_rig_binding_available_count"
        ],
        "verified_coordinate_transform_count": licensed_screen[
            "verified_coordinate_transform_count"
        ],
        "calibration_variant_review_count": licensed_screen[
            "calibration_variant_review_count"
        ],
        "association_review_status_counts": licensed_screen[
            "association_review_status_counts"
        ],
        "reserve_materialized_sensor_clip_count": licensed_screen[
            "reserve_materialized_sensor_clip_count"
        ],
        "reserve_materialized_sensor_member_count": licensed_screen[
            "reserve_materialized_sensor_member_count"
        ],
        "reserve_materialized_sensor_bytes": licensed_screen[
            "reserve_materialized_sensor_bytes"
        ],
        "reserve_sensor_temporal_closure_candidate_count": licensed_screen[
            "reserve_sensor_temporal_closure_candidate_count"
        ],
        "reserve_calibration_candidate_count": licensed_screen[
            "reserve_calibration_candidate_count"
        ],
        "reserve_calibration_feature_count": licensed_screen[
            "reserve_calibration_feature_count"
        ],
        "reserve_calibration_materialized_bytes": licensed_screen[
            "reserve_calibration_materialized_bytes"
        ],
        "total_materialized_sensor_unique_clip_count": (
            licensed_screen["materialized_sensor_candidate_count"]
            + licensed_screen["reserve_materialized_sensor_clip_count"]
        ),
        "total_materialized_sensor_member_count": (
            licensed_screen["materialized_sensor_member_count"]
            + licensed_screen["reserve_materialized_sensor_member_count"]
        ),
        "total_materialized_sensor_bytes": (
            licensed_screen["materialized_sensor_bytes"]
            + licensed_screen["reserve_materialized_sensor_bytes"]
        ),
        "total_materialized_calibration_feature_count": (
            licensed_screen["calibration_candidate_feature_count"]
            + licensed_screen["reserve_calibration_feature_count"]
        ),
        "total_materialized_calibration_bytes": (
            licensed_screen["calibration_materialized_bytes"]
            + licensed_screen["reserve_calibration_materialized_bytes"]
        ),
        "classified_event_temporal_closure_count": licensed_screen[
            "classified_event_temporal_closure_count"
        ],
        "classified_event_calibration_closure_count": licensed_screen[
            "classified_event_calibration_closure_count"
        ],
        "classified_event_recorded_rig_binding_count": licensed_screen[
            "classified_event_recorded_rig_binding_count"
        ],
        "classified_event_verified_transform_count": licensed_screen[
            "classified_event_verified_transform_count"
        ],
        "classified_event_source_complete_8_of_8_count": licensed_screen[
            "classified_event_source_complete_8_of_8_count"
        ],
        "classified_event_final_outcome_assigned_count": licensed_screen[
            "classified_event_final_outcome_assigned_count"
        ],
        "classified_event_association_review_status_counts": licensed_screen[
            "classified_event_association_review_status_counts"
        ],
        "source_review_precheck_status": "COMPLETE",
        "source_review_human_packet_count": source_review_precheck[
            "human_review_packet_count"
        ],
        "source_review_geometry_source_required_count": source_review_precheck[
            "geometry_source_required_count"
        ],
        "calibration_variant_source_decision": calibration_variant_source_audit[
            "decision"
        ],
        "excluded_count": eligibility["excluded_count"],
        "annotation_start_allowed": preflight["annotation_start_allowed"],
        "annotation_started": False,
        "synthetic_required_field_fill_count": 0,
        "unsourced_normative_or_numeric_value_count": 0,
        "actual_vehicle_validation_deferred_to_m21": True,
        "vehicle_safety_validated": False,
        "claim_scope": CLAIM_SCOPE,
    }
    revision, workspace_state = _git_revision()
    z3_runtime = configure_project_z3(ROOT).manifest()
    run_manifest = {
        **result,
        "code_revision": revision,
        "workspace_state": workspace_state,
        "python_version": sys.version.split()[0],
        "z3_runtime": z3_runtime,
        "input_class": "LICENSE_RESTRICTED_SELECTED_SENSOR_MEMBERS",
        "license_boundary": "NVIDIA_LICENSE_RESTRICTED_INTERNAL_DERIVATIVES",
        "input_hashes": {
            **input_hashes,
            "cascade_annotation_collection": annotation_screen[
                "annotation_collection_sha256"
            ],
        },
        "deterministic_seed": 16060,
        "test_commands": test_results,
        "restricted_identifier_leakage_to_public_count": 0,
    }
    restricted_output_dir.mkdir(parents=True)
    restricted_output_dir.chmod(0o700)
    artifacts = {
        "RESULT.json": result,
        "RUN_MANIFEST.json": run_manifest,
        "SCENE_ELIGIBILITY_MANIFEST.json": eligibility,
        "SCENE_SOURCE_CLOSURE.json": source_closure,
        "SLOT_BINDING_MANIFEST.json": slot_binding,
        "SCOPE_COMPATIBILITY_AUDIT.json": scope_audit,
        "ACQUISITION_GAP_MANIFEST.json": gaps,
        "LICENSED_CANDIDATE_SCREEN.json": licensed_screen,
        "ANNOTATION_CANDIDATE_SCREEN.json": annotation_screen,
        "SENSOR_MATERIALIZATION_SHORTLIST.json": sensor_shortlist,
        "ATTRITION_RESERVE_COHORT.json": attrition_reserve,
        "SENSOR_RESERVE_SHORTLIST.json": reserve_shortlist,
        "SENSOR_MATERIALIZATION_AUDIT.json": sensor_materialization,
        "SENSOR_EVIDENCE_AUDIT.json": sensor_evidence_audit,
        "CALIBRATION_MATERIALIZATION_AUDIT.json": calibration_manifest,
        "CALIBRATION_ASSOCIATION_AUDIT.json": calibration_audit,
        "ASSOCIATION_REVIEW_QUEUE.json": association_queue,
        "RESERVE_SENSOR_MATERIALIZATION_AUDIT.json": reserve_sensor_materialization,
        "RESERVE_SENSOR_EVIDENCE_AUDIT.json": reserve_sensor_evidence_audit,
        "RESERVE_CALIBRATION_MATERIALIZATION_AUDIT.json": reserve_calibration_manifest,
        "RESERVE_CALIBRATION_ASSOCIATION_AUDIT.json": reserve_calibration_audit,
        "RESERVE_ASSOCIATION_REVIEW_QUEUE.json": reserve_association_queue,
        "ATTRITION_RESERVE_EVIDENCE_AUDIT.json": attrition_reserve_evidence_audit,
        "ATTRITION_RESERVE_REVIEW_QUEUE.json": attrition_reserve_review_queue,
        "CALIBRATION_VARIANT_SOURCE_AUDIT.json": calibration_variant_source_audit,
        "SOURCE_REVIEW_PRECHECK.json": source_review_precheck,
        "HUMAN_SOURCE_REVIEW_PACKET.json": human_source_review_packet,
        "PILOT_PREFLIGHT.json": preflight,
        "TRANSLATION_RESULTS.json": translation,
    }
    for filename, value in artifacts.items():
        _write_json(restricted_output_dir / filename, value)
    (restricted_output_dir / "REPORT_KO.md").write_text(
        "# M16 source-complete 장면 확보·적격성 재감사\n\n"
        f"- 상태: **{result['status']}**\n"
        f"- source record: **{audit_stats['candidate_source_record_count']}개**\n"
        f"- alias 중복 제거: **{audit_stats['source_alias_deduplicated_count']}개**\n"
        f"- distinct candidate event: **{audit_stats['distinct_candidate_count']}개**\n"
        f"- 기존 적격 4개 재감사: **retained {result['prior_eligible_retained_count']}/4**\n"
        f"- 8/8 source closure: **{result['source_complete_8_of_8_count']}개**\n"
        f"- multi-jurisdiction eligible: **{result['eligible_scene_count']}/60**\n"
        f"- 새 eligible: **{result['newly_eligible_count']}개**\n"
        f"- licensed candidate screen: **{result['licensed_candidate_event_count']} events / "
        f"{result['sensor_eligible_candidate_clip_count']} sensor-eligible clips**\n"
        f"- locally materialized additional candidates: "
        f"**{result['locally_materialized_additional_candidate_count']}개**\n"
        f"- annotation-classified candidates: "
        f"**{result['annotation_classified_event_count']}/135 events**\n"
        f"- sensor shortlist: **{result['sensor_shortlist_unique_clip_count']} clips / "
        f"{result['sensor_shortlist_unique_chunk_count']} chunks / "
        f"{result['estimated_sensor_package_count']} packages**\n"
        f"- attrition reserve: **{result['attrition_reserve_event_count']} events / "
        f"{result['attrition_reserve_new_clip_count']} new clips / "
        f"{result['attrition_reserve_reused_clip_event_count']} reused-clip events**\n"
        f"- reserve sensor materialization: **{result['reserve_materialized_sensor_clip_count']} "
        f"clips / {result['reserve_materialized_sensor_member_count']} members / "
        f"{result['reserve_materialized_sensor_bytes']} bytes**\n"
        f"- total materialized sensor cohort: "
        f"**{result['total_materialized_sensor_unique_clip_count']} unique clips / "
        f"{result['total_materialized_sensor_member_count']} members / "
        f"{result['total_materialized_sensor_bytes']} bytes**\n"
        f"- all classified event temporal/calibration/rig closure: "
        f"**{result['classified_event_temporal_closure_count']}/"
        f"{result['classified_event_calibration_closure_count']}/"
        f"{result['classified_event_recorded_rig_binding_count']} of 98**\n"
        f"- all classified event verified transform/8-of-8/outcome: "
        f"**{result['classified_event_verified_transform_count']}/"
        f"{result['classified_event_source_complete_8_of_8_count']}/"
        f"{result['classified_event_final_outcome_assigned_count']}**\n"
        f"- source-review precheck: **{result['source_review_precheck_status']}**; "
        f"human packet {result['source_review_human_packet_count']}/98, "
        f"geometry source required {result['source_review_geometry_source_required_count']}/98\n"
        f"- calibration variant source decision: "
        f"**{result['calibration_variant_source_decision']}**\n"
        f"- materialized sensor evidence: **{result['materialized_sensor_candidate_count']} "
        f"candidates / {result['materialized_sensor_member_count']} members / "
        f"{result['materialized_sensor_bytes']} bytes**\n"
        f"- sensor temporal closure: "
        f"**{result['sensor_temporal_closure_candidate_count']}/59**\n"
        f"- restricted selected camera video retained: "
        f"**{result['total_materialized_sensor_unique_clip_count']} members**\n"
        f"- calibration closure: **{result['calibration_candidate_count']}/59 "
        f"candidates, {result['calibration_candidate_feature_count']} feature records, "
        f"{result['calibration_materialized_bytes']} bytes**\n"
        f"- recorded rig / verified transform: "
        f"**{result['recorded_rig_binding_available_count']}/"
        f"{result['verified_coordinate_transform_count']}**\n"
        f"- calibration variant review: **{result['calibration_variant_review_count']}/59**\n"
        f"- sensor-derived new 8/8/outcome: "
        f"**{result['sensor_source_complete_8_of_8_candidate_count']}/"
        f"{result['sensor_final_outcome_assigned_count']}**\n"
        "- annotation start: **금지**\n"
        "- synthetic required-field fill: **0건**\n"
        "- actual vehicle assurance: **M21로 이관 유지**\n\n"
        "국가 제한 없는 multi-jurisdiction 정책으로 기존 네 장면을 다시 판정했다. 한 장면은 "
        "image timestamp와 actor/transform event가 서로 다른 cross-event packet으로 재확인되어 "
        "8/8 closure를 유지하지 않았다. source-complete 세 장면 중 한 장면만 촬영 관할과 "
        "jurisdiction-independent verified system requirement가 함께 닫혀 eligible로 유지됐다. "
        "나머지 두 장면은 촬영 관할이 UNKNOWN이므로 review 대상으로 남겼다.\n\n"
        "새로 승격된 장면은 없고 유지된 한 장면은 기존 M13 실행 근거가 있으므로 추가 "
        "GuardSynth→EBLC→Core→Z3 재실행은 수행하지 않았다. "
        "승인된 CASCADE annotation과 59개 primary shortlist 및 22개 reserve clip의 선택 sensor "
        "member를 materialize했다. 총 81개 clip의 asset을 사용해 classified 98 events 모두에서 "
        "네 time stream, 5/5 calibration과 recorded-rig binding을 확인했다. exact "
        "recorded-rig binding은 닫혔지만 online/offline calibration 차이에 대한 upstream 선택 "
        "근거가 없어 verified transform을 닫지 않았다. target/lane association, jurisdiction-"
        "matched rule source와 outcome witness도 review queue에 남아 이번 eligible 증분은 0이다. "
        "이는 데이터·scope gate 판정이며 전문가 agreement, GuardSynth 효과, 법규 준수 또는 차량 "
        "안전성을 입증하지 않는다.\n",
        encoding="utf-8",
    )
    (restricted_output_dir / "REPORT_KO.md").chmod(0o600)

    if public_output_dir is not None:
        public_annotation_screen = {
            key: value
            for key, value in annotation_screen.items()
            if key not in {"annotation_collection_sha256", "records"}
        }
        public_result = {
            key: result[key]
            for key in (
                "experiment_id",
                "run_id",
                "run_date",
                "status",
                "candidate_source_record_count",
                "source_alias_deduplicated_count",
                "distinct_candidate_count",
                "prior_eligible_reaudited_count",
                "prior_eligible_retained_count",
                "source_complete_8_of_8_count",
                "eligible_scene_count",
                "newly_eligible_count",
                "licensed_candidate_event_count",
                "sensor_eligible_candidate_clip_count",
                "locally_materialized_additional_candidate_count",
                "acquisition_session_status",
                "annotation_classified_event_count",
                "annotation_unsupported_event_count",
                "sensor_shortlist_unique_clip_count",
                "sensor_shortlist_unique_chunk_count",
                "classified_unique_clip_count",
                "attrition_reserve_event_count",
                "attrition_reserve_new_clip_count",
                "attrition_reserve_reused_clip_event_count",
                "attrition_reserve_new_clip_secondary_event_count",
                "attrition_reserve_unique_chunk_count",
                "estimated_additional_sensor_package_count",
                "estimated_sensor_package_count",
                "materialized_sensor_candidate_count",
                "materialized_sensor_member_count",
                "materialized_sensor_bytes",
                "sensor_temporal_closure_candidate_count",
                "sensor_source_complete_8_of_8_candidate_count",
                "sensor_final_outcome_assigned_count",
                "calibration_candidate_count",
                "calibration_candidate_feature_count",
                "calibration_materialized_bytes",
                "recorded_rig_binding_available_count",
                "verified_coordinate_transform_count",
                "calibration_variant_review_count",
                "reserve_materialized_sensor_clip_count",
                "reserve_materialized_sensor_member_count",
                "reserve_materialized_sensor_bytes",
                "reserve_sensor_temporal_closure_candidate_count",
                "reserve_calibration_candidate_count",
                "reserve_calibration_feature_count",
                "reserve_calibration_materialized_bytes",
                "total_materialized_sensor_unique_clip_count",
                "total_materialized_sensor_member_count",
                "total_materialized_sensor_bytes",
                "total_materialized_calibration_feature_count",
                "total_materialized_calibration_bytes",
                "classified_event_temporal_closure_count",
                "classified_event_calibration_closure_count",
                "classified_event_recorded_rig_binding_count",
                "classified_event_verified_transform_count",
                "classified_event_source_complete_8_of_8_count",
                "classified_event_final_outcome_assigned_count",
                "source_review_precheck_status",
                "source_review_human_packet_count",
                "source_review_geometry_source_required_count",
                "calibration_variant_source_decision",
                "excluded_count",
                "annotation_start_allowed",
                "annotation_started",
                "synthetic_required_field_fill_count",
                "claim_scope",
            )
        }
        public_manifest = {
            "experiment_id": EXPERIMENT_ID,
            "run_id": run_id,
            "run_date": result["run_date"],
            "input_class": "PUBLIC_DEIDENTIFIED_AGGREGATE",
            "source_run_hash": hashlib.sha256(
                json.dumps(result, sort_keys=True).encode()
            ).hexdigest(),
            "restricted_identifier_leakage_count": 0,
            "annotation_started": False,
            "claim_scope": CLAIM_SCOPE,
        }
        assert_public_export_safe(public_result)
        assert_public_export_safe(public_manifest)
        assert_public_export_safe(public_annotation_screen)
        public_attrition_reserve = {
            key: value
            for key, value in attrition_reserve.items()
            if key not in {"records", "materialization_records"}
        }
        assert_public_export_safe(public_attrition_reserve)
        public_output_dir.mkdir(parents=True)
        _write_json(public_output_dir / "RESULT.json", public_result, restricted=False)
        _write_json(public_output_dir / "RUN_MANIFEST.json", public_manifest, restricted=False)
        _write_json(
            public_output_dir / "ANNOTATION_CANDIDATE_SCREEN.json",
            public_annotation_screen,
            restricted=False,
        )
        _write_json(
            public_output_dir / "ATTRITION_RESERVE_COHORT.json",
            public_attrition_reserve,
            restricted=False,
        )
        public_sensor_audit = {
            key: value
            for key, value in sensor_evidence_audit.items()
            if key not in {"materialization_manifest_sha256", "records"}
        }
        assert_public_export_safe(public_sensor_audit)
        _write_json(
            public_output_dir / "SENSOR_EVIDENCE_AUDIT.json",
            public_sensor_audit,
            restricted=False,
        )
        public_calibration_audit = {
            key: value
            for key, value in calibration_audit.items()
            if key not in {"calibration_manifest_sha256", "records"}
        }
        assert_public_export_safe(public_calibration_audit)
        _write_json(
            public_output_dir / "CALIBRATION_ASSOCIATION_AUDIT.json",
            public_calibration_audit,
            restricted=False,
        )
        public_attrition_reserve_audit = {
            key: value
            for key, value in attrition_reserve_evidence_audit.items()
            if key not in {
                "attrition_reserve_cohort_sha256",
                "primary_sensor_manifest_sha256",
                "reserve_sensor_manifest_sha256",
                "primary_calibration_manifest_sha256",
                "reserve_calibration_manifest_sha256",
                "records",
            }
        }
        assert_public_export_safe(public_attrition_reserve_audit)
        _write_json(
            public_output_dir / "ATTRITION_RESERVE_EVIDENCE_AUDIT.json",
            public_attrition_reserve_audit,
            restricted=False,
        )
        public_source_review_precheck = public_source_review_precheck_summary(
            source_review_precheck
        )
        assert_public_export_safe(public_source_review_precheck)
        _write_json(
            public_output_dir / "SOURCE_REVIEW_PRECHECK.json",
            public_source_review_precheck,
            restricted=False,
        )
        (public_output_dir / "REPORT_KO.md").write_text(
            "# M16 장면 적격성 공개 비식별 집계\n\n"
            f"- 상태: **{result['status']}**\n"
            f"- distinct candidates: **{result['distinct_candidate_count']}개**\n"
            f"- alias 중복 제거: **{result['source_alias_deduplicated_count']}개**\n"
            f"- 8/8 source closure: **{result['source_complete_8_of_8_count']}개**\n"
            f"- multi-jurisdiction eligible: **{result['eligible_scene_count']}/60**\n"
            f"- licensed candidate events: **{result['licensed_candidate_event_count']}개**\n"
            f"- sensor-eligible candidate clips: **{result['sensor_eligible_candidate_clip_count']}개**\n"
            f"- annotation-classified candidates: **{result['annotation_classified_event_count']}개**\n"
            f"- sensor shortlist: **{result['sensor_shortlist_unique_clip_count']} clips / "
            f"{result['estimated_sensor_package_count']} packages**\n"
            f"- attrition reserve: **{result['attrition_reserve_event_count']} events / "
            f"{result['attrition_reserve_new_clip_count']} new clips**\n"
            f"- total materialized sensor cohort: "
            f"**{result['total_materialized_sensor_unique_clip_count']} unique clips / "
            f"{result['total_materialized_sensor_member_count']} members**\n"
            f"- all classified event temporal/calibration/rig closure: "
            f"**{result['classified_event_temporal_closure_count']}/"
            f"{result['classified_event_calibration_closure_count']}/"
            f"{result['classified_event_recorded_rig_binding_count']} of 98**\n"
            f"- all classified event verified transform/8-of-8/outcome: "
            f"**{result['classified_event_verified_transform_count']}/"
            f"{result['classified_event_source_complete_8_of_8_count']}/"
            f"{result['classified_event_final_outcome_assigned_count']}**\n"
            f"- source-review precheck: **{result['source_review_precheck_status']}**; "
            f"human packet {result['source_review_human_packet_count']}/98, "
            f"geometry source required {result['source_review_geometry_source_required_count']}/98\n"
            f"- materialized sensor candidates: "
            f"**{result['materialized_sensor_candidate_count']}개**\n"
            f"- sensor temporal closure: "
            f"**{result['sensor_temporal_closure_candidate_count']}/59**\n"
            "- sensor-derived new 8/8/outcome: **0/0**\n"
            f"- calibration closure: **{result['calibration_candidate_count']}/59**\n"
            f"- recorded rig / verified transform: "
            f"**{result['recorded_rig_binding_available_count']}/"
            f"{result['verified_coordinate_transform_count']}**\n"
            f"- locally materialized additional candidates: **0개**\n"
            "- annotation start: **금지**\n"
            "- 공개 제한 식별자·경로·CoC 전문: **0건**\n\n"
            "국가 제한 없는 정책에서도 장면별 관할·ODD·rule source와 8/8 field closure를 "
            "모두 요구했다. 이 집계는 전문가 결과나 차량 안전성 증거가 아니다.\n",
            encoding="utf-8",
        )
        assert_public_export_safe(
            (public_output_dir / "REPORT_KO.md").read_text(encoding="utf-8")
        )
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--restricted-output-dir", type=Path, required=True)
    parser.add_argument("--public-output-dir", type=Path)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--test-results", type=Path)
    args = parser.parse_args()
    test_results = _load(args.test_results) if args.test_results else []
    result = execute(
        restricted_output_dir=args.restricted_output_dir,
        public_output_dir=args.public_output_dir,
        run_id=args.run_id,
        test_results=test_results,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
