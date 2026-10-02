"""Audit route provenance and suspend the source-conditioned ACTION task; never infer gold."""

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re

ROOT = next(p for p in Path(__file__).resolve().parents if (p / "PROJECT_REGISTRY.json").is_file())
BASE = ROOT / "artifacts/projects/guardsynth-coc/restricted/guardsynth-paper1-training-readiness-001"
PREFLIGHT = BASE / "m17-machine-preflight-2026-09-28-002"
PARENT = BASE / "conditional-candidates-2026-09-08-002"
UI = BASE / "m17-action-review-ui-2026-09-28-001"
DECISION = ROOT / "projects/04-guardsynth-coc/docs/decisions/PAPER1_ACTION_TASK_REDESIGN_DECISION_V01.md"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def key_inventory(value, path=""):
    paths = []
    if isinstance(value, dict):
        for key, child in value.items():
            current = path + "/" + key
            paths.append(current)
            paths.extend(key_inventory(child, current))
    elif isinstance(value, list):
        for child in value:
            paths.extend(key_inventory(child, path + "/*"))
    return sorted(set(paths))


def screen(row, binding, observation, annotation):
    raw = observation["raw_answer"] if observation else None
    active = binding["active_ego_actions"]
    # This is a metadata screen, never an independent visual route decision.
    turn_claims = [a for a in active if "Turn" in a["action_type"] or "ChangeLane" in a["action_type"]]
    return {
        "candidate_digest": row["candidate_digest"], "candidate_index": row["geometry_index"],
        "video_review_index": row["review_index"], "clip_id": row["clip_id"],
        "event_timestamp_us": row["event_timestamp_us"],
        "sample_id": f"development-p{observation['position']:03d}" if observation else None,
        "in_suspended_16": bool(observation and observation["scope_route"] == "CONDITIONAL_PEDESTRIAN_CANDIDATE"),
        "reported_pedestrian_relation": raw["ped_truth"] if raw else None,
        "reported_reason": raw["ped_reason"] if raw else None,
        "other_condition_reports": {k: raw[k] for k in ("road_context", "road_truth", "control_context", "control_truth")} if raw else None,
        "reported_clear_screening_candidate": bool(raw and raw["ped_truth"] == "FALSE"),
        "source_action_claims": active, "source_turn_claims": turn_claims,
        "annotation_schema_paths": key_inventory(annotation),
        "route_like_field_paths": [p for p in key_inventory(annotation) if re.search(r"route|navigation|destination|planned|intended|intent|maneuver|trajectory|path", p.split('/')[-1], re.I)],
        "intended_route_status": "NOT_ESTABLISHED_IN_AUDITED_INPUTS",
        "route_visual_validation": "NOT_PERFORMED",
        "annotation_timing_limit": "FULL_CLIP_RETROSPECTIVE_NOT_PREDECISION_ROUTE_LOG",
        "hazard_polygon_is_route": False, "normal_progress_gold": None,
        "independent_action_gold_created": False, "main_training_allowed": False,
        "screening_disposition": "CHECK_ROUTE_AND_OTHER_CONTROLS_NOT_ENTER_GOLD" if raw and raw["ped_truth"] == "FALSE" else "RETAIN_WITHOUT_ACTION_RELABEL",
    }


def execute(output):
    import pyarrow.parquet as pq
    if output.exists():
        raise FileExistsError(output)
    inputs = {}
    def pin(path, expected=None):
        actual = digest(path)
        if expected is not None and actual != expected:
            raise ValueError("input hash mismatch: " + str(path))
        inputs[str(path.relative_to(ROOT))] = actual
        return path
    def load_run(run, name):
        manifest = json.loads(pin(run / "RUN_MANIFEST.json").read_text())
        return json.loads(pin(run / name, manifest["output_hashes"][name]).read_text())
    rows = load_run(PARENT, "candidate_readiness.json")["records"]
    bindings = {r["candidate_digest"]: r for r in load_run(PARENT, "event_source_bindings.json")["records"]}
    observations = {r["candidate_digest"]: r for r in load_run(PREFLIGHT, "grounding_scope_audit.json")["records"]}
    ui = load_run(UI, "RESULT.json")
    pin(DECISION)
    pin(ROOT / "projects/04-guardsynth-coc/experiments/paper1_cnl_learning/source_gap_review.html")
    records = []
    for row in rows:
        annotation = json.loads(pin(ROOT / row["annotation_path"], row["annotation_sha256"]).read_text())
        binding = bindings[row["candidate_digest"]]
        if binding["event_timestamp_us"] != row["event_timestamp_us"] or binding["annotation_sha256"] != row["annotation_sha256"]:
            raise ValueError("binding identity mismatch")
        records.append(screen(row, binding, observations.get(row["candidate_digest"]), annotation))
    index = pin(ROOT / "data/restricted/nvidia_physicalai/clip_index.parquet")
    columns = pq.read_schema(index).names
    # Inventory only: no inference that filename absence proves upstream route absence.
    materialized = sorted(p.relative_to(ROOT).as_posix() for p in (ROOT / "data/restricted/nvidia_physicalai").rglob('*') if p.is_file() and re.search(r"route|navigation|planned|intent", p.name, re.I))
    subset = [r for r in records if r["in_suspended_16"]]
    if len(records) != 32 or len(observations) != 30 or len(subset) != 16:
        raise ValueError("candidate denominator mismatch")
    result = {
        "project_id": "guardsynth-coc", "status": "ACTION_TASK_SUSPENDED_ROUTE_CONTEXT_UNRESOLVED",
        "candidates_audited": len(records), "observations_retained": len(observations),
        "suspended_action_packets": len(subset),
        "observed_relation_counts_30": dict(Counter(r["raw_answer"]["ped_truth"] for r in observations.values())),
        "suspended_subset_relation_counts": dict(Counter(r["reported_pedestrian_relation"] for r in subset)),
        "reported_clear_candidates": [r["candidate_index"] for r in records if r["reported_clear_screening_candidate"]],
        "source_turn_claim_candidates": [r["candidate_index"] for r in records if r["source_turn_claims"]],
        "predecision_route_established_in_audited_inputs": 0,
        "normal_progress_gold_created": 0, "new_training_scenes": 0,
        "physicalai_clip_index_fields": columns, "route_like_local_filenames": materialized,
        "scope_limit": "32_LINKED_ANNOTATIONS_30_OBSERVATIONS_BINDINGS_LOCAL_INDEX_NOT_ENTIRE_UPSTREAM_DATASET_OR_VISUAL_ROUTE_AUDIT",
        "reviewer_assignment": "SUSPENDED_RECHECK_EXPOSURE_BEFORE_REPLACEMENT",
        "replacement_review_ready": False, "repeat_source_survey_requested": False,
        "formal_gate_changed": False, "main_split": "NOT_FROZEN",
        "next_human_decision": "SUPPLY_PREDECISION_ROUTE_PROVENANCE_OR_APPROVE_EXPLICIT_HYPOTHETICAL_MANEUVER_TASK",
    }
    output.mkdir(parents=True)
    def write_json(name, value):
        (output / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
    write_json("RESULT.json", result)
    write_json("route_context_audit.json", {"records": records})
    write_json("normal_progress_screening_queue.json", {"action_gold": False, "records": [r for r in records if r["reported_clear_screening_candidate"]]})
    template = Path(__file__).with_name("action_review_suspended.html")
    key = 'guardsynth-action-batch:' + ui['bundle_sha256'] + ':' + ui['reviewer_id']
    (output / "action_review_suspended.html").write_text(template.read_text().replace('__DRAFT_KEY__', json.dumps(key)))
    report = ["# 행동 검토 중단 및 경로 근거 감사", "", "기존 답변·영역·조건부 명세는 보존하고 노란 영역 ACTION 설문만 중단합니다.", "",
              f"- 감사: {len(records)}개 후보, 기존 관찰 {len(observations)}건, 중단 ACTION {len(subset)}건.",
              f"- 16건의 기존 보행자 관계: {result['suspended_subset_relation_counts']}. 모두 위험 장면이라는 앞선 단정은 철회합니다.",
              "- FALSE는 보행자 관계에 대한 기존 답변일 뿐 전체 진입 허가나 독립 행동 정답이 아닙니다.",
              "- 감사한 자료에서 판단 전 주어진 예정 경로를 입증한 후보: 0건. upstream 전체에 경로가 없다는 뜻은 아닙니다.",
              f"- 관측 주행/회전 주석이 있는 후보: {result['source_turn_claim_candidates']}. 사후 행동 주석을 예정 경로나 정답으로 사용하지 않았습니다.",
              f"- 로컬 clip_index 열: {columns}. 센서 움직임/보간 정보도 주행 의도 인증이 아닙니다.",
              "- 신규 시각 경로 검증·학습 정답 생성·학습 실행 없음. M16/M17 PARTIAL 유지.", "", "## 정상 진행 가능성 점검 후보 (정답 아님)", "",
              "| 후보 | 검토 ID | 기존 설명 | 다른 통제 (적용/상태) |", "|---|---|---|---|"]
    for r in records:
        if r["reported_clear_screening_candidate"]:
            c = r["other_condition_reports"]
            reason = r['reported_reason'].replace('|', '/').replace('\n', ' ')
            report.append(f"| #{r['candidate_index']} | {r['sample_id']} | {reason} | {c['control_context']}/{c['control_truth']} |")
    report += ["", "다른 차량 조건의 NOT_APPLICABLE도 기존 의미를 유지하며 자동 clearance로 승격하지 않습니다.", "",
               "## 다음 단계", "", "추가 전수 검토는 요청하지 않습니다. 판단 전 경로 명령/주행 계획 근거가 있다면 먼저 연결합니다.",
               "없다면 실제 운전자 의도가 아닌 명시적 가정 경로 과제로 바꿀지 승인받아야 합니다.",
               "이 선택 전에는 무표시 영상만 다시 보여주거나 정상 진행 정답을 기계 생성하지 않습니다.",
               "새 ACTION 모집 전 노출을 재확인하고 모든 ACTION 제출 전 CNL 공개를 보류합니다."]
    (output / "REPORT_KO.md").write_text('\n'.join(report) + '\n')
    write_json("RUN_MANIFEST.json", {
        "project_id": "guardsynth-coc", "experiment_id": output.parent.name, "run_id": output.name,
        "created_at_utc": datetime.now(timezone.utc).isoformat(), "status": result["status"],
        "input_hashes": inputs, "code_hashes": {str(p.relative_to(ROOT)): digest(p) for p in (Path(__file__), template)},
        "output_hashes": {p.name: digest(p) for p in sorted(output.iterdir())}, "network_used": False,
    })
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, required=True)
    print(json.dumps(execute(parser.parse_args().output_dir), ensure_ascii=False, indent=2))
