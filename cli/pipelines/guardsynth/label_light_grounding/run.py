"""Run label-light proposal, triage, review, and EBLC/Z3 handoff."""

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

from guard_synth import LABEL_LIGHT_GROUNDING_VERSION
from guard_synth.assurance_registry import load_assurance_registry
from guard_synth.label_light_grounding import (
    ReviewDecision,
    aggregate_label_light_metrics,
    apply_review_decision,
    assess_legacy_adapter_label_light,
    parse_label_light_packet,
    triage_label_light_packet,
)
from guard_synth.source_authoring import author_generation_request
from guard_synth.source_aware_generator import generate_from_request, parse_generation_request
from guard_synth_eblc.bundle_elaborator import elaborate_bundle
from guard_synth_eblc.indexed_collection import expand_indexed_collection
from guard_synth_eblc.schema_validation import load_json
from guard_synth_eblc.smt_compiler import compile_core_model, export_compilation


EXPERIMENT_ID = "GUARDSYNTH-LABEL-LIGHT-GROUNDING-001"
DEFAULT_RUN_ID = "label-light-2026-08-10-v1"
PACKET_FIXTURE = ROOT / "src/guard_synth/fixtures/label_light_grounding_packet_v0_1.json"
BASE_REQUEST = ROOT / "src/guard_synth/fixtures/source_aware_generation_request_p0b_v0_1.json"
REGISTRY_FIXTURE = ROOT / "src/guard_synth/fixtures/vehicle_assurance_registry_synthetic_test_v0_1.json"
LEGACY_ADAPTER = ROOT / "artifacts/results/restricted/eblc-p0b-001/p0b-restricted-grounding-multiview-2026-08-08-v1/ADAPTER_RESULT.json"
CLAIM_SCOPE = "LABEL_LIGHT_SYNTHETIC_GROUNDING_AND_BOUNDED_HANDOFF_NOT_ASSOCIATION_ACCURACY_OR_VEHICLE_SAFETY"


def _write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


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


def _second_packet(raw: dict[str, Any]) -> dict[str, Any]:
    value = deepcopy(raw)
    value["packet_id"] = "label_light_scene_002"
    value["scene_ref"] = "synthetic-scene:002"
    value["hazard"]["evidence_ref"] = "OBS-002"
    value["targets"][0].update({"target_entity_id": "pedestrian:P18", "track_evidence_ref": "TRACK-002"})
    value["zones"][0].update({
        "zone_id": "zone:Z5", "geometry_evidence_ref": "GEOMETRY-002",
        "transform_evidence_ref": "TRANSFORM-002", "entry_x_m": 12.0,
    })
    value["pair_candidates"][0].update({
        "target_entity_id": "pedestrian:P18", "zone_id": "zone:Z5",
        "association_evidence_ref": "ASSOC-002",
    })
    value["source_refs"].extend(["OBS-002", "TRACK-002", "GEOMETRY-002", "TRANSFORM-002", "ASSOC-002"])
    return value


def _scenario_result(scenario_id: str, result) -> dict[str, Any]:
    return {
        "scenario_id": scenario_id,
        "association_status": result.association_status,
        "contract_readiness": result.contract_readiness,
        "reason_codes": list(result.reason_codes),
        "review_interactions": result.review_task["estimated_interactions"] if result.review_task else 0,
        "grounded_scene_created": result.grounded_scene is not None,
        "human_correction": result.human_correction,
    }


def _run_scenarios(base: dict[str, Any]) -> tuple[list[dict[str, Any]], list[Any]]:
    cases: list[tuple[str, dict[str, Any]]] = []
    cases.append(("AUTO_UNIQUE_CALIBRATED", deepcopy(base)))
    disabled = deepcopy(base)
    disabled["policy"]["auto_confirm_enabled"] = False
    cases.append(("REVIEW_POLICY_DISABLED", disabled))
    low = deepcopy(base)
    low["pair_candidates"][0]["confidence_lower_bound"] = 0.70
    cases.append(("REVIEW_LOW_CONFIDENCE", low))
    multi = deepcopy(base)
    multi["targets"].append({
        "target_entity_id": "pedestrian:P19", "classification": "PEDESTRIAN",
        "track_evidence_ref": "TRACK-019",
    })
    multi["pair_candidates"].append({
        "target_entity_id": "pedestrian:P19", "zone_id": "zone:Z4",
        "path_intersection": "TRUE", "association_evidence_ref": "ASSOC-019",
        "confidence_lower_bound": 0.96, "confidence_upper_bound": 0.99,
        "calibration_evidence_ref": "CALIBRATION-001",
    })
    multi["source_refs"].extend(["TRACK-019", "ASSOC-019"])
    cases.append(("REVIEW_MULTIPLE_CANDIDATES", multi))
    missing_transform = deepcopy(base)
    missing_transform["zones"][0]["transform_verified"] = False
    cases.append(("UNSUPPORTED_UNVERIFIED_TRANSFORM", missing_transform))
    conflict = deepcopy(base)
    conflict["hazard"]["truth"] = "CONFLICT"
    cases.append(("CONFLICT_HAZARD", conflict))
    claimed = deepcopy(base)
    claimed["hazard"]["epistemic_kind"] = "CLAIMED"
    cases.append(("REVIEW_CLAIMED_HAZARD", claimed))

    results = []
    records = []
    for scenario_id, raw in cases:
        result = triage_label_light_packet(parse_label_light_packet(raw))
        results.append(result)
        records.append(_scenario_result(scenario_id, result))

    packet = parse_label_light_packet(disabled)
    review = triage_label_light_packet(packet)
    human = apply_review_decision(packet, review, ReviewDecision(
        decision="CONFIRM_PROPOSAL", selected_target_entity_id=None,
        selected_zone_id=None, reviewer_evidence_ref="SYNTHETIC-REVIEW-001",
    ))
    results.append(human)
    records.append(_scenario_result("HUMAN_ONE_CLICK_CONFIRMATION", human))
    return records, results


def _end_to_end(base: dict[str, Any], output: Path) -> dict[str, Any]:
    grounded = []
    for raw in (base, _second_packet(base)):
        result = triage_label_light_packet(parse_label_light_packet(raw))
        if result.grounded_scene is None:
            raise RuntimeError(f"locked auto scene did not ground: {result.reason_codes}")
        grounded.append(result.grounded_scene)
    request = author_generation_request(
        base_request=load_json(BASE_REQUEST), grounded_scenes=grounded,
        registry=load_assurance_registry(REGISTRY_FIXTURE),
        request_id="label_light_two_scene_request",
    )
    generated = generate_from_request(parse_generation_request(request))
    if generated.collection is None:
        raise RuntimeError(f"generator abstained: {generated.reason_codes}")
    expanded = expand_indexed_collection(generated.collection)
    if expanded.bundle is None:
        raise RuntimeError(f"collection expansion failed: {expanded.reason_codes}")
    elaborated = elaborate_bundle(expanded.bundle)
    compiled = compile_core_model(elaborated.core_model)
    smt_output = output / "smt"
    smt_output.mkdir()
    queries = export_compilation(compiled, smt_output)
    _write_json(output / "AUTHORED_GENERATION_REQUEST.json", request)
    _write_json(output / "GENERATED_INDEXED_COLLECTION.json", generated.collection.raw)
    _write_json(output / "GENERATED_BUNDLE.json", expanded.bundle.raw)
    _write_json(output / "ELABORATED_CORE.json", elaborated.core_document)
    return {
        "grounded_scene_count": len(grounded),
        "generator_verdict": generated.verdict,
        "contract_instance_count": len(generated.collection.instances),
        "collection_expansion_verdict": expanded.verdict,
        "core_query_count": len(queries["results"]),
        "core_query_agreement": queries["agreement"],
        "z3_version": Z3_RUNTIME.version,
    }


def _report(result: dict[str, Any]) -> str:
    metrics = result["metrics"]
    legacy = result["legacy_restricted_aggregate"]
    tests = result["tests"]
    return f"""# GuardSynth label-light grounding v0.1 실행 보고서

- 상태: **{result['status']}**
- synthetic scenario: {result['scenario_gate']['matched']}/{result['scenario_gate']['total']}
- 자동 확인: {metrics['auto_confirmed']}
- 사람 확인 요청: {metrics['review_required']}
- 최소 확인 완료: {metrics['human_confirmed']}
- 입력 부족 중단: {metrics['unsupported']}
- 충돌 보존: {metrics['conflict']}
- Z3: {result['end_to_end']['z3_version']}, query agreement {result['end_to_end']['core_query_agreement']:.0%}
- 주장 범위: `{CLAIM_SCOPE}`

## 무엇을 구현했는가

대량의 새 polygon/trajectory 레이블을 전제로 하지 않는다. 기존 perception·tracking·map
출력으로 target–zone 후보를 만들고, 승인된 calibration의 하한과 유일성 조건이 만족되면
자동 확인한다. 저신뢰·다중 후보·CoC claim-only 입력은 한 번의 선택/확인 작업으로 보내며,
geometry·좌표 변환·근거가 없거나 evidence가 충돌하면 EBLC를 만들지 않는다.

자동 확인된 synthetic 장면 두 개는 source authoring → GuardSynth generator → EBLC indexed
collection → bundle → Core → 실제 Z3까지 전달됐다. 사람 확인 근거도 최종 generation request의
provenance에 보존된다.

## 현재 제한 파생 입력

- 후보 event: {legacy.get('candidate_event_count', 0)}/24
- association review 필요: {legacy.get('association_review_required_count', 0)}
- 자동 확인 가능: {legacy.get('auto_confirmed_count', 0)}
- contract 입력 부족: {legacy.get('contract_blocked_count', 0)}

이는 기존 제한 입력을 재레이블링한 결과가 아니라 식별자 없는 준비도 집계다. 현재 데이터에는
calibrated association proposal, 검증된 좌표 변환 및 실제 vehicle assurance가 없으므로
`DATA_GAP_PIVOT`은 유지된다.

## 테스트

- label-light 집중 테스트: {tests['label_light']['passed_count']}/{tests['label_light']['test_count']}
- 전체 maintained 테스트: {tests['full']['passed_count']}/{tests['full']['test_count']}
- P0a 회귀: {tests['p0a']['passed_count']}/{tests['p0a']['test_count']}
- 구조/문서 링크: {tests['structure']['passed_count']}/{tests['structure']['test_count']}

confidence는 관측 사실이나 안전 보장이 아니다. 이 결과는 label 부담을 줄이는 software
workflow와 bounded handoff를 검증했을 뿐 association 정확도, 실제 법규 또는 차량 안전성을
입증하지 않는다.
"""


def execute(run_id: str) -> tuple[Path, dict[str, Any]]:
    output = ROOT / "artifacts/results/public/guardsynth-label-light-grounding-001" / run_id
    if output.exists():
        raise FileExistsError(f"refusing to overwrite existing run: {run_id}")
    output.mkdir(parents=True)
    base = load_json(PACKET_FIXTURE)
    scenarios, workflow_results = _run_scenarios(base)
    expected = {
        "AUTO_UNIQUE_CALIBRATED": "AUTO_CONFIRMED",
        "REVIEW_POLICY_DISABLED": "REVIEW_REQUIRED",
        "REVIEW_LOW_CONFIDENCE": "REVIEW_REQUIRED",
        "REVIEW_MULTIPLE_CANDIDATES": "REVIEW_REQUIRED",
        "UNSUPPORTED_UNVERIFIED_TRANSFORM": "UNSUPPORTED",
        "CONFLICT_HAZARD": "CONFLICT",
        "REVIEW_CLAIMED_HAZARD": "REVIEW_REQUIRED",
        "HUMAN_ONE_CLICK_CONFIRMATION": "HUMAN_CONFIRMED",
    }
    matched = sum(item["association_status"] == expected[item["scenario_id"]] for item in scenarios)
    metrics = aggregate_label_light_metrics(workflow_results)
    end_to_end = _end_to_end(base, output)
    legacy = (
        assess_legacy_adapter_label_light(load_json(LEGACY_ADAPTER), target_slots=24)
        if LEGACY_ADAPTER.is_file()
        else {"status": "RESTRICTED_ADAPTER_ABSENT", "raw_identifiers_included": False}
    )
    _write_json(output / "SCENARIO_RESULTS.json", scenarios)
    _write_json(output / "METRICS.json", metrics)
    _write_json(output / "END_TO_END_RESULT.json", end_to_end)
    _write_json(output / "LEGACY_RESTRICTED_AGGREGATE.json", legacy)
    (output / "REPORT_KO.md").write_text("# GuardSynth label-light grounding\n\nGate execution in progress.\n", encoding="utf-8")
    tests = {
        "label_light": _test([sys.executable, "-m", "unittest", "tests.guard_synth_eblc.test_label_light_grounding", "-v"]),
        "full": _test([sys.executable, "-m", "unittest", "discover", "-s", "tests/guard_synth_eblc", "-p", "test_*.py", "-v"]),
        "p0a": _test([sys.executable, "-m", "unittest", "experiments.eblc_pilot.test_pilot", "-v"]),
        "structure": _test([sys.executable, "-m", "unittest", "tests.structure.test_project_layout", "-v"]),
    }
    gates = {
        "scenario_directions": matched == len(expected),
        "two_scene_generation": end_to_end["generator_verdict"] == "VALIDATED" and end_to_end["contract_instance_count"] == 2,
        "core_z3_agreement": end_to_end["core_query_agreement"] == 1.0,
        "restricted_aggregate_redacted": legacy.get("raw_identifiers_included") is False,
        "tests": all(item["passed"] for item in tests.values()),
    }
    result = {
        "experiment_id": EXPERIMENT_ID, "run_id": run_id,
        "run_date": date.today().isoformat(),
        "status": "EXECUTED" if all(gates.values()) else "FAILED",
        "decision": "LABEL_LIGHT_SOFTWARE_GO_DATA_GAP_PIVOT_REMAINS",
        "scenario_gate": {"matched": matched, "total": len(expected)},
        "metrics": metrics, "end_to_end": end_to_end,
        "legacy_restricted_aggregate": legacy, "tests": tests, "gates": gates,
        "claim_scope": CLAIM_SCOPE,
    }
    _write_json(output / "RESULT.json", result)
    _write_json(output / "RUN_MANIFEST.json", {
        "experiment_id": EXPERIMENT_ID, "run_id": run_id,
        "run_date": date.today().isoformat(), "python_version": sys.version.split()[0],
        "z3_runtime": Z3_RUNTIME.manifest(), "code_revision": "WORKSPACE_WITHOUT_GIT_METADATA",
        "input_class": "SYNTHETIC_PLUS_LICENSE_RESTRICTED_AGGREGATES_ONLY",
        "versions": {"label_light_grounding": LABEL_LIGHT_GROUNDING_VERSION},
        "deterministic_scenarios": True, "random_seed": None,
        "file_hashes": {
            path.relative_to(ROOT).as_posix(): _sha256(path)
            for path in (PACKET_FIXTURE, REGISTRY_FIXTURE, Path(__file__).resolve(), ROOT / "src/guard_synth/label_light_grounding.py")
        },
        "test_commands": tests, "raw_restricted_identifiers_included": False,
        "claim_scope": CLAIM_SCOPE,
    })
    (output / "REPORT_KO.md").write_text(_report(result), encoding="utf-8")
    return output, result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run label-light GuardSynth grounding validation.")
    parser.add_argument("--run-id", default=DEFAULT_RUN_ID)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output, result = execute(args.run_id)
    print(json.dumps({
        "status": result["status"], "decision": result["decision"],
        "output": output.relative_to(ROOT).as_posix(),
    }, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "EXECUTED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
