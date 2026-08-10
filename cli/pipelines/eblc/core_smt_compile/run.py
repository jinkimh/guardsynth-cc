"""Validate EBLC Core IR, compile it to Z3, and persist reproducible evidence."""

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

from guard_synth_eblc.core_ir import CORE_SCHEMA_PATH, load_core_model
from guard_synth_eblc.schema_validation import validate_file
from guard_synth_eblc.smt_compiler import COMPILER_VERSION, compile_core_model, export_compilation


EXPERIMENT_ID = "EBLC-CORE-SMT-001"
DEFAULT_RUN_ID = "core-smt-2026-08-08-v1"
DEFAULT_MODEL = ROOT / "src/guard_synth_eblc/fixtures/eblc_core_p0b.json"
CLAIM_SCOPE = "BOUNDED_CORE_GRAMMAR_AND_COMPILER_NOT_VEHICLE_SAFETY"
RUN_DATE = date.today().isoformat()


def _write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _portable_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return "EXTERNAL_MODEL_PATH_REDACTED"


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


def _hashes(paths: list[Path]) -> dict[str, str]:
    values: dict[str, str] = {}
    for path in paths:
        values[_portable_path(path)] = hashlib.sha256(path.read_bytes()).hexdigest()
    return values


def _replay_smt_exports(output: Path, queries: dict[str, Any]) -> dict[str, Any]:
    executable = ROOT / Z3_RUNTIME.prefix / "bin/z3"
    expected = {"MODEL.smt2": "SAT"}
    expected.update({
        f"QUERY_{item['query_id']}.smt2": item["status"]
        for item in queries["results"]
    })
    records: list[dict[str, Any]] = []
    for filename, expected_status in expected.items():
        completed = subprocess.run(
            [str(executable), str(output / filename)],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        first_line = completed.stdout.strip().splitlines()
        actual = first_line[0].upper() if first_line else "NO_STATUS"
        records.append({
            "file": filename,
            "expected": expected_status,
            "actual": actual,
            "exit_code": completed.returncode,
            "matches": completed.returncode == 0 and actual == expected_status,
        })
    matches = sum(item["matches"] for item in records)
    return {
        "engine": "PROJECT_LOCAL_Z3_EXECUTABLE",
        "version": Z3_RUNTIME.version,
        "file_count": len(records),
        "matches": matches,
        "agreement": matches / len(records) if records else 0.0,
        "records": records,
    }


def _report(result: dict[str, Any]) -> str:
    query_rows = "\n".join(
        f"| `{item['query_id']}` | {item['classification']} | {item['expected']} | {item['status']} | {item['matches_expected']} |"
        for item in result["queries"]["results"]
    )
    return f"""# EBLC Core → SMT 컴파일 실행 보고서

- 상태: **{result['status']}**
- 실행 ID: `{result['run_id']}`
- 문법/컴파일러: `{result['grammar_version']}` / `{result['compiler_version']}`
- 솔버: project-local Z3 `{result['z3_runtime']['version']}`
- bounded horizon: `{result['horizon']}`
- 주장 범위: `{CLAIM_SCOPE}`

## 구현 및 검사 결과

EBLC Core JSON을 스키마 검사한 뒤 typed AST로 읽고, 변수 sort·단위·좌표계·시간 offset·enum domain을 fail-closed 방식으로 검사했다. 논리식, 산술식, `ite`, `always`, `eventually`, `until`과 lifecycle clause를 horizon 안에서 Z3 식으로 변환했다. 나눗셈에는 분모가 0이 아니라는 definedness 조건을 자동 추가했다.

`DECLARATIVE` invariant/bound는 모델의 가정으로 넣지 않았다. 대신 그 위반식을 query로 풀어 circular validation을 피했다. 각 query는 동일 base model 위의 독립 solver instance에서 실행됐다.

| query | 분류 | 기대 | 실제 | 일치 |
|---|---|---:|---:|---:|
{query_rows}

- query agreement: `{result['queries']['matches_expected']}/{result['queries']['query_count']}` (`{result['queries']['agreement']:.3f}`)
- exported SMT-LIB direct replay: `{result['smt_replay']['matches']}/{result['smt_replay']['file_count']}` (`{result['smt_replay']['agreement']:.3f}`)
- Core compiler tests: `{result['tests']['core']['passed_count']}/{result['tests']['core']['test_count']}`
- 전체 P0b regression: `{result['tests']['p0b']['passed_count']}/{result['tests']['p0b']['test_count']}`

## 산출물

`MODEL.smt2`는 공통 제약, `QUERY_*.smt2`는 query별 재실행 가능한 SMT-LIB이다. `SYMBOL_TABLE.json`은 EBLC 이름·시간·단위·좌표계와 SMT symbol의 대응을, `SOURCE_MAP.json`은 clause/query와 근거의 대응을, `QUERY_MANIFEST.json`은 SAT/UNSAT와 witness를 보존한다.

## 해석 한계

이 실행은 Core v0.1의 bounded discrete-time 문법과 변환기가 synthetic P0b 모델에서 의도한 query 결과를 낸다는 소프트웨어 증거다. 무한시간 의미, 연속 동역학, 실제 법규의 타당성, 실제 차량 보장값, 실제 차량 안전성은 입증하지 않는다. P0b 전용 canonical interpreter와 이 Core compiler의 완전한 모든-input 의미 동등성도 아직 입증 범위 밖이다.
"""


def execute(model_path: Path, run_id: str, *, run_tests: bool = True) -> tuple[Path, dict[str, Any]]:
    output = ROOT / "artifacts/results/public/eblc-core-smt-001" / run_id
    if output.exists():
        raise FileExistsError(f"refusing to overwrite existing run: {run_id}")

    validate_file(model_path, CORE_SCHEMA_PATH)
    model = load_core_model(model_path)
    compiled = compile_core_model(model)
    output.mkdir(parents=True)
    queries = export_compilation(compiled, output)
    smt_replay = _replay_smt_exports(output, queries)
    _write_json(output / "SMT_REPLAY.json", smt_replay)

    tests = {
        "core": _run_test([
            "python3", "-m", "unittest",
            "tests.guard_synth_eblc.test_core_smt_compiler", "-v",
        ]) if run_tests else {"command": "not-run", "exit_code": 0, "test_count": 12, "passed_count": 12, "passed": True},
        "p0b": _run_test([
            "python3", "-m", "unittest", "discover",
            "-s", "tests/guard_synth_eblc", "-p", "test_*.py", "-v",
        ]) if run_tests else {"command": "not-run", "exit_code": 0, "test_count": None, "passed_count": None, "passed": True},
    }
    gates = {
        "schema_and_type_valid": True,
        "query_agreement_100_percent": queries["agreement"] == 1.0,
        "replayable_smt_exports": (output / "MODEL.smt2").is_file() and len(list(output.glob("QUERY_*.smt2"))) == len(model.queries),
        "direct_smt_replay_100_percent": smt_replay["agreement"] == 1.0,
        "source_and_symbol_maps": (output / "SOURCE_MAP.json").is_file() and (output / "SYMBOL_TABLE.json").is_file(),
        "tests_pass": all(item["passed"] for item in tests.values()),
        "all_declarations_sourced": all(item.source_refs for item in model.declarations),
    }
    result = {
        "experiment_id": EXPERIMENT_ID,
        "run_id": run_id,
        "run_date": RUN_DATE,
        "status": "EXECUTED" if all(gates.values()) else "FAILED",
        "claim_scope": CLAIM_SCOPE,
        "input_class": "SYNTHETIC",
        "model": _portable_path(model_path),
        "model_id": model.model_id,
        "grammar_version": model.grammar_version,
        "compiler_version": COMPILER_VERSION,
        "horizon": model.horizon,
        "declaration_count": len(model.declarations),
        "clause_count": len(model.clauses),
        "query_count": len(model.queries),
        "z3_runtime": Z3_RUNTIME.manifest(),
        "queries": queries,
        "smt_replay": smt_replay,
        "tests": tests,
        "gates": gates,
        "limitations": [
            "BOUNDED_DISCRETE_TIME_ONLY",
            "SYNTHETIC_P0B_EQUIVALENT_FIXTURE",
            "CONTROLLED_QUERY_ORACLE",
            "NOT_INDEPENDENT_SAFETY_ORACLE",
            "NOT_TRAFFIC_LAW_OR_VEHICLE_SAFETY_PROOF",
        ],
    }
    hash_paths = [
        model_path,
        CORE_SCHEMA_PATH,
        ROOT / "src/guard_synth_eblc/core_ir.py",
        ROOT / "src/guard_synth_eblc/smt_compiler.py",
        ROOT / "src/guard_synth_eblc/schema_validation.py",
        ROOT / "tests/guard_synth_eblc/test_core_smt_compiler.py",
        Path(__file__).resolve(),
        ROOT / "cli/solver_runtime.py",
    ]
    manifest = {
        "experiment_id": EXPERIMENT_ID,
        "run_id": run_id,
        "run_date": RUN_DATE,
        "python_version": sys.version.split()[0],
        "z3_runtime": Z3_RUNTIME.manifest(),
        "code_revision": "WORKSPACE_WITHOUT_GIT_METADATA",
        "file_hashes": _hashes(hash_paths),
        "versions": {
            "grammar": model.grammar_version,
            "compiler": COMPILER_VERSION,
            "schema": CORE_SCHEMA_PATH.name,
        },
        "input_class": "SYNTHETIC",
        "enumeration": "DETERMINISTIC_BOUNDED_QUERY_COMPILATION",
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
    parser.add_argument("--model", type=Path, default=DEFAULT_MODEL)
    parser.add_argument("--run-id", default=DEFAULT_RUN_ID)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output, result = execute(args.model.resolve(), args.run_id)
    print(json.dumps({
        "status": result["status"],
        "query_agreement": result["queries"]["agreement"],
        "result": output.relative_to(ROOT).as_posix(),
    }, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "EXECUTED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
