"""Audit reusable evidence and prepare one event-time source review, not gold."""

import argparse
import base64
from collections import Counter
from datetime import datetime, timezone
import hashlib
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from align_reviews import ROOT, BASE, ACQUISITION, SUBMISSION, digest, load, verified, write_json
from worked_example import source_example, BINDING, ALIGNMENT, GEOMETRY
from guard_synth.source_acceptance import VERSION, validate_review

EXPERIMENT = "guardsynth-paper1-source-acceptance-001"
DESIGN = ROOT / "projects/04-guardsynth-coc/docs/designs/PAPER1_SOURCE_ACCEPTANCE_DESIGN_V01.md"
TEMPLATE = Path(__file__).with_name("source_acceptance_review.html")


def json_text(value):
    import json
    return json.dumps(value, ensure_ascii=False).replace("<", "\\u003c")


def audit_inputs():
    manifest = load(BINDING / "RUN_MANIFEST.json")
    for name, sha in manifest["output_hashes"].items():
        verified(BINDING / name, sha)
    inputs = dict(load(BINDING / "RESULT.json")["input_hashes"])
    for path, sha in inputs.items():
        verified(ROOT / path, sha)
    inputs[str((BINDING / "event_source_bindings.json").relative_to(ROOT))] = digest(BINDING / "event_source_bindings.json")
    inputs[str((BINDING / "RUN_MANIFEST.json").relative_to(ROOT))] = digest(BINDING / "RUN_MANIFEST.json")
    inputs[str(DESIGN.relative_to(ROOT))] = digest(DESIGN)
    bindings = load(BINDING / "event_source_bindings.json")
    aligned = {r["candidate_digest"]: r for r in load(ALIGNMENT / "scene_constraint_alignment.json")["records"]}
    geometry = {r["candidate_digest"]: r for r in load(GEOMETRY / "GEOMETRY_CANDIDATE_MANIFEST.json")["records"]}
    submission = load(SUBMISSION / "m16_geometry_candidate_review (1).json")
    upload_counts = {}
    for name in ("m16_geometry_candidate_review.json", "m16_geometry_candidate_review (1).json"):
        path = SUBMISSION / name
        inputs[str(path.relative_to(ROOT))] = digest(path)
        uploaded = load(path)["records"]
        upload_counts[name] = {"records": len(uploaded), "records_with_coordinates": sum(bool(r["normalized_pixel_polygons"]) for r in uploaded)}
    submitted = {r["candidate_digest"]: r for r in submission["records"]}
    if len(submitted) != 98:
        raise ValueError("geometry denominator/duplicate mismatch")
    rows = []
    for b in bindings["records"]:
        key = b["candidate_digest"]
        a, g, s = aligned[key], geometry[key], submitted[key]
        t0 = next(f for f in g["frames"] if f["offset_s"] == 0)
        if (s["event_timestamp_us"] != b["event_timestamp_us"] or s["t0_source_pixel_sha256"] != t0["source_pixel_sha256"]
            or s["source_video_sha256"] != g["source_video_sha256"] or a["geometry"]["normalized_pixel_polygons"] != s["normalized_pixel_polygons"]):
            raise ValueError("geometry source/review mismatch")
        rows.append({"candidate_digest": key, "review_index": b["review_index"], "geometry_index": g["review_index"],
            "clip_id": b["group_id"], "event_timestamp_us": b["event_timestamp_us"], "upstream_split": b["upstream_split"],
            "review_reused": True, "geometry_review_completed": a["geometry"]["review_completed"],
            "geometry_assessment": s["machine_geometry_assessment"], "retained_polygons": s["normalized_pixel_polygons"],
            "source_linked_person_ids": b["source_linked_person_ids"], "active_control_count": len(b["active_control_annotations"]),
            "event_time_point_count": sum(p["event_time_location_available"] for actor in b["active_actors"]
                if actor["person_or_cyclist"] for p in actor["keypoints"]),
            "prior_window_observation": b["prior_observation"]["visual_temporal_observation"],
            "status": "EVENT_PREDICATE_AND_SEMANTIC_ZONE_UNCONFIRMED", "learning_export_allowed": False})
    deferred = bindings["deferred_records"]
    if len(rows) != 19 or len(deferred) != 13:
        raise ValueError("paper development denominator changed")
    return {"candidate_count": 32, "records": rows, "deferred_records": deferred,
        "original_geometry_uploads": upload_counts,
        "geometry_submission_records": len(submitted),
        "geometry_submission_records_with_coordinates": sum(bool(r["normalized_pixel_polygons"]) for r in submitted.values()),
        "note": "Empty exported coordinates do not prove no drawing occurred in a browser; review completion is retained."}, inputs


def image_assets(scene, output, inputs):
    import cv2
    import pyarrow.parquet as pq
    video = ROOT / scene["raw_video"]
    times_path = video.with_name("frame_timestamps.parquet")
    inputs[str(times_path.relative_to(ROOT))] = digest(times_path)
    rows = pq.read_table(times_path).to_pylist()
    if any(b["timestamp"] <= a["timestamp"] for a,b in zip(rows, rows[1:])):
        raise ValueError("non-monotonic sensor timestamps")
    allowed = [r for r in rows if r["timestamp"] <= scene["event_timestamp_us"]]
    t0 = allowed[-1]
    if rows[0]["frame_index"] != 0:
        raise ValueError("unexpected first decoded frame index")
    if (t0["frame_index"] != scene["decoded_video_frame_index"] or t0["timestamp"] != scene["decoded_video_timestamp_us"]):
        raise ValueError("past-only selection conflicts with prior frame binding")
    # Dense enough for inspection, no claim of automatic identity tracking or motion truth.
    selected = [r for r in allowed if r["frame_index"] % 15 == 0 or r is t0]
    cap = cv2.VideoCapture(str(video))
    frames = []
    try:
        for r in selected:
            cap.set(cv2.CAP_PROP_POS_FRAMES, r["frame_index"])
            ok, frame = cap.read()
            if not ok:
                raise ValueError("source frame decode failed")
            pixel_sha = hashlib.sha256(frame.tobytes()).hexdigest()
            if r is t0:
                geo = next(g for g in load(GEOMETRY / "GEOMETRY_CANDIDATE_MANIFEST.json")["records"] if g["candidate_digest"] == scene["candidate_digest"])
                expected = next(f for f in geo["frames"] if f["offset_s"] == 0)["source_pixel_sha256"]
                if pixel_sha != expected:
                    raise ValueError("t0 decoded source pixels changed")
            if r is t0:
                ok, exact = cv2.imencode(".png", frame)
                if not ok:
                    raise ValueError("exact PNG encoding failed")
                (output / "event_frame_exact.png").write_bytes(exact.tobytes())
            ok, encoded = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 92])
            if not ok:
                raise ValueError("display JPEG encoding failed")
            name = f"frame_{r['frame_index']:04d}.jpg"
            (output / name).write_bytes(encoded.tobytes())
            frames.append({"file": name, "frame_index": r["frame_index"], "timestamp_us": r["timestamp"],
                "pixel_sha256": pixel_sha, "sha256": digest(output / name),
                "width": int(frame.shape[1]), "height": int(frame.shape[0]), "is_t0": r is t0,
                "display_encoding": "NATIVE_RESOLUTION_JPEG_Q92_NOT_EXACT_PIXEL_BYTES"})
    finally:
        cap.release()
    return frames


def execute(output):
    audit, inputs = audit_inputs()
    scene, scene_inputs = source_example()
    inputs.update(scene_inputs)
    frames = image_assets(scene, output, inputs)
    source = load(ROOT / scene["annotation_path"])
    actor = next(a for a in source["annotation"]["agents"] if a["id"] == "Agent3")
    # Keep the original source object with its timestamp; never move its point to t0.
    packet = {"review_version": VERSION, "candidate_digest": scene["candidate_digest"], "review_index": 18,
        "event_timestamp_us": scene["event_timestamp_us"], "clip_id": scene["clip_id"], "upstream_split": "train",
        "coc": scene["coc"], "prior_observation": scene["prior_observation"], "source_anchor": actor["keypoints"][0],
        "source_anchor_display": {"authority": "CONTEXT_ONLY_NO_TIME_ALIGNMENT_ASSERTION",
            "source_declared_timestamp_us": 0, "display_frame_timestamp_us": frames[0]["timestamp_us"],
            "exact_time_match": frames[0]["timestamp_us"] == 0},
        "source_anchor_entity_id": "Agent3", "frames": frames,
        "machine_proposal": {"authority": "MODEL_VISUAL_PROPOSAL_REQUIRES_CONFIRMATION", "confidence": "LOW",
            "basis": "Assistant inspection of the pinned t0 overlay; no tracking or polygon ground truth.",
            "target_point": [0.386, 0.782], "zone_polygon": [[0.28,0.79],[0.58,0.76],[0.77,0.96],[0.22,0.96]]},
        "human_decisions_prefilled": False, "independent_gold_screen": False, "learning_export_allowed": False,
        "clock_alignment": "EXISTING_CROSS_DATASET_ANCHOR_NOT_INDEPENDENTLY_VERIFIED",
        "input_hashes": inputs}
    write_json(output / "source_review_packet.json", packet)
    packet_sha = digest(output / "source_review_packet.json")
    display = dict(packet)
    display["packet_sha256"] = packet_sha
    display["frames"] = [{**f, "data_url": "data:image/jpeg;base64,"+base64.b64encode((output/f["file"]).read_bytes()).decode()} for f in frames]
    html = TEMPLATE.read_text(encoding="utf-8")
    if html.count("__SOURCE_REVIEW_PACKET__") != 1:
        raise ValueError("template marker mismatch")
    (output / "scene18_source_binding_review.html").write_text(html.replace("__SOURCE_REVIEW_PACKET__", json_text(display)), encoding="utf-8")
    write_json(output / "source_acceptance_audit.json", audit)
    result = {"status": "MACHINE_SOURCE_ACCEPTANCE_AUDIT_COMPLETE_HUMAN_REVIEW_REQUIRED",
        "project_id": "guardsynth-coc", "candidate_count": 32, "existing_reviews_reused": 19, "deferred_count": 13,
        "reviewed_events_with_exported_polygons": sum(bool(r["retained_polygons"]) for r in audit["records"]),
        "reviewed_events_with_exact_person_points": sum(r["event_time_point_count"] > 0 for r in audit["records"]),
        "geometry_submission_records_with_coordinates": audit["geometry_submission_records_with_coordinates"],
        "source_review_scenes_requested": 1, "repeat_full_survey_requested": False,
        "past_only_frame_count": len(frames), "max_input_timestamp_us": max(f["timestamp_us"] for f in frames),
        "event_timestamp_us": scene["event_timestamp_us"], "packet_sha256": packet_sha,
        "source_verified_contracts": 0, "human_reviews_received": 0, "training_exports": 0,
        "independent_action_gold": None, "independent_cnl_audit": "PENDING", "input_hashes": inputs,
        "observation_counts": dict(Counter(r["prior_window_observation"] for r in audit["records"]))}
    write_json(output / "RESULT.json", result)
    (output / "REPORT_KO.md").write_text(
        "# 사건 근거 수용 준비 결과\n\n"
        "32개 후보 분모와 기존 관찰 19개/미관찰 13개를 유지하고, 원본 해시·시점·geometry 제출을 재검증했다. "
        "해당 geometry export 98개에는 실제 좌표가 없으며 이전 검토 완료는 취소하지 않았다. 브라우저에서 그린 적이 없다는 뜻은 아니다.\n\n"
        f"#18은 과거 프레임 {len(frames)}개(마지막 9,788,396us)를 원해상도 JPEG 표시본으로 만들고 t0 원본 픽셀은 PNG로 별도 보존했다. 사건 이후 프레임은 화면에 포함하지 않는다. "
        "첫 영상 프레임은 -111,570us이고 Agent3 점의 주석은 0초다. 두 시점은 동일하다고 가정하지 않으며 첫 프레임의 점은 context-only 참고 표시다. 현재 위치로 보간하지 않았다. 대상 점/영역은 확인 전 기계 초안이며 human truth는 빈 상태다.\n\n"
        "source 검토 화면은 한 장면만 다룬다. 확대/닫기, 모드별 좌표 수정, 자동저장, JSON 내보내기/불러오기를 제공한다. "
        "CoC/기존 답변이 보이므로 독립 행동 정답 검토가 아니다. 행동 gold 화면은 영역 확정 이후 별도 생성하며 독립 검토자 판단이 필요하다.\n\n"
        "자동으로 확정할 수 없는 대상 동일성·의미 영역·보행자/주도로 조건이 남아 사람 확인이 필요하다. 모름도 유효한 제출이며 학습 export는 차단된다.\n", encoding="utf-8")
    return result


def run(output, review=None, packet_path=None):
    if review is not None:
        if packet_path.name != "source_review_packet.json":
            raise ValueError("canonical source review packet required")
        packet_manifest = load(packet_path.parent / "RUN_MANIFEST.json")
        if (packet_manifest.get("project_id") != "guardsynth-coc" or packet_manifest.get("experiment_id") != EXPERIMENT
            or packet_manifest.get("status") != "MACHINE_SOURCE_ACCEPTANCE_AUDIT_COMPLETE_HUMAN_REVIEW_REQUIRED"):
            raise ValueError("packet manifest is not a completed source acceptance preparation")
        verified(packet_path, packet_manifest["output_hashes"][packet_path.name])
        packet = load(packet_path)
        if packet.get("review_version") != VERSION or packet.get("human_decisions_prefilled") is not False:
            raise ValueError("packet version/initial review state mismatch")
        for path, sha in packet["input_hashes"].items():
            verified(ROOT / path, sha)
        for frame in packet["frames"]:
            verified(packet_path.parent / frame["file"], frame["sha256"])
        verdict = validate_review(load(review), packet, digest(packet_path))
    output.mkdir(parents=True, exist_ok=False, mode=0o700)
    code = [Path(__file__).resolve(), TEMPLATE, Path(__file__).with_name("align_reviews.py"), Path(__file__).with_name("worked_example.py"),
        ROOT / "projects/04-guardsynth-coc/src/guard_synth/source_acceptance.py"]
    manifest = {"project_id": "guardsynth-coc", "experiment_id": EXPERIMENT, "run_id": output.name,
        "created_at_utc": datetime.now(timezone.utc).isoformat(), "status": "RUNNING", "network_used": False,
        "code_hashes": {str(p.relative_to(ROOT)): digest(p) for p in code}}
    write_json(output / "RUN_MANIFEST.json", manifest)
    try:
        if review is None:
            result = execute(output)
        else:
            # Intake is preserved separately; source acceptance never substitutes for gold/CNL audit.
            result = {**verdict, "input_hashes": {str(p): digest(p) for p in (review, packet_path)}}
            write_json(output / "review_submission.json", load(review))
            write_json(output / "RESULT.json", result)
        manifest.update(status=result["status"], input_hashes=result["input_hashes"])
    except Exception as exc:
        manifest["status"] = "FAILED"
        write_json(output / "RESULT.json", {"status": "FAILED", "error": f"{type(exc).__name__}: {exc}"})
        write_json(output / "RUN_MANIFEST.json", manifest)
        raise
    manifest["output_hashes"] = {p.name: digest(p) for p in sorted(output.iterdir()) if p.name != "RUN_MANIFEST.json"}
    write_json(output / "RUN_MANIFEST.json", manifest)
    for p in output.iterdir():
        p.chmod(0o600)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--review", type=Path)
    parser.add_argument("--packet", type=Path)
    args = parser.parse_args()
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*-[0-9]+", args.run_id) or bool(args.review) != bool(args.packet):
        parser.error("unused kebab-case run ID required; --review and --packet must be paired")
    output = BASE / EXPERIMENT / args.run_id
    result = run(output, args.review, args.packet)
    print(result["status"])
    print(output)


if __name__ == "__main__":
    main()
