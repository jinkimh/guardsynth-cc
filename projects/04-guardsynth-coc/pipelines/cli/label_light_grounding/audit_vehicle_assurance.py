#!/usr/bin/env python3
"""Audit whether one restricted scene has a source-bearing assurance profile."""

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

from guard_synth.vehicle_assurance_audit import audit_vehicle_assurance_candidates


EXPERIMENT_ID = "GUARDSYNTH-VEHICLE-ASSURANCE-AUDIT-001"
RESTRICTED_RESULTS = ROOT / "artifacts/results/restricted"
RESTRICTED_DATA = ROOT / "data/restricted"
DATASET_URL = "https://huggingface.co/datasets/nvidia/PhysicalAI-Autonomous-Vehicles"
DRIVE_AGX_URL = "https://developer.nvidia.com/drive/agx"
VEHICLEIO_WORKFLOW_URL = (
    "https://developer.nvidia.com/docs/drive/drive-os/7.0.3/public/drive-os-linux-sdk/"
    "embedded-software-components/DRIVE_AGX_SoC/DriveWorks/DriveWorks_SDK/tutorials/"
    "intermediate_tutorials/vehicle_action/vehicleio/usecase1.html"
)
VEHICLEIO_ACTUATORS_URL = (
    "https://developer.nvidia.com/docs/drive/drive-os/7.0.3/public/"
    "drive-os-linux-sdk-api-ref/group__VehicleIO__actuators__group.html"
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    path.chmod(0o600)


def _restricted_input(path: Path) -> Path:
    result = path.resolve()
    if not (
        result.is_relative_to(RESTRICTED_RESULTS.resolve())
        or result.is_relative_to(RESTRICTED_DATA.resolve())
    ):
        raise ValueError("scene inputs must remain under restricted data/results")
    return result


def _validate_snapshot(path: Path, tokens: tuple[bytes, ...]) -> str:
    if not path.is_file():
        raise FileNotFoundError(f"official source snapshot is missing: {path.name}")
    body = path.read_bytes()
    normalized = body.lower()
    if not all(token.lower() in normalized for token in tokens):
        raise ValueError(f"OFFICIAL_SOURCE_CONTENT_MISMATCH:{path.name}")
    return hashlib.sha256(body).hexdigest()


def execute(
    *,
    scene_source_bundle_path: Path,
    cohort_conformance_path: Path,
    experiment_report_path: Path,
    dataset_card_snapshot: Path,
    drive_agx_snapshot: Path,
    vehicleio_workflow_snapshot: Path,
    vehicleio_actuators_snapshot: Path,
    output_dir: Path,
) -> tuple[Path, dict[str, Any]]:
    bundle_path = _restricted_input(scene_source_bundle_path)
    cohort_path = _restricted_input(cohort_conformance_path)
    report_path = _restricted_input(experiment_report_path)
    output_dir = output_dir.resolve()
    if not output_dir.is_relative_to(RESTRICTED_RESULTS.resolve()):
        raise ValueError("assurance audit result must remain under restricted results")
    if any(not path.is_file() for path in (bundle_path, cohort_path, report_path)):
        raise FileNotFoundError("local assurance audit input is missing")
    if output_dir.exists():
        raise FileExistsError(f"refusing to overwrite existing output: {output_dir}")

    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
    binding = bundle.get("vehicle_binding")
    if not (
        isinstance(binding, dict)
        and binding.get("status") == "AVAILABLE_SOURCE_LINKED"
        and isinstance(binding.get("vehicle_binding_key"), str)
    ):
        raise ValueError("MISSING_SOURCE_LINKED_VEHICLE_BINDING")
    binding_key = binding["vehicle_binding_key"]

    official_hashes = {
        "physicalai_dataset_card": _validate_snapshot(
            dataset_card_snapshot,
            (b"egomotion", b"vehicle_dimensions", b"hyperion_8.1"),
        ),
        "drive_agx": _validate_snapshot(
            drive_agx_snapshot, (b"vehicle accessory kit", b"vehicle io")
        ),
        "vehicleio_workflow": _validate_snapshot(
            vehicleio_workflow_snapshot,
            (b"100 milliseconds", b"vendor documentation", b"brakevalid"),
        ),
        "vehicleio_actuators": _validate_snapshot(
            vehicleio_actuators_snapshot,
            (
                b"highly dependent on the type of the actuation interface",
                b"dwvehicleio_getcapabilities",
            ),
        ),
    }
    candidates = [
        {
            "candidate_id": "physicalai-observed-egomotion",
            "source_kind": "OBSERVED_EGOMOTION",
            "source_ref": DATASET_URL,
            "source_sha256": official_hashes["physicalai_dataset_card"],
        },
        {
            "candidate_id": "coc-derived-response-latency",
            "source_kind": "DERIVED_COC_RESPONSE_LATENCY",
            "source_ref": f"restricted-sha256:{_sha256(cohort_path)}#/episodes",
            "source_sha256": _sha256(cohort_path),
        },
        {
            "candidate_id": "drive-agx-platform-description",
            "source_kind": "PLATFORM_INTERFACE_DOCUMENTATION",
            "source_ref": DRIVE_AGX_URL,
            "source_sha256": official_hashes["drive_agx"],
        },
        {
            "candidate_id": "driveworks-vehicleio-interface",
            "source_kind": "PLATFORM_INTERFACE_DOCUMENTATION",
            "source_ref": VEHICLEIO_ACTUATORS_URL,
            "source_sha256": official_hashes["vehicleio_actuators"],
        },
    ]
    audit = audit_vehicle_assurance_candidates(
        vehicle_binding_key=binding_key,
        candidates=candidates,
    )
    if audit["status"] != "REVIEW_REQUIRED":
        raise ValueError("UNEXPECTED_ASSURANCE_AUDIT_RESULT")
    audit.update({
        "scene_ref": bundle.get("scene_ref"),
        "binding_scope": binding.get("binding_scope"),
        "local_source_findings": [
            "EGOMOTION_CONTAINS_OBSERVED_ACCELERATION_NOT_ACTUATOR_COMMAND",
            "COC_RESPONSE_LATENCY_IS_BEHAVIORAL_DERIVATION_NOT_CONTROL_LATENCY",
            "NO_BRAKE_COMMAND_OR_ACTUATION_FEEDBACK_FEATURE_IN_DATASET_SCHEMA",
        ],
        "official_source_findings": [
            "DRIVE_AGX_IS_COMPUTE_AND_IO_PLATFORM_NOT_BOUND_TEST_VEHICLE",
            "VEHICLEIO_LIMITS_DEPEND_ON_ACTUATION_INTERFACE",
            "RUNTIME_CAPABILITIES_AND_VENDOR_VALIDATION_REQUIRED",
        ],
        "experiment_report_sha256": _sha256(report_path),
        "official_source_refs": [
            DATASET_URL,
            DRIVE_AGX_URL,
            VEHICLEIO_WORKFLOW_URL,
            VEHICLEIO_ACTUATORS_URL,
        ],
    })

    output_dir.mkdir(parents=True)
    _write_json(output_dir / "VEHICLE_ASSURANCE_AUDIT.json", audit)
    data_gap = {
        "status": "P0B_VEHICLE_ASSURANCE_BLOCKED_DATA_GAP",
        "scene_ref": bundle.get("scene_ref"),
        "reason_code": audit["reason_code"],
        "missing_evidence": audit["required_evidence_manifest"],
        "rejected_candidates": audit["rejected_candidates"],
        "permitted_resolution_paths": [
            {
                "path": "BOUND_RESEARCH_VEHICLE",
                "required": "vehicle/DBW identity, runtime capabilities, vendor or controlled-test validation",
            },
            {
                "path": "SOURCE_BEARING_SIMULATOR_PROFILE",
                "required": "versioned dynamics/controller model and validated bounds; report separately from real vehicle",
            },
        ],
        "observed_clip_envelope_usable_as_hard_bound": False,
        "contract_generation_allowed": False,
    }
    _write_json(output_dir / "ASSURANCE_DATA_GAP.json", data_gap)
    result = {
        "experiment_id": EXPERIMENT_ID,
        "run_id": output_dir.name,
        "run_date": date.today().isoformat(),
        "status": "BLOCKED_SOURCE_GAP",
        "scene_ref": bundle.get("scene_ref"),
        "assurance_profile_status": audit["status"],
        "accepted_profile_count": 0,
        "rejected_candidate_count": len(audit["rejected_candidates"]),
        "contract_generation_allowed": False,
        "synthetic_value_fill_performed": False,
        "vehicle_safety_validated": False,
        "claim_scope": audit["claim_scope"],
    }
    _write_json(output_dir / "RESULT.json", result)
    _write_json(output_dir / "RUN_MANIFEST.json", {
        **result,
        "input_class": "LICENSE_RESTRICTED",
        "restricted_input_hashes": {
            "scene_source_bundle": _sha256(bundle_path),
            "cohort_conformance": _sha256(cohort_path),
            "experiment_report": _sha256(report_path),
        },
        "official_source_snapshot_hashes": official_hashes,
        "official_source_urls": audit["official_source_refs"],
        "audit_module_sha256": _sha256(
            ROOT / "projects/04-guardsynth-coc/src/guard_synth/vehicle_assurance_audit.py"
        ),
        "cli_sha256": _sha256(Path(__file__).resolve()),
        "raw_clip_id_included": False,
        "official_source_snapshots_copied": False,
        "network_or_credential_use_performed_by_audit": False,
        "deterministic": True,
    })
    (output_dir / "REPORT_KO.md").write_text(
        f"""# GuardSynth 차량 assurance source 감사

- 상태: **BLOCKED_SOURCE_GAP**
- 장면: `{bundle.get('scene_ref')}`
- source-linked vehicle/rig binding: **있음**
- 승인 가능한 assurance profile: **0건**
- 검토했으나 거부한 후보: **{len(audit['rejected_candidates'])}건**
- 계약 생성 허용: **아니오**
- 임의 수치 보충: **0건**

로컬 데이터의 egomotion acceleration은 녹화된 움직임이고, CoC response latency는 문장 event와
속도 변화 사이의 파생 응답시간이다. 둘 다 brake command→실제 감속의 보장 지연이나 최소 보장
감속도가 아니다. PhysicalAI schema에도 brake command와 actuation feedback이 없다.

공식 DRIVE AGX 문서는 compute/IO 개발 플랫폼을 설명하며 수집 차량의 제동 성능을 보장하지
않는다. VehicleIO 문서는 지원 한계가 actuation interface에 의존하고 runtime capabilities 및
DBW vendor 근거가 필요함을 명시한다. 따라서 Hyperion 8.1 rig binding만으로 수치를 만들지 않았다.

실제 장면 9/9를 닫으려면 동일 vehicle/DBW binding에 대한 capability dump와 vendor/OEM 문서 또는
통제된 제동시험으로 감속·command-to-deceleration latency·jerk·운용조건·불확실성을 함께 제공해야
한다. 대안은 source-bearing simulator profile로 별도 실험을 수행하는 것이며 실제 차량 안전
증거로 주장할 수 없다.
""",
        encoding="utf-8",
    )
    return output_dir, result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scene-source-bundle", type=Path, required=True)
    parser.add_argument("--cohort-conformance", type=Path, required=True)
    parser.add_argument("--experiment-report", type=Path, required=True)
    parser.add_argument("--dataset-card-snapshot", type=Path, required=True)
    parser.add_argument("--drive-agx-snapshot", type=Path, required=True)
    parser.add_argument("--vehicleio-workflow-snapshot", type=Path, required=True)
    parser.add_argument("--vehicleio-actuators-snapshot", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output, result = execute(
        scene_source_bundle_path=args.scene_source_bundle,
        cohort_conformance_path=args.cohort_conformance,
        experiment_report_path=args.experiment_report,
        dataset_card_snapshot=args.dataset_card_snapshot,
        drive_agx_snapshot=args.drive_agx_snapshot,
        vehicleio_workflow_snapshot=args.vehicleio_workflow_snapshot,
        vehicleio_actuators_snapshot=args.vehicleio_actuators_snapshot,
        output_dir=args.output_dir,
    )
    print(json.dumps({
        "status": result["status"],
        "output": output.relative_to(ROOT).as_posix(),
        "assurance_profile_status": result["assurance_profile_status"],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
