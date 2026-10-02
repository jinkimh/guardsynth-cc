"""Freeze and verify the scoped EBLC v0.2 release candidate."""

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

from guard_synth_eblc import (
    BUNDLE_VERSION,
    CNL_LANGUAGE_VERSION,
    CNL_RENDERER_VERSION,
    CORE_GRAMMAR_VERSION,
    CORE_SMT_COMPILER_VERSION,
    LATEST_PROGRAM_VERSION,
)
from guard_synth_eblc.adapters.synthetic_pedestrian import (
    PILOT_PROFILE,
    frame,
    initial_frame,
)
from guard_synth_eblc.binders import bind_pedestrian_contract
from guard_synth_eblc.bundle_conformance import compare_bundle_trace
from guard_synth_eblc.catalog import load_pilot_rule, load_predicate_spec
from guard_synth_eblc.cnl_renderer import export_cnl, render_bundle, render_program
from guard_synth_eblc.conformance import generated_p0b_conformance_suite, validate_conformance
from guard_synth_eblc.examples import synthetic_bundle_v02, synthetic_program_v02
from guard_synth_eblc.types import Truth
from cli.checks.project_integrity import broken_markdown_links


EXPERIMENT_ID = "EBLC-RELEASE-CANDIDATE-001"
DEFAULT_RUN_ID = "eblc-v0.2-rc1-2026-08-09"
RUN_DATE = date.today().isoformat()
CLAIM_SCOPE = "EBLC_V02_LANGUAGE_AND_TOOLING_RELEASE_CANDIDATE_NOT_VEHICLE_SAFETY"

STABLE_BASELINE_MODULES = (
    "platforms/eblc-bcv/tests/unit/test_composition_compilation.py",
    "platforms/eblc-bcv/tests/unit/test_composition_v02_derivation.py",
    "platforms/eblc-bcv/tests/unit/test_core_smt_compiler.py",
    "platforms/eblc-bcv/tests/unit/test_derivation_compiler.py",
    "platforms/eblc-bcv/tests/unit/test_elaboration_conformance.py",
    "platforms/eblc-bcv/tests/unit/test_indexed_collection.py",
    "platforms/eblc-bcv/tests/unit/test_program_v02_typed_derivation.py",
    "platforms/eblc-bcv/tests/unit/test_public_layout.py",
    "projects/04-guardsynth-coc/tests/integration/test_real_scene_adapter.py",
    "platforms/eblc-bcv/tests/robustness/test_robustness.py",
    "platforms/eblc-bcv/tests/translation/test_scenario_matrix.py",
    "platforms/eblc-bcv/tests/unit/test_schema_binding.py",
    "platforms/eblc-bcv/tests/unit/test_semantics.py",
    "platforms/eblc-bcv/tests/mutation/test_translation_mutations.py",
)


TRACEABILITY = (
    ("REQ-TRUTH", "Four-valued fact truth", "SUPPORTED", "types.py; semantics.py"),
    ("REQ-EPISTEMIC", "Observed/predicted/derived/claimed evidence kinds", "SUPPORTED", "types.py; program.py"),
    ("REQ-VERDICT", "Validated/review/unsupported/conflict verdicts", "SUPPORTED", "types.py; semantics.py"),
    ("REQ-LIFECYCLE", "Activation, maintenance, release, reactivation and expiry", "SUPPORTED", "semantics.py; elaborator.py"),
    ("REQ-RULE", "Source/version/scope/precondition/exception RuleTemplate representation", "SUPPORTED", "types.py; rule_template.schema.json"),
    ("REQ-BINDING", "Target-zone binding with ambiguity reasons", "SUPPORTED", "binders.py; indexed_collection.py"),
    ("REQ-PARTIAL", "Value/Interval/Set/Unsupported binder results", "SUPPORTED", "types.py; binders.py"),
    ("REQ-OBSERVABILITY", "Freshness and failure-to-UNKNOWN contract", "SUPPORTED", "semantics.py; elaborator.py"),
    ("REQ-EVIDENCE", "Evidence refs and typed parameter derivation DAG", "SUPPORTED", "derivation.py; program.py"),
    ("REQ-PRIORITY", "Non-scalar priority and action composition", "SUPPORTED", "composition.py; bundle_elaborator.py"),
    ("REQ-CORE-SMT", "High-level EBLC to typed Core to bounded SMT", "SUPPORTED", "elaborator.py; smt_compiler.py"),
    ("REQ-TARGETS", "Canonical/runtime/Z3 translation agreement", "SUPPORTED", "translation_validator.py; conformance.py"),
    ("REQ-BCV", "Controlled under/overconstraint mutation witnesses", "SUPPORTED", "mutations.py"),
    ("REQ-MULTI", "Multi-contract and indexed actor-zone expansion", "SUPPORTED", "composition.py; indexed_collection.py"),
    ("REQ-CNL", "Deterministic EBLC-to-CNL prompt projection", "SUPPORTED", "cnl_renderer.py"),
    ("REQ-EXCEPTION-ALGEBRA", "General operational exception algebra", "DEFERRED_V0_3", "Rule field is represented; general execution algebra is not"),
    ("REQ-QUANTIFIERS", "Unbounded collections and quantifiers", "OUT_OF_SCOPE_V0_2", "Use finite indexed collections"),
    ("REQ-HYBRID", "Continuous/hybrid dynamics and unbounded time", "OUT_OF_SCOPE_V0_2", "Bounded discrete semantics only"),
    ("REQ-NL-GENERATOR", "CoC/natural-language to source-grounded EBLC generation", "NEXT_LAYER_GUARDSYNTH", "Not part of EBLC execution language"),
    ("REQ-REAL-ASSURANCE", "Perception association and vehicle assurance authoring", "DATA_ADAPTER_GAP", "No values are inferred or defaulted"),
    ("REQ-SAFETY-PROOF", "Independent vehicle-safety proof", "NOT_CLAIMED", "Requires independent physics/simulator/vehicle evidence"),
)


def _write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _test(command: list[str]) -> dict[str, Any]:
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


def _portable(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def _hashes(paths: list[Path]) -> dict[str, str]:
    return {
        _portable(path): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in paths
    }


def _conformance_probe(program) -> dict[str, Any]:
    outcome = bind_pedestrian_contract(
        load_pilot_rule(), load_predicate_spec(), initial_frame(), PILOT_PROFILE
    )
    if outcome.contract is None:
        raise RuntimeError(f"synthetic binding failed: {outcome.reason_codes}")
    result = validate_conformance(
        outcome.contract, program, generated_p0b_conformance_suite()
    )
    return {
        "trace_count": result["trace_count"],
        "matching_traces": result["matching_traces"],
        "trace_agreement": result["trace_agreement"],
        "frame_count": result["frame_count"],
        "matching_frames": result["matching_frames"],
        "frame_agreement": result["frame_agreement"],
        "limitations": result["limitations"],
    }


def _bundle_probe(bundle) -> dict[str, Any]:
    outcome = bind_pedestrian_contract(
        load_pilot_rule(), load_predicate_spec(), initial_frame(), PILOT_PROFILE
    )
    if outcome.contract is None:
        raise RuntimeError(f"synthetic binding failed: {outcome.reason_codes}")
    contracts = {
        item.contract_id: replace(outcome.contract, contract_id=item.contract_id)
        for item in bundle.contracts
    }
    trace = (frame(0.0, Truth.TRUE),)
    result = compare_bundle_trace(
        bundle, contracts, {contract_id: trace for contract_id in contracts}
    )
    return {
        "matches": result["matches"],
        "mismatches": result["mismatches"],
        "canonical": result["canonical"],
        "core_smt": result["core_smt"],
    }


def _traceability_record() -> dict[str, Any]:
    entries = [
        {"requirement_id": item[0], "requirement": item[1], "status": item[2], "implementation_or_boundary": item[3]}
        for item in TRACEABILITY
    ]
    return {
        "release": "EBLC-v0.2-rc1",
        "scope_decision": "FEATURE_COMPLETE_SCOPED_RELEASE_CANDIDATE",
        "entries": entries,
        "counts": {
            status: sum(entry["status"] == status for entry in entries)
            for status in sorted({entry["status"] for entry in entries})
        },
    }


def _report(result: dict[str, Any]) -> str:
    tests = result["tests"]
    return f"""# EBLC v0.2 scoped release candidate 보고서

- 상태: **{result['status']}**
- release decision: `{result['release_decision']}`
- run ID: `{result['run_id']}`
- solver: project-local Z3 `{result['z3_runtime']['version']}`
- 주장 범위: `{CLAIM_SCOPE}`

## 검증 결과

| 항목 | 결과 |
|---|---:|
| 동결 전 EBLC 기준선 | {tests['stable_baseline']['passed_count']}/{tests['stable_baseline']['test_count']} |
| CNL renderer 신규 테스트 | {tests['cnl_renderer']['passed_count']}/{tests['cnl_renderer']['test_count']} |
| 전체 EBLC 테스트 | {tests['full_eblc']['passed_count']}/{tests['full_eblc']['test_count']} |
| P0a 회귀 | {tests['p0a']['passed_count']}/{tests['p0a']['test_count']} |
| 프로젝트 구조/문서 링크 | {tests['structure']['passed_count']}/{tests['structure']['test_count']} |
| program canonical–Core-SMT | {result['conformance']['matching_traces']}/{result['conformance']['trace_count']} traces, {result['conformance']['matching_frames']}/{result['conformance']['frame_count']} frames |
| bundle canonical–Core-SMT | {'일치' if result['bundle_probe']['matches'] else '불일치'} |

## 동결 판단

EBLC v0.2는 bounded discrete contract 표현, lifecycle, evidence/derivation,
non-scalar composition, indexed actor-zone expansion, Core/SMT lowering 및 결정론적
CNL projection 범위에서 **scoped feature complete RC**로 동결한다. CNL은 모델 입력을
위한 읽기 표현이며 구조화 EBLC를 실행 권위로 대체하지 않는다.

자연어 CoC에서 source-aware 계약을 만드는 기능은 다음 GuardSynth generator 계층이다.
일반 exception algebra, quantifier, continuous/hybrid dynamics는 v0.2 완료 조건이 아니며
traceability에서 명시적으로 이관했다. 실제 association, 법규 근거, 차량 assurance 및
차량 안전성은 이 실행이 입증하지 않는다.
"""


def execute(run_id: str) -> tuple[Path, dict[str, Any]]:
    output = ROOT / "artifacts/results/public/eblc-release-candidate-001" / run_id
    if output.exists():
        raise FileExistsError(f"refusing to overwrite existing run: {run_id}")
    output.mkdir(parents=True)

    program = synthetic_program_v02()
    bundle = synthetic_bundle_v02()
    program_cnl = render_program(program)
    bundle_cnl = render_bundle(bundle)
    export_cnl(
        program_cnl, output,
        text_name="PROGRAM_CONSTRAINTS.txt", mapping_name="PROGRAM_CNL_MAPPING.json",
    )
    export_cnl(
        bundle_cnl, output,
        text_name="BUNDLE_CONSTRAINTS.txt", mapping_name="BUNDLE_CNL_MAPPING.json",
    )
    _write_json(output / "INPUT_PROGRAM.json", program.raw)
    _write_json(output / "INPUT_BUNDLE.json", bundle.raw)

    conformance = _conformance_probe(program)
    bundle_probe = _bundle_probe(bundle)
    traceability = _traceability_record()
    _write_json(output / "CONFORMANCE_SUMMARY.json", conformance)
    _write_json(output / "BUNDLE_CONFORMANCE.json", bundle_probe)
    _write_json(output / "REQUIREMENT_TRACEABILITY.json", traceability)
    # The documentation checker resolves the canonical result link during the
    # run; the final report replaces this in-run marker after all gates exist.
    (output / "REPORT_KO.md").write_text(
        "# EBLC v0.2 release candidate\n\nRC gate execution in progress.\n",
        encoding="utf-8",
    )

    tests = {
        "stable_baseline": _test(["python3", "-m", "unittest", *STABLE_BASELINE_MODULES, "-v"]),
        "cnl_renderer": _test(["python3", "-m", "unittest", "platforms/eblc-bcv/tests/unit/test_cnl_renderer.py", "-v"]),
        "full_eblc": _test(["python3", "-m", "unittest", "discover", "-s", "platforms/eblc-bcv/tests", "-p", "test_*.py", "-v"]),
        "p0a": _test(["python3", "-m", "unittest", "experiments.eblc_pilot.test_pilot", "-v"]),
        "structure": _test(["python3", "-m", "unittest", "tests.structure.test_project_layout", "-v"]),
    }
    link_gaps = list(broken_markdown_links(ROOT))
    gates = {
        "stable_baseline_128_of_128": tests["stable_baseline"]["passed"] and tests["stable_baseline"]["test_count"] == 128,
        "cnl_renderer_10_of_10": tests["cnl_renderer"]["passed"] and tests["cnl_renderer"]["test_count"] == 10,
        "full_current_suite_at_least_rc_138": (
            tests["full_eblc"]["passed"]
            and tests["full_eblc"]["test_count"] is not None
            and tests["full_eblc"]["test_count"] >= 138
        ),
        "p0a_7_of_7": tests["p0a"]["passed"] and tests["p0a"]["test_count"] == 7,
        "structure_8_of_8": tests["structure"]["passed"] and tests["structure"]["test_count"] == 8,
        "program_translation_agreement": conformance["trace_agreement"] == 1.0 and conformance["frame_agreement"] == 1.0,
        "bundle_translation_agreement": bundle_probe["matches"],
        "cnl_program_full_top_level_coverage": not program_cnl.omitted_paths,
        "cnl_bundle_full_top_level_coverage": not bundle_cnl.omitted_paths,
        "documentation_links": not link_gaps,
        "project_local_z3_5": Z3_RUNTIME.version == "5.0.0",
    }
    passed = all(gates.values())
    result = {
        "experiment_id": EXPERIMENT_ID,
        "run_id": run_id,
        "run_date": RUN_DATE,
        "status": "EXECUTED" if passed else "FAILED",
        "release_decision": "EBLC_V02_FEATURE_COMPLETE_SCOPED_RC1" if passed else "SEMANTICS_OR_RELEASE_REWORK",
        "claim_scope": CLAIM_SCOPE,
        "input_class": "SYNTHETIC",
        "versions": {
            "program": LATEST_PROGRAM_VERSION,
            "bundle": BUNDLE_VERSION,
            "core": CORE_GRAMMAR_VERSION,
            "core_smt_compiler": CORE_SMT_COMPILER_VERSION,
            "cnl_renderer": CNL_RENDERER_VERSION,
            "cnl_language": CNL_LANGUAGE_VERSION,
        },
        "z3_runtime": Z3_RUNTIME.manifest(),
        "cnl": {
            "program_input_sha256": program_cnl.input_sha256,
            "program_output_sha256": program_cnl.output_sha256,
            "bundle_input_sha256": bundle_cnl.input_sha256,
            "bundle_output_sha256": bundle_cnl.output_sha256,
            "authority_boundary": "STRUCTURED_EBLC_REMAINS_EXECUTION_AUTHORITY",
        },
        "conformance": conformance,
        "bundle_probe": bundle_probe,
        "traceability_counts": traceability["counts"],
        "tests": tests,
        "documentation_link_gaps": link_gaps,
        "gates": gates,
        "limitations": [
            "BOUNDED_DISCRETE_SEMANTICS",
            "SYNTHETIC_PUBLIC_FIXTURES",
            "CNL_IS_ONE_WAY_NON_AUTHORITATIVE_PROJECTION",
            "NOT_AN_INDEPENDENT_SAFETY_ORACLE",
            "NOT_A_VEHICLE_SAFETY_PROOF",
        ],
    }
    hash_paths = [
        ROOT / "platforms/eblc-bcv/src/guard_synth_eblc/cnl_renderer.py",
        ROOT / "platforms/eblc-bcv/src/guard_synth_eblc/fixtures/eblc_program_p0b_v0_2.json",
        ROOT / "platforms/eblc-bcv/tests/test_cnl_renderer.py",
        ROOT / "docs/specifications/eblc/EBLC_LANGUAGE_SPEC_V02.md",
        ROOT / "docs/guides/eblc/EBLC_USER_GUIDE_V02.md",
        ROOT / "docs/reports/EBLC_REQUIREMENT_TRACEABILITY_V02.md",
        ROOT / "docs/releases/EBLC_RELEASE_NOTES_V02.md",
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
        "enumeration": "DETERMINISTIC_FIXTURES_AND_GENERATED_BOUNDED_CONFORMANCE",
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
    parser.add_argument("--run-id", default=DEFAULT_RUN_ID)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output, result = execute(args.run_id)
    print(json.dumps({
        "status": result["status"],
        "release_decision": result["release_decision"],
        "result": output.relative_to(ROOT).as_posix(),
        "full_eblc": result["tests"]["full_eblc"],
    }, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "EXECUTED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
