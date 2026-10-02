"""Studio's human-bound entry profile and Q1–Q5 queries. Not a visual extractor."""

import hashlib
import inspect
import json

from guard_synth_eblc.action_contract import parse_action_contract, lower_action_contract, var, literal, binary, conjunction, neg
from guard_synth_eblc.core_ir import parse_core_model
from guard_synth_eblc.smt_compiler import compile_core_model, check_queries
from guard_synth_eblc.cnl_renderer import render_action_contract

PROFILE = "studio-entry-v0.1"
QUERY_VERSION = "studio-entry-q1-q5-v0.1"
RENDERER_VERSION = "studio-entry-ko-v0.1"
PREDICATES = {"pedestrian_conflict": "보행자 관련 위험", "main_road_yield_required": "주도로 교통에 양보할 필요"}


def sha(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()


def renderer_signature():
    return sha([RENDERER_VERSION, inspect.getsource(render_action_contract), inspect.getsource(render)])


def validate_profile(raw, binding):
    contract = parse_action_contract(raw)
    if raw["horizon"] != 3 or raw["subject_id"] != "ego" or not raw["zone_id"]:
        raise ValueError("UNSUPPORTED Studio entry profile")
    if binding.get("zone_id") != raw["zone_id"] or not binding.get("zone_polygon"):
        raise ValueError("UNBOUND entry zone")
    if binding.get("max_observed_timestamp_us", 0) > binding["t0_us"]:
        raise ValueError("FUTURE observation")
    observations = binding.get("event_predicates", {})
    ids = {ob["obligation_id"] for ob in raw["obligations"]}
    if set(observations) != ids:
        raise ValueError("UNBOUND predicates")
    for ob in raw["obligations"]:
        if ob["predicate_id"] not in PREDICATES:
            raise ValueError("UNSUPPORTED predicate")
        obs = observations[ob["obligation_id"]]
        if obs.get("truth") not in ("TRUE", "FALSE", "UNKNOWN", "CONFLICT") or type(obs.get("evidence_valid")) is not bool:
            raise ValueError("Invalid four-valued observation")
        if obs.get("prior_active") is not None and type(obs["prior_active"]) is not bool:
            raise ValueError("Invalid prior state")
        if ob["target_entity_id"] is None:
            if not obs.get("contextual_target_confirmed"):
                raise ValueError("UNBOUND null target")
        elif ob["target_entity_id"] != binding.get("target_id") or not binding.get("target_point"):
            raise ValueError("UNBOUND target")
    return contract


def eq(name, value, offset=0, enum=None):
    return binary("eq", var(name, offset), literal(value, enum))


def evidence(oid, truth, valid=True, offset=0):
    return conjunction(eq(oid + "_truth", truth, offset, "Truth"), eq(oid + "_evidence_valid", valid, offset))


def add_query(core, qid, formula, expected):
    core["queries"].append({"id": qid, "formula": formula, "expected": expected, "classification": "EXAMPLE",
                            "source_refs": core["source_refs"], "description": qid + "; conditional, not scene truth"})


def build_models(raw, binding):
    contract = validate_profile(raw, binding)
    core = lower_action_contract(contract)
    obs = binding["event_predicates"]
    assumptions = [evidence(oid, v["truth"], v["evidence_valid"]) for oid, v in obs.items()]
    for oid, v in obs.items():
        if v.get("prior_active") is not None:
            assumptions.append(eq(oid + "_prior_active", v["prior_active"]))
    core["clauses"].append({"id": "reviewed_event", "kind": "ASSUMPTION", "enforcement": "INITIAL",
                            "formula": conjunction(*assumptions), "source_refs": raw["source_refs"],
                            "description": "Human-reviewed current evidence; later offsets unobserved"})
    core["queries"] = []
    clear = all(v["truth"] == "FALSE" and v["evidence_valid"] for v in obs.values())
    review = any(v["truth"] in ("UNKNOWN", "CONFLICT") or not v["evidence_valid"] for v in obs.values())
    add_query(core, "q1_premises", literal(True), "SAT")
    add_query(core, "q2_enter", eq("action", "ENTER_ZONE", enum="Action"), "SAT" if clear else "UNSAT")
    add_query(core, "q2_defer", eq("action", "DEFER_ENTRY", enum="Action"), "SAT")
    add_query(core, "q2_observation_contradiction", neg(conjunction(*assumptions)), "UNSAT")
    add_query(core, "q3_review_contradiction", neg(eq("review_required", review)), "UNSAT")
    for oid, v in obs.items():
        if v.get("prior_active") is None:
            for prior in (False, True):
                add_query(core, f"q3_{oid}_prior_{str(prior).lower()}", eq(oid + "_prior_active", prior), "SAT")
    next_clear = conjunction(*(evidence(oid, "FALSE", offset=1) for oid in obs))
    add_query(core, "q4_clear_premises", next_clear, "SAT")
    for action in ("ENTER_ZONE", "DEFER_ENTRY"):
        add_query(core, "q4_clear_" + action.lower(), conjunction(next_clear, eq("action", action, 1, "Action")), "SAT")
    add_query(core, "q4_no_clear_enter", conjunction(neg(next_clear), eq("action", "ENTER_ZONE", 1, "Action")), "UNSAT")
    harness = lower_action_contract(contract)
    harness["queries"] = []
    for oid in obs:
        trace = conjunction(evidence(oid, "TRUE"), evidence(oid, "FALSE", offset=1), evidence(oid, "TRUE", offset=2))
        add_query(harness, f"q5_{oid}_trace", trace, "SAT")
        for t, active in enumerate((True, False, True)):
            add_query(harness, f"q5_{oid}_active_{t}", conjunction(trace, neg(eq(oid + "_active", active, t))), "UNSAT")
        for t in (0, 2):
            add_query(harness, f"q5_{oid}_forbid_{t}", conjunction(trace, eq("action", "ENTER_ZONE", t, "Action")), "UNSAT")
        for truth, valid in (("UNKNOWN", True), ("CONFLICT", True), ("FALSE", False)):
            for prior in (False, True):
                premise = conjunction(eq(oid + "_prior_active", prior), evidence(oid, truth, valid))
                suffix = f"{oid}_{truth.lower()}_{str(valid).lower()}_{str(prior).lower()}"
                add_query(harness, "q5_hold_premises_" + suffix, premise, "SAT")
                add_query(harness, "q5_hold_" + suffix, conjunction(premise, neg(eq(oid + "_active", prior))), "UNSAT")
    if len(obs) > 1:
        a, b = list(obs)[:2]
        partial = conjunction(evidence(a, "FALSE", offset=1), evidence(b, "TRUE", offset=1))
        add_query(harness, "q5_partial_release", partial, "SAT")
        add_query(harness, "q5_partial_entry", conjunction(partial, eq("action", "ENTER_ZONE", 1, "Action")), "UNSAT")
    return core, harness


def check(raw, binding):
    models = build_models(raw, binding)
    results = [check_queries(compile_core_model(parse_core_model(m))) for m in models]
    passed = all(r["query_count"] > 0 and r["matches_expected"] == r["query_count"] for r in results)
    return {"profile": PROFILE, "query_version": QUERY_VERSION, "status": "PASS" if passed else "FAILED", "models": models, "results": results,
            "contract_sha256": sha(raw), "binding_sha256": sha(binding),
            "observed_offsets": [0], "unobserved_offsets": [1, 2], "scene_truth_certified": False}


def render(raw, binding, checked):
    contract = validate_profile(raw, binding)
    if (checked.get("status") != "PASS" or checked.get("contract_sha256") != sha(raw)
            or checked.get("binding_sha256") != sha(binding)):
        raise ValueError("Current check required")
    english = render_action_contract(contract)
    clauses = []
    clear = True
    review = False
    for ob in raw["obligations"]:
        oid = ob["obligation_id"]
        v = binding["event_predicates"][oid]
        confirmed = v["evidence_valid"] and v["truth"] in ("TRUE", "FALSE")
        label = PREDICATES[ob["predicate_id"]]
        state = ("있음" if v["truth"] == "TRUE" else "없음") if confirmed else ("근거 충돌" if v["truth"] == "CONFLICT" else "미확인")
        clear &= v["evidence_valid"] and v["truth"] == "FALSE"
        review |= not confirmed
        clauses.append({"id": oid, "text_ko": f"현재 사람 검토에 따른 {label}: {state}.",
                        "binding_path": "$.event_predicates." + oid, "core_clause_ids": ["reviewed_event", oid + "_clear"],
                        "support_query_ids": ["q1_premises", "q2_observation_contradiction"], "source_refs": ob["source_refs"]})
    clauses.append({"id": "action", "text_ko": "현재 지정 영역에 진입할 수 있으나 계속 보류해도 됩니다." if clear else "현재 지정 영역 진입을 보류해야 합니다. 이는 급제동 명령이 아닙니다.",
                    "core_clause_ids": ["entry_gate", "action_gate"], "support_query_ids": ["q2_enter", "q2_defer"]})
    clauses.append({"id": "release", "text_ko": "이후 모든 의무의 해제가 유효한 근거로 확인될 때만 진입할 수 있습니다. 해제는 진입 강제가 아니며 이후의 실제 관찰을 예측하지 않습니다.",
                    "core_clause_ids": ["entry_gate"], "support_query_ids": ["q4_clear_premises", "q4_no_clear_enter"]})
    text = "\n".join(c["text_ko"] for c in clauses)
    return {"renderer_version": RENDERER_VERSION, "renderer_signature": renderer_signature(), "language_version": "ko-v0.1", "text_ko": text,
            "text_en": english.text, "english_mapping": english.mapping_record(), "clauses": clauses,
            "contract_sha256": sha(raw), "binding_sha256": sha(binding), "text_sha256": sha(text),
            "allowed_actions": ["DEFER_ENTRY", "ENTER_ZONE"] if clear else ["DEFER_ENTRY"],
            "review_required": review, "kind": "DETERMINISTIC", "scene_truth_certified": False}
