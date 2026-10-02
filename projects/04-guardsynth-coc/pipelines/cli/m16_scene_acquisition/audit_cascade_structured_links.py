#!/usr/bin/env python3
"""Audit M16 CASCADE relation/containment sources before any curator UI."""

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
SRC = ROOT / "projects/04-guardsynth-coc/src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
PLATFORM_SRC = ROOT / "platforms/eblc-bcv/src"
if str(PLATFORM_SRC) not in sys.path:
    sys.path.insert(0, str(PLATFORM_SRC))

from guard_synth.m16_cascade_link_audit import (
    apply_cascade_link_audit,
    audit_cascade_event_links,
    public_cascade_link_audit_summary,
)
from guard_synth.m16_scene_acquisition import assert_public_export_safe


EXPERIMENT_ID = "GUARDSYNTH-M16-SCENE-ACQUISITION-001"
PRIOR_ROOT = ROOT / (
    "artifacts/projects/guardsynth-coc/restricted/"
    "guardsynth-m16-scene-acquisition-001/"
    "m16-event-anchor-transform-2026-09-05-v1"
)
ACQUISITION_ROOT = ROOT / (
    "artifacts/projects/guardsynth-coc/restricted/"
    "guardsynth-m16-scene-acquisition-001/"
    "m16-source-acquisition-2026-08-14-v18"
)
CASCADE_ROOT = ROOT / "data/restricted/nvidia_cascade"
CASCADE_DATA = CASCADE_ROOT / "data"
CASCADE_README = CASCADE_ROOT / "README.md"
PRIOR_AUDIT = PRIOR_ROOT / "EVENT_ANCHOR_TRANSFORM_AUDIT.json"
PRIOR_RESULT = PRIOR_ROOT / "RESULT.json"
PRIOR_MANIFEST = PRIOR_ROOT / "RUN_MANIFEST.json"
PRIMARY_COHORT = ACQUISITION_ROOT / "SENSOR_MATERIALIZATION_SHORTLIST.json"
RESERVE_COHORT = ACQUISITION_ROOT / "ATTRITION_RESERVE_COHORT.json"
CLAIM_SCOPE = (
    "M16_CASCADE_STRUCTURED_LINK_SOURCE_AUDIT_NOT_UNANNOTATED_GEOMETRY_"
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


def _cascade_by_video_reference() -> dict[str, Path]:
    result: dict[str, Path] = {}
    for path in CASCADE_DATA.rglob("*.json"):
        parts = path.stem.split("__", 1)
        if len(parts) != 2 or not parts[1]:
            raise ValueError("CASCADE_ANNOTATION_FILENAME_INVALID")
        reference = parts[1]
        if reference in result:
            raise ValueError("CASCADE_VIDEO_REFERENCE_DUPLICATE")
        result[reference] = path
    return result


def _event_records() -> list[dict[str, Any]]:
    primary = _load(PRIMARY_COHORT)["records"]
    reserve = _load(RESERVE_COHORT)["records"]
    records = [
        {
            "candidate_digest": item["candidate_digest"],
            "annotation_sha256": item["annotation_sha256"],
            "video_reference": item["clip_id"],
            "event_timestamp_us": int(item["event_timestamp_us"]),
            "slice": item["shortlist_slice"],
        }
        for item in primary
    ] + [
        {
            "candidate_digest": item["candidate_digest"],
            "annotation_sha256": item["annotation_sha256"],
            "video_reference": item["clip_id"],
            "event_timestamp_us": int(item["event_timestamp_us"]),
            "slice": item["reserve_slice"],
        }
        for item in reserve
    ]
    digests = [item["candidate_digest"] for item in records]
    if len(records) != 98 or len(set(digests)) != 98:
        raise ValueError("M16_CASCADE_EVENT_SET_INVALID")
    return records


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
        raise FileExistsError("refusing to overwrite M16 CASCADE structured-link run")
    required = (
        PRIOR_AUDIT,
        PRIOR_RESULT,
        PRIOR_MANIFEST,
        PRIMARY_COHORT,
        RESERVE_COHORT,
        CASCADE_README,
    )
    if any(not path.is_file() for path in required) or not CASCADE_DATA.is_dir():
        raise FileNotFoundError("M16_CASCADE_STRUCTURED_LINK_INPUT_MISSING")

    prior_audit = _load(PRIOR_AUDIT)
    prior_result = _load(PRIOR_RESULT)
    if (
        prior_result.get("verified_coordinate_transform_count") != 98
        or prior_result.get("eligible_scene_count") != 1
        or prior_audit.get("classified_event_count") != 98
    ):
        raise ValueError("PRIOR_EVENT_ANCHOR_BASELINE_CHANGED")
    cascade_sources = _cascade_by_video_reference()
    records = _event_records()
    if {item["candidate_digest"] for item in records} != {
        item["candidate_digest"] for item in prior_audit["records"]
    }:
        raise ValueError("CASCADE_AND_EVENT_ANCHOR_EVENT_SET_MISMATCH")

    event_audits: dict[str, dict[str, Any]] = {}
    unique_annotation_hashes: set[str] = set()
    for record in records:
        source = cascade_sources.get(record["video_reference"])
        if source is None or _sha256(source) != record["annotation_sha256"]:
            raise ValueError("CASCADE_ANNOTATION_HASH_BINDING_INVALID")
        payload = _load(source)
        if (
            payload.get("status") != "approved"
            or payload.get("schema_version") != "2.0.0"
            or payload.get("provenance", {}).get("generated_by") != "human"
            or payload.get("video", {}).get("clip_id") != record["video_reference"]
        ):
            raise ValueError("CASCADE_APPROVED_SOURCE_CONTRACT_INVALID")
        event_audits[record["candidate_digest"]] = audit_cascade_event_links(
            annotation=payload["annotation"],
            event_timestamp_us=record["event_timestamp_us"],
            scene_slice=record["slice"],
            annotation_sha256=record["annotation_sha256"],
        )
        unique_annotation_hashes.add(record["annotation_sha256"])

    audit = apply_cascade_link_audit(prior_audit, event_audits)
    audit.update({
        "cascade_schema_version": "2.0.0",
        "cascade_approved_human_annotation_event_count": 98,
        "cascade_unique_annotation_count": len(unique_annotation_hashes),
        "curator_review_screen_generated": False,
        "curator_review_screen_reason": "NO_HUMAN_ANSWER_CAN_REPLACE_MISSING_SOURCE_GEOMETRY",
        "claim_scope": CLAIM_SCOPE,
    })
    remaining = audit["remaining_field_event_counts"]
    result = {
        "experiment_id": EXPERIMENT_ID,
        "run_id": run_id,
        "run_date": date.today().isoformat(),
        "status": "M16_SOURCE_CLOSURE_PARTIAL_STRUCTURED_RELATION_AUDITED",
        "classified_event_count": 98,
        "cascade_annotation_hash_verified_count": 98,
        "cascade_unique_annotation_count": len(unique_annotation_hashes),
        "relevant_actor_or_control_state_closed_count": audit[
            "relevant_actor_or_control_state_closed_count"
        ],
        "target_zone_or_lane_association_closed_count": audit[
            "target_zone_or_lane_association_closed_count"
        ],
        "verified_coordinate_transform_count": 98,
        "new_source_complete_8_of_8_count": 0,
        "new_final_outcome_assigned_count": 0,
        "newly_eligible_scene_count": 0,
        "historical_source_complete_8_of_8_count": 3,
        "eligible_scene_count": 1,
        "target_scene_count": 60,
        "total_scene_shortfall": 59,
        "curator_review_screen_generated": False,
        "annotation_start_allowed": False,
        "annotation_started": False,
        "synthetic_required_field_fill_count": 0,
        "actual_vehicle_validation_deferred_to_m21": True,
        "claim_scope": CLAIM_SCOPE,
    }
    acquisition = {
        "manifest_version": "guardsynth-m16-source-geometry-acquisition-v0.1",
        "classified_event_count": 98,
        "source_link_automatic_closure": {
            "relevant_actor_or_control_state": audit[
                "relevant_actor_or_control_state_closed_count"
            ],
            "target_zone_or_lane_association": audit[
                "target_zone_or_lane_association_closed_count"
            ],
        },
        "remaining_event_counts": remaining,
        "required_source_by_slice": {
            "PEDESTRIAN_CYCLIST_YIELD": [
                "timestamped_actor_track_to_crossing_or_ego-lane_geometry",
                "crosswalk_or_conflict-zone_polygon_when_applicable",
            ],
            "STOP_SIGNALS": [
                "control-state-to-applicable-lane association",
                "stop-line or stopping-zone geometry",
            ],
            "FOLLOWING_CUT_IN": [
                "timestamped target-track-to-lane assignment",
                "lane boundaries or centerline and longitudinal conflict geometry",
            ],
        },
        "minimum_source_contract": [
            "content hash and version",
            "coordinate frame and unit",
            "event timestamp coverage",
            "entity/control identifier binding",
            "lane/zone geometry or explicit containment relation",
        ],
        "human_video_observation_is_source_geometry": False,
        "empty_or_unsourced_review_prohibited": True,
        "curator_review_screen_generation_allowed": False,
        "screen_generation_gate": (
            "NEW_SOURCE_GEOMETRY_MUST_BE_BOUND_BEFORE_PRESENTING_A_CURATOR_DECISION"
        ),
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
            "M16_SOURCE_GEOMETRY_AUTHORITY_AND_LIFECYCLE_NOT_CLOSED",
            "M16_SLICE_AND_OUTCOME_QUOTAS_NOT_MET",
        ],
        "synthetic_scene_fill_performed": False,
        "actual_vehicle_validation_deferred_to_m21": True,
        "claim_scope": "M16_PILOT_PREFLIGHT_NOT_EXPERT_RESULT_OR_VEHICLE_SAFETY",
    }
    schema_evidence = {
        "source": "NVIDIA-CASCADE-local-licensed-snapshot",
        "schema_version": "2.0.0",
        "readme_sha256": _sha256(CASCADE_README),
        "audited_semantics": [
            "because_of",
            "action_target",
            "containment",
            "optional_environment_and_containment_layers",
        ],
        "interpretation": (
            "Structured links are source evidence only where present and temporally active; "
            "optional missing layers are not inferred."
        ),
        "claim_scope": CLAIM_SCOPE,
    }
    revision, workspace_state = _git_revision()
    manifest = {
        **result,
        "input_class": "NVIDIA_LICENSE_RESTRICTED_INTERNAL_DERIVATIVES",
        "code_revision": revision,
        "workspace_state": workspace_state,
        "source_hashes": {
            "prior_event_anchor_audit": _sha256(PRIOR_AUDIT),
            "prior_event_anchor_result": _sha256(PRIOR_RESULT),
            "prior_event_anchor_manifest": _sha256(PRIOR_MANIFEST),
            "primary_candidate_cohort": _sha256(PRIMARY_COHORT),
            "reserve_candidate_cohort": _sha256(RESERVE_COHORT),
            "cascade_readme": _sha256(CASCADE_README),
            "pipeline": _sha256(Path(__file__).resolve()),
            "audit_module": _sha256(
                ROOT / "projects/04-guardsynth-coc/src/guard_synth/m16_cascade_link_audit.py"
            ),
        },
        "all_event_annotation_hashes_verified": True,
        "restricted_identifier_leakage_to_public_count": 0,
        "raw_video_copied": False,
    }

    restricted_output_dir.mkdir(parents=True)
    restricted_output_dir.chmod(0o700)
    for name, payload in (
        ("CASCADE_SCHEMA_EVIDENCE.json", schema_evidence),
        ("CASCADE_STRUCTURED_LINK_AUDIT.json", audit),
        ("SOURCE_GEOMETRY_ACQUISITION_MANIFEST.json", acquisition),
        ("PILOT_PREFLIGHT.json", preflight),
        ("RESULT.json", result),
        ("RUN_MANIFEST.json", manifest),
    ):
        _write_json(restricted_output_dir / name, payload, restricted=True)
    status_counts = Counter(
        item["relevant_actor_or_control_state_status"]
        for item in event_audits.values()
    )
    report = (
        "# M16 CASCADE structured-link source 감사\n\n"
        f"- 상태: **{result['status']}**\n"
        "- approved CASCADE annotation hash binding: **98/98**\n"
        f"- distinct annotation sources: **{len(unique_annotation_hashes)}**\n"
        "- relevant actor/control source set 폐쇄: "
        f"**{result['relevant_actor_or_control_state_closed_count']}/98**\n"
        "- target lane/zone containment 폐쇄: "
        f"**{result['target_zone_or_lane_association_closed_count']}/98**\n"
        "- 신규 8/8 / final outcome / eligible: **0 / 0 / 0**\n"
        "- 전체 eligible: **1/60**, shortfall **59**\n"
        "- 새 curator 설문 화면: **생성하지 않음**\n\n"
        "CASCADE schema의 because_of/action_target과 시간 활성 상태를 사용해 근거가 있는 "
        "actor/control SET만 닫았다. optional containment에서 ego와 모든 active target이 같은 "
        "environment/lane으로 연결된 경우에만 lane relation을 닫았다. 나머지 영상 관찰을 "
        "geometry로 해석하지 않았다. 따라서 새 source 없이 사람이 답할 수 없는 빈 curator "
        "설문은 만들지 않았고, 필요한 source 계약을 acquisition manifest에 기록했다.\n\n"
        f"Structured-link status counts: `{dict(sorted(status_counts.items()))}`\n"
    )
    report_path = restricted_output_dir / "REPORT_KO.md"
    report_path.write_text(report, encoding="utf-8")
    report_path.chmod(0o600)

    if public_output_dir is not None:
        public_audit = public_cascade_link_audit_summary(audit)
        public_manifest = {
            "experiment_id": EXPERIMENT_ID,
            "run_id": run_id,
            "run_date": result["run_date"],
            "input_class": "PUBLIC_DEIDENTIFIED_AGGREGATE",
            "restricted_identifier_leakage_count": 0,
            "claim_scope": CLAIM_SCOPE,
        }
        for payload in (
            result,
            schema_evidence,
            public_audit,
            acquisition,
            preflight,
            public_manifest,
        ):
            assert_public_export_safe(payload)
        assert_public_export_safe(report)
        public_output_dir.mkdir(parents=True)
        for name, payload in (
            ("CASCADE_SCHEMA_EVIDENCE.json", schema_evidence),
            ("CASCADE_STRUCTURED_LINK_AUDIT.json", public_audit),
            ("SOURCE_GEOMETRY_ACQUISITION_MANIFEST.json", acquisition),
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
