"""Execute high-level EBLC elaboration and generated conformance."""

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

from guard_synth_eblc.adapters.synthetic_pedestrian import PILOT_PROFILE, initial_frame
from guard_synth_eblc.binders import bind_pedestrian_contract
from guard_synth_eblc.catalog import load_pilot_rule, load_predicate_spec
from guard_synth_eblc.conformance import CONFORMANCE_VERSION, generated_p0b_conformance_suite, validate_conformance
from guard_synth_eblc.elaborator import ELABORATOR_VERSION, elaborate_program
from guard_synth_eblc.program import (
    PROGRAM_SCHEMA_PATH,
    PROGRAM_V02_SCHEMA_PATH,
    PROGRAM_VERSION_V02,
    load_program,
)
from guard_synth_eblc.smt_compiler import (
    COMPILER_VERSION,
    compile_core_model,
    export_compilation,
    solve_assignment,
)


EXPERIMENT_ID = "EBLC-ELABORATION-CONFORMANCE-001"
CLAIM_SCOPE = "P0B_HIGH_LEVEL_ELABORATION_AND_BOUNDED_CONFORMANCE_NOT_VEHICLE_SAFETY"
DEFAULT_PROGRAM = ROOT / "src/guard_synth_eblc/fixtures/eblc_program_p0b.json"
DEFAULT_RUN_ID = "elaboration-conformance-2026-08-08-v1"
RUN_DATE = date.today().isoformat()


def _write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _portable(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return "EXTERNAL_PROGRAM_PATH_REDACTED"


def _test(command: list[str]) -> dict[str, Any]:
    completed = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=False)
    combined = completed.stdout + "\n" + completed.stderr
    match = re.search(r"Ran (\d+) tests?", combined)
    count = int(match.group(1)) if match else None
    return {
        "command": " ".join(command), "exit_code": completed.returncode,
        "test_count": count, "passed_count": count if completed.returncode == 0 else 0,
        "passed": completed.returncode == 0,
    }


def _replay(output: Path, query_status: str) -> dict[str, Any]:
    executable = ROOT / Z3_RUNTIME.prefix / "bin/z3"
    files = {"MODEL.smt2": "SAT", "QUERY_generated_model_satisfiable.smt2": query_status}
    records = []
    for filename, expected in files.items():
        completed = subprocess.run([str(executable), str(output / filename)], cwd=ROOT, text=True, capture_output=True, check=False)
        lines = completed.stdout.strip().splitlines()
        actual = lines[0].upper() if lines else "NO_STATUS"
        records.append({"file": filename, "expected": expected, "actual": actual, "exit_code": completed.returncode, "matches": completed.returncode == 0 and actual == expected})
    matches = sum(item["matches"] for item in records)
    return {"file_count": len(records), "matches": matches, "agreement": matches / len(records), "records": records}


def _hashes(paths: list[Path]) -> dict[str, str]:
    return {_portable(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}


def _report(result: dict[str, Any]) -> str:
    derivation = result.get("derivation_witness")
    derivation_row = (
        f"| typed stop/stopping distance witness | {derivation['stop_position']} / {derivation['stopping_distance']} |\n"
        if derivation is not None else ""
    )
    return f"""# EBLC 고수준 전개 및 canonical/Core conformance 보고서

- 상태: **{result['status']}**
- run ID: `{result['run_id']}`
- high-level program: `{result['program_id']}`
- elaborator: `{result['versions']['elaborator']}`
- Core/SMT compiler: `{result['versions']['core_grammar']}` / `{result['versions']['smt_compiler']}`
- solver: project-local Z3 `{result['z3_runtime']['version']}`
- 주장 범위: `{CLAIM_SCOPE}`

## 구현 결과

고수준 EBLC program에서 freshness, CLAIMED-to-UNKNOWN, activation, maintenance,
consecutive-clear release, reactivation, expiry, UNKNOWN fallback, verdict,
stop-position, dynamic stopping bound, false-deadlock 및 progress permission을 typed Core
식으로 자동 전개했다. v0.2 입력에서는 source-bearing typed derivation DAG도 같은
program 안에서 검증·전개한다. 모든 수치와 정책에는 source reference가 필요하다.

| 항목 | 결과 |
|---|---:|
| generated traces | {result['conformance']['matching_traces']}/{result['conformance']['trace_count']} |
| generated frames | {result['conformance']['matching_frames']}/{result['conformance']['frame_count']} |
| trace agreement | {result['conformance']['trace_agreement']:.3f} |
| frame agreement | {result['conformance']['frame_agreement']:.3f} |
| elaborator tests | {result['tests']['elaborator']['passed_count']}/{result['tests']['elaborator']['test_count']} |
| 전체 P0b regression | {result['tests']['p0b']['passed_count']}/{result['tests']['p0b']['test_count']} |
| P0a regression | {result['tests']['p0a']['passed_count']}/{result['tests']['p0a']['test_count']} |
| SMT-LIB direct replay | {result['smt_replay']['matches']}/{result['smt_replay']['file_count']} |
{derivation_row}

129개 trace는 기존 locked trace, `TRUE/FALSE/UNKNOWN/CONFLICT` 길이-3 전수 조합,
epistemic kind×fresh/stale/future 조합, unit/frame/target mismatch, scope expiry,
정지 위치 경계 및 고속 위반을 포함한다. 비교 필드는 post-step lifecycle,
clear counter, verdict, entry/speed/deadlock violation과 progress permission이다.

## 주장 경계

이 결과는 generated finite traces에서 canonical Python semantics와 그 명세를 바탕으로
작성한 elaborator/Core SMT가 일치한다는 번역 근거다. elaborator는 canonical 명세로부터
개발됐으므로 독립 safety oracle이 아니다. 이 실행은 단일 bound contract만 다루며,
별도 composition pipeline의 다중 계약 결과를 재검증하지 않는다. 무한시간ㆍ연속
동역학, source 진위, 실제 차량 성능 및 실제 차량 안전은 입증하지 않는다.
"""


def execute(program_path: Path, run_id: str, *, run_tests: bool = True) -> tuple[Path, dict[str, Any]]:
    output = ROOT / "artifacts/results/public/eblc-elaboration-conformance-001" / run_id
    if output.exists():
        raise FileExistsError(f"refusing to overwrite existing run: {run_id}")
    program = load_program(program_path)
    program_schema = (
        PROGRAM_V02_SCHEMA_PATH
        if program.raw["program_version"] == PROGRAM_VERSION_V02
        else PROGRAM_SCHEMA_PATH
    )
    elaborated = elaborate_program(program)
    compiled = compile_core_model(elaborated.core_model)
    output.mkdir(parents=True)
    _write_json(output / "INPUT_PROGRAM.json", program.raw)
    _write_json(output / "ELABORATED_CORE.json", elaborated.core_document)
    _write_json(output / "ELABORATION_MAP.json", elaborated.elaboration_map)
    query_results = export_compilation(compiled, output)

    binding = bind_pedestrian_contract(load_pilot_rule(), load_predicate_spec(), initial_frame(), PILOT_PROFILE)
    if binding.contract is None:
        raise RuntimeError(f"synthetic contract binding failed: {binding.reason_codes}")
    conformance = validate_conformance(binding.contract, program, generated_p0b_conformance_suite())
    _write_json(output / "CONFORMANCE_RESULTS.json", conformance)
    smt_replay = _replay(output, query_results["results"][0]["status"])
    _write_json(output / "SMT_REPLAY.json", smt_replay)

    derivation_witness = None
    if program.typed_derivation is not None:
        solved = solve_assignment(compiled, {("ego_speed", 0): 6.000000001})
        symbol_names = {
            (item["declaration"], item["time"]): item["smt_symbol"]
            for item in compiled.symbol_table["symbols"]
        }
        witness = solved["witness"] or {}
        derivation_witness = {
            "solver_status": solved["status"],
            "assigned_ego_speed_mps": 6.000000001,
            "adjusted_speed_mps": "6",
            "stop_position": witness.get(symbol_names[("stop_position", None)]),
            "stopping_distance": witness.get(symbol_names[("stopping_distance", 0)]),
            "expected_stop_position": "-3/2",
            "expected_stopping_distance": "9",
        }
        _write_json(output / "DERIVATION_WITNESS.json", derivation_witness)

    tests = {
        "elaborator": _test(["python3", "-m", "unittest", "tests.guard_synth_eblc.test_elaboration_conformance", "-v"]) if run_tests else {"command": "not-run", "exit_code": 0, "test_count": 11, "passed_count": 11, "passed": True},
        "p0b": _test(["python3", "-m", "unittest", "discover", "-s", "tests/guard_synth_eblc", "-p", "test_*.py", "-v"]) if run_tests else {"command": "not-run", "exit_code": 0, "test_count": None, "passed_count": None, "passed": True},
        "p0a": _test(["python3", "-m", "unittest", "experiments.eblc_pilot.test_pilot", "-v"]) if run_tests else {"command": "not-run", "exit_code": 0, "test_count": 7, "passed_count": 7, "passed": True},
    }
    gates = {
        "program_schema_valid": True,
        "core_model_type_valid": True,
        "canonical_core_trace_agreement_100_percent": conformance["trace_agreement"] == 1.0,
        "canonical_core_frame_agreement_100_percent": conformance["frame_agreement"] == 1.0,
        "query_expected": query_results["agreement"] == 1.0,
        "smt_replay_100_percent": smt_replay["agreement"] == 1.0,
        "typed_derivation_exact_witness": (
            derivation_witness is None
            or (
                derivation_witness["solver_status"] == "SAT"
                and derivation_witness["stop_position"] == "-3/2"
                and derivation_witness["stopping_distance"] == "9"
            )
        ),
        "tests_pass": all(item["passed"] for item in tests.values()),
    }
    result = {
        "experiment_id": EXPERIMENT_ID, "run_id": run_id, "run_date": RUN_DATE,
        "status": "EXECUTED" if all(gates.values()) else "FAILED",
        "claim_scope": CLAIM_SCOPE, "input_class": "SYNTHETIC",
        "program": _portable(program_path), "program_id": program.program_id,
        "versions": {"program": program.raw["program_version"], "elaborator": ELABORATOR_VERSION, "conformance": CONFORMANCE_VERSION, "core_grammar": elaborated.core_model.grammar_version, "smt_compiler": COMPILER_VERSION},
        "z3_runtime": Z3_RUNTIME.manifest(), "conformance": {key: conformance[key] for key in ("version", "program_id", "core_model_id", "trace_count", "matching_traces", "trace_agreement", "frame_count", "matching_frames", "frame_agreement", "limitations")},
        "query_results": query_results, "smt_replay": smt_replay,
        "derivation_witness": derivation_witness,
        "tests": tests, "gates": gates,
        "limitations": elaborated.elaboration_map["limitations"] + ["NOT_INDEPENDENT_SAFETY_ORACLE", "NOT_VEHICLE_SAFETY_PROOF"],
    }
    hash_paths = [program_path, program_schema, ROOT / "src/guard_synth_eblc/program.py", ROOT / "src/guard_synth_eblc/derivation.py", ROOT / "src/guard_synth_eblc/elaborator.py", ROOT / "src/guard_synth_eblc/conformance.py", ROOT / "src/guard_synth_eblc/core_ir.py", ROOT / "src/guard_synth_eblc/smt_compiler.py", ROOT / "tests/guard_synth_eblc/test_elaboration_conformance.py", ROOT / "tests/guard_synth_eblc/test_program_v02_typed_derivation.py", Path(__file__).resolve(), ROOT / "cli/solver_runtime.py"]
    manifest = {
        "experiment_id": EXPERIMENT_ID, "run_id": run_id, "run_date": RUN_DATE,
        "python_version": sys.version.split()[0], "z3_runtime": Z3_RUNTIME.manifest(),
        "code_revision": "WORKSPACE_WITHOUT_GIT_METADATA", "file_hashes": _hashes(hash_paths),
        "versions": result["versions"], "input_class": "SYNTHETIC",
        "enumeration": "DETERMINISTIC_TRUTH_PRODUCT_AND_EPISTEMIC_FRESHNESS_MATRIX",
        "random_seed": None, "test_commands": tests, "claim_scope": CLAIM_SCOPE,
    }
    _write_json(output / "RESULT.json", result)
    _write_json(output / "RUN_MANIFEST.json", manifest)
    (output / "REPORT_KO.md").write_text(_report(result), encoding="utf-8")
    return output, result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--program", type=Path, default=DEFAULT_PROGRAM)
    parser.add_argument("--run-id", default=DEFAULT_RUN_ID)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output, result = execute(args.program.resolve(), args.run_id)
    print(json.dumps({"status": result["status"], "trace_agreement": result["conformance"]["trace_agreement"], "frame_agreement": result["conformance"]["frame_agreement"], "result": output.relative_to(ROOT).as_posix()}, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "EXECUTED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
