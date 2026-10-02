#!/usr/bin/env python3
"""Build a review-only run from an immutable M16 geometry candidate run."""

from __future__ import annotations

import argparse
import base64
from datetime import date
import hashlib
import json
from pathlib import Path
import subprocess
from typing import Any

from generate_geometry_candidates import render_workbench


EXPERIMENT_ID = "GUARDSYNTH-M16-SCENE-ACQUISITION-001"
RUN_STATUS = "M16_GEOMETRY_CURATOR_WORKBENCH_READY"
WORKBENCH_NAME = "geometry_candidate_workbench.html"


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    path.chmod(0o600)


def _write_text(path: Path, value: str) -> None:
    path.write_text(value, encoding="utf-8")
    path.chmod(0o600)


def _verified_image_data_url(root: Path, relative: str, expected_hash: str) -> str:
    path = root / relative
    if not path.is_file() or _sha256(path) != expected_hash:
        raise ValueError("M16_GEOMETRY_REVIEW_SOURCE_IMAGE_HASH_CHANGED")
    return "data:image/jpeg;base64," + base64.b64encode(path.read_bytes()).decode("ascii")


def _review_record(source_run_dir: Path, record: dict[str, Any]) -> dict[str, Any]:
    t0 = [frame for frame in record["frames"] if float(frame["offset_s"]) == 0.0]
    if len(t0) != 1:
        raise ValueError("M16_GEOMETRY_REVIEW_T0_FRAME_INVALID")
    frame = t0[0]
    return {
        "review_index": record["review_index"],
        "candidate_digest": record["candidate_digest"],
        "slice": record["slice"],
        "event_timestamp_us": record["event_timestamp_us"],
        "source_video_sha256": record["source_video_sha256"],
        "t0_source_pixel_sha256": frame["source_pixel_sha256"],
        "t0_overlay_sha256": frame["overlay_sha256"],
        "contact_sheet_data_url": _verified_image_data_url(
            source_run_dir,
            record["contact_sheet_path"],
            record["contact_sheet_sha256"],
        ),
        "t0_overlay_data_url": _verified_image_data_url(
            source_run_dir,
            frame["overlay_path"],
            frame["overlay_sha256"],
        ),
    }


def execute(*, source_run_dir: Path, output_dir: Path, run_id: str) -> dict[str, Any]:
    if output_dir.exists():
        raise FileExistsError("refusing to overwrite M16 geometry review run")
    candidate_path = source_run_dir / "GEOMETRY_CANDIDATE_MANIFEST.json"
    source_manifest_path = source_run_dir / "RUN_MANIFEST.json"
    if not candidate_path.is_file() or not source_manifest_path.is_file():
        raise FileNotFoundError("M16_GEOMETRY_REVIEW_SOURCE_RUN_INCOMPLETE")
    candidate_hash = _sha256(candidate_path)
    source_manifest = _load(source_manifest_path)
    if (
        source_manifest.get("output_hashes", {}).get("geometry_candidate_manifest")
        != candidate_hash
    ):
        raise ValueError("M16_GEOMETRY_REVIEW_SOURCE_MANIFEST_HASH_CHANGED")
    candidate_manifest = _load(candidate_path)
    records = candidate_manifest.get("records", [])
    if (
        candidate_manifest.get("classified_event_count") != 98
        or len(records) != 98
        or len({record["candidate_digest"] for record in records}) != 98
    ):
        raise ValueError("M16_GEOMETRY_REVIEW_CANDIDATE_SET_INVALID")

    review_records = [_review_record(source_run_dir, record) for record in records]
    output_dir.mkdir(parents=True)
    output_dir.chmod(0o700)
    workbench_path = output_dir / WORKBENCH_NAME
    _write_text(
        workbench_path,
        render_workbench(review_records, manifest_sha256=candidate_hash),
    )
    result = {
        "experiment_id": EXPERIMENT_ID,
        "run_id": run_id,
        "run_date": date.today().isoformat(),
        "status": RUN_STATUS,
        "candidate_count": len(records),
        "curator_review_completed_count": 0,
        "source_candidate_run_id": source_manifest.get("run_id", source_run_dir.name),
        "machine_candidate_promoted_to_ground_truth": False,
        "claim_scope": candidate_manifest.get("claim_scope", ""),
    }
    revision = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=Path(__file__).resolve().parents[5],
        check=False,
        capture_output=True,
        text=True,
    ).stdout.strip() or "NO_GIT_METADATA"
    manifest = {
        **result,
        "code_revision": revision,
        "input_hashes": {
            "geometry_candidate_manifest": candidate_hash,
            "source_run_manifest": _sha256(source_manifest_path),
        },
        "output_hashes": {
            "geometry_candidate_workbench": _sha256(workbench_path),
        },
        "network_use_performed": False,
        "gpu_inference_performed": False,
    }
    report = f"""# M16 geometry curator 검토 화면

- 상태: `{RUN_STATUS}`
- 후보 수: {len(records)}
- 원본 후보 run: `{result['source_candidate_run_id']}`

기존 source-bound geometry 후보와 이미지 해시를 검증한 뒤 검토 화면만 새로 구성했다.
모델 추론이나 source-complete·eligible 판정은 다시 수행하지 않았다.
"""
    _write_json(output_dir / "RESULT.json", result)
    _write_json(output_dir / "RUN_MANIFEST.json", manifest)
    _write_text(output_dir / "REPORT_KO.md", report)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-run-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    result = execute(
        source_run_dir=args.source_run_dir,
        output_dir=args.output_dir,
        run_id=args.run_id,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
