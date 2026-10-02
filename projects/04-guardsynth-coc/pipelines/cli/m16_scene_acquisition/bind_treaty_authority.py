#!/usr/bin/env python3
"""Bind the audited UN-treaty research baseline to the current M16 frontier."""

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
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from guard_synth.m16_treaty_authority import (
    CATALOG_PATH,
    bind_treaty_authority,
    load_treaty_authority_catalog,
)


EXPERIMENT_ID = "GUARDSYNTH-M16-SCENE-ACQUISITION-001"
CLAIM_SCOPE = (
    "INTERNATIONAL_TREATY_RESEARCH_BASELINE_NOT_DOMESTIC_LEGAL_"
    "COMPLIANCE_LEGAL_ADVICE_OR_VEHICLE_SAFETY"
)


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


def _revision() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    ).stdout.strip()


def execute(
    *,
    frontier_run_dir: Path,
    output_dir: Path,
    run_id: str,
) -> dict[str, Any]:
    if output_dir.exists():
        raise FileExistsError("refusing to overwrite M16 treaty authority run")
    audit_path = frontier_run_dir / "GEOMETRY_SOURCE_INTEGRATION_AUDIT.json"
    queue_path = frontier_run_dir / "SOURCE_ACQUISITION_QUEUE.json"
    frontier_result_path = frontier_run_dir / "RESULT.json"
    frontier_manifest_path = frontier_run_dir / "RUN_MANIFEST.json"
    required = (audit_path, queue_path, frontier_result_path, frontier_manifest_path, CATALOG_PATH)
    if any(not path.is_file() for path in required):
        raise FileNotFoundError("M16_TREATY_AUTHORITY_INPUT_MISSING")

    frontier_manifest = _load(frontier_manifest_path)
    expected_hashes = frontier_manifest.get("output_hashes", {})
    if (
        expected_hashes.get("geometry_source_integration_audit") != _sha256(audit_path)
        or expected_hashes.get("source_acquisition_queue") != _sha256(queue_path)
        or expected_hashes.get("result") != _sha256(frontier_result_path)
    ):
        raise ValueError("M16_TREATY_AUTHORITY_FRONTIER_HASH_CHANGED")

    frontier_audit = _load(audit_path)
    frontier_queue = _load(queue_path)
    frontier_result = _load(frontier_result_path)
    if (
        frontier_audit.get("classified_event_count") != 98
        or frontier_queue.get("record_count") != 98
        or len(frontier_audit.get("records", ())) != 98
    ):
        raise ValueError("M16_TREATY_AUTHORITY_FRONTIER_COUNT_INVALID")

    catalog = load_treaty_authority_catalog(CATALOG_PATH)
    authority_audit = bind_treaty_authority(frontier_audit["records"], catalog)
    if authority_audit["authority_bound_count"] != 98:
        raise ValueError("M16_TREATY_AUTHORITY_COHORT_NOT_FULLY_BOUND")

    task_counts: Counter[str] = Counter()
    queue_records: list[dict[str, Any]] = []
    for record in authority_audit["records"]:
        task_counts.update(record.get("next_source_tasks", ()))
        queue_records.append({
            "candidate_digest": record["candidate_digest"],
            "review_index": record["review_index"],
            "slice": record["slice"],
            "country": record["country"],
            "authority_status": record["authority_status"],
            "rule_strength": record["rule_strength"],
            "domestic_detail_required": record["domestic_detail_required"],
            "next_source_tasks": record.get("next_source_tasks", []),
        })
    queue = {
        "queue_version": "guardsynth-m16-source-frontier-queue-v0.2",
        "record_count": len(queue_records),
        "task_counts": dict(sorted(task_counts.items())),
        "country_counts": frontier_queue["country_counts"],
        "slice_counts": frontier_queue["slice_counts"],
        "treaty_normative_baseline_bound_count": authority_audit[
            "authority_bound_count"
        ],
        "records": queue_records,
        "claim_scope": "SOURCE_ACQUISITION_QUEUE_WITH_TREATY_BASELINE_NOT_COMPLETED_SOURCE_OR_SAFETY",
    }
    result = {
        "experiment_id": EXPERIMENT_ID,
        "run_id": run_id,
        "run_date": date.today().isoformat(),
        "status": "M16_TREATY_BASELINE_BOUND_OTHER_SOURCE_GATES_REMAIN",
        "claim_scope": CLAIM_SCOPE,
        "classified_event_count": 98,
        "treaty_normative_baseline_bound_count": authority_audit[
            "authority_bound_count"
        ],
        "direct_treaty_rule_count": authority_audit["direct_treaty_rule_count"],
        "general_due_care_fallback_count": authority_audit[
            "general_due_care_fallback_count"
        ],
        "domestic_detail_required_count": authority_audit[
            "domestic_detail_required_count"
        ],
        "domestic_legal_compliance_closed_count": 0,
        "remaining_authority_binding_task_count": task_counts.get(
            "BIND_JURISDICTION_MATCHED_AUTHORITY", 0
        ),
        "relevant_actor_or_control_state_closed_count": frontier_result[
            "relevant_actor_or_control_state_closed_count"
        ],
        "target_zone_or_lane_association_closed_count": frontier_result[
            "target_zone_or_lane_association_closed_count"
        ],
        "slice_specific_geometry_closed_count": frontier_result[
            "slice_specific_geometry_closed_count"
        ],
        "outcome_lifecycle_witness_closed_count": frontier_result[
            "outcome_lifecycle_witness_closed_count"
        ],
        "eligible_scene_count": frontier_result["eligible_scene_count"],
        "target_scene_count": frontier_result["target_scene_count"],
        "total_scene_shortfall": frontier_result["total_scene_shortfall"],
        "annotation_start_allowed": False,
        "synthetic_required_field_fill_count": 0,
    }

    output_dir.mkdir(parents=True)
    authority_path = output_dir / "TREATY_AUTHORITY_AUDIT.json"
    next_queue_path = output_dir / "SOURCE_ACQUISITION_QUEUE.json"
    result_path = output_dir / "RESULT.json"
    report_path = output_dir / "REPORT_KO.md"
    manifest_path = output_dir / "RUN_MANIFEST.json"
    _write_json(authority_path, authority_audit)
    _write_json(next_queue_path, queue)
    _write_json(result_path, result)
    _write_text(
        report_path,
        "\n".join((
            "# M16 UN 도로교통협약 기준 결합 보고",
            "",
            f"- 실행 ID: `{run_id}`",
            "- 단계 상태: `COMPLETE` — 현재 98개 장면에 국제협약 연구 기준 결합",
            "- 마일스톤 상태: `M16 PARTIAL` — eligible 1/60 유지",
            f"- 직접 협약 규칙: {authority_audit['direct_treaty_rule_count']}/98",
            f"- 일반 주의의무 fallback: {authority_audit['general_due_care_fallback_count']}/98",
            f"- 국내법 세부사항 필요: {authority_audit['domestic_detail_required_count']}/98",
            "- 국내법 준수 판정: 0/98 (본 단계의 주장 범위에서 제외)",
            "",
            "이 결합은 비엔나 1968 및 제네바 1949 도로교통협약을 중립적 연구 기준으로",
            "선택한 것이다. 현지 국내법 준수, 법률 자문 또는 차량 안전성을 주장하지 않는다.",
            "authority 획득 task는 해소됐지만 geometry, lane/zone association 및 lifecycle",
            "witness가 남아 있으므로 expert annotation은 시작하지 않는다.",
            "",
        )),
    )
    output_hashes = {
        "treaty_authority_audit": _sha256(authority_path),
        "source_acquisition_queue": _sha256(next_queue_path),
        "result": _sha256(result_path),
        "report_ko": _sha256(report_path),
    }
    manifest = {
        **result,
        "code_revision": _revision(),
        "input_class": "LICENSE_RESTRICTED_COHORT_AND_PUBLIC_OFFICIAL_TREATY_METADATA",
        "input_hashes": {
            "geometry_source_integration_audit": _sha256(audit_path),
            "source_acquisition_queue": _sha256(queue_path),
            "frontier_result": _sha256(frontier_result_path),
            "frontier_run_manifest": _sha256(frontier_manifest_path),
            "treaty_authority_catalog": _sha256(CATALOG_PATH),
            "pipeline": _sha256(Path(__file__)),
        },
        "output_hashes": output_hashes,
        "network_use_performed": False,
        "raw_video_copied": False,
        "workspace_dirty_state_preserved": True,
    }
    _write_json(manifest_path, manifest)
    return result


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--frontier-run-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--run-id", required=True)
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    print(json.dumps(execute(
        frontier_run_dir=args.frontier_run_dir,
        output_dir=args.output_dir,
        run_id=args.run_id,
    ), ensure_ascii=False, indent=2, sort_keys=True))
