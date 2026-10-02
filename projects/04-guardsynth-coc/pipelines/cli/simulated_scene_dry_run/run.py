"""Run recorded scene evidence through a separate simulated vehicle binding."""

from __future__ import annotations

import argparse
from datetime import date
import hashlib
import json
from pathlib import Path
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

from guard_synth.simulated_scene_dry_run import (
    build_reference_translation_cases,
    build_simulated_generation_request,
    concrete_scene_t0_assignments,
    load_simulated_assurance_model,
    simulate_full_stop,
)
from guard_synth.source_aware_generator import generate_from_request
from guard_synth_eblc.bundle_elaborator import elaborate_bundle
from guard_synth_eblc.indexed_collection import expand_indexed_collection
from guard_synth_eblc.schema_validation import load_json
from guard_synth_eblc.smt_compiler import compile_core_model, export_compilation, solve_assignment


EXPERIMENT_ID = "GUARDSYNTH-SIMULATED-SCENE-DRY-RUN-001"
CLAIM_SCOPE = (
    "RECORDED_RESTRICTED_SCENE_EVIDENCE_PROJECTED_ON_SIMULATED_VEHICLE_"
    "NOT_REAL_VEHICLE_ASSURANCE_OR_SAFETY"
)
DEFAULT_AUDIT = ROOT / (
    "artifacts/results/restricted/guardsynth-calibration-scene-source-audit-001/"
    "alpamayo-calibration-source-2026-08-11-v17-rule-applicability/"
    "CALIBRATION_SOURCE_AUDIT.json"
)
DEFAULT_ASSOCIATION = ROOT / (
    "artifacts/results/restricted/guardsynth-geometric-association-001/"
    "alpamayo-episode-05-event-01-2026-08-11-v2/ASSOCIATION_EVIDENCE.json"
)
DEFAULT_RULE = ROOT / (
    "artifacts/results/restricted/guardsynth-rule-applicability-001/"
    "alpamayo-episode-05-2026-08-11-v1/RULE_APPLICABILITY_EVIDENCE.json"
)
DEFAULT_ADAPTER = ROOT / (
    "artifacts/results/restricted/eblc-p0b-001/"
    "p0b-data-adapter-2026-08-11-v2-all-candidates/ADAPTER_RESULT.json"
)
DEFAULT_MODEL = ROOT / "projects/04-guardsynth-coc/src/guard_synth/fixtures/simulated_assurance_profile_v0_1.json"
DEFAULT_BASE = ROOT / "projects/04-guardsynth-coc/src/guard_synth/fixtures/source_aware_generation_request_p0b_v0_1.json"


def _write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _replay_z3(output_dir: Path, expected_query_status: str) -> dict[str, Any]:
    executable = ROOT / Z3_RUNTIME.prefix / "bin/z3"
    expectations = {
        "MODEL.smt2": "SAT",
        "QUERY_composed_model_satisfiable.smt2": expected_query_status,
    }
    records = []
    for filename, expected in expectations.items():
        completed = subprocess.run(
            [str(executable), str(output_dir / filename)],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
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
    return {
        "records": records,
        "matches": sum(item["matches"] for item in records),
        "file_count": len(records),
        "agreement": sum(item["matches"] for item in records) / len(records),
    }


def _coc_claim_for_audit(audit: dict[str, Any], adapter: dict[str, Any]) -> dict[str, Any]:
    index_value = audit.get("adapter_candidate_index")
    if index_value is None:
        evidence_ref = audit["field_status"]["conflict_or_stop_geometry"]["evidence_ref"]
        marker = "#/candidates/"
        if marker not in evidence_ref:
            raise ValueError("audit does not identify its adapter candidate")
        index_value = evidence_ref.split(marker, 1)[1].split("/", 1)[0]
    try:
        candidate = adapter["candidates"][int(index_value)]
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        raise ValueError("audit adapter candidate is unavailable") from exc
    claim = candidate.get("coc_claim")
    if not isinstance(claim, dict):
        raise ValueError("adapter candidate has no CoC claim evidence")
    return claim


def execute(
    *,
    source_audit_path: Path,
    association_path: Path,
    rule_path: Path,
    adapter_path: Path,
    model_path: Path,
    base_request_path: Path,
    output_dir: Path,
) -> tuple[Path, dict[str, Any]]:
    inputs = (
        source_audit_path,
        association_path,
        rule_path,
        adapter_path,
        model_path,
        base_request_path,
    )
    if any(not path.is_file() for path in inputs):
        raise FileNotFoundError("simulated scene dry-run input is missing")
    if output_dir.exists():
        raise FileExistsError(f"refusing to overwrite existing output: {output_dir}")

    audit = load_json(source_audit_path)
    association = load_json(association_path)
    rule = load_json(rule_path)
    adapter = load_json(adapter_path)
    model = load_simulated_assurance_model(model_path)
    authored = build_simulated_generation_request(
        base_request=load_json(base_request_path),
        source_audit=audit,
        association_evidence=association,
        rule_evidence=rule,
        coc_claim_evidence=_coc_claim_for_audit(audit, adapter),
        model_source=model_path,
        request_id=(
            "alpamayo_"
            + "".join(
                character if character.isalnum() else "_"
                for character in str(audit["scene_ref"])
            )
            + "_simulation_projection"
        ),
    )
    generated = generate_from_request(authored.request)
    if generated.collection is None or generated.program_template is None:
        raise RuntimeError(f"generation failed: {generated.verdict}:{generated.reason_codes}")
    expansion = expand_indexed_collection(generated.collection)
    if expansion.bundle is None:
        raise RuntimeError(f"indexed expansion failed: {expansion.reason_codes}")
    elaborated = elaborate_bundle(expansion.bundle)
    compiled = compile_core_model(elaborated.core_model)

    speed = float(audit["field_status"]["ego_pose_and_speed"]["speed_mps"])
    assignments = concrete_scene_t0_assignments(
        audit,
        association,
        contract_count=len(generated.collection.instances),
    )
    solved = solve_assignment(compiled, assignments)
    symbol_names = {
        (item["declaration"], item["time"]): item["smt_symbol"]
        for item in compiled.symbol_table["symbols"]
    }
    concrete_t0_outputs = {
        f"C{index}": {
            "next_lifecycle": solved["witness"][symbol_names[(f"c{index}__state", 1)]],
            "verdict": solved["witness"][symbol_names[(f"c{index}__verdict", 0)]],
            "entry_violation": solved["witness"][
                symbol_names[(f"c{index}__entry_violation", 0)]
            ],
            "speed_violation": solved["witness"][
                symbol_names[(f"c{index}__speed_violation", 0)]
            ],
        }
        for index in range(len(generated.collection.instances))
    }
    reference_translation = build_reference_translation_cases(
        source_audit=audit,
        association_evidence=association,
        model_source=model_path,
        collection=generated.collection.raw,
    )
    canonical_core_records = []
    for record in reference_translation["records"]:
        concrete = concrete_t0_outputs[record["contract_id"]]
        canonical = record["canonical"]
        expected_violations = []
        if concrete["entry_violation"]:
            expected_violations.append("CONFLICT_ZONE_ENTRY_WHILE_OBLIGATION_ACTIVE")
        if concrete["speed_violation"]:
            expected_violations.append("DYNAMIC_STOPPING_SPEED_BOUND_EXCEEDED")
        canonical_core_records.append({
            "contract_id": record["contract_id"],
            "matches": (
                canonical["lifecycle"][-1] == concrete["next_lifecycle"]
                and canonical["verdict"] == concrete["verdict"]
                and canonical["violations"] == expected_violations
            ),
        })
    canonical_core_agreement = sum(
        item["matches"] for item in canonical_core_records
    ) / len(canonical_core_records)
    reference_translation["canonical_core_frame0_records"] = canonical_core_records
    reference_translation["canonical_core_frame0_agreement"] = canonical_core_agreement
    simulation_trace = simulate_full_stop(model, initial_speed_mps=speed)
    analytic_distance = (
        speed * model.response_time_s
        + speed**2 / (2.0 * model.maximum_service_deceleration_mps2)
    )

    output_dir.mkdir(parents=True)
    _write_json(output_dir / "INPUT_REQUEST.json", authored.request.raw)
    _write_json(output_dir / "GENERATED_PROGRAM_TEMPLATE.json", generated.program_template.raw)
    _write_json(output_dir / "GENERATED_INDEXED_COLLECTION.json", generated.collection.raw)
    _write_json(output_dir / "GENERATED_BUNDLE.json", expansion.bundle.raw)
    _write_json(output_dir / "ELABORATED_CORE.json", elaborated.core_document)
    _write_json(output_dir / "ELABORATION_MAP.json", elaborated.elaboration_map)
    query_results = export_compilation(compiled, output_dir)
    z3_replay = _replay_z3(output_dir, query_results["results"][0]["status"])
    _write_json(output_dir / "CONCRETE_T0_SMT_WITNESS.json", solved)
    _write_json(output_dir / "CONCRETE_T0_RESULTS.json", concrete_t0_outputs)
    _write_json(
        output_dir / "CANONICAL_RUNTIME_BOUNDED_TRANSLATION.json",
        reference_translation,
    )
    _write_json(output_dir / "Z3_REPLAY.json", z3_replay)
    _write_json(output_dir / "SIMULATED_STOP_TRACE.json", {
        "initial_speed_mps": speed,
        "analytic_stopping_distance_m": analytic_distance,
        "simulated_stopping_distance_m": simulation_trace[-1]["position_m"],
        "sample_count": len(simulation_trace),
        "trace": simulation_trace,
    })
    closure = {
        "scene_ref": audit["scene_ref"],
        "recorded_scene_source_fields": len(audit["available_fields"]),
        "recorded_scene_required_fields": 9,
        "recorded_vehicle_source_complete": False,
        "remaining_recorded_vehicle_gaps": list(authored.remaining_real_vehicle_gaps),
        "simulation_projection_source_complete": True,
        "recorded_vehicle_binding_key": authored.recorded_vehicle_binding_key,
        "simulation_vehicle_binding_key": authored.simulation_vehicle_binding_key,
        "bindings_are_distinct": (
            authored.recorded_vehicle_binding_key
            != authored.simulation_vehicle_binding_key
        ),
        "simulation_profile_source_class": authored.profile_source_class,
        "simulation_profile_evidence_ref": authored.simulation_evidence_ref,
        "coc_claim_count": len(authored.request.raw["context_graph"]["coc_claims"]),
        "coc_claim_evidence_ref": authored.coc_claim_evidence_ref,
        "coc_claim_used_as_activation_evidence": False,
        "conditional_rule_source_refs": list(authored.conditional_rule_source_refs),
        "hazard_semantics": "DERIVED_GEOMETRIC_PEDESTRIAN_TRACK_EGO_CORRIDOR_OVERLAP",
        "collision_prediction_claimed": False,
        "claim_scope": CLAIM_SCOPE,
    }
    _write_json(output_dir / "SIMULATION_PROJECTION_CLOSURE.json", closure)

    numeric_profile_refs = {
        evidence_ref
        for symbol in generated.program_template.raw["typed_derivation"]["symbols"]
        if symbol["symbol_id"] in {"response_time", "deceleration"}
        for evidence_ref in symbol["evidence_refs"]
    }
    gates = {
        "recorded_scene_evidence_8_of_9": len(audit["available_fields"]) == 8,
        "recorded_vehicle_gap_preserved": (
            authored.remaining_real_vehicle_gaps
            == ("source_bearing_vehicle_assurance_profile",)
        ),
        "distinct_vehicle_bindings": closure["bindings_are_distinct"],
        "simulation_projection_source_complete": authored.simulation_projection_source_complete,
        "guardsynth_generation_validated": generated.verdict == "VALIDATED",
        "indexed_expansion_validated": expansion.verdict == "VALIDATED",
        "core_z3_compilation_agreement": query_results["agreement"] == 1.0,
        "direct_z3_smtlib_replay": z3_replay["agreement"] == 1.0,
        "concrete_t0_assignment_sat": solved["status"] == "SAT",
        "concrete_t0_contracts_active_and_validated": all(
            item == {
                "next_lifecycle": "ACTIVE",
                "verdict": "VALIDATED",
                "entry_violation": False,
                "speed_violation": False,
            }
            for item in concrete_t0_outputs.values()
        ),
        "canonical_runtime_recorded_frame_agreement": (
            reference_translation["canonical_runtime_agreement"] == 1.0
        ),
        "canonical_bounded_recorded_frame_agreement": (
            reference_translation["canonical_bounded_target_agreement"] == 1.0
        ),
        "canonical_core_recorded_frame_agreement": canonical_core_agreement == 1.0,
        "simulator_analytic_agreement": abs(
            simulation_trace[-1]["position_m"] - analytic_distance
        ) <= 1e-9,
        "coc_claim_not_activation_evidence": (
            all(
                claim["evidence_ref"]
                not in generated.program_template.raw["predicate"]["evidence_refs"]
                for claim in authored.request.raw["context_graph"]["coc_claims"]
            )
        ),
        "conditional_rules_not_numeric_profile_sources": all(
            source_ref not in numeric_profile_refs
            for source_ref in authored.conditional_rule_source_refs
        ),
    }
    result = {
        "experiment_id": EXPERIMENT_ID,
        "run_id": output_dir.name,
        "run_date": date.today().isoformat(),
        "status": "EXECUTED" if all(gates.values()) else "FAILED",
        "decision": "SIMULATION_PATH_EXECUTED_REAL_VEHICLE_PATH_STILL_BLOCKED",
        "input_class": "LICENSE_RESTRICTED_SCENE_PLUS_SIMULATED_ASSURANCE",
        "scene_ref": audit["scene_ref"],
        "contract_count": len(generated.collection.instances),
        "guardsynth_eblc_core_z3_scene_runs": 1,
        "z3_query_agreement": query_results["agreement"],
        "direct_z3_smtlib_replay_agreement": z3_replay["agreement"],
        "concrete_t0_assignment_status": solved["status"],
        "canonical_runtime_recorded_frame_agreement": reference_translation[
            "canonical_runtime_agreement"
        ],
        "canonical_bounded_recorded_frame_agreement": reference_translation[
            "canonical_bounded_target_agreement"
        ],
        "canonical_core_recorded_frame_agreement": canonical_core_agreement,
        "concrete_t0_results": concrete_t0_outputs,
        "recorded_vehicle_source_complete": False,
        "simulation_projection_source_complete": True,
        "vehicle_safety_validated": False,
        "gates": gates,
        "limitations": [
            *model.limitations,
            "GEOMETRIC_CORRIDOR_OVERLAP_IS_NOT_COLLISION_PREDICTION",
            "CONDITIONAL_RULE_APPLICABILITY_IS_NOT_NUMERIC_VEHICLE_ASSURANCE",
            "BOUNDED_SMT_SATISFIABILITY_IS_NOT_VEHICLE_SAFETY_PROOF",
        ],
        "claim_scope": CLAIM_SCOPE,
    }
    _write_json(output_dir / "RESULT.json", result)
    _write_json(output_dir / "RUN_MANIFEST.json", {
        "experiment_id": EXPERIMENT_ID,
        "run_id": output_dir.name,
        "run_date": date.today().isoformat(),
        "python_version": sys.version.split()[0],
        "z3_runtime": Z3_RUNTIME.manifest(),
        "input_class": result["input_class"],
        "deterministic": True,
        "random_seed": None,
        "input_hashes": {
            "source_audit": _sha256(source_audit_path),
            "association_evidence": _sha256(association_path),
            "rule_applicability_evidence": _sha256(rule_path),
            "adapter_result": _sha256(adapter_path),
            "simulated_assurance_model": _sha256(model_path),
            "base_generation_request": _sha256(base_request_path),
        },
        "code_hashes": {
            "simulation_module": _sha256(ROOT / "projects/04-guardsynth-coc/src/guard_synth/simulated_scene_dry_run.py"),
            "pipeline": _sha256(Path(__file__).resolve()),
        },
        "restricted_raw_paths_in_outputs": False,
        "real_vehicle_assurance_substitution_performed": False,
        "claim_scope": CLAIM_SCOPE,
    })
    (output_dir / "REPORT_KO.md").write_text(
        f"""# GuardSynth 실제 장면 × 가상 차량 dry run

- 상태: **{result['status']}**
- 실제 장면 근거: **8/9**
- 실제 차량 source-complete: **아니오**
- 시뮬레이션 투영 source-complete: **예**
- 생성 계약: **{result['contract_count']}개** (보행자 track SET의 각 원소)
- GuardSynth→EBLC→Core→Z3 실행: **1장면**
- Z3 query agreement: **{result['z3_query_agreement']:.1%}**
- 실제 frame-0 입력 대입 결과: **{result['concrete_t0_assignment_status']}**
- Canonical/runtime 실제 frame-0 agreement: **{result['canonical_runtime_recorded_frame_agreement']:.1%}**
- Canonical/bounded Z3 실제 frame-0 agreement: **{result['canonical_bounded_recorded_frame_agreement']:.1%}**
- Canonical/Core 실제 frame-0 agreement: **{result['canonical_core_recorded_frame_agreement']:.1%}**
- Z3 SMT-LIB 직접 replay: **{result['direct_z3_smtlib_replay_agreement']:.1%}**

실제 장면에서 얻은 timestamp, ego state, 보행자 track SET, association, 동적 corridor
geometry, 좌표 변환, 조건부 규칙 또는 system requirement 근거와 recorded-rig binding을 사용했다. 제동 수치는
`{model.profile_id}` 가상 차량 모델에서만 가져왔다. 두 vehicle binding은 서로 다르며,
실제 차량의 assurance 누락은 그대로 남아 있다.

활성 조건은 충돌 예측이 아니라 source-linked 보행자 oriented box가 ego corridor와 겹친다는
기하 조건이다. Alpamayo CoC는 원문 대신 SHA-256과 `CLAIMED`로 보존하고 activation fact로
사용하지 않았다. 조건부 applicability source도 가상 제동 수치의 출처로 사용하지 않았다. 따라서
이 실행은 파이프라인의 시뮬레이션 가능성을 보이지만 실제
차량 제동 성능, 법적 판단 또는 안전성을 입증하지 않는다.
""",
        encoding="utf-8",
    )
    return output_dir, result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-audit", type=Path, default=DEFAULT_AUDIT)
    parser.add_argument("--association", type=Path, default=DEFAULT_ASSOCIATION)
    parser.add_argument("--rule-evidence", type=Path, default=DEFAULT_RULE)
    parser.add_argument("--adapter-result", type=Path, default=DEFAULT_ADAPTER)
    parser.add_argument("--model", type=Path, default=DEFAULT_MODEL)
    parser.add_argument("--base-request", type=Path, default=DEFAULT_BASE)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    _, result = execute(
        source_audit_path=args.source_audit,
        association_path=args.association,
        rule_path=args.rule_evidence,
        adapter_path=args.adapter_result,
        model_path=args.model,
        base_request_path=args.base_request,
        output_dir=args.output_dir,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result["status"] == "EXECUTED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
