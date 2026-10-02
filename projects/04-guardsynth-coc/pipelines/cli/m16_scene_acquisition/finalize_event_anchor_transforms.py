#!/usr/bin/env python3
"""Close M16 review-event transforms from materialized offline egomotion."""

from __future__ import annotations

import argparse
from datetime import date
import hashlib
import json
from math import isfinite
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

from guard_synth.m16_event_anchor_transform import (
    EVENT_ANCHOR_POLICY_VERSION,
    apply_verified_event_anchor_transforms,
    public_event_anchor_transform_summary,
    verify_event_anchor_transform,
)
from guard_synth.m16_scene_acquisition import assert_public_export_safe


EXPERIMENT_ID = "GUARDSYNTH-M16-SCENE-ACQUISITION-001"
PRIOR_ROOT = ROOT / (
    "artifacts/projects/guardsynth-coc/restricted/"
    "guardsynth-m16-scene-acquisition-001/"
    "m16-post-review-source-closure-2026-09-05-v1"
)
ACQUISITION_ROOT = ROOT / (
    "artifacts/projects/guardsynth-coc/restricted/"
    "guardsynth-m16-scene-acquisition-001/"
    "m16-source-acquisition-2026-08-14-v18"
)
PRIMARY_ROOT = ROOT / "data/restricted/nvidia_physicalai/internal-derived/m16-shortlist-v1"
RESERVE_ROOT = ROOT / "data/restricted/nvidia_physicalai/internal-derived/m16-reserve-v1"
PRIOR_AUDIT = PRIOR_ROOT / "POST_REVIEW_SOURCE_CLOSURE_AUDIT.json"
PRIOR_RESULT = PRIOR_ROOT / "RESULT.json"
PRIOR_MANIFEST = PRIOR_ROOT / "RUN_MANIFEST.json"
RESERVE_COHORT = ACQUISITION_ROOT / "ATTRITION_RESERVE_COHORT.json"
PRIMARY_SENSOR_MANIFEST = PRIMARY_ROOT / "MANIFEST.json"
PRIMARY_CALIBRATION_MANIFEST = PRIMARY_ROOT / "CALIBRATION_MANIFEST.json"
RESERVE_SENSOR_MANIFEST = RESERVE_ROOT / "MANIFEST.json"
RESERVE_CALIBRATION_MANIFEST = RESERVE_ROOT / "CALIBRATION_MANIFEST.json"
CLAIM_SCOPE = (
    "M16_EVENT_ANCHOR_TRANSFORM_CLOSURE_NOT_GEOMETRIC_ASSOCIATION_"
    "EXPERT_EFFECT_OR_VEHICLE_SAFETY"
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


def _validate_member(root: Path, record: dict[str, Any]) -> Path:
    relative = Path(record["relative_path"])
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError("MATERIALIZED_MEMBER_PATH_UNSAFE")
    path = root / relative
    if (
        not path.is_file()
        or path.stat().st_size != record.get("bytes")
        or _sha256(path) != record.get("sha256")
    ):
        raise ValueError("MATERIALIZED_MEMBER_INTEGRITY_FAILURE")
    return path


def _feature_assets(
    feature: str,
    manifests: tuple[tuple[Path, dict[str, Any]], ...],
) -> dict[str, tuple[Path, dict[str, Any]]]:
    assets: dict[str, tuple[Path, dict[str, Any]]] = {}
    for root, manifest in manifests:
        for record in manifest["records"]:
            if record.get("feature") != feature:
                continue
            digest = record["candidate_digest"]
            if digest in assets:
                raise ValueError(f"DUPLICATE_MATERIALIZED_FEATURE_ASSET:{feature}")
            assets[digest] = (root, record)
    return assets


def _validate_offline_extrinsics(path: Path) -> int:
    import pyarrow.parquet as parquet

    rows = parquet.read_table(path).to_pylist()
    required = ("qx", "qy", "qz", "qw", "x", "y", "z", "sensor_name")
    if not rows or any(any(key not in row for key in required) for row in rows):
        raise ValueError("OFFLINE_SENSOR_EXTRINSICS_SCHEMA_INVALID")
    names: set[str] = set()
    for row in rows:
        values = [float(row[key]) for key in ("qx", "qy", "qz", "qw", "x", "y", "z")]
        if not all(isfinite(value) for value in values):
            raise ValueError("OFFLINE_SENSOR_EXTRINSICS_NONFINITE_VALUE")
        quaternion_norm = sum(value * value for value in values[:4]) ** 0.5
        if abs(quaternion_norm - 1.0) > 1e-5:
            raise ValueError("OFFLINE_SENSOR_EXTRINSICS_QUATERNION_NOT_NORMALIZED")
        name = row["sensor_name"]
        if not isinstance(name, str) or not name or name in names:
            raise ValueError("OFFLINE_SENSOR_EXTRINSICS_SENSOR_NAME_INVALID")
        names.add(name)
    return len(rows)


def _event_asset_bindings() -> tuple[
    dict[str, tuple[str, int]],
    dict[str, tuple[Path, dict[str, Any]]],
    dict[str, tuple[Path, dict[str, Any]]],
]:
    primary_sensor = _load(PRIMARY_SENSOR_MANIFEST)
    reserve_sensor = _load(RESERVE_SENSOR_MANIFEST)
    primary_calibration = _load(PRIMARY_CALIBRATION_MANIFEST)
    reserve_calibration = _load(RESERVE_CALIBRATION_MANIFEST)
    sensor_assets = _feature_assets(
        "egomotion.offline",
        ((PRIMARY_ROOT, primary_sensor), (RESERVE_ROOT, reserve_sensor)),
    )
    extrinsics_assets = _feature_assets(
        "sensor_extrinsics.offline",
        ((PRIMARY_ROOT, primary_calibration), (RESERVE_ROOT, reserve_calibration)),
    )
    if len(sensor_assets) != 81 or set(sensor_assets) != set(extrinsics_assets):
        raise ValueError("OFFLINE_TRANSFORM_ASSET_SET_INVALID")

    event_bindings = {
        digest: (digest, int(record["event_timestamp_us"]))
        for digest, (_, record) in sensor_assets.items()
        if digest in {
            item["candidate_digest"]
            for item in _load(PRIOR_AUDIT)["records"]
            if item.get("cohort_role") == "PRIMARY"
        }
    }
    reserve_records = _load(RESERVE_COHORT)["records"]
    for record in reserve_records:
        digest = record["candidate_digest"]
        if digest in event_bindings:
            raise ValueError("PRIMARY_RESERVE_EVENT_OVERLAP")
        event_bindings[digest] = (
            record["asset_candidate_digest"],
            int(record["event_timestamp_us"]),
        )
    if len(event_bindings) != 98:
        raise ValueError("M16_EVENT_ASSET_BINDING_COUNT_INVALID")
    return event_bindings, sensor_assets, extrinsics_assets


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
) -> dict[str, Any]:
    if restricted_output_dir.exists() or (
        public_output_dir is not None and public_output_dir.exists()
    ):
        raise FileExistsError("refusing to overwrite M16 event-anchor transform run")
    required = (
        PRIOR_AUDIT,
        PRIOR_RESULT,
        PRIOR_MANIFEST,
        RESERVE_COHORT,
        PRIMARY_SENSOR_MANIFEST,
        PRIMARY_CALIBRATION_MANIFEST,
        RESERVE_SENSOR_MANIFEST,
        RESERVE_CALIBRATION_MANIFEST,
    )
    if any(not path.is_file() for path in required):
        raise FileNotFoundError("M16_EVENT_ANCHOR_TRANSFORM_INPUT_MISSING")

    import pyarrow.parquet as parquet

    prior_audit = _load(PRIOR_AUDIT)
    prior_result = _load(PRIOR_RESULT)
    if (
        prior_result.get("verified_coordinate_transform_count") != 0
        or prior_result.get("eligible_scene_count") != 1
        or prior_audit.get("classified_event_count") != 98
    ):
        raise ValueError("PRIOR_POST_REVIEW_CLOSURE_BASELINE_CHANGED")
    event_bindings, sensor_assets, extrinsics_assets = _event_asset_bindings()
    if set(event_bindings) != {
        item["candidate_digest"] for item in prior_audit["records"]
    }:
        raise ValueError("POST_REVIEW_EVENT_ASSET_SET_MISMATCH")

    validated_extrinsics: dict[str, int] = {}
    transforms: dict[str, dict[str, Any]] = {}
    for candidate_digest in sorted(event_bindings):
        asset_digest, event_timestamp_us = event_bindings[candidate_digest]
        sensor_root, sensor_record = sensor_assets[asset_digest]
        extrinsics_root, extrinsics_record = extrinsics_assets[asset_digest]
        sensor_path = _validate_member(sensor_root, sensor_record)
        extrinsics_path = _validate_member(extrinsics_root, extrinsics_record)
        if asset_digest not in validated_extrinsics:
            validated_extrinsics[asset_digest] = _validate_offline_extrinsics(
                extrinsics_path
            )
        rows = parquet.read_table(sensor_path).to_pylist()
        transform = verify_event_anchor_transform(
            egomotion_rows=rows,
            event_timestamp_us=event_timestamp_us,
            egomotion_sha256=sensor_record["sha256"],
            offline_extrinsics_sha256=extrinsics_record["sha256"],
        )
        transform["asset_candidate_digest"] = asset_digest
        transforms[candidate_digest] = transform

    audit = apply_verified_event_anchor_transforms(prior_audit, transforms)
    audit.update({
        "event_anchor_binding_count": 98,
        "offline_egomotion_event_coverage_count": 98,
        "offline_extrinsics_asset_validation_count": len(validated_extrinsics),
        "offline_extrinsics_row_validation_count": sum(validated_extrinsics.values()),
        "t0_policy_version": EVENT_ANCHOR_POLICY_VERSION,
        "event_to_t0_max_identity_error": max(
            item["event_to_t0_identity_max_abs_error"] for item in transforms.values()
        ),
        "inverse_closure_max_abs_error": max(
            item["inverse_closure_max_abs_error"] for item in transforms.values()
        ),
        "claim_scope": CLAIM_SCOPE,
    })
    result = {
        "experiment_id": EXPERIMENT_ID,
        "run_id": run_id,
        "run_date": date.today().isoformat(),
        "status": "M16_SOURCE_CLOSURE_PARTIAL_EVENT_ANCHOR_TRANSFORM_RESOLVED",
        "classified_event_count": 98,
        "human_observation_completed_count": 60,
        "materialized_unique_clip_count": 81,
        "calibration_variant_selection_closed_count": 98,
        "event_anchor_binding_count": 98,
        "verified_coordinate_transform_count": 98,
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
    policy = {
        "policy_version": EVENT_ANCHOR_POLICY_VERSION,
        "scope": "M16_60_SCENE_EXPERT_FORMAL_PILOT_SOURCE_CURATION",
        "binding": "MODEL_T0_EQUALS_REVIEW_EVENT_TIMESTAMP",
        "rationale": (
            "Each M16 review item is an event-anchored curation scene; it is not a replay "
            "of an unrelated upstream Alpamayo inference manifest."
        ),
        "source_frame": "dataset_rig_at_event",
        "target_frame": "ego_at_model_t0",
        "event_to_t0_expected_transform": "IDENTITY",
        "offline_pose_interpolation_required": True,
        "reuse_unrelated_inference_t0_prohibited": True,
        "does_not_close": [
            "lane_or_zone_geometry",
            "actor_or_control_association",
            "jurisdiction_authority",
            "outcome_lifecycle",
        ],
        "claim_scope": CLAIM_SCOPE,
    }
    work_orders = {
        "work_order_version": "guardsynth-m16-curator-work-orders-v0.2",
        "classified_event_count": 98,
        "completed_work": {
            "human_video_observation": 60,
            "temporal_closure": 98,
            "calibration_5_of_5": 98,
            "recorded_rig_binding": 98,
            "calibration_variant_selection": 98,
            "event_anchor_binding": 98,
            "verified_coordinate_transform": 98,
        },
        "remaining_work": audit["remaining_field_event_counts"],
        "next_execution_order": [
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
            "M16_GEOMETRY_AUTHORITY_AND_LIFECYCLE_FIELDS_NOT_CLOSED",
            "M16_SLICE_AND_OUTCOME_QUOTAS_NOT_MET",
        ],
        "synthetic_scene_fill_performed": False,
        "actual_vehicle_validation_deferred_to_m21": True,
        "claim_scope": "M16_PILOT_PREFLIGHT_NOT_EXPERT_RESULT_OR_VEHICLE_SAFETY",
    }
    revision, workspace_state = _git_revision()
    manifest = {
        **result,
        "input_class": "NVIDIA_LICENSE_RESTRICTED_INTERNAL_DERIVATIVES",
        "code_revision": revision,
        "workspace_state": workspace_state,
        "source_hashes": {
            "prior_post_review_audit": _sha256(PRIOR_AUDIT),
            "prior_post_review_result": _sha256(PRIOR_RESULT),
            "prior_post_review_manifest": _sha256(PRIOR_MANIFEST),
            "attrition_reserve_cohort": _sha256(RESERVE_COHORT),
            "primary_sensor_manifest": _sha256(PRIMARY_SENSOR_MANIFEST),
            "primary_calibration_manifest": _sha256(PRIMARY_CALIBRATION_MANIFEST),
            "reserve_sensor_manifest": _sha256(RESERVE_SENSOR_MANIFEST),
            "reserve_calibration_manifest": _sha256(RESERVE_CALIBRATION_MANIFEST),
            "pipeline": _sha256(Path(__file__).resolve()),
            "transform_module": _sha256(
                ROOT / "projects/04-guardsynth-coc/src/guard_synth/m16_event_anchor_transform.py"
            ),
        },
        "restricted_identifier_leakage_to_public_count": 0,
        "raw_video_copied": False,
    }

    restricted_output_dir.mkdir(parents=True)
    restricted_output_dir.chmod(0o700)
    for name, payload in (
        ("EVENT_ANCHOR_POLICY.json", policy),
        ("EVENT_ANCHOR_TRANSFORM_AUDIT.json", audit),
        ("CURATOR_WORK_ORDERS.json", work_orders),
        ("PILOT_PREFLIGHT.json", preflight),
        ("RESULT.json", result),
        ("RUN_MANIFEST.json", manifest),
    ):
        _write_json(restricted_output_dir / name, payload, restricted=True)

    report = (
        "# M16 event-anchor coordinate transform 폐쇄\n\n"
        f"- 상태: **{result['status']}**\n"
        "- M16 review-event t0 binding: **98/98**\n"
        "- offline egomotion event coverage: **98/98**\n"
        "- offline extrinsics validated assets: **81/81**\n"
        "- verified coordinate transform: **98/98**\n"
        "- 신규 8/8 / final outcome / eligible: **0 / 0 / 0**\n"
        "- 전체 eligible: **1/60**, shortfall **59**\n"
        "- formal expert annotation 시작: **금지**\n\n"
        "M16 검토 항목은 각 event timestamp에 고정된 curation scene이므로 그 시각을 이 "
        "pilot의 model-t0로 명시했다. 다른 Alpamayo 추론 run의 t0는 재사용하지 않았다. "
        "선택된 offline egomotion에서 event pose를 보간하고 event→t0 행렬과 역행렬을 수치 "
        "검증했다. 같은 시각·같은 ego frame의 변환은 identity인 것이 정상이다. 이 결과는 "
        "lane/zone geometry, actor/control association, 관할 authority 또는 outcome lifecycle을 "
        "닫지 않으며 차량 안전성 주장도 아니다.\n"
    )
    report_path = restricted_output_dir / "REPORT_KO.md"
    report_path.write_text(report, encoding="utf-8")
    report_path.chmod(0o600)

    if public_output_dir is not None:
        public_audit = public_event_anchor_transform_summary(audit)
        public_manifest = {
            "experiment_id": EXPERIMENT_ID,
            "run_id": run_id,
            "run_date": result["run_date"],
            "input_class": "PUBLIC_DEIDENTIFIED_AGGREGATE",
            "restricted_identifier_leakage_count": 0,
            "claim_scope": CLAIM_SCOPE,
        }
        for payload in (result, policy, public_audit, work_orders, preflight, public_manifest):
            assert_public_export_safe(payload)
        assert_public_export_safe(report)
        public_output_dir.mkdir(parents=True)
        for name, payload in (
            ("EVENT_ANCHOR_POLICY.json", policy),
            ("EVENT_ANCHOR_TRANSFORM_AUDIT.json", public_audit),
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
    args = parser.parse_args()
    result = execute(
        restricted_output_dir=args.restricted_output_dir,
        public_output_dir=args.public_output_dir,
        run_id=args.run_id,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
