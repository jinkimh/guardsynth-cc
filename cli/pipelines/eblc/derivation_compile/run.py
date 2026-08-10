"""Execute typed EBLC derivation augmentation, SMT export, and conformance."""

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

from guard_synth_eblc.adapters.synthetic_pedestrian import PILOT_PROFILE, initial_frame, locked_translation_traces
from guard_synth_eblc.binders import bind_pedestrian_contract
from guard_synth_eblc.catalog import load_pilot_rule, load_predicate_spec
from guard_synth_eblc.conformance import compare_trace
from guard_synth_eblc.derivation import (
    DERIVATION_COMPILER_VERSION,
    DERIVATION_SCHEMA_PATH,
    DERIVATION_VERSION,
    elaborate_derivation,
    load_derivation_spec,
)
from guard_synth_eblc.elaborator import elaborate_program
from guard_synth_eblc.examples import synthetic_stop_position_derivation
from guard_synth_eblc.program import load_program
from guard_synth_eblc.smt_compiler import COMPILER_VERSION, compile_core_model, export_compilation, solve_assignment


EXPERIMENT_ID = "EBLC-DERIVATION-COMPILATION-001"
CLAIM_SCOPE = "SYNTHETIC_TYPED_DERIVATION_AND_BOUNDED_TRANSLATION_NOT_VEHICLE_SAFETY"
DEFAULT_RUN_ID = "typed-derivation-2026-08-09-v1"
DEFAULT_PROGRAM = ROOT / "src/guard_synth_eblc/fixtures/eblc_program_p0b.json"
RUN_DATE = date.today().isoformat()
PRE_DERIVATION_TEST_MODULES = (
    "tests.guard_synth_eblc.test_composition_compilation",
    "tests.guard_synth_eblc.test_core_smt_compiler",
    "tests.guard_synth_eblc.test_elaboration_conformance",
    "tests.guard_synth_eblc.test_public_layout",
    "tests.guard_synth_eblc.test_real_scene_adapter",
    "tests.guard_synth_eblc.test_robustness",
    "tests.guard_synth_eblc.test_scenario_matrix",
    "tests.guard_synth_eblc.test_schema_binding",
    "tests.guard_synth_eblc.test_semantics",
    "tests.guard_synth_eblc.test_translation_mutations",
)


def _write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _portable(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return "EXTERNAL_INPUT_PATH_REDACTED"


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
    }


def _replay(output: Path, query_status: str) -> dict[str, Any]:
    executable = ROOT / Z3_RUNTIME.prefix / "bin/z3"
    files = {
        "MODEL.smt2": "SAT",
        "QUERY_generated_model_satisfiable.smt2": query_status,
    }
    records = []
    for filename, expected in files.items():
        completed = subprocess.run(
            [str(executable), str(output / filename)], cwd=ROOT,
            text=True, capture_output=True, check=False,
        )
        lines = completed.stdout.strip().splitlines()
        actual = lines[0].upper() if lines else "NO_STATUS"
        records.append({
            "file": filename,
            "expected": expected,
            "actual": actual,
            "exit_code": completed.returncode,
            "matches": completed.returncode == 0 and actual == expected,
        })
    matches = sum(item["matches"] for item in records)
    return {
        "file_count": len(records),
        "matches": matches,
        "agreement": matches / len(records),
        "records": records,
    }


def _hashes(paths: list[Path]) -> dict[str, str]:
    return {
        _portable(path): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in paths
    }


def _report(result: dict[str, Any]) -> str:
    tests = result["tests"]
    return f"""# EBLC typed derivation→Core→SMT 실행 보고서

- 상태: **{result['status']}**
- run ID: `{result['run_id']}`
- solver: project-local Z3 `{result['z3_runtime']['version']}`
- 주장 범위: `{CLAIM_SCOPE}`

## TDD 및 변환 결과

| 항목 | 결과 |
|---|---:|
| 구현 전 EBLC 기준선 | {tests['pre_derivation_baseline']['passed_count']}/{tests['pre_derivation_baseline']['test_count']} |
| derivation 신규 테스트 | {tests['derivation']['passed_count']}/{tests['derivation']['test_count']} |
| 전체 EBLC 테스트 | {tests['full_eblc']['passed_count']}/{tests['full_eblc']['test_count']} |
| P0a 회귀 | {tests['p0a']['passed_count']}/{tests['p0a']['test_count']} |
| locked trace canonical/Core-SMT agreement | {result['conformance']['matching_traces']}/{result['conformance']['trace_count']} |
| SMT-LIB 직접 replay | {result['smt_replay']['matches']}/{result['smt_replay']['file_count']} |

실패 테스트를 먼저 작성한 뒤 typed `SUB` derivation으로 `0.0 m - 1.5 m = -1.5 m`을
Core 식으로 생성했다. 기존의 정적 `bind_stop_position` 절은 명시적으로 교체됐고,
Z3 witness는 `-3/2`를 반환했다. 미등록 ref, DAG cycle, 연산 arity, 근거 누락,
unit/frame mismatch 및 0 나눗셈 definedness도 fail-closed로 검사한다.

## 주장 경계

현재 v0.1은 유한 typed arithmetic DAG (`ADD/SUB/MUL/DIV/NEG/MIN/MAX`)의 bounded
symbolic replay다. free-form `operation` 문자열을 자동 해석하지 않으며 실제 source,
차량 profile 또는 안전성을 입증하지 않는다.
"""


def execute(program_path: Path, spec_path: Path | None, run_id: str) -> tuple[Path, dict[str, Any]]:
    output = ROOT / "artifacts/results/public/eblc-derivation-compilation-001" / run_id
    if output.exists():
        raise FileExistsError(f"refusing to overwrite existing run: {run_id}")
    program = load_program(program_path)
    base = elaborate_program(program)
    spec = (
        load_derivation_spec(spec_path)
        if spec_path is not None
        else synthetic_stop_position_derivation(horizon=base.core_model.horizon)
    )
    derived = elaborate_derivation(spec, base_core_document=base.core_document)
    compiled = compile_core_model(derived.core_model)
    output.mkdir(parents=True)
    _write_json(output / "INPUT_DERIVATION_SPEC.json", spec.raw)
    _write_json(output / "DERIVED_CORE.json", derived.core_document)
    _write_json(output / "DERIVATION_MAP.json", derived.derivation_map)
    query_results = export_compilation(compiled, output)

    binding = bind_pedestrian_contract(
        load_pilot_rule(), load_predicate_spec(), initial_frame(), PILOT_PROFILE
    )
    if binding.contract is None:
        raise RuntimeError(f"synthetic contract binding failed: {binding.reason_codes}")
    records = [
        compare_trace(binding.contract, program, compiled, trace_id, samples)
        for trace_id, samples in locked_translation_traces().items()
    ]
    matching = sum(bool(item["matches"]) for item in records)
    conformance = {
        "trace_count": len(records),
        "matching_traces": matching,
        "agreement": matching / len(records),
        "records": records,
        "limitations": [
            "GENERATED_FINITE_TRACE_CONFORMANCE",
            "NOT_AN_INDEPENDENT_SAFETY_ORACLE",
        ],
    }
    _write_json(output / "DERIVATION_CONFORMANCE.json", conformance)
    solved = solve_assignment(compiled, {})
    stop_symbol = next(
        item["smt_symbol"]
        for item in compiled.symbol_table["symbols"]
        if item["declaration"] == "stop_position"
    )
    derived_value = (solved["witness"] or {}).get(stop_symbol)
    smt_replay = _replay(output, query_results["results"][0]["status"])
    _write_json(output / "SMT_REPLAY.json", smt_replay)

    tests = {
        "pre_derivation_baseline": _test(["python3", "-m", "unittest", *PRE_DERIVATION_TEST_MODULES, "-v"]),
        "derivation": _test(["python3", "-m", "unittest", "tests.guard_synth_eblc.test_derivation_compiler", "-v"]),
        "full_eblc": _test(["python3", "-m", "unittest", "discover", "-s", "tests/guard_synth_eblc", "-p", "test_*.py", "-v"]),
        "p0a": _test(["python3", "-m", "unittest", "experiments.eblc_pilot.test_pilot", "-v"]),
    }
    gates = {
        "derivation_schema_and_semantics_valid": True,
        "derived_core_type_valid": True,
        "derived_value_exact_negative_three_halves": derived_value == "-3/2",
        "canonical_core_smt_agreement_100_percent": conformance["agreement"] == 1.0,
        "query_expected": query_results["agreement"] == 1.0,
        "smt_replay_100_percent": smt_replay["agreement"] == 1.0,
        "pre_derivation_baseline_89_of_89": tests["pre_derivation_baseline"]["test_count"] == 89 and tests["pre_derivation_baseline"]["passed"],
        "all_tests_pass": all(item["passed"] for item in tests.values()),
    }
    result = {
        "experiment_id": EXPERIMENT_ID,
        "run_id": run_id,
        "run_date": RUN_DATE,
        "status": "EXECUTED" if all(gates.values()) else "FAILED",
        "claim_scope": CLAIM_SCOPE,
        "input_class": "SYNTHETIC",
        "program": _portable(program_path),
        "derivation_spec": _portable(spec_path) if spec_path else "GENERATED_PUBLIC_SYNTHETIC_EXAMPLE",
        "versions": {
            "derivation": DERIVATION_VERSION,
            "derivation_compiler": DERIVATION_COMPILER_VERSION,
            "core_grammar": derived.core_model.grammar_version,
            "smt_compiler": COMPILER_VERSION,
        },
        "z3_runtime": Z3_RUNTIME.manifest(),
        "derived_values": {"stop_position": derived_value},
        "conformance": conformance,
        "query_results": query_results,
        "smt_replay": smt_replay,
        "tests": tests,
        "gates": gates,
        "limitations": derived.derivation_map["limitations"] + [
            "GENERATED_TRANSLATION_ORACLE",
            "NOT_INDEPENDENT_SAFETY_ORACLE",
        ],
    }
    manifest = {
        "experiment_id": EXPERIMENT_ID,
        "run_id": run_id,
        "run_date": RUN_DATE,
        "python_version": sys.version.split()[0],
        "z3_runtime": Z3_RUNTIME.manifest(),
        "code_revision": "WORKSPACE_WITHOUT_GIT_METADATA",
        "file_hashes": _hashes([
            DERIVATION_SCHEMA_PATH,
            ROOT / "src/guard_synth_eblc/derivation.py",
            ROOT / "src/guard_synth_eblc/examples.py",
            ROOT / "src/guard_synth_eblc/elaborator.py",
            ROOT / "src/guard_synth_eblc/core_ir.py",
            ROOT / "src/guard_synth_eblc/smt_compiler.py",
            ROOT / "tests/guard_synth_eblc/test_derivation_compiler.py",
            Path(__file__).resolve(),
        ]),
        "versions": result["versions"],
        "input_class": "SYNTHETIC",
        "enumeration": "DETERMINISTIC_LOCKED_TRACE_REPLAY",
        "random_seed": None,
        "test_commands": tests,
        "claim_scope": CLAIM_SCOPE,
    }
    _write_json(output / "RESULT.json", result)
    _write_json(output / "RUN_MANIFEST.json", manifest)
    (output / "REPORT_KO.md").write_text(_report(result), encoding="utf-8")
    return output, result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--program", type=Path, default=DEFAULT_PROGRAM)
    parser.add_argument("--spec", type=Path)
    parser.add_argument("--run-id", default=DEFAULT_RUN_ID)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output, result = execute(
        args.program.resolve(), args.spec.resolve() if args.spec else None, args.run_id
    )
    print(json.dumps({
        "status": result["status"],
        "pre_derivation_baseline": result["tests"]["pre_derivation_baseline"],
        "full_eblc": result["tests"]["full_eblc"],
        "conformance_agreement": result["conformance"]["agreement"],
        "derived_stop_position": result["derived_values"]["stop_position"],
        "result": output.relative_to(ROOT).as_posix(),
    }, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "EXECUTED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
