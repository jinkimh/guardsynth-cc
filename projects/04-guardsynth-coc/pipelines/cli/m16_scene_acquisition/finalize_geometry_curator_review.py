#!/usr/bin/env python3
"""Validate an uploaded M16 geometry review and record review completion."""

from __future__ import annotations

import argparse
from collections import Counter
import csv
from datetime import date
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from typing import Any


if __package__ in {None, ""}:
    ROOT_BOOTSTRAP = next(
        parent
        for parent in Path(__file__).resolve().parents
        if (parent / "PROJECT_REGISTRY.json").is_file()
    )
    sys.path.insert(0, str(ROOT_BOOTSTRAP))

from cli.project_paths import project_root


ROOT = project_root(__file__)
EXPERIMENT_ID = "GUARDSYNTH-M16-SCENE-ACQUISITION-001"
ALLOWED_ASSESSMENTS = {
    "ACCEPTABLE_VISIBLE_CANDIDATE",
    "MINOR_CORRECTION_REQUIRED",
    "UNUSABLE_MACHINE_CANDIDATE",
    "NOT_OBSERVABLE",
}
EXPECTED_DISPOSITIONS = {
    "ACCEPTABLE_VISIBLE_CANDIDATE": "CONFIRM_MACHINE_CANDIDATE",
    "MINOR_CORRECTION_REQUIRED": "USE_MANUAL_POLYGONS",
    "UNUSABLE_MACHINE_CANDIDATE": "USE_MANUAL_POLYGONS",
    "NOT_OBSERVABLE": "DEFER_INSUFFICIENT_EVIDENCE",
}
MANUAL_ASSESSMENTS = {
    "MINOR_CORRECTION_REQUIRED",
    "UNUSABLE_MACHINE_CANDIDATE",
}


def _load(path: Path) -> Any:
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


def _required_polygon_labels(slice_name: str) -> set[str]:
    second = {
        "PEDESTRIAN_CYCLIST_YIELD": "CROSSING_CONFLICT_ZONE",
        "STOP_SIGNALS": "STOP_LINE_STOPPING_ZONE",
        "FOLLOWING_CUT_IN": "TARGET_LANE_CORRIDOR",
    }.get(slice_name)
    if second is None:
        raise ValueError("M16_GEOMETRY_REVIEW_SLICE_INVALID")
    return {"EGO_LANE_ZONE", second}


def _validate_polygons(value: Any) -> dict[str, list[list[list[float]]]]:
    if not isinstance(value, dict):
        raise ValueError("M16_GEOMETRY_REVIEW_POLYGONS_INVALID")
    normalized: dict[str, list[list[list[float]]]] = {}
    for label, polygons in value.items():
        if not isinstance(label, str) or not isinstance(polygons, list):
            raise ValueError("M16_GEOMETRY_REVIEW_POLYGONS_INVALID")
        normalized[label] = []
        for polygon in polygons:
            if not isinstance(polygon, list) or len(polygon) < 3:
                raise ValueError("M16_GEOMETRY_REVIEW_POLYGON_TOO_SHORT")
            points: list[list[float]] = []
            for point in polygon:
                if (
                    not isinstance(point, list)
                    or len(point) != 2
                    or not all(isinstance(axis, (int, float)) for axis in point)
                    or not all(0.0 <= float(axis) <= 1.0 for axis in point)
                ):
                    raise ValueError("M16_GEOMETRY_REVIEW_POINT_INVALID")
                points.append([float(point[0]), float(point[1])])
            normalized[label].append(points)
    return normalized


def _normalize_json_record(record: dict[str, Any]) -> dict[str, Any]:
    value = dict(record)
    value["review_index"] = int(value["review_index"])
    value["event_timestamp_us"] = int(value["event_timestamp_us"])
    value["normalized_pixel_polygons"] = _validate_polygons(
        value.get("normalized_pixel_polygons", {})
    )
    return value


def _normalize_csv_record(record: dict[str, str]) -> dict[str, Any]:
    value: dict[str, Any] = dict(record)
    value["review_index"] = int(value["review_index"])
    value["event_timestamp_us"] = int(value["event_timestamp_us"])
    value["normalized_pixel_polygons"] = _validate_polygons(
        json.loads(value["normalized_pixel_polygons"] or "{}")
    )
    source_decision = value.get("source_complete_decision_included", "").lower()
    if source_decision not in {"false", "0"}:
        raise ValueError("M16_GEOMETRY_REVIEW_SOURCE_DECISION_INCLUDED")
    value["source_complete_decision_included"] = False
    return value


def _load_csv(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8", newline="") as stream:
        return [_normalize_csv_record(row) for row in csv.DictReader(stream)]


def _candidate_review_record(record: dict[str, Any]) -> dict[str, Any]:
    t0 = [frame for frame in record["frames"] if float(frame["offset_s"]) == 0.0]
    if len(t0) != 1:
        raise ValueError("M16_GEOMETRY_REVIEW_T0_FRAME_INVALID")
    return {
        "candidate_digest": record["candidate_digest"],
        "review_index": record["review_index"],
        "slice": record["slice"],
        "event_timestamp_us": record["event_timestamp_us"],
        "source_video_sha256": record["source_video_sha256"],
        "t0_source_pixel_sha256": t0[0]["source_pixel_sha256"],
        "t0_overlay_sha256": t0[0]["overlay_sha256"],
    }


def _validate_records(
    *,
    candidate_records: list[dict[str, Any]],
    review_records: list[dict[str, Any]],
    curator_id: str,
) -> dict[str, Any]:
    if len(candidate_records) != 98 or len(review_records) != 98:
        raise ValueError("M16_GEOMETRY_REVIEW_RECORD_COUNT_INVALID")
    if not curator_id.strip():
        raise ValueError("M16_GEOMETRY_REVIEW_CURATOR_ID_REQUIRED")

    assessments: Counter[str] = Counter()
    polygon_record_count = 0
    polygon_count = 0
    manual_geometry_ready_count = 0
    for candidate, review in zip(candidate_records, review_records):
        expected = _candidate_review_record(candidate)
        if any(review.get(key) != value for key, value in expected.items()):
            raise ValueError("M16_GEOMETRY_REVIEW_CANDIDATE_BINDING_MISMATCH")
        assessment = str(review.get("machine_geometry_assessment", ""))
        if assessment not in ALLOWED_ASSESSMENTS:
            raise ValueError("M16_GEOMETRY_REVIEW_ASSESSMENT_MISSING")
        if review.get("geometry_disposition") != EXPECTED_DISPOSITIONS[assessment]:
            raise ValueError("M16_GEOMETRY_REVIEW_DISPOSITION_INVALID")
        if review.get("source_complete_decision_included") is not False:
            raise ValueError("M16_GEOMETRY_REVIEW_SOURCE_DECISION_INCLUDED")
        embedded_curator = str(review.get("curator_id", "")).strip()
        if embedded_curator and embedded_curator != curator_id.strip():
            raise ValueError("M16_GEOMETRY_REVIEW_CURATOR_ID_MISMATCH")

        assessments[assessment] += 1
        polygons = review["normalized_pixel_polygons"]
        if polygons:
            polygon_record_count += 1
            polygon_count += sum(len(items) for items in polygons.values())
        if assessment in MANUAL_ASSESSMENTS and _required_polygon_labels(review["slice"]).issubset(
            {label for label, items in polygons.items() if items}
        ):
            manual_geometry_ready_count += 1

    accepted = assessments["ACCEPTABLE_VISIBLE_CANDIDATE"]
    manual = sum(assessments[name] for name in MANUAL_ASSESSMENTS)
    deferred = assessments["NOT_OBSERVABLE"]
    return {
        "curator_review_completed_count": sum(assessments.values()),
        "assessment_counts": dict(sorted(assessments.items())),
        "accepted_machine_geometry_count": accepted,
        "manual_correction_requested_count": manual,
        "manual_geometry_ready_count": manual_geometry_ready_count,
        "manual_correction_pending_count": manual - manual_geometry_ready_count,
        "not_observable_count": deferred,
        "polygon_record_count": polygon_record_count,
        "polygon_count": polygon_count,
        "geometry_resolution_complete_count": accepted + manual_geometry_ready_count,
    }


def execute(
    *,
    candidate_run_dir: Path,
    review_json_path: Path,
    review_csv_path: Path,
    output_dir: Path,
    run_id: str,
    curator_id: str,
) -> dict[str, Any]:
    if output_dir.exists():
        raise FileExistsError("refusing to overwrite M16 geometry curator review result")
    candidate_path = candidate_run_dir / "GEOMETRY_CANDIDATE_MANIFEST.json"
    candidate_run_manifest_path = candidate_run_dir / "RUN_MANIFEST.json"
    required = (
        candidate_path,
        candidate_run_manifest_path,
        review_json_path,
        review_csv_path,
    )
    if any(not path.is_file() for path in required):
        raise FileNotFoundError("M16_GEOMETRY_REVIEW_INPUT_MISSING")

    candidate_hash = _sha256(candidate_path)
    candidate_manifest = _load(candidate_path)
    candidate_run_manifest = _load(candidate_run_manifest_path)
    if (
        candidate_run_manifest.get("output_hashes", {}).get("geometry_candidate_manifest")
        != candidate_hash
    ):
        raise ValueError("M16_GEOMETRY_REVIEW_CANDIDATE_MANIFEST_HASH_CHANGED")

    review_document = _load(review_json_path)
    if review_document.get("manifest_sha256") != candidate_hash:
        raise ValueError("M16_GEOMETRY_REVIEW_MANIFEST_BINDING_MISMATCH")
    json_records = [
        _normalize_json_record(record) for record in review_document.get("records", [])
    ]
    csv_records = _load_csv(review_csv_path)
    if json_records != csv_records:
        raise ValueError("M16_GEOMETRY_REVIEW_JSON_CSV_MISMATCH")

    summary = _validate_records(
        candidate_records=candidate_manifest.get("records", []),
        review_records=json_records,
        curator_id=curator_id,
    )
    review_complete = summary["curator_review_completed_count"] == 98
    geometry_complete = summary["geometry_resolution_complete_count"] == 98
    status = (
        "GEOMETRY_CURATOR_REVIEW_COMPLETE"
        if geometry_complete
        else "GEOMETRY_CURATOR_REVIEW_COMPLETE_CORRECTION_DATA_PENDING"
    )
    result = {
        "experiment_id": EXPERIMENT_ID,
        "run_id": run_id,
        "run_date": date.today().isoformat(),
        "status": status,
        "claim_scope": "CURATOR_GEOMETRY_REVIEW_NOT_SOURCE_COMPLETE_OR_VEHICLE_SAFETY",
        "review_record_count": len(json_records),
        "reviewer_count": 1,
        "review_completion_rule": "NONEMPTY_MACHINE_GEOMETRY_ASSESSMENT",
        "curator_review_complete": review_complete,
        **summary,
        "source_field_update_count": 0,
        "machine_candidate_promoted_to_ground_truth": False,
        "annotation_start_allowed": False,
    }

    output_dir.mkdir(parents=True)
    output_dir.chmod(0o700)
    result_path = output_dir / "RESULT.json"
    report_path = output_dir / "REPORT_KO.md"
    _write_json(result_path, result)
    _write_text(
        report_path,
        f"""# M16 geometry curator 검토 결과

- 상태: `{status}`
- 검토 완료: {summary['curator_review_completed_count']}/98
- 기계 geometry 확인: {summary['accepted_machine_geometry_count']}
- 수동 보정 요청: {summary['manual_correction_requested_count']}
- 파일에 좌표가 저장된 항목: {summary['polygon_record_count']}
- geometry 해소: {summary['geometry_resolution_complete_count']}/98

기존 업로드 JSON/CSV의 품질 평가 선택을 장면 검토 완료 기준으로 사용했다. 따라서 98개 장면의
검토는 모두 완료다. 업로드 파일에 없는 polygon 좌표는 생성하거나 추정하지 않았으며,
`USE_MANUAL_POLYGONS`로 답한 항목 가운데 좌표가 없는 항목은 별도 보정 데이터 대기로 유지한다.
이 결과는 source-complete, eligible scene 또는 차량 안전 판정이 아니다.
""",
    )
    revision = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    ).stdout.strip() or "NO_GIT_METADATA"
    dirty = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    ).stdout
    manifest = {
        **result,
        "code_revision": revision,
        "workspace_dirty_state_preserved": bool(dirty),
        "input_class": "LICENSE_RESTRICTED_HUMAN_GEOMETRY_REVIEW",
        "input_hashes": {
            "geometry_candidate_manifest": candidate_hash,
            "geometry_candidate_run_manifest": _sha256(candidate_run_manifest_path),
            "review_json": _sha256(review_json_path),
            "review_csv": _sha256(review_csv_path),
            "finalizer": _sha256(Path(__file__)),
        },
        "output_hashes": {
            "result": _sha256(result_path),
            "report_ko": _sha256(report_path),
        },
        "reviewer_identifiers_in_aggregate_outputs": False,
        "raw_image_bytes_included": False,
        "network_use_performed": False,
        "gpu_inference_performed": False,
    }
    _write_json(output_dir / "RUN_MANIFEST.json", manifest)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate-run-dir", type=Path, required=True)
    parser.add_argument("--review-json", type=Path, required=True)
    parser.add_argument("--review-csv", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--curator-id", required=True)
    args = parser.parse_args()
    result = execute(
        candidate_run_dir=args.candidate_run_dir,
        review_json_path=args.review_json,
        review_csv_path=args.review_csv,
        output_dir=args.output_dir,
        run_id=args.run_id,
        curator_id=args.curator_id,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
