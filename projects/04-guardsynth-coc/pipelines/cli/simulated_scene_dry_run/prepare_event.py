#!/usr/bin/env python3
"""Prepare source closure for one derived event and a simulation-only requirement."""

from __future__ import annotations

import argparse
from datetime import date
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

from cli.project_paths import project_root


ROOT = project_root(__file__)
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from guard_synth.simulated_scene_evidence import (
    build_event_scene_source_closure,
    build_system_requirement_applicability,
)


EXPERIMENT_ID = "GUARDSYNTH-SIMULATED-SCENE-EVIDENCE-001"
RESTRICTED_ROOT = ROOT / "artifacts/results/restricted"
DEFAULT_REQUIREMENT = (
    ROOT / "projects/04-guardsynth-coc/src/guard_synth/fixtures/simulated_corridor_requirement_v0_1.json"
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    path.chmod(0o600)


def execute(
    *,
    scene_ref: str,
    adapter_path: Path,
    adapter_candidate_index: int,
    source_bundle_path: Path,
    association_path: Path,
    requirement_path: Path,
    output_dir: Path,
) -> tuple[Path, dict[str, Any]]:
    restricted_inputs = (adapter_path, source_bundle_path, association_path)
    if any(not path.is_file() for path in (*restricted_inputs, requirement_path)):
        raise FileNotFoundError("event evidence input is missing")
    if any(not path.resolve().is_relative_to(ROOT.resolve()) for path in restricted_inputs):
        raise ValueError("restricted evidence must remain inside the project")
    output_dir = output_dir.resolve()
    if not output_dir.is_relative_to(RESTRICTED_ROOT.resolve()):
        raise ValueError("event evidence output must remain under restricted results")
    if output_dir.exists():
        raise FileExistsError(f"refusing to overwrite existing output: {output_dir}")

    adapter = json.loads(adapter_path.read_text(encoding="utf-8"))
    try:
        candidate = adapter["candidates"][adapter_candidate_index]
    except (KeyError, IndexError, TypeError) as exc:
        raise ValueError("ADAPTER_CANDIDATE_NOT_FOUND") from exc
    source_bundle = json.loads(source_bundle_path.read_text(encoding="utf-8"))
    association = json.loads(association_path.read_text(encoding="utf-8"))
    applicability = build_system_requirement_applicability(
        scene_ref=scene_ref,
        association=association,
        requirement_path=requirement_path,
    )

    adapter_sha = _sha256(adapter_path)
    source_bundle_sha = _sha256(source_bundle_path)
    association_sha = _sha256(association_path)
    output_dir.mkdir(parents=True)
    applicability_path = output_dir / "SYSTEM_REQUIREMENT_APPLICABILITY.json"
    _write_json(applicability_path, applicability)
    applicability_sha = _sha256(applicability_path)
    closure = build_event_scene_source_closure(
        scene_ref=scene_ref,
        adapter_candidate=candidate,
        adapter_candidate_index=adapter_candidate_index,
        adapter_sha256=adapter_sha,
        source_bundle=source_bundle,
        source_bundle_sha256=source_bundle_sha,
        association=association,
        association_sha256=association_sha,
        applicability=applicability,
        applicability_sha256=applicability_sha,
    )
    _write_json(output_dir / "SCENE_SOURCE_CLOSURE.json", closure)

    result = {
        "experiment_id": EXPERIMENT_ID,
        "run_id": output_dir.name,
        "run_date": date.today().isoformat(),
        "status": "EXECUTED" if closure["simulation_projection_allowed"] else "PARTIAL",
        "scene_ref": scene_ref,
        "recorded_scene_field_count": len(closure["available_fields"]),
        "recorded_scene_field_required_for_simulation": 8,
        "remaining_real_vehicle_gaps": list(closure["missing_fields"]),
        "simulation_projection_allowed": closure["simulation_projection_allowed"],
        "synthetic_scene_fill_performed": False,
        "legal_authority_claimed": False,
        "vehicle_safety_validated": False,
        "claim_scope": closure["claim_scope"],
    }
    _write_json(output_dir / "RESULT.json", result)
    _write_json(output_dir / "RUN_MANIFEST.json", {
        **result,
        "input_class": "LICENSE_RESTRICTED",
        "deterministic": True,
        "network_or_credential_use_performed_by_this_stage": False,
        "input_hashes": {
            "adapter_result": adapter_sha,
            "scene_source_bundle": source_bundle_sha,
            "association_evidence": association_sha,
            "simulation_system_requirement": _sha256(requirement_path),
        },
        "code_hashes": {
            "scene_evidence_module": _sha256(
                ROOT / "projects/04-guardsynth-coc/src/guard_synth/simulated_scene_evidence.py"
            ),
            "pipeline": _sha256(Path(__file__).resolve()),
        },
    })
    (output_dir / "REPORT_KO.md").write_text(
        f"""# GuardSynth event source closure

- 상태: **{result['status']}**
- 장면: `{scene_ref}`
- simulation 실행에 필요한 실제/파생 장면 근거: **{len(closure['available_fields'])}/8**
- 실제 차량 assurance: **없음 — M21로 이관**
- simulation system requirement 조건부 applicability: **확보**
- 합성 scene field: **0건**

timestamp, ego pose/speed, actor track, geometric SET association, dynamic corridor geometry,
event→model-t0 transform, simulation 전용 system requirement와 recorded-rig binding을 각각
source hash에 연결했다. system requirement는 법규가 아니며 CoC는 관측 사실이나 규범 근거로
사용하지 않았다. 이 closure는 별도 가상 차량 모델 투영을 허용하지만 실제 차량 source closure,
법적 판단, 충돌 예측 또는 차량 안전성을 입증하지 않는다.
""",
        encoding="utf-8",
    )
    return output_dir, result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scene-ref", required=True)
    parser.add_argument("--adapter-result", type=Path, required=True)
    parser.add_argument("--adapter-candidate-index", type=int, required=True)
    parser.add_argument("--source-bundle", type=Path, required=True)
    parser.add_argument("--association", type=Path, required=True)
    parser.add_argument("--requirement", type=Path, default=DEFAULT_REQUIREMENT)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    _, result = execute(
        scene_ref=args.scene_ref,
        adapter_path=args.adapter_result,
        adapter_candidate_index=args.adapter_candidate_index,
        source_bundle_path=args.source_bundle,
        association_path=args.association,
        requirement_path=args.requirement,
        output_dir=args.output_dir,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result["status"] == "EXECUTED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
