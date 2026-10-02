"""Audit all 32 existing development candidates; never infer missing gold or splits."""

import argparse
from collections import Counter, defaultdict
import csv
from datetime import datetime, timezone
import hashlib
from html import escape
import json
from pathlib import Path
import re

import prepare_source_review as source
import align_reviews as alignment
import execute_reviewed_contract as reviewed

ROOT, BASE = source.ROOT, source.BASE
EXPERIMENT = "guardsynth-paper1-training-readiness-001"
PREFLIGHT = BASE / reviewed.EXPERIMENT / "scene18-training-preflight-2026-09-08-001"
LINKAGE = PREFLIGHT.parent / "scene18-review-linkage-2026-09-08-001"
STATUS_KO = {"READY": "사용 가능", "NEEDS_CONFIRMATION": "추가 확인 필요", "CURRENTLY_UNUSABLE": "현재 사용 불가"}
REASONS = {
    "ASSET_UNAVAILABLE_OR_MISMATCH": ("MACHINE", "원본 CoC·주석·영상·프레임 연결 오류를 해결"),
    "PRIOR_NOT_OBSERVABLE": ("SOURCE_CURATOR", "기존 관찰 불가를 보존; 새 근거 확보 전 현재 자료로 정답을 만들지 않음"),
    "NO_PRIOR_VIDEO_OBSERVATION": ("MACHINE_THEN_CURATOR", "원본 근거를 먼저 정리한 뒤 필요한 관측만 확인"),
    "EXACT_EVENT_BINDING_PENDING": ("MACHINE", "사건 시점 원본 interval·대상 연결 감사 확장"),
    "EVENT_TARGET_ZONE_PREDICATES_UNCONFIRMED": ("MACHINE_THEN_CURATOR", "기존 관찰·기계 표시 재사용 후 t0 대상·의미 영역·조건의 누락만 확인"),
    "ROAD_UNKNOWN": ("SOURCE_CURATOR_OR_TASK_POLICY", "미확정 도로 조건을 유지; 추가 근거나 명시적 과제 수용 정책 필요"),
    "COC_UNKNOWN_TARGET_POLICY": ("RESEARCH_PROTOCOL", "원본 CoC의 양보 지시와 미확정 근거를 학습 target에서 어떻게 다룰지 결정"),
    "CONTROL_SCOPE_REVIEW": ("RESEARCH_PROTOCOL_THEN_CURATOR", "작업자·신호 등 동시 통제의 적용 여부와 구현 subset 적합성 확인"),
    "RELEASE_NOT_GLOBAL_PERMISSION": ("RESEARCH_PROTOCOL_THEN_CURATOR", "보행자 위험 해제를 전체 진입 허가로 바꾸지 않음; 다른 통제 확인"),
    "WINDOW_ABSENCE_NOT_ACTION_GOLD": ("INDEPENDENT_ACTION_REVIEWER", "시간창 위험 없음으로 진입 정답을 자동 생성하지 않음"),
    "CONTRACT_CNL_NOT_LINKED": ("MACHINE_AFTER_SOURCE", "수용된 장면 근거로 EBLC·검사·CNL을 연결; #18 규칙을 무조건 복제하지 않음"),
    "INDEPENDENT_ACTION_PENDING": ("INDEPENDENT_ACTION_REVIEWER", "source/CNL 답변을 노출하지 않은 별도 행동 판정 필요"),
    "SCENE_CNL_REVIEW_PENDING": ("INDEPENDENT_CNL_REVIEWER", "생성 문장이 장면 근거·명세를 정확히 전달하는지 검토"),
}


def index_unique(records):
    result = {}
    for row in records:
        key = row["candidate_digest"]
        if key in result:
            raise ValueError("duplicate candidate")
        result[key] = row
    return result


def classify(row):
    if not row["assets_verified"] or row["prior_observation"] == "NOT_OBSERVABLE":
        return "CURRENTLY_UNUSABLE"
    gates = ("source_accepted", "contract_cnl_linked", "independent_action_available", "cnl_review_available")
    if all(row[k] is True for k in gates) and not row["missing_codes"]:
        return "READY"
    return "NEEDS_CONFIRMATION"


def select_causal_frame(times, event_us):
    if any(y["timestamp"] <= x["timestamp"] for x, y in zip(times, times[1:])):
        raise ValueError("non-monotonic source timestamps")
    candidates = [f for f in times if f["timestamp"] <= event_us]
    return candidates[-1] if candidates else None


def split_audit(records):
    groups = defaultdict(list)
    for row in records:
        groups[row["clip_id"]].append(row)
    return {
        "status": "DEVELOPMENT_QUARANTINE_NO_MAIN_SPLIT_ASSIGNED", "split_frozen": False,
        "group_count": len(groups), "fresh_test_candidate_count": 0,
        "reason": "All selected candidates inherit NOT_ADMITTED_PRIOR_DEVELOPMENT_POOL; unreviewed is not unexposed.",
        "train_assignments": [], "dev_assignments": [], "test_assignments": [],
        "groups": [{"clip_id": clip, "candidate_digests": [r["candidate_digest"] for r in rows],
                    "geometry_indices": [r["geometry_index"] for r in rows],
                    "upstream_splits": sorted({r["upstream_split"] for r in rows}),
                    "allowed_future_role": "TRAIN_OR_DEV_ONLY_AFTER_ADMISSION", "test_allowed": False}
                   for clip, rows in sorted(groups.items())],
        "scope": "CLIP_LEVEL_QUARANTINE_NOT_PROOF_OF_CROSS_CLIP_EPISODE_INDEPENDENCE",
    }


def collect():
    import cv2
    import pyarrow.parquet as pq
    audit, inputs = source.audit_inputs()
    # Recheck path-keyed source runs; older geometry manifests use semantic labels.
    for directory in (source.ALIGNMENT, alignment.INVENTORY, reviewed.CLARIFICATION, LINKAGE, PREFLIGHT):
        manifest = reviewed.revalidate_run(directory)
        for path in [directory / "RUN_MANIFEST.json"] + [directory / n for n in manifest["output_hashes"]]:
            inputs[str(path.relative_to(ROOT))] = source.digest(path)
    inventory = [r for r in source.load(alignment.INVENTORY / "source_audit.json") if r["selected_development_family"]]
    selected = index_unique(inventory)
    if len(selected) != 32:
        raise ValueError("32-scene denominator drift")
    bound_data = source.load(source.BINDING / "event_source_bindings.json")
    bindings = index_unique(bound_data["records"])
    if set(bindings) & set(index_unique(bound_data["deferred_records"])) or set(selected) != set(bindings) | set(index_unique(bound_data["deferred_records"])):
        raise ValueError("binding partition differs from inventory")
    aligned = index_unique(source.load(source.ALIGNMENT / "scene_constraint_alignment.json")["records"])
    geometries = index_unique(source.load(source.GEOMETRY / "GEOMETRY_CANDIDATE_MANIFEST.json")["records"])
    submitted = index_unique(source.load(source.SUBMISSION / "m16_geometry_candidate_review (1).json")["records"])
    structured_path = alignment.ACQUISITION / "m16-cascade-structured-link-audit-2026-09-05-v1/CASCADE_STRUCTURED_LINK_AUDIT.json"
    structured = index_unique(source.load(structured_path)["records"])
    authority_path = alignment.ACQUISITION / "m16-treaty-authority-binding-2026-09-06-v2/TREATY_AUTHORITY_AUDIT.json"
    authorities = index_unique(source.load(authority_path)["records"])
    reasoning = ROOT / "data/restricted/nvidia_physicalai/reasoning/ood_reasoning.parquet"
    events = defaultdict(list)
    for clip in pq.read_table(reasoning).to_pylist():
        for event in json.loads(clip["events"] or "[]"):
            events[(clip["clip_id"], int(event["event_start_timestamp"]))].append(event["coc"])
    annotations = defaultdict(list)
    for path in (ROOT / "data/restricted/nvidia_cascade/data").glob("*/*.json"):
        annotations[path.stem.split("__")[-1]].append(path)
    accepted_scene, _, effective, extra = reviewed.reviewed_inputs()
    inputs.update(extra)
    scene18_key = accepted_scene["candidate_digest"]
    current_binding = source.load(PREFLIGHT.parent / "scene18-conditioned-cnl-2026-09-08-002/event_binding.json")
    linkage = source.load(LINKAGE / "RESULT.json")
    rows = []
    for key, item in selected.items():
        g, s = geometries[key], submitted[key]
        t = item["event_timestamp_us"]
        if g["event_timestamp_us"] != t or s["event_timestamp_us"] != t:
            raise ValueError("geometry event mismatch")
        a, b = aligned.get(key), bindings.get(key)
        errors = []
        def verify(path, expected):
            try:
                source.verified(path, expected)
            except (OSError, ValueError):
                errors.append(str(path.relative_to(ROOT)))
                return False
            inputs[str(path.relative_to(ROOT))] = expected
            return True
        matches = events[(item["group_id"], t)]
        coc_ok = len(matches) == 1 and hashlib.sha256(matches[0].encode()).hexdigest() == item["coc_sha256"]
        if not coc_ok:
            errors.append("original CoC identity/hash mismatch")
        annotation_paths = annotations[item["group_id"]]
        expected_annotation = structured[key]["cascade_structured_link_audit"]["annotation_sha256"]
        annotation_ok = len(annotation_paths) == 1 and verify(annotation_paths[0], expected_annotation)
        if annotation_ok and source.load(annotation_paths[0])["video"]["clip_id"] != item["group_id"]:
            raise ValueError("annotation clip mismatch")
        event_folder = "event-" + g["asset_candidate_digest"].split(":")[1]
        paths = [ROOT / "data/restricted/nvidia_physicalai/internal-derived" / folder / event_folder / "camera_front_wide_120fov/video.mp4"
                 for folder in ("m16-shortlist-v1", "m16-reserve-v1")]
        videos = [p for p in paths if p.is_file()]
        # Primary/reserve may contain byte-identical materializations of the same event.
        video_matches = [verify(p, g["source_video_sha256"]) for p in videos]
        video_ok = bool(videos) and all(video_matches)
        f = next(f for f in g["frames"] if f["offset_s"] == 0)
        frame_ok = False
        causal = None
        causal_sha = None
        if video_ok:
            times = videos[0].with_name("frame_timestamps.parquet")
            inputs[str(times.relative_to(ROOT))] = source.digest(times)
            times_rows = pq.read_table(times).to_pylist()
            causal = select_causal_frame(times_rows, t)
            timestamp_ok = any((x["frame_index"], x["timestamp"]) == (f["frame_index"], f["timestamp_us"]) for x in times_rows)
            cap = cv2.VideoCapture(str(videos[0]))
            try:
                cap.set(cv2.CAP_PROP_POS_FRAMES, f["frame_index"])
                ok, pixels = cap.read()
                historical_ok = ok and timestamp_ok and hashlib.sha256(pixels.tobytes()).hexdigest() == f["source_pixel_sha256"]
                if causal:
                    cap.set(cv2.CAP_PROP_POS_FRAMES, causal["frame_index"])
                    causal_ok, causal_pixels = cap.read()
                    if causal_ok:
                        causal_sha = hashlib.sha256(causal_pixels.tobytes()).hexdigest()
                    frame_ok = historical_ok and causal_ok
            finally:
                cap.release()
        overlay_ok = verify(source.GEOMETRY / f["overlay_path"], f["overlay_sha256"])
        if s["source_video_sha256"] != g["source_video_sha256"] or s["t0_source_pixel_sha256"] != f["source_pixel_sha256"]:
            raise ValueError("geometry submission reference mismatch")
        observation = a["observation"]["visual_temporal_observation"] if a else None
        special = key == scene18_key
        missing = []
        if not all((coc_ok, annotation_ok, video_ok, frame_ok, overlay_ok)):
            missing.append("ASSET_UNAVAILABLE_OR_MISMATCH")
        if observation == "NOT_OBSERVABLE":
            missing.append("PRIOR_NOT_OBSERVABLE")
        if a is None:
            missing.extend(["NO_PRIOR_VIDEO_OBSERVATION", "EXACT_EVENT_BINDING_PENDING"])
        if special:
            missing.extend(["ROAD_UNKNOWN", "COC_UNKNOWN_TARGET_POLICY"])
        else:
            missing.extend(["EVENT_TARGET_ZONE_PREDICATES_UNCONFIRMED", "CONTRACT_CNL_NOT_LINKED", "INDEPENDENT_ACTION_PENDING", "SCENE_CNL_REVIEW_PENDING"])
        if b and b["clause_route"] in {"MIXED_CONTROL_OR_WORK_CONTEXT", "RELEASE_WITH_OTHER_CONTROL_CHECK"}:
            missing.append("CONTROL_SCOPE_REVIEW")
        if b and b["release_control_check_required"]:
            missing.append("RELEASE_NOT_GLOBAL_PERMISSION")
        if observation == "NO_HAZARD_VISIBLE":
            missing.append("WINDOW_ABSENCE_NOT_ACTION_GOLD")
        row = {"candidate_digest": key, "asset_candidate_digest": g["asset_candidate_digest"], "clip_id": item["group_id"], "event_timestamp_us": t,
            "review_index": a["review_index"] if a else None, "geometry_index": g["review_index"],
            "upstream_split": item["upstream_split"], "original_coc": matches[0] if coc_ok else None,
            "coc_sha256": item["coc_sha256"], "prior_observation": observation,
            "geometry_review_completed": True, "exported_polygon_count": len(s["normalized_pixel_polygons"]),
            "reviewed_event_zone": effective["zone_polygon"] if special else None,
            "reviewed_event_target": effective["target_point"] if special else None,
            "event_predicates": current_binding["event_predicates"] if special else None,
            "source_accepted": current_binding["source_accepted_for_development"] if special else False,
            "exact_event_source_audit": b is not None,
            "source_linked_person_ids": b["source_linked_person_ids"] if b else None,
            "active_control_count": len(b["active_control_annotations"]) if b else None,
            "clause_route": b["clause_route"] if b else "NOT_YET_ROUTED",
            "authority_record": authorities[key], "authority_is_action_gold": False,
            "assets_verified": all((coc_ok, annotation_ok, video_ok, frame_ok, overlay_ok)), "asset_errors": errors,
            "raw_video": str(videos[0].relative_to(ROOT)) if video_ok else None,
            "annotation_path": str(annotation_paths[0].relative_to(ROOT)) if annotation_ok else None,
            "annotation_sha256": expected_annotation, "source_video_sha256": g["source_video_sha256"],
            "causal_frame_pixel_verified": frame_ok, "causal_frame_pixel_sha256": causal_sha,
            "causal_frame_index": causal["frame_index"] if causal else None,
            "causal_frame_offset_us": causal["timestamp"] - t if causal else None,
            "historical_display_frame_offset_us": f["timestamp_us"] - t,
            "historical_display_is_future": f["timestamp_us"] > t,
            "video_materialization_count": len(videos),
            "context_overlay": str((source.GEOMETRY / f["overlay_path"]).relative_to(ROOT)),
            "contract_cnl_linked": special and linkage["generated_text_replay_matches"],
            "independent_action_available": special and linkage["review_verdicts"]["ACTION"]["judgement_available"],
            "cnl_review_available": special and linkage["korean_all_supported"],
            "independent_development_action": linkage["independent_action_label"] if special else None,
            "exposure_status": item["independent_test_admission"], "test_allowed": False,
            "missing_codes": missing, "learning_export_allowed": False}
        if row["exposure_status"] != "NOT_ADMITTED_PRIOR_DEVELOPMENT_POOL":
            raise ValueError("exposure policy changed; reassess split authority")
        row["status"] = classify(row)
        row["display_label"] = (f"영상 #{a['review_index']:02d}" if a else "영상검토 없음") + f" · 후보 #{g['review_index']:02d}"
        row["evidence_refs"] = {"inventory": str((alignment.INVENTORY / "source_audit.json").relative_to(ROOT)),
            "geometry_submission": str((source.SUBMISSION / "m16_geometry_candidate_review (1).json").relative_to(ROOT)),
            "event_binding": str((source.BINDING / "event_source_bindings.json").relative_to(ROOT)) if b else None,
            "current_scene18_preflight": str((PREFLIGHT / "RUN_MANIFEST.json").relative_to(ROOT)) if special else None}
        rows.append(row)
    return sorted(rows, key=lambda x: x["geometry_index"]), inputs


def run(output):
    if output.exists():
        raise FileExistsError(output)
    rows, inputs = collect()
    counts = Counter(r["status"] for r in rows)
    splits = split_audit(rows)
    gaps = [{"code": code, "owner": owner, "required_work_ko": text,
             "candidate_digests": [r["candidate_digest"] for r in rows if code in r["missing_codes"]],
             "scene_labels": [r["display_label"] for r in rows if code in r["missing_codes"]]}
            for code, (owner, text) in REASONS.items() if any(code in r["missing_codes"] for r in rows)]
    result = {"project_id": "guardsynth-coc", "status": "CANDIDATE_READINESS_AUDIT_COMPLETE_MAIN_DATA_BLOCKED",
        "candidate_count": len(rows), "status_counts": {s: counts[s] for s in STATUS_KO},
        "clip_group_count": splits["group_count"], "assets_verified_count": sum(r["assets_verified"] for r in rows),
        "historical_display_future_count": sum(r["historical_display_is_future"] for r in rows),
        "duplicate_video_materialization_count": sum(r["video_materialization_count"] > 1 for r in rows),
        "asset_alias_count": sum(r["asset_candidate_digest"] != r["candidate_digest"] for r in rows),
        "prior_observations_reused": sum(r["prior_observation"] is not None for r in rows),
        "without_prior_observation": sum(r["prior_observation"] is None for r in rows),
        "geometry_reviews_reused": len(rows), "reviewed_event_zone_count": sum(bool(r["reviewed_event_zone"]) for r in rows),
        "conditional_contract_cnl_count": sum(r["contract_cnl_linked"] for r in rows),
        "independent_development_action_count": sum(r["independent_action_available"] for r in rows),
        "fresh_test_candidate_count": 0, "split_frozen": False, "training_exports": 0,
        "repeat_full_survey_requested": False, "new_human_answers_inferred": 0,
        "main_study_gates": ["TASK_SOURCE_AND_TARGET_POLICY", "REAL_L1_L2_L3_PROVIDERS", "INDEPENDENT_MAIN_GOLD_AND_FRESH_TEST_COHORT", "FRAME_SAMPLING_AND_MATCHED_BUDGET", "SAMPLE_SIZE_AND_SPLIT_FREEZE"],
        "claim_scope": "DEVELOPMENT_DATA_READINESS_NOT_MAIN_ELIGIBILITY_OR_LEARNING_EFFECT"}
    lines = ["# 32장면 학습 데이터 적격성 점검", "",
        f"사용 가능 {counts['READY']}, 추가 확인 필요 {counts['NEEDS_CONFIRMATION']}, 현재 사용 불가 {counts['CURRENTLY_UNUSABLE']}. 분모 32건을 모두 보존했다.",
        "사용 가능은 현재 장면 자료의 수용 조건을 뜻하며 본 학습 허가는 아니다. 부족한 검토·좌표·조건을 자동 생성하지 않았다.",
        "현재 사용 불가는 영구 폐기가 아니다. 기존 관찰 불가 또는 자료 오류를 현재 근거로 해결하지 못했다는 뜻이다.",
        "기존 nearest-frame 표시는 보존하고 원본 영상에서 마지막 과거 프레임을 별도로 선택·해시 기록했다. 중복 materialization은 원본 해시가 모두 같을 때만 재사용한다.",
        "영상 검토 번호와 geometry 후보 번호가 다르므로 함께 표시한다. 원본 CoC·기존 설문·업로드는 변경하지 않았다.", "",
        "| 장면 | 판정 | 기존 관찰 | 필요한 항목 |", "|---|---|---|---|"]
    for row in rows:
        labels = "; ".join(REASONS[c][1] for c in row["missing_codes"])
        lines.append(f"| {row['display_label']} | {STATUS_KO[row['status']]} | {row['prior_observation'] or '미검토'} | {labels} |")
    lines += ["", "## 분할 및 해석", "",
        f"32건은 {splits['group_count']}개 영상 그룹이다. 모두 기존 개발 후보군이므로 시험용 신규 후보는 0이다. 미검토 13건도 미노출 시험 표본이라고 간주하지 않는다.",
        "동일 영상의 모든 사건은 한 그룹으로 묶었다. train/dev/test는 아직 배정하지 않았다. episode 수준의 영상 간 연관성은 추가 감사 대상이다.",
        "#18의 새 대상/영역·보행자 TRUE·행동/CNL 검토는 반영했다. road UNKNOWN은 유지하므로 전체 source 수용으로 승격하지 않았다.",
        "001/002는 경로·프레임 선택 구현 점검 이력이다. 현 실행은 manifest의 asset alias를 따르고 nearest-frame와 causal-frame를 분리한다. 기존 입력/검토를 수정하거나 미래 프레임을 허용한 것이 아니다.",
        "#54/#56의 보행자 위험 해제는 다른 통제를 해제하지 않는다. 작업자/통제 혼합 장면은 과제 subset 검토 대상이지 자동 제외가 아니다.",
        "기존 geometry 검토 완료와 좌표 export 존재는 구분한다. 좌표 없음은 브라우저에서 그리지 않았다는 뜻이 아니다.",
        "## 다음 실행 순서", "",
        "1. 연구자가 과제별 UNKNOWN/원본 CoC target 처리와 혼합 통제 적용 범위를 확정한다.",
        "2. 기계가 미관측 13건의 시점별 source 연결을 확장하고, 기존 19건은 누락된 대상·영역·조건만 준비한다.",
        "3. 필요한 source 확인과 독립 ACTION/CNL 검토를 분리한다. 여기의 부족 항목 수는 새 설문 건수가 아니다.",
        "4. 별도 미노출 시험 후보군과 본 gold·분할·표본 수·비교 예산을 동결한다. 32건을 임의로 나눠 독립 시험 세트를 만들지 않는다.", ""]
    output.mkdir(parents=True, exist_ok=False, mode=0o700)
    for name, value in (("candidate_readiness.json", {"records": rows}), ("missing_evidence.json", {"work_groups": gaps}),
                        ("split_feasibility.json", splits), ("RESULT.json", result)):
        source.write_json(output / name, value)
    columns = ["display_label", "candidate_digest", "clip_id", "event_timestamp_us", "upstream_split", "status", "prior_observation", "assets_verified", "contract_cnl_linked", "independent_action_available", "test_allowed", "missing_codes"]
    with (output / "candidate_readiness.csv").open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: ";".join(row[k]) if isinstance(row[k], list) else row[k] for k in columns})
    (output / "REPORT_KO.md").write_text("\n".join(lines), encoding="utf-8")
    cards = "".join(f"<details><summary>{escape(r['display_label'])} — {STATUS_KO[r['status']]}</summary><p>원본 CoC: {escape(r['original_coc'] or '연결 오류')}</p><p>기존 관찰: {escape(r['prior_observation'] or '미검토')}</p><ul>" + "".join(f"<li>{escape(REASONS[c][1])}</li>" for c in r["missing_codes"]) + "</ul></details>" for r in rows)
    (output / "candidate_readiness.html").write_text('<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>32장면 적격성 점검</title><style>body{font:18px/1.7 system-ui;max-width:1400px;margin:24px auto;padding:16px}details{border:1px solid #bbb;padding:12px;margin:12px 0}summary{cursor:pointer}</style><h1>32장면 학습 데이터 적격성 점검</h1><p>읽기 전용 결과입니다. 새 설문이 아닙니다.</p><p>' + escape(lines[2]) + f'</p><p>32건 / {splits["group_count"]}개 개발 영상. 독립 시험용 0건. 기존 #18 검토를 다시 하지 않습니다. 본 학습·분할 확정은 아닙니다.</p>' + cards + '</html>', encoding="utf-8")
    code = [Path(__file__).resolve(), Path(source.__file__).resolve(), Path(reviewed.__file__).resolve()]
    source.write_json(output / "RUN_MANIFEST.json", {"project_id": "guardsynth-coc", "experiment_id": EXPERIMENT,
        "run_id": output.name, "status": result["status"], "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "network_used": False, "input_hashes": inputs, "code_hashes": {str(p.relative_to(ROOT)): source.digest(p) for p in code},
        "output_hashes": {p.name: source.digest(p) for p in output.iterdir()}})
    for path in output.iterdir():
        path.chmod(0o600)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*-[0-9]+", args.run_id):
        parser.error("unused numeric run ID required")
    output = BASE / EXPERIMENT / args.run_id
    print(json.dumps(run(output), ensure_ascii=False, indent=2))
    print(output)
