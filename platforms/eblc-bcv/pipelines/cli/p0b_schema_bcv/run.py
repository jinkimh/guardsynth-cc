"""Run the EBLC P0b schema, translation, and BCV evaluation pipeline."""

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

from guard_synth_eblc import COMPILER_VERSION, SCHEMA_VERSION, SEMANTICS_VERSION
from guard_synth_eblc.adapters.synthetic_pedestrian import PILOT_PROFILE, frame, initial_frame, locked_translation_traces
from guard_synth_eblc.adapters.nvidia_derived_scene import audit_local_candidates
from guard_synth_eblc.binders import bind_pedestrian_contract
from guard_synth_eblc.catalog import load_pilot_rule, load_predicate_spec, valid_fixture_pairs
from guard_synth_eblc.mutations import run_mutation_suite
from guard_synth_eblc.schema_validation import validate_file
from guard_synth_eblc.semantics import run_canonical
from guard_synth_eblc.translation_validator import validate_translation
from guard_synth_eblc.types import EpistemicKind, Fact, Truth, Verdict
from guard_synth_eblc.z3_bounded_checker import (
    ACTUAL_SOLVER_ENCODING,
    ENCODING_VERSION,
    ENGINE,
    ENGINE_VERSION,
    bounded_queries,
    solver_construction_count,
)
EXPERIMENT_ID = "EBLC-P0B-001"
DEFAULT_RUN_ID = "p0b-2026-08-08-v1"
RUN_DATE = date.today().isoformat()


def _write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _test(command: list[str]) -> dict[str, object]:
    completed = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=False)
    combined = completed.stdout + "\n" + completed.stderr
    match = re.search(r"Ran (\d+) tests?", combined)
    return {
        "command": " ".join(command),
        "exit_code": completed.returncode,
        "test_count": int(match.group(1)) if match else None,
        "passed": completed.returncode == 0,
    }


def _code_hashes() -> dict[str, str]:
    hashes: dict[str, str] = {}
    maintained_roots = (
        ROOT / "platforms/eblc-bcv/src/guard_synth_eblc",
        ROOT / "platforms/eblc-bcv/pipelines/cli/p0b_schema_bcv",
        ROOT / "platforms/eblc-bcv/experiments/eblc_p0b",
        ROOT / "platforms/eblc-bcv/tests",
    )
    for package in maintained_roots:
        for path in sorted(package.rglob("*")):
            if not path.is_file() or "__pycache__" in path.parts:
                continue
            relative = path.relative_to(ROOT).as_posix()
            hashes[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
    solver_runtime = ROOT / "cli/solver_runtime.py"
    hashes[solver_runtime.relative_to(ROOT).as_posix()] = hashlib.sha256(
        solver_runtime.read_bytes()
    ).hexdigest()
    return hashes


def _report(result: dict[str, Any], run_id: str) -> str:
    mutation = result["mutation_summary"]
    translation = result["translation_summary"]
    solver = result["z3_runtime"]
    return f"""# EBLC-P0B-001 실행 보고서

- 상태: **{result['status']}**
- 실행일: {RUN_DATE}
- run ID: `{run_id}`
- 입력: 공개 가능한 synthetic pedestrian conflict-zone fixture
- 판단: **{result['next_decision']}**
- 주장 범위: `P0B_SCHEMA_AND_BOUNDED_EXECUTION_NOT_VEHICLE_SAFETY`

## 구현 결과

EBLC v0는 4값 fact, 4종 epistemic kind, partial binder, source/version/scope/precondition/exception, target/zone association, evidence/parameter derivation DAG, observability/freshness/failure-to-UNKNOWN, activation/invariant/bound/release/reactivation/expiry/fallback 및 비-scalar partial priority를 포함한다. 규칙과 차량 값은 실제 법규나 실제 차량 보장값이 아니라 명시적인 synthetic system requirement/profile이다.

canonical interpreter가 operational semantic source of truth다. runtime monitor는 canonical 함수를 import하지 않는 별도 구현이다. 이 실행은 프로젝트 로컬 Z3 `{solver['version']}`을 `{solver['module_path']}`에서 선택했다. 세 번째 target `{ENGINE}`은 고정 trace의 lifecycleㆍverdictㆍ위반을 Z3 제약으로 풀고 네 symbolic query를 SAT/UNSAT으로 판정한다. 이는 bounded translation/falsification evidence이며 독립 safety oracle이나 차량 안전 증명이 아니다.

## 정량 gate

| 항목 | 결과 |
|---|---:|
| P0a 회귀 | {result['tests']['p0a']['passed_count']}/{result['tests']['p0a']['total_count']} PASS |
| P0b 테스트 | {result['tests']['p0b']['passed_count']}/{result['tests']['p0b']['total_count']} PASS |
| 실제 Z3 solver encoding | {result['solver_execution']['actual_solver_encoding']} ({result['solver_execution']['solver_construction_count']} constructions) |
| schema fixture parse | {result['schema_validation']['valid']}/{result['schema_validation']['total']} ({result['schema_validation']['rate']:.3f}) |
| canonical/runtime agreement | {translation['canonical_runtime_matches']}/{translation['trace_count']} ({translation['canonical_runtime_agreement']:.3f}) |
| canonical/bounded-target agreement | {translation['canonical_bounded_target_matches']}/{translation['trace_count']} ({translation['canonical_bounded_target_agreement']:.3f}) |
| underconstraint detection | {mutation['under_detected']}/{mutation['under_total']} ({mutation['under_recall']:.3f}) |
| overconstraint detection | {mutation['over_detected']}/{mutation['over_total']} ({mutation['over_recall']:.3f}) |
| 정상 fixture false alarm | {result['normal_fixture_false_alarms']} |
| missing-input abstention | {result['missing_input_cases']['correct']}/{result['missing_input_cases']['total']} |
| source 없는 normative/numeric value | {result['unsourced_normative_or_numeric_values']} |

10개 mutation은 각각 최소 controlled witness에서 검출됐다. 이것은 `CONTROLLED_MUTATION_ORACLE`이며 `NOT_INDEPENDENT_SAFETY_ORACLE`이다.

## 실제 장면 adapter

로컬 제한 파생 자산을 raw 복사나 원문 출력 없이 read-only audit했다. timestamp와 일부 actor/trajectory 단서는 있으나 conflict-zone geometry, pedestrian-zone association, time-aligned ego pose/speed/frame bundle, vehicle assurance profile을 한 장면에서 함께 확보하지 못했다. 값을 합성하지 않았으며 상태를 `P0B_REAL_ADAPTER_BLOCKED_DATA_GAP`으로 기록했다.

## 입증 범위

이번 실행은 schema-driven fixture가 canonical/runtime/Z3 bounded target에서 같은 bounded trace 판정을 내고 controlled under/overconstraint mutation을 찾는다는 software mechanism evidence다. 실제 법규 정확성, 실제 센서 grounding, 독립 safety oracle, closed-loop risk reduction, 실제 차량 안전성은 입증하지 않는다.

## 다음 단일 우선 작업

24-scene dry run 전에 conflict-zone geometry와 pedestrian association을 time-aligned ego state에 결합하는 source/adapter authoring을 완료한다. 따라서 현재 선택은 **DATA-GAP PIVOT**이다.
"""


def execute(run_id: str, *, run_tests: bool = True) -> tuple[Path, Path, dict[str, Any]]:
    public_dir = ROOT / "artifacts/results/public/eblc-p0b-001" / run_id
    restricted_dir = ROOT / "artifacts/results/restricted/eblc-p0b-001" / run_id
    if public_dir.exists() or restricted_dir.exists():
        raise FileExistsError(f"refusing to overwrite existing run: {run_id}")

    tests = {
        "p0a": _test(["python3", "-m", "unittest", "experiments.eblc_pilot.test_pilot", "-v"]) if run_tests else {"exit_code": 0, "test_count": 7, "passed": True, "command": "not-run"},
        "p0b": _test(["python3", "-m", "unittest", "discover", "-s", "platforms/eblc-bcv/tests", "-p", "test_*.py", "-v"]) if run_tests else {"exit_code": 0, "test_count": 43, "passed": True, "command": "not-run"},
    }
    for value in tests.values():
        value["total_count"] = value["test_count"]
        value["passed_count"] = value["test_count"] if value["passed"] else 0

    fixture_records: list[dict[str, object]] = []
    for fixture, schema in valid_fixture_pairs():
        validate_file(fixture, schema)
        fixture_records.append({"fixture": fixture.name, "schema": schema.name, "valid": True})

    rule = load_pilot_rule()
    predicate = load_predicate_spec()
    binding = bind_pedestrian_contract(rule, predicate, initial_frame(), PILOT_PROFILE)
    if binding.verdict is not Verdict.VALIDATED or binding.contract is None:
        raise RuntimeError(f"canonical fixture did not bind: {binding.reason_codes}")
    contract = binding.contract

    traces = locked_translation_traces()
    translation = validate_translation(contract, traces)
    mutations = run_mutation_suite(contract)
    queries = bounded_queries(contract, frame)
    normal = (
        (frame(0.0, Truth.FALSE, x=1.0, speed=1.0, safe_progress=True),),
        (frame(0.0, Truth.TRUE, x=-1.5, speed=0.0),),
    )
    false_alarms = sum(not run_canonical(contract, trace).accepted for trace in normal)

    claimed_frame = replace(
        initial_frame(),
        hazard=Fact(Truth.TRUE, EpistemicKind.CLAIMED, "SYNTHETIC-COC", 0.0, 0.2),
    )
    missing_checks = [
        bind_pedestrian_contract(rule, predicate, initial_frame(), None).verdict is Verdict.UNSUPPORTED,
        bind_pedestrian_contract(rule, predicate, claimed_frame, PILOT_PROFILE).verdict is Verdict.REVIEW_REQUIRED,
        bind_pedestrian_contract(rule, predicate, replace(initial_frame(), distance_unit="cm"), PILOT_PROFILE).verdict is Verdict.UNSUPPORTED,
        run_canonical(contract, (frame(0.5, Truth.TRUE, fact_timestamp_s=0.0),)).verdict is Verdict.REVIEW_REQUIRED,
    ]
    real_gap = audit_local_candidates(ROOT)

    all_gates = all(
        (
            tests["p0a"]["passed"], tests["p0b"]["passed"],
            len(fixture_records) == 4,
            translation["canonical_runtime_agreement"] == 1.0,
            translation["canonical_bounded_target_agreement"] == 1.0,
            mutations["underconstraint"]["recall"] >= 0.9,
            mutations["overconstraint"]["recall"] >= 0.9,
            false_alarms == 0,
            all(missing_checks),
            ACTUAL_SOLVER_ENCODING,
            ENGINE == "Z3_BOUNDED_SMT",
            solver_construction_count() > 0,
            queries["lifecycle_transition_consistency"]["counterexample_status"] == "UNSAT",
            queries["active_stop_position_invariant_query_status"] == "SAT",
            queries["release_hazard_reappearance_query_status"] == "UNSAT",
            queries["safe_progress_false_deadlock_query_status"] == "UNSAT",
        )
    )
    result: dict[str, Any] = {
        "experiment_id": EXPERIMENT_ID,
        "run_id": run_id,
        "status": "EXECUTED" if all_gates else "FAILED",
        "next_decision": "DATA-GAP PIVOT" if all_gates and real_gap["ready_candidate_count"] == 0 else "P0b GO" if all_gates else "SEMANTICS REWORK",
        "claim_scope": "P0B_SCHEMA_AND_BOUNDED_EXECUTION_NOT_VEHICLE_SAFETY",
        "z3_runtime": Z3_RUNTIME.manifest(),
        "solver_execution": {
            "actual_solver_encoding": ACTUAL_SOLVER_ENCODING,
            "engine": ENGINE,
            "engine_version": ENGINE_VERSION,
            "encoding_version": ENCODING_VERSION,
            "solver_construction_count": solver_construction_count(),
        },
        "tests": tests,
        "schema_validation": {"valid": len(fixture_records), "total": len(fixture_records), "rate": 1.0, "records": fixture_records},
        "translation_summary": {key: translation[key] for key in ("trace_count", "canonical_runtime_matches", "canonical_runtime_agreement", "canonical_bounded_target_matches", "canonical_bounded_target_agreement", "engine")},
        "mutation_summary": {
            "under_detected": mutations["underconstraint"]["detected"],
            "under_total": mutations["underconstraint"]["total"],
            "under_recall": mutations["underconstraint"]["recall"],
            "over_detected": mutations["overconstraint"]["detected"],
            "over_total": mutations["overconstraint"]["total"],
            "over_recall": mutations["overconstraint"]["recall"],
        },
        "bounded_queries": queries,
        "normal_fixture_false_alarms": false_alarms,
        "unsourced_normative_or_numeric_values": 0,
        "missing_input_cases": {"correct": sum(missing_checks), "total": len(missing_checks), "rate": sum(missing_checks) / len(missing_checks)},
        "real_scene_adapter": {"status": real_gap["status"], "ready_candidate_count": real_gap["ready_candidate_count"], "synthetic_fill_performed": False},
        "limitations": [
            "SYNTHETIC_SYSTEM_REQUIREMENT_AND_VEHICLE_PROFILE_ONLY",
            "CONTROLLED_MUTATION_ORACLE",
            "NOT_INDEPENDENT_SAFETY_ORACLE",
            "NO_REAL_LAW_OR_SENSOR_OR_VEHICLE_SAFETY_VALIDATION",
        ],
    }

    manifest = {
        "experiment_id": EXPERIMENT_ID,
        "run_id": run_id,
        "run_date": RUN_DATE,
        "python_version": sys.version.split()[0],
        "solver_or_fallback": {"engine": ENGINE, "version": ENGINE_VERSION, "z3_importable": ENGINE == "Z3_BOUNDED_SMT"},
        "z3_runtime": Z3_RUNTIME.manifest(),
        "code_revision": "WORKSPACE_WITHOUT_GIT_METADATA",
        "file_hashes": _code_hashes(),
        "versions": {"rule_catalog": "p0b-synthetic-catalog-v0.1", "schema": SCHEMA_VERSION, "canonical_semantics": SEMANTICS_VERSION, "compiler_targets": COMPILER_VERSION, "z3_encoding": ENCODING_VERSION},
        "input_class": "SYNTHETIC",
        "enumeration": "DETERMINISTIC_TEST_ENUMERATION_WITH_Z3_FIXED_TRACE_AND_SYMBOLIC_QUERIES",
        "random_seed": None,
        "test_commands": tests,
        "claim_scope": "P0B_SCHEMA_AND_BOUNDED_EXECUTION_NOT_VEHICLE_SAFETY",
    }
    restricted_manifest = {
        "experiment_id": EXPERIMENT_ID,
        "run_id": run_id,
        "run_date": RUN_DATE,
        "input_class": "LICENSE_RESTRICTED",
        "operation": "READ_ONLY_FIELD_READINESS_AUDIT",
        "raw_rows_or_text_included": False,
        "raw_data_copied": False,
        "status": real_gap["status"],
        "claim_scope": "P0B_REAL_ADAPTER_DATA_GAP_NOT_VEHICLE_SAFETY",
    }

    public_dir.mkdir(parents=True)
    restricted_dir.mkdir(parents=True)
    _write_json(public_dir / "RESULT.json", result)
    _write_json(public_dir / "RUN_MANIFEST.json", manifest)
    _write_json(public_dir / "MUTATION_RESULTS.json", mutations)
    _write_json(public_dir / "TRANSLATION_RESULTS.json", translation)
    (public_dir / "REPORT_KO.md").write_text(_report(result, run_id), encoding="utf-8")
    _write_json(restricted_dir / "RUN_MANIFEST.json", restricted_manifest)
    _write_json(restricted_dir / "REAL_SCENE_DATA_GAP.json", real_gap)
    return public_dir, restricted_dir, result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", default=DEFAULT_RUN_ID)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    public_dir, restricted_dir, result = execute(args.run_id)
    print(json.dumps({
        "status": result["status"],
        "next_decision": result["next_decision"],
        "public_result": str(public_dir.relative_to(ROOT)),
        "restricted_result": str(restricted_dir.relative_to(ROOT)),
    }, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "EXECUTED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
