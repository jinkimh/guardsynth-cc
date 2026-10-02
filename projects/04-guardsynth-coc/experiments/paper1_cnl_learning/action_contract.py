"""Execute the pinned #18 conditional action contract through shared EBLC Core."""

from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from align_reviews import ROOT, BASE, digest, write_json
from worked_example import source_example

sys.path.insert(0, str(ROOT / "platforms/eblc-bcv/src"))
from guard_synth.qualitative_scene_contract import prepare_scene18_contract
from guard_synth_eblc.action_contract import lower_action_contract, var, literal, binary, conjunction, neg
from guard_synth_eblc.core_ir import parse_core_model
from guard_synth_eblc.smt_compiler import compile_core_model, check_queries
from guard_synth_eblc.cnl_renderer import render_action_contract, export_cnl

EXPERIMENT = "guardsynth-paper1-action-contract-001"
POLICY = ROOT / "projects/04-guardsynth-coc/docs/designs/PAPER1_ACTION_CONTRACT_DESIGN_V01.md"


def eq(name, value, offset=0, enum=None):
    return binary("eq", var(name, offset), literal(value, enum))


def evidence(oid, truth, valid=True, offset=0):
    return conjunction(eq(oid + "_truth", truth, offset, "Truth"), eq(oid + "_evidence_valid", valid, offset))


def cases():
    enter = eq("action", "ENTER_ZONE", enum="Action")
    defer = eq("action", "DEFER_ENTRY", enum="Action")
    clear = conjunction(evidence("ped", "FALSE"), evidence("road", "FALSE"))
    return [
        ("conflict_entry", evidence("ped", "TRUE"), enter, "UNSAT"),
        ("unknown_retains", conjunction(eq("ped_prior_active", True), evidence("ped", "UNKNOWN")), neg(var("ped_active")), "UNSAT"),
        ("invalid_clear_retains", conjunction(eq("ped_prior_active", True), evidence("ped", "FALSE", False)), neg(var("ped_active")), "UNSAT"),
        ("clear_and_wait", clear, conjunction(neg(var("ped_active")), defer), "SAT"),
        ("other_obligation", conjunction(evidence("ped", "FALSE"), evidence("road", "TRUE")), enter, "UNSAT"),
        ("reactivation", conjunction(evidence("ped", "TRUE"), evidence("ped", "FALSE", offset=1), evidence("ped", "TRUE", offset=2)), neg(var("ped_active", 2)), "UNSAT"),
        ("nominal_entry", clear, enter, "SAT"),
        ("unknown_person_gap", conjunction(eq("ped_prior_active", False), evidence("ped", "UNKNOWN"), evidence("road", "FALSE")), enter, "UNSAT"),
        ("unknown_road_gap", conjunction(evidence("ped", "FALSE"), evidence("road", "UNKNOWN")), enter, "UNSAT"),
        ("conflicting_evidence", conjunction(evidence("ped", "CONFLICT"), evidence("road", "FALSE")), enter, "UNSAT"),
        ("invalid_clear_entry", conjunction(evidence("ped", "FALSE", False), evidence("road", "FALSE")), enter, "UNSAT"),
        ("source_pending_defer", conjunction(evidence("ped", "UNKNOWN", False), evidence("road", "UNKNOWN", False)), conjunction(defer, var("review_required")), "SAT"),
    ]


def add_query(core, qid, formula, expected):
    core["queries"].append({"id": qid, "formula": formula, "expected": expected,
        "classification": "EXAMPLE", "source_refs": core["source_refs"],
        "description": "Conditional policy regression, not observed scene truth: " + qid})


def export_checks(core, output, prefix):
    compiled = compile_core_model(parse_core_model(core))
    checked = check_queries(compiled)
    if checked["matches_expected"] != checked["query_count"]:
        raise ValueError("Core solver regression failed")
    for record in checked["results"]:
        name = prefix + "_" + record["query_id"] + ".smt2"
        (output / name).write_text(record.pop("smt2"), encoding="utf-8")
        record["smt2_file"] = name
    write_json(output / (prefix + "_checks.json"), checked)
    return checked


def execute(output):
    scene, inputs = source_example()
    inputs[str(POLICY.relative_to(ROOT))] = digest(POLICY)
    policy_ref = "sha256:" + digest(POLICY) + "#GS-PAPER1-ENTRY-POLICY-v0.1"
    refs = [policy_ref] + [f"sha256:{sha}#{path}" for path, sha in sorted(inputs.items()) if path != str(POLICY.relative_to(ROOT))]
    contract, gate = prepare_scene18_contract(scene, policy_ref=policy_ref, source_refs=refs)
    core = lower_action_contract(contract)
    for qid, premises, probe, expected in cases():
        add_query(core, qid + "_premises", premises, "SAT")
        add_query(core, qid, conjunction(premises, probe), expected)
    checks = export_checks(core, output, "query")
    mutation = deepcopy(core)
    mutation["clauses"] = [c for c in mutation["clauses"] if c["id"] != "action_gate"]
    mutation["queries"] = []
    _, premises, probe, _ = next(c for c in cases() if c[0] == "unknown_person_gap")
    add_query(mutation, "no_gate_premises", premises, "SAT")
    add_query(mutation, "no_gate_entry", conjunction(premises, probe), "SAT")
    mutation_checks = export_checks(mutation, output, "mutation")
    document = render_action_contract(contract)
    export_cnl(document, output, text_name="constraints.txt", mapping_name="cnl_mapping.json")
    for name, data in (("source_example.json", scene), ("source_gate.json", gate),
                       ("action_contract.json", contract.raw), ("core_model.json", core),
                       ("mutation_core_model.json", mutation)):
        write_json(output / name, data)
    result = {"project_id": "guardsynth-coc", "experiment_id": EXPERIMENT,
        "status": "ACTION_CONTRACT_EXECUTABLE_SOURCE_PENDING", "input_hashes": inputs,
        "engine": checks["engine"], "z3_version": checks["z3_version"],
        "compiler_version": checks["compiler_version"], "renderer_version": document.renderer_version,
        "query_count": checks["query_count"], "matches_expected": checks["matches_expected"],
        "premise_checks_sat": 12, "regression_probes": 12,
        "probe_sat": 3, "probe_unsat": 9, "mutation_queries": mutation_checks["query_count"],
        "previous_unknown_gaps_closed": 2, "conditional_contracts": 1, "conditional_cnl_documents": 1,
        "source_verified_contracts": 0, "training_exports": 0, "action_gold": None,
        "source_gate": gate, "claim_scope": contract.raw["claim_scope"]}
    write_json(output / "RESULT.json", result)
    (output / "REPORT_KO.md").write_text(
        "# #18 실행 가능한 행동 계약\n\n"
        "원본 CoC·CASCADE·영상·geometry hash를 재확인했다. 버전된 행동 계약을 parser → 기존 Core → SMT로 자동 변환하고 공통 renderer로 CNL을 생성했다.\n\n"
        "기본 일관성 SAT, 전제 12/12 SAT, 검사 12/12 예상 일치(SAT 3, UNSAT 9). UNKNOWN 진입 반례 2개는 명시한 CLEAR_REQUIRED_FOR_ENTRY 정책에서 UNSAT가 됐다. action_gate 제거 mutation에서는 동일 반례가 SAT로 재현된다.\n\n"
        "이는 3개 추상 결정 시점의 조건부 명세 검사이며 영상 해석 정확성·실차 안전성·보편적 의미보존 증명이 아니다. 전제가 모두 해소되면 진입은 허용되지만 강제하지 않으므로 정상 진행 가능성만 검사했다.\n\n"
        "#18의 Agent3는 출처상 후보이며 사건 시점 대상/영역·양보 의무·근거 수용은 미확정이다. 실제 입력은 UNKNOWN/invalid로 보존했다. CNL 독립 검토와 행동 정답은 없고 학습 export는 0건이다. DEFER_ENTRY를 행동 정답으로 복사하지 않는다.\n",
        encoding="utf-8")
    return result


def run(output):
    output.mkdir(parents=True, exist_ok=False, mode=0o700)
    code = [Path(__file__).resolve(), Path(__file__).with_name("worked_example.py"), Path(__file__).with_name("align_reviews.py"),
            ROOT / "projects/04-guardsynth-coc/src/guard_synth/qualitative_scene_contract.py"]
    # Pin the reusable implementation and all schemas, including transitive compiler dependencies.
    package = ROOT / "platforms/eblc-bcv/src/guard_synth_eblc"
    code += sorted(package.glob("*.py")) + sorted((package / "schemas").glob("*.json"))
    manifest = {"project_id": "guardsynth-coc", "experiment_id": EXPERIMENT, "run_id": output.name,
        "created_at_utc": datetime.now(timezone.utc).isoformat(), "status": "RUNNING", "network_used": False,
        "code_hashes": {str(p.relative_to(ROOT)): digest(p) for p in code}}
    write_json(output / "RUN_MANIFEST.json", manifest)
    try:
        result = execute(output)
    except Exception as exc:
        manifest["status"] = "FAILED"
        write_json(output / "RESULT.json", {"status": "FAILED", "error": f"{type(exc).__name__}: {exc}"})
        write_json(output / "RUN_MANIFEST.json", manifest)
        raise
    manifest.update(status=result["status"], input_hashes=result["input_hashes"],
                    runtime={"python": sys.version, "executable": sys.executable, "z3_version": result["z3_version"]})
    manifest["output_hashes"] = {p.name: digest(p) for p in sorted(output.iterdir()) if p.name != "RUN_MANIFEST.json"}
    write_json(output / "RUN_MANIFEST.json", manifest)
    for path in output.iterdir():
        path.chmod(0o600)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*-[0-9]+", args.run_id):
        parser.error("run-id must be kebab-case ending in a number")
    output = BASE / EXPERIMENT / args.run_id
    result = run(output)
    print(result["status"], result["matches_expected"], "/", result["query_count"], "queries")
    print(output)


if __name__ == "__main__":
    main()
