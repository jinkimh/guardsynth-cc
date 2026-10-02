"""Link the two received development reviews without promoting them to training gold."""

import argparse
from datetime import datetime, timezone
from pathlib import Path
import re

import generate_scene_cnl as generation
from guard_synth.independent_development_review import validate_independent_review

r = generation.r
BASE = r.BASE / r.EXPERIMENT
GENERATION = BASE / "scene18-conditioned-cnl-2026-09-08-002"
UI = BASE / "scene18-cnl-save-ui-2026-09-08-001"
ACTION = BASE / "scene18-action-intake-2026-09-08-001"
CNL = BASE / "scene18-cnl-intake-2026-09-08-001"


def compare_packets(action, cnl):
    for field in ("event_timestamp_us", "zone_polygon", "frames"):
        if action[field] != cnl[field]:
            raise ValueError("review scene mismatch: " + field)
    if any(f["timestamp_us"] > cnl["event_timestamp_us"] for f in cnl["frames"]):
        raise ValueError("future review frame")


def run(output):
    sources = (generation.PARENT, GENERATION, UI, ACTION, CNL)
    inputs = {}
    for source in sources:
        manifest = r.revalidate_run(source)
        for path in [source / "RUN_MANIFEST.json"] + [source / p for p in manifest["output_hashes"]]:
            inputs[str(path.relative_to(r.ROOT))] = r.digest(path)
    action_packet = r.load(generation.PARENT / "scene18_independent_action_review_packet.json")
    cnl_packet = r.load(UI / "scene18_scene_cnl_review_packet.json")
    compare_packets(action_packet, cnl_packet)
    responses, verdicts = {}, {}
    for kind, intake, packet_run, packet_name in (
        ("ACTION", ACTION, generation.PARENT, "scene18_independent_action_review_packet.json"),
        ("SCENE_CNL", CNL, UI, "scene18_scene_cnl_review_packet.json"),
    ):
        path = packet_run / packet_name
        responses[kind] = r.load(intake / "review_submission.json")
        verdicts[kind] = validate_independent_review(
            responses[kind], r.load(path), r.digest(path),
            known_exposed_reviewer_ids=r.load(packet_run / "review_coordination.json")["known_source_exposed_reviewers"])
    raw = r.load(generation.PARENT / "action_contract.json")
    binding = r.load(GENERATION / "event_binding.json")
    # Reproduce text from source/contract, never from independent action labels.
    document, _, checks = generation.generate_scene_cnl(raw, binding)
    if document != r.load(GENERATION / "scene_cnl.json"):
        raise ValueError("generated document replay mismatch")
    r.verified(GENERATION / "scene_cnl.json", cnl_packet["document_sha256"])
    if [i["text"] for i in cnl_packet["items"]] != [c["text_ko"] for c in document["clauses"]]:
        raise ValueError("reviewed text differs from document")
    action = responses["ACTION"]["answers"]["action"]
    allowed = next(c for c in document["clauses"] if c["id"] == "action.now")["semantics"]["allowed_actions"]
    time_of = lambda kind: datetime.fromisoformat(responses[kind]["reviewed_at"].replace("Z", "+00:00"))
    result = {
        "project_id": "guardsynth-coc", "status": "DEVELOPMENT_REVIEWS_LINKED_ENGLISH_REVIEW_PENDING",
        "review_verdicts": verdicts, "same_scene_frames_zone": True,
        "declared_action_before_cnl": time_of("ACTION") < time_of("SCENE_CNL"),
        "order_assurance": "CLIENT_TIMESTAMPS_NOT_PROOF_OF_BLINDING_OR_IDENTITY",
        "independent_action_label": action, "action_matches_conditioned_instruction": action in allowed,
        "korean_all_supported": all(v == "SUPPORTED" for v in responses["SCENE_CNL"]["answers"].values()),
        "generated_text_replay_matches": True, "query_count": checks["query_count"],
        "matches_expected": checks["matches_expected"], "event_predicates": binding["event_predicates"],
        "english_fidelity_review_complete": False, "full_source_verified_contracts": 0,
        "learning_export_allowed": False, "training_exports": 0, "main_test_eligibility": False,
        "blocked_by": ["INDEPENDENT_ENGLISH_TEXT_REVIEW", "FULL_SOURCE_ACCEPTANCE", "MAIN_COHORT_GOLD_SPLIT_FREEZE"],
        "claim_scope": "SINGLE_DEVELOPMENT_REVIEW_LINKAGE_NOT_ACCURACY_OR_LEARNING_EFFECT",
    }
    report = ["# #18 개발 검토 연결 결과", "",
        "한글 CNL 답변을 정식 수용하고 기존 ACTION과 동일 시점·영역·과거 프레임인지 확인했다.",
        "원본 근거와 명세만으로 문장을 재생성하여 저장된 문장과 일치를 확인했다. ACTION 답변은 생성 입력이 아니다.",
        "행동 답변 DEFER_ENTRY는 조건부 명세의 현재 지시와 부합한다. 한글 네 문장은 모두 SUPPORTED다.",
        "제출 시각상 ACTION이 CNL보다 먼저다. 이는 검토 전 미노출이나 신원·전문성의 인증이 아니다.",
        "주도로 UNKNOWN, 전체 source 수용 0, 학습 export 0, main-test 부적격을 유지한다.", "",
        "## 다음 사람 검토: 실제 학습에 넣을 영문", "",
        "아래 한글은 이미 검토했다. 장면이나 한글 판단을 반복하지 않고, 영문이 같은 뜻을 전달하는지만 확인한다.",
        "각 항목에 ‘의미 일치 / 의미 불일치 / 판단 불가’와 이유를 적는다. 이름·참여 여부·검토 시각도 함께 기록한다.",
        "확인할 점: 근거에 대한 귀속, 미확인을 부재로 바꾸지 않음, 현재 보류 의무, 두 조건의 동시 확인 및 진입 비강제.",
        "작성자·생성기 참여자의 검토는 독립 검토와 구분한다. 이 자료의 준비는 영문 검토 완료가 아니다.", ""]
    for i, clause in enumerate(document["clauses"], 1):
        report.extend([f"### {i}. {clause['id']}", "", "한글: " + clause["text_ko"], "",
                       "영문: " + clause["text_en"], "", "판정: [미입력] · 이유: [미입력]", ""])
    output.mkdir(parents=True, exist_ok=False, mode=0o700)
    r.write_json(output / "RESULT.json", result)
    (output / "REPORT_KO.md").write_text("\n".join(report), encoding="utf-8")
    r.write_json(output / "RUN_MANIFEST.json", {
        "project_id": "guardsynth-coc", "experiment_id": r.EXPERIMENT, "run_id": output.name,
        "created_at_utc": datetime.now(timezone.utc).isoformat(), "status": result["status"],
        "network_used": False, "input_hashes": inputs,
        "code_hashes": {str(p.relative_to(r.ROOT)): r.digest(p) for p in (
            Path(__file__).resolve(), Path(generation.__file__).resolve(), Path(r.__file__).resolve(),
            r.ROOT / "projects/04-guardsynth-coc/src/guard_synth/scene_conditioned_cnl.py",
            r.ROOT / "projects/04-guardsynth-coc/src/guard_synth/independent_development_review.py")},
        "output_hashes": {p.name: r.digest(p) for p in output.iterdir()},
    })
    for path in output.iterdir():
        path.chmod(0o600)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*-[0-9]+", args.run_id):
        parser.error("unused numeric run ID required")
    output = BASE / args.run_id
    print(run(output)["status"])
    print(output)
