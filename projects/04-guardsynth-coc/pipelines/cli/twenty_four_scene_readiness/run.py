"""Assess the locked 24-slot real-scene dry-run input readiness."""

from __future__ import annotations

import argparse
from datetime import date
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from cli.project_paths import project_root


ROOT = project_root(__file__)
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from guard_synth.dry_run_readiness import assess_dry_run_readiness
from guard_synth.source_catalog import KR_FIXTURE_PATH, load_source_catalog


EXPERIMENT_ID = "GUARDSYNTH-24-SCENE-DRY-RUN-001"
DEFAULT_RUN_ID = "kr-dry-run-readiness-2026-08-10-v1"
LEGACY_PUBLIC_RESULT = ROOT / "artifacts/results/public/guardsynth-real-scene-readiness-001/terminal-readiness-2026-08-09-v3/RESULT.json"
CLAIM_SCOPE = "M13_SLOT_AND_INPUT_READINESS_NOT_REAL_SCENE_EXECUTION_ASSOCIATION_ACCURACY_OR_VEHICLE_SAFETY"


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _test(command: list[str]) -> dict[str, Any]:
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(SRC) + os.pathsep + str(ROOT)
    completed = subprocess.run(
        command, cwd=ROOT, env=environment, text=True, capture_output=True, check=False
    )
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
    current = readiness["input_readiness"]
    tests = result["tests"]
    return f"""# GuardSynth 24-scene dry-run 준비도 보고서

- 실행 상태: **{result['status']}**
- 단계 판단: **{result['decision']}**
- planned slot: {readiness['slot_count']}개 ({readiness['slots_per_slice']}개/slice)
- 기존 실제 후보: {current['actual_candidate_event_count']}개
- adapter partial 후보: {current['adapted_candidate_count']}개
- source-complete: {current['source_complete_scene_count']}/{current['source_complete_required']}
- 실제 scene EBLC/Core/Z3 실행: {readiness['execution']['guardsynth_eblc_core_z3_scene_runs']}건
- synthetic fill: {current['synthetic_scene_fill_performed']}
- 주장 범위: `{CLAIM_SCOPE}`

## 실행한 것

pedestrian/cyclist, stop/signals, following/cut-in에 각각 8개 slot을 배정하고 visible hazard,
occlusion/reappearance, nominal clear, release/reactivation strata를 고정했다. M12 대한민국
catalog 15개 규칙은 준비 gate를 통과했다.

## 중단된 것

기존 제한 파생 데이터 집계는 후보 5개와 partial adapter 4개만 보여 주며 source-complete
장면은 0개다. target-zone/lane association, 검증된 좌표 변환, 정확한 차량 binding과
source-bearing assurance profile이 없으므로 실제 계약 생성이나 Z3 scene run을 수행하지
않았다. 빈 slot을 synthetic 값으로 채우지 않았다.

## 테스트

- 24-slot readiness 집중: {tests['focused']['passed_count']}/{tests['focused']['test_count']}
- 전체 maintained: {tests['full']['passed_count']}/{tests['full']['test_count']}
- P0a 회귀: {tests['p0a']['passed_count']}/{tests['p0a']['test_count']}
- 구조/문서 링크: {tests['structure']['passed_count']}/{tests['structure']['test_count']}

다음 단계는 더 많은 EBLC 문법이 아니라, 24개 slot에 들어갈 source-complete 실제 scene
packet과 vehicle assurance를 확보·작성하는 것이다.
"""


def execute(run_id: str) -> tuple[Path, dict[str, Any]]:
    output = ROOT / "artifacts/results/public/guardsynth-24-scene-dry-run-001" / run_id
    if output.exists():
        raise FileExistsError(f"refusing to overwrite existing run: {run_id}")
    output.mkdir(parents=True)
    readiness = assess_dry_run_readiness(
        load_source_catalog(KR_FIXTURE_PATH), _load(LEGACY_PUBLIC_RESULT)
    )
    python = "/usr/bin/python3"
    tests = {
        "focused": _test([python, "-m", "unittest", "projects/04-guardsynth-coc/tests/unit/test_dry_run_readiness.py", "projects/04-guardsynth-coc/tests/unit/test_source_catalog.py", "-v"]),
        "full": _test([python, "-m", "unittest", "discover", "-s", "projects/04-guardsynth-coc/tests", "-p", "test_*.py", "-v"]),
        "p0a": _test([python, "-m", "unittest", "experiments.eblc_pilot.test_pilot", "-v"]),
        "structure": _test([python, "-m", "unittest", "tests.structure.test_project_layout", "-v"]),
    }
    software_gate = all(item["passed"] for item in tests.values()) and readiness["catalog_gate"]["ready"]
    result = {
        "experiment_id": EXPERIMENT_ID,
        "run_id": run_id,
        "run_date": str(date.today()),
        "status": "PARTIAL" if software_gate else "FAILED",
        "decision": readiness["decision"] if software_gate else "M13_READINESS_SOFTWARE_REWORK",
        "readiness": readiness,
        "tests": tests,
        "claim_scope": CLAIM_SCOPE,
    }
    _write_json(output / "DRY_RUN_PLAN.json", {"slot_plan": readiness["slot_plan"], "required_scene_fields": readiness["required_scene_fields"]})
    _write_json(output / "REAL_SCENE_DATA_GAP.json", {"decision": readiness["decision"], "blockers": readiness["blockers"], "input_readiness": readiness["input_readiness"]})
    _write_json(output / "RESULT.json", result)
    _write_json(output / "RUN_MANIFEST.json", {
        "experiment_id": EXPERIMENT_ID,
        "run_id": run_id,
        "run_date": str(date.today()),
        "input_class": "PUBLIC_AGGREGATES_OF_LICENSE_RESTRICTED_DERIVED_INPUT",
        "raw_identifiers_included": False,
        "catalog_sha256": hashlib.sha256(KR_FIXTURE_PATH.read_bytes()).hexdigest(),
        "legacy_public_aggregate_sha256": hashlib.sha256(LEGACY_PUBLIC_RESULT.read_bytes()).hexdigest(),
        "synthetic_scene_fill_performed": False,
        "tests": tests,
        "claim_scope": CLAIM_SCOPE,
    })
    (output / "REPORT_KO.md").write_text(_report(result), encoding="utf-8")
    return output, result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", default=DEFAULT_RUN_ID)
    args = parser.parse_args()
    output, result = execute(args.run_id)
    print(json.dumps({"output": str(output), "status": result["status"], "decision": result["decision"]}, ensure_ascii=False))
    return 0 if result["status"] == "PARTIAL" else 1


if __name__ == "__main__":
    raise SystemExit(main())
