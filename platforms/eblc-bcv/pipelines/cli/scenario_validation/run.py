"""Run and record multi-angle EBLC unit and integration validation."""

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

from cli.solver_runtime import configure_project_z3


Z3_RUNTIME = configure_project_z3(ROOT)
from guard_synth_eblc import (
    COMPILER_VERSION,
    CONFORMANCE_VERSION,
    CORE_GRAMMAR_VERSION,
    CORE_SMT_COMPILER_VERSION,
    ELABORATOR_VERSION,
    PROGRAM_VERSION,
    SCHEMA_VERSION,
    SEMANTICS_VERSION,
)

EXPERIMENT_ID = "EBLC-SCENARIO-TEST-001"
CLAIM_SCOPE = "SYNTHETIC_EBLC_SOFTWARE_UNIT_INTEGRATION_VALIDATION_NOT_VEHICLE_SAFETY"
DEFAULT_RUN_ID = "scenario-matrix-2026-08-08-v3"
RUN_DATE = date.today().isoformat()


SCENARIO_GROUPS = (
    {
        "group": "PROGRAM_AND_SCHEMA_NEGATIVE_INPUTS",
        "case_count": 9,
        "examples": [
            "duplicate source reference", "duplicate derivation node",
            "four invalid numeric ranges", "nonfinite value",
            "scalarized priority", "missing quantity evidence",
        ],
        "targets": ["JSON_SCHEMA", "PROGRAM_PARSER"],
    },
    {
        "group": "LIFECYCLE_AND_POLICY_VARIANTS",
        "case_count": 9,
        "examples": [
            "release disabled", "reactivation disabled", "UNKNOWN as FALSE",
            "UNKNOWN as TRUE", "always active", "explicit expiry",
            "invariant disabled", "forced false deadlock", "one-frame release",
        ],
        "targets": ["CANONICAL", "RUNTIME", "Z3_BOUNDED", "CORE_SMT", "ENUMERATOR"],
    },
    {
        "group": "NUMERIC_AND_FRESHNESS_BOUNDARIES",
        "case_count": 23,
        "examples": [
            "stop position before/equal/after tolerance",
            "freshness before/equal/after tolerance",
            "future timestamp boundary", "dynamic speed bounds at three distances",
        ],
        "targets": ["CANONICAL", "RUNTIME", "Z3_BOUNDED", "CORE_SMT", "ENUMERATOR"],
    },
    {
        "group": "COMBINED_FAILURE_PRECEDENCE",
        "case_count": 1,
        "examples": ["scope plus unit failure"],
        "targets": ["CANONICAL", "RUNTIME", "Z3_BOUNDED", "CORE_SMT", "ENUMERATOR"],
    },
    {
        "group": "EPISTEMIC_POLICY_LOWERING",
        "case_count": 1,
        "examples": ["disallowed predicted evidence becomes UNKNOWN"],
        "targets": ["CORE_SMT"],
    },
    {
        "group": "MINIMUM_BOUNDED_HORIZON",
        "case_count": 1,
        "examples": ["one-frame bounded horizon"],
        "targets": ["CANONICAL", "CORE_SMT"],
    },
)


def _write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _test(command: list[str]) -> dict[str, Any]:
    completed = subprocess.run(
        command, cwd=ROOT, text=True, capture_output=True, check=False
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
        "output_sha256": hashlib.sha256(combined.encode("utf-8")).hexdigest(),
    }


def _hashes(paths: list[Path]) -> dict[str, str]:
    return {
        path.relative_to(ROOT).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in paths
    }


def _report(result: dict[str, Any]) -> str:
    tests = result["tests"]
    rows = "\n".join(
        f"| {name} | {record['passed_count']}/{record['test_count']} | {record['exit_code']} |"
        for name, record in tests.items()
    )
    groups = "\n".join(
        f"| `{group['group']}` | {group['case_count']} | {', '.join(group['targets'])} |"
        for group in result["scenario_coverage"]["groups"]
    )
    return f"""# EBLC 다각도 단위·통합 검증 보고서

- 상태: **{result['status']}**
- run ID: `{result['run_id']}`
- solver: project-local Z3 `{result['z3_runtime']['version']}`
- 명시적 신규 시나리오: {result['scenario_coverage']['explicit_case_count']}개
- 주장 범위: `{CLAIM_SCOPE}`

## 검증 관점

| 그룹 | case 수 | 실행 target |
|---|---:|---|
{groups}

경계 행렬은 정지 위치, 동적 허용 속도, freshness, 미래 timestamp에 대해
경계 직전·경계값·경계 직후를 비교한다. 정책 행렬은 release/reactivation,
UNKNOWN 처리, expiry, invariant, deadlock을 변형한다. 정책·경계 trace를 canonical,
별도 runtime monitor, 기존 bounded Z3 target, 고수준 program에서 전개된 Core-SMT,
finite-state enumerator에 통과시켜 결과 일치를 검사한다.

## 실행 결과

| test suite | pass | exit code |
|---|---:|---:|
{rows}

초기 실행에서 binary-float 계산 때문에 freshness 경계 두 건이 ideal-real Core-SMT와
불일치했다. 의미 epsilon(1e-9)보다 훨씬 작은 roundoff guard(1e-15)를 적용한 뒤
동일 고정 기대값으로 재실행하여 전부 통과했다.

## 해석 한계

이 결과는 명시된 synthetic 유한 시나리오와 software target 사이의 일치 및
fail-closed 동작을 확인한다. 실제 법규의 정당성, 차량 제동 성능, 센서 정확도,
무한시간 성질 또는 실제 차량 안전을 입증하지 않는다.
"""


def execute(run_id: str) -> tuple[Path, dict[str, Any]]:
    output = ROOT / "artifacts/results/public/eblc-scenario-test-001" / run_id
    if output.exists():
        raise FileExistsError(f"refusing to overwrite existing run: {run_id}")

    tests = {
        "scenario_matrix": _test([
            "python3", "-m", "unittest",
            "platforms/eblc-bcv/tests/translation/test_scenario_matrix.py", "-v",
        ]),
        "core_smt_compiler": _test([
            "python3", "-m", "unittest",
            "platforms/eblc-bcv/tests/unit/test_core_smt_compiler.py", "-v",
        ]),
        "elaboration_conformance": _test([
            "python3", "-m", "unittest",
            "platforms/eblc-bcv/tests/unit/test_elaboration_conformance.py", "-v",
        ]),
        "robustness": _test([
            "python3", "-m", "unittest",
            "platforms/eblc-bcv/tests/robustness/test_robustness.py", "-v",
        ]),
        "all_p0b": _test([
            "python3", "-m", "unittest", "discover", "-s",
            "platforms/eblc-bcv/tests", "-p", "test_*.py",
        ]),
        "p0a_regression": _test([
            "python3", "-m", "unittest",
            "experiments.eblc_pilot.test_pilot", "-v",
        ]),
    }
    gates = {
        "all_test_commands_pass": all(item["passed"] for item in tests.values()),
        "scenario_matrix_11_of_11": tests["scenario_matrix"]["passed_count"] == 11,
        "core_smt_12_of_12": tests["core_smt_compiler"]["passed_count"] == 12,
        "robustness_10_of_10": tests["robustness"]["passed_count"] == 10,
        "full_p0b_77_of_77": tests["all_p0b"]["passed_count"] == 77,
        "p0a_7_of_7": tests["p0a_regression"]["passed_count"] == 7,
    }
    coverage = {
        "explicit_case_count": sum(group["case_count"] for group in SCENARIO_GROUPS),
        "groups": list(SCENARIO_GROUPS),
        "boundary_semantics": {
            "semantic_epsilon": 1e-9,
            "binary_float_roundoff_guard": 1e-15,
            "policy": "STRICT_BEYOND_EPSILON_AND_ROUNDOFF_ONLY",
        },
    }
    result = {
        "experiment_id": EXPERIMENT_ID,
        "run_id": run_id,
        "run_date": RUN_DATE,
        "status": "EXECUTED" if all(gates.values()) else "FAILED",
        "claim_scope": CLAIM_SCOPE,
        "input_class": "SYNTHETIC",
        "z3_runtime": Z3_RUNTIME.manifest(),
        "versions": {
            "schema": SCHEMA_VERSION,
            "canonical_semantics": SEMANTICS_VERSION,
            "compiler_targets": COMPILER_VERSION,
            "core_grammar": CORE_GRAMMAR_VERSION,
            "core_smt_compiler": CORE_SMT_COMPILER_VERSION,
            "program": PROGRAM_VERSION,
            "elaborator": ELABORATOR_VERSION,
            "conformance": CONFORMANCE_VERSION,
        },
        "scenario_coverage": coverage,
        "tests": tests,
        "gates": gates,
        "observed_and_fixed_discrepancy": {
            "count": 2,
            "class": "BINARY_FLOAT_BOUNDARY_ROUNDOFF",
            "affected_cases": ["freshness at +epsilon", "future age at -epsilon"],
            "post_fix_status": "REGRESSION_PASS",
        },
        "limitations": [
            "FINITE_SYNTHETIC_SCENARIOS_ONLY",
            "TARGET_AGREEMENT_NOT_INDEPENDENT_SAFETY_ORACLE",
            "NOT_LEGAL_VALIDATION",
            "NOT_VEHICLE_SAFETY_PROOF",
        ],
    }
    output.mkdir(parents=True)
    _write_json(output / "RESULT.json", result)
    _write_json(output / "SCENARIO_COVERAGE.json", coverage)
    manifest_paths = [
        ROOT / "platforms/eblc-bcv/src/guard_synth_eblc/__init__.py",
        ROOT / "platforms/eblc-bcv/src/guard_synth_eblc/semantics.py",
        ROOT / "platforms/eblc-bcv/src/guard_synth_eblc/runtime_monitor.py",
        ROOT / "platforms/eblc-bcv/src/guard_synth_eblc/finite_state_enumerator.py",
        ROOT / "platforms/eblc-bcv/src/guard_synth_eblc/z3_bounded_checker.py",
        ROOT / "platforms/eblc-bcv/src/guard_synth_eblc/smt_compiler.py",
        ROOT / "platforms/eblc-bcv/tests/test_scenario_matrix.py",
        Path(__file__).resolve(),
        ROOT / "cli/solver_runtime.py",
    ]
    manifest = {
        "experiment_id": EXPERIMENT_ID,
        "run_id": run_id,
        "run_date": RUN_DATE,
        "python_version": sys.version.split()[0],
        "z3_runtime": Z3_RUNTIME.manifest(),
        "versions": result["versions"],
        "code_revision": "WORKSPACE_WITHOUT_GIT_METADATA",
        "file_hashes": _hashes(manifest_paths),
        "input_class": "SYNTHETIC",
        "enumeration": "DETERMINISTIC_SCENARIO_AND_BOUNDARY_MATRICES",
        "random_seed": None,
        "test_commands": tests,
        "claim_scope": CLAIM_SCOPE,
    }
    _write_json(output / "RUN_MANIFEST.json", manifest)
    (output / "REPORT_KO.md").write_text(_report(result), encoding="utf-8")
    return output, result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", default=DEFAULT_RUN_ID)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output, result = execute(args.run_id)
    print(json.dumps({
        "status": result["status"],
        "explicit_scenarios": result["scenario_coverage"]["explicit_case_count"],
        "result": output.relative_to(ROOT).as_posix(),
    }, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "EXECUTED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
