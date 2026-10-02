"""Run indexed actor-zone expansion through bundle, Core, SMT, and Z3."""

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

from guard_synth_eblc.bundle_elaborator import BUNDLE_ELABORATOR_VERSION, elaborate_bundle
from guard_synth_eblc.composition import BUNDLE_VERSION, COMPOSITION_VERSION
from guard_synth_eblc.indexed_collection import (
    INDEXED_COLLECTION_COMPILER_VERSION,
    INDEXED_COLLECTION_VERSION,
    expand_indexed_collection,
    load_indexed_collection,
    parse_indexed_collection,
)
from guard_synth_eblc.smt_compiler import (
    COMPILER_VERSION,
    compile_core_model,
    export_compilation,
    solve_assignment,
)


EXPERIMENT_ID = "EBLC-INDEXED-COLLECTION-001"
CLAIM_SCOPE = "SYNTHETIC_INDEXED_ACTOR_ZONE_EXPANSION_AND_BOUNDED_TRANSLATION_NOT_VEHICLE_SAFETY"
DEFAULT_RUN_ID = "indexed-collection-2026-08-09-v1"
DEFAULT_FIXTURE = ROOT / "platforms/eblc-bcv/src/guard_synth_eblc/fixtures/eblc_indexed_collection_p0b_v0_1.json"
RUN_DATE = date.today().isoformat()
STABLE_BASELINE_TEST_MODULES = (
    "platforms/eblc-bcv/tests/unit/test_composition_compilation.py",
    "platforms/eblc-bcv/tests/unit/test_composition_v02_derivation.py",
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
        return "EXTERNAL_COLLECTION_PATH_REDACTED"


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


def _hashes(paths: list[Path]) -> dict[str, str]:
    return {
        _portable(path): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in paths
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
    definedness = [item for item in compiled.assertions if item.role == "DEFINEDNESS"]
    return {
        "status": solved["status"],
        "exact_outputs": {
            "c0__stop_position": witness.get(symbols[("c0__stop_position", None)]),
            "c1__stop_position": witness.get(symbols[("c1__stop_position", None)]),
            "c0__stopping_distance@0": witness.get(symbols[("c0__stopping_distance", 0)]),
            "c1__stopping_distance@0": witness.get(symbols[("c1__stopping_distance", 0)]),
        },
        "definedness_assertion_count": len(definedness),
    }


def _abstention_probe(raw: dict[str, Any]) -> dict[str, Any]:
    probe = deepcopy(raw)
    association = probe["instances"][1]["association"]
    association.update({
        "status": "AMBIGUOUS",
        "target_entity_id": None,
        "zone_id": None,
        "zone_geometry_ref": None,
        "coordinate_transform_ref": None,
        "candidate_target_entity_ids": ["synthetic-pedestrian:P18", "synthetic-pedestrian:P19"],
        "candidate_zone_ids": ["synthetic-zone:CZ5"],
        "reason_codes": ["MULTIPLE_TARGET_CANDIDATES"],
    })
    probe["instances"][1]["zone_entry"] = None
    result = expand_indexed_collection(parse_indexed_collection(probe))
    return {
        "verdict": result.verdict,
        "reason_codes": list(result.reason_codes),
        "unresolved_instance_ids": list(result.unresolved_instance_ids),
        "bundle_generated": result.bundle is not None,
    }


def _report(result: dict[str, Any]) -> str:
    tests = result["tests"]
    witness = result["exact_witness"]
    return f"""# EBLC indexed actor–zone collection 실행 보고서

- 상태: **{result['status']}**
- run ID: `{result['run_id']}`
- solver: project-local Z3 `{result['z3_runtime']['version']}`
- 주장 범위: `{CLAIM_SCOPE}`

## 결과

| 항목 | 결과 |
|---|---:|
| 기존 EBLC 기준선 | {tests['stable_baseline']['passed_count']}/{tests['stable_baseline']['test_count']} |
| indexed collection 신규 테스트 | {tests['indexed_collection']['passed_count']}/{tests['indexed_collection']['test_count']} |
| 전체 EBLC 테스트 | {tests['full_eblc']['passed_count']}/{tests['full_eblc']['test_count']} |
| P0a 회귀 | {tests['p0a']['passed_count']}/{tests['p0a']['test_count']} |
| SMT-LIB 직접 replay | {result['smt_replay']['matches']}/{result['smt_replay']['file_count']} |
| ambiguous association abstention | `{result['abstention_probe']['verdict']}`, bundle=false |

두 actor–zone binding을 하나의 v0.2 template에서 펼쳐 계약별 namespace로 분리했다.
Z3 exact stop-position witness는 `{witness['exact_outputs']['c0__stop_position']}`와
`{witness['exact_outputs']['c1__stop_position']}`, stopping-distance witness는 `9`와 `3`이다.
모호한 association은 일부 계약만 조용히 실행하지 않고 collection 전체를
`REVIEW_REQUIRED`로 중단한다.

이는 synthetic bounded expansion/translation evidence다. 실제 association 정확성,
법규 source, 차량 성능 또는 차량 안전성을 입증하지 않는다.
"""


def execute(collection_path: Path, run_id: str) -> tuple[Path, dict[str, Any]]:
    output = ROOT / "artifacts/results/public/eblc-indexed-collection-001" / run_id
    if output.exists():
        raise FileExistsError(f"refusing to overwrite existing run: {run_id}")
    collection = load_indexed_collection(collection_path)
    expansion = expand_indexed_collection(collection)
    output.mkdir(parents=True)
    _write_json(output / "INPUT_COLLECTION.json", collection.raw)
    expansion_record = {
        "collection_id": expansion.collection_id,
        "verdict": expansion.verdict,
        "reason_codes": list(expansion.reason_codes),
        "unresolved_instance_ids": list(expansion.unresolved_instance_ids),
        "bundle_generated": expansion.bundle is not None,
    }
    _write_json(output / "EXPANSION_RESULT.json", expansion_record)
    if expansion.bundle is None:
        result = {
            "experiment_id": EXPERIMENT_ID, "run_id": run_id, "run_date": RUN_DATE,
            "status": "EXECUTED_ABSTAINED", "claim_scope": CLAIM_SCOPE,
            "input_class": "SYNTHETIC", "expansion": expansion_record,
            "z3_runtime": Z3_RUNTIME.manifest(),
        }
        _write_json(output / "RESULT.json", result)
        (output / "REPORT_KO.md").write_text(
            "# EBLC indexed collection\n\n미해결 association 때문에 bundle을 생성하지 않았다.\n",
            encoding="utf-8",
        )
        return output, result

    elaborated = elaborate_bundle(expansion.bundle)
    compiled = compile_core_model(elaborated.core_model)
    _write_json(output / "EXPANDED_BUNDLE.json", expansion.bundle.raw)
    _write_json(output / "ELABORATED_CORE.json", elaborated.core_document)
    _write_json(output / "ELABORATION_MAP.json", elaborated.elaboration_map)
    query_results = export_compilation(compiled, output)
    smt_replay = _replay(output, query_results["results"][0]["status"])
    exact_witness = _exact_witness(compiled)
    abstention_probe = _abstention_probe(collection.raw)
    _write_json(output / "EXACT_WITNESS.json", exact_witness)
    _write_json(output / "ASSOCIATION_ABSTENTION.json", abstention_probe)
    _write_json(output / "SMT_REPLAY.json", smt_replay)

    tests = {
        "stable_baseline": _test(["python3", "-m", "unittest", *STABLE_BASELINE_TEST_MODULES, "-v"]),
        "indexed_collection": _test(["python3", "-m", "unittest", "platforms/eblc-bcv/tests/unit/test_indexed_collection.py", "-v"]),
        "full_eblc": _test(["python3", "-m", "unittest", "discover", "-s", "platforms/eblc-bcv/tests", "-p", "test_*.py", "-v"]),
        "p0a": _test(["python3", "-m", "unittest", "experiments.eblc_pilot.test_pilot", "-v"]),
    }
    gates = {
        "stable_baseline_119_of_119": tests["stable_baseline"]["passed"] and tests["stable_baseline"]["test_count"] == 119,
        "indexed_collection_9_of_9": tests["indexed_collection"]["passed"] and tests["indexed_collection"]["test_count"] == 9,
        "full_eblc_128_of_128": tests["full_eblc"]["passed"] and tests["full_eblc"]["test_count"] == 128,
        "p0a_7_of_7": tests["p0a"]["passed"] and tests["p0a"]["test_count"] == 7,
        "query_agreement": query_results["agreement"] == 1.0,
        "smt_replay": smt_replay["agreement"] == 1.0,
        "exact_multi_zone_witness": exact_witness["exact_outputs"] == {
            "c0__stop_position": "-3/2", "c1__stop_position": "21/2",
            "c0__stopping_distance@0": "9", "c1__stopping_distance@0": "3",
        },
        "ambiguous_association_abstains": (
            abstention_probe["verdict"] == "REVIEW_REQUIRED"
            and not abstention_probe["bundle_generated"]
        ),
    }
    result = {
        "experiment_id": EXPERIMENT_ID,
        "run_id": run_id,
        "run_date": RUN_DATE,
        "status": "EXECUTED" if all(gates.values()) else "FAILED",
        "claim_scope": CLAIM_SCOPE,
        "input_class": "SYNTHETIC",
        "input_collection": _portable(collection_path),
        "versions": {
            "indexed_collection": INDEXED_COLLECTION_VERSION,
            "indexed_collection_compiler": INDEXED_COLLECTION_COMPILER_VERSION,
            "bundle": BUNDLE_VERSION,
            "composition": COMPOSITION_VERSION,
            "bundle_elaborator": BUNDLE_ELABORATOR_VERSION,
            "core_smt_compiler": COMPILER_VERSION,
        },
        "z3_runtime": Z3_RUNTIME.manifest(),
        "expansion": expansion_record,
        "query_results": query_results,
        "smt_replay": smt_replay,
        "exact_witness": exact_witness,
        "abstention_probe": abstention_probe,
        "tests": tests,
        "gates": gates,
        "limitations": [
            "SYNTHETIC_ASSOCIATION_AND_GEOMETRY",
            "BOUNDED_DISCRETE_TIME",
            "NOT_AN_INDEPENDENT_SAFETY_ORACLE",
            "NOT_A_VEHICLE_SAFETY_PROOF",
        ],
    }
    hash_paths = [
        ROOT / "platforms/eblc-bcv/src/guard_synth_eblc/schemas/eblc_indexed_collection.schema.json",
        ROOT / "platforms/eblc-bcv/src/guard_synth_eblc/fixtures/eblc_indexed_collection_p0b_v0_1.json",
        ROOT / "platforms/eblc-bcv/src/guard_synth_eblc/indexed_collection.py",
        ROOT / "platforms/eblc-bcv/src/guard_synth_eblc/bundle_elaborator.py",
        ROOT / "platforms/eblc-bcv/src/guard_synth_eblc/smt_compiler.py",
        ROOT / "platforms/eblc-bcv/tests/test_indexed_collection.py",
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
        "enumeration": "DETERMINISTIC_TWO_ACTOR_TWO_ZONE_FIXTURE_AND_ABSTENTION_PROBE",
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
    parser.add_argument("--collection", type=Path, default=DEFAULT_FIXTURE)
    parser.add_argument("--run-id", default=DEFAULT_RUN_ID)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output, result = execute(args.collection.resolve(), args.run_id)
    print(json.dumps({
        "status": result["status"],
        "result": output.relative_to(ROOT).as_posix(),
        "full_eblc": result.get("tests", {}).get("full_eblc"),
    }, ensure_ascii=False, indent=2))
    return 0 if result["status"] in {"EXECUTED", "EXECUTED_ABSTAINED"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
