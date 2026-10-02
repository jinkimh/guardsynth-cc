"""Pin completed source observations without promoting absence to clearance or action gold."""

import argparse
from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
import re
import shutil

import prepare_development_dataset as entry

POLICY = entry.r.ROOT / "projects/04-guardsynth-coc/docs/decisions/SOURCE_GAP_OBSERVATION_ACCEPTANCE_DECISION_V01.md"
SCENE59 = "candidate-sha256:a832a5734000c2f4dcb712242c077189ec200b959d5529076f761b43fa27300d"


def validate_submission(packet, packet_sha256, response, draft):
    if set(response) != {"review_version", "packet_sha256", "reviewer_id", "records"}:
        raise ValueError("submission fields mismatch")
    for document in (response, draft):
        if document["review_version"] != entry.VERSION or document["packet_sha256"] != packet_sha256:
            raise ValueError("wrong packet/version")
    if not isinstance(response["reviewer_id"], str) or not response["reviewer_id"].strip():
        raise ValueError("reviewer required")
    scenes = {s["candidate_digest"]: s for s in packet["scenes"]}
    ids = [a["candidate_digest"] for a in response["records"]]
    if len(ids) != len(set(ids)) or set(ids) != set(scenes):
        raise ValueError("full unique packet coverage required")
    for answer in response["records"]:
        entry.validate_answer(answer, scenes[answer["candidate_digest"]])
    draft_ids = [a["candidate_digest"] for a in draft["records"]]
    if (draft.get("kind") != "DRAFT" or draft["reviewer_id"] != response["reviewer_id"]
        or len(draft_ids) != len(set(draft_ids)) or set(draft_ids) != set(ids)
        or len(draft["completed"]) != len(ids) or set(draft["completed"]) != set(ids)
        or {a["candidate_digest"]: a for a in draft["records"]}
        != {a["candidate_digest"]: a for a in response["records"]}):
        raise ValueError("draft/final answers or completions differ")


def interpret(answer, scene):
    # No text heuristic or CoC-derived truth is allowed to overwrite the reviewer.
    fields = {
        field: {"raw_choice": answer[field],
                "interpretation": "UNRESOLVED_LEGACY_NOT_APPLICABLE"
                if answer[field] == "NOT_APPLICABLE" else "REPORTED_" + answer[field],
                "formal_evidence_validated": False}
        for field in entry.CHOICES
    }
    geometry = answer["target_status"] == answer["zone_status"] == "CONFIRMED"
    route = "GROUNDING_AUDIT" if geometry and answer["ped_truth"] in {"TRUE", "FALSE"} else "APPLICABILITY_SCOPE_AUDIT"
    clarification = None
    if scene["candidate_digest"] == SCENE59:
        clarification = {
            "source": str(POLICY.relative_to(entry.r.ROOT)),
            "user_statement": "18번 / 후보 #59 - 현재 시점에서 신호가 보이지 않음",
            "interpretation": "SIGNAL_NOT_OBSERVED_AT_JUDGMENT_TIME",
            "applies_to": "SIGNAL_ONLY_NOT_ALL_CONTROLS",
            "actual_signal_applicability": "UNRESOLVED",
        }
    return {
        "candidate_digest": scene["candidate_digest"], "label": scene["label"],
        "event_timestamp_us": scene["event_timestamp_us"],
        "original_coc": scene["original_coc"], "coc_role": "CLAIM_NOT_GOLD",
        "raw_answer": deepcopy(answer), "field_interpretations": fields,
        "user_clarification": clarification, "next_machine_task": route,
        "confirmed_geometry_reported": geometry,
        "source_review_received": True, "full_source_accepted": False,
        "formal_predicates": None, "independent_action_gold": None,
        "main_training_allowed": False, "test_allowed": False,
        "repeat_source_survey_requested": False,
    }


def run(output, packet_path, response_path, draft_path):
    if output.exists():
        raise FileExistsError(output)
    inputs = {}
    entry.pin_run(packet_path.parent, inputs)
    packet, response, draft = [entry.r.load(p) for p in (packet_path, response_path, draft_path)]
    validate_submission(packet, entry.r.digest(packet_path), response, draft)
    by_id = {a["candidate_digest"]: a for a in response["records"]}
    records = [interpret(by_id[s["candidate_digest"]], s) for s in packet["scenes"]]
    for path in (response_path, draft_path, POLICY):
        inputs[str(path.resolve().relative_to(entry.r.ROOT))] = entry.r.digest(path)
    routes = dict(Counter(r["next_machine_task"] for r in records))
    result = {
        "project_id": "guardsynth-coc", "status": "SOURCE_OBSERVATION_REVIEW_COMPLETE_NOT_FORMAL_ACCEPTANCE",
        "source_reviews_received": len(records), "source_review_completion": "COMPLETE",
        "reviewer_id": response["reviewer_id"], "machine_queue_counts": routes,
        "clarified_scenes": sum(r["user_clarification"] is not None for r in records),
        "legacy_not_applicable_fields": sum(a[f] == "NOT_APPLICABLE" for a in response["records"] for f in entry.CHOICES),
        "full_source_accepted_added": 0, "training_scenes_added": 0,
        "independent_action_gold_added": 0, "optimizer_steps": 0,
        "repeat_source_survey_requested": False, "main_cohort_frozen": False,
        "milestone": "M16 PARTIAL",
    }
    output.mkdir(parents=True, exist_ok=False, mode=0o700)
    shutil.copyfile(response_path, output / "review_submission.json")
    shutil.copyfile(draft_path, output / "review_draft.json")
    entry.r.write_json(output / "observation_interpretations.json", {"records": records})
    entry.r.write_json(output / "machine_work_queue.json", {"records": [
        {k: row[k] for k in ("candidate_digest", "label", "next_machine_task", "repeat_source_survey_requested")}
        for row in records]})
    entry.r.write_json(output / "RESULT.json", result)
    (output / "REPORT_KO.md").write_text(
        "# 30장면 관찰 검토 접수 및 해석 감사\n\n"
        f"검토자 {response['reviewer_id']}: 최종 답변 {len(records)}건과 초안 완료 목록 일치. "
        "필수 항목·도형·시점·패킷 검증 통과. 업로드 원본은 바이트 그대로 보관했다.\n\n"
        "관찰 설문은 완료로 접수한다. 해당 없음은 미관찰/비적용 의미가 혼재하므로 원답을 보존하고 "
        "적용성 해석은 미확정으로 둔다. #59의 신호 미관찰 설명은 별도 출처로 기록했다. "
        "CoC가 답변의 정답이 아니며 미관찰은 진입 허가나 모든 의무 해제가 아니다.\n\n"
        f"기계 후속 분류: {routes}. 이 분류는 학습 가능 수나 정답 판정이 아니다. "
        "도형의 영상 의미·적용성·제약 범위를 먼저 확인하고, 별도 독립 행동/CNL 검토를 준비한다. "
        "새 전수 설문은 요청하지 않는다. 32개 기존 후보 중 #18 개발 1건과 #47 관찰 불가 이력은 유지한다.\n\n"
        "M16 PARTIAL 유지. 신규 source 확정·학습 데이터·독립 행동 정답·optimizer step은 모두 0. "
        "기존 #18 개발용 1장면과 본 학습 0장면은 변하지 않는다.\n", encoding="utf-8")
    code = [Path(__file__), Path(entry.__file__), entry.r.ROOT / "projects/04-guardsynth-coc/src/guard_synth/source_acceptance.py"]
    manifest = {
        "project_id": "guardsynth-coc", "experiment_id": entry.admission.audit.EXPERIMENT,
        "run_id": output.name, "status": result["status"],
        "created_at_utc": datetime.now(timezone.utc).isoformat(), "network_used": False,
        "input_hashes": inputs,
        "code_hashes": {str(p.resolve().relative_to(entry.r.ROOT)): entry.r.digest(p) for p in code},
        "output_hashes": {p.name: entry.r.digest(p) for p in output.iterdir() if p.is_file()},
    }
    entry.r.write_json(output / "RUN_MANIFEST.json", manifest)
    for path in output.iterdir():
        path.chmod(0o600)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--packet", type=Path, required=True)
    parser.add_argument("--review", type=Path, required=True)
    parser.add_argument("--draft", type=Path, required=True)
    args = parser.parse_args()
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*-[0-9]+", args.run_id):
        parser.error("numeric-suffix run ID required")
    print(run(entry.PARENT.parent / args.run_id, args.packet, args.review, args.draft))
