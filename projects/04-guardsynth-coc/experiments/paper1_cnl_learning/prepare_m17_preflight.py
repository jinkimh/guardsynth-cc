"""Replay 30 reviewed scenes; prepare conditional contracts and M17 gates, never gold."""

import argparse
from collections import Counter, defaultdict
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sys

import accept_source_observations as acceptance
import execute_reviewed_contract as review
from guard_synth_eblc.action_contract import parse_action_contract, lower_action_contract, literal, neg, var, conjunction
from guard_synth_eblc.cnl_renderer import render_action_contract, export_cnl

entry = acceptance.entry
ROOT = entry.r.ROOT
BASE = entry.PARENT.parent
INTAKE = BASE / "source-observation-intake-2026-09-28-001"
PACKET = BASE / "source-gap-ui-2026-09-09-002/source_gap_packet.json"
EXPOSURE = ROOT / "artifacts/projects/guardsynth-coc/restricted/guardsynth-eblc-learning-001/paper1-source-audit-2026-09-06-002/source_audit.json"
DESIGN = ROOT / "projects/04-guardsynth-coc/docs/designs/PAPER1_M17_MACHINE_PREFLIGHT_DESIGN_V01.md"
CLAIM = "CONDITIONAL_ACTION_SELECTION_NOT_VEHICLE_SAFETY"


def scope_route(answer):
    if answer["target_status"] == answer["zone_status"] == "CONFIRMED":
        if answer["ped_truth"] in {"TRUE", "FALSE"}:
            return "CONDITIONAL_PEDESTRIAN_CANDIDATE"
        return "OCCUPANCY_UNRESOLVED"
    if answer["control_context"] == "APPLICABLE":
        return "CONTROL_TASK_OUTSIDE_PEDESTRIAN_SUBSET"
    return "TARGET_ZONE_OR_APPLICABILITY_UNRESOLVED"


def build_contract(answer, scene, refs):
    if scope_route(answer) != "CONDITIONAL_PEDESTRIAN_CANDIDATE":
        raise ValueError("unsupported or unresolved pedestrian binding")
    key = scene["candidate_digest"].split(":")[1][:12]
    return parse_action_contract({
        "contract_version": "eblc-action-contract-v0.1", "contract_id": "ped_candidate_" + key,
        "horizon": 3, "claim_scope": CLAIM, "subject_id": "ego",
        "zone_id": "reviewed_zone_" + key, "policy": "CLEAR_REQUIRED_FOR_ENTRY",
        "source_refs": refs, "obligations": [{"obligation_id": "ped",
            "predicate_id": "person_occupies_designated_entry_path",
            "target_entity_id": "reviewed_person_" + key,
            "rule_ref": refs[0], "source_refs": refs}],
    })


def checks_for(contract, truth):
    h = review.helpers
    core = lower_action_contract(contract)
    core["clauses"].append({"id": "reported_relation_hypothesis", "kind": "ASSUMPTION",
        "enforcement": "INITIAL", "formula": h.evidence("ped", truth),
        "source_refs": contract.raw["source_refs"],
        "description": "Assume the reviewer report is correct ONLY for this conditional scenario; not source certification."})
    enter = h.eq("action", "ENTER_ZONE", enum="Action")
    h.add_query(core, "current_enter", enter, "UNSAT" if truth == "TRUE" else "SAT")
    h.add_query(core, "current_defer", h.eq("action", "DEFER_ENTRY", enum="Action"), "SAT")
    h.add_query(core, "opposite_active", neg(var("ped_active")) if truth == "TRUE" else var("ped_active"), "UNSAT")
    for prior in (False, True):
        h.add_query(core, "unobserved_prior_" + str(prior).lower(), h.eq("ped_prior_active", prior), "SAT")
    for future in ("TRUE", "FALSE"):
        h.add_query(core, "unobserved_future_" + future.lower(), h.evidence("ped", future, offset=1), "SAT")
    generic = lower_action_contract(contract)
    generic["queries"] = []
    for name, premise, probe, expected in (
        ("unknown", h.evidence("ped", "UNKNOWN"), enter, "UNSAT"),
        ("invalid_clear", h.evidence("ped", "FALSE", False), enter, "UNSAT"),
        ("clear", h.evidence("ped", "FALSE"), enter, "SAT"),
        ("conflict", h.evidence("ped", "CONFLICT"), enter, "UNSAT"),
    ):
        h.add_query(generic, name + "_premises", premise, "SAT")
        h.add_query(generic, name + "_probe", conjunction(premise, probe), expected)
    mutant = lower_action_contract(contract)
    mutant["clauses"] = [c for c in mutant["clauses"] if c["id"] != "action_gate"]
    mutant["queries"] = []
    gap = conjunction(h.evidence("ped", "UNKNOWN"), h.eq("ped_prior_active", False), enter)
    h.add_query(mutant, "missing_gate_unknown_entry", gap, "SAT")
    return core, generic, mutant


def action_packet(scene, answer, sample):
    # Allowlist: no original CoC, target point, source annotations, answers or verdicts.
    return {"review_version": review.VERSION, "kind": "ACTION", "sample_id": sample,
        "event_timestamp_us": scene["event_timestamp_us"], "zone_polygon": deepcopy(answer["zone_polygon"]),
        "frames": [{"timestamp_us": f["timestamp_us"], "sha256": f["sha256"],
                    "is_t0": i == len(scene["frames"]) - 1} for i, f in enumerate(scene["frames"])],
        "choices": ["ENTER_ZONE", "DEFER_ENTRY", "UNJUDGEABLE"],
        "scope": "PROVISIONAL_DEVELOPMENT_TASK_NOT_MAIN_GOLD_REQUIRES_COORDINATOR_ACCEPTANCE",
        "gold_prefilled": False}


def write_packet(output, name, packet, images=None):
    entry.r.write_json(output / (name + "_packet.json"), packet)
    display = {**packet, "packet_sha256": entry.r.digest(output / (name + "_packet.json"))}
    if images is not None:
        display["images"] = images
    # Reuse immutable template semantics, change only its generic sample label/filename locally.
    template = review.TEMPLATE.read_text().replace("개발 예제 A001", packet["sample_id"])
    template = template.replace("'scene18_independent_'", "'" + packet["sample_id"] + "_'")
    notice = "배정 전 준비 자료: 담당자의 과제·영역 확인 및 독립 검토자 배정 후 사용합니다. 본 시험 정답이 아닙니다."
    if packet["kind"] == "CNL":
        notice += " CNL은 보행자 조건만 다루며 전체 진입 허가를 뜻하지 않습니다."
    template = template.replace('<h1 id="title"></h1>', '<p class="note">' + notice + '</p><h1 id="title"></h1>')
    (output / (name + ".html")).write_text(template.replace("__INDEPENDENT_REVIEW_PACKET__",
        json.dumps(display, ensure_ascii=False).replace("<", "\\u003c")), encoding="utf-8")


def exposure_ledger(rows, exposed):
    groups = defaultdict(list)
    for row in rows:
        groups[row["clip_id"]].append(row["candidate_digest"])
    return {"split_status": "NOT_FROZEN", "main_n": None, "fresh_test_scenes": 0,
        "excluded_test_clip_ids": sorted({r["group_id"] for r in exposed}),
        "groups": [{"clip_id": clip, "candidate_digests": ids, "assigned_split": "DEVELOPMENT_EXPOSED",
                    "main_test_allowed": False} for clip, ids in sorted(groups.items())],
        "upstream_train_val_is_paper_split": False, "independent_action_gold_added": 0}


def disposition(row):
    # Historical video-review numbers differ from acquisition/geometry candidate numbers.
    if row["review_index"] == 18:
        return "PRIOR_DEVELOPMENT_EXPORT"
    if row["review_index"] == 47:
        return "PRIOR_UNOBSERVABLE_NO_REPEAT"
    return "REVIEWED_DEVELOPMENT_PENDING_GATES"


def execute(output):
    inputs = {}
    for directory in (INTAKE, PACKET.parent, entry.PARENT):
        entry.pin_run(directory, inputs)
    for path in (DESIGN, acceptance.POLICY, EXPOSURE):
        inputs[str(path.relative_to(ROOT))] = entry.r.digest(path)
    packet = entry.r.load(PACKET)
    response = entry.r.load(INTAKE / "review_submission.json")
    acceptance.validate_submission(packet, entry.r.digest(PACKET), response, entry.r.load(INTAKE / "review_draft.json"))
    answers = {a["candidate_digest"]: a for a in response["records"]}
    candidates = entry.r.load(entry.PARENT / "candidate_readiness.json")["records"]
    by_id = {r["candidate_digest"]: r for r in candidates}
    bindings = {r["candidate_digest"]: r for r in entry.r.load(entry.PARENT / "event_source_bindings.json")["records"]}
    interpretations = {r["candidate_digest"]: r for r in entry.r.load(INTAKE / "observation_interpretations.json")["records"]}
    records, coordination = [], []
    total_checks = mutation_checks = generated_clauses = 0
    for position, scene in enumerate(packet["scenes"], 1):
        cid = scene["candidate_digest"]
        row, binding, answer = by_id[cid], bindings[cid], answers[cid]
        if (scene["clip_id"] != row["clip_id"] or scene["event_timestamp_us"] != row["event_timestamp_us"]
            or scene["original_coc"] != row["original_coc"]
            or hashlib.sha256(scene["original_coc"].encode()).hexdigest() != row["coc_sha256"]):
            raise ValueError("scene identity/CoC drift")
        entry.r.verified(ROOT / row["annotation_path"], row["annotation_sha256"])
        replay = entry.review_scene(row, binding, inputs)
        if replay["frames"] != scene["frames"]:
            raise ValueError("raw video to displayed frame replay differs")
        route = scope_route(answer)
        record = {"position": position, "candidate_digest": cid, "label": scene["label"],
            "clip_id": scene["clip_id"], "event_timestamp_us": scene["event_timestamp_us"],
            "source_replay": "PASS", "frame_count": len(scene["frames"]), "scope_route": route,
            "geometry_syntax": "PASS", "geometry_visual_semantics": "NOT_INDEPENDENTLY_VERIFIED",
            "source_linked_person_ids": binding["source_linked_person_ids"],
            "active_ego_actions_source_claims": binding["active_ego_actions"],
            "active_control_source_claims": binding["active_control_annotations"],
            "user_clarification": interpretations[cid]["user_clarification"],
            "raw_answer": answer, "actual_scene_entry_permission": None,
            "main_training_allowed": False, "independent_action_gold": None,
            "source_coc_agreement": "NOT_SCORED_WITHOUT_INDEPENDENT_REFERENCE"}
        if route == "CONDITIONAL_PEDESTRIAN_CANDIDATE":
            sample = f"development-p{position:03d}"
            folder = output / sample
            folder.mkdir()
            refs = ["sha256:" + entry.r.digest(DESIGN) + "#pedestrian-only-research-policy",
                    "sha256:" + entry.r.digest(INTAKE / "review_submission.json") + "#" + cid,
                    "sha256:" + row["annotation_sha256"] + "#source-context-not-gold"]
            contract = build_contract(answer, scene, refs)
            core, generic, mutant = checks_for(contract, answer["ped_truth"])
            for prefix, model in (("reported_hypothesis", core), ("generic_policy", generic), ("mutation", mutant)):
                checked = review.helpers.export_checks(model, folder, prefix)
                entry.r.write_json(folder / (prefix + "_core.json"), model)
                if prefix == "mutation": mutation_checks += checked["query_count"]
                else: total_checks += checked["query_count"]
            document = render_action_contract(contract)
            export_cnl(document, folder, text_name="conditional_constraints_en.txt", mapping_name="cnl_mapping.json")
            entry.r.write_json(folder / "action_contract.json", contract.raw)
            entry.r.write_json(folder / "binding_scope.json", {"candidate_digest": cid,
                "target_point": answer["target_point"], "zone_polygon": answer["zone_polygon"],
                "reported_pedestrian_relation": answer["ped_truth"], "formal_evidence_validated": False,
                "assumption_scope": "REPORT_CORRECT_HYPOTHESIS_NOT_WORLD_CERTIFICATION",
                "excluded_conditions": ["ROAD_YIELD", "SIGNALS_SIGNS_WORKER_CONTROLS", "METRIC_SAFETY"],
                "overall_entry_permission": None, "learning_export_allowed": False})
            action = action_packet(scene, answer, sample)
            write_packet(folder, "action_review", action, [f["data_url"] for f in scene["frames"]])
            cnl = {"review_version": review.VERSION, "kind": "CNL", "sample_id": sample + "-cnl",
                "clause_ids": [c.clause_id for c in document.clauses], "contract": contract.raw,
                "core_semantics": {**lower_action_contract(contract), "queries": []},
                "cnl_mapping": document.mapping_record(), "cnl_text": document.text,
                "scope": "PEDESTRIAN_ONLY_CONDITIONAL_FIDELITY_NOT_FULL_SCENE_POLICY", "gold_prefilled": False}
            write_packet(folder, "cnl_review", cnl)
            generated_clauses += len(document.clauses)
            record["conditional_artifact_directory"] = sample
            coordination.append({"sample_id": sample, "candidate_digest": cid,
                "action_packet": sample + "/action_review_packet.json",
                "action_page": sample + "/action_review.html", "cnl_page": sample + "/cnl_review.html",
                "action_reviewer_slots": [None, None], "cnl_reviewer": None,
                "known_source_exposed_reviewers": [response["reviewer_id"]],
                "assignment_state": "COORDINATOR_TASK_ZONE_ACCEPTANCE_REQUIRED",
                "order": "ACTION_BEFORE_CNL_OR_SOURCE", "adjudication_if_disagree": True})
        records.append(record)
        print(f"{position}/30 {scene['label']}: source replay PASS / {route}", flush=True)
    ledger = exposure_ledger(candidates, entry.r.load(EXPOSURE))
    ledger["candidate_dispositions"] = [{"candidate_digest": r["candidate_digest"],
        "disposition": disposition(r)}
        for r in candidates]
    if Counter(r["disposition"] for r in ledger["candidate_dispositions"]) != {
        "PRIOR_DEVELOPMENT_EXPORT": 1, "PRIOR_UNOBSERVABLE_NO_REPEAT": 1,
        "REVIEWED_DEVELOPMENT_PENDING_GATES": 30}:
        raise ValueError("historical development/abstention denominator drift")
    cn = len(coordination)
    result = {"project_id": "guardsynth-coc", "status": "M17_MACHINE_PREFLIGHT_COMPLETE_HUMAN_GATES_PENDING",
        "source_scenes_replayed": len(records), "frames_replayed": sum(r["frame_count"] for r in records),
        "scope_counts": dict(Counter(r["scope_route"] for r in records)), "denominator": len(candidates),
        "conditional_pedestrian_contracts": cn, "cnl_documents": cn, "cnl_clauses": generated_clauses,
        "solver_queries": total_checks, "solver_matches_expected": total_checks,
        "mutation_counterexamples_reproduced": mutation_checks,
        "provisional_action_packets": cn, "provisional_action_response_slots": 2 * cn,
        "fresh_test_scenes": 0, "main_n": None, "main_split_frozen": False,
        "source_verified_contracts_added": 0, "independent_action_gold_added": 0,
        "training_scenes_added": 0, "optimizer_steps": 0,
        "m16_gate": "PARTIAL", "m17_gate": "PARTIAL_PREPARATION_ONLY",
        "blockers": ["COORDINATOR_TASK_ZONE_INPUT_ACCEPTANCE", "TWO_INDEPENDENT_ACTION_REVIEWS_AND_ADJUDICATION",
                     "INDEPENDENT_CNL_SEMANTIC_AUDIT", "FULL_TASK_APPLICABILITY_AND_PROVIDER_SCOPE",
                     "FRESH_HELD_OUT_COHORT_AND_MAIN_N", "EMPIRICAL_INTRINSIC_COMPARISONS"]}
    for name, value in (("grounding_scope_audit.json", {"records": records}), ("split_exposure_ledger.json", ledger),
                        ("review_coordination.json", {"records": coordination}), ("RESULT.json", result)):
        entry.r.write_json(output / name, value)
    (output / "REPORT_KO.md").write_text(
        "# M16 기계 감사와 M17 준비\n\n"
        f"30장면 {result['frames_replayed']}개 과거 프레임을 원본 영상에서 재생성하고 픽셀·JPEG·시점·CoC·주석 연결을 재검증했다. "
        "대상 점·영역의 영상 의미를 기계 검증만으로 인증하지 않았다.\n\n"
        f"조건부 보행자 단일 제약 {cn}건 → 기존 EBLC Core/SMT → 공통 영문 CNL {cn}건을 생성했다. "
        f"{total_checks}/{total_checks} 조건부 질의 예상 일치, 게이트 제거 반례 {mutation_checks}건 재현. "
        "검토 답변이 옳다는 가정 아래의 논리 검증이며 장면 정답·완전한 진입 허가가 아니다. "
        "다른 차량·신호·통제는 제거/해제하지 않았고 지원 범위 밖으로 명시했다.\n\n"
        f"과제·영역 적합성 확인 후 사용할 독립 행동 자료 {cn}건(2인 응답 슬롯 {2*cn})과 "
        f"별도 CNL 자료 {cn}건({generated_clauses}개 조항)을 준비했다. 배정·답변은 0건이며 기존 설문 재작성이 아니다. "
        "담당자는 ACTION 링크만 먼저 전달하고 이후 CNL을 제공해야 한다.\n\n"
        f"기존 32개 후보를 모두 분모에 유지, {len(ledger['groups'])}개 개발 영상 그룹과 "
        f"기존 노출 {len(ledger['excluded_test_clip_ids'])}개 영상의 시험 제외 목록을 만들었다. "
        "신규 시험 장면과 main N은 미확정이다. M16/M17 전체 완료가 아니라 기계 준비 완료이다. "
        "독립 정답·의미 검토·과제 적용성·본 표본수/분할·실제 intrinsic 비교가 필요하다. 학습 데이터 추가와 가중치 갱신은 0이다.\n",
        encoding="utf-8")
    return result, inputs


def run(output):
    output.mkdir(parents=True, exist_ok=False, mode=0o700)
    package = ROOT / "platforms/eblc-bcv/src/guard_synth_eblc"
    code = list(Path(__file__).parent.glob("*.py")) + [review.TEMPLATE]
    code += list((ROOT / "projects/04-guardsynth-coc/src/guard_synth").glob("*.py"))
    code += list(package.glob("*.py")) + list((package / "schemas").glob("*.json"))
    manifest = {"project_id": "guardsynth-coc", "experiment_id": entry.admission.audit.EXPERIMENT,
        "run_id": output.name, "status": "RUNNING", "network_used": False,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "code_hashes": {str(p.relative_to(ROOT)): entry.r.digest(p) for p in code}}
    try:
        result, inputs = execute(output)
        manifest.update(status=result["status"], input_hashes=inputs)
    except Exception as exc:
        manifest["status"] = "FAILED"
        entry.r.write_json(output / "RESULT.json", {"status": "FAILED", "error": str(exc)})
        raise
    finally:
        manifest["output_hashes"] = {str(p.relative_to(output)): entry.r.digest(p)
            for p in output.rglob("*") if p.is_file() and p.name != "RUN_MANIFEST.json"}
        entry.r.write_json(output / "RUN_MANIFEST.json", manifest)
        for p in output.rglob("*"):
            if p.is_file(): p.chmod(0o600)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*-[0-9]+", args.run_id):
        parser.error("unused numeric-suffix run ID required")
    print(run(BASE / args.run_id))
