#!/usr/bin/env python3
"""Bind official California rule sources to one reviewed restricted scene."""

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

from guard_synth.rule_applicability import (
    LOCALIZATION_STATUS,
    build_rule_applicability_evidence,
)


EXPERIMENT_ID = "GUARDSYNTH-RULE-APPLICABILITY-001"
RESTRICTED_ROOT = ROOT / "artifacts/results/restricted"
CA_21950_URL = (
    "https://leginfo.legislature.ca.gov/faces/codes_displaySection.xhtml"
    "?lawCode=VEH&sectionNum=21950."
)
CA_21954_URL = (
    "https://leginfo.legislature.ca.gov/faces/codes_displaySection.xhtml"
    "?lawCode=VEH&sectionNum=21954."
)
SFMTA_ROUTE_URL = "https://www.sfmta.com/routes/powell-hyde-cable-car"
SFCTA_REPORT_URL = (
    "https://www.sfcta.org/sites/default/files/content/Executive/Meetings/"
    "board/2017/03-Mar-14/lombard_final_report_021517.pdf"
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    path.chmod(0o600)


def _restricted(path: Path) -> Path:
    result = path.resolve()
    if not result.is_relative_to(RESTRICTED_ROOT.resolve()):
        raise ValueError("scene evidence and results must remain under restricted results")
    return result


def _validate_snapshot(path: Path, required_tokens: tuple[bytes, ...]) -> str:
    if not path.is_file():
        raise FileNotFoundError(f"official source snapshot is missing: {path.name}")
    body = path.read_bytes()
    normalized = body.lower()
    if not all(token.lower() in normalized for token in required_tokens):
        raise ValueError(f"OFFICIAL_SOURCE_CONTENT_MISMATCH:{path.name}")
    return hashlib.sha256(body).hexdigest()


def execute(
    *,
    packets_path: Path,
    association_path: Path,
    source_audit_path: Path,
    ca_21950_snapshot: Path,
    ca_21954_snapshot: Path,
    sfmta_route_snapshot: Path,
    sfcta_report_snapshot: Path,
    scene_ref: str,
    dataset_country: str,
    output_dir: Path,
) -> tuple[Path, dict[str, Any]]:
    packets_path = _restricted(packets_path)
    association_path = _restricted(association_path)
    source_audit_path = _restricted(source_audit_path)
    output_dir = _restricted(output_dir)
    scene_inputs = (packets_path, association_path, source_audit_path)
    if any(not path.is_file() for path in scene_inputs):
        raise FileNotFoundError("restricted scene evidence is missing")
    if output_dir.exists():
        raise FileExistsError(f"refusing to overwrite existing output: {output_dir}")

    packet_collection = json.loads(packets_path.read_text(encoding="utf-8"))
    association = json.loads(association_path.read_text(encoding="utf-8"))
    source_audit = json.loads(source_audit_path.read_text(encoding="utf-8"))
    packets = [
        item for item in packet_collection.get("packets", ())
        if isinstance(item, dict) and item.get("scene_ref") == scene_ref
    ]
    if len(packets) != 1:
        raise ValueError("SCENE_PACKET_NOT_UNIQUE")
    if source_audit.get("scene_ref") != scene_ref:
        raise ValueError("SOURCE_AUDIT_SCENE_MISMATCH")
    image_sha256 = (
        source_audit.get("field_status", {}).get("timestamps", {}).get("image_sha256")
    )
    if not isinstance(image_sha256, str) or len(image_sha256) != 64:
        raise ValueError("MISSING_HASH_LINKED_REVIEW_IMAGE")

    snapshot_hashes = {
        "ca_vehicle_code_21950": _validate_snapshot(
            ca_21950_snapshot,
            (b"21950", b"driver of a vehicle", b"marked crosswalk", b"unmarked crosswalk"),
        ),
        "ca_vehicle_code_21954": _validate_snapshot(
            ca_21954_snapshot, (b"21954", b"driver of a vehicle")
        ),
        "sfmta_powell_hyde_route": _validate_snapshot(
            sfmta_route_snapshot,
            (b"powell / hyde cable car", b"hyde st &amp; lombard st"),
        ),
        "sfcta_lombard_report": _validate_snapshot(
            sfcta_report_snapshot, (b"%pdf",)
        ),
    }
    localization = {
        "status": LOCALIZATION_STATUS,
        "country": dataset_country,
        "administrative_area": "California",
        "locality": "San Francisco",
        "intersection_hypothesis": "Hyde St & Lombard St",
        "method": "IMAGE_CUES_CORROBORATED_BY_OFFICIAL_TRANSPORT_AND_MUNICIPAL_SOURCES",
        "evidence_refs": [
            f"restricted-image-sha256:{image_sha256}",
            f"restricted-sha256:{_sha256(packets_path)}#/packets",
            SFMTA_ROUTE_URL,
            SFCTA_REPORT_URL,
        ],
        "independent_dataset_gps_confirmation": False,
    }
    rule_sources = [
        {
            "source_id": "CA-VEH-21950",
            "authority": "California Legislature",
            "jurisdiction": "California",
            "section": "Vehicle Code 21950",
            "official_url": CA_21950_URL,
            "snapshot_sha256": snapshot_hashes["ca_vehicle_code_21950"],
            "role": "PRIMARY_CROSSWALK_YIELD_DUE_CARE",
            "effective_date": "2023-01-01",
        },
        {
            "source_id": "CA-VEH-21954",
            "authority": "California Legislature",
            "jurisdiction": "California",
            "section": "Vehicle Code 21954",
            "official_url": CA_21954_URL,
            "snapshot_sha256": snapshot_hashes["ca_vehicle_code_21954"],
            "role": "OUTSIDE_CROSSWALK_EXCEPTION_CONTEXT",
            "effective_date": "2023-01-01",
        },
    ]
    evidence = build_rule_applicability_evidence(
        scene_ref=scene_ref,
        dataset_country=dataset_country,
        packet=packets[0],
        association=association,
        localization=localization,
        rule_sources=rule_sources,
    )
    if evidence["status"] != "AVAILABLE_SOURCE_LINKED":
        raise ValueError(str(evidence["reason_code"]))

    output_dir.mkdir(parents=True)
    _write_json(output_dir / "RULE_APPLICABILITY_EVIDENCE.json", evidence)
    result = {
        "experiment_id": EXPERIMENT_ID,
        "run_id": output_dir.name,
        "run_date": date.today().isoformat(),
        "status": "EXECUTED",
        "scene_ref": scene_ref,
        "rule_source_status": evidence["status"],
        "applicability_verdict": evidence["applicability_verdict"],
        "primary_rule_source_id": evidence["primary_rule_source_id"],
        "localization_status": LOCALIZATION_STATUS,
        "independent_dataset_gps_confirmation": False,
        "unsourced_normative_or_numeric_value_count": 0,
        "vehicle_safety_validated": False,
        "claim_scope": evidence["claim_scope"],
    }
    _write_json(output_dir / "RESULT.json", result)
    _write_json(output_dir / "RUN_MANIFEST.json", {
        **result,
        "input_class": "LICENSE_RESTRICTED",
        "restricted_input_hashes": {
            "partial_packets": _sha256(packets_path),
            "association_evidence": _sha256(association_path),
            "source_audit": _sha256(source_audit_path),
        },
        "official_source_snapshot_hashes": snapshot_hashes,
        "official_source_urls": [
            CA_21950_URL, CA_21954_URL, SFMTA_ROUTE_URL, SFCTA_REPORT_URL,
        ],
        "rule_applicability_code_sha256": _sha256(
            ROOT / "projects/04-guardsynth-coc/src/guard_synth/rule_applicability.py"
        ),
        "cli_sha256": _sha256(Path(__file__).resolve()),
        "raw_restricted_source_paths_included": False,
        "official_source_snapshots_copied": False,
        "deterministic": True,
        "network_or_credential_use_performed_by_builder": False,
    })
    (output_dir / "REPORT_KO.md").write_text(
        f"""# GuardSynth 규칙 적용성 근거 결과

- 상태: **EXECUTED**
- 장면: `{scene_ref}`
- 공식 주 규칙: **California Vehicle Code §21950**
- 적용성: **CONDITIONALLY_APPLICABLE**
- 위치 근거: **이미지 단서 + 공식 교통·도시 자료 교차 확인**
- 데이터셋 GPS 확인: **없음**
- 출처 없는 규범·수치값: **0건**

사람이 높은 신뢰도로 횡단보도와 보행자의 conflict-region 점유를 판정한 장면에 공식
California Vehicle Code §21950을 연결했다. §21954는 횡단보도 밖 상황의 예외 문맥으로만
보존했다. 원문 URL과 수집 스냅샷 SHA-256은 manifest에 기록했다.

장소는 데이터셋 GPS가 아니라 이미지의 케이블카 선로·정류장·도로 형태를 SFMTA
Powell/Hyde 노선 및 SFCTA Lombard 자료와 대조해 얻은 고신뢰 추론이다. 따라서 이 결과는
법률 자문, 최종 법적 판정, 수치 제동 한계 또는 차량 안전성을 입증하지 않는다.
""",
        encoding="utf-8",
    )
    return output_dir, result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packets", type=Path, required=True)
    parser.add_argument("--association-evidence", type=Path, required=True)
    parser.add_argument("--source-audit", type=Path, required=True)
    parser.add_argument("--ca-21950-snapshot", type=Path, required=True)
    parser.add_argument("--ca-21954-snapshot", type=Path, required=True)
    parser.add_argument("--sfmta-route-snapshot", type=Path, required=True)
    parser.add_argument("--sfcta-report-snapshot", type=Path, required=True)
    parser.add_argument("--scene-ref", required=True)
    parser.add_argument("--dataset-country", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output, result = execute(
        packets_path=args.packets,
        association_path=args.association_evidence,
        source_audit_path=args.source_audit,
        ca_21950_snapshot=args.ca_21950_snapshot,
        ca_21954_snapshot=args.ca_21954_snapshot,
        sfmta_route_snapshot=args.sfmta_route_snapshot,
        sfcta_report_snapshot=args.sfcta_report_snapshot,
        scene_ref=args.scene_ref,
        dataset_country=args.dataset_country,
        output_dir=args.output_dir,
    )
    print(json.dumps({
        "status": result["status"],
        "applicability_verdict": result["applicability_verdict"],
        "output": output.relative_to(ROOT).as_posix(),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
