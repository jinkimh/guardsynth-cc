#!/usr/bin/env python3
"""Range-stream calibration packages and retain only M16 shortlist rows."""

from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import date
import hashlib
import json
import math
from pathlib import Path
import re
from typing import Any


PAI_REPO = "nvidia/PhysicalAI-Autonomous-Vehicles"
PAI_REVISION = "b719eea7f0a63619ef51ec7f54178af0937ef050"
FEATURES = (
    "camera_intrinsics",
    "camera_intrinsics.offline",
    "sensor_extrinsics",
    "sensor_extrinsics.offline",
    "vehicle_dimensions",
)
PACKAGE_TEMPLATES = {
    feature: f"calibration/{feature}/{feature}.chunk_{{chunk:04d}}.parquet"
    for feature in FEATURES
}
_CANDIDATE_RE = re.compile(r"^candidate-sha256:([0-9a-f]{64})$")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def target_relative_path(candidate_digest: str, feature: str) -> Path:
    match = _CANDIDATE_RE.fullmatch(candidate_digest)
    if match is None or feature not in FEATURES:
        raise ValueError("CALIBRATION_SHORTLIST_TARGET_INVALID")
    return (
        Path("event-" + match.group(1))
        / feature.replace(".", "_")
        / "calibration.parquet"
    )


def build_work_items(shortlist: dict[str, Any]) -> list[dict[str, Any]]:
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
        raise ValueError("CALIBRATION_SHORTLIST_RECORD_COUNT_INVALID")
    grouped: dict[tuple[str, int], list[dict[str, Any]]] = defaultdict(list)
    seen: set[str] = set()
    for record in records:
        clip_id = record.get("clip_id")
        chunk = record.get("chunk")
        if not isinstance(clip_id, str) or not clip_id or clip_id in seen:
            raise ValueError("CALIBRATION_SHORTLIST_CLIP_INVALID_OR_DUPLICATE")
        if isinstance(chunk, bool) or not isinstance(chunk, int) or chunk < 0:
            raise ValueError("CALIBRATION_SHORTLIST_CHUNK_INVALID")
        target_relative_path(str(record.get("candidate_digest")), FEATURES[0])
        seen.add(clip_id)
        for feature in FEATURES:
            grouped[(feature, chunk)].append(record)
    work = [
        {
            "feature": feature,
            "chunk": chunk,
            "package_path": PACKAGE_TEMPLATES[feature].format(chunk=chunk),
            "records": grouped[(feature, chunk)],
        }
        for feature in FEATURES
        for _, chunk in sorted(key for key in grouped if key[0] == feature)
    ]
    expected_package_count = len({item["chunk"] for item in records}) * len(FEATURES)
    if len(work) != expected_package_count:
        raise ValueError("CALIBRATION_PACKAGE_COUNT_INVALID")
    return work


def _validate_table(feature: str, table) -> dict[str, Any]:
    if table.num_rows <= 0:
        raise ValueError("CALIBRATION_CLIP_ROWS_EMPTY")
    names = []
    for column in ("camera_name", "sensor_name"):
        if column in table.column_names:
            names = table[column].to_pylist()
    if feature != "vehicle_dimensions" and "camera_front_wide_120fov" not in names:
        raise ValueError("CALIBRATION_FRONT_CAMERA_ROW_MISSING")
    if feature.startswith("sensor_extrinsics"):
        max_norm_error = max(
            abs(
                math.sqrt(sum(float(table[name][index].as_py()) ** 2 for name in ("qx", "qy", "qz", "qw")))
                - 1.0
            )
            for index in range(table.num_rows)
        )
        if not math.isfinite(max_norm_error) or max_norm_error > 1e-6:
            raise ValueError("CALIBRATION_QUATERNION_NORM_INVALID")
        return {
            "validation": "EXTRINSICS_QUATERNION_UNIT_NORM",
            "quaternion_norm_max_abs_error": max_norm_error,
        }
    if feature == "vehicle_dimensions":
        if any(
            not math.isfinite(float(table[name][0].as_py()))
            or float(table[name][0].as_py()) <= 0
            for name in ("length", "width", "height", "wheelbase", "track_width")
        ):
            raise ValueError("VEHICLE_DIMENSIONS_INVALID")
        return {"validation": "VEHICLE_DIMENSIONS_POSITIVE_FINITE"}
    return {"validation": "FRONT_CAMERA_INTRINSICS_PRESENT"}


def materialize(
    *, shortlist_path: Path, output_root: Path, manifest_path: Path
) -> dict[str, Any]:
    if manifest_path.exists():
        raise FileExistsError("refusing to overwrite completed calibration materialization")
    import pyarrow.compute as compute
    import pyarrow.parquet as parquet
    from huggingface_hub import HfFileSystem

    shortlist = json.loads(shortlist_path.read_text(encoding="utf-8"))
    work = build_work_items(shortlist)
    filesystem = HfFileSystem()
    materialized: list[dict[str, Any]] = []
    packages: list[dict[str, Any]] = []
    for package_index, item in enumerate(work, start=1):
        remote = f"datasets/{PAI_REPO}@{PAI_REVISION}/{item['package_path']}"
        with filesystem.open(remote, "rb") as source:
            package_table = parquet.read_table(source)
        package_selected_rows = 0
        for record in item["records"]:
            selected = package_table.filter(
                compute.equal(package_table["clip_id"], record["clip_id"])
            )
            if selected.num_rows <= 0:
                raise ValueError("CALIBRATION_SHORTLIST_ROW_MISSING")
            selected = selected.drop_columns(["clip_id"])
            validation = _validate_table(item["feature"], selected)
            relative = target_relative_path(
                record["candidate_digest"], item["feature"]
            )
            target = output_root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            if not target.exists():
                partial = target.with_suffix(".parquet.part")
                parquet.write_table(selected, partial)
                partial.chmod(0o600)
                partial.replace(target)
            materialized.append({
                "candidate_digest": record["candidate_digest"],
                "clip_id": record["clip_id"],
                "feature": item["feature"],
                "relative_path": relative.as_posix(),
                "rows": selected.num_rows,
                "bytes": target.stat().st_size,
                "sha256": _sha256(target),
                **validation,
            })
            package_selected_rows += selected.num_rows
        packages.append({
            "feature": item["feature"],
            "chunk": item["chunk"],
            "package_path": item["package_path"],
            "selected_row_count": package_selected_rows,
        })
        if package_index % 25 == 0 or package_index == len(work):
            print(
                f"calibration packages {package_index}/{len(work)}; "
                f"candidate features {len(materialized)}",
                flush=True,
            )
    closure: dict[str, int] = defaultdict(int)
    for item in materialized:
        closure[item["candidate_digest"]] += 1
    expected_candidate_count = len(shortlist["records"])
    if len(closure) != expected_candidate_count or set(closure.values()) != {5}:
        raise ValueError("CALIBRATION_CANDIDATE_CLOSURE_FAILED")
    result = {
        "materialization_version": "guardsynth-m16-calibration-materialization-v0.2",
        "run_date": date.today().isoformat(),
        "source_repository": PAI_REPO,
        "source_revision": PAI_REVISION,
        "shortlist_sha256": _sha256(shortlist_path),
        "calibration_features": list(FEATURES),
        "selected_candidate_count": len(closure),
        "accessed_package_count": len(packages),
        "materialized_candidate_feature_count": len(materialized),
        "materialized_bytes": sum(item["bytes"] for item in materialized),
        "candidate_feature_closure": (
            f"{expected_candidate_count}_OF_{expected_candidate_count}_HAVE_5_OF_5_CALIBRATION_FEATURES"
        ),
        "full_package_download_performed": False,
        "range_streamed_selected_rows_only": True,
        "network_or_credential_use_performed": True,
        "accessed_packages": packages,
        "records": materialized,
        "claim_scope": "CALIBRATION_SOURCE_MATERIALIZATION_NOT_ASSOCIATION_OR_VEHICLE_SAFETY",
    }
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
            "materialized_candidate_feature_count",
            "materialized_bytes",
            "candidate_feature_closure",
        )
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
