"""Run EBLC bundle composition, Core elaboration, SMT export, and agreement."""

from __future__ import annotations

import argparse
from dataclasses import replace
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

from guard_synth_eblc.adapters.synthetic_pedestrian import PILOT_PROFILE, frame, initial_frame
from guard_synth_eblc.binders import bind_pedestrian_contract
from guard_synth_eblc.bundle_conformance import BUNDLE_CONFORMANCE_VERSION, compare_bundle_trace
from guard_synth_eblc.bundle_elaborator import BUNDLE_ELABORATOR_VERSION, elaborate_bundle
from guard_synth_eblc.catalog import load_pilot_rule, load_predicate_spec
from guard_synth_eblc.composition import BUNDLE_VERSION, COMPOSITION_VERSION, EBLCBundle, load_bundle
from guard_synth_eblc.derivation import DERIVATION_COMPILER_VERSION, DERIVATION_VERSION
from guard_synth_eblc.examples import synthetic_bundle, synthetic_bundle_v02
from guard_synth_eblc.smt_compiler import (
    COMPILER_VERSION,
    compile_core_model,
    export_compilation,
    solve_assignment,
)
from guard_synth_eblc.types import Truth


EXPERIMENT_ID = "EBLC-COMPOSITION-COMPILATION-001"
CLAIM_SCOPE = "SYNTHETIC_MULTI_CONTRACT_COMPOSITION_AND_BOUNDED_TRANSLATION_NOT_VEHICLE_SAFETY"
DEFAULT_RUN_ID = "composition-v02-typed-derivation-2026-08-09-v2"
RUN_DATE = date.today().isoformat()
STABLE_BASELINE_TEST_MODULES = (
    "platforms/eblc-bcv/tests/unit/test_composition_compilation.py",
    "platforms/eblc-bcv/tests/unit/test_core_smt_compiler.py",
    "platforms/eblc-bcv/tests/unit/test_derivation_compiler.py",
    "platforms/eblc-bcv/tests/unit/test_elaboration_conformance.py",
    "platforms/eblc-bcv/tests/unit/test_program_v02_typed_derivation.py",
    "platforms/eblc-bcv/tests/unit/test_public_layout.py",
    "projects/04-guardsynth-coc/tests/integration/test_real_scene_adapter.py",
    "platforms/eblc-bcv/tests/robustness/test_robustness.py",
    "platforms/eblc-bcv/tests/translation/test_scenario_matrix.py",
    "platforms/eblc-bcv/tests/unit/test_schema_binding.py",
    "platforms/eblc-bcv/tests/unit/test_semantics.py",
    "platforms/eblc-bcv/tests/mutation/test_translation_mutations.py",
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
        return "EXTERNAL_BUNDLE_PATH_REDACTED"


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
        "QUERY_composed_model_satisfiable.smt2": query_status,
    }
    records = []
    for filename, expected in files.items():
        completed = subprocess.run(
            [str(executable), str(output / filename)],
            cwd=ROOT, text=True, capture_output=True, check=False,
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


def _synthetic_contracts(bundle: EBLCBundle):
    binding = bind_pedestrian_contract(
        load_pilot_rule(), load_predicate_spec(), initial_frame(), PILOT_PROFILE
    )
    if binding.contract is None:
        raise RuntimeError(f"synthetic contract binding failed: {binding.reason_codes}")
    return {
        item.contract_id: replace(binding.contract, contract_id=item.contract_id)
        for item in bundle.contracts
    }


def _bundle_factory(program_version: str):
    if program_version == "eblc-program-v0.2":
        return synthetic_bundle_v02
    if program_version == "eblc-program-v0.1":
        return synthetic_bundle
    raise ValueError(f"unsupported synthetic program version: {program_version}")


def _scenario_matrix(program_version: str) -> dict[str, Any]:
    make_bundle = _bundle_factory(program_version)
    scenarios = (
        ("hard_suppresses_service", make_bundle(), Truth.TRUE, False),
        (
            "incomparable_hard_conflict",
            make_bundle(("HARD", "HARD"), (("STOP",), ("PROCEED",)), bundle_id="hard_conflict_bundle"),
            Truth.TRUE, True,
        ),
        (
            "incomparable_service_review",
            make_bundle(("SERVICE", "SERVICE"), (("STOP",), ("PROCEED",)), bundle_id="service_review_bundle"),
            Truth.TRUE, False,
        ),
        (
            "explicit_same_tier_override",
            make_bundle(
                ("SERVICE", "SERVICE"), (("STOP",), ("PROCEED",)),
                (("C1",), ()), bundle_id="explicit_override_bundle",
            ),
            Truth.TRUE, False,
        ),
        ("no_live_full_action_domain", make_bundle(bundle_id="no_live_bundle"), Truth.FALSE, False),
    )
    records = []
    for scenario_id, bundle, truth, safe_progress in scenarios:
        contracts = _synthetic_contracts(bundle)
        trace = (frame(0.0, truth),)
        result = compare_bundle_trace(
            bundle,
            contracts,
            {contract_id: trace for contract_id in contracts},
            safe_progress_action_exists=(safe_progress,),
        )
        records.append({"scenario_id": scenario_id, **result})
    matches = sum(bool(item["matches"]) for item in records)
    return {
        "program_version": program_version,
        "scenario_count": len(records),
        "matching_scenarios": matches,
        "agreement": matches / len(records),
        "records": records,
    }


def _derivation_witness(compiled) -> dict[str, Any]:
    declarations = {item.name for item in compiled.model.declarations}
    if not {"c0__stopping_distance", "c1__stopping_distance"}.issubset(declarations):
        return {
            "status": "NOT_APPLICABLE",
            "reason_code": "BUNDLE_COMPONENTS_HAVE_NO_SYMBOLIC_STOPPING_DERIVATION",
        }
    solved = solve_assignment(compiled, {
        ("c0__ego_speed", 0): 6.000000001,
        ("c1__ego_speed", 0): 3.000000001,
    })
    symbols = {
        (item["declaration"], item["time"]): item["smt_symbol"]
        for item in compiled.symbol_table["symbols"]
    }
    witness = solved["witness"] or {}
    definedness = [item for item in compiled.assertions if item.role == "DEFINEDNESS"]
    return {
        "status": solved["status"],
        "assignments": {
            "c0__ego_speed@0": 6.000000001,
            "c1__ego_speed@0": 3.000000001,
        },
        "exact_outputs": {
            "c0__stop_position": witness.get(symbols[("c0__stop_position", None)]),
            "c0__stopping_distance@0": witness.get(symbols[("c0__stopping_distance", 0)]),
            "c1__stop_position": witness.get(symbols[("c1__stop_position", None)]),
            "c1__stopping_distance@0": witness.get(symbols[("c1__stopping_distance", 0)]),
        },
        "definedness_assertion_count": len(definedness),
        "definedness_clause_ids": sorted({item.clause_id for item in definedness}),
        "claim_scope": "EXACT_SYNTHETIC_BOUNDED_DERIVATION_REPLAY_NOT_VEHICLE_SAFETY",
    }


def _hashes(paths: list[Path]) -> dict[str, str]:
    return {
        _portable(path): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in paths
    }


def _report(result: dict[str, Any]) -> str:
    tests = result["tests"]
    return f"""# EBLC 다중 계약 composition 및 고수준→Core→SMT 실행 보고서

- 상태: **{result['status']}**
- run ID: `{result['run_id']}`
- solver: project-local Z3 `{result['z3_runtime']['version']}`
- 주장 범위: `{CLAIM_SCOPE}`

## 결과

| 항목 | 결과 |
|---|---:|
| 기존 EBLC 111개 기준선 회귀 | {tests['stable_baseline']['passed_count']}/{tests['stable_baseline']['test_count']} |
| v0.2 composition 신규 테스트 | {tests['composition_v02']['passed_count']}/{tests['composition_v02']['test_count']} |
| 전체 EBLC 테스트 | {tests['full_eblc']['passed_count']}/{tests['full_eblc']['test_count']} |
| P0a 회귀 | {tests['p0a']['passed_count']}/{tests['p0a']['test_count']} |
| composition canonical/Core-SMT agreement | {result['scenario_matrix']['matching_scenarios']}/{result['scenario_matrix']['scenario_count']} |
| SMT-LIB 직접 replay | {result['smt_replay']['matches']}/{result['smt_replay']['file_count']} |

bundle v0.1 컨테이너 안에서 `EBLCProgram v0.2`의 typed derivation을 계약별로
namespace하여 Core와 SMT까지 전달했다. priority는 scalar
weight가 아니라 `HARD > SERVICE > PREFERENCE` 및 근거 있는 비순환 override로
처리한다. 선택 계약의 허용 action 교집합이 비면 hard-hard는 `CONFLICT`, 그 밖은
`REVIEW_REQUIRED`다. 생성된 namespaced Core는 generic compiler를 통해 실제
SMT-LIB/Z3로 변환됐다. 두 계약의 정지거리 식과 나눗셈 분모 비영 조건도
각각 독립된 SMT assertion으로 보존된다.

## 주장 경계

결과는 synthetic bounded trace에서 composition 의미와 Core/Z3 번역이 일치한다는
근거다. 독립 safety oracle, 실제 법규 해석, 실제 차량 성능 보장 또는 차량 안전
증명이 아니다. 현재 typed derivation 문법이 허용하는 유한 산술 DAG만 다루며,
무한시간/연속 동역학과 임의 사용자 정의 함수는 아직 범위 밖이다.
"""


def execute(
    bundle_path: Path | None,
    run_id: str,
    program_version: str = "eblc-program-v0.2",
) -> tuple[Path, dict[str, Any]]:
    output = ROOT / "artifacts/results/public/eblc-composition-compilation-001" / run_id
    if output.exists():
        raise FileExistsError(f"refusing to overwrite existing run: {run_id}")
    bundle = (
        load_bundle(bundle_path)
        if bundle_path is not None
        else _bundle_factory(program_version)()
    )
    elaborated = elaborate_bundle(bundle)
    compiled = compile_core_model(elaborated.core_model)
    output.mkdir(parents=True)
    _write_json(output / "INPUT_BUNDLE.json", bundle.raw)
    _write_json(output / "ELABORATED_CORE.json", elaborated.core_document)
    _write_json(output / "ELABORATION_MAP.json", elaborated.elaboration_map)
    query_results = export_compilation(compiled, output)
    smt_replay = _replay(output, query_results["results"][0]["status"])
    scenario_matrix = _scenario_matrix(program_version)
    derivation_witness = _derivation_witness(compiled)
    _write_json(output / "COMPOSITION_RESULTS.json", scenario_matrix)
    _write_json(output / "SMT_REPLAY.json", smt_replay)
    _write_json(output / "DERIVATION_WITNESS.json", derivation_witness)

    tests = {
        "stable_baseline": _test(["python3", "-m", "unittest", *STABLE_BASELINE_TEST_MODULES, "-v"]),
        "composition_v02": _test(["python3", "-m", "unittest", "platforms/eblc-bcv/tests/unit/test_composition_v02_derivation.py", "-v"]),
        "full_eblc": _test(["python3", "-m", "unittest", "discover", "-s", "platforms/eblc-bcv/tests", "-p", "test_*.py", "-v"]),
        "p0a": _test(["python3", "-m", "unittest", "experiments.eblc_pilot.test_pilot", "-v"]),
    }
    exact_derivation_gate = (
        derivation_witness["status"] == "NOT_APPLICABLE"
        or (
            derivation_witness["status"] == "SAT"
            and derivation_witness["exact_outputs"]["c0__stopping_distance@0"] == "9"
            and derivation_witness["exact_outputs"]["c1__stopping_distance@0"] == "3"
            and derivation_witness["definedness_assertion_count"] == 18
        )
    )
    gates = {
        "bundle_schema_and_semantics_valid": True,
        "core_type_valid": True,
        "priority_not_scalarized": not elaborated.elaboration_map["priority"]["compiled_as_scalar_weight"],
        "query_expected": query_results["agreement"] == 1.0,
        "canonical_core_smt_agreement_100_percent": scenario_matrix["agreement"] == 1.0,
        "smt_replay_100_percent": smt_replay["agreement"] == 1.0,
        "stable_baseline_111_of_111": tests["stable_baseline"]["test_count"] == 111 and tests["stable_baseline"]["passed"],
        "v02_composition_8_of_8": tests["composition_v02"]["test_count"] == 8 and tests["composition_v02"]["passed"],
        "symbolic_derivation_exact_or_explicitly_not_applicable": exact_derivation_gate,
        "all_tests_pass": all(item["passed"] for item in tests.values()),
    }
    result = {
        "experiment_id": EXPERIMENT_ID,
        "run_id": run_id,
        "run_date": RUN_DATE,
        "status": "EXECUTED" if all(gates.values()) else "FAILED",
        "claim_scope": CLAIM_SCOPE,
        "input_class": "SYNTHETIC",
        "input_bundle": _portable(bundle_path) if bundle_path else "GENERATED_PUBLIC_SYNTHETIC_EXAMPLE",
        "bundle_id": bundle.bundle_id,
        "versions": {
            "bundle": BUNDLE_VERSION,
            "composition": COMPOSITION_VERSION,
            "bundle_elaborator": BUNDLE_ELABORATOR_VERSION,
            "bundle_conformance": BUNDLE_CONFORMANCE_VERSION,
            "component_programs": elaborated.elaboration_map["component_program_versions"],
            "component_typed_derivations": elaborated.elaboration_map["component_typed_derivations"],
            "derivation_language": DERIVATION_VERSION,
            "derivation_compiler": DERIVATION_COMPILER_VERSION,
            "core_grammar": elaborated.core_model.grammar_version,
            "smt_compiler": COMPILER_VERSION,
        },
        "z3_runtime": Z3_RUNTIME.manifest(),
        "scenario_matrix": scenario_matrix,
        "derivation_witness": derivation_witness,
        "query_results": query_results,
        "smt_replay": smt_replay,
        "tests": tests,
        "gates": gates,
        "limitations": elaborated.elaboration_map["limitations"] + [
            "GENERATED_TRANSLATION_ORACLE",
            "NOT_INDEPENDENT_SAFETY_ORACLE",
        ],
    }
    hash_paths = [
        ROOT / "platforms/eblc-bcv/src/guard_synth_eblc/schemas/eblc_bundle.schema.json",
        ROOT / "platforms/eblc-bcv/src/guard_synth_eblc/schemas/eblc_program_v0_2.schema.json",
        ROOT / "platforms/eblc-bcv/src/guard_synth_eblc/fixtures/eblc_program_p0b_v0_2.json",
        ROOT / "platforms/eblc-bcv/src/guard_synth_eblc/composition.py",
        ROOT / "platforms/eblc-bcv/src/guard_synth_eblc/bundle_elaborator.py",
        ROOT / "platforms/eblc-bcv/src/guard_synth_eblc/bundle_conformance.py",
        ROOT / "platforms/eblc-bcv/src/guard_synth_eblc/elaborator.py",
        ROOT / "platforms/eblc-bcv/src/guard_synth_eblc/core_ir.py",
        ROOT / "platforms/eblc-bcv/src/guard_synth_eblc/smt_compiler.py",
        ROOT / "platforms/eblc-bcv/tests/test_composition_compilation.py",
        ROOT / "platforms/eblc-bcv/tests/test_composition_v02_derivation.py",
        Path(__file__).resolve(),
    ]
    manifest = {
        "experiment_id": EXPERIMENT_ID,
        "run_id": run_id,
        "run_date": RUN_DATE,
        "python_version": sys.version.split()[0],
        "z3_runtime": Z3_RUNTIME.manifest(),
        "code_revision": "WORKSPACE_WITHOUT_GIT_METADATA",
        "file_hashes": _hashes(hash_paths),
        "versions": result["versions"],
        "input_class": "SYNTHETIC",
        "enumeration": "DETERMINISTIC_COMPOSITION_SCENARIO_MATRIX",
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
    parser.add_argument("--bundle", type=Path)
    parser.add_argument("--run-id", default=DEFAULT_RUN_ID)
    parser.add_argument(
        "--program-version",
        choices=("eblc-program-v0.1", "eblc-program-v0.2"),
        default="eblc-program-v0.2",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    bundle_path = args.bundle.resolve() if args.bundle else None
    output, result = execute(bundle_path, args.run_id, args.program_version)
    print(json.dumps({
        "status": result["status"],
        "stable_baseline": result["tests"]["stable_baseline"],
        "full_eblc": result["tests"]["full_eblc"],
        "composition_agreement": result["scenario_matrix"]["agreement"],
        "result": output.relative_to(ROOT).as_posix(),
    }, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "EXECUTED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
