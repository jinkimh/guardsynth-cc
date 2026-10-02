#!/usr/bin/env python3
"""Reaudit M16 source closure after completed human video observation."""

from __future__ import annotations

import argparse
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
SRC = ROOT / "projects/04-guardsynth-coc/src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
PLATFORM_SRC = ROOT / "platforms/eblc-bcv/src"
if str(PLATFORM_SRC) not in sys.path:
    sys.path.insert(0, str(PLATFORM_SRC))

from guard_synth.m16_post_review_source_closure import (
    audit_ncore_offline_variant_rule,
    build_post_review_source_closure,
    public_post_review_source_closure_summary,
)
from guard_synth.m16_scene_acquisition import assert_public_export_safe


EXPERIMENT_ID = "GUARDSYNTH-M16-SCENE-ACQUISITION-001"
ARTIFACT_ROOT = ROOT / (
    "artifacts/projects/guardsynth-coc/restricted/"
    "guardsynth-m16-scene-acquisition-001/m16-source-acquisition-2026-08-14-v18"
)
REVIEW_ROOT = ROOT / (
    "artifacts/projects/guardsynth-coc/restricted/"
    "guardsynth-m16-source-review-001/m16-source-review-2026-09-04-v1"
)
PRIMARY_ROOT = ROOT / "data/restricted/nvidia_physicalai/internal-derived/m16-shortlist-v1"
RESERVE_ROOT = ROOT / "data/restricted/nvidia_physicalai/internal-derived/m16-reserve-v1"
PRECHECK = ARTIFACT_ROOT / "SOURCE_REVIEW_PRECHECK.json"
PRIMARY_SENSOR_MANIFEST = PRIMARY_ROOT / "MANIFEST.json"
PRIMARY_CALIBRATION_MANIFEST = PRIMARY_ROOT / "CALIBRATION_MANIFEST.json"
PRIMARY_SENSOR_AUDIT = PRIMARY_ROOT / "SENSOR_EVIDENCE_AUDIT.json"
PRIMARY_CALIBRATION_AUDIT = PRIMARY_ROOT / "CALIBRATION_ASSOCIATION_AUDIT.json"
RESERVE_SENSOR_MANIFEST = RESERVE_ROOT / "MANIFEST.json"
RESERVE_CALIBRATION_MANIFEST = RESERVE_ROOT / "CALIBRATION_MANIFEST.json"
ATTRITION_AUDIT = RESERVE_ROOT / "ATTRITION_RESERVE_EVIDENCE_AUDIT.json"
REVIEW_EXPORT = REVIEW_ROOT / "m16_video_observation_review.json"
REVIEW_SUMMARY = REVIEW_ROOT / "HUMAN_VIDEO_OBSERVATION_SUMMARY.json"
PRIOR_RESULT = ARTIFACT_ROOT / "RESULT.json"
CLAIM_SCOPE = (
    "POST_REVIEW_SOURCE_CLOSURE_AUDIT_NOT_FINAL_ASSOCIATION_EXPERT_EFFECT_OR_VEHICLE_SAFETY"
)


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _write_json(path: Path, value: Any, *, restricted: bool) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    path.chmod(0o600 if restricted else 0o644)


def _validate_member(root: Path, record: dict[str, Any]) -> None:
    path = root / record["relative_path"]
    if (
        not path.is_file()
        or path.stat().st_size != record.get("bytes")
        or _sha256(path) != record.get("sha256")
    ):
        raise ValueError("MATERIALIZED_MEMBER_INTEGRITY_FAILURE")


def _validate_materialized_evidence() -> dict[str, int]:
    precheck = _load(PRECHECK)
    primary_sensor = _load(PRIMARY_SENSOR_MANIFEST)
    primary_calibration = _load(PRIMARY_CALIBRATION_MANIFEST)
    reserve_sensor = _load(RESERVE_SENSOR_MANIFEST)
    reserve_calibration = _load(RESERVE_CALIBRATION_MANIFEST)
    primary_sensor_audit = _load(PRIMARY_SENSOR_AUDIT)
    primary_calibration_audit = _load(PRIMARY_CALIBRATION_AUDIT)
    attrition_audit = _load(ATTRITION_AUDIT)

    primary_digests = {
        item["candidate_digest"] for item in primary_calibration_audit["records"]
    }
    reserve_asset_digests = {
        item["candidate_digest"] for item in reserve_calibration["records"]
    }
    all_asset_digests = primary_digests | reserve_asset_digests
    if (
        len(primary_digests) != 59
        or len(reserve_asset_digests) != 22
        or len(all_asset_digests) != 81
    ):
        raise ValueError("MATERIALIZED_UNIQUE_CLIP_COUNT_INVALID")

    primary_precheck = {
        item["candidate_digest"]
        for item in precheck["records"]
        if item.get("cohort_role") == "PRIMARY"
    }
    if primary_precheck != primary_digests:
        raise ValueError("PRIMARY_PRECHECK_MATERIALIZATION_MISMATCH")
    attrition_by_candidate = {
        item["candidate_digest"]: item for item in attrition_audit["records"]
    }
    reserve_precheck = {
        item["candidate_digest"]
        for item in precheck["records"]
        if item.get("cohort_role") == "RESERVE"
    }
    if reserve_precheck != set(attrition_by_candidate):
        raise ValueError("RESERVE_PRECHECK_MATERIALIZATION_MISMATCH")
    if any(
        item.get("asset_candidate_digest") not in all_asset_digests
        for item in attrition_by_candidate.values()
    ):
        raise ValueError("RESERVE_ASSET_BINDING_MISSING")

    sensor_offline_assets: set[str] = set()
    for root, manifest in (
        (PRIMARY_ROOT, primary_sensor),
        (RESERVE_ROOT, reserve_sensor),
    ):
        for record in manifest["records"]:
            if record.get("feature") == "egomotion.offline":
                _validate_member(root, record)
                sensor_offline_assets.add(record["candidate_digest"])
    calibration_offline_assets: set[str] = set()
    for root, manifest in (
        (PRIMARY_ROOT, primary_calibration),
        (RESERVE_ROOT, reserve_calibration),
    ):
        for record in manifest["records"]:
            _validate_member(root, record)
            if record.get("feature") == "sensor_extrinsics.offline":
                calibration_offline_assets.add(record["candidate_digest"])
    if (
        sensor_offline_assets != all_asset_digests
        or calibration_offline_assets != all_asset_digests
    ):
        raise ValueError("OFFLINE_FEATURE_ASSET_CLOSURE_INVALID")

    counts = {
        "temporal_closure": (
            primary_sensor_audit.get("temporal_closure_candidate_count", 0)
            + attrition_audit.get("temporal_closure_event_count", 0)
        ),
        "calibration_5_of_5": (
            primary_calibration_audit.get("calibration_5_of_5_candidate_count", 0)
            + attrition_audit.get("calibration_5_of_5_event_count", 0)
        ),
        "recorded_rig_binding": (
            primary_calibration_audit.get("recorded_rig_binding_available_count", 0)
            + attrition_audit.get("recorded_rig_binding_available_event_count", 0)
        ),
    }
    if set(counts.values()) != {98}:
        raise ValueError("CLASSIFIED_EVENT_EVIDENCE_CLOSURE_INVALID")
    return {**counts, "materialized_unique_clip_count": len(all_asset_digests)}


def _git_revision() -> tuple[str, str]:
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
    return revision, "WORKSPACE_WITH_UNCOMMITTED_CHANGES" if dirty else "CLEAN"


def execute(
    *,
    restricted_output_dir: Path,
    public_output_dir: Path | None,
    run_id: str,
    ncore_source_path: Path,
    ncore_commit_sha: str,
    ncore_source_url: str,
) -> dict[str, Any]:
    if restricted_output_dir.exists() or (
        public_output_dir is not None and public_output_dir.exists()
    ):
        raise FileExistsError("refusing to overwrite post-review source-closure run")
    required = (
        PRECHECK,
        REVIEW_EXPORT,
        REVIEW_SUMMARY,
        PRIOR_RESULT,
        PRIMARY_SENSOR_MANIFEST,
        PRIMARY_CALIBRATION_MANIFEST,
        PRIMARY_SENSOR_AUDIT,
        PRIMARY_CALIBRATION_AUDIT,
        RESERVE_SENSOR_MANIFEST,
        RESERVE_CALIBRATION_MANIFEST,
        ATTRITION_AUDIT,
        ncore_source_path,
    )
    if any(not path.is_file() for path in required):
        raise FileNotFoundError("M16_POST_REVIEW_SOURCE_INPUT_MISSING")

    source_sha = _sha256(ncore_source_path)
    variant_rule = audit_ncore_offline_variant_rule(
        ncore_source_path.read_text(encoding="utf-8"),
        commit_sha=ncore_commit_sha,
        source_sha256=source_sha,
        source_url=ncore_source_url,
    )
    evidence = _validate_materialized_evidence()
    audit = build_post_review_source_closure(
        precheck=_load(PRECHECK),
        review_export=_load(REVIEW_EXPORT),
        review_summary=_load(REVIEW_SUMMARY),
        variant_rule=variant_rule,
        evidence_counts=evidence,
    )
    audit["materialized_unique_clip_count"] = evidence[
        "materialized_unique_clip_count"
    ]
    prior = _load(PRIOR_RESULT)
    if (
        prior.get("eligible_scene_count") != 1
        or prior.get("source_complete_8_of_8_count") != 3
    ):
        raise ValueError("PRIOR_M16_ELIGIBILITY_BASELINE_CHANGED")

    result = {
        "experiment_id": EXPERIMENT_ID,
        "run_id": run_id,
        "run_date": date.today().isoformat(),
        "status": "M16_SOURCE_CLOSURE_PARTIAL_CALIBRATION_VARIANT_RESOLVED",
        "classified_event_count": audit["classified_event_count"],
        "human_observation_completed_count": audit[
            "human_observation_completed_count"
        ],
        "human_observation_deferred_source_first_count": audit[
            "human_observation_deferred_source_first_count"
        ],
        "materialized_unique_clip_count": evidence["materialized_unique_clip_count"],
        "temporal_closure_count": audit["temporal_closure_count"],
        "calibration_5_of_5_count": audit["calibration_5_of_5_count"],
        "recorded_rig_binding_count": audit["recorded_rig_binding_count"],
        "calibration_variant_selection_closed_count": audit[
            "calibration_variant_selection_closed_count"
        ],
        "selected_calibration_variant": "offline",
        "verified_coordinate_transform_count": 0,
        "new_source_complete_8_of_8_count": 0,
        "new_final_outcome_assigned_count": 0,
        "newly_eligible_scene_count": 0,
        "historical_source_complete_8_of_8_count": 3,
        "eligible_scene_count": 1,
        "target_scene_count": 60,
        "total_scene_shortfall": 59,
        "annotation_start_allowed": False,
        "annotation_started": False,
        "synthetic_required_field_fill_count": 0,
        "actual_vehicle_validation_deferred_to_m21": True,
        "claim_scope": CLAIM_SCOPE,
    }
    work_orders = {
        "work_order_version": "guardsynth-m16-curator-work-orders-v0.1",
        "classified_event_count": 98,
        "completed_work": {
            "human_video_observation": 60,
            "temporal_closure": 98,
            "calibration_5_of_5": 98,
            "recorded_rig_binding": 98,
            "calibration_variant_selection": 98,
        },
        "remaining_work": audit["remaining_field_event_counts"],
        "next_execution_order": [
            "BIND_MODEL_T0_AND_NUMERICALLY_VERIFY_OFFLINE_COORDINATE_TRANSFORM",
            "ACQUIRE_SOURCE_LINKED_LANE_OR_ZONE_GEOMETRY_AND_ASSOCIATE_TRACKS",
            "BIND_JURISDICTION_MATCHED_VERSIONED_AUTHORITY",
            "BUILD_SOURCE_COMPLETE_LIFECYCLE_WITNESSES_AND_ASSIGN_OUTCOMES",
            "RECOMPUTE_8_OF_8_ELIGIBILITY_AND_60_SLOT_QUOTAS",
        ],
        "human_observation_is_not_source_substitute": True,
        "annotation_start_allowed": False,
        "claim_scope": CLAIM_SCOPE,
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
            "M16_REMAINING_SOURCE_FIELDS_NOT_CLOSED",
            "M16_SLICE_AND_OUTCOME_QUOTAS_NOT_MET",
        ],
        "synthetic_scene_fill_performed": False,
        "actual_vehicle_validation_deferred_to_m21": True,
        "claim_scope": "M16_PILOT_PREFLIGHT_NOT_EXPERT_RESULT_OR_VEHICLE_SAFETY",
    }
    revision, workspace_state = _git_revision()
    source_hashes = {
        "nvidia_ncore_data_provider": source_sha,
        "source_review_precheck": _sha256(PRECHECK),
        "human_video_observation_review": _sha256(REVIEW_EXPORT),
        "human_video_observation_summary": _sha256(REVIEW_SUMMARY),
        "prior_m16_result": _sha256(PRIOR_RESULT),
        "primary_sensor_manifest": _sha256(PRIMARY_SENSOR_MANIFEST),
        "primary_calibration_manifest": _sha256(PRIMARY_CALIBRATION_MANIFEST),
        "reserve_sensor_manifest": _sha256(RESERVE_SENSOR_MANIFEST),
        "reserve_calibration_manifest": _sha256(RESERVE_CALIBRATION_MANIFEST),
        "attrition_reserve_evidence_audit": _sha256(ATTRITION_AUDIT),
        "pipeline": _sha256(Path(__file__).resolve()),
        "audit_module": _sha256(
            ROOT / "projects/04-guardsynth-coc/src/guard_synth/m16_post_review_source_closure.py"
        ),
    }
    manifest = {
        **result,
        "input_class": "NVIDIA_LICENSE_RESTRICTED_INTERNAL_DERIVATIVES",
        "code_revision": revision,
        "workspace_state": workspace_state,
        "source_hashes": source_hashes,
        "nvidia_ncore_commit_sha": ncore_commit_sha,
        "restricted_identifier_leakage_to_public_count": 0,
        "raw_video_copied": False,
        "network_source_snapshot_copied_into_artifact": False,
    }

    restricted_output_dir.mkdir(parents=True)
    restricted_output_dir.chmod(0o700)
    for name, payload in (
        ("UPSTREAM_CALIBRATION_RULE_EVIDENCE.json", variant_rule),
        ("POST_REVIEW_SOURCE_CLOSURE_AUDIT.json", audit),
        ("CURATOR_WORK_ORDERS.json", work_orders),
        ("PILOT_PREFLIGHT.json", preflight),
        ("RESULT.json", result),
        ("RUN_MANIFEST.json", manifest),
    ):
        _write_json(restricted_output_dir / name, payload, restricted=True)
    report = (
        "# M16 post-review source closure 재감사\n\n"
        f"- 상태: **{result['status']}**\n"
        "- human video observation: **60/60 완료·무결성 검증**\n"
        "- classified events / materialized unique clips: **98 / 81**\n"
        "- temporal / calibration 5-of-5 / recorded rig: **98 / 98 / 98**\n"
        "- NVIDIA 공식 offline variant 선택 근거: **98/98 연결**\n"
        "- verified coordinate transform: **0/98** (장면별 model-t0와 수치 폐쇄 필요)\n"
        "- 신규 8/8 / final outcome / eligible: **0 / 0 / 0**\n"
        "- 전체 eligible: **1/60**, shortfall **59**\n"
        "- formal expert annotation 시작: **금지**\n\n"
        "NVIDIA NCore의 고정 커밋은 PhysicalAI 변환에서 offline egomotion과 offline "
        "sensor extrinsics를 요구하며 non-offline 변형은 지원하지 않는다고 명시한다. 이에 따라 "
        "이전의 variant-selection 미결정은 해소했다. 다만 이를 장면별 좌표변환 완료로 과대 "
        "해석하지 않았다. model-t0 binding과 역행렬 수치 폐쇄, source-linked lane/zone geometry, "
        "관할에 맞는 versioned authority, lifecycle witness가 각각 98건 남아 있다. 사람의 영상 "
        "답변은 관찰 근거로 연결했지만 이 source 필드들을 대신하지 않는다.\n"
    )
    report_path = restricted_output_dir / "REPORT_KO.md"
    report_path.write_text(report, encoding="utf-8")
    report_path.chmod(0o600)

    if public_output_dir is not None:
        public_audit = public_post_review_source_closure_summary(audit)
        public_variant = dict(variant_rule)
        public_manifest = {
            "experiment_id": EXPERIMENT_ID,
            "run_id": run_id,
            "run_date": result["run_date"],
            "input_class": "PUBLIC_DEIDENTIFIED_AGGREGATE",
            "nvidia_ncore_commit_sha": ncore_commit_sha,
            "restricted_identifier_leakage_count": 0,
            "claim_scope": CLAIM_SCOPE,
        }
        for payload in (result, public_audit, public_variant, work_orders, preflight, public_manifest):
            assert_public_export_safe(payload)
        assert_public_export_safe(report)
        public_output_dir.mkdir(parents=True)
        for name, payload in (
            ("UPSTREAM_CALIBRATION_RULE_EVIDENCE.json", public_variant),
            ("POST_REVIEW_SOURCE_CLOSURE_AUDIT.json", public_audit),
            ("CURATOR_WORK_ORDERS.json", work_orders),
            ("PILOT_PREFLIGHT.json", preflight),
            ("RESULT.json", result),
            ("RUN_MANIFEST.json", public_manifest),
        ):
            _write_json(public_output_dir / name, payload, restricted=False)
        public_report = public_output_dir / "REPORT_KO.md"
        public_report.write_text(report, encoding="utf-8")
        public_report.chmod(0o644)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--restricted-output-dir", type=Path, required=True)
    parser.add_argument("--public-output-dir", type=Path)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--ncore-source", type=Path, required=True)
    parser.add_argument("--ncore-commit-sha", required=True)
    parser.add_argument("--ncore-source-url", required=True)
    args = parser.parse_args()
    result = execute(
        restricted_output_dir=args.restricted_output_dir,
        public_output_dir=args.public_output_dir,
        run_id=args.run_id,
        ncore_source_path=args.ncore_source,
        ncore_commit_sha=args.ncore_commit_sha,
        ncore_source_url=args.ncore_source_url,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
