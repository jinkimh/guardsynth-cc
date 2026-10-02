"""Audit one blinded calibration scene for hash-linked source closure."""

from __future__ import annotations

import argparse
from datetime import date
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from cli.project_paths import project_root


ROOT = project_root(__file__)
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from guard_synth.scene_source_closure import audit_calibration_scene_source


EXPERIMENT_ID = "GUARDSYNTH-CALIBRATION-SCENE-SOURCE-AUDIT-001"
RESTRICTED_ROOT = ROOT / "artifacts/results/restricted"
CLAIM_SCOPE = "ONE_SCENE_HASH_LINKED_SOURCE_AUDIT_NOT_SOURCE_CLOSURE_ASSOCIATION_ACCURACY_OR_VEHICLE_SAFETY"

_ACCEPTANCE = {
    "timestamps": "동일 장면 이미지/센서 frame에 해시로 연결된 단조 timestamp 배열과 source reference",
    "ego_pose_and_speed": "동일 timestamp에 정렬된 ego pose와 speed 및 원본 field reference",
    "relevant_actor_tracks": "동일 장면의 actor track ID, 시간열과 detector/tracker evidence reference",
    "target_zone_or_lane_association": "유일한 target–zone/lane 선택과 독립 검토 가능한 association evidence",
    "conflict_or_stop_geometry": "ego-path frame의 conflict/stop geometry와 생성 source fields",
    "verified_coordinate_transform": "sensor/rig에서 ego-path frame으로의 검증된 transform과 calibration evidence",
    "applicable_rule_source_refs": "장면 관할·ODD·maneuver에 적용되는 versioned rule source reference",
    "exact_vehicle_binding": "실행 차량/rig/configuration을 유일하게 식별하는 binding key와 evidence",
    "source_bearing_vehicle_assurance_profile": "binding과 scope가 일치하는 제동·지연·불확실성 profile source",
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _restricted(path: Path) -> Path:
    resolved = path.resolve()
    if not resolved.is_relative_to(RESTRICTED_ROOT.resolve()):
        raise ValueError("all calibration source audit paths must remain restricted")
    return resolved


def execute(
    *,
    packets_path: Path,
    embedded_manifest_path: Path,
    adapter_result_path: Path,
    scene_source_bundle_path: Path | None,
    association_evidence_path: Path | None,
    rule_applicability_evidence_path: Path | None,
    source_root: Path,
    output_dir: Path,
) -> tuple[Path, dict[str, Any]]:
    inputs = [
        _restricted(path) for path in
        (packets_path, embedded_manifest_path, adapter_result_path)
    ]
    source_bundle_path = (
        _restricted(scene_source_bundle_path)
        if scene_source_bundle_path is not None else None
    )
    if source_bundle_path is not None:
        inputs.append(source_bundle_path)
    association_path = (
        _restricted(association_evidence_path)
        if association_evidence_path is not None else None
    )
    if association_path is not None:
        inputs.append(association_path)
    rule_applicability_path = (
        _restricted(rule_applicability_evidence_path)
        if rule_applicability_evidence_path is not None else None
    )
    if rule_applicability_path is not None:
        inputs.append(rule_applicability_path)
    source_root = _restricted(source_root)
    output_dir = _restricted(output_dir)
    if any(not path.is_file() for path in inputs):
        raise FileNotFoundError("calibration source audit input is missing")
    if not source_root.is_dir():
        raise FileNotFoundError("calibration source root is missing")
    if output_dir.exists():
        raise FileExistsError(f"refusing to overwrite existing output: {output_dir}")

    packet_collection = json.loads(inputs[0].read_text(encoding="utf-8"))
    embedded_manifest = json.loads(inputs[1].read_text(encoding="utf-8"))
    adapter_result = json.loads(inputs[2].read_text(encoding="utf-8"))
    scene_source_bundle = (
        json.loads(source_bundle_path.read_text(encoding="utf-8"))
        if source_bundle_path is not None else None
    )
    association_evidence = (
        json.loads(association_path.read_text(encoding="utf-8"))
        if association_path is not None else None
    )
    rule_applicability_evidence = (
        json.loads(rule_applicability_path.read_text(encoding="utf-8"))
        if rule_applicability_path is not None else None
    )
    packets = list(packet_collection.get("packets", ()))
    if not packets:
        raise ValueError("partial packet collection is empty")
    adapter_sha256 = _sha256(inputs[2])
    audits = [
        audit_calibration_scene_source(
            packet,
            embedded_manifest,
            source_root,
            adapter_result=adapter_result,
            adapter_document_sha256=adapter_sha256,
            scene_source_bundle=scene_source_bundle,
            scene_source_bundle_sha256=(
                _sha256(source_bundle_path) if source_bundle_path is not None else None
            ),
            association_evidence=association_evidence,
            association_evidence_sha256=(
                _sha256(association_path) if association_path is not None else None
            ),
            rule_applicability_evidence=rule_applicability_evidence,
            rule_applicability_evidence_sha256=(
                _sha256(rule_applicability_path)
                if rule_applicability_path is not None else None
            ),
        )
        for packet in packets
    ]
    audit = min(
        audits,
        key=lambda item: (
            -len(item["available_fields"]),
            hashlib.sha256(item["packet_id"].encode("utf-8")).hexdigest(),
        ),
    )
    work_order = {
        "work_order_version": "guardsynth-calibration-source-acquisition-v0.1",
        "packet_id": audit["packet_id"],
        "scene_ref": audit["scene_ref"],
        "status": "BLOCKED_SOURCE_ACQUISITION",
        "selection_method": "MAX_SOURCE_LINKED_FIELD_COUNT_THEN_PACKET_ID_SHA256",
        "completed_fields": audit["available_fields"],
        "pending_task_count": len(audit["missing_fields"]),
        "tasks": [
            {
                "field": field,
                "reason_code": audit["field_status"][field]["reason_code"],
                "accepted_evidence": _ACCEPTANCE[field],
                "synthetic_or_image_only_substitution_allowed": False,
                "status": "OPEN",
            }
            for field in audit["missing_fields"]
        ],
        "execution_allowed": False,
        "claim_scope": CLAIM_SCOPE,
    }
    result = {
        "experiment_id": EXPERIMENT_ID,
        "run_id": output_dir.name,
        "run_date": date.today().isoformat(),
        "status": "EXECUTED_AUDIT",
        "decision": "M13_CALIBRATION_SCENE_BLOCKED_SOURCE_ACQUISITION",
        "available_field_count": len(audit["available_fields"]),
        "missing_field_count": len(audit["missing_fields"]),
        "source_complete_scene_count": int(audit["source_complete"]),
        "guardsynth_eblc_core_z3_scene_runs": 0,
        "synthetic_required_values": len(audit["synthesized_required_values"]),
        "association_review_ui_generated": bool(
            association_path is not None
            and (association_path.parent / "ASSOCIATION_REVIEW.html").is_file()
        ),
        "association_review_blocker": audit["association_readiness"]["reason_code"],
        "rule_applicability_source_linked": (
            audit["field_status"]["applicable_rule_source_refs"]["status"]
            == "AVAILABLE_SOURCE_LINKED"
        ),
        "claim_scope": CLAIM_SCOPE,
    }
    association = audit["association_readiness"]
    association_resolved = (
        audit["field_status"]["target_zone_or_lane_association"]["status"]
        == "AVAILABLE_SOURCE_LINKED"
    )
    association_blocker = {
        "experiment_id": EXPERIMENT_ID,
        "run_id": output_dir.name,
        "status": (
            "ASSOCIATION_SOURCE_LINKED"
            if association_resolved else
            "READY_FOR_ASSOCIATION_REVIEW"
            if association["review_ui_allowed"] else
            "BLOCKED_INCOMPLETE_ACTOR_CANDIDATE_SET"
        ),
        "reason_code": None if association_resolved else association["reason_code"],
        "review_ui_generated": result["association_review_ui_generated"],
        "declared_candidate_count": association["declared_candidate_count"],
        "serialized_candidate_record_count": association[
            "serialized_candidate_record_count"
        ],
        "candidate_track_samples_preserved": association[
            "candidate_track_samples_preserved"
        ],
        "required_extractor": (
            "projects/03-sequential-coc-verification/experiments/feasibility/analyze_nvidia_obstacle_feasibility.py"
        ),
        "required_output_format": "obstacle-feasibility-v2-all-candidates",
        "existing_restricted_input_overwritten": False,
        "network_or_credential_use_performed": False,
        "claim_scope": "ASSOCIATION_REVIEW_INPUT_COMPLETENESS_NOT_ASSOCIATION_ACCURACY_OR_SAFETY",
    }

    output_dir.mkdir(parents=True)
    _write_json(output_dir / "CALIBRATION_SOURCE_AUDIT.json", audit)
    _write_json(output_dir / "SOURCE_ACQUISITION_WORK_ORDER.json", work_order)
    _write_json(output_dir / "ACTOR_ASSOCIATION_BLOCKER.json", association_blocker)
    _write_json(output_dir / "RESULT.json", result)
    _write_json(output_dir / "RUN_MANIFEST.json", {
        "experiment_id": EXPERIMENT_ID,
        "run_id": output_dir.name,
        "run_date": date.today().isoformat(),
        "input_class": "LICENSE_RESTRICTED",
        "python_version": sys.version.split()[0],
        "solver_execution": "NOT_RUN_SOURCE_CLOSURE_BLOCKED",
        "input_hashes": {
            "partial_packets": _sha256(inputs[0]),
            "embedded_manifest": _sha256(inputs[1]),
            "derived_adapter_result": adapter_sha256,
            **({
                "scene_source_bundle": _sha256(source_bundle_path)
            } if source_bundle_path is not None else {}),
            **({
                "association_evidence": _sha256(association_path)
            } if association_path is not None else {}),
            **({
                "rule_applicability_evidence": _sha256(rule_applicability_path)
            } if rule_applicability_path is not None else {}),
        },
        "code_hashes": {
            "audit_cli": _sha256(Path(__file__).resolve()),
            "source_audit_module": _sha256(ROOT / "projects/04-guardsynth-coc/src/guard_synth/scene_source_closure.py"),
            "actor_candidate_export": _sha256(
                ROOT / "projects/04-guardsynth-coc/src/guard_synth/actor_candidate_export.py"
            ),
            "obstacle_extractor": _sha256(
                ROOT / "projects/03-sequential-coc-verification/experiments/feasibility/analyze_nvidia_obstacle_feasibility.py"
            ),
            **({
                "association_module": _sha256(
                    ROOT / "projects/04-guardsynth-coc/src/guard_synth/geometric_association.py"
                ),
                "association_cli": _sha256(
                    ROOT / "projects/04-guardsynth-coc/pipelines/cli/label_light_grounding/build_geometric_association.py"
                ),
            } if association_path is not None else {}),
            **({
                "rule_applicability_module": _sha256(
                    ROOT / "projects/04-guardsynth-coc/src/guard_synth/rule_applicability.py"
                ),
                "rule_applicability_cli": _sha256(
                    ROOT / "projects/04-guardsynth-coc/pipelines/cli/label_light_grounding/build_rule_applicability.py"
                ),
            } if rule_applicability_path is not None else {}),
        },
        "source_root_recorded": False,
        "raw_source_paths_included": False,
        "raw_images_copied": False,
        "deterministic_hash_linkage": True,
        "synthetic_scene_fill_performed": False,
        "claim_scope": CLAIM_SCOPE,
    })
    association_summary = (
        "all-candidates track과 차량 폭의 oriented-box corridor overlap을 계산해 target을\n"
        "최근접 단일 후보가 아닌 source-linked SET으로 고정했다. 이는 CoC 지시 대상, 법적 zone 또는\n"
        "충돌 확률 판정이 아니라 기하학적 track–corridor association이다."
        if association_resolved else
        "all-candidates v2 근거에서 선언된 actor 후보와 시간순 track sample이 모두 보존됐다.\n"
        "따라서 association 최소 검토 입력은 준비됐지만 target–zone 선택 자체는 아직 수행하지 않았다."
        if association["review_ui_allowed"]
        else
        "기존 obstacle 파생물은 각 이벤트의 전체 actor 후보가 아니라 가장 가까운 후보만 보존했다.\n"
        "따라서 제한된 선택지를 보여 주는 편향된 검토 화면은 만들지 않았다. 구체적인 차단 사유와\n"
        "새 all-candidates 추출 형식은 `ACTOR_ASSOCIATION_BLOCKER.json`에 기록했다."
    )
    source_bundle_summary = (
        "별도 scene source bundle의 dataset revision, egomotion, calibration 및 configuration 근거를\n"
        "검증해 event rig→model-t0 ego-path transform과 clip-specific rig binding을 연결했다.\n"
        "이 binding은 물리 차량 VIN이나 제동 보장 profile을 의미하지 않는다."
        if source_bundle_path is not None else
        "별도 scene source bundle은 입력되지 않았다."
    )
    rule_summary = (
        "공식 California Vehicle Code §21950/§21954 원문 snapshot과 사람의 횡단보도 장면\n"
        "판정, source-linked actor SET을 결합해 규칙 적용성을 조건부로 연결했다. 관할 위치는\n"
        "데이터셋 GPS가 아니라 이미지 단서와 공식 교통·도시 자료의 교차 확인이므로 그 한계를\n"
        "evidence에 명시했다. 법률 자문, 수치 차량 한계 또는 안전 검증을 뜻하지 않는다."
        if result["rule_applicability_source_linked"] else
        "장면에 적용할 공식 rule source는 아직 source-linked 상태가 아니다."
    )
    (output_dir / "REPORT_KO.md").write_text(
        f"""# GuardSynth 첫 calibration 장면 source audit

- 상태: **EXECUTED_AUDIT**
- source-complete 장면: **{result['source_complete_scene_count']}/1**
- hash-linked 실제 입력: **{result['available_field_count']}/9**
- 미확보 입력: **{result['missing_field_count']}/9**
- GuardSynth→EBLC→Core/Z3 실행: **0건**
- 임의 생성 필수값: **{result['synthetic_required_values']}건**
- association 검토 화면 생성: **{'예' if result['association_review_ui_generated'] else '아니오'}**

10개 심사 장면 중 source-linked field가 가장 많은 항목을 deterministic hash tie-break로 골랐다.
심사 이미지와 기존 제한 파생 이미지는 content SHA-256으로 유일하게 연결됐다. 같은 디렉터리의
sidecar timestamp와 동일 episode의 기존 derived adapter에서 ego pose/speed 및 1-D conflict
geometry를 연결했다. 나머지 field도 각각 독립된 source evidence가 있을 때만 연결했다.

{association_summary}

{source_bundle_summary}

{rule_summary}

따라서 이 결과는 source discovery 진전이지 source closure나 차량 안전 검증이 아니다.
`SOURCE_ACQUISITION_WORK_ORDER.json`의 {result['missing_field_count']}개 항목을 실제 근거로 닫기 전에는 계약 실행을 금지한다.
""",
        encoding="utf-8",
    )
    return output_dir, result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packets", type=Path, required=True)
    parser.add_argument("--embedded-manifest", type=Path, required=True)
    parser.add_argument("--adapter-result", type=Path, required=True)
    parser.add_argument("--scene-source-bundle", type=Path)
    parser.add_argument("--association-evidence", type=Path)
    parser.add_argument("--rule-applicability-evidence", type=Path)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output, result = execute(
        packets_path=args.packets,
        embedded_manifest_path=args.embedded_manifest,
        adapter_result_path=args.adapter_result,
        scene_source_bundle_path=args.scene_source_bundle,
        association_evidence_path=args.association_evidence,
        rule_applicability_evidence_path=args.rule_applicability_evidence,
        source_root=args.source_root,
        output_dir=args.output_dir,
    )
    print(json.dumps({
        "status": result["status"],
        "decision": result["decision"],
        "output": output.relative_to(ROOT).as_posix(),
        "available_field_count": result["available_field_count"],
        "missing_field_count": result["missing_field_count"],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
