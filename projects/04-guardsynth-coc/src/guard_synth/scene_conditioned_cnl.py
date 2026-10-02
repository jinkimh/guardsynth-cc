"""Evidence-conditioned entry instruction for the paper-1 two-obligation subset.

Project-specific predicates and language; shared EBLC compiler remains authoritative.
No inferred visual observations, law, metric control, independent gold or training approval.
"""

from copy import deepcopy
import hashlib
import json

from guard_synth_eblc.action_contract import parse_action_contract, lower_action_contract, var, literal, binary, conjunction, neg
from guard_synth_eblc.core_ir import parse_core_model
from guard_synth_eblc.smt_compiler import compile_core_model, check_queries

VERSION = "paper1-scene-conditioned-cnl-v0.1"


def object_sha(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()


def generate_scene_cnl(raw_contract, binding):
    contract = parse_action_contract(raw_contract)
    obs = binding["event_predicates"]
    required = {"ped":"pedestrian_conflict", "road":"main_road_yield_required"}
    if (contract.raw["subject_id"] != "ego"
        or {o["obligation_id"]:o["predicate_id"] for o in contract.raw["obligations"]} != required):
        raise ValueError("unsupported scene predicate subset")
    if (set(obs) != set(required) or binding["observed_core_offsets"] != [0]
        or not contract.raw["zone_id"] or binding["zone_id"] != contract.raw["zone_id"]
        or binding["review_ref"] not in contract.raw["source_refs"]):
        raise ValueError("unbound scene/time/source")
    if (type(binding["event_timestamp_us"]) is not int or type(binding["source_frame_timestamp_us"]) is not int
        or binding["source_frame_timestamp_us"] > binding["event_timestamp_us"]):
        raise ValueError("invalid event or future input")
    for v in obs.values():
        if (set(v) != {"truth","evidence_valid"} or v["truth"] not in ("TRUE","FALSE","UNKNOWN","CONFLICT")
            or type(v["evidence_valid"]) is not bool):
            raise ValueError("invalid observation")

    def eq(name,value,offset=0,enum=None):return binary("eq",var(name,offset),literal(value,enum))
    def evidence(oid,v,offset=0):
        return conjunction(eq(oid+"_truth",v["truth"],offset,"Truth"),eq(oid+"_evidence_valid",v["evidence_valid"],offset))
    core=lower_action_contract(contract)
    event=conjunction(*(evidence(oid,obs[oid]) for oid in required))
    core["clauses"].append({"id":"reviewed_event_inputs","kind":"ASSUMPTION","enforcement":"INITIAL",
        "formula":event,"source_refs":[binding["review_ref"]],"description":"One reviewed event; future values remain free."})
    core["queries"]=[]
    def query(qid,formula,expected):
        core["queries"].append({"id":qid,"formula":formula,"expected":expected,"classification":"EXAMPLE",
            "source_refs":core["source_refs"],"description":"Scene-conditioned claim check, not independent scene truth: "+qid})
    clear=all(v=={"truth":"FALSE","evidence_valid":True} for v in obs.values())
    unresolved=any(not v["evidence_valid"] or v["truth"] in ("UNKNOWN","CONFLICT") for v in obs.values())
    query("event_premises",literal(True),"SAT")
    query("event_enter",eq("action","ENTER_ZONE",enum="Action"),"SAT" if clear else "UNSAT")
    query("event_defer",eq("action","DEFER_ENTRY",enum="Action"),"SAT")
    for oid in required:query(oid+"_observation_contradiction",neg(evidence(oid,obs[oid])),"UNSAT")
    query("review_flag_contradiction",neg(eq("review_required",unresolved)),"UNSAT")
    next_clear=conjunction(*(evidence(oid,{"truth":"FALSE","evidence_valid":True},1) for oid in required))
    query("next_entry_without_clearance",conjunction(eq("action","ENTER_ZONE",1,"Action"),neg(next_clear)),"UNSAT")
    query("next_clearance_premises",next_clear,"SAT")
    query("next_clearance_enter",conjunction(next_clear,eq("action","ENTER_ZONE",1,"Action")),"SAT")
    query("next_clearance_defer",conjunction(next_clear,eq("action","DEFER_ENTRY",1,"Action")),"SAT")
    # Show that road uncertainty is not filled from the solver's arbitrary witness.
    for prior in (False,True):query("road_prior_"+str(prior).lower(),eq("road_prior_active",prior),"SAT")
    checked=check_queries(compile_core_model(parse_core_model(core)))
    if checked["matches_expected"] != checked["query_count"]:
        raise ValueError("scene CNL support checks failed; no text emitted")

    clauses=[]
    labels={"ped":("보행자 관련 위험","pedestrian-related risk"),"road":("주도로 교통에 양보할 필요","need to yield to main-road traffic")}
    for oid,(ko,en) in labels.items():
        v=obs[oid]
        subject=ko+("이" if oid=="ped" else "가")
        if v["evidence_valid"] and v["truth"] in ("TRUE","FALSE"):
            exists=v["truth"]=="TRUE"
            text_ko=f"현재 검토 결과에서는 {subject} {'있다' if exists else '없다'}고 확인되었습니다."
            text_en=f"The current reviewed evidence confirms {'the presence' if exists else 'the absence'} of {en}."
        elif v["truth"]=="CONFLICT":
            text_ko=f"{ko}에 관한 근거가 서로 충돌하므로, 현재 판단을 확정할 수 없습니다."
            text_en=f"Evidence about {en} conflicts; it cannot currently be resolved."
        else:
            text_ko=f"{subject} 있는지는 현재 유효한 근거로 확인되지 않았습니다."
            text_en=f"Whether there is {en} is not established by valid current evidence."
        clauses.append({"id":"observation."+oid,"kind":"REVIEW_ATTRIBUTED_OBSERVATION", "text_ko":text_ko,"text_en":text_en,
            "semantics":{"obligation_id":oid,**deepcopy(v),"attribution":"review_not_solver_perception"},
            "binding_paths":["$.event_predicates."+oid,"$.review_ref"],"core_clause_ids":["reviewed_event_inputs"],
            "support_query_ids":["event_premises",oid+"_observation_contradiction"]})
    clauses.append({"id":"action.now","kind":"CURRENT_POLICY_INSTRUCTION",
        "text_ko":("현재 검토 근거와 이 과제의 규칙에 따르면, 에고 차량은 지금 지정된 영역으로 진입할 수 있습니다. 다만 진입을 계속 보류해도 됩니다." if clear else
                   "현재 검토 근거와 이 과제의 규칙에 따르면, 에고 차량은 지금 지정된 영역으로 진입하지 말고 진입을 보류해야 합니다."),
        "text_en":("Under the current reviewed evidence and task policy, the ego vehicle may enter the designated zone now; deferring entry is also allowed." if clear else
                   "Under the current reviewed evidence and task policy, the ego vehicle must not enter the designated zone now and must defer entry."),
        "semantics":{"offset":0,"allowed_actions":["DEFER_ENTRY","ENTER_ZONE"] if clear else ["DEFER_ENTRY"],"zone_id":binding["zone_id"]},
        "binding_paths":["$.event_predicates","$.zone_id"],"core_clause_ids":["reviewed_event_inputs","entry_gate","action_gate"],
        "support_query_ids":["event_premises","event_enter","event_defer"]})
    clauses.append({"id":"action.reconsider","kind":"CONDITIONAL_REASSESSMENT_NOT_FUTURE_OBSERVATION",
        "text_ko":"이후에는 보행자 관련 위험이 없고 주도로 교통에 양보할 필요도 없다는 점이 모두 유효한 근거로 확인되어야 지정된 영역으로 진입할 수 있습니다. 둘 중 하나라도 확인되지 않으면 진입을 보류하세요. 두 조건이 모두 확인되어도 반드시 진입해야 하는 것은 아닙니다.",
        "text_en":"At a later decision, entry into the designated zone is permitted only when valid evidence confirms both no pedestrian-related risk and no need to yield to main-road traffic. Defer entry if either clearance is unconfirmed. Even when both are confirmed, entry is not mandatory.",
        "semantics":{"requires_all_confirmed_clearance":["ped","road"],"forces_entry":False,"future_observation_claimed":False},
        "binding_paths":[],"core_clause_ids":["ped_clear","road_clear","entry_gate","action_gate"],
        "support_query_ids":["next_entry_without_clearance","next_clearance_premises","next_clearance_enter","next_clearance_defer"]})
    document={"version":VERSION,"event_timestamp_us":binding["event_timestamp_us"],"zone_id":binding["zone_id"],
        "contract_sha256":object_sha(contract.raw),"binding_sha256":object_sha(binding),"core_sha256":object_sha(core),
        "clauses":clauses,"text_ko":"\n".join(c["text_ko"] for c in clauses),"text_en":"\n".join(c["text_en"] for c in clauses),
        "learning_export_allowed":False,"independent_semantic_review_complete":False,
        "claim_scope":"REVIEW_CONDITIONED_TWO_ACTION_INSTRUCTION_NOT_FULL_LIFECYCLE_EQUIVALENCE_OR_VEHICLE_SAFETY"}
    return document,core,checked
