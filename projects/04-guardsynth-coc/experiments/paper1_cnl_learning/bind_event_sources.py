"""Pin reviewed development events to exact-time structured source witnesses."""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from align_reviews import ROOT, BASE, ACQUISITION, EXPERIMENT, digest, load, verified, write_json
from guard_synth.event_source_binding import BINDING_VERSION, bind_event
from guard_synth.review_constraint_alignment import index_records

PRIOR = BASE / EXPERIMENT / "reviewed-scene-alignment-2026-09-07-001"
STRUCTURED = ACQUISITION / "m16-cascade-structured-link-audit-2026-09-05-v1/CASCADE_STRUCTURED_LINK_AUDIT.json"


def execute(output):
    prior_manifest = load(PRIOR / "RUN_MANIFEST.json")
    for name in ("RESULT.json", "scene_constraint_alignment.json"):
        verified(PRIOR / name, prior_manifest["output_hashes"][name])
    hashes = dict(load(PRIOR / "RESULT.json")["input_hashes"])
    for path, expected in hashes.items():
        verified(ROOT / path, expected)
    for name in ("RESULT.json", "scene_constraint_alignment.json", "RUN_MANIFEST.json"):
        hashes[str((PRIOR / name).relative_to(ROOT))] = digest(PRIOR / name)
    prior = load(PRIOR / "scene_constraint_alignment.json")
    structured = index_records(load(STRUCTURED)["records"])
    source_paths = {}
    for path in (ROOT / "data/restricted/nvidia_cascade/data").glob("*/*.json"):
        clip = path.stem.split("__")[-1]
        if clip in source_paths:
            raise ValueError("ambiguous annotation clip")
        source_paths[clip] = path
    rows = []
    for row in prior["records"]:
        source = source_paths[row["group_id"]]
        previous = structured[row["candidate_digest"]]["cascade_structured_link_audit"]
        if previous["event_timestamp_us"] != row["event_timestamp_us"]:
            raise ValueError("structured event mismatch")
        sha = previous["annotation_sha256"]
        verified(source, sha)
        hashes[str(source.relative_to(ROOT))] = sha
        result = bind_event(row, load(source), sha)
        result["annotation_path"] = str(source.relative_to(ROOT))
        rows.append(result)
    if len(rows) != 19 or len(index_records(rows)) != 19 or len(prior["deferred_records"]) != 13:
        raise ValueError("reviewed development denominator changed")
    result = {
        "status": "EXACT_EVENT_SOURCE_WITNESSES_COMPLETE_OPERATIONAL_BINDING_PENDING",
        "candidate_count": 32, "reviewed_event_count": len(rows), "deferred_event_count": 13,
        "pinned_annotation_count": len({r["annotation_sha256"] for r in rows}),
        "event_with_active_causal_target_count": sum(bool(r["active_source_targets"]) for r in rows),
        "event_with_unique_source_linked_person_count": sum(r["unique_source_linked_person_id"] is not None for r in rows),
        "event_with_visible_person_source_count": sum(bool(r["visible_person_source_ids"]) for r in rows),
        "event_with_active_control_annotation_count": sum(bool(r["active_control_annotations"]) for r in rows),
        "event_with_shared_lane_source_count": sum(bool(r["shared_lane_relations"]) for r in rows),
        "event_with_exact_person_keypoint_count": sum(any(p["event_time_location_available"] for a in r["active_actors"]
            if a["person_or_cyclist"] for p in a["keypoints"]) for r in rows),
        "release_control_check_review_indices": [r["review_index"] for r in rows if r["release_control_check_required"]],
        "clause_route_counts": dict(Counter(r["clause_route"] for r in rows)),
        "window_target_set_changed_review_indices": [r["review_index"] for r in rows
            if r["previous_window_target_ids"] != sorted(t["source_ref_id"] for t in r["active_source_targets"])],
        "executable_eblc_count": 0, "sat_query_count": 0, "verified_cnl_count": 0,
        "learning_export_count": 0, "repeat_existing_survey_requested_count": 0,
        "paper_cohort_eligibility": "NOT_EVALUATED", "independent_accuracy": "NOT_EVALUATED",
        "claim_scope": "EXACT_DECLARED_ANNOTATION_INTERVALS_NOT_SCENE_TRUTH_OR_ACTION_GOLD",
        "input_hashes": hashes,
    }
    write_json(output / "event_source_bindings.json", {"records": rows, "deferred_records": prior["deferred_records"]})
    write_json(output / "RESULT.json", result)
    report = ["# 사건 시점 source 연결 결과", "",
        "기존 답변은 그대로 두고 19개 사건의 원본 CASCADE 대상·행동·신호 interval과 출처를 연결했다. "
        "32개 개발 후보와 기존 노출/split은 유지한다. 새 설문 요청이나 학습 export는 없다.", "",
        f"사건 시점의 직접 causal target이 있는 사건 {result['event_with_active_causal_target_count']}/19, "
        f"그중 단일 person source가 연결되는 사건 {result['event_with_unique_source_linked_person_count']}/19. "
        "이는 원본 주석 안의 ID 연결이며, 검토자가 확인한 대상 ID나 위험 정답을 뜻하지 않는다.", "",
        "## 사건별 근거", "",
        "| 기존 번호 | t0 (초) | t0 원본 ego 행동 | 직접 source target | 제약 분기 |",
        "|---|---:|---|---|---|"]
    for row in rows:
        actions = ", ".join(a["action_type"] for a in row["active_ego_actions"]) or "없음"
        targets = ", ".join(t["source_ref_id"] for t in row["active_source_targets"]) or "없음"
        report.append(f"| #{row['review_index']:02d} | {row['event_timestamp_us']/1e6:.6f} | {actions} | {targets} | {row['clause_route']} |")
    report += ["", "## 해석과 다음 단계", "",
        "- interval은 원본 시작/끝을 포함해 대조하며 ±0.5초 확장을 하지 않았다. 경계 일치는 별도 표시한다. "
        "이 결과는 기존 event-anchor 계약을 사용한 대조이며 데이터 간 시계 정렬의 독립 검증은 아니다.",
        "- 미래 ego 행동과 keypoint는 context-only로 보존한다. 미래 정답 입력, t0 위치 보간, "
        "point→polygon, 원본 운전 행동→규범적 action gold 변환은 하지 않았다.",
        "- #54·#56은 release와 다른 통제 의무의 동시 검토가 필요하다. 원본에 event 시점 적색 신호가 "
        "있으며 #54에는 사람의 Stop 신호도 있다. 이것만으로 적용 차로·실제 신호·기존 사람 답변 중 "
        "어느 것이 틀렸다고 단정할 수 없다. 보행자가 비켰다는 사실만으로 PROCEED를 만들지 않는다.",
        "- ego와 대상의 공통 lane source 및 정확한 t0 person keypoint가 이 run에서 모두 "
        f"{result['event_with_shared_lane_source_count']}건 / {result['event_with_exact_person_keypoint_count']}건이다. "
        "수치 정지거리 backend에 synthetic 값을 넣어 실행하지 않았다. EBLC/SAT/CNL은 미실행이다.",
        "- 다음은 M12-R01의 과제 계약: 1차 논문의 qualitative 행동 제약에 필요한 EBLC subset을 "
        "기존 metric stopping backend와 구분해 설계하고, source 전제·UNKNOWN·release/다른 의무·" 
        "행동 후보를 명시한다. 연구용 행동 제약을 차량 정지거리 보증이나 국가 법규 확정으로 주장하지 않는다.", ""]
    (output / "REPORT_KO.md").write_text("\n".join(report), encoding="utf-8")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*-[0-9]+", args.run_id):
        parser.error("run-id must be kebab-case ending in a number")
    output = BASE / EXPERIMENT / args.run_id
    output.mkdir(parents=True, exist_ok=False, mode=0o700)
    code = [Path(__file__).resolve(), Path(__file__).with_name("align_reviews.py"),
            ROOT / "projects/04-guardsynth-coc/src/guard_synth/event_source_binding.py",
            ROOT / "projects/04-guardsynth-coc/src/guard_synth/review_constraint_alignment.py"]
    manifest = {"project_id": "guardsynth-coc", "experiment_id": EXPERIMENT, "run_id": args.run_id,
        "binding_version": BINDING_VERSION, "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "RUNNING", "network_used": False,
        "code_hashes": {str(p.relative_to(ROOT)): digest(p) for p in code}}
    write_json(output / "RUN_MANIFEST.json", manifest)
    try:
        result = execute(output)
    except Exception as exc:
        result = {"status": "FAILED", "error": f"{type(exc).__name__}: {exc}"}
        write_json(output / "RESULT.json", result)
        manifest["status"] = "FAILED"
        write_json(output / "RUN_MANIFEST.json", manifest)
        raise
    manifest["status"] = result["status"]
    manifest["output_hashes"] = {p.name: digest(p) for p in output.iterdir() if p.name != "RUN_MANIFEST.json"}
    write_json(output / "RUN_MANIFEST.json", manifest)
    for path in output.iterdir():
        path.chmod(0o600)
    print(json.dumps({k: v for k, v in result.items() if k != "input_hashes"}, ensure_ascii=False, indent=2))
    print(output)


if __name__ == "__main__":
    main()
