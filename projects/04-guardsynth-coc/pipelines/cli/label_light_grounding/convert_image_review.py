"""Convert a restricted image-only review export into fail-closed partial scene packets."""

from __future__ import annotations

import argparse
from collections import Counter
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

from guard_synth.label_light_grounding import (
    IMAGE_REVIEW_PARTIAL_PACKET_SCHEMA_PATH,
    IMAGE_REVIEW_PARTIAL_PACKET_VERSION,
    build_blinded_calibration_audit_queue,
    convert_image_review_export,
)
from guard_synth_eblc.schema_validation import load_json


EXPERIMENT_ID = "GUARDSYNTH-IMAGE-REVIEW-PARTIAL-SCENE-001"
RESTRICTED_ROOT = ROOT / "artifacts/results/restricted"
CLAIM_SCOPE = "IMAGE_REVIEW_TO_PARTIAL_SCENE_PACKET_NOT_SOURCE_CLOSURE_ASSOCIATION_ACCURACY_OR_VEHICLE_SAFETY"


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
        raise ValueError("image-review input and output must remain under artifacts/results/restricted")
    return resolved


def execute(input_path: Path, output_dir: Path) -> tuple[Path, dict[str, Any]]:
    input_path = _restricted(input_path)
    output_dir = _restricted(output_dir)
    if not input_path.is_file():
        raise FileNotFoundError(f"image-review export not found: {input_path}")
    if output_dir.exists():
        raise FileExistsError(f"refusing to overwrite existing output: {output_dir}")

    source_sha256 = _sha256(input_path)
    packets = convert_image_review_export(load_json(input_path), source_sha256)
    calibration_queue = build_blinded_calibration_audit_queue(packets)
    output_dir.mkdir(parents=True)

    missing_fields = Counter()
    reasons = Counter()
    slices = Counter()
    strata = Counter()
    for packet in packets:
        missing_fields.update(packet["source_closure"]["missing_fields"])
        reasons.update(packet["source_closure"]["reason_codes"])
        slices.update(packet["selection_hints"]["candidate_slices"])
        strata.update(packet["selection_hints"]["candidate_strata"])

    manifest = {
        "packet_count": len(packets),
        "source_complete_packet_count": sum(
            packet["source_closure"]["source_complete"] for packet in packets
        ),
        "contract_generation_allowed_count": sum(
            packet["source_closure"]["contract_generation_allowed"] for packet in packets
        ),
        "synthesized_required_value_count": sum(
            len(packet["source_closure"]["synthesized_required_values"])
            for packet in packets
        ),
        "missing_field_counts": dict(sorted(missing_fields.items())),
        "reason_code_counts": dict(sorted(reasons.items())),
        "candidate_slice_counts": dict(sorted(slices.items())),
        "candidate_stratum_counts": dict(sorted(strata.items())),
        "slot_assignment_status": "UNASSIGNED_REVIEW_REQUIRED",
        "calibration_audit_sample_count": calibration_queue["sample_count"],
        "calibration_audit_status": "PENDING_INDEPENDENT_REVIEW",
        "claim_scope": CLAIM_SCOPE,
    }
    gates = {
        "all_records_converted": len(packets) > 0,
        "all_packets_fail_closed": all(
            packet["source_closure"]["status"] == "REVIEW_REQUIRED"
            and not packet["source_closure"]["source_complete"]
            and not packet["source_closure"]["contract_generation_allowed"]
            for packet in packets
        ),
        "missing_inputs_reported_for_every_packet": all(
            len(packet["source_closure"]["missing_fields"]) == 9 for packet in packets
        ),
        "no_required_value_synthesized": manifest["synthesized_required_value_count"] == 0,
    }
    result = {
        "experiment_id": EXPERIMENT_ID,
        "run_id": output_dir.name,
        "run_date": date.today().isoformat(),
        "status": "EXECUTED" if all(gates.values()) else "FAILED",
        "decision": "PARTIAL_SCENE_PACKETS_CREATED_SOURCE_CLOSURE_REQUIRED",
        "gates": gates,
        "metrics": manifest,
        "claim_scope": CLAIM_SCOPE,
    }

    _write_json(output_dir / "PARTIAL_SCENE_PACKETS.json", {
        "collection_version": IMAGE_REVIEW_PARTIAL_PACKET_VERSION,
        "input_class": "LICENSE_RESTRICTED",
        "packets": packets,
    })
    _write_json(output_dir / "MISSING_FIELD_MANIFEST.json", manifest)
    _write_json(output_dir / "CALIBRATION_AUDIT_QUEUE.json", calibration_queue)
    _write_json(output_dir / "RESULT.json", result)
    _write_json(output_dir / "RUN_MANIFEST.json", {
        "experiment_id": EXPERIMENT_ID,
        "run_id": output_dir.name,
        "run_date": date.today().isoformat(),
        "input_class": "LICENSE_RESTRICTED",
        "source_review_filename": input_path.name,
        "source_review_sha256": source_sha256,
        "source_review_copied": False,
        "raw_images_included": False,
        "packet_version": IMAGE_REVIEW_PARTIAL_PACKET_VERSION,
        "file_hashes": {
            "converter": _sha256(Path(__file__).resolve()),
            "packet_schema": _sha256(IMAGE_REVIEW_PARTIAL_PACKET_SCHEMA_PATH),
        },
        "deterministic_conversion": True,
        "synthetic_scene_fill_performed": False,
        "claim_scope": CLAIM_SCOPE,
    })
    (output_dir / "REPORT_KO.md").write_text(
        f"""# GuardSynth image-only 검토 → partial scene packet

- 상태: **{result['status']}**
- 입력: 완료된 restricted image-only 검토 {len(packets)}건
- 생성한 partial packet: {len(packets)}건
- source-complete: {manifest['source_complete_packet_count']}/{len(packets)}
- 계약 생성 허용: {manifest['contract_generation_allowed_count']}/{len(packets)}
- 임의 생성한 M13 필수값: {manifest['synthesized_required_value_count']}건
- slot 배정: `UNASSIGNED_REVIEW_REQUIRED`
- 독립 calibration/audit 표본: {calibration_queue['sample_count']}건, 기존 판정 비공개, 재검토 대기
- 주장 범위: `{CLAIM_SCOPE}`

이미지에서 사람이 기록한 값은 `HUMAN_REVIEWED_IMAGE_CLAIM`으로만 보존했다. timestamp,
ego pose/speed, actor track, target–zone association, geometry, coordinate transform, rule source,
vehicle binding과 assurance profile을 이미지로부터 추정하지 않았다. 따라서 모든 packet은
`REVIEW_REQUIRED`이며 GuardSynth/EBLC/Core/Z3 계약 실행 입력으로 사용할 수 없다.

다음 작업은 packet별 association·transform/time·rule applicability·vehicle assurance 근거를
연결하고 24-slot 배정을 심사하는 것이다.
""",
        encoding="utf-8",
    )
    return output_dir, result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output, result = execute(args.input, args.output_dir)
    print(json.dumps({
        "status": result["status"],
        "decision": result["decision"],
        "output": output.relative_to(ROOT).as_posix(),
        "packet_count": result["metrics"]["packet_count"],
    }, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "EXECUTED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
