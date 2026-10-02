#!/usr/bin/env python3
"""Audit M16 materialized sensor members without inventing outcome or rule evidence."""

from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import json
import math
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

from guard_synth.m16_sensor_evidence_audit import (
    audit_timestamp_series,
    field_status,
    public_sensor_audit_summary,
    speed_norm,
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _table(path: Path):
    import pyarrow.parquet as parquet

    return parquet.read_table(path)


def _audit_candidate(output_root: Path, records: list[dict[str, Any]]) -> dict[str, Any]:
    candidate_digest = records[0]["candidate_digest"]
    event_timestamp_us = records[0]["event_timestamp_us"]
    if len(records) != 6 or any(
        item["candidate_digest"] != candidate_digest
        or item["event_timestamp_us"] != event_timestamp_us
        for item in records
    ):
        raise ValueError("SENSOR_CANDIDATE_MEMBER_GROUP_INVALID")
    paths: dict[tuple[str, str], Path] = {}
    for item in records:
        relative = Path(item["relative_path"])
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError("SENSOR_MATERIALIZATION_PATH_UNSAFE")
        path = output_root / relative
        if not path.is_file():
            raise FileNotFoundError("SENSOR_MATERIALIZED_MEMBER_MISSING")
        if path.stat().st_size != item["bytes"] or _sha256(path) != item["sha256"]:
            raise ValueError("SENSOR_MATERIALIZED_MEMBER_INTEGRITY_FAILURE")
        paths[(item["feature"], item["role"])] = path

    camera = _table(paths[("camera_front_wide_120fov", "frame_timestamps")])
    egomotion = _table(paths[("egomotion", "egomotion")])
    egomotion_offline = _table(paths[("egomotion.offline", "egomotion_offline")])
    obstacle = _table(paths[("obstacle.offline", "obstacle_offline")])
    streams = {
        "camera_frame_timestamps": audit_timestamp_series(
            camera["timestamp"].to_pylist(), event_timestamp_us
        ),
        "egomotion": audit_timestamp_series(
            egomotion["timestamp"].to_pylist(), event_timestamp_us
        ),
        "egomotion_offline": audit_timestamp_series(
            egomotion_offline["timestamp"].to_pylist(), event_timestamp_us
        ),
        "obstacle_offline": audit_timestamp_series(
            obstacle["timestamp_us"].to_pylist(), event_timestamp_us
        ),
    }
    temporal_closure = all(item["event_covered"] for item in streams.values())
    ego_timestamps = egomotion["timestamp"].to_pylist()
    nearest_index = min(
        range(len(ego_timestamps)),
        key=lambda index: abs(ego_timestamps[index] - event_timestamp_us),
    )
    event_speed = speed_norm(
        egomotion["vx"][nearest_index].as_py(),
        egomotion["vy"][nearest_index].as_py(),
        egomotion["vz"][nearest_index].as_py(),
    )
    obstacle_timestamps = obstacle["timestamp_us"].to_pylist()
    event_rows = [
        index
        for index, timestamp in enumerate(obstacle_timestamps)
        if abs(timestamp - event_timestamp_us) <= 500_000
    ]
    labels = obstacle["label_class"].to_pylist()
    tracks = obstacle["track_id"].to_pylist()
    statuses = field_status(
        temporal_closure=temporal_closure,
        ego_speed_finite=event_speed is not None and math.isfinite(event_speed),
    )
    return {
        "candidate_digest": candidate_digest,
        "shortlist_slice": records[0]["shortlist_slice"],
        "member_closure": "6_OF_6",
        "temporal_closure": temporal_closure,
        "time_streams": streams,
        "ego_speed_at_event_mps": event_speed,
        "obstacle_rows_within_500ms": len(event_rows),
        "obstacle_track_count_within_500ms": len({tracks[index] for index in event_rows}),
        "obstacle_label_counts_within_500ms": dict(sorted(
            {
                label: sum(labels[index] == label for index in event_rows)
                for label in {labels[index] for index in event_rows}
            }.items()
        )),
        "field_status": statuses,
        "source_complete": all(status == "AVAILABLE_SOURCE_LINKED" for status in statuses.values()),
        "outcome_status": "REVIEW_REQUIRED_SENSOR_AND_NORMATIVE_CLOSURE",
        "final_outcome_assigned": False,
    }


def audit_event_from_asset(
    output_root: Path,
    asset_records: list[dict[str, Any]],
    event_record: dict[str, Any],
) -> dict[str, Any]:
    """Audit another event against already materialized members from the same clip."""
    remapped = [
        {
            **item,
            "candidate_digest": event_record["candidate_digest"],
            "event_timestamp_us": event_record["event_timestamp_us"],
            "shortlist_slice": event_record["reserve_slice"],
        }
        for item in asset_records
    ]
    return _audit_candidate(output_root, remapped)


def execute(*, manifest_path: Path, output_root: Path, audit_path: Path) -> dict[str, Any]:
    if audit_path.exists():
        raise FileExistsError("refusing to overwrite completed sensor evidence audit")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in manifest.get("records", ()):
        grouped[record["candidate_digest"]].append(record)
    expected_candidate_count = manifest.get("selected_candidate_count")
    if (
        isinstance(expected_candidate_count, bool)
        or not isinstance(expected_candidate_count, int)
        or expected_candidate_count <= 0
        or len(grouped) != expected_candidate_count
    ):
        raise ValueError("SENSOR_AUDIT_CANDIDATE_COUNT_INVALID")
    records = [
        _audit_candidate(output_root, grouped[digest]) for digest in sorted(grouped)
    ]
    summary = public_sensor_audit_summary(records)
    result = {
        **summary,
        "materialization_manifest_sha256": _sha256(manifest_path),
        "records": records,
    }
    audit_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    audit_path.chmod(0o600)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--audit", type=Path, required=True)
    args = parser.parse_args()
    result = execute(
        manifest_path=args.manifest,
        output_root=args.output_root,
        audit_path=args.audit,
    )
    print(json.dumps(
        {key: value for key, value in result.items() if key != "records"},
        indent=2,
        sort_keys=True,
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
