"""Pinned scene-18 Korean review presentation; never rewrite execution or human inputs."""

import argparse
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
import re

import execute_reviewed_contract as runner

ROOT, BASE = runner.ROOT, runner.BASE
PARENT = BASE / runner.EXPERIMENT / "reviewed-scene18-execution-2026-09-08-001"
PACKET_NAME = "scene18_independent_cnl_review_packet.json"
PARENT_SHA = "cedf8157306ceb17ded427228e376b405d3a672f610db49a202f2e93385387f7"
BASIS = "KOREAN_ASSISTED_CNL_REVIEW_NOT_ENGLISH_ONLY_FIDELITY"


def korean_view(packet):
    # This is a maintained translation of one pinned review, not a general Korean renderer.
    refs = packet["contract"]["source_refs"]
    names = ["[근거 1: 진입 판단 정책]", "[근거 2: 사용자 추가 확인을 반영한 개발 검토]",
             "[근거 3: 장면 근거 검토 자료]", "[근거 4: 장면 18의 CASCADE 주석]"]
    aliases = dict(zip(refs, names, strict=True))
    lifecycle = (
        "조건의 값은 참, 거짓, 알 수 없음, 근거 충돌 중 하나입니다. "
        "근거가 유효하고 조건이 참인 경우, 그리고 그 경우에만 활성화가 확인됩니다. "
        "근거가 유효하고 조건이 거짓인 경우, 그리고 그 경우에만 해제가 확인됩니다. "
        "각 판단 시점에서 활성화가 확인되면 의무를 활성화하고, 해제가 확인되면 비활성화하며, "
        "둘 다 확인되지 않으면 이전 활성 상태를 유지합니다. 해제 이후에도 같은 규칙을 적용합니다. "
        "첫 판단 직전의 활성 상태는 별도 입력으로 주어집니다. 의무가 활성 상태이면 영역 진입을 금지합니다."
    )
    translations = {
        "action.identity": "조건부 명세 ‘장면 18 검토 근거 연결 계약’(EBLC 행동 계약 v0.1)은 에고 차량과 검토에서 지정한 진입 영역을 대상으로, 추상적인 판단 시점 3개를 다룹니다. 범위는 조건부 행동 선택이며 차량 안전성 보증이 아닙니다. 정책은 모든 의무의 해제가 확인되어야 진입을 허용한다는 것입니다. 이 자연어 문장은 실행의 기준 명세가 아니며, 근거의 사실성이나 차량 안전성을 인증하지 않습니다.",
        "action.sources": "이 명세에 선언된 출처는 " + ", ".join(names) + "입니다.",
        "ped": "보행자 관련 의무는 ‘보행자와의 충돌 조건’을 사용하며 대상은 보행자 Agent3, 규칙 출처는 [근거 1: 진입 판단 정책]입니다. " + lifecycle,
        "road": "주도로 관련 의무는 ‘주도로 교통에 대한 양보 필요 조건’을 사용합니다. 구체적인 대상은 아직 연결되지 않았으며, 규칙 출처는 [근거 1: 진입 판단 정책]입니다. " + lifecycle,
        "action.composition": "해당 판단 시점에서 선언된 모든 의무의 해제가 확인된 경우, 그리고 그 경우에만 진입을 허용합니다. 적어도 하나의 의무에서 근거가 유효하지 않거나 조건이 ‘알 수 없음’ 또는 ‘근거 충돌’인 경우, 그리고 그 경우에만 추가 검토가 필요합니다. 추가 검토가 필요하면 진입을 허용하지 않습니다. 선택할 수 있는 행동은 ‘진입 보류’와 ‘영역 진입’입니다. 진입 허가가 없으면 진입 보류를 선택합니다. 진입 허가가 있어도 두 행동 중 어느 것이든 선택할 수 있으며, 진입을 강제하지 않습니다. 진입 보류는 이번 진입 결정을 미루는 것이지 급제동 지시나 물리적 안전 보증이 아닙니다. 한 의무를 해제해도 다른 의무는 해제되지 않습니다. 근거의 유효성과 대상·영역 연결은 별도의 출처 확인이 필요합니다."
    }
    titles = dict(zip(packet["clause_ids"], ["1. 대상·영역·명세 범위", "2. 출처 목록", "3. 보행자 관련 의무", "4. 주도로 관련 의무", "5. 여러 의무의 결합과 최종 행동"], strict=True))
    summary = {
        "명세": "장면 18 검토 근거 연결 계약 / EBLC 행동 계약 v0.1",
        "주체": "에고 차량", "영역": "검토에서 지정한 진입 영역", "판단 범위": "추상 판단 시점 3개 (영상 3프레임이라는 뜻 아님)",
        "정책": "모든 의무의 해제가 확인되어야 진입 허용", "주장 범위": "조건부 행동 선택, 차량 안전성 보증 아님",
        "보행자 의무": {"조건": "보행자와의 충돌 조건", "대상": "보행자 Agent3", "규칙": names[0], "근거": names},
        "주도로 의무": {"조건": "주도로 교통에 대한 양보 필요 조건", "대상": "미연결 (없다는 뜻 아님)", "규칙": names[0], "근거": names},
        "출처": names,
    }
    def variable(name):
        for prefix, label in (("ped_", "보행자 / "), ("road_", "주도로 / ")):
            if name.startswith(prefix):
                return label + {"on":"활성화 확인", "clear":"해제 확인", "active":"의무 활성", "prior_active":"첫 판단 직전 의무 활성", "truth":"조건 값", "evidence_valid":"근거 유효"}[name[len(prefix):]]
        return {"action":"선택 행동", "entry_permitted":"진입 허가", "review_required":"추가 검토 필요"}[name]
    def formula(f):
        op = f["op"]
        if op == "var": return variable(f["name"]) + ("[다음 시점]" if f["offset"] == 1 else "[현재 시점]")
        if op == "literal":
            if isinstance(f["value"], bool): return "참" if f["value"] else "거짓"
            return {"TRUE":"참", "FALSE":"거짓", "UNKNOWN":"알 수 없음", "CONFLICT":"근거 충돌", "ENTER_ZONE":"영역 진입", "DEFER_ENTRY":"진입 보류"}[f["value"]]
        if op in {"and", "or"}: return "(" + (" 그리고 " if op == "and" else " 또는 ").join(formula(a) for a in f["args"]) + ")"
        if op == "not": return "아님(" + formula(f["arg"]) + ")"
        if op == "ite": return "만약 " + formula(f["condition"]) + "이면 " + formula(f["then"]) + ", 아니면 " + formula(f["else"])
        symbol = {"eq":" = ", "ne":" ≠ ", "implies":" ⇒ "}[op]
        return "(" + formula(f["left"]) + symbol + formula(f["right"]) + ")"
    rules = [{"적용 시점": {"INITIAL":"첫 판단", "EACH_FRAME":"매 판단", "EACH_TRANSITION":"각 다음 판단으로 전환할 때"}[c["enforcement"]],
              "원본 조항 ID":c["id"], "논리식":formula(c["formula"])} for c in packet["core_semantics"]["clauses"]]
    clauses = {c["clause_id"]:c for c in packet["cnl_mapping"]["clauses"]}
    cores = {c["id"]:c for c in packet["core_semantics"]["clauses"]}
    pairs = {}
    for oid, title, condition, target in (
        ("ped", "1. 보행자 때문에 진입을 금지하는 조건", "보행자 관련 위험", "대상: 보행자 Agent3"),
        ("road", "2. 주도로 교통 때문에 진입을 금지하는 조건", "주도로 교통에 양보할 필요", "대상 차량: 아직 연결되지 않음 (차량이 없다는 뜻 아님)"),
    ):
        core_ids = [oid+suffix for suffix in ("_on", "_clear", "_initial", "_transition", "_no_entry")]
        # Exact renderer output suffix, not a newly invented English example.
        full = clauses[oid]["text"]
        excerpt = full[full.index("Its truth is "):]
        pairs[oid] = {"title":title, "target":target, "core_clause_ids":core_ids,
            "source_explanation":[
                f"{condition}이 있다는 유효한 근거 → 해당 진입 금지 적용.",
                f"{condition}이 없다는 유효한 근거 → 이 조건 때문에 적용한 진입 금지 해제.",
                "어느 쪽도 확인 못함 → 이전 적용 상태 유지. 해제한 뒤 다시 조건이 확인되면 재적용.",
                "첫 판단 직전의 적용 상태는 따로 입력. 해당 금지가 적용 중이면 진입 불가."],
            "generated_excerpt":excerpt, "excerpt_start":full.index(excerpt),
            "translation_lines":[
                f"{condition}은 ‘있음’, ‘없음’, ‘알 수 없음’, ‘근거끼리 충돌함’ 중 하나로 표현합니다.",
                f"유효한 근거로 {condition}이 있다고 확인했을 때, 그리고 그때만 ‘금지를 시작할 조건이 확인됨’으로 처리합니다.",
                f"유효한 근거로 {condition}이 없다고 확인했을 때, 그리고 그때만 ‘금지를 해제할 조건이 확인됨’으로 처리합니다.",
                "각 판단에서 시작 조건을 확인하면 해당 진입 금지를 적용하고, 해제 조건을 확인하면 해제합니다. 둘 다 확인하지 못하면 이전 적용 상태를 그대로 유지합니다.",
                "한 번 해제한 뒤에도 같은 규칙을 사용합니다. 첫 판단 직전의 적용 상태는 따로 입력받습니다.",
                "해당 진입 금지가 적용되는 동안에는 지정된 영역으로 들어가면 안 됩니다."],
            "question":"B가 A의 금지 시작·해제·유지·재적용 조건을 빠뜨리거나 바꾸지 않았나요?"}
    cid="action.composition"
    pairs[cid] = {"title":"3. 두 조건을 합쳐 진입 여부를 결정하는 규칙", "target":"적용 대상: 에고 차량의 지정 영역 진입",
        "core_clause_ids":["entry_gate", "review_gate", "action_gate"],
        "source_explanation":[
            "보행자 조건과 주도로 양보 조건이 모두 유효한 근거로 해제 확인됨 ↔ 진입 허가.",
            "하나라도 근거가 유효하지 않거나 조건을 모르거나 근거끼리 충돌함 ↔ 추가 검토 필요. 이때 진입 불가.",
            "진입 허가 없음 → 보류만 가능. 진입 허가 있음 → 진입 또는 보류 모두 가능."],
        "generated_excerpt":clauses[cid]["text"], "excerpt_start":0,
        "translation_lines":[
            "두 조건 모두에서 금지를 해제할 수 있다고 확인된 경우에만, 그리고 그런 경우에는 진입을 허용합니다.",
            "하나라도 근거가 유효하지 않거나, 조건을 알 수 없거나, 근거끼리 충돌하면 추가 검토가 필요합니다. 추가 검토 필요 여부는 이 조건으로 정합니다.",
            "추가 검토가 필요할 때에는 진입할 수 없습니다.",
            "행동은 ‘진입 보류’와 ‘영역 진입’ 중에서 선택합니다. 진입 허가가 없으면 보류해야 합니다.",
            "진입 허가가 있어도 반드시 들어가야 하는 것은 아닙니다. 계속 보류해도 됩니다.",
            "진입 보류는 이번 진입 결정을 미룬다는 뜻이지, 급제동 지시나 실제 안전 보증이 아닙니다.",
            "보행자 조건의 금지를 해제해도 주도로 조건까지 해제되는 것은 아닙니다. 근거가 유효한지, 대상·영역이 맞게 연결됐는지는 별도로 확인해야 합니다."],
        "question":"B가 A의 ‘두 조건 모두 확인’, ‘모르면 진입 불가’, ‘허가가 있어도 진입 강제 아님’을 그대로 전달하나요?"}
    for cid,pair in pairs.items():
        pair["source_core"]=[deepcopy(cores[name]) for name in pair["core_clause_ids"]]
        pair["source_core_ko"]=[item for item in rules if item["원본 조항 ID"] in pair["core_clause_ids"]]
        pair["generated_clause_id"]=cid
        pair["generated_file"]="cnl_mapping.json"
        pair["source_file"]="core_model.json"
    return {"presentation_version":"scene18-cnl-ko-v0.2", "review_basis":BASIS,
        "reference_aliases":aliases, "contract_ko":summary, "core_ko":rules,
        "clauses":{cid:{"title":titles[cid], "translation":translations[cid]} for cid in packet["clause_ids"]},
        "pairs":pairs, "review_clause_ids":list(pairs),
        "excluded_review_clause_ids":["action.identity", "action.sources"],
        "notice":"비교할 것은 각 카드의 A(명세 규칙의 해설)와 B(실제 생성 문장의 한글 번역)입니다. 소개·버전·출처 목록에는 답하지 않습니다. 한글 해설과 번역도 오류가 있을 수 있어 원본 조항을 함께 연결했습니다. 이 답변만으로 원본 명세의 엄밀한 의미보존을 입증하지는 않습니다."}


def run(output):
    runner.revalidate_run(PARENT)
    runner.verified(PARENT/PACKET_NAME, PARENT_SHA)
    packet = deepcopy(runner.load(PARENT/PACKET_NAME))
    packet["korean_review"] = korean_view(packet)
    output.mkdir(parents=True, exist_ok=False, mode=0o700)
    runner.write_review(output, "scene18_independent_cnl_review", packet, {})
    runner.write_json(output/"review_coordination.json", runner.load(PARENT/"review_coordination.json"))
    result = {"project_id":"guardsynth-coc", "status":"KOREAN_CNL_REVIEW_READY", "review_basis":BASIS,
        "parent_packet_sha256":PARENT_SHA, "cnl_reviews":0, "learning_export_allowed":False,
        "claim_scope":"REVIEW_PRESENTATION_ONLY_NOT_NEW_EXECUTION_OR_INDEPENDENT_FIDELITY_RESULT"}
    runner.write_json(output/"RESULT.json", result)
    design = ROOT/"projects/04-guardsynth-coc/docs/designs/PAPER1_PAIRED_CNL_REVIEW_DESIGN_V01.md"
    inputs = [PARENT/PACKET_NAME, PARENT/"RUN_MANIFEST.json", PARENT/"review_coordination.json", design]
    code = [Path(__file__).resolve(), runner.TEMPLATE, Path(runner.__file__).resolve()]
    manifest = {"project_id":"guardsynth-coc", "experiment_id":runner.EXPERIMENT, "run_id":output.name,
        "created_at_utc":datetime.now(timezone.utc).isoformat(), "status":result["status"],
        "input_hashes":{str(p.relative_to(ROOT)):runner.digest(p) for p in inputs},
        "code_hashes":{str(p.relative_to(ROOT)):runner.digest(p) for p in code},
        "output_hashes":{p.name:runner.digest(p) for p in output.iterdir()}}
    runner.write_json(output/"RUN_MANIFEST.json", manifest)
    for p in output.iterdir(): p.chmod(0o600)
    return result


if __name__ == "__main__":
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument("--run-id", required=True); args=parser.parse_args()
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*-[0-9]+", args.run_id): parser.error("unused numeric run ID required")
    output=BASE/runner.EXPERIMENT/args.run_id
    print(run(output)["status"]); print(output)
