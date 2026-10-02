"""Generate actual scene-conditioned text, traceable review and a blocked CoC preview."""

import argparse
import base64
import hashlib
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sys

import execute_reviewed_contract as r
from guard_synth.scene_conditioned_cnl import generate_scene_cnl
from guard_synth.independent_development_review import SCENE_VERSION

PARENT=r.BASE/r.EXPERIMENT/"reviewed-scene18-execution-2026-09-08-001"
TEMPLATE=Path(__file__).with_name("scene_cnl_review.html")
DESIGN=r.ROOT/"projects/04-guardsynth-coc/docs/designs/PAPER1_SCENE_CONDITIONED_CNL_DESIGN_V01.md"


def execute(output):
    r.revalidate_run(PARENT)
    scene,source,review,inputs=r.reviewed_inputs()
    raw=r.load(PARENT/"action_contract.json");saved=r.load(PARENT/"event_binding.json")
    contract,binding=r.bind_reviewed_scene18(scene,source,review,
        packet_sha256=r.digest(r.PREPARATION/"source_review_packet.json"),review_ref=saved["review_ref"],
        policy_ref=raw["obligations"][0]["rule_ref"],source_refs=raw["source_refs"])
    if contract.raw!=raw or binding!=saved:raise ValueError("review binding replay differs from pinned execution")
    document,core,checks=generate_scene_cnl(raw,binding)
    for q in checks["results"]:
        name="claim_"+q["query_id"]+".smt2"
        (output/name).write_text(q.pop("smt2"),encoding="utf-8");q["smt2_file"]=name
    for name,value in (("scene_cnl.json",document),("core_model.json",core),("claim_checks.json",checks),("event_binding.json",binding)):
        r.write_json(output/name,value)
    for lang in ("ko","en"):(output/("scene_constraints_"+lang+".txt")).write_text(document["text_"+lang]+"\n",encoding="utf-8")
    titles={"observation.ped":"보행자에 관한 문장", "observation.road":"확인하지 못한 주도로 교통에 관한 문장",
            "action.now":"이 장면에서 지금 해야 할 행동", "action.reconsider":"나중에 진입을 다시 판단할 조건"}
    evidence={
        "observation.ped":["기존 보행자 검토 답변: "+review["ped_reason"].strip(),"구조화된 수용값: 보행자 위험 있음 / 근거 유효. 이는 사람의 검토 결과이지 솔버의 영상 인식 결과가 아닙니다."],
        "observation.road":[review["road_reason"],"수용값: 주도로 양보 필요 여부 UNKNOWN / 근거 미확정. 차량이 없다거나 양보가 불필요하다고 확인한 것이 아닙니다."],
        "action.now":["입력: 보행자 위험 확인, 주도로 양보 필요 여부 미확인.","이 과제의 정책: 두 조건 모두 해제가 확인되어야 진입 허용.","해당 입력으로 실행한 결과: 진입 불허, 진입 보류 허용. 이 결과는 주어진 전제와 진입/보류 두 행동 범위에 한정됩니다."],
        "action.reconsider":["이후 영상에서 이미 해제됐다는 관측은 없습니다.","명세의 진입 조건: 보행자 위험 없음과 주도로 양보 필요 없음이 모두 유효한 근거로 확인되어야 합니다. 허가가 있어도 진입을 강제하지 않습니다."]}
    questions={"observation.ped":"기존 보행자 검토 결과를 과장하거나 다른 사실을 덧붙이지 않고 전달하나요?",
        "observation.road":"확인하지 못했다는 점을 유지하고, 차량이 없거나 양보가 불필요하다고 단정하지 않나요?",
        "action.now":"입력 근거와 정책으로 도출된 현재 행동(진입 금지·보류)을 문장이 정확히 전달하나요?",
        "action.reconsider":"두 조건을 모두 확인해야 한다는 점을 유지하고, 미래에 이미 안전해졌다고 단정하지 않나요?"}
    frames=[];images=[]
    for f in source["frames"]:
        if f["timestamp_us"]>binding["event_timestamp_us"]:raise ValueError("future review image")
        path=r.PREPARATION/f["file"];r.verified(path,f["sha256"])
        frames.append({k:f[k] for k in ("timestamp_us","sha256","is_t0")})
        images.append("data:image/jpeg;base64,"+base64.b64encode(path.read_bytes()).decode())
        inputs[str(path.relative_to(r.ROOT))]=r.digest(path)
    packet={"kind":"SCENE_CNL","review_version":SCENE_VERSION,"review_index":18,
        "event_timestamp_us":binding["event_timestamp_us"],"zone_polygon":binding["zone_polygon"],"target_point":binding["target_point"],
        "frames":frames,"generated_text_ko":document["text_ko"],"document_sha256":r.digest(output/"scene_cnl.json"),
        "clause_ids":[c["id"] for c in document["clauses"]],
        "items":[{"id":c["id"],"title":titles[c["id"]],"text":c["text_ko"],"kind":c["kind"],
                  "evidence":evidence[c["id"]],"question":questions[c["id"]],
                  "core_clause_ids":c["core_clause_ids"],"support_query_ids":c["support_query_ids"]} for c in document["clauses"]],
        "human_answers_prefilled":False,"review_basis":"INFORMED_SCENE_CNL_CLAIMS_NOT_BLIND_ACTION_GOLD",
        "learning_export_allowed":False}
    packet_path=output/"scene18_scene_cnl_review_packet.json";r.write_json(packet_path,packet)
    display={**packet,"packet_sha256":r.digest(packet_path),"images":images}
    template=TEMPLATE.read_text(encoding="utf-8")
    if template.count("__SCENE_CNL_PACKET__")!=1:raise ValueError("template marker")
    (output/"scene18_scene_cnl_review.html").write_text(template.replace("__SCENE_CNL_PACKET__",json.dumps(display,ensure_ascii=False).replace("<","\\u003c")),encoding="utf-8")
    r.write_json(output/"review_coordination.json",{"known_source_exposed_reviewers":[review["reviewer_id"]],
        "kind":"SCENE_CNL","required_order":"AFTER_BLIND_ACTION_SUBMISSION","reviewer_assignment":"PENDING_HUMAN_REVIEW",
        "scope":"INFORMED_CLAIM_REVIEW_NOT_ACTION_GOLD"})
    # Do not read the independent ACTION answer into the text generation path.
    r.write_json(output/"coc_cnl_preview.json",{"candidate_digest":scene["candidate_digest"],"clip_id":scene["clip_id"],
        "event_timestamp_us":scene["event_timestamp_us"],"original_coc":scene["coc"],
        "constraint_supervision_candidate_en":document["text_en"],
        "assistant_target_preview":scene["coc"]+"\n\nScene constraints:\n"+document["text_en"],
        "input_frames":frames,"learning_export_allowed":False,"independent_action_gold":None,
        "blocked_by":["INDEPENDENT_SCENE_CNL_REVIEW","FULL_SOURCE_ACCEPTANCE","GOLD_LINKAGE_AND_MAIN_SPLIT_FREEZE","ENGLISH_TEXT_FIDELITY_REVIEW"],
        "scope":"DEVELOPMENT_PREVIEW_NOT_TRAINING_RECORD"})
    for path in (PARENT/"RUN_MANIFEST.json",PARENT/"action_contract.json",PARENT/"event_binding.json",DESIGN,r.helpers.POLICY):
        inputs[str(path.relative_to(r.ROOT))]=r.digest(path)
    result={"project_id":"guardsynth-coc","status":"SCENE_CONDITIONED_CNL_GENERATED_REVIEW_PENDING",
        "input_hashes":inputs,"query_count":checks["query_count"],"matches_expected":checks["matches_expected"],
        "z3_version":checks["z3_version"],"generated_scene_count":1,"generated_clause_count":len(document["clauses"]),
        "event_predicates":binding["event_predicates"],"independent_scene_cnl_reviews":0,"training_exports":0,
        "full_source_verified_contracts":0,"claim_scope":document["claim_scope"]}
    r.write_json(output/"RESULT.json",result)
    (output/"REPORT_KO.md").write_text("# #18 실제 관측값을 연결한 자연어 생성\n\n"+document["text_ko"]+
        "\n\n실제 검토값과 명세를 함께 입력해 문장을 생성했다. 12/12 Core 질의 예상 일치. 관측은 사람 검토에 귀속하며, 주도로 UNKNOWN과 미관측 과거·미래를 유지한다. 현재 행동은 정책의 논리적 귀결이지 독립 정답이 아니다. 이후 조건은 가정적 재판단 조건이다.\n\n"
        "기존 공통 규칙 설명/A-B 화면은 장면별 검토를 대신하지 않는다. 별도 장면 화면에서 실제 생성 문장과 기존 근거를 검토한다. 독립 ACTION 답변은 생성 입력에서 제외했다. CoC 삽입 결과는 미리보기이며 학습 export·M16 전체 완료가 아니다.\n",encoding="utf-8")
    return result


def run(output):
    output.mkdir(parents=True,exist_ok=False,mode=0o700)
    code=[Path(__file__).resolve(),TEMPLATE,Path(r.__file__).resolve(),Path(r.helpers.__file__).resolve()]
    code += [r.ROOT/"projects/04-guardsynth-coc/src/guard_synth"/name for name in ("scene_conditioned_cnl.py","reviewed_action_contract.py","source_acceptance.py","qualitative_scene_contract.py","independent_development_review.py")]
    code += [Path(__file__).with_name(name) for name in ("align_reviews.py","worked_example.py")]
    package=r.ROOT/"platforms/eblc-bcv/src/guard_synth_eblc"
    code+=sorted(package.glob("*.py"))+sorted((package/"schemas").glob("*.json"))
    m={"project_id":"guardsynth-coc","experiment_id":r.EXPERIMENT,"run_id":output.name,"status":"RUNNING",
        "created_at_utc":datetime.now(timezone.utc).isoformat(),"network_used":False,
        "code_hashes":{str(p.relative_to(r.ROOT)):r.digest(p) for p in code}}
    r.write_json(output/"RUN_MANIFEST.json",m)
    try:result=execute(output)
    except Exception as exc:
        m["status"]="FAILED";r.write_json(output/"RESULT.json",{"status":"FAILED","error":str(exc)});r.write_json(output/"RUN_MANIFEST.json",m);raise
    m.update(status=result["status"],input_hashes=result["input_hashes"],runtime={"python":sys.version,"z3_version":result["z3_version"]})
    m["output_hashes"]={p.name:r.digest(p) for p in output.iterdir() if p.name!="RUN_MANIFEST.json"}
    r.write_json(output/"RUN_MANIFEST.json",m)
    for p in output.iterdir():p.chmod(0o600)
    return result


def refresh_review(output, source):
    """Re-render only the UI, retaining the exact packet and saved-draft identity."""
    source=source.resolve();r.revalidate_run(source)
    packet_path=source/"scene18_scene_cnl_review_packet.json"
    packet=r.load(packet_path)
    html_path=source/"scene18_scene_cnl_review.html"
    display=json.loads(re.search(r'<script id="packet" type="application/json">(.*?)</script>',html_path.read_text(encoding="utf-8"),re.S)[1])
    if display["packet_sha256"]!=r.digest(packet_path) or {k:v for k,v in display.items() if k not in {"images","packet_sha256"}}!=packet:
        raise ValueError("display differs from pinned packet")
    if len(display["images"])!=len(packet["frames"]):raise ValueError("image count mismatch")
    for frame,img in zip(packet["frames"],display["images"]):
        if frame["timestamp_us"]>packet["event_timestamp_us"] or hashlib.sha256(base64.b64decode(img.split(',',1)[1],validate=True)).hexdigest()!=frame["sha256"]:
            raise ValueError("display image mismatch")
    template=TEMPLATE.read_text(encoding="utf-8")
    if template.count("__SCENE_CNL_PACKET__")!=1:raise ValueError("template marker")
    names=["scene18_scene_cnl_review_packet.json","review_coordination.json","scene_cnl.json"]
    r.verified(source/"scene_cnl.json",packet["document_sha256"])
    paths=[source/name for name in names]+[html_path,source/"RUN_MANIFEST.json"]
    inputs={str(p.relative_to(r.ROOT)) if p.is_relative_to(r.ROOT) else str(p):r.digest(p) for p in paths}
    output.mkdir(parents=True,exist_ok=False,mode=0o700)
    for name in names:(output/name).write_bytes((source/name).read_bytes())
    (output/"scene18_scene_cnl_review.html").write_text(template.replace("__SCENE_CNL_PACKET__",json.dumps(display,ensure_ascii=False).replace("<","\\u003c")),encoding="utf-8")
    result={"project_id":"guardsynth-coc","status":"SCENE_CNL_REVIEW_UI_REFRESHED","source_run_id":source.name,
        "packet_sha256":r.digest(packet_path),"packet_unchanged":True,"draft_compatible":True,
        "claim_scope":"PRESENTATION_ONLY_NO_NEW_REVIEW_OR_TRAINING","input_hashes":inputs}
    r.write_json(output/"RESULT.json",result)
    r.write_json(output/"RUN_MANIFEST.json",{"project_id":"guardsynth-coc","experiment_id":r.EXPERIMENT,
        "run_id":output.name,"status":result["status"],"created_at_utc":datetime.now(timezone.utc).isoformat(),
        "network_used":False,"input_hashes":inputs,
        "code_hashes":{str(p.relative_to(r.ROOT)):r.digest(p) for p in (Path(__file__).resolve(),TEMPLATE)},
        "output_hashes":{p.name:r.digest(p) for p in output.iterdir()}})
    for p in output.iterdir():p.chmod(0o600)
    return result


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument("--run-id",required=True)
    parser.add_argument("--refresh-review-from",type=Path,help="Refresh UI only; preserve the source packet and browser drafts")
    args=parser.parse_args()
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*-[0-9]+",args.run_id):parser.error("unused numeric run ID required")
    output=r.BASE/r.EXPERIMENT/args.run_id
    result=refresh_review(output,args.refresh_review_from) if args.refresh_review_from else run(output)
    print(result["status"]);print(output)
