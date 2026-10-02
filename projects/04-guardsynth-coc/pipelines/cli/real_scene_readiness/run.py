"""Freeze the P0b real-scene readiness decision without fabricating inputs."""

from __future__ import annotations

import argparse
from datetime import date
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
from typing import Any

from cli.project_paths import project_root


ROOT = project_root(__file__)
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from guard_synth.assurance_registry import load_assurance_registry
from guard_synth.source_authoring import assess_scene_readiness
from guard_synth_eblc.schema_validation import load_json


EXPERIMENT_ID = "GUARDSYNTH-REAL-SCENE-READINESS-001"
DEFAULT_RUN_ID = "terminal-readiness-2026-08-09-v1"
DEFAULT_ADAPTER_RESULT = ROOT / "artifacts/results/restricted/eblc-p0b-001/p0b-restricted-grounding-multiview-2026-08-08-v1/ADAPTER_RESULT.json"
DEFAULT_REGISTRY = ROOT / "projects/04-guardsynth-coc/src/guard_synth/fixtures/vehicle_assurance_registry_empty_v0_1.json"
CLAIM_SCOPE = "SOURCE_READINESS_AND_ABSTENTION_NOT_REAL_SCENE_CONTRACT_OR_VEHICLE_SAFETY"


def _write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _run_test(command: list[str]) -> dict[str, Any]:
    completed = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=False)
    combined = completed.stdout + "\n" + completed.stderr
    match = re.search(r"Ran (\d+) tests?", combined)
    count = int(match.group(1)) if match else None
    return {
        "command": " ".join(command),
        "exit_code": completed.returncode,
        "test_count": count,
        "passed_count": count if completed.returncode == 0 else 0,
        "passed": completed.returncode == 0,
    }


def _report(result: dict[str, Any]) -> str:
    readiness = result["readiness"]
    tests = result["tests"]
    return f"""# GuardSynth P0b 종료 준비도 보고서

- 상태: **{result['status']}**
- 최종 판단: **{result['decision']}**
- 실제/파생 후보 event: {readiness['actual_candidate_event_count']}/24
- source-complete scene: {readiness['source_complete_scene_count']}/24
- 실제 24-scene 계약 실행 완료: {readiness['twenty_four_scene_execution_completed']}
- synthetic scene 보충: {readiness['synthetic_scene_fill_performed']}
- 주장 범위: `{CLAIM_SCOPE}`

## 해석

이 실행은 24개의 실제 장면을 검증했다고 주장하지 않는다. 현재 로컬에서 확인된
후보 5개를 점검하고, 나머지 {readiness['missing_scene_input_slot_count']}개 slot은
`MISSING_SCENE_INPUT`으로 남겼다. 부분 ContextGraph {readiness['adapted_candidate_count']}개도
association, 검증된 좌표 변환 및 source-bearing vehicle assurance가 부족하여 실행 가능한
EBLC로 승격하지 않았다.

## 주요 data gap

{chr(10).join(f"- `{key}`: {value}" for key, value in readiness['reason_code_counts'].items())}

## 회귀 테스트

- source authoring: {tests['source_authoring']['passed_count']}/{tests['source_authoring']['test_count']}
- source-boundary adversarial: {tests['source_boundary_adversarial']['passed_count']}/{tests['source_boundary_adversarial']['test_count']}
- 전체 테스트: {tests['full']['passed_count']}/{tests['full']['test_count']}
- 구조/링크: {tests['structure']['passed_count']}/{tests['structure']['test_count']}

## 종료 판정

현재 software path는 source-complete 입력이 주어졌을 때 GuardSynth→EBLC 생성을 수행하고,
불완전한 입력에는 fail-closed로 중단한다. 막힌 부분은 EBLC 언어 구현 반복이 아니라
외부 입력 authoring이다. 다음 연구 단계는 새로운 언어 기능이 아니라 association annotation,
rig→ego-path transform 검증, 차량 validation/assurance source 확보 후 24개 장면을 채우는 것이다.
"""


def execute(adapter_path: Path, registry_path: Path, run_id: str) -> tuple[Path, Path, dict[str, Any]]:
    restricted = ROOT / "artifacts/results/restricted/guardsynth-real-scene-readiness-001" / run_id
    public = ROOT / "artifacts/results/public/guardsynth-real-scene-readiness-001" / run_id
    if restricted.exists() or public.exists():
        raise FileExistsError(f"refusing to overwrite run: {run_id}")
    restricted.mkdir(parents=True, mode=0o700)
    public.mkdir(parents=True)

    adapter = load_json(adapter_path)
    registry = load_assurance_registry(registry_path)
    readiness = assess_scene_readiness(adapter, registry, target_slots=24)

    # Create the report before structure/link tests so the run is visible to
    # checks that inspect referenced output paths.
    preliminary = {
        "status": "EXECUTED",
        "decision": readiness["decision"],
        "readiness": readiness,
        "tests": {
            "source_authoring": {"passed_count": 0, "test_count": 0},
            "source_boundary_adversarial": {"passed_count": 0, "test_count": 0},
            "full": {"passed_count": 0, "test_count": 0},
            "structure": {"passed_count": 0, "test_count": 0},
        },
    }
    (public / "REPORT_KO.md").write_text(_report(preliminary), encoding="utf-8")
    tests = {
        "source_authoring": _run_test([sys.executable, "-m", "unittest", "projects/04-guardsynth-coc/tests/unit/test_source_authoring.py", "-v"]),
        "source_boundary_adversarial": _run_test([sys.executable, "-m", "unittest", "projects/04-guardsynth-coc/tests/unit/test_source_authoring_adversarial.py", "-v"]),
        "full": _run_test([sys.executable, "-m", "unittest", "discover", "-s", "projects/04-guardsynth-coc/tests", "-p", "test_*.py", "-v"]),
        "structure": _run_test([sys.executable, "-m", "unittest", "tests.structure.test_project_layout", "-v"]),
    }
    all_tests_pass = all(item["passed"] for item in tests.values())
    status = "EXECUTED" if all_tests_pass else "FAILED"
    decision = readiness["decision"] if all_tests_pass else "SEMANTICS_REWORK"
    result = {
        "experiment_id": EXPERIMENT_ID,
        "run_id": run_id,
        "run_date": date.today().isoformat(),
        "status": status,
        "decision": decision,
        "readiness": readiness,
        "tests": tests,
        "software_scope_complete": all_tests_pass,
        "current_research_stage_closed": all_tests_pass,
        "remaining_software_task_in_current_scope": None if all_tests_pass else "FIX_FAILED_REGRESSION",
        "external_inputs_required_for_go": [
            "24_SOURCE_COMPLETE_SCENES",
            "UNAMBIGUOUS_TARGET_ZONE_ASSOCIATION",
            "VERIFIED_RIG_TO_EGO_PATH_TRANSFORM",
            "SOURCE_BEARING_VEHICLE_ASSURANCE_PROFILE",
        ],
        "claim_scope": CLAIM_SCOPE,
    }
    _write_json(restricted / "READINESS_MATRIX.json", readiness)
    _write_json(restricted / "REAL_SCENE_DATA_GAP.json", {
        "decision": decision,
        "source_complete_scene_count": readiness["source_complete_scene_count"],
        "reason_code_counts": readiness["reason_code_counts"],
        "raw_identifiers_included": False,
        "synthetic_fill_performed": False,
    })
    _write_json(restricted / "RUN_MANIFEST.json", {
        "experiment_id": EXPERIMENT_ID,
        "run_id": run_id,
        "run_date": date.today().isoformat(),
        "python_version": sys.version.split()[0],
        "input_class": "LICENSE_RESTRICTED",
        "adapter_result_sha256": _sha256(adapter_path),
        "assurance_registry_sha256": _sha256(registry_path),
        "code_revision": "WORKSPACE_WITHOUT_GIT_METADATA",
        "deterministic_readiness_enumeration": True,
        "raw_identifier_output": False,
        "tests": tests,
        "claim_scope": CLAIM_SCOPE,
    })
    public_result = {
        key: value for key, value in result.items() if key != "readiness"
    }
    public_result["readiness_summary"] = {
        key: readiness[key] for key in (
            "slot_count", "actual_candidate_event_count", "adapted_candidate_count",
            "derivation_gap_count", "missing_scene_input_slot_count",
            "source_complete_scene_count", "twenty_four_scene_readiness_gate_passed",
            "twenty_four_scene_execution_completed",
            "synthetic_scene_fill_performed", "reason_code_counts", "decision",
        )
    }
    _write_json(public / "RESULT.json", public_result)
    _write_json(public / "RUN_MANIFEST.json", {
        "experiment_id": EXPERIMENT_ID,
        "run_id": run_id,
        "run_date": date.today().isoformat(),
        "input_class": "LICENSE_RESTRICTED_AGGREGATES_ONLY",
        "restricted_result_path": restricted.relative_to(ROOT).as_posix(),
        "raw_identifiers_included": False,
        "claim_scope": CLAIM_SCOPE,
    })
    (public / "REPORT_KO.md").write_text(_report(result), encoding="utf-8")
    for path in restricted.iterdir():
        path.chmod(0o600)
    return restricted, public, result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run terminal 24-slot real-scene readiness audit.")
    parser.add_argument("--adapter-result", type=Path, default=DEFAULT_ADAPTER_RESULT)
    parser.add_argument("--assurance-registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--run-id", default=DEFAULT_RUN_ID)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    restricted, public, result = execute(args.adapter_result, args.assurance_registry, args.run_id)
    print(json.dumps({
        "status": result["status"],
        "decision": result["decision"],
        "restricted_output": restricted.relative_to(ROOT).as_posix(),
        "public_output": public.relative_to(ROOT).as_posix(),
    }, indent=2))
    return 0 if result["status"] == "EXECUTED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
