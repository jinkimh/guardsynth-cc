#!/usr/bin/env python3
"""Integrate completed M16 geometry review into the fail-closed source frontier."""

from __future__ import annotations

import argparse
from collections import Counter
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
CLAIM_SCOPE = (
    "CURATOR_CONFIRMED_SOURCE_BOUND_ROAD_GEOMETRY_CANDIDATE_"
    "NOT_SEMANTIC_ASSOCIATION_SOURCE_COMPLETE_OR_VEHICLE_SAFETY"
)
ACCEPTED = "ACCEPTABLE_VISIBLE_CANDIDATE"
MANUAL = {"MINOR_CORRECTION_REQUIRED", "UNUSABLE_MACHINE_CANDIDATE"}


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    path.chmod(0o600)


def _write_text(path: Path, value: str) -> None:
    path.write_text(value, encoding="utf-8")
    path.chmod(0o600)


def _assert_hash(path: Path, expected: str, reason: str) -> None:
    if not path.is_file() or _sha256(path) != expected:
        raise ValueError(reason)


def _t0(record: dict[str, Any]) -> dict[str, Any]:
    frames = [frame for frame in record["frames"] if float(frame["offset_s"]) == 0.0]
    if len(frames) != 1:
        raise ValueError("M16_GEOMETRY_FRONTIER_T0_FRAME_INVALID")
    return frames[0]


def _review_binding_valid(
    candidate: dict[str, Any], review: dict[str, Any]
) -> bool:
    frame = _t0(candidate)
    expected = {
        "review_index": candidate["review_index"],
        "slice": candidate["slice"],
        "event_timestamp_us": candidate["event_timestamp_us"],
        "source_video_sha256": candidate["source_video_sha256"],
        "t0_source_pixel_sha256": frame["source_pixel_sha256"],
        "t0_overlay_sha256": frame["overlay_sha256"],
    }
    return all(review.get(key) == value for key, value in expected.items())


def _verified_mask_evidence(
    candidate_run_dir: Path, candidate: dict[str, Any]
) -> list[dict[str, Any]]:
    evidence: list[dict[str, Any]] = []
    for frame in candidate["frames"]:
        item = {
            "offset_s": frame["offset_s"],
            "timestamp_us": frame["timestamp_us"],
        }
        for kind in ("drivable", "lane"):
            path_key = f"{kind}_mask_path"
            hash_key = f"{kind}_mask_sha256"
            _assert_hash(
                candidate_run_dir / frame[path_key],
                frame[hash_key],
                "M16_GEOMETRY_FRONTIER_MASK_HASH_CHANGED",
            )
            item[f"{kind}_mask"] = {
                "relative_path": frame[path_key],
                "sha256": frame[hash_key],
                "evidence_ref": f"restricted-sha256:{frame[hash_key]}#/",
            }
        evidence.append(item)
    return evidence


def build_frontier(
    *,
    candidate_run_dir: Path,
    candidate_manifest: dict[str, Any],
    review_document: dict[str, Any],
    curator_result: dict[str, Any],
    structured_audit: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    candidates = candidate_manifest.get("records", [])
    reviews = review_document.get("records", [])
    prior_records = structured_audit.get("records", [])
    if (
        len(candidates) != 98
        or len(reviews) != 98
        or len(prior_records) != 98
        or curator_result.get("curator_review_complete") is not True
        or curator_result.get("curator_review_completed_count") != 98
    ):
        raise ValueError("M16_GEOMETRY_FRONTIER_INPUT_COUNT_INVALID")

    reviews_by_digest = {record["candidate_digest"]: record for record in reviews}
    prior_by_digest = {record["candidate_digest"]: record for record in prior_records}
    candidate_digests = {record["candidate_digest"] for record in candidates}
    if (
        len(reviews_by_digest) != 98
        or len(prior_by_digest) != 98
        or set(reviews_by_digest) != candidate_digests
        or set(prior_by_digest) != candidate_digests
    ):
        raise ValueError("M16_GEOMETRY_FRONTIER_EVENT_SET_MISMATCH")

    records: list[dict[str, Any]] = []
    mask_file_count = 0
    accepted_count = 0
    manual_pending_count = 0
    semantic_pixel_count = 0
    country_counts: Counter[str] = Counter()
    slice_counts: Counter[str] = Counter()
    task_counts: Counter[str] = Counter()
    for candidate in sorted(candidates, key=lambda item: item["review_index"]):
        digest = candidate["candidate_digest"]
        review = reviews_by_digest[digest]
        prior = prior_by_digest[digest]
        if not _review_binding_valid(candidate, review):
            raise ValueError("M16_GEOMETRY_FRONTIER_REVIEW_BINDING_INVALID")
        assessment = review.get("machine_geometry_assessment")
        polygons = review.get("normalized_pixel_polygons") or {}
        mask_evidence: list[dict[str, Any]] = []
        if assessment == ACCEPTED:
            accepted_count += 1
            mask_evidence = _verified_mask_evidence(candidate_run_dir, candidate)
            mask_file_count += 2 * len(mask_evidence)
            pixel_status = "AVAILABLE_CURATOR_CONFIRMED_MACHINE_MASKS"
        elif assessment in MANUAL and polygons:
            semantic_pixel_count += 1
            pixel_status = "AVAILABLE_CURATOR_NORMALIZED_PIXEL_POLYGONS"
        elif assessment in MANUAL:
            manual_pending_count += 1
            pixel_status = "REVIEW_COMPLETE_CORRECTION_DATA_PENDING"
        elif assessment == "NOT_OBSERVABLE":
            pixel_status = "DEFERRED_NOT_OBSERVABLE"
        else:
            raise ValueError("M16_GEOMETRY_FRONTIER_ASSESSMENT_INVALID")

        tasks: list[str] = []
        if assessment in MANUAL and not polygons:
            tasks.append("ACQUIRE_MANUAL_NORMALIZED_PIXEL_POLYGONS")
        elif pixel_status.startswith("AVAILABLE_"):
            tasks.append("BIND_SLICE_SPECIFIC_SEMANTIC_ZONE_IN_DATASET_RIG")
        if prior["field_status"]["relevant_actor_or_control_state"] != "AVAILABLE_SOURCE_LINKED":
            tasks.append("ACQUIRE_RELEVANT_ACTOR_OR_CONTROL_SOURCE")
        if prior["field_status"]["target_zone_or_lane_association"] != "AVAILABLE_SOURCE_LINKED":
            tasks.append("ACQUIRE_TARGET_ZONE_OR_LANE_ASSOCIATION")
        tasks.extend((
            "BIND_JURISDICTION_MATCHED_AUTHORITY",
            "ACQUIRE_OUTCOME_LIFECYCLE_WITNESS",
        ))
        task_counts.update(tasks)
        country = prior.get("country", "UNKNOWN")
        country_counts[country] += 1
        slice_counts[candidate["slice"]] += 1
        records.append({
            "candidate_digest": digest,
            "review_index": candidate["review_index"],
            "slice": candidate["slice"],
            "country": country,
            "event_timestamp_us": candidate["event_timestamp_us"],
            "curator_assessment": assessment,
            "pixel_geometry_status": pixel_status,
            "coordinate_frame": candidate_manifest["coordinate_frame"],
            "unit": "pixel",
            "source_video_sha256": candidate["source_video_sha256"],
            "model_source_revision": candidate["model_source_revision"],
            "model_weight_sha256": candidate["model_weight_sha256"],
            "machine_mask_evidence": mask_evidence,
            "normalized_pixel_polygons": polygons,
            "relevant_actor_or_control_state_status": prior[
                "field_status"
            ]["relevant_actor_or_control_state"],
            "target_zone_or_lane_association_status": prior[
                "field_status"
            ]["target_zone_or_lane_association"],
            "slice_specific_geometry_status": (
                "REVIEW_REQUIRED_SEMANTIC_ZONE_AND_DATASET_RIG_BINDING"
            ),
            "jurisdiction_authority_status": (
                "REVIEW_REQUIRED_JURISDICTION_MATCHED_AUTHORITY"
            ),
            "outcome_lifecycle_status": "REVIEW_REQUIRED_SOURCE_LIFECYCLE_WITNESS",
            "source_complete": False,
            "eligible": False,
            "next_source_tasks": tasks,
        })

    if accepted_count != curator_result.get("accepted_machine_geometry_count"):
        raise ValueError("M16_GEOMETRY_FRONTIER_ACCEPTED_COUNT_MISMATCH")
    if manual_pending_count != curator_result.get("manual_correction_pending_count"):
        raise ValueError("M16_GEOMETRY_FRONTIER_MANUAL_PENDING_COUNT_MISMATCH")

    audit = {
        "audit_version": "guardsynth-m16-geometry-source-frontier-v0.1",
        "claim_scope": CLAIM_SCOPE,
        "classified_event_count": 98,
        "curator_review_completed_count": 98,
        "curator_confirmed_machine_mask_event_count": accepted_count,
        "verified_machine_mask_file_count": mask_file_count,
        "curator_semantic_pixel_polygon_event_count": semantic_pixel_count,
        "manual_correction_data_pending_count": manual_pending_count,
        "relevant_actor_or_control_state_closed_count": structured_audit[
            "relevant_actor_or_control_state_closed_count"
        ],
        "target_zone_or_lane_association_closed_count": structured_audit[
            "target_zone_or_lane_association_closed_count"
        ],
        "slice_specific_geometry_closed_count": 0,
        "jurisdiction_authority_closed_count": 0,
        "outcome_lifecycle_witness_closed_count": 0,
        "source_complete_8_of_8_count": 0,
        "new_final_outcome_assigned_count": 0,
        "newly_eligible_scene_count": 0,
        "historical_eligible_scene_count": 1,
        "annotation_start_allowed": False,
        "synthetic_required_field_fill_count": 0,
        "country_counts": dict(sorted(country_counts.items())),
        "slice_counts": dict(sorted(slice_counts.items())),
        "source_task_counts": dict(sorted(task_counts.items())),
        "records": records,
    }
    queue = {
        "queue_version": "guardsynth-m16-source-frontier-queue-v0.1",
        "record_count": len(records),
        "task_counts": dict(sorted(task_counts.items())),
        "country_counts": dict(sorted(country_counts.items())),
        "slice_counts": dict(sorted(slice_counts.items())),
        "records": [
            {
                "candidate_digest": record["candidate_digest"],
                "review_index": record["review_index"],
                "slice": record["slice"],
                "country": record["country"],
                "next_source_tasks": record["next_source_tasks"],
            }
            for record in records
        ],
        "claim_scope": "SOURCE_ACQUISITION_QUEUE_NOT_COMPLETED_SOURCE_OR_SAFETY",
    }
    return audit, queue


def execute(
    *,
    candidate_run_dir: Path,
    curator_review_dir: Path,
    review_json_path: Path,
    structured_link_run_dir: Path,
    output_dir: Path,
    run_id: str,
) -> dict[str, Any]:
    if output_dir.exists():
        raise FileExistsError("refusing to overwrite M16 geometry source frontier run")
    candidate_path = candidate_run_dir / "GEOMETRY_CANDIDATE_MANIFEST.json"
    candidate_run_manifest_path = candidate_run_dir / "RUN_MANIFEST.json"
    curator_result_path = curator_review_dir / "RESULT.json"
    curator_run_manifest_path = curator_review_dir / "RUN_MANIFEST.json"
    structured_audit_path = structured_link_run_dir / "CASCADE_STRUCTURED_LINK_AUDIT.json"
    structured_run_manifest_path = structured_link_run_dir / "RUN_MANIFEST.json"
    required = (
        candidate_path,
        candidate_run_manifest_path,
        curator_result_path,
        curator_run_manifest_path,
        review_json_path,
        structured_audit_path,
        structured_run_manifest_path,
    )
    if any(not path.is_file() for path in required):
        raise FileNotFoundError("M16_GEOMETRY_FRONTIER_INPUT_MISSING")

    candidate_hash = _sha256(candidate_path)
    candidate_run_manifest = _load(candidate_run_manifest_path)
    if candidate_run_manifest.get("output_hashes", {}).get(
        "geometry_candidate_manifest"
    ) != candidate_hash:
        raise ValueError("M16_GEOMETRY_FRONTIER_CANDIDATE_HASH_CHANGED")
    curator_run_manifest = _load(curator_run_manifest_path)
    _assert_hash(
        curator_result_path,
        curator_run_manifest.get("output_hashes", {}).get("result", ""),
        "M16_GEOMETRY_FRONTIER_CURATOR_RESULT_HASH_CHANGED",
    )
    if (
        curator_run_manifest.get("input_hashes", {}).get("geometry_candidate_manifest")
        != candidate_hash
        or curator_run_manifest.get("input_hashes", {}).get("review_json")
        != _sha256(review_json_path)
    ):
        raise ValueError("M16_GEOMETRY_FRONTIER_CURATOR_INPUT_BINDING_CHANGED")
    review_document = _load(review_json_path)
    if review_document.get("manifest_sha256") != candidate_hash:
        raise ValueError("M16_GEOMETRY_FRONTIER_REVIEW_MANIFEST_MISMATCH")

    audit, queue = build_frontier(
        candidate_run_dir=candidate_run_dir,
        candidate_manifest=_load(candidate_path),
        review_document=review_document,
        curator_result=_load(curator_result_path),
        structured_audit=_load(structured_audit_path),
    )
    result = {
        "experiment_id": EXPERIMENT_ID,
        "run_id": run_id,
        "run_date": date.today().isoformat(),
        "status": "M16_SOURCE_FRONTIER_AUDITED_EXTERNAL_SOURCES_REQUIRED",
        "claim_scope": CLAIM_SCOPE,
        "classified_event_count": 98,
        "curator_review_completed_count": 98,
        "curator_confirmed_machine_mask_event_count": audit[
            "curator_confirmed_machine_mask_event_count"
        ],
        "verified_machine_mask_file_count": audit["verified_machine_mask_file_count"],
        "manual_correction_data_pending_count": audit[
            "manual_correction_data_pending_count"
        ],
        "relevant_actor_or_control_state_closed_count": audit[
            "relevant_actor_or_control_state_closed_count"
        ],
        "target_zone_or_lane_association_closed_count": audit[
            "target_zone_or_lane_association_closed_count"
        ],
        "slice_specific_geometry_closed_count": 0,
        "jurisdiction_authority_closed_count": 0,
        "outcome_lifecycle_witness_closed_count": 0,
        "new_source_complete_8_of_8_count": 0,
        "new_final_outcome_assigned_count": 0,
        "newly_eligible_scene_count": 0,
        "eligible_scene_count": 1,
        "target_scene_count": 60,
        "total_scene_shortfall": 59,
        "annotation_start_allowed": False,
        "synthetic_required_field_fill_count": 0,
    }
    preflight = {
        "protocol_version": "guardsynth-expert-pilot-v0.1",
        "status": "BLOCKED_DATA_SHORTFALL",
        "annotation_start_allowed": False,
        "eligible_scene_count": 1,
        "target_scene_count": 60,
        "total_scene_shortfall": 59,
        "reason_codes": [
            "M16_REQUIRES_60_SOURCE_COMPLETE_SCENES",
            "M16_SEMANTIC_GEOMETRY_AUTHORITY_AND_LIFECYCLE_NOT_CLOSED",
            "M16_SLICE_AND_OUTCOME_QUOTAS_NOT_MET",
        ],
        "synthetic_scene_fill_performed": False,
        "actual_vehicle_validation_deferred_to_m21": True,
        "claim_scope": "M16_PILOT_PREFLIGHT_NOT_EXPERT_RESULT_OR_VEHICLE_SAFETY",
    }

    output_dir.mkdir(parents=True)
    output_dir.chmod(0o700)
    audit_path = output_dir / "GEOMETRY_SOURCE_INTEGRATION_AUDIT.json"
    queue_path = output_dir / "SOURCE_ACQUISITION_QUEUE.json"
    result_path = output_dir / "RESULT.json"
    preflight_path = output_dir / "PILOT_PREFLIGHT.json"
    report_path = output_dir / "REPORT_KO.md"
    _write_json(audit_path, audit)
    _write_json(queue_path, queue)
    _write_json(result_path, result)
    _write_json(preflight_path, preflight)
    _write_text(
        report_path,
        f"""# M16 geometry source frontier 통합 감사

- curator 검토 완료: **98/98**
- curator가 확인한 source-bound machine mask: **{audit['curator_confirmed_machine_mask_event_count']}/98**
- 재검증한 mask 파일: **{audit['verified_machine_mask_file_count']}**
- 수동 보정 좌표 대기: **{audit['manual_correction_data_pending_count']}**
- relevant actor/control source SET: **{audit['relevant_actor_or_control_state_closed_count']}/98**
- target lane/zone association: **{audit['target_zone_or_lane_association_closed_count']}/98**
- slice-specific rig-frame geometry / authority / lifecycle: **0 / 0 / 0**
- 신규 8/8 / outcome / eligible: **0 / 0 / 0**
- 전체 eligible: **1/60**

승인된 61건의 다섯 시점 drivable/lane mask 610개를 원본 후보 manifest의 경로와 SHA-256으로
재검증해 source-bound road-geometry candidate로 결합했다. 그러나 이 mask는 에고 차로,
횡단 충돌 영역, 정지선·정지 영역 또는 대상 차량 차로의 의미적 binding을 직접 제공하지 않고
camera pixel frame에 머문다. 따라서 dataset-rig meter geometry나 8/8 필드를 임의로 닫지 않았다.

나머지 actor/control association, 관할에 맞는 versioned authority, outcome lifecycle witness를
항목별 `SOURCE_ACQUISITION_QUEUE.json`으로 고정했다. 이 자료가 확보되기 전에는 formal pilot
annotation을 시작하지 않는다.
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
        "input_class": "LICENSE_RESTRICTED_SOURCE_AND_HUMAN_REVIEW",
        "input_hashes": {
            "geometry_candidate_manifest": candidate_hash,
            "geometry_candidate_run_manifest": _sha256(candidate_run_manifest_path),
            "geometry_curator_result": _sha256(curator_result_path),
            "geometry_curator_run_manifest": _sha256(curator_run_manifest_path),
            "geometry_review_json": _sha256(review_json_path),
            "cascade_structured_link_audit": _sha256(structured_audit_path),
            "cascade_structured_link_run_manifest": _sha256(
                structured_run_manifest_path
            ),
            "pipeline": _sha256(Path(__file__)),
        },
        "output_hashes": {
            "geometry_source_integration_audit": _sha256(audit_path),
            "source_acquisition_queue": _sha256(queue_path),
            "pilot_preflight": _sha256(preflight_path),
            "result": _sha256(result_path),
            "report_ko": _sha256(report_path),
        },
        "raw_video_copied": False,
        "network_use_performed": False,
        "gpu_inference_performed": False,
    }
    _write_json(output_dir / "RUN_MANIFEST.json", manifest)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate-run-dir", type=Path, required=True)
    parser.add_argument("--curator-review-dir", type=Path, required=True)
    parser.add_argument("--review-json", type=Path, required=True)
    parser.add_argument("--structured-link-run-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    result = execute(
        candidate_run_dir=args.candidate_run_dir,
        curator_review_dir=args.curator_review_dir,
        review_json_path=args.review_json,
        structured_link_run_dir=args.structured_link_run_dir,
        output_dir=args.output_dir,
        run_id=args.run_id,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
