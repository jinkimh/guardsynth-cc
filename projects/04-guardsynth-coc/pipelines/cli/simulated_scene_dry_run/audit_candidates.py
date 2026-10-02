"""Create the restricted candidate inventory for M13 simulation-24."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

from cli.project_paths import project_root


ROOT = project_root(__file__)
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from guard_synth.simulated_scene_inventory import build_scene_candidate_inventory


DEFAULT_PACKETS = ROOT / (
    "artifacts/results/restricted/guardsynth-image-review-partial-scene-001/"
    "alpamayo-image-review-2026-08-11-v2/PARTIAL_SCENE_PACKETS.json"
)
DEFAULT_ADAPTER = ROOT / (
    "artifacts/results/restricted/eblc-p0b-001/"
    "p0b-data-adapter-2026-08-11-v2-all-candidates/ADAPTER_RESULT.json"
)
DEFAULT_AUDIT = ROOT / (
    "artifacts/results/restricted/guardsynth-calibration-scene-source-audit-001/"
    "alpamayo-calibration-source-2026-08-11-v17-rule-applicability/"
    "CALIBRATION_SOURCE_AUDIT.json"
)


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def execute(
    packets: Path,
    adapter: Path,
    audit: Path,
    output_dir: Path,
    *,
    event_closures: tuple[Path, ...] = (),
) -> dict:
    if output_dir.exists():
        raise FileExistsError(f"refusing to overwrite existing output: {output_dir}")
    result = build_scene_candidate_inventory(
        _load(packets),
        _load(adapter),
        _load(audit),
        event_closures=[_load(path) for path in event_closures],
    )
    output_dir.mkdir(parents=True)
    (output_dir / "SCENE_CANDIDATE_INVENTORY.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    manifest = {
        "experiment_id": "GUARDSYNTH-SIM24-CANDIDATE-AUDIT-001",
        "run_id": output_dir.name,
        "input_class": "LICENSE_RESTRICTED_DERIVED",
        "input_hashes": {
            "partial_packets": _sha256(packets),
            "adapter_result": _sha256(adapter),
            "calibration_audit": _sha256(audit),
            "event_closures": [_sha256(path) for path in event_closures],
        },
        "raw_identifiers_included": False,
        "synthetic_scene_fill_performed": False,
        "claim_scope": result["claim_scope"],
    }
    (output_dir / "RUN_MANIFEST.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (output_dir / "REPORT_KO.md").write_text(
        "# M13 simulation-24 장면 후보 감사\n\n"
        f"- 중복 제거 후보: **{result['candidate_count']}개**\n"
        f"- 장면 근거 8/8 준비: **{result['simulation_projection_ready_count']}개**\n"
        f"- 추가 필요: **{result['additional_ready_candidates_needed']}개**\n"
        f"- 판단: **{result['decision']}**\n\n"
        "실제 차량 assurance는 이 감사의 입력이나 gate가 아니다. 장면 근거가 부족한 후보는 "
        "가상 값으로 채우지 않았으며, 이 결과는 차량 안전성 또는 장면 해석 정확도 증거가 아니다.\n",
        encoding="utf-8",
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packets", type=Path, default=DEFAULT_PACKETS)
    parser.add_argument("--adapter", type=Path, default=DEFAULT_ADAPTER)
    parser.add_argument("--audit", type=Path, default=DEFAULT_AUDIT)
    parser.add_argument("--event-closure", type=Path, action="append", default=[])
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    result = execute(
        args.packets,
        args.adapter,
        args.audit,
        args.output_dir,
        event_closures=tuple(args.event_closure),
    )
    print(json.dumps({key: result[key] for key in (
        "candidate_count",
        "simulation_projection_ready_count",
        "additional_ready_candidates_needed",
        "decision",
    )}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
