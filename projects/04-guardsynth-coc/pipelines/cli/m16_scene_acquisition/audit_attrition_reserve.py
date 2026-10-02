#!/usr/bin/env python3
"""Audit every reserve event while reusing sensor/calibration assets by clip."""

from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import sys
from typing import Any


if __package__ in {None, ""}:
    ROOT = next(
        parent
        for parent in Path(__file__).resolve().parents
        if (parent / "PROJECT_REGISTRY.json").is_file()
    )
    sys.path.insert(0, str(ROOT / "projects/04-guardsynth-coc/src"))

from guard_synth.m16_attrition_reserve_audit import (
    public_attrition_reserve_summary,
)

from audit_calibration_association import _point_count, _relevant_agent
from audit_sensor_materialization import audit_event_from_asset
from guard_synth.m16_calibration_association_audit import association_review_status


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _sensor_assets(
    manifest_path: Path, output_root: Path
) -> dict[str, tuple[Path, list[dict[str, Any]], str]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in _load(manifest_path).get("records", ()):
        grouped[record["candidate_digest"]].append(record)
    assets: dict[str, tuple[Path, list[dict[str, Any]], str]] = {}
    for digest, records in grouped.items():
        clip_ids = {str(item["clip_id"]) for item in records}
        if len(records) != 6 or len(clip_ids) != 1:
            raise ValueError("ATTRITION_SENSOR_ASSET_GROUP_INVALID")
        assets[digest] = (output_root, records, next(iter(clip_ids)))
    return assets


def _calibration_assets(
    manifest_path: Path, output_root: Path
) -> dict[str, str]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in _load(manifest_path).get("records", ()):
        grouped[record["candidate_digest"]].append(record)
    assets: dict[str, str] = {}
    for digest, records in grouped.items():
        clip_ids = {str(item["clip_id"]) for item in records}
        if len(records) != 5 or len(clip_ids) != 1:
            raise ValueError("ATTRITION_CALIBRATION_ASSET_GROUP_INVALID")
        for item in records:
            path = output_root / item["relative_path"]
            if (
                not path.is_file()
                or path.stat().st_size != item["bytes"]
                or _sha256(path) != item["sha256"]
            ):
                raise ValueError("ATTRITION_CALIBRATION_ASSET_INTEGRITY_FAILURE")
        assets[digest] = next(iter(clip_ids))
    return assets


def execute(
    *,
    cohort_path: Path,
    primary_sensor_manifest_path: Path,
    primary_sensor_root: Path,
    reserve_sensor_manifest_path: Path,
    reserve_sensor_root: Path,
    primary_calibration_manifest_path: Path,
    primary_calibration_root: Path,
    reserve_calibration_manifest_path: Path,
    reserve_calibration_root: Path,
    annotation_root: Path,
    audit_path: Path,
    queue_path: Path,
) -> dict[str, Any]:
    if audit_path.exists() or queue_path.exists():
        raise FileExistsError("refusing to overwrite completed attrition reserve audit")
    cohort = _load(cohort_path)
    event_records = cohort.get("records")
    if (
        not isinstance(event_records, list)
        or len(event_records) != cohort.get("reserve_event_count")
    ):
        raise ValueError("ATTRITION_RESERVE_EVENT_COUNT_INVALID")

    sensor_assets = {
        **_sensor_assets(primary_sensor_manifest_path, primary_sensor_root),
        **_sensor_assets(reserve_sensor_manifest_path, reserve_sensor_root),
    }
    calibration_assets = {
        **_calibration_assets(
            primary_calibration_manifest_path, primary_calibration_root
        ),
        **_calibration_assets(
            reserve_calibration_manifest_path, reserve_calibration_root
        ),
    }
    annotations = {}
    for path in annotation_root.rglob("*.json"):
        payload = _load(path)
        annotations[payload["video"]["clip_id"]] = payload["annotation"]

    audited: list[dict[str, Any]] = []
    queue_records: list[dict[str, Any]] = []
    for event in event_records:
        asset_digest = event["asset_candidate_digest"]
        if asset_digest not in sensor_assets or asset_digest not in calibration_assets:
            raise ValueError("ATTRITION_RESERVE_ASSET_NOT_MATERIALIZED")
        sensor_root, asset_records, sensor_clip_id = sensor_assets[asset_digest]
        clip_id = event["clip_id"]
        if sensor_clip_id != clip_id or calibration_assets[asset_digest] != clip_id:
            raise ValueError("ATTRITION_RESERVE_EVENT_ASSET_CLIP_MISMATCH")
        event_audit = audit_event_from_asset(sensor_root, asset_records, event)
        slice_name = event["reserve_slice"]
        annotation = annotations[clip_id]
        agents = [
            item
            for item in annotation.get("agents", ())
            if _relevant_agent(item, slice_name)
        ]
        environments = [
            item
            for item in annotation.get("environments", ())
            if any(
                token in str(item.get("type", "")).lower()
                for token in ("crossing", "cyclelane", "lanemerge")
            )
        ]
        controls = list(annotation.get("traffic_objects", ()))
        controls.extend(
            head
            for light in annotation.get("traffic_lights", ())
            for head in light.get("signal_heads", ())
        )
        timestamp = event["event_timestamp_us"]
        agent_points = _point_count(agents, timestamp)
        zone_points = _point_count(environments, timestamp)
        control_points = _point_count(controls, timestamp)
        obstacle_tracks = event_audit["obstacle_track_count_within_500ms"]
        association = association_review_status(
            slice_name=slice_name,
            relevant_agent_keypoints=agent_points,
            zone_keypoints=zone_points,
            control_keypoints=control_points,
            obstacle_tracks=obstacle_tracks,
        )
        audited.append({
            "candidate_digest": event["candidate_digest"],
            "asset_candidate_digest": asset_digest,
            "reserve_tier": event["reserve_tier"],
            "reserve_slice": slice_name,
            "temporal_closure": event_audit["temporal_closure"],
            "time_streams": event_audit["time_streams"],
            "ego_speed_at_event_mps": event_audit["ego_speed_at_event_mps"],
            "obstacle_track_count_within_500ms": obstacle_tracks,
            "field_status": event_audit["field_status"],
            "calibration_closure": "5_OF_5",
            "recorded_rig_binding_status": "AVAILABLE_SOURCE_LINKED",
            "coordinate_transform_status": (
                "REVIEW_REQUIRED_ONLINE_OFFLINE_VARIANT_SELECTION"
            ),
            "association_review_status": association,
            "source_complete": False,
            "final_outcome_assigned": False,
        })
        queue_records.append({
            "candidate_digest": event["candidate_digest"],
            "reserve_tier": event["reserve_tier"],
            "reserve_slice": slice_name,
            "country": event["country"],
            "relevant_agent_keypoint_count": agent_points,
            "zone_keypoint_count": zone_points,
            "control_keypoint_count": control_points,
            "obstacle_track_count_within_500ms": obstacle_tracks,
            "association_review_status": association,
            "coordinate_transform_status": (
                "REVIEW_REQUIRED_ONLINE_OFFLINE_VARIANT_SELECTION"
            ),
            "rule_scope_status": "REVIEW_REQUIRED_JURISDICTION_MATCHED_AUTHORITY",
            "outcome_status": "REVIEW_REQUIRED_LIFECYCLE_WITNESS",
            "final_outcome_assigned": False,
        })

    summary = public_attrition_reserve_summary(audited)
    audit = {
        **summary,
        "attrition_reserve_cohort_sha256": _sha256(cohort_path),
        "primary_sensor_manifest_sha256": _sha256(primary_sensor_manifest_path),
        "reserve_sensor_manifest_sha256": _sha256(reserve_sensor_manifest_path),
        "primary_calibration_manifest_sha256": _sha256(
            primary_calibration_manifest_path
        ),
        "reserve_calibration_manifest_sha256": _sha256(
            reserve_calibration_manifest_path
        ),
        "records": audited,
    }
    queue = {
        "queue_version": "guardsynth-m16-attrition-reserve-review-queue-v0.1",
        "candidate_event_count": len(queue_records),
        "records": queue_records,
        "claim_scope": "RESERVE_SOURCE_REVIEW_QUEUE_NOT_FINAL_OUTCOME_OR_SAFETY",
    }
    for path, value in ((audit_path, audit), (queue_path, queue)):
        path.write_text(
            json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        path.chmod(0o600)
    return audit


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cohort", type=Path, required=True)
    parser.add_argument("--primary-sensor-manifest", type=Path, required=True)
    parser.add_argument("--primary-sensor-root", type=Path, required=True)
    parser.add_argument("--reserve-sensor-manifest", type=Path, required=True)
    parser.add_argument("--reserve-sensor-root", type=Path, required=True)
    parser.add_argument("--primary-calibration-manifest", type=Path, required=True)
    parser.add_argument("--primary-calibration-root", type=Path, required=True)
    parser.add_argument("--reserve-calibration-manifest", type=Path, required=True)
    parser.add_argument("--reserve-calibration-root", type=Path, required=True)
    parser.add_argument("--annotation-root", type=Path, required=True)
    parser.add_argument("--audit", type=Path, required=True)
    parser.add_argument("--queue", type=Path, required=True)
    args = parser.parse_args()
    result = execute(
        cohort_path=args.cohort,
        primary_sensor_manifest_path=args.primary_sensor_manifest,
        primary_sensor_root=args.primary_sensor_root,
        reserve_sensor_manifest_path=args.reserve_sensor_manifest,
        reserve_sensor_root=args.reserve_sensor_root,
        primary_calibration_manifest_path=args.primary_calibration_manifest,
        primary_calibration_root=args.primary_calibration_root,
        reserve_calibration_manifest_path=args.reserve_calibration_manifest,
        reserve_calibration_root=args.reserve_calibration_root,
        annotation_root=args.annotation_root,
        audit_path=args.audit,
        queue_path=args.queue,
    )
    print(json.dumps(
        {key: value for key, value in result.items() if key != "records"},
        indent=2,
        sort_keys=True,
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
