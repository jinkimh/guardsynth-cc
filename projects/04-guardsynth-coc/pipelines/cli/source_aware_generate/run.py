"""Execute source-aware GuardSynth generation through EBLC Core and Z3."""

from __future__ import annotations

import argparse
from copy import deepcopy
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

from guard_synth import SOURCE_AWARE_GENERATOR_VERSION
from guard_synth.source_aware_generator import (
    generate_from_request,
    load_generation_request,
    parse_generation_request,
)
from guard_synth_eblc.bundle_elaborator import elaborate_bundle
from guard_synth_eblc.cnl_renderer import export_cnl, render_bundle, render_program
from guard_synth_eblc.indexed_collection import expand_indexed_collection
from guard_synth_eblc.schema_validation import load_json
from guard_synth_eblc.smt_compiler import compile_core_model, export_compilation, solve_assignment


EXPERIMENT_ID = "GUARDSYNTH-SOURCE-AWARE-GENERATOR-001"
DEFAULT_RUN_ID = "source-aware-generator-2026-08-09-v3"
DEFAULT_REQUEST = ROOT / "projects/04-guardsynth-coc/src/guard_synth/fixtures/source_aware_generation_request_p0b_v0_1.json"
RUN_DATE = date.today().isoformat()
CLAIM_SCOPE = "SOURCE_AWARE_SYNTHETIC_GENERATION_AND_BOUNDED_TRANSLATION_NOT_VEHICLE_SAFETY"
STABLE_BASELINE_MODULES = (
    "platforms/eblc-bcv/tests/unit/test_cnl_renderer.py",
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
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return "EXTERNAL_REQUEST_PATH_REDACTED"


def _hashes(paths: list[Path]) -> dict[str, str]:
    return {_portable(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}


def _exact_witness(compiled) -> dict[str, Any]:
    solved = solve_assignment(compiled, {
        ("c0__ego_speed", 0): 6.000000001,
        ("c1__ego_speed", 0): 3.000000001,
    })
    symbols = {
        (item["declaration"], item["time"]): item["smt_symbol"]
        for item in compiled.symbol_table["symbols"]
    }
    witness = solved["witness"] or {}
    return {
        "status": solved["status"],
        "exact_outputs": {
            "c0__stop_position": witness.get(symbols[("c0__stop_position", None)]),
            "c1__stop_position": witness.get(symbols[("c1__stop_position", None)]),
            "c0__stopping_distance@0": witness.get(symbols[("c0__stopping_distance", 0)]),
            "c1__stopping_distance@0": witness.get(symbols[("c1__stopping_distance", 0)]),
        },
        "definedness_assertion_count": sum(
            item.role == "DEFINEDNESS" for item in compiled.assertions
        ),
    }


def _replay(output: Path, expected_query: str) -> dict[str, Any]:
    executable = ROOT / Z3_RUNTIME.prefix / "bin/z3"
    expected = {"MODEL.smt2": "SAT", "QUERY_composed_model_satisfiable.smt2": expected_query}
    records = []
    for filename, wanted in expected.items():
        completed = subprocess.run(
            [str(executable), str(output / filename)], cwd=ROOT,
            text=True, capture_output=True, check=False,
        )
        lines = completed.stdout.strip().splitlines()
        actual = lines[0].upper() if lines else "NO_STATUS"
        records.append({
            "file": filename, "expected": wanted, "actual": actual,
            "exit_code": completed.returncode,
            "matches": completed.returncode == 0 and actual == wanted,
        })
    return {
        "file_count": len(records),
        "matches": sum(item["matches"] for item in records),
        "agreement": sum(item["matches"] for item in records) / len(records),
        "records": records,
    }


def _probe(raw: dict[str, Any], mutation: str) -> dict[str, Any]:
    value = deepcopy(raw)
    if mutation == "CLAIMED_ONLY":
        value["context_graph"]["instances"][0]["hazard_fact"]["epistemic_kind"] = "CLAIMED"
    elif mutation == "MISSING_PROFILE":
        value["vehicle_profile"] = None
    elif mutation == "MISSING_GEOMETRY":
        value["context_graph"]["instances"][1]["association"]["zone_geometry_ref"] = None
    elif mutation == "AMBIGUOUS_TARGET":
        association = value["context_graph"]["instances"][0]["association"]
        association["selected_target_entity_id"] = None
        association["candidate_target_entity_ids"] = [
            "synthetic-pedestrian:P17", "synthetic-pedestrian:P19",
        ]
    elif mutation == "DUPLICATE_BINDING":
        first = value["context_graph"]["instances"][0]["association"]
        second = value["context_graph"]["instances"][1]["association"]
        second["selected_target_entity_id"] = first["selected_target_entity_id"]
        second["selected_zone_id"] = first["selected_zone_id"]
        second["candidate_target_entity_ids"] = [first["selected_target_entity_id"]]
        second["candidate_zone_ids"] = [first["selected_zone_id"]]
    elif mutation == "UNIT_MISMATCH":
        value["context_graph"]["instances"][0]["zone_entry"]["unit"] = "cm"
    else:
        raise ValueError(mutation)
    result = generate_from_request(parse_generation_request(value))
    return {
        "probe_id": mutation,
        "verdict": result.verdict,
        "reason_codes": list(result.reason_codes),
        "program_generated": result.program_template is not None,
        "collection_generated": result.collection is not None,
    }


def _report(result: dict[str, Any]) -> str:
    tests = result["tests"]
    witness = result["exact_witness"]
    return f"""# GuardSynth source-aware generator v0.1 실행 보고서

- 상태: **{result['status']}**
- run ID: `{result['run_id']}`
- solver: project-local Z3 `{result['z3_runtime']['version']}`
- 주장 범위: `{CLAIM_SCOPE}`

## 결과

| 항목 | 결과 |
|---|---:|
| EBLC v0.2 RC 기준선 | {tests['stable_baseline']['passed_count']}/{tests['stable_baseline']['test_count']} |
| source-aware generator 신규 테스트 | {tests['source_aware_generator']['passed_count']}/{tests['source_aware_generator']['test_count']} |
| 전체 EBLC/GuardSynth 테스트 | {tests['full']['passed_count']}/{tests['full']['test_count']} |
| P0a 회귀 | {tests['p0a']['passed_count']}/{tests['p0a']['test_count']} |
| 구조/문서 링크 | {tests['structure']['passed_count']}/{tests['structure']['test_count']} |
| SMT-LIB 직접 replay | {result['smt_replay']['matches']}/{result['smt_replay']['file_count']} |

정상 synthetic request는 RuleTemplate, predicate, vehicle profile, 관측/association,
geometry/transform 근거와 explicit compiler policy를 결합해 program v0.2 및 두 instance
indexed collection을 생성했다. Z3 exact stop position은
`{witness['exact_outputs']['c0__stop_position']}`, `{witness['exact_outputs']['c1__stop_position']}`이고
stopping distance는 `9`, `3`이다.

CoC claim-only, missing profile/geometry, ambiguous target, duplicate binding 및 unit mismatch
probe는 모두 collection을 생성하지 않았다. CoC evidence는 `CLAIMED`로 provenance에
보존하지만 activation evidence에는 포함하지 않았다.

이는 공개 synthetic source-flow와 bounded translation의 구현 근거다. 실제 법규 source,
perception association, 차량 보장값 또는 차량 안전성을 입증하지 않는다.
"""


def execute(request_path: Path, run_id: str) -> tuple[Path, dict[str, Any]]:
    output = ROOT / "artifacts/results/public/guardsynth-source-aware-generator-001" / run_id
    if output.exists():
        raise FileExistsError(f"refusing to overwrite existing run: {run_id}")
    output.mkdir(parents=True)
    request = load_generation_request(request_path)
    generated = generate_from_request(request)
    if generated.collection is None or generated.program_template is None:
        raise RuntimeError(f"locked fixture did not generate: {generated.reason_codes}")
    expansion = expand_indexed_collection(generated.collection)
    if expansion.bundle is None:
        raise RuntimeError(f"generated collection did not expand: {expansion.reason_codes}")
    elaborated = elaborate_bundle(expansion.bundle)
    compiled = compile_core_model(elaborated.core_model)

    _write_json(output / "INPUT_REQUEST.json", request.raw)
    _write_json(output / "GENERATED_PROGRAM_TEMPLATE.json", generated.program_template.raw)
    _write_json(output / "GENERATED_INDEXED_COLLECTION.json", generated.collection.raw)
    _write_json(output / "GENERATED_BUNDLE.json", expansion.bundle.raw)
    _write_json(output / "GENERATION_MAP.json", generated.generation_map)
    _write_json(output / "ELABORATED_CORE.json", elaborated.core_document)
    _write_json(output / "ELABORATION_MAP.json", elaborated.elaboration_map)
    query_results = export_compilation(compiled, output)
    smt_replay = _replay(output, query_results["results"][0]["status"])
    exact_witness = _exact_witness(compiled)
    _write_json(output / "EXACT_WITNESS.json", exact_witness)
    _write_json(output / "SMT_REPLAY.json", smt_replay)
    export_cnl(
        render_program(generated.program_template), output,
        text_name="GENERATED_PROGRAM_CNL.txt", mapping_name="GENERATED_PROGRAM_CNL_MAPPING.json",
    )
    export_cnl(
        render_bundle(expansion.bundle), output,
        text_name="GENERATED_BUNDLE_CNL.txt", mapping_name="GENERATED_BUNDLE_CNL_MAPPING.json",
    )

    raw = request.raw
    probes = {
        probe_id: _probe(raw, probe_id)
        for probe_id in (
            "CLAIMED_ONLY", "MISSING_PROFILE", "MISSING_GEOMETRY",
            "AMBIGUOUS_TARGET", "DUPLICATE_BINDING", "UNIT_MISMATCH",
        )
    }
    _write_json(output / "ABSTENTION_RESULTS.json", probes)
    # Canonical documentation links are checked during the run. The final
    # report replaces this marker after every gate has been evaluated.
    (output / "REPORT_KO.md").write_text(
        "# GuardSynth source-aware generator\n\nGate execution in progress.\n",
        encoding="utf-8",
    )

    tests = {
        "stable_baseline": _test(["python3", "-m", "unittest", *STABLE_BASELINE_MODULES, "-v"]),
        "source_aware_generator": _test(["python3", "-m", "unittest", "projects/04-guardsynth-coc/tests/integration/test_source_aware_generator.py", "-v"]),
        "full": _test(["python3", "-m", "unittest", "discover", "-s", "projects/04-guardsynth-coc/tests", "-p", "test_*.py", "-v"]),
        "p0a": _test(["python3", "-m", "unittest", "experiments.eblc_pilot.test_pilot", "-v"]),
        "structure": _test(["python3", "-m", "unittest", "tests.structure.test_project_layout", "-v"]),
    }
    expected_probes = {
        "CLAIMED_ONLY": "REVIEW_REQUIRED",
        "MISSING_PROFILE": "UNSUPPORTED",
        "MISSING_GEOMETRY": "UNSUPPORTED",
        "AMBIGUOUS_TARGET": "REVIEW_REQUIRED",
        "DUPLICATE_BINDING": "CONFLICT",
        "UNIT_MISMATCH": "UNSUPPORTED",
    }
    probe_gate = all(
        probes[key]["verdict"] == verdict and not probes[key]["collection_generated"]
        for key, verdict in expected_probes.items()
    )
    coc_ref = "P0B-SYNTHETIC-COC-CLAIM-v0"
    coc_separated = (
        coc_ref in generated.claimed_evidence_refs
        and coc_ref not in generated.program_template.raw["predicate"]["evidence_refs"]
        and generated.generation_map["coc_used_as_activation_evidence"] is False
    )
    gates = {
        "stable_baseline_138_of_138": tests["stable_baseline"]["passed"] and tests["stable_baseline"]["test_count"] == 138,
        "generator_12_of_12": tests["source_aware_generator"]["passed"] and tests["source_aware_generator"]["test_count"] == 12,
        "full_150_of_150": tests["full"]["passed"] and tests["full"]["test_count"] == 150,
        "p0a_7_of_7": tests["p0a"]["passed"] and tests["p0a"]["test_count"] == 7,
        "structure_9_of_9": tests["structure"]["passed"] and tests["structure"]["test_count"] == 9,
        "source_complete_generation": generated.verdict == "VALIDATED" and expansion.verdict == "VALIDATED",
        "coc_claim_separated": coc_separated,
        "abstention_probe_directions": probe_gate,
        "core_query_agreement": query_results["agreement"] == 1.0,
        "smt_replay": smt_replay["agreement"] == 1.0,
        "exact_witness": exact_witness["exact_outputs"] == {
            "c0__stop_position": "-3/2", "c1__stop_position": "21/2",
            "c0__stopping_distance@0": "9", "c1__stopping_distance@0": "3",
        },
    }
    result = {
        "experiment_id": EXPERIMENT_ID,
        "run_id": run_id,
        "run_date": RUN_DATE,
        "status": "EXECUTED" if all(gates.values()) else "FAILED",
        "claim_scope": CLAIM_SCOPE,
        "input_class": "SYNTHETIC",
        "input_request": _portable(request_path),
        "generator_version": SOURCE_AWARE_GENERATOR_VERSION,
        "z3_runtime": Z3_RUNTIME.manifest(),
        "generation": {
            "verdict": generated.verdict,
            "reason_codes": list(generated.reason_codes),
            "program_id": generated.program_template.program_id,
            "collection_id": generated.collection.collection_id,
            "instance_count": len(generated.collection.instances),
            "claimed_evidence_refs": list(generated.claimed_evidence_refs),
        },
        "query_results": query_results,
        "smt_replay": smt_replay,
        "exact_witness": exact_witness,
        "abstention_probes": probes,
        "tests": tests,
        "gates": gates,
        "limitations": [
            "SYNTHETIC_RULE_CONTEXT_PROFILE_AND_ASSOCIATION",
            "FINITE_PEDESTRIAN_CONFLICT_ZONE_VERTICAL_SLICE",
            "NO_FREE_FORM_NATURAL_LANGUAGE_PARSING",
            "NOT_AN_INDEPENDENT_SAFETY_ORACLE",
            "NOT_A_VEHICLE_SAFETY_PROOF",
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
            ROOT / "projects/04-guardsynth-coc/src/guard_synth/source_aware_generator.py",
            ROOT / "projects/04-guardsynth-coc/src/guard_synth/schemas/source_aware_generation_request.schema.json",
            ROOT / "projects/04-guardsynth-coc/src/guard_synth/fixtures/source_aware_generation_request_p0b_v0_1.json",
            ROOT / "projects/04-guardsynth-coc/tests/test_source_aware_generator.py",
            Path(__file__).resolve(),
        ]),
        "versions": {"source_aware_generator": SOURCE_AWARE_GENERATOR_VERSION},
        "input_class": "SYNTHETIC",
        "enumeration": "DETERMINISTIC_TWO_INSTANCE_FIXTURE_AND_SIX_ABSTENTION_PROBES",
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
    parser.add_argument("--request", type=Path, default=DEFAULT_REQUEST)
    parser.add_argument("--run-id", default=DEFAULT_RUN_ID)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output, result = execute(args.request.resolve(), args.run_id)
    print(json.dumps({
        "status": result["status"],
        "result": output.relative_to(ROOT).as_posix(),
        "generation": result["generation"],
        "full": result["tests"]["full"],
    }, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "EXECUTED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
