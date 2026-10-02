"""Finish 13 source-only bindings and apply the explicit conditional-admission policy."""

import argparse
from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
from html import escape
from pathlib import Path
import re

import audit_training_candidates as audit
import generate_scene_cnl as generation
from guard_synth.event_source_binding import bind_event
from guard_synth.review_constraint_alignment import _CONTEXT
from guard_synth.conditional_admission import assess_conditional_candidate

r = audit.reviewed
PRIOR = audit.BASE / audit.EXPERIMENT / "candidate-readiness-2026-09-08-003"
POLICY = r.ROOT / "projects/04-guardsynth-coc/docs/decisions/PAPER1_CONDITIONAL_DATA_ADMISSION_DECISION_V01.md"


def source_only_row(row, structured):
    text = row["original_coc"]
    contexts = [{"context": name, "matched_text": match.group(), "span": list(match.span()),
                 "epistemic_kind": "CLAIMED", "evidence_ref": "sha256:" + row["coc_sha256"]}
                for name, pattern in _CONTEXT.items() for match in re.finditer(pattern, text, re.I)]
    return {"candidate_digest": row["candidate_digest"], "group_id": row["clip_id"],
        "review_index": None, "event_timestamp_us": row["event_timestamp_us"], "upstream_split": row["upstream_split"],
        "coc": {"text": text, "sha256": row["coc_sha256"], "epistemic_kind": "CLAIMED", "context_matches": contexts,
                "mixed_work_or_control_context": any(x["context"] in {"WORKER_OR_FLAGGER", "TRAFFIC_CONTROL", "WORK_ZONE_OR_CONES"} for x in contexts)},
        "observation": {"visual_temporal_observation": None, "visual_association_observation": None,
                        "notes": None, "image_sha256": None},
        "evidence_refs": {"coc": "sha256:" + row["coc_sha256"], "observation": None,
                          "annotation": "sha256:" + row["annotation_sha256"]},
        "structured_target_candidates": structured["cascade_structured_link_audit"]["active_source_targets"]}


def execute():
    inputs = {}
    for directory in (PRIOR, audit.source.BINDING, audit.source.ALIGNMENT, audit.PREFLIGHT,
                      audit.LINKAGE, generation.PARENT, generation.PARENT.parent / "scene18-conditioned-cnl-2026-09-08-002"):
        manifest = r.revalidate_run(directory)
        inputs.update(manifest.get("input_hashes", {}))
        for path in [directory / "RUN_MANIFEST.json"] + [directory / n for n in manifest["output_hashes"]]:
            inputs[str(path.relative_to(r.ROOT))] = r.digest(path)
    inputs[str(POLICY.relative_to(r.ROOT))] = r.digest(POLICY)
    prior_rows = r.load(PRIOR / "candidate_readiness.json")["records"]
    if len(audit.index_unique(prior_rows)) != 32:
        raise ValueError("denominator drift")
    old_bindings = audit.index_unique(r.load(audit.source.BINDING / "event_source_bindings.json")["records"])
    old_alignment = audit.index_unique(r.load(audit.source.ALIGNMENT / "scene_constraint_alignment.json")["records"])
    structured = audit.index_unique(r.load(audit.alignment.ACQUISITION / "m16-cascade-structured-link-audit-2026-09-05-v1/CASCADE_STRUCTURED_LINK_AUDIT.json")["records"])
    scene, packet, source_review, source_inputs = r.reviewed_inputs()
    inputs.update(source_inputs)
    document, _, checks = generation.generate_scene_cnl(r.load(generation.PARENT / "action_contract.json"), r.load(generation.PARENT / "event_binding.json"))
    current = generation.PARENT.parent / "scene18-conditioned-cnl-2026-09-08-002"
    if document != r.load(current / "scene_cnl.json"):
        raise ValueError("scene18 document replay mismatch")
    english = r.load(audit.PREFLIGHT / "english_feedback.json")
    english_recorded = (english["document_sha256"] == r.digest(current / "scene_cnl.json")
                        and english["independence_eligible_on_existing_record"] is True
                        and english["scope"] == "OVERALL_MEANING_OF_FOUR_DISPLAYED_ENGLISH_SENTENCES")
    allowed = next(c["semantics"]["allowed_actions"] for c in document["clauses"] if c["id"] == "action.now")
    bindings, rows = [], []
    for prior in prior_rows:
        row = deepcopy(prior)
        key = row["candidate_digest"]
        path = r.ROOT / row["annotation_path"]
        r.verified(path, row["annotation_sha256"])
        inputs[row["annotation_path"]] = row["annotation_sha256"]
        existing = key in old_bindings
        input_row = old_alignment[key] if existing else source_only_row(row, structured[key])
        bound = bind_event(input_row, r.load(path), row["annotation_sha256"])
        bound["annotation_path"] = row["annotation_path"]
        if existing and bound != old_bindings[key]:
            raise ValueError("existing source binding replay changed")
        if not existing:
            bound["observation_status"] = "NOT_COLLECTED_NO_HUMAN_VALUE_INFERRED"
        bindings.append(bound)
        row.update(exact_event_source_audit=True, source_linked_person_ids=bound["source_linked_person_ids"],
                   active_control_count=len(bound["active_control_annotations"]), clause_route=bound["clause_route"])
        row["missing_codes"] = [c for c in row["missing_codes"] if c != "EXACT_EVENT_BINDING_PENDING"]
        if bound["clause_route"] == "MIXED_CONTROL_OR_WORK_CONTEXT" and "CONTROL_SCOPE_REVIEW" not in row["missing_codes"]:
            row["missing_codes"].append("CONTROL_SCOPE_REVIEW")
        is_reviewed = key == scene["candidate_digest"]
        supported = is_reviewed and not bound["active_control_annotations"] and bound["clause_route"] == "PERSON_INTERACTION_CONFLICT_UNCONFIRMED"
        admission = assess_conditional_candidate(row, english_meaning_recorded=is_reviewed and english_recorded,
            supported_scope=supported, solver_checks_passed=is_reviewed and checks["matches_expected"] == checks["query_count"] and checks["query_count"] > 0,
            permitted_actions=allowed if is_reviewed else ())
        row["conditional_admission"] = admission
        row["strict_source_status_unchanged"] = prior["status"]
        if admission["conditional_development_admissible"]:
            row["status"] = "CONDITIONAL_DEVELOPMENT_ADMITTED"
            row["missing_codes"] = [c for c in row["missing_codes"] if c not in {"ROAD_UNKNOWN", "COC_UNKNOWN_TARGET_POLICY"}]
            row["retained_uncertainty"] = ["ROAD_UNKNOWN"]
        rows.append(row)
    if len(old_bindings) != 19 or len(bindings) - len(old_bindings) != 13:
        raise ValueError("19/13 partition changed")
    return rows, bindings, inputs


def run(output):
    if output.exists():
        raise FileExistsError(output)
    rows, bindings, inputs = execute()
    admitted = [row for row in rows if row["conditional_admission"]["conditional_development_admissible"]]
    nominal = sum(r["conditional_admission"]["nominal_entry_label_available"] for r in rows)
    result = {"project_id": "guardsynth-coc", "status": "MACHINE_BINDINGS_COMPLETE_CONDITIONAL_ADMISSION_APPLIED",
        "candidate_count": len(rows), "exact_event_source_bindings": len(bindings), "new_unreviewed_source_bindings": 13,
        "prior_bindings_replayed_unchanged": 19, "conditional_development_admitted": len(admitted),
        "pending_count": sum(r["status"] == "NEEDS_CONFIRMATION" for r in rows),
        "currently_unusable_count": sum(r["status"] == "CURRENTLY_UNUSABLE" for r in rows),
        "full_source_verified_count": sum(r["source_accepted"] for r in rows), "main_training_admitted": 0,
        "nominal_entry_label_count": nominal, "fresh_test_candidates": 0, "training_exports": 0,
        "new_human_answers_inferred": 0, "optimizer_steps": 0,
        "control_scope_pending": sum("CONTROL_SCOPE_REVIEW" in r["missing_codes"] for r in rows),
        "machine_clause_routes": dict(Counter(b["clause_route"] for b in bindings)),
        "human_action_labels": dict(Counter(r["independent_development_action"] for r in rows if r["independent_action_available"])),
        "main_training_blockers": ["NOMINAL_ENTRY_GOLD_MISSING", "INDEPENDENT_MAIN_GOLD_AND_FRESH_TEST", "REAL_L1_L2_AND_SOURCE_ACCEPTED_L3_PROVIDERS", "FRAME_SAMPLING_SPLIT_POWER_MATCHED_BUDGET"],
        "claim_scope": "SOURCE_WITNESSES_AND_CONDITIONAL_DEVELOPMENT_ADMISSION_NOT_MAIN_LEARNING"}
    questions = []
    for row in rows:
        if row["status"] in {"CONDITIONAL_DEVELOPMENT_ADMITTED", "CURRENTLY_UNUSABLE"}:
            continue
        questions.append({"candidate_digest": row["candidate_digest"], "display_label": row["display_label"],
            "machine_source_target_ids": row["source_linked_person_ids"], "machine_control_count": row["active_control_count"],
            "source_curator_questions": ["판단 시점의 대상과 진입 영역을 확인할 수 있는가?", "그 시점의 관련 조건은 확인됨/해제 확인/미확인 중 무엇인가?"]
                + (["다른 신호·작업자 통제가 이 진입 판단에 적용되는가?"] if "CONTROL_SCOPE_REVIEW" in row["missing_codes"] else []),
            "independent_action_review": "별도 검토자에게 source/CNL 답변 노출 전 진입/보류/판단불가 확인",
            "cnl_review": "확정 근거로 실제 문장을 생성한 뒤 별도 확인",
            "answers": None, "review_packet_ready": False})
    output.mkdir(parents=True, exist_ok=False, mode=0o700)
    for name, value in (("candidate_readiness.json", {"records": rows}), ("event_source_bindings.json", {"records": bindings}),
                        ("human_work_queue.json", {"records": questions, "not_a_ready_survey": True}),
                        ("conditional_development_candidates.json", {"records": admitted, "learning_export_allowed": False}),
                        ("RESULT.json", result)):
        r.write_json(output / name, value)
    report = ["# 조건부 수용 및 기계 근거 연결 완료", "",
        f"32건 전체 source interval 연결: 기존 19건 동일 재현 + 미검토 13건 추가. 사람 답변 생성 0건.",
        f"조건부 개발 후보 {len(admitted)}, 추가 확인 {result['pending_count']}, 현재 사용 불가 {result['currently_unusable_count']}. 전체 source 확정은 {result['full_source_verified_count']}건이다.",
        "#18은 확인된 대상/영역·보행자 TRUE·독립 행동/CNL·영문 의견과 선언된 정책으로 조건부 수용했다. road UNKNOWN은 그대로이며 원본 CoC와 source 판정을 수정하지 않았다.",
        "기존 0/31/1은 strict source 기준 결과로 보존하고 새 정책의 조건부 수용 열을 추가했다. 본 학습 승인이나 시험용 전환은 아니다.",
        f"독립 정상 진입 정답 {nominal}, 신규 미노출 시험 후보 0. 현재 DEFER_ENTRY 한 사례로는 정상 진행 유지나 학습 효과를 입증할 수 없다.",
        "## 남은 작업", "", "- 대상/영역/조건이 미확정인 장면의 사람 확인. 기계 source ID를 인간 확인으로 승격하지 않는다.",
        "- 혼합 통제 적용성은 별도 확인. 보행자가 비켰다는 관찰만으로 다른 신호까지 해제하지 않는다.",
        "- 독립 행동 및 CNL 검토를 분리하고 정상 진입 사례를 확보한다. 미관측 13건의 observation은 계속 null이다.",
        "- L1/L2 실제 provider와 본 gold·미노출 test·sampling·표본 수·동일 예산은 미완료다. VLM 본 학습은 실행하지 않았다.", "",
        "| 장면 | 상태 | source 대상 ID(사람 확인 아님) | 통제 수 |", "|---|---|---|---|"]
    labels = {**audit.STATUS_KO, "CONDITIONAL_DEVELOPMENT_ADMITTED": "조건부 개발 후보 수용"}
    for row in rows:
        report.append(f"| {row['display_label']} | {labels[row['status']]} | {', '.join(row['source_linked_person_ids']) or '없음'} | {row['active_control_count']} |")
    (output / "REPORT_KO.md").write_text("\n".join(report), encoding="utf-8")
    cards = ''.join(f"<details><summary>{escape(row['display_label'])} — {labels[row['status']]}</summary><p>{escape(row['original_coc'])}</p><p>기계 source 대상: {escape(', '.join(row['source_linked_person_ids']) or '없음')} · 사람 확인과 다릅니다.</p><ul>" + ''.join(f"<li>{escape(audit.REASONS[c][1])}</li>" for c in row['missing_codes']) + '</ul></details>' for row in rows)
    (output / "candidate_readiness.html").write_text('<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>조건부 데이터 수용</title><style>body{font:18px/1.7 system-ui;max-width:1400px;margin:24px auto;padding:16px}details{border:1px solid #bbb;padding:12px;margin:12px 0}summary{cursor:pointer}</style><h1>32장면 조건부 데이터 수용</h1><p>읽기 전용 결과 · 새 설문이 아닙니다.</p><p>' + escape(report[2] + ' ' + report[3]) + '</p><p>#18의 주도로 UNKNOWN은 유지합니다. 조건부 개발 후보와 전체 근거 확정·본 학습 승인은 다릅니다. 정상 진입 정답과 미노출 시험 후보는 아직 0건입니다.</p>' + cards + '</html>', encoding="utf-8")
    code = [Path(__file__).resolve(), Path(audit.__file__).resolve(), Path(generation.__file__).resolve(),
            r.ROOT / "projects/04-guardsynth-coc/src/guard_synth/conditional_admission.py",
            r.ROOT / "projects/04-guardsynth-coc/src/guard_synth/event_source_binding.py",
            r.ROOT / "projects/04-guardsynth-coc/src/guard_synth/review_constraint_alignment.py"]
    r.write_json(output / "RUN_MANIFEST.json", {"project_id": "guardsynth-coc", "experiment_id": audit.EXPERIMENT,
        "run_id": output.name, "status": result["status"], "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "network_used": False, "input_hashes": inputs, "code_hashes": {str(p.relative_to(r.ROOT)): r.digest(p) for p in code},
        "output_hashes": {p.name: r.digest(p) for p in output.iterdir()}})
    for p in output.iterdir():
        p.chmod(0o600)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*-[0-9]+", args.run_id):
        parser.error("unused numeric run ID required")
    output = audit.BASE / audit.EXPERIMENT / args.run_id
    print(run(output))
    print(output)
