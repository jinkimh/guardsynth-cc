#!/usr/bin/env python3
"""Range-stream and materialize only sensor members named by the M16 shortlist."""

from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import date
import hashlib
import json
from pathlib import Path
import re
import sys
from typing import Any, Iterable
import zipfile


PAI_REPO = "nvidia/PhysicalAI-Autonomous-Vehicles"
PAI_REVISION = "b719eea7f0a63619ef51ec7f54178af0937ef050"
FEATURE_ORDER = (
    "egomotion.offline",
    "egomotion",
    "obstacle.offline",
    "camera_front_wide_120fov",
)
PACKAGE_TEMPLATES = {
    "egomotion": "labels/egomotion/egomotion.chunk_{chunk:04d}.zip",
    "egomotion.offline": (
        "labels/egomotion.offline/egomotion.offline.chunk_{chunk:04d}.zip"
    ),
    "obstacle.offline": (
        "labels/obstacle.offline/obstacle.offline.chunk_{chunk:04d}.zip"
    ),
    "camera_front_wide_120fov": (
        "camera/camera_front_wide_120fov/"
        "camera_front_wide_120fov.chunk_{chunk:04d}.zip"
    ),
}
MEMBER_TEMPLATES = {
    "egomotion": {"egomotion": "{clip_id}.egomotion.parquet"},
    "egomotion.offline": {
        "egomotion_offline": "{clip_id}.egomotion.offline.parquet"
    },
    "obstacle.offline": {
        "obstacle_offline": "{clip_id}.obstacle.offline.parquet"
    },
    "camera_front_wide_120fov": {
        "video": "{clip_id}.camera_front_wide_120fov.mp4",
        "frame_timestamps": (
            "{clip_id}.camera_front_wide_120fov.timestamps.parquet"
        ),
        "blurred_boxes": (
            "{clip_id}.camera_front_wide_120fov.blurred_boxes.parquet"
        ),
    },
}
_CANDIDATE_RE = re.compile(r"^candidate-sha256:([0-9a-f]{64})$")


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _candidate_token(candidate_digest: str) -> str:
    match = _CANDIDATE_RE.fullmatch(candidate_digest)
    if match is None:
        raise ValueError("SENSOR_SHORTLIST_CANDIDATE_DIGEST_INVALID")
    return "event-" + match.group(1)


def target_relative_path(
    candidate_digest: str, feature: str, role: str, member_name: str
) -> Path:
    """Return a deidentified path that never embeds the source clip identifier."""
    if feature not in MEMBER_TEMPLATES or role not in MEMBER_TEMPLATES[feature]:
        raise ValueError("SENSOR_MEMBER_ROLE_INVALID")
    suffix = ".mp4" if member_name.endswith(".mp4") else ".parquet"
    safe_feature = feature.replace(".", "_")
    return Path(_candidate_token(candidate_digest)) / safe_feature / f"{role}{suffix}"


def build_work_items(shortlist: dict[str, Any]) -> list[dict[str, Any]]:
    """Validate the locked shortlist and group records by package."""
    if tuple(shortlist.get("required_sensor_features", ())) != (
        "camera_front_wide_120fov",
        "egomotion",
        "egomotion.offline",
        "obstacle.offline",
    ):
        raise ValueError("SENSOR_SHORTLIST_REQUIRED_FEATURES_CHANGED")
    records = shortlist.get("records")
    expected_candidate_count = shortlist.get(
        "selected_unique_clip_count", len(records) if isinstance(records, list) else 0
    )
    if (
        not isinstance(records, list)
        or not records
        or isinstance(expected_candidate_count, bool)
        or not isinstance(expected_candidate_count, int)
        or len(records) != expected_candidate_count
    ):
        raise ValueError("SENSOR_SHORTLIST_RECORD_COUNT_INVALID")
    seen_clips: set[str] = set()
    grouped: dict[tuple[str, int], list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        clip_id = record.get("clip_id")
        chunk = record.get("chunk")
        if not isinstance(clip_id, str) or not clip_id or clip_id in seen_clips:
            raise ValueError("SENSOR_SHORTLIST_CLIP_ID_INVALID_OR_DUPLICATE")
        if isinstance(chunk, bool) or not isinstance(chunk, int) or chunk < 0:
            raise ValueError("SENSOR_SHORTLIST_CHUNK_INVALID")
        _candidate_token(str(record.get("candidate_digest")))
        seen_clips.add(clip_id)
        for feature in FEATURE_ORDER:
            grouped[(feature, chunk)].append(record)
    work = [
        {
            "feature": feature,
            "chunk": chunk,
            "package_path": PACKAGE_TEMPLATES[feature].format(chunk=chunk),
            "records": sorted(
                grouped[(feature, chunk)], key=lambda item: item["candidate_digest"]
            ),
        }
        for feature in FEATURE_ORDER
        for _, chunk in sorted(key for key in grouped if key[0] == feature)
    ]
    expected_package_count = len({item["chunk"] for item in records}) * len(FEATURE_ORDER)
    declared_package_count = shortlist.get(
        "estimated_sensor_package_count", expected_package_count
    )
    if len(work) != expected_package_count or declared_package_count != expected_package_count:
        raise ValueError("SENSOR_SHORTLIST_PACKAGE_COUNT_INVALID")
    return work


def _validate_materialized(path: Path) -> dict[str, Any]:
    if path.suffix == ".mp4":
        head = path.read_bytes()[:32]
        if b"ftyp" not in head:
            raise ValueError("MATERIALIZED_MP4_HEADER_INVALID")
        return {"validation": "MP4_FTYP_PRESENT"}
    import pyarrow.parquet as parquet

    metadata = parquet.read_metadata(path)
    if metadata.num_rows <= 0 or metadata.num_columns <= 0:
        raise ValueError("MATERIALIZED_PARQUET_EMPTY")
    return {
        "validation": "PARQUET_METADATA_READABLE",
        "rows": metadata.num_rows,
        "columns": metadata.num_columns,
    }


def materialize(
    *,
    shortlist_path: Path,
    output_root: Path,
    manifest_path: Path,
) -> dict[str, Any]:
    if manifest_path.exists():
        raise FileExistsError("refusing to overwrite completed sensor materialization")
    shortlist = json.loads(shortlist_path.read_text(encoding="utf-8"))
    work = build_work_items(shortlist)

    from huggingface_hub import HfFileSystem

    filesystem = HfFileSystem()
    output_root.mkdir(parents=True, exist_ok=True)
    output_root.chmod(0o700)
    materialized: list[dict[str, Any]] = []
    accessed_packages: list[dict[str, Any]] = []
    for package_index, item in enumerate(work, start=1):
        remote_path = (
            f"datasets/{PAI_REPO}@{PAI_REVISION}/{item['package_path']}"
        )
        with filesystem.open(remote_path, "rb") as source:
            with zipfile.ZipFile(source) as archive:
                archive_names = set(archive.namelist())
                package_members = 0
                for record in item["records"]:
                    for role, template in MEMBER_TEMPLATES[item["feature"]].items():
                        member_name = template.format(clip_id=record["clip_id"])
                        if member_name not in archive_names:
                            raise FileNotFoundError("SHORTLIST_SENSOR_MEMBER_MISSING")
                        relative = target_relative_path(
                            record["candidate_digest"],
                            item["feature"],
                            role,
                            member_name,
                        )
                        target = output_root / relative
                        target.parent.mkdir(parents=True, exist_ok=True)
                        if target.exists():
                            member_sha = _sha256_file(target)
                            member_bytes = target.stat().st_size
                        else:
                            raw = archive.read(member_name)
                            member_sha = _sha256_bytes(raw)
                            member_bytes = len(raw)
                            partial = target.with_suffix(target.suffix + ".part")
                            partial.write_bytes(raw)
                            partial.chmod(0o600)
                            partial.replace(target)
                        validation = _validate_materialized(target)
                        materialized.append({
                            "candidate_digest": record["candidate_digest"],
                            "clip_id": record["clip_id"],
                            "event_timestamp_us": record["event_timestamp_us"],
                            "shortlist_slice": record["shortlist_slice"],
                            "feature": item["feature"],
                            "role": role,
                            "relative_path": relative.as_posix(),
                            "bytes": member_bytes,
                            "sha256": member_sha,
                            **validation,
                        })
                        package_members += 1
        accessed_packages.append({
            "feature": item["feature"],
            "chunk": item["chunk"],
            "package_path": item["package_path"],
            "selected_member_count": package_members,
        })
        if package_index % 10 == 0 or package_index == len(work):
            print(
                f"materialized packages {package_index}/{len(work)}; "
                f"members {len(materialized)}",
                flush=True,
            )

    candidate_counts: dict[str, int] = defaultdict(int)
    for item in materialized:
        candidate_counts[item["candidate_digest"]] += 1
    expected_candidate_count = len(shortlist["records"])
    if set(candidate_counts.values()) != {6} or len(candidate_counts) != expected_candidate_count:
        raise ValueError("SENSOR_MATERIALIZATION_CANDIDATE_CLOSURE_FAILED")
    result = {
        "materialization_version": "guardsynth-m16-sensor-member-materialization-v0.2",
        "run_date": date.today().isoformat(),
        "source_repository": PAI_REPO,
        "source_revision": PAI_REVISION,
        "shortlist_sha256": _sha256_file(shortlist_path),
        "selected_candidate_count": len(candidate_counts),
        "accessed_package_count": len(accessed_packages),
        "materialized_member_count": len(materialized),
        "materialized_bytes": sum(item["bytes"] for item in materialized),
        "full_package_download_performed": False,
        "range_streamed_selected_members_only": True,
        "network_or_credential_use_performed": True,
        "candidate_member_closure": (
            f"{expected_candidate_count}_OF_{expected_candidate_count}_HAVE_6_OF_6_MEMBERS"
        ),
        "accessed_packages": accessed_packages,
        "records": materialized,
        "claim_scope": "LICENSE_RESTRICTED_SENSOR_MATERIALIZATION_NOT_VEHICLE_SAFETY",
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    manifest_path.chmod(0o600)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--shortlist", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args()
    result = materialize(
        shortlist_path=args.shortlist,
        output_root=args.output_root,
        manifest_path=args.manifest,
    )
    print(json.dumps({
        key: result[key]
        for key in (
            "selected_candidate_count",
            "accessed_package_count",
            "materialized_member_count",
            "materialized_bytes",
            "candidate_member_closure",
        )
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
