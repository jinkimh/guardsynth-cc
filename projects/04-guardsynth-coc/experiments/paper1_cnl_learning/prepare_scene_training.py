"""Real-scene processor preflight, not a training export or four-arm experiment."""

import argparse
from datetime import datetime, timezone
from pathlib import Path
import re

import run as learning
import link_scene_reviews as linked
from guard_synth.cnl_training import ConstraintSupervision, build_example, digest_text

r = linked.r
LINKAGE = linked.BASE / "scene18-review-linkage-2026-09-08-001"


def english_feedback(reviewer, statement, document):
    prior = r.load(linked.CNL / "review_submission.json")
    normalize = lambda s: " ".join(s.casefold().split())
    if normalize(reviewer) != normalize(prior["reviewer_id"]):
        raise ValueError("cannot reuse another reviewer's involvement declaration")
    if not statement.strip():
        raise ValueError("actual user statement required")
    verdict = r.load(linked.CNL / "RESULT.json")
    return {
        "kind": "CONVERSATION_ATTRIBUTED_ENGLISH_MEANING_FEEDBACK",
        "reviewer_id": reviewer, "user_statement": statement,
        "attribution_source": "USER_IDENTIFIED_REVIEWER_IN_CONVERSATION",
        "scope": "OVERALL_MEANING_OF_FOUR_DISPLAYED_ENGLISH_SENTENCES",
        "clause_ids": [c["id"] for c in document["clauses"]],
        "document_sha256": r.digest(linked.GENERATION / "scene_cnl.json"),
        "reviewed_at": None, "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
        "independence_declaration": prior["independence"],
        "independence_basis": "REUSED_PRIOR_SCENE_CNL_DECLARATION_NOT_NEW_ATTESTATION",
        "declaration_source_sha256": r.digest(linked.CNL / "review_submission.json"),
        "independence_eligible_on_existing_record": verdict["independence_eligible"],
        "authenticated_identity_or_expertise": False,
        "formal_per_clause_response": False, "general_renderer_fidelity_proved": False,
    }


def prepare(reviewer, statement):
    inputs = {}
    for source in (LINKAGE, linked.GENERATION, linked.ACTION, linked.CNL):
        manifest = r.revalidate_run(source)
        for p in [source / "RUN_MANIFEST.json"] + [source / n for n in manifest["output_hashes"]]:
            inputs[str(p.relative_to(r.ROOT))] = r.digest(p)
    scene, packet, _, source_inputs = r.reviewed_inputs()
    inputs.update(source_inputs)
    document = r.load(linked.GENERATION / "scene_cnl.json")
    binding = r.load(linked.GENERATION / "event_binding.json")
    raw = r.load(linked.generation.PARENT / "action_contract.json")
    replay, _, checks = linked.generation.generate_scene_cnl(raw, binding)
    if replay != document:
        raise ValueError("source/contract text replay differs")
    feedback = english_feedback(reviewer, statement, document)
    action = r.load(linked.ACTION / "review_submission.json")["answers"]["action"]
    if not r.load(linked.ACTION / "RESULT.json")["judgement_available"]:
        raise ValueError("independent development action unavailable")
    frame = packet["frames"][-1]
    if not frame["is_t0"] or frame["timestamp_us"] > binding["event_timestamp_us"]:
        raise ValueError("invalid event input frame")
    image = r.PREPARATION / frame["file"]
    r.verified(image, frame["sha256"])
    inputs[str(image.relative_to(r.ROOT))] = frame["sha256"]
    constraint = ConstraintSupervision("L3", document["text_en"], {
        "text_sha256": digest_text(document["text_en"]),
        "document_sha256": r.digest(linked.GENERATION / "scene_cnl.json"),
        "semantic_verification": "PARTIAL_SOURCE_CONDITIONED_BOUNDED_QUERIES",
        "source_complete": False, "provider_status": "DEVELOPMENT_PREVIEW_NOT_MAIN_L3_PROVIDER",
    })
    zone = str(binding["zone_polygon"])
    examples = [build_example(
        scene_id=scene["candidate_digest"], group_id=scene["clip_id"], split="dev",
        image=image, image_sha256=frame["sha256"], coc=scene["coc"],
        coc_source_ref="sha256:" + digest_text(scene["coc"]) + "#pinned-original-coc",
        choices={"ENTER_ZONE": "Enter the designated zone (normalized image polygon " + zone + ") now",
                 "DEFER_ENTRY": "Defer entry into that zone now"},
        action=action, action_source_ref="sha256:" + r.digest(linked.ACTION / "review_submission.json") + "#development-action",
        arm=arm, constraint=constraint if arm == "L3" else None,
    ) for arm in ("L0", "L3")]
    for example in examples:
        example.update(preview_only=True, learning_export_allowed=False, main_test_eligibility=False)
    if examples[0]["input"] != examples[1]["input"] or examples[0]["common_example_sha256"] != examples[1]["common_example_sha256"]:
        raise ValueError("preview base inputs/labels differ")
    return feedback, examples, inputs, {
        "event_timestamp_us": binding["event_timestamp_us"], "input_frame_timestamp_us": frame["timestamp_us"],
        "input_frame_offset_us": frame["timestamp_us"] - binding["event_timestamp_us"],
        "review_frame_count": len(packet["frames"]), "processor_frame_count": 1,
        "frame_sampling_scope": "LAST_CAUSAL_FRAME_PREFLIGHT_NOT_FROZEN_MAIN_SAMPLING",
        "event_predicates": binding["event_predicates"], "matches_expected": checks["matches_expected"],
    }


def run(output, reviewer, statement):
    if output.exists():
        raise FileExistsError(output)
    feedback, examples, inputs, details = prepare(reviewer, statement)
    from transformers import AutoProcessor
    processor = AutoProcessor.from_pretrained(learning.MODEL_PATH, local_files_only=True)
    metrics = []
    for example in examples:
        full, prompt = learning.encode(processor, example)
        n = prompt["input_ids"].shape[1]
        if not (full["labels"][:, :n] == -100).all() or not full["labels"][:, n:].equal(full["input_ids"][:, n:]):
            raise ValueError("assistant-only label mask mismatch")
        metrics.append({"preview_arm": example["arm"], "prompt_tokens": n,
            "sequence_tokens": full["input_ids"].shape[1], "supervised_tokens": int((full["labels"] != -100).sum()),
            "pixel_values_shape": list(full["pixel_values"].shape), "image_grid_thw": full["image_grid_thw"].tolist()})
    for path in learning.MODEL_PATH.iterdir():
        if path.suffix == ".json" or path.name in {"merges.txt", "vocab.json"}:
            inputs[str(path)] = r.digest(path)
    result = {"project_id": "guardsynth-coc", "status": "REAL_SCENE_PROCESSOR_PREFLIGHT_COMPLETE_MAIN_DATA_BLOCKED",
        **details, "processor_revision": learning.REVISION, "processor_metrics": metrics,
        "english_feedback_recorded": True, "formal_english_questionnaire_received": False,
        "matched_preview_pair": True, "four_arm_comparison_complete": False,
        "missing_real_providers": ["L1", "L2"], "learning_export_allowed": False,
        "training_exports": 0, "optimizer_steps": 0, "model_weights_loaded": False,
        "full_source_verified_contracts": 0, "main_test_eligibility": False,
        "blocked_by": ["FULL_SOURCE_ACCEPTANCE", "MAIN_COHORT_GOLD_SPLIT_FREEZE", "REAL_FOUR_ARM_PROVIDERS_AND_BUDGET"],
        "claim_scope": "REAL_IMAGE_TEXT_ENCODING_AND_MASK_ONLY_NOT_LEARNING_OR_EFFECT"}
    output.mkdir(parents=True, exist_ok=False, mode=0o700)
    for name, value in (("english_feedback.json", feedback), ("development_previews.json", examples), ("RESULT.json", result)):
        r.write_json(output / name, value)
    (output / "REPORT_KO.md").write_text(
        "# #18 실제 학습 입력 준비 검사\n\n"
        "Jun Choi의 영문 의미 일치 의견을 대화 기반으로 기록했다. 기존 참여 여부 신고를 재사용했으며 새 서명·문장별 설문이나 신원 인증을 만들지 않았다.\n\n"
        "실제 원본 프레임·CoC·독립 개발 행동 답변으로 L0/L3 형식의 미리보기 두 건을 구성하고 로컬 VLM processor로 인코딩했다. CNL은 assistant target에만 추가하며 공통 입력·행동 답변은 동일하다. 프롬프트 loss 제외, assistant 토큰 학습 대상, 이미지 tensor 및 무절단을 검사했다.\n\n"
        "마지막 과거 프레임 한 장의 전처리 점검이지 21프레임 검토 조건과 같은 평가가 아니다. 원본 CoC의 주도로 양보 지시는 보존하지만 독립 근거의 road UNKNOWN을 덮어쓰지 않는다. 이 차이의 학습 target 정책은 main 동결 전 해결해야 한다.\n\n"
        "L1/L2 실제 provider와 L3 source 수용은 미완료다. 미리보기를 네 조건 공정 비교·학습 export로 세지 않는다. 가중치 로딩/갱신 0, source-verified 0, export 0. 다음 작업은 과제별 source 수용·원본 CoC/UNKNOWN 처리 및 main 후보/split/정답 기준 동결이다.\n", encoding="utf-8")
    code = [Path(__file__).resolve(), Path(learning.__file__).resolve(), Path(linked.__file__).resolve(),
            r.ROOT / "projects/04-guardsynth-coc/src/guard_synth/cnl_training.py"]
    r.write_json(output / "RUN_MANIFEST.json", {"project_id": "guardsynth-coc", "experiment_id": r.EXPERIMENT,
        "run_id": output.name, "status": result["status"], "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "network_used": False, "input_hashes": inputs,
        "code_hashes": {str(p.relative_to(r.ROOT)): r.digest(p) for p in code},
        "output_hashes": {p.name: r.digest(p) for p in output.iterdir()}})
    for path in output.iterdir():
        path.chmod(0o600)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--reviewer", required=True)
    parser.add_argument("--statement", required=True)
    args = parser.parse_args()
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*-[0-9]+", args.run_id):
        parser.error("unused numeric run ID required")
    output = linked.BASE / args.run_id
    print(run(output, args.reviewer, args.statement)["status"])
    print(output)
