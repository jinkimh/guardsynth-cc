"""Run adversarial EBLC probes and persist an explicit gap report."""

from __future__ import annotations

import argparse
import ast
from copy import deepcopy
from dataclasses import replace
from datetime import date
import hashlib
from itertools import product
import json
import math
from pathlib import Path
import sys
from typing import Any, Callable


from cli.project_paths import project_root

ROOT = project_root(__file__)
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cli.solver_runtime import configure_project_z3

Z3_RUNTIME = configure_project_z3(ROOT)

from guard_synth_eblc import SCHEMA_VERSION, SEMANTICS_VERSION
from guard_synth_eblc.adapters.synthetic_pedestrian import PILOT_PROFILE, frame, initial_frame
from guard_synth_eblc.binders import bind_pedestrian_contract
from guard_synth_eblc.catalog import SCHEMA_ROOT, load_pilot_rule, load_predicate_spec
from guard_synth_eblc.mutations import run_mutation_suite
from guard_synth_eblc.runtime_monitor import run_runtime
from guard_synth_eblc.schema_validation import SchemaValidationError, load_json, validate
from guard_synth_eblc.semantics import run_canonical
from guard_synth_eblc.translation_validator import normalized
from guard_synth_eblc.types import Truth, Verdict
from guard_synth_eblc.z3_bounded_checker import ENGINE, run_bounded_target


DEFAULT_RUN_ID = "robustness-2026-08-08-v1"
RUN_DATE = date.today().isoformat()


def _record(
    probe_id: str,
    passed: bool,
    expected: str,
    observed: Any,
    severity: str,
) -> dict[str, Any]:
    return {
        "probe_id": probe_id,
        "passed": passed,
        "expected": expected,
        "observed": observed,
        "severity_if_failed": severity,
    }


def _raises(action: Callable[[], Any], exception: type[Exception]) -> bool:
    try:
        action()
    except exception:
        return True
    return False


def run_audit() -> dict[str, Any]:
    rule = load_pilot_rule()
    predicate = load_predicate_spec()
    binding = bind_pedestrian_contract(rule, predicate, initial_frame(), PILOT_PROFILE)
    if binding.contract is None:
        raise RuntimeError("locked public contract no longer binds")
    contract = binding.contract
    probes: list[dict[str, Any]] = []

    context_schema = load_json(SCHEMA_ROOT / "context_graph.schema.json")
    context = {
        "timestamp_s": 0.0,
        "hazard_fact": {"truth": "TRUE", "epistemic_kind": "OBSERVED", "source": "SYNTHETIC", "timestamp_s": 0.0, "maximum_age_s": 0.2},
        "ego_front_x_m": -12.0,
        "ego_speed_mps": 6.0,
        "zone_entry_x_m": 0.0,
        "target_entity_id": "pedestrian:P17",
        "zone_id": "zone:CZ4",
        "coordinate_frame": "ego_path_s",
        "distance_unit": "m",
    }
    extra = deepcopy(context); extra["silent_default"] = 1
    rejected = _raises(lambda: validate(extra, context_schema), SchemaValidationError)
    probes.append(_record("SCHEMA_REJECTS_ADDITIONAL_PROPERTY", rejected, "REJECT", "REJECT" if rejected else "ACCEPT", "HIGH"))

    nan_context = deepcopy(context); nan_context["ego_speed_mps"] = math.nan
    rejected = _raises(lambda: validate(nan_context, context_schema), SchemaValidationError)
    probes.append(_record("SCHEMA_REJECTS_NONFINITE_NUMBER", rejected, "REJECT", "REJECT" if rejected else "ACCEPT", "HIGH"))

    unsupported_keyword = _raises(
        lambda: validate({}, {"type": "object", "patternProperties": {}}),
        SchemaValidationError,
    )
    probes.append(_record("SCHEMA_FAILS_CLOSED_ON_UNKNOWN_KEYWORD", unsupported_keyword, "REJECT", "REJECT" if unsupported_keyword else "ACCEPT", "MEDIUM"))

    nan_profile = replace(PILOT_PROFILE, maximum_service_deceleration_mps2=math.nan)
    nan_binding = bind_pedestrian_contract(rule, predicate, initial_frame(), nan_profile)
    profile_rejected = nan_binding.verdict is Verdict.UNSUPPORTED
    probes.append(_record("BINDER_REJECTS_NONFINITE_VEHICLE_PROFILE", profile_rejected, "UNSUPPORTED", nan_binding.verdict.value, "CRITICAL"))

    nan_frame = frame(0.0, Truth.TRUE, x=-12.0, speed=math.nan)
    nan_results = {
        "canonical": normalized(run_canonical(contract, (nan_frame,))),
        "runtime": normalized(run_runtime(contract, (nan_frame,))),
        "bounded": normalized(run_bounded_target(contract, (nan_frame,))),
    }
    nan_rejected = all(not item["accepted"] for item in nan_results.values())
    probes.append(_record("MONITORS_REJECT_NONFINITE_SCENE_VALUE", nan_rejected, "ALL_REJECT", {key: value["accepted"] for key, value in nan_results.items()}, "CRITICAL"))

    empty = {
        "canonical": normalized(run_canonical(contract, ())),
        "runtime": normalized(run_runtime(contract, ())),
        "bounded": normalized(run_bounded_target(contract, ())),
    }
    empty_rejected = all(not item["accepted"] for item in empty.values())
    probes.append(_record("MONITORS_REJECT_EMPTY_TRACE", empty_rejected, "ALL_REJECT", {key: value["accepted"] for key, value in empty.items()}, "HIGH"))

    reversed_trace = (
        frame(0.1, Truth.TRUE, x=-12.0, speed=0.0),
        frame(0.0, Truth.FALSE, x=-12.0, speed=0.0),
    )
    reversed_results = {
        "canonical": normalized(run_canonical(contract, reversed_trace)),
        "runtime": normalized(run_runtime(contract, reversed_trace)),
        "bounded": normalized(run_bounded_target(contract, reversed_trace)),
    }
    reversed_rejected = all(not item["accepted"] for item in reversed_results.values())
    probes.append(_record("MONITORS_REJECT_NONMONOTONIC_TIMESTAMPS", reversed_rejected, "ALL_REJECT", {key: value["accepted"] for key, value in reversed_results.items()}, "HIGH"))

    required = set(load_json(SCHEMA_ROOT / "eblc_contract.schema.json")["required"])
    runtime_fields = {
        "derivation_dag",
        "predicate_maximum_age_s",
        "maximum_service_deceleration_mps2",
        "response_time_s",
        "position_uncertainty_m",
    }
    missing_runtime_fields = sorted(runtime_fields - required)
    probes.append(_record("CONTRACT_SCHEMA_COVERS_RUNTIME_PARAMETERS", not missing_runtime_fields, "NO_MISSING_FIELDS", missing_runtime_fields, "HIGH"))

    agreement_count = 0
    disagreement_examples = []
    for sequence in product(tuple(Truth), repeat=5):
        frames = tuple(frame(i * 0.1, truth, x=-12.0, speed=0.0) for i, truth in enumerate(sequence))
        canonical = normalized(run_canonical(contract, frames))
        runtime = normalized(run_runtime(contract, frames))
        bounded = normalized(run_bounded_target(contract, frames))
        if canonical == runtime == bounded:
            agreement_count += 1
        elif len(disagreement_examples) < 3:
            disagreement_examples.append([truth.value for truth in sequence])
    probes.append(_record("EXHAUSTIVE_FOUR_VALUED_LENGTH5_AGREEMENT", agreement_count == 4 ** 5, str(4 ** 5), {"matches": agreement_count, "examples": disagreement_examples}, "CRITICAL"))

    mutations = run_mutation_suite(contract)
    mutation_detected = mutations["underconstraint"]["detected"] + mutations["overconstraint"]["detected"]
    probes.append(_record("CONTROLLED_MUTATIONS_DETECTED", mutation_detected == 10, "10/10", f"{mutation_detected}/10", "HIGH"))

    independent = True
    imported_modules: dict[str, list[str]] = {}
    for name in ("runtime_monitor.py", "z3_bounded_checker.py"):
        tree = ast.parse((SRC / "guard_synth_eblc" / name).read_text(encoding="utf-8"))
        imported = sorted({node.module or "" for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)})
        imported_modules[name] = imported
        independent &= not any(module.endswith("semantics") for module in imported)
    probes.append(_record("TARGETS_DO_NOT_IMPORT_CANONICAL_SEMANTICS", independent, "NO_CANONICAL_IMPORT", imported_modules, "CRITICAL"))

    checker_tree = ast.parse(
        (SRC / "guard_synth_eblc/z3_bounded_checker.py").read_text(encoding="utf-8")
    )
    z3_solver_calls = sorted({
        node.func.attr
        for node in ast.walk(checker_tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "z3"
        and node.func.attr in {"Solver", "SolverFor", "Optimize", "Fixedpoint"}
    })
    probes.append(_record(
        "Z3_ENGINE_HAS_ACTUAL_SOLVER_ENCODING",
        bool(z3_solver_calls),
        "AT_LEAST_ONE_Z3_SOLVER_CONSTRUCTION",
        z3_solver_calls,
        "CRITICAL",
    ))

    p0b_runner_text = (
        ROOT / "cli/pipelines/eblc/p0b_schema_bcv/run.py"
    ).read_text(encoding="utf-8")
    unconditional_no_z3_text = "현재 환경에는 z3-solver가 없어" in p0b_runner_text
    probes.append(_record(
        "REPORT_ENGINE_DESCRIPTION_IS_ENVIRONMENT_CONDITIONAL",
        not unconditional_no_z3_text,
        "REPORT_TEXT_DERIVED_FROM_ENGINE",
        "UNCONDITIONAL_NO_Z3_TEXT" if unconditional_no_z3_text else "CONDITIONAL",
        "HIGH",
    ))

    failed = [probe for probe in probes if not probe["passed"]]
    return {
        "experiment_id": "EBLC-ROBUSTNESS-AUDIT-001",
        "status": "EXECUTED_WITH_GAPS" if failed else "EXECUTED_NO_GAPS_DETECTED",
        "engine": ENGINE,
        "z3_runtime": Z3_RUNTIME.manifest(),
        "probe_count": len(probes),
        "passed_probe_count": len(probes) - len(failed),
        "gap_count": len(failed),
        "gaps_by_severity": {
            severity: sum(probe["severity_if_failed"] == severity for probe in failed)
            for severity in ("CRITICAL", "HIGH", "MEDIUM", "LOW")
        },
        "probes": probes,
        "claim_scope": "ADVERSARIAL_SOFTWARE_ROBUSTNESS_AUDIT_NOT_VEHICLE_SAFETY_VALIDATION",
    }


def _report(result: dict[str, Any], run_id: str) -> str:
    failed = [probe for probe in result["probes"] if not probe["passed"]]
    lines = [
        "# EBLC 공개 구현 강건성 감사",
        "",
        f"- run ID: `{run_id}`",
        f"- 상태: **{result['status']}**",
        f"- 통과 probe: {result['passed_probe_count']}/{result['probe_count']}",
        f"- 발견 gap: {result['gap_count']}",
        "- 범위: software robustness only; 차량 안전성 검증 아님",
        "",
        "## 발견된 gap",
        "",
    ]
    if not failed:
        lines.append("없음")
    else:
        for probe in failed:
            lines.append(f"- `{probe['probe_id']}` ({probe['severity_if_failed']}): expected {probe['expected']}, observed `{json.dumps(probe['observed'], sort_keys=True)}`")
    interpretation = (
        "이번 고정 probe 집합에서는 fail-closed gap이 검출되지 않았다. 이는 명시된 software robustness 범위의 결과이며 실제 차량 안전성 검증은 아니다."
        if not failed
        else "translation agreement와 controlled mutation 검출은 별도 의미론 target 간 일치를 보여주지만, 모든 target이 공유하는 입력 검증 공백을 제거하지는 않는다. gap은 사후 기대값 변경 없이 그대로 기록했다."
    )
    lines.extend(("", "## 해석", "", interpretation, ""))
    return "\n".join(lines)


def write_run(run_id: str) -> Path:
    output = ROOT / "artifacts/results/public/eblc-robustness-audit-001" / run_id
    if output.exists():
        raise FileExistsError(f"refusing to overwrite existing audit run: {run_id}")
    result = run_audit()
    output.mkdir(parents=True)
    (output / "RESULT.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (output / "REPORT_KO.md").write_text(_report(result, run_id), encoding="utf-8")
    manifest = {
        "experiment_id": result["experiment_id"],
        "run_id": run_id,
        "run_date": RUN_DATE,
        "python_version": sys.version.split()[0],
        "schema_version": SCHEMA_VERSION,
        "semantics_version": SEMANTICS_VERSION,
        "engine": ENGINE,
        "z3_runtime": Z3_RUNTIME.manifest(),
        "input_class": "SYNTHETIC_ADVERSARIAL",
        "deterministic_enumeration": True,
        "audit_script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "claim_scope": result["claim_scope"],
    }
    (output / "RUN_MANIFEST.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return output


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run deterministic adversarial EBLC robustness probes.")
    parser.add_argument("--run-id", default=DEFAULT_RUN_ID)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output = write_run(args.run_id)
    result = json.loads((output / "RESULT.json").read_text(encoding="utf-8"))
    print(json.dumps({
        "status": result["status"],
        "passed_probe_count": result["passed_probe_count"],
        "probe_count": result["probe_count"],
        "gap_count": result["gap_count"],
        "output": str(output.relative_to(ROOT)),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
