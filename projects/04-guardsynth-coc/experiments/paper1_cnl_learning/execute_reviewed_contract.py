"""Execute #18 corrected review through Core/SMT and prepare independent dev audits."""

import argparse
import base64
from copy import deepcopy
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from align_reviews import ROOT, BASE, digest, load, verified, write_json
from worked_example import source_example

# Avoid an ambiguous import of this experiment's action_contract.py vs platform module.
spec = importlib.util.spec_from_file_location("paper_action_helpers", Path(__file__).with_name("action_contract.py"))
helpers = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helpers)
from guard_synth.reviewed_action_contract import bind_reviewed_scene18
from guard_synth.independent_development_review import VERSION, validate_independent_review
from guard_synth_eblc.action_contract import lower_action_contract, literal, var, neg, conjunction
from guard_synth_eblc.cnl_renderer import render_action_contract, export_cnl

EXPERIMENT = "guardsynth-paper1-reviewed-contract-001"
CLARIFICATION = BASE / "guardsynth-paper1-source-acceptance-001/scene18-source-clarification-2026-09-08-001"
PREPARATION = BASE / "guardsynth-paper1-source-acceptance-001/scene18-source-acceptance-2026-09-08-003"
TEMPLATE = Path(__file__).with_name("independent_development_review.html")


def revalidate_run(path):
    m = load(path / "RUN_MANIFEST.json")
    if m["status"] in {"FAILED", "RUNNING"}:
        raise ValueError("incomplete source run")
    for rel, sha in m["output_hashes"].items():
        verified(path / rel, sha)
    for rel, sha in m.get("input_hashes", {}).items():
        verified(ROOT / rel, sha)
    return m


def reviewed_inputs():
    revalidate_run(CLARIFICATION)
    revalidate_run(PREPARATION)
    packet = load(PREPARATION / "source_review_packet.json")
    for rel, sha in packet["input_hashes"].items():
        verified(ROOT / rel, sha)
    original = load(CLARIFICATION / "original_submission.json")
    correction = load(CLARIFICATION / "clarification.json")
    effective = load(CLARIFICATION / "effective_review.json")
    for key, change in correction["changes"].items():
        if original[key] != change["before"]:
            raise ValueError("correction before value mismatch")
        original[key] = change["after"]
    if original != effective or correction["user_statement"] != "다른 차량의 움직임은 확인되지 않았어요.":
        raise ValueError("clarification replay mismatch")
    scene, inputs = source_example()
    inputs.update(packet["input_hashes"])
    for directory in (CLARIFICATION, PREPARATION):
        for name in ("RUN_MANIFEST.json", "RESULT.json"):
            inputs[str((directory/name).relative_to(ROOT))] = digest(directory/name)
    for name in ("original_submission.json", "effective_review.json", "clarification.json"):
        inputs[str((CLARIFICATION/name).relative_to(ROOT))] = digest(CLARIFICATION/name)
    inputs[str((PREPARATION/"source_review_packet.json").relative_to(ROOT))] = digest(PREPARATION/"source_review_packet.json")
    return scene, packet, effective, inputs


def observed_queries(core, binding):
    event = conjunction(*(helpers.evidence(oid, v["truth"], v["evidence_valid"]) for oid,v in binding["event_predicates"].items()))
    core["clauses"].append({"id": "reviewed_event_inputs", "kind": "ASSUMPTION", "enforcement": "INITIAL",
        "formula": event, "source_refs": [binding["review_ref"]],
        "description": "Human-reviewed single decision inputs; no prior or future state observation."})
    core["queries"] = []
    probes = [("event_premises", literal(True), "SAT"),
        ("event_enter", helpers.eq("action", "ENTER_ZONE", enum="Action"), "UNSAT"),
        ("event_defer", helpers.eq("action", "DEFER_ENTRY", enum="Action"), "SAT"),
        ("ped_not_active", neg(var("ped_active")), "UNSAT"),
        ("road_claimed_clear", var("road_clear"), "UNSAT"),
        ("review_not_required", neg(var("review_required")), "UNSAT"),
        ("road_prior_inactive", helpers.eq("road_prior_active", False), "SAT"),
        ("road_prior_active", helpers.eq("road_prior_active", True), "SAT"),
        ("unobserved_next_ped_true", helpers.evidence("ped", "TRUE", offset=1), "SAT"),
        ("unobserved_next_ped_false", helpers.evidence("ped", "FALSE", offset=1), "SAT")]
    for name, formula, expected in probes:
        helpers.add_query(core, name, formula, expected)
        core["queries"][-1]["description"] = "Single reviewed-event input test, not independent action truth: " + name


def write_review(output, name, packet, presentation):
    path = output / (name + "_packet.json")
    write_json(path, packet)
    display = {**packet, **presentation, "packet_sha256": digest(path)}
    html = TEMPLATE.read_text(encoding="utf-8")
    if html.count("__INDEPENDENT_REVIEW_PACKET__") != 1:
        raise ValueError("review template marker mismatch")
    (output/(name+".html")).write_text(html.replace("__INDEPENDENT_REVIEW_PACKET__", json.dumps(display,ensure_ascii=False).replace("<","\\u003c")),encoding="utf-8")


def execute(output):
    scene, packet, review, inputs = reviewed_inputs()
    design = ROOT / "projects/04-guardsynth-coc/docs/designs/PAPER1_INDEPENDENT_DEVELOPMENT_REVIEW_DESIGN_V01.md"
    inputs[str(design.relative_to(ROOT))] = digest(design)
    inputs[str(helpers.POLICY.relative_to(ROOT))] = digest(helpers.POLICY)
    policy_ref = "sha256:"+digest(helpers.POLICY)+"#GS-PAPER1-ENTRY-POLICY-v0.1"
    review_ref = "sha256:"+digest(CLARIFICATION/"effective_review.json")+"#user-clarified-development-review"
    refs = [policy_ref,review_ref,
        "sha256:"+digest(PREPARATION/"source_review_packet.json")+"#source-review-packet",
        "sha256:"+inputs[scene["annotation_path"]]+"#CASCADE-scene18"]
    contract,binding = bind_reviewed_scene18(scene,packet,review,packet_sha256=digest(PREPARATION/"source_review_packet.json"),
        review_ref=review_ref,policy_ref=policy_ref,source_refs=refs)
    if binding["event_predicates"] != {"ped":{"truth":"TRUE","evidence_valid":True},"road":{"truth":"UNKNOWN","evidence_valid":False}}:
        raise ValueError("outside this pinned reviewed-event experiment")
    core = lower_action_contract(contract)
    observed_queries(core,binding)
    checked = helpers.export_checks(core,output,"observed")
    document = render_action_contract(contract)
    export_cnl(document,output,text_name="constraints.txt",mapping_name="cnl_mapping.json")
    for name,value in (("action_contract.json",contract.raw),("event_binding.json",binding),("core_model.json",core)):
        write_json(output/name,value)
    # Action reviewers get an allowlisted task view, never the source packet itself.
    frames = [{k:f[k] for k in ("timestamp_us","sha256","is_t0")} for f in packet["frames"]]
    action_packet = {"review_version":VERSION,"kind":"ACTION","sample_id":"development-a001",
        "event_timestamp_us":packet["event_timestamp_us"],"zone_polygon":review["zone_polygon"],
        "frames":frames,"choices":["ENTER_ZONE","DEFER_ENTRY","UNJUDGEABLE"],
        "scope":"DEVELOPMENT_ACTION_AUDIT_NOT_HELD_OUT_TEST","gold_prefilled":False}
    images=[]
    for f in packet["frames"]:
        if f["timestamp_us"]>packet["event_timestamp_us"]:
            raise ValueError("future frame leak")
        image_path=PREPARATION/f["file"];verified(image_path,f["sha256"])
        inputs[str(image_path.relative_to(ROOT))]=f["sha256"]
        images.append("data:image/jpeg;base64,"+base64.b64encode(image_path.read_bytes()).decode())
    write_review(output,"scene18_independent_action_review",action_packet,{"images":images})
    # CNL reviewers see the intended contract and Core, but not the solver verdict or source answers.
    audit_core=deepcopy(core)
    audit_core["clauses"]=[c for c in audit_core["clauses"] if c["id"]!="reviewed_event_inputs"]
    audit_core["queries"]=[]
    cnl_packet={"review_version":VERSION,"kind":"CNL","sample_id":"development-cnl-a001",
        "clause_ids":[c.clause_id for c in document.clauses],"contract":contract.raw,"core_semantics":audit_core,
        "cnl_mapping":document.mapping_record(),"cnl_text":document.text,
        "scope":"INDEPENDENT_DEVELOPMENT_FIDELITY_AUDIT_NOT_GENERAL_LANGUAGE_PROOF","gold_prefilled":False}
    write_review(output,"scene18_independent_cnl_review",cnl_packet,{})
    write_json(output/"review_coordination.json",{"action_packet":"scene18_independent_action_review_packet.json",
        "cnl_packet":"scene18_independent_cnl_review_packet.json","candidate_digest":scene["candidate_digest"],
        "known_source_exposed_reviewers":[review["reviewer_id"]],"required_order":"ACTION_BEFORE_CNL_OR_SOURCE_MATERIAL",
        "reviewer_assignment":"PENDING_HUMAN_COORDINATION","scope":"DEVELOPMENT_ONLY",
        "warning":"Do not send source/CNL/solver materials to an action reviewer before their decision."})
    result={"status":"REVIEWED_EVENT_EXECUTED_INDEPENDENT_AUDIT_PENDING","project_id":"guardsynth-coc",
        "input_hashes":inputs,"query_count":checked["query_count"],"matches_expected":checked["matches_expected"],
        "z3_version":checked["z3_version"],"event_predicates":binding["event_predicates"],
        "enter_status":"UNSAT","defer_status":"SAT","conditioned_event_count":1,"observed_core_offsets":[0],
        "full_source_verified_contracts":0,"independent_action_reviews":0,"independent_cnl_reviews":0,
        "training_exports":0,"independent_action_gold":None,"claim_scope":"REVIEW_CONDITIONED_BOUNDED_CONTRACT_NOT_SCENE_SAFETY_OR_LEARNING_EFFECT"}
    write_json(output/"RESULT.json",result)
    (output/"REPORT_KO.md").write_text("# #18 검토 근거 연결 실행\n\n"
        "원본·추가 확인을 재검증하고 확정된 대상/영역 및 보행자 TRUE/valid, 주도로 UNKNOWN/invalid를 기존 Core의 INITIAL 전제로 연결했다. 이전/다음 시점 관측은 만들지 않았다.\n\n"
        "10/10 검사 예상 일치: 전제 SAT, 진입 UNSAT, 보류 SAT. 보행자 비활성·주도로 clearance·review 미필요 반례는 UNSAT다. 미관측 이전 road 상태와 다음 ped TRUE/FALSE는 각각 SAT로 자유 입력임을 확인했다.\n\n"
        "공통 CNL은 조건부 정책을 표현하며 현재 관측 값은 별도 event_binding.json에 있다. 이를 합쳐 영상 사실이나 독립 행동 정답으로 주장하지 않는다. 원본 CoC/기존 답변/솔버 결과가 없는 독립 행동 화면과 조항별 CNL 검토 화면을 분리했다.\n\n"
        "#18은 이미 노출된 개발 사례다. Jin Hyun Kim은 이 장면의 source/CoC를 보았으므로 독립 행동 검토자로 자동 인정하지 않는다. 다른 검토자의 실제 응답이 필요하며, 행동 검토 전에 CNL/source 자료를 보여주지 않는다. 검토 자료 준비는 응답 완료가 아니다. 전체 source/학습 export는 0건이다.\n",encoding="utf-8")
    return result


def run(output):
    output.mkdir(parents=True,exist_ok=False,mode=0o700)
    package=ROOT/"platforms/eblc-bcv/src/guard_synth_eblc"
    code=[Path(__file__).resolve(),TEMPLATE,Path(__file__).with_name("action_contract.py"),Path(__file__).with_name("worked_example.py"),Path(__file__).with_name("align_reviews.py")]
    code += [ROOT/"projects/04-guardsynth-coc/src/guard_synth"/name for name in ("source_acceptance.py","qualitative_scene_contract.py","reviewed_action_contract.py","independent_development_review.py")]
    code += sorted(package.glob("*.py"))+sorted((package/"schemas").glob("*.json"))
    m={"project_id":"guardsynth-coc","experiment_id":EXPERIMENT,"run_id":output.name,"created_at_utc":datetime.now(timezone.utc).isoformat(),
       "status":"RUNNING","network_used":False,"code_hashes":{str(p.relative_to(ROOT)):digest(p) for p in code}}
    write_json(output/"RUN_MANIFEST.json",m)
    try:result=execute(output)
    except Exception as exc:
        m["status"]="FAILED";write_json(output/"RESULT.json",{"status":"FAILED","error":str(exc)});write_json(output/"RUN_MANIFEST.json",m);raise
    m.update(status=result["status"],input_hashes=result["input_hashes"],runtime={"python":sys.version,"z3_version":result["z3_version"]})
    m["output_hashes"]={p.name:digest(p) for p in output.iterdir() if p.name!="RUN_MANIFEST.json"}
    write_json(output/"RUN_MANIFEST.json",m)
    for p in output.iterdir():p.chmod(0o600)
    return result


def intake(output, review_path, packet_path):
    revalidate_run(packet_path.parent)
    packet=load(packet_path)
    expected_name={"ACTION":"scene18_independent_action_review_packet.json","CNL":"scene18_independent_cnl_review_packet.json",
                   "SCENE_CNL":"scene18_scene_cnl_review_packet.json"}
    if packet_path.name!=expected_name.get(packet.get("kind")):
        raise ValueError("independent packet filename/kind mismatch")
    coordination=load(packet_path.parent/"review_coordination.json")
    known=coordination["known_source_exposed_reviewers"] if packet["kind"] in ("ACTION","SCENE_CNL") else ()
    verdict=validate_independent_review(load(review_path),packet,digest(packet_path),known_exposed_reviewer_ids=known)
    output.mkdir(parents=True,exist_ok=False,mode=0o700)
    write_json(output/"review_submission.json",load(review_path))
    result={"project_id":"guardsynth-coc","status":"INDEPENDENT_DEVELOPMENT_REVIEW_RECORDED",**verdict}
    if packet["kind"] == "SCENE_CNL":
        result.update(review_basis="SCENE_CONDITIONED_CNL_CLAIM_REVIEW", review_language="ko",
                      reviewed_clause_ids=packet["clause_ids"], english_only_fidelity_established=False,
                      claim_scope="INFORMED_SCENE_CNL_REVIEW_NOT_BLIND_ACTION_GOLD_OR_FULL_SEMANTIC_PROOF")
    if "korean_review" in packet:
        result["review_basis"] = packet["korean_review"]["review_basis"]
        result["presentation_version"] = packet["korean_review"]["presentation_version"]
        result["english_only_fidelity_established"] = False
        result["reviewed_clause_ids"] = packet["korean_review"].get("review_clause_ids", packet["clause_ids"])
        result["excluded_review_clause_ids"] = packet["korean_review"].get("excluded_review_clause_ids", [])
    write_json(output/"RESULT.json",result)
    m={"project_id":"guardsynth-coc","experiment_id":EXPERIMENT,"run_id":output.name,
        "created_at_utc":datetime.now(timezone.utc).isoformat(),"status":result["status"],
        "input_hashes":{str(p.resolve()):digest(p) for p in (review_path,packet_path,packet_path.parent/"RUN_MANIFEST.json")},
        "code_hashes":{str(p.relative_to(ROOT)):digest(p) for p in (Path(__file__).resolve(),ROOT/"projects/04-guardsynth-coc/src/guard_synth/independent_development_review.py")},
        "output_hashes":{p.name:digest(p) for p in output.iterdir()}}
    write_json(output/"RUN_MANIFEST.json",m)
    for p in output.iterdir():p.chmod(0o600)
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument("--run-id",required=True)
    parser.add_argument("--review",type=Path);parser.add_argument("--packet",type=Path);args=parser.parse_args()
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*-[0-9]+",args.run_id):parser.error("unused kebab-case numeric run ID required")
    if bool(args.review)!=bool(args.packet):parser.error("--review and --packet must be paired")
    out=BASE/EXPERIMENT/args.run_id
    result=intake(out,args.review,args.packet) if args.review else run(out)
    print(result["status"]);print(out)


if __name__=="__main__":main()
