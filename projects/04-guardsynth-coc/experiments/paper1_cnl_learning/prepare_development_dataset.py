"""Export one reviewed development scene and prepare 30 source-only gap reviews."""

import argparse
import base64
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import shutil

# Select the project solver before importing any compiler consumers.
import run as learning
import complete_candidate_bindings as admission
from guard_synth.cnl_training import ConstraintSupervision, build_example, digest_text
from guard_synth.source_acceptance import point, polygon

r = admission.r
PARENT = admission.audit.BASE / admission.audit.EXPERIMENT / "conditional-candidates-2026-09-08-002"
DESIGN = r.ROOT / "projects/04-guardsynth-coc/docs/designs/PAPER1_DEVELOPMENT_DATASET_AND_GAP_REVIEW_DESIGN_V01.md"
TEMPLATE = Path(__file__).with_name("source_gap_review.html")
SCRIPT = Path(__file__).with_name("source_gap_review.js")
VERSION = "paper1-source-gap-v0.1"
SUBMISSION = PARENT.parent / "source-gap-submission-2026-09-08-001"
CHOICES = {
    "target_status": {"CONFIRMED", "UNKNOWN", "NOT_APPLICABLE"}, "zone_status": {"CONFIRMED", "UNKNOWN", "NOT_APPLICABLE"},
    "ped_truth": {"TRUE", "FALSE", "UNKNOWN", "CONFLICT", "NOT_APPLICABLE"},
    "road_context": {"APPLICABLE", "NOT_APPLICABLE", "UNKNOWN"},
    "road_truth": {"TRUE", "FALSE", "UNKNOWN", "CONFLICT", "NOT_APPLICABLE"},
    "control_context": {"APPLICABLE", "NOT_APPLICABLE", "UNKNOWN"},
    "control_truth": {"TRUE", "FALSE", "UNKNOWN", "CONFLICT", "NOT_APPLICABLE"},
}
TEXTS = ("target_description", "ped_reason", "road_reason", "control_reason")


def validate_answer(answer, scene):
    required = set(CHOICES) | set(TEXTS) | {"candidate_digest", "event_timestamp_us", "target_point", "zone_polygon", "reviewed_at"}
    if not isinstance(answer, dict) or set(answer) != required:
        raise ValueError("answer fields mismatch")
    if answer["candidate_digest"] != scene["candidate_digest"] or type(answer["event_timestamp_us"]) is not int or answer["event_timestamp_us"] != scene["event_timestamp_us"]:
        raise ValueError("wrong scene/time")
    for field, allowed in CHOICES.items():
        if not isinstance(answer[field], str) or answer[field] not in allowed:
            raise ValueError("choice missing: " + field)
    reason_choice = {"target_description": "target_status", "ped_reason": "ped_truth", "road_reason": "road_context", "control_reason": "control_context"}
    for field in TEXTS:
        if (not isinstance(answer[field], str) or len(answer[field]) > 4000
            or (not answer[field].strip() and answer[reason_choice[field]] != "NOT_APPLICABLE")):
            raise ValueError("reason missing: " + field)
    if not isinstance(answer["reviewed_at"], str) or datetime.fromisoformat(answer["reviewed_at"].replace("Z", "+00:00")).tzinfo is None:
        raise ValueError("review timestamp requires timezone")
    if answer["target_point"] is not None:
        point(answer["target_point"])
    if not isinstance(answer["zone_polygon"], list):
        raise ValueError("zone must be a list")
    if answer["zone_polygon"]:
        polygon(answer["zone_polygon"])
    if answer["target_status"] == "CONFIRMED" and answer["target_point"] is None:
        raise ValueError("confirmed target requires point")
    if answer["zone_status"] == "CONFIRMED" and not answer["zone_polygon"]:
        raise ValueError("confirmed zone requires polygon")
    for prefix in ("road", "control"):
        context, truth = answer[prefix + "_context"], answer[prefix + "_truth"]
        if (context == "NOT_APPLICABLE") != (truth == "NOT_APPLICABLE") or (context == "UNKNOWN" and truth != "UNKNOWN"):
            raise ValueError("context/truth mismatch: " + prefix)
    if answer["ped_truth"] in {"TRUE", "FALSE"} and (answer["target_status"] != "CONFIRMED" or answer["zone_status"] != "CONFIRMED"):
        raise ValueError("resolved pedestrian relation needs target and zone")
    return deepcopy(answer)


def pin_run(directory, inputs):
    directory = directory.resolve()
    manifest = r.revalidate_run(directory)
    inputs.update(manifest.get("input_hashes", {}))
    for path in [directory / "RUN_MANIFEST.json"] + [directory / name for name in manifest["output_hashes"]]:
        inputs[str(path.relative_to(r.ROOT))] = r.digest(path)


def export_development(output, rows, inputs):
    selected = [row for row in rows if row["conditional_admission"]["conditional_development_admissible"]]
    if len(selected) != 1 or selected[0]["review_index"] != 18:
        raise ValueError("this export supports only the reviewed scene18; re-audit other admissions")
    row = selected[0]
    preflight = admission.audit.PREFLIGHT
    generation = admission.generation.PARENT.parent / "scene18-conditioned-cnl-2026-09-08-002"
    pin_run(preflight, inputs)
    pin_run(generation, inputs)
    document, _, checks = admission.generation.generate_scene_cnl(
        r.load(admission.generation.PARENT / "action_contract.json"), r.load(admission.generation.PARENT / "event_binding.json"))
    if document != r.load(generation / "scene_cnl.json") or checks["matches_expected"] != checks["query_count"]:
        raise ValueError("reviewed CNL replay failed")
    previews = r.load(preflight / "development_previews.json")
    original = next(p for p in previews if p["arm"] == "L0")
    if (original["scene_id"] != row["candidate_digest"] or original["action"] != row["independent_development_action"]
        or original["coc_sha256"] != row["coc_sha256"]):
        raise ValueError("reviewed label/CoC mismatch")
    image = Path(original["image"])
    r.verified(image, original["image_sha256"])
    inputs[str(image.relative_to(r.ROOT))] = r.digest(image)
    local_image = output / "scene18_input.jpg"
    shutil.copyfile(image, local_image)
    constraint = ConstraintSupervision("L3", document["text_en"], {
        "text_sha256": digest_text(document["text_en"]), "document_sha256": r.digest(generation / "scene_cnl.json"),
        "semantic_verification": "REVIEWED_PARTIAL_SOURCE_BOUNDED_CONTRACT", "source_complete": False,
        "provider_status": "REVIEWED_DEVELOPMENT_ONLY_NOT_MAIN_L3_PROVIDER"})
    examples = [build_example(scene_id=row["candidate_digest"], group_id=row["clip_id"], split="dev",
        image=local_image, image_sha256=original["image_sha256"], coc=row["original_coc"],
        coc_source_ref=original["coc_source_ref"], choices=original["choices"], action=original["action"],
        action_source_ref=original["action_source_ref"], arm=arm, constraint=constraint if arm == "L3" else None)
        for arm in ("L0", "L3")]
    from transformers import AutoProcessor
    processor = AutoProcessor.from_pretrained(learning.MODEL_PATH, local_files_only=True)
    metrics = []
    for example in examples:
        example.update(dataset_scope="DEVELOPMENT_SFT_DEBUG_ONLY", development_training_allowed=True,
            main_training_allowed=False, main_test_eligibility=False, preview_only=False,
            review_input_equivalence=False, event_predicates=row["event_predicates"])
        full, prompt = learning.encode(processor, example)
        n = prompt["input_ids"].shape[1]
        if not (full["labels"][:, :n] == -100).all() or not full["labels"][:, n:].equal(full["input_ids"][:, n:]):
            raise ValueError("assistant loss mask mismatch")
        metrics.append({"arm": example["arm"], "prompt_tokens": n, "supervised_tokens": int((full["labels"] != -100).sum()),
                        "pixel_values_shape": list(full["pixel_values"].shape)})
        (output / (example["arm"].lower() + "_development.jsonl")).write_text(json.dumps(example, ensure_ascii=False) + "\n", encoding="utf-8")
    if examples[0]["input"] != examples[1]["input"] or examples[0]["common_example_sha256"] != examples[1]["common_example_sha256"]:
        raise ValueError("unmatched development pair")
    for path in learning.MODEL_PATH.iterdir():
        if path.suffix == ".json" or path.name in {"merges.txt", "vocab.json"}:
            inputs[str(path)] = r.digest(path)
    return examples, metrics


def select_past_frames(times, event):
    if not times or any(b["timestamp"] <= a["timestamp"] for a, b in zip(times, times[1:])):
        raise ValueError("invalid frame timestamps")
    causal = [t for t in times if t["timestamp"] <= event]
    if not causal:
        raise ValueError("no causal input")
    return [causal[i] for i in sorted({round(k * (len(causal) - 1) / 6) for k in range(7)})]


def review_scene(row, binding, inputs):
    import cv2
    import pyarrow.parquet as pq
    video = r.ROOT / row["raw_video"]
    r.verified(video, row["source_video_sha256"])
    inputs[row["raw_video"]] = row["source_video_sha256"]
    timeline = video.with_name("frame_timestamps.parquet")
    inputs[str(timeline.relative_to(r.ROOT))] = r.digest(timeline)
    selected = select_past_frames(pq.read_table(timeline).to_pylist(), row["event_timestamp_us"])
    if selected[-1]["frame_index"] != row["causal_frame_index"]:
        raise ValueError("causal frame selection drift")
    frames, cap = [], cv2.VideoCapture(str(video))
    try:
        for t in selected:
            cap.set(cv2.CAP_PROP_POS_FRAMES, t["frame_index"])
            ok, pixels = cap.read()
            if not ok:
                raise ValueError("frame decode failed")
            sha = hashlib.sha256(pixels.tobytes()).hexdigest()
            if t == selected[-1] and sha != row["causal_frame_pixel_sha256"]:
                raise ValueError("causal pixel identity changed")
            ok, encoded = cv2.imencode(".jpg", pixels, [cv2.IMWRITE_JPEG_QUALITY, 90])
            if not ok:
                raise ValueError("JPEG encoding failed")
            frames.append({"timestamp_us": t["timestamp"], "frame_index": t["frame_index"],
                "pixel_sha256": sha, "sha256": hashlib.sha256(encoded.tobytes()).hexdigest(),
                "data_url": "data:image/jpeg;base64," + base64.b64encode(encoded.tobytes()).decode()})
    finally:
        cap.release()
    proposals = [{"point": [p["x"], p["y"]], "source_id": a["source_ref_id"], "timestamp_us": p["timestamp_us"]}
        for a in binding["active_actors"] if a["person_or_cyclist"] for p in a["keypoints"]
        if p["event_time_location_available"] and p["usable_as_event_input"] and p["timestamp_us"] == row["event_timestamp_us"]]
    return {"candidate_digest": row["candidate_digest"], "label": row["display_label"],
        "event_timestamp_us": row["event_timestamp_us"], "clip_id": row["clip_id"], "frames": frames,
        "original_coc": row["original_coc"], "prior_observation": row["prior_observation"],
        "geometry_review_reused": row["geometry_review_completed"], "machine_points": proposals,
        "source_person_ids": row["source_linked_person_ids"], "control_count": row["active_control_count"],
        "clause_route": row["clause_route"], "answers": None, "independent_action_gold": None,
        "priority": "NOMINAL_COVERAGE_CHECK_NOT_GOLD" if row["prior_observation"] == "NO_HAZARD_VISIBLE" else "MISSING_SOURCE_CHECK"}


def intake(output, packet_path, response_path):
    inputs = {}
    pin_run(packet_path.parent, inputs)
    packet, response = r.load(packet_path), r.load(response_path)
    if set(response) != {"review_version", "packet_sha256", "reviewer_id", "records"}:
        raise ValueError("submission fields mismatch")
    if response["review_version"] != VERSION or response["packet_sha256"] != r.digest(packet_path):
        raise ValueError("wrong packet")
    if not isinstance(response["reviewer_id"], str) or not response["reviewer_id"].strip():
        raise ValueError("reviewer required")
    scenes = {s["candidate_digest"]: s for s in packet["scenes"]}
    records = response["records"]
    if not isinstance(records, list) or not records or any(not isinstance(a, dict) for a in records):
        raise ValueError("nonempty records required")
    if len({a.get("candidate_digest") for a in records}) != len(records):
        raise ValueError("duplicate answers")
    for answer in records:
        if answer.get("candidate_digest") not in scenes:
            raise ValueError("unrequested scene")
        validate_answer(answer, scenes[answer["candidate_digest"]])
    inputs[str(response_path.resolve())] = r.digest(response_path)
    output.mkdir(parents=True, exist_ok=False, mode=0o700)
    r.write_json(output / "review_submission.json", response)
    result = {"project_id": "guardsynth-coc", "status": "SOURCE_GAP_RESPONSES_RECORDED_NOT_ACTION_GOLD",
        "source_reviews_received": len(records), "independent_action_gold_added": 0, "training_scenes_added": 0,
        "remaining_in_this_packet": len(scenes) - len(records), "automatic_source_acceptance": False}
    finish(output, inputs, result)
    return result


def finish(output, inputs, result):
    r.write_json(output / "RESULT.json", result)
    code = [Path(__file__).resolve(), TEMPLATE, SCRIPT,
            r.ROOT / "projects/04-guardsynth-coc/src/guard_synth/cnl_training.py",
            r.ROOT / "projects/04-guardsynth-coc/src/guard_synth/source_acceptance.py"]
    r.write_json(output / "RUN_MANIFEST.json", {"project_id": "guardsynth-coc", "experiment_id": admission.audit.EXPERIMENT,
        "run_id": output.name, "status": result["status"], "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "network_used": False, "input_hashes": inputs, "code_hashes": {str(p.relative_to(r.ROOT)): r.digest(p) for p in code},
        "output_hashes": {p.name: r.digest(p) for p in output.iterdir() if p.is_file() and p.name != "RUN_MANIFEST.json"}})
    for path in output.iterdir():
        if path.is_file():
            path.chmod(0o600)


def render_review(packet, packet_sha256):
    # Browser artifacts expose project-relative submission locations, not host paths.
    display = {**packet, "packet_sha256": packet_sha256,
               "submission_directory": str(Path(packet["submission_directory"]).relative_to(r.ROOT))}
    html = TEMPLATE.read_text(encoding="utf-8")
    if html.count("__PACKET__") != 1 or html.count("__SCRIPT__") != 1:
        raise ValueError("template markers changed")
    return html.replace("__PACKET__", json.dumps(display, ensure_ascii=False).replace("<", "\\u003c")).replace("__SCRIPT__", SCRIPT.read_text(encoding="utf-8"))


def refresh_review(output, source):
    if output.exists():
        raise FileExistsError(output)
    inputs = {}
    completion_design = r.ROOT / "projects/04-guardsynth-coc/docs/designs/SOURCE_GAP_COMPLETION_UI_DESIGN_V01.md"
    inputs[str(completion_design.relative_to(r.ROOT))] = r.digest(completion_design)
    pin_run(source, inputs)
    packet_path = source / "source_gap_packet.json"
    packet = r.load(packet_path)
    if packet["review_version"] != VERSION:
        raise ValueError("wrong review version")
    html = render_review(packet, r.digest(packet_path))
    output.mkdir(parents=True, exist_ok=False, mode=0o700)
    shutil.copyfile(packet_path, output / "source_gap_packet.json")
    (output / "source_gap_review.html").write_text(html, encoding="utf-8")
    result = {"project_id": "guardsynth-coc", "status": "SOURCE_GAP_UI_REFRESHED_PACKET_UNCHANGED",
              "source_review_scenes": len(packet["scenes"]), "packet_sha256": r.digest(packet_path),
              "training_data_changed": False, "human_answers_changed": False}
    finish(output, inputs, result)
    return result


def run(output):
    if output.exists():
        raise FileExistsError(output)
    inputs = {str(DESIGN.relative_to(r.ROOT)): r.digest(DESIGN)}
    pin_run(PARENT, inputs)
    rows = r.load(PARENT / "candidate_readiness.json")["records"]
    bindings = admission.audit.index_unique(r.load(PARENT / "event_source_bindings.json")["records"])
    output.mkdir(parents=True, exist_ok=False, mode=0o700)
    try:
        examples, metrics = export_development(output, rows, inputs)
        pending = sorted([row for row in rows if row["status"] == "NEEDS_CONFIRMATION"],
                         key=lambda row: (row["prior_observation"] != "NO_HAZARD_VISIBLE", row["geometry_index"]))
        scenes = [review_scene(row, bindings[row["candidate_digest"]], inputs) for row in pending]
        packet = {"review_version": VERSION, "scenes": scenes, "main_test_eligibility": False,
                  "independent_action_review": False, "sampling": "UP_TO_SEVEN_PAST_STILLS_NOT_CONTINUOUS_MOTION",
                  "submission_directory": str(SUBMISSION)}
        r.write_json(output / "source_gap_packet.json", packet)
        html = render_review(packet, r.digest(output / "source_gap_packet.json"))
        (output / "source_gap_review.html").write_text(html, encoding="utf-8")
        disposition = [{"candidate_digest": row["candidate_digest"], "label": row["display_label"],
            "disposition": "DEVELOPMENT_DATASET" if row["review_index"] == 18 else "NO_REPEAT_UNOBSERVABLE" if row["review_index"] == 47 else "SOURCE_GAP_REVIEW",
            "main_training_allowed": False, "test_allowed": False} for row in rows]
        r.write_json(output / "candidate_disposition.json", {"records": disposition})
        result = {"project_id": "guardsynth-coc", "status": "DEVELOPMENT_DATASET_EXPORTED_SOURCE_GAP_REVIEW_READY",
            "candidate_count": len(rows), "development_training_scenes": 1, "development_arm_records": len(examples),
            "arms": [e["arm"] for e in examples], "main_training_scenes": 0, "four_arm_comparison_ready": False,
            "source_review_scenes": len(scenes), "prior_no_hazard_priority_scenes": sum(s["priority"] == "NOMINAL_COVERAGE_CHECK_NOT_GOLD" for s in scenes),
            "not_repeated_scenes": [18, 47], "new_human_answers": 0, "nominal_action_gold": 0,
            "optimizer_steps": 0, "processor_revision": learning.REVISION, "processor_metrics": metrics,
            "review_input_equivalence": False, "main_test_eligibility": False,
            "claim_scope": "ONE_SCENE_LOCAL_DEVELOPMENT_SFT_DATA_NOT_MAIN_EXPERIMENT_OR_EFFECT"}
        (output / "REPORT_KO.md").write_text(
            "# 개발용 학습 데이터와 누락 근거 검토\n\n"
            "개발 학습 데이터 1장면(#18), L0/L3 JSONL 각 1행을 생성했다. 두 행은 같은 장면이며 본 학습 데이터는 0장면이다. "
            "원본 CoC·독립 개발 행동 DEFER_ENTRY·검토된 영문 CNL과 실제 과거 이미지를 연결하고 processor/mask를 확인했다. "
            "입력에는 정답/CoC/CNL을 넣지 않았다. UNKNOWN은 보존했다. 단일 프레임 학습 입력은 21프레임 검토와 동등하지 않으며 효과 평가용이 아니다.\n\n"
            "나머지 30장면의 실제 근거 검토 화면을 만들었다. 기존 NO_HAZARD_VISIBLE 4건을 앞에 배치했지만 진입 가능 정답은 부여하지 않았다. "
            "#18 검토 재사용, #47 반복 제외. 과거 프레임 최대 7개를 제공하며 연속 움직임이 불명확하면 판단 불가로 답한다. "
            "이 화면은 근거 확인이고 독립 행동 정답 설문은 아니다. 답변 후 확정 영역으로 별도 ACTION/CNL 검토를 준비한다.\n\n"
            f"제출 폴더: `{SUBMISSION}`. 완료한 장면만 JSON 저장 가능. 새 사람 답변·정상 진입 정답·가중치 갱신은 0이다.\n", encoding="utf-8")
        finish(output, inputs, result)
        return result
    except Exception as error:
        finish(output, inputs, {"project_id": "guardsynth-coc", "status": "FAILED", "error": str(error)})
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--packet", type=Path)
    parser.add_argument("--review", type=Path)
    parser.add_argument("--refresh-review-from", type=Path)
    args = parser.parse_args()
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*-[0-9]+", args.run_id) or bool(args.packet) != bool(args.review):
        parser.error("unused numeric run ID required; pair --packet and --review")
    if args.refresh_review_from and args.review:
        parser.error("UI refresh and intake are separate operations")
    output = PARENT.parent / args.run_id
    if output.exists():
        raise FileExistsError(output)
    print(refresh_review(output, args.refresh_review_from) if args.refresh_review_from else intake(output, args.packet, args.review) if args.review else run(output))
    print(output)
