"""Build a read-only source → observation → conditional-constraint correspondence."""

from __future__ import annotations

import argparse
import base64
from collections import Counter
import csv
from datetime import datetime, timezone
import hashlib
from html import escape
import importlib.util
import json
from pathlib import Path
import re
import sys

ROOT = next(p for p in Path(__file__).resolve().parents if (p / "PROJECT_REGISTRY.json").is_file())
sys.path[:0] = [str(ROOT), str(ROOT / "projects/04-guardsynth-coc/src")]
from guard_synth.review_constraint_alignment import ALIGNMENT_VERSION, align_reviewed_scene, index_records

BASE = ROOT / "artifacts/projects/guardsynth-coc/restricted"
ACQUISITION = BASE / "guardsynth-m16-scene-acquisition-001"
REVIEW = BASE / "guardsynth-m16-source-review-001/m16-source-review-2026-09-04-v1"
GEOMETRY = ACQUISITION / "m16-geometry-candidate-2026-09-05-v1"
SUBMISSION = ACQUISITION / "m16-geometry-curator-submission-2026-09-06-v1"
INVENTORY = BASE / "guardsynth-eblc-learning-001/paper1-source-audit-2026-09-06-002"
EXPERIMENT = "guardsynth-review-constraint-alignment-001"


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    path.chmod(0o600)


def pipeline(name, relative):
    path = ROOT / "projects/04-guardsynth-coc/pipelines/cli" / relative
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def verified(path, expected):
    if digest(path) != expected:
        raise ValueError(f"source hash changed: {path.name}")


def render_table(records, images):
    cards = []
    for row in records:
        obs = row["observation"]
        draft = row["draft"]
        text = draft["text_ko"] if draft else "관측 불가 답변을 보존하며 제약 초안을 보류합니다."
        fields = "".join(f"<tr><td>{escape(k)}</td><td>{escape(v)}</td></tr>" for k, v in row["field_correspondence"].items())
        issues = "".join(f"<li>{escape(i['detail'])} ({escape(i['owner'])})</li>" for i in row["issues"])
        image = images[row["candidate_digest"]]["image_data_url"]
        cards.append(f'''<details><summary>기존 #{row['review_index']:02d} · {escape(obs['visual_temporal_observation'])}</summary>
<p>원본 CoC: {escape(row['coc']['text'])}</p>
<p>기존 답변: {escape(obs['visual_association_observation'])} / {escape(obs['visual_temporal_observation'])}
 · 메모: {escape(obs['notes']) or '없음'}</p>
<p>Geometry 검토: {escape(row['geometry']['assessment'])} · 제출 polygon {row['geometry']['polygon_count']}개</p>
<button class="picture" type="button" title="이미지 확대"><img src="{image}" alt="기존 검토 시간창"></button>
<p class="draft">검토 기반 조건부 초안 — 검증된 EBLC/CNL 아님<br>{escape(text)}</p>
<table><thead><tr><th>EBLC 연결 대상</th><th>현재 상태</th></tr></thead><tbody>{fields}</tbody></table>
<p>EBLC 생성: 보류 · SAT: 미실행 · 학습 데이터 배포: 보류</p><ul>{issues}</ul>
<details><summary>출처와 전체 연결 정보</summary><pre>{escape(json.dumps(row,ensure_ascii=False,indent=2))}</pre></details>
</details>''')
    return '''<!doctype html><html lang="ko"><meta charset="utf-8"><title>기존 검토와 제약 대응표</title>
<style>body{font-family:system-ui;max-width:1500px;margin:24px auto;padding:0 20px;line-height:1.6}details{border:1px solid #bbb;padding:12px;margin:12px 0}summary{cursor:pointer;font-weight:600}table{border-collapse:collapse;width:100%}td,th{border:1px solid #ccc;padding:8px;text-align:left}.picture{width:100%;background:white;border:0;cursor:zoom-in}.picture img{width:100%}.draft{background:#fff5d8;padding:12px}pre{white-space:pre-wrap;overflow-wrap:anywhere}dialog{max-width:96vw;max-height:94vh}dialog img{width:90vw}dialog button{position:sticky;top:0;font-size:18px}</style>
<h1>기존 영상 검토 → 제약 대응표</h1><p>읽기 전용입니다. 새 설문이 아니며 기존 답변을 다시 작성할 필요가 없습니다.</p>
<p>32개 개발 후보 중 기존 영상 검토 19건을 연결했습니다. 남은 13건도 JSON/CSV 분모에 보존했습니다.
관찰은 전후 시간창에 대한 것이며, 검증된 사건 시점 정답이나 독립 모델 정확도 평가가 아닙니다.</p>
<p>이미지를 누르면 확대됩니다. 닫기 또는 Esc로 이 화면에 돌아옵니다.</p>''' + "".join(cards) + '''
<dialog id="zoom"><button id="close" type="button">닫기 · 대응표로 돌아가기</button><img alt="확대 영상"></dialog>
<script>const d=document.getElementById('zoom');document.querySelectorAll('.picture').forEach(b=>b.onclick=()=>{d.querySelector('img').src=b.querySelector('img').src;d.showModal()});document.getElementById('close').onclick=()=>d.close();</script></html>'''


def execute(output):
    import pyarrow.parquet as pq
    review_validator = pipeline("alignment_video_validator", "m16_source_review_portal/finalize_review.py")
    geometry_validator = pipeline("alignment_geometry_validator", "m16_scene_acquisition/finalize_geometry_curator_review.py")
    json_path = REVIEW / "m16_video_observation_review.json"
    csv_path = json_path.with_suffix(".csv")
    packet_path = review_validator.DEFAULT_PACKET
    html_path = review_validator.DEFAULT_SOURCE_HTML
    review_summary = review_validator.validate_review_export(json_path, csv_path, packet_path, html_path)
    html_manifest = load(html_path.parent / "RUN_MANIFEST.json")
    verified(html_path, html_manifest["html_sha256"])
    observations = index_records(load(json_path)["records"])
    images = index_records(review_validator._embedded_review_data(html_path)["records"])
    for record in images.values():
        data = base64.b64decode(record["image_data_url"].split(",", 1)[1], validate=True)
        if hashlib.sha256(data).hexdigest() != record["image_sha256"]:
            raise ValueError("review image bytes hash mismatch")

    geometry_path = GEOMETRY / "GEOMETRY_CANDIDATE_MANIFEST.json"
    geometry_manifest = load(geometry_path)
    verified(geometry_path, load(GEOMETRY / "RUN_MANIFEST.json")["output_hashes"]["geometry_candidate_manifest"])
    geometry_json = SUBMISSION / "m16_geometry_candidate_review (1).json"
    geometry_csv = geometry_json.with_suffix(".csv")
    geometry_export = load(geometry_json)
    verified(geometry_path, geometry_export["manifest_sha256"])
    geometry_records = [geometry_validator._normalize_json_record(r) for r in geometry_export["records"]]
    if geometry_records != geometry_validator._load_csv(geometry_csv):
        raise ValueError("geometry JSON/CSV mismatch")
    geometry_validator._validate_records(candidate_records=geometry_manifest["records"], review_records=geometry_records,
                                         curator_id="Jin Hyun Kim")
    geometries = index_records(geometry_records)
    geometry_candidates = index_records(geometry_manifest["records"])

    inventory_path = INVENTORY / "source_audit.json"
    verified(inventory_path, load(INVENTORY / "RUN_MANIFEST.json")["output_hashes"]["source_audit.json"])
    scenes = [r for r in load(inventory_path) if r["selected_development_family"]]
    if len(scenes) != 32 or len(index_records(scenes)) != 32:
        raise ValueError("selected development cohort drift")
    structured_path = ACQUISITION / "m16-cascade-structured-link-audit-2026-09-05-v1/CASCADE_STRUCTURED_LINK_AUDIT.json"
    verified(structured_path, load(INVENTORY / "RESULT.json")["input_hashes"][str(structured_path.relative_to(ROOT))])
    structured = index_records(load(structured_path)["records"])
    authority_path = ACQUISITION / "m16-treaty-authority-binding-2026-09-06-v2/TREATY_AUTHORITY_AUDIT.json"
    verified(authority_path, load(authority_path.parent / "RUN_MANIFEST.json")["output_hashes"]["treaty_authority_audit"])
    authorities = index_records(load(authority_path)["records"])
    reasoning_path = ROOT / "data/restricted/nvidia_physicalai/reasoning/ood_reasoning.parquet"
    verified(reasoning_path, load(INVENTORY / "RESULT.json")["input_hashes"][str(reasoning_path.relative_to(ROOT))])
    coc_index = {}
    for clip in pq.read_table(reasoning_path).to_pylist():
        for event in json.loads(clip["events"] or "[]"):
            key = (clip["clip_id"], int(event["event_start_timestamp"]))
            coc_index.setdefault(key, []).append(event["coc"])
    input_paths = [json_path, csv_path, packet_path, html_path, geometry_path, geometry_json, geometry_csv,
                   inventory_path, structured_path, authority_path, reasoning_path]
    hashes = {str(p.relative_to(ROOT)): digest(p) for p in input_paths}
    refs = {name: f"sha256:{digest(path)}" for name, path in (
        ("observation", json_path), ("geometry", geometry_json), ("structured", structured_path),
        ("authority", authority_path), ("coc", reasoning_path))}
    rows = []
    deferred = []
    for scene in scenes:
        key = scene["candidate_digest"]
        if key not in observations:
            deferred.append({"candidate_digest": key, "group_id": scene["group_id"],
                             "status": "NO_PRIOR_VIDEO_OBSERVATION_SOURCE_FIRST",
                             "geometry_review_completed": key in geometries,
                             "learning_export_allowed": False, "repeat_existing_survey_requested": False})
            continue
        matches = coc_index[(scene["group_id"], int(scene["event_timestamp_us"]))]
        if len(matches) != 1:
            raise ValueError("CoC event ambiguous")
        # Verify actual files behind all five frames, not only metadata strings.
        candidate = geometry_candidates[key]
        for frame in candidate["frames"]:
            for kind in ("overlay", "drivable_mask", "lane_mask"):
                path = GEOMETRY / frame[f"{kind}_path"]
                verified(path, frame[f"{kind}_sha256"])
                hashes[str(path.relative_to(ROOT))] = frame[f"{kind}_sha256"]
        source_refs = {name: value + f"#candidate={key}" for name, value in refs.items()}
        source_refs["coc"] = refs["coc"] + f"#clip={scene['group_id']}&event_timestamp_us={scene['event_timestamp_us']}"
        row = align_reviewed_scene(scene=scene, coc=matches[0], observation=observations[key],
            geometry=geometries[key], structured=structured[key], authority=authorities[key], evidence_refs=source_refs)
        row["observation_frame_offsets_s"] = images[key]["frame_offsets_s"]
        row["geometry_frame_timestamps_us"] = [f["timestamp_us"] for f in candidate["frames"]]
        rows.append(row)
    rows.sort(key=lambda r: r["review_index"])
    if len(rows) != 19 or len(deferred) != 13:
        raise ValueError("review reuse count drift")
    write_json(output / "scene_constraint_alignment.json", {"records": rows, "deferred_records": deferred})
    with (output / "scene_constraint_alignment.csv").open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["review_index", "candidate_digest", "observation", "coc", "draft_kind", "draft", "eblc_status", "sat_status"])
        for row in rows:
            d = row["draft"] or {}
            writer.writerow([row["review_index"], row["candidate_digest"], row["observation"]["visual_temporal_observation"],
                row["coc"]["text"], d.get("kind", "ABSTAIN"), d.get("text_ko", ""), row["eblc_preflight"]["status"], "NOT_RUN"])
        for row in deferred:
            writer.writerow(["", row["candidate_digest"], row["status"], "", "DEFERRED", "", "NOT_ATTEMPTED", "NOT_RUN"])
    (output / "review_constraint_alignment.html").write_text(render_table(rows, images), encoding="utf-8")
    result = {
        "status": "PRIOR_REVIEW_ALIGNMENT_COMPLETE_EXECUTABLE_BINDING_PENDING",
        "candidate_count": 32, "prior_observation_reused_count": len(rows), "no_prior_observation_count": len(deferred),
        "observation_counts": dict(Counter(r["observation"]["visual_temporal_observation"] for r in rows)),
        "conditional_draft_count": sum(r["draft"] is not None for r in rows),
        "unobservable_abstention_count": sum(r["draft"] is None for r in rows),
        "mixed_work_or_control_context_count": sum(r["coc"]["mixed_work_or_control_context"] for r in rows),
        "executable_eblc_count": 0, "sat_query_count": 0, "verified_cnl_count": 0,
        "repeat_existing_survey_requested_count": 0, "independent_accuracy": "NOT_EVALUATED",
        "paper_cohort_eligibility": "NOT_EVALUATED", "learning_export_count": 0,
        "claim_scope": "REUSE_OF_HUMAN_OBSERVATIONS_AND_CONDITIONAL_DRAFTS_NOT_VERIFIED_EBLC_OR_MODEL_ACCURACY",
        "review_integrity": review_summary, "input_hashes": hashes,
    }
    write_json(output / "RESULT.json", result)
    (output / "REPORT_KO.md").write_text(
        "# 기존 검토와 실제 장면 제약 연결 결과\n\n"
        f"기존 19건 재사용, 후보 32건 분모 유지, 조건부 초안 {result['conditional_draft_count']}건.\n\n"
        "초안은 기존 관찰을 구조화한 것이며 독립 모델 예측이나 검증된 EBLC/CNL이 아니다. "
        "정확한 대상·영역 binding, 사건 시점 predicate, operational clause 및 기존 numeric backend의 "
        "수치 근거가 없어 EBLC 생성·SAT·CNL renderer는 실행하지 않았다.\n\n"
        f"기존 관찰 분포: {json.dumps(result['observation_counts'], ensure_ascii=False)}. "
        "전이 메모를 시점별 release 정답으로 승격하거나, 위험이 보이지 않음을 진행 허가로 바꾸지 않았다.\n\n"
        "다음은 재설문이 아니라 CASCADE 대상과 검토 영역의 연결, 시간창/시점 근거 분리, "
        "공사 인력·교통 통제가 섞인 CoC의 적용 제약을 구분하는 작업이다.\n", encoding="utf-8")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*-[0-9]+", args.run_id):
        parser.error("run-id must be kebab-case ending in a number")
    output = BASE / EXPERIMENT / args.run_id
    output.mkdir(parents=True, exist_ok=False, mode=0o700)
    manifest = {"project_id": "guardsynth-coc", "experiment_id": EXPERIMENT, "run_id": args.run_id,
                "alignment_version": ALIGNMENT_VERSION, "created_at_utc": datetime.now(timezone.utc).isoformat(),
                "network_used": False, "status": "RUNNING", "code_hashes": {str(p.relative_to(ROOT)): digest(p) for p in (
                    Path(__file__).resolve(), ROOT / "projects/04-guardsynth-coc/src/guard_synth/review_constraint_alignment.py",
                    ROOT / "projects/04-guardsynth-coc/pipelines/cli/m16_source_review_portal/finalize_review.py",
                    ROOT / "projects/04-guardsynth-coc/pipelines/cli/m16_scene_acquisition/finalize_geometry_curator_review.py")}}
    write_json(output / "RUN_MANIFEST.json", manifest)
    try:
        result = execute(output)
    except Exception as exc:
        result = {"status": "FAILED", "error": f"{type(exc).__name__}: {exc}"}
        write_json(output / "RESULT.json", result)
        manifest["status"] = "FAILED"; write_json(output / "RUN_MANIFEST.json", manifest)
        raise
    manifest["status"] = result["status"]
    manifest["output_hashes"] = {p.name: digest(p) for p in output.iterdir() if p.is_file() and p.name != "RUN_MANIFEST.json"}
    write_json(output / "RUN_MANIFEST.json", manifest)
    for path in output.iterdir():
        if path.is_file():
            path.chmod(0o600)
    print(json.dumps({k: v for k, v in result.items() if k not in {"input_hashes", "review_integrity"}}, ensure_ascii=False, indent=2))
    print(str(output))


if __name__ == "__main__":
    main()
