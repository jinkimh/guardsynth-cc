#!/usr/bin/env python3
"""Audit M16 calibration and build a deidentified association review queue."""

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

from guard_synth.m16_annotation_candidate_screen import parse_cascade_timestamp_us
from guard_synth.m16_calibration_association_audit import (
    association_review_status,
    extrinsics_variant_delta,
    public_calibration_association_summary,
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _active(item: dict[str, Any], event_timestamp_us: int) -> bool:
    start = parse_cascade_timestamp_us(
        item.get("visibility_start_timestamp", item.get("start_timestamp"))
    )
    end = parse_cascade_timestamp_us(
        item.get("visibility_end_timestamp", item.get("end_timestamp"))
    )
    if start is None and end is None:
        return True
    start = end if start is None else start
    end = start if end is None else end
    assert start is not None and end is not None
    return start - 500_000 <= event_timestamp_us <= end + 500_000


def _point_count(items: list[dict[str, Any]], event_timestamp_us: int) -> int:
    count = 0
    for item in items:
        if not _active(item, event_timestamp_us):
            continue
        groups = item.get("keypoints") or []
        for group in groups:
            points = [group] if isinstance(group, dict) else group
            for point in points:
                if not isinstance(point, dict):
                    continue
                timestamp = parse_cascade_timestamp_us(point.get("timestamp"))
                if timestamp is None or abs(timestamp - event_timestamp_us) <= 500_000:
                    count += 1
    return count


def _relevant_agent(item: dict[str, Any], slice_name: str) -> bool:
    agent_type = str(item.get("type", "")).lower()
    if slice_name == "PEDESTRIAN_CYCLIST_YIELD":
        return any(
            token in agent_type
            for token in ("pedestrian", "bicycle", "cyclist", "wheelchair", "scooter")
        )
    if slice_name == "FOLLOWING_CUT_IN":
        return any(
            token in agent_type
            for token in ("car", "truck", "vehicle", "bus", "motorcycle")
        )
    return False


def _row_dict(table, name_column: str, name: str) -> dict[str, float]:
    import pyarrow.compute as compute

    selected = table.filter(compute.equal(table[name_column], name))
    if selected.num_rows != 1:
        raise ValueError("CALIBRATION_FRONT_CAMERA_ROW_NOT_UNIQUE")
    return {
        key: float(selected[key][0].as_py())
        for key in ("qx", "qy", "qz", "qw", "x", "y", "z")
    }


def execute(
    *,
    shortlist_path: Path,
    calibration_manifest_path: Path,
    sensor_audit_path: Path,
    calibration_root: Path,
    annotation_root: Path,
    audit_path: Path,
    queue_path: Path,
) -> dict[str, Any]:
    if audit_path.exists() or queue_path.exists():
        raise FileExistsError("refusing to overwrite completed calibration association audit")
    import pyarrow.parquet as parquet

    shortlist = json.loads(shortlist_path.read_text(encoding="utf-8"))
    calibration_manifest = json.loads(
        calibration_manifest_path.read_text(encoding="utf-8")
    )
    sensor_audit = json.loads(sensor_audit_path.read_text(encoding="utf-8"))
    shortlist_records = shortlist.get("records")
    if not isinstance(shortlist_records, list) or not shortlist_records:
        raise ValueError("CALIBRATION_SHORTLIST_RECORDS_INVALID")
    expected_candidate_count = len(shortlist_records)
    if calibration_manifest.get("candidate_feature_closure") != (
        f"{expected_candidate_count}_OF_{expected_candidate_count}_HAVE_5_OF_5_CALIBRATION_FEATURES"
    ):
        raise ValueError("CALIBRATION_MANIFEST_CLOSURE_INVALID")
    if (
        calibration_manifest.get("selected_candidate_count") != expected_candidate_count
        or sensor_audit.get("audited_candidate_count") != expected_candidate_count
    ):
        raise ValueError("CALIBRATION_SENSOR_CANDIDATE_COUNT_MISMATCH")

    calibration_by_candidate: dict[str, list[dict[str, Any]]] = defaultdict(list)
    clip_by_candidate: dict[str, str] = {}
    for record in calibration_manifest["records"]:
        path = calibration_root / record["relative_path"]
        if (
            not path.is_file()
            or path.stat().st_size != record["bytes"]
            or _sha256(path) != record["sha256"]
        ):
            raise ValueError("CALIBRATION_MATERIALIZATION_INTEGRITY_FAILURE")
        calibration_by_candidate[record["candidate_digest"]].append(record)
        clip_by_candidate[record["candidate_digest"]] = record["clip_id"]
    sensor_by_candidate = {
        record["candidate_digest"]: record for record in sensor_audit["records"]
    }
    shortlist_by_candidate = {
        record["candidate_digest"]: record for record in shortlist["records"]
    }
    annotations = {}
    for path in annotation_root.rglob("*.json"):
        payload = json.loads(path.read_text(encoding="utf-8"))
        annotations[payload["video"]["clip_id"]] = payload["annotation"]

    calibration_records: list[dict[str, Any]] = []
    queue_records: list[dict[str, Any]] = []
    for candidate_digest in sorted(shortlist_by_candidate):
        calibration_items = calibration_by_candidate[candidate_digest]
        if len(calibration_items) != 5:
            raise ValueError("CALIBRATION_CANDIDATE_FEATURE_COUNT_INVALID")
        paths = {
            item["feature"]: calibration_root / item["relative_path"]
            for item in calibration_items
        }
        online = _row_dict(
            parquet.read_table(paths["sensor_extrinsics"]),
            "sensor_name",
            "camera_front_wide_120fov",
        )
        offline = _row_dict(
            parquet.read_table(paths["sensor_extrinsics.offline"]),
            "sensor_name",
            "camera_front_wide_120fov",
        )
        delta = extrinsics_variant_delta(online, offline)
        rig_digest = hashlib.sha256(
            "".join(sorted(item["sha256"] for item in calibration_items)).encode()
        ).hexdigest()
        calibration_records.append({
            "candidate_digest": candidate_digest,
            "calibration_closure": "5_OF_5",
            "recorded_rig_binding_status": "AVAILABLE_SOURCE_LINKED",
            "recorded_rig_binding_digest": "recorded-rig-sha256:" + rig_digest,
            "coordinate_transform_status": (
                "REVIEW_REQUIRED_ONLINE_OFFLINE_VARIANT_SELECTION"
            ),
            **delta,
        })

        shortlist_record = shortlist_by_candidate[candidate_digest]
        event_timestamp_us = shortlist_record["event_timestamp_us"]
        slice_name = shortlist_record["shortlist_slice"]
        annotation = annotations[clip_by_candidate[candidate_digest]]
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
        agent_points = _point_count(agents, event_timestamp_us)
        zone_points = _point_count(environments, event_timestamp_us)
        control_points = _point_count(controls, event_timestamp_us)
        obstacle_tracks = sensor_by_candidate[candidate_digest][
            "obstacle_track_count_within_500ms"
        ]
        queue_records.append({
            "candidate_digest": candidate_digest,
            "shortlist_slice": slice_name,
            "country": shortlist_record["country"],
            "relevant_agent_keypoint_count": agent_points,
            "zone_keypoint_count": zone_points,
            "control_keypoint_count": control_points,
            "obstacle_track_count_within_500ms": obstacle_tracks,
            "association_review_status": association_review_status(
                slice_name=slice_name,
                relevant_agent_keypoints=agent_points,
                zone_keypoints=zone_points,
                control_keypoints=control_points,
                obstacle_tracks=obstacle_tracks,
            ),
            "coordinate_transform_status": (
                "REVIEW_REQUIRED_ONLINE_OFFLINE_VARIANT_SELECTION"
            ),
            "rule_scope_status": "REVIEW_REQUIRED_JURISDICTION_MATCHED_AUTHORITY",
            "outcome_status": "REVIEW_REQUIRED_LIFECYCLE_WITNESS",
            "final_outcome_assigned": False,
        })

    summary = public_calibration_association_summary(
        calibration_records, queue_records
    )
    audit = {
        **summary,
        "calibration_manifest_sha256": _sha256(calibration_manifest_path),
        "records": calibration_records,
    }
    queue = {
        "queue_version": "guardsynth-m16-association-review-queue-v0.2",
        "candidate_count": len(queue_records),
        "records": queue_records,
        "claim_scope": "SOURCE_REVIEW_QUEUE_NOT_FINAL_ASSOCIATION_OUTCOME_OR_SAFETY",
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
    parser.add_argument("--shortlist", type=Path, required=True)
    parser.add_argument("--calibration-manifest", type=Path, required=True)
    parser.add_argument("--sensor-audit", type=Path, required=True)
    parser.add_argument("--calibration-root", type=Path, required=True)
    parser.add_argument("--annotation-root", type=Path, required=True)
    parser.add_argument("--audit", type=Path, required=True)
    parser.add_argument("--queue", type=Path, required=True)
    args = parser.parse_args()
    result = execute(
        shortlist_path=args.shortlist,
        calibration_manifest_path=args.calibration_manifest,
        sensor_audit_path=args.sensor_audit,
        calibration_root=args.calibration_root,
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
