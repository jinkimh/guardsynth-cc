"""Reproduce the scene-18 paper illustration, not an executable EBLC export."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from html import escape
import json
import os
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from align_reviews import ROOT, BASE, ACQUISITION, digest, load, verified, write_json

EXPERIMENT = "guardsynth-paper-worked-example-001"
PRIOR = BASE / "guardsynth-review-constraint-alignment-001"
BINDING = PRIOR / "event-source-binding-2026-09-07-002"
ALIGNMENT = PRIOR / "reviewed-scene-alignment-2026-09-07-001"
GEOMETRY = ACQUISITION / "m16-geometry-candidate-2026-09-05-v1"

# Manually authored semantic/CNL pairs for this illustration only. This is not
# a general EBLC renderer and does not attest independent semantic fidelity.
CLAUSES = [
    {"id": "C1", "formula": "on_t = valid_p_t AND p_t=TRUE; clear_t = valid_p_t AND p_t=FALSE",
     "cnl": "A pedestrian conflict is confirmed if and only if its truth is TRUE and its evidence is valid. Conflict clearance is confirmed if and only if its truth is FALSE and its evidence is valid."},
    {"id": "C2", "formula": "active_t = ITE(on_t, TRUE, ITE(clear_t, FALSE, previous_active_t))",
     "cnl": "Activate the pedestrian obligation when conflict is confirmed. Deactivate it when clearance is confirmed. Otherwise retain its previous activation state. Apply this rule again at each decision, including after release."},
    {"id": "C3", "formula": "review_t = (p_t=CONFLICT) OR (NOT(on_t OR clear_t) AND NOT previous_active_t)",
     "cnl": "Mark review as required when pedestrian evidence is conflicting, or when neither conflict nor clearance is confirmed and the previous activation state is inactive. Otherwise do not set this review flag."},
    {"id": "C4", "formula": "active_t IMPLIES NOT enter_t",
     "cnl": "While the pedestrian obligation is active, do not enter the conflict zone."},
    {"id": "C5", "formula": "(valid_r_t AND r_t=TRUE) IMPLIES NOT enter_t",
     "cnl": "Do not enter the conflict zone when a main-road yielding obligation is confirmed by valid evidence, regardless of the pedestrian obligation's activation state."},
]
GAP_NOTE = "The draft does not constrain entry solely because a review flag is set or a yielding condition is UNKNOWN. These are unresolved policy gaps, not permission or safety findings."


def build_model():
    import z3
    T, F, U, C = range(4)
    prior = z3.Bool("previously_active")
    names = {"p": "ped_truth", "vp": "ped_evidence_valid", "r": "road_yield_required",
             "vr": "road_evidence_valid", "a": "ped_active", "e": "enter_conflict_zone", "q": "ped_review_required"}
    v = {k: [(z3.Int if k in {"p", "r"} else z3.Bool)(f"{name}_{i}") for i in range(3)] for k, name in names.items()}
    clauses = {"DOMAIN": [], **{c["id"]: [] for c in CLAUSES if c["id"] != "C1"}}
    for i in range(3):
        prev = prior if i == 0 else v["a"][i-1]
        on = z3.And(v["vp"][i], v["p"][i] == T)
        clear = z3.And(v["vp"][i], v["p"][i] == F)
        clauses["DOMAIN"] += [v["p"][i] >= T, v["p"][i] <= C, v["r"][i] >= T, v["r"][i] <= C]
        clauses["C2"].append(v["a"][i] == z3.If(on, True, z3.If(clear, False, prev)))
        clauses["C3"].append(v["q"][i] == z3.Or(v["p"][i] == C, z3.And(z3.Not(z3.Or(on, clear)), z3.Not(prev))))
        clauses["C4"].append(z3.Implies(v["a"][i], z3.Not(v["e"][i])))
        clauses["C5"].append(z3.Implies(z3.And(v["vr"][i], v["r"][i] == T), z3.Not(v["e"][i])))
    p, vp, r, vr, a, e, q = (v[k] for k in ("p", "vp", "r", "vr", "a", "e", "q"))
    cases = [
        ("q01_consistency", [], z3.BoolVal(True), "sat", None),
        ("q02_conflict_entry", [p[0] == T, vp[0]], e[0], "unsat", None),
        ("q03_unknown_release", [prior, p[0] == U, vp[0]], z3.Not(a[0]), "unsat", None),
        ("q04_stale_release", [prior, p[0] == F, z3.Not(vp[0])], z3.Not(a[0]), "unsat", None),
        ("q05_clear_and_wait", [prior, p[0] == F, vp[0]], z3.And(z3.Not(a[0]), z3.Not(e[0])), "sat", None),
        ("q06_other_yield", [prior, p[0] == F, vp[0], r[0] == T, vr[0]], e[0], "unsat", None),
        ("q07_reactivation", [z3.Not(prior), p[0] == T, p[1] == F, p[2] == T, *vp], z3.Not(a[2]), "unsat", None),
        ("q08_nominal_entry", [p[0] == F, vp[0], r[0] == F, vr[0]], e[0], "sat", None),
        ("q09_gap_unknown_person", [z3.Not(prior), p[0] == U, vp[0], r[0] == F, vr[0]], z3.And(q[0], e[0]), "sat", None),
        ("q10_gap_unknown_road", [p[0] == F, vp[0], r[0] == U, vr[0]], e[0], "sat", None),
        ("q11_mutation_no_entry_rule", [p[0] == T, vp[0], r[0] == F, vr[0]], e[0], "sat", "C4"),
    ]
    return prior, v, clauses, cases


def run_queries(output):
    import z3
    prior, variables, clauses, cases = build_model()
    results = []
    for name, premises, probe, expected, omitted in cases:
        s = z3.Solver()
        s.set(timeout=10000)
        s.add(*(f for cid, formulas in clauses.items() if cid != omitted for f in formulas), *premises)
        # Each UNSAT test gets a separate satisfiable-premise check to avoid vacuity.
        (output / f"{name}_premises.smt2").write_text(s.to_smt2(), encoding="utf-8")
        premise_result = str(s.check())
        if premise_result != "sat":
            raise ValueError(f"{name}: invalid premise result {premise_result}")
        s.add(probe)
        (output / f"{name}.smt2").write_text(s.to_smt2(), encoding="utf-8")
        status = str(s.check())
        if status != expected:
            raise ValueError(f"{name}: unexpected result {status}")
        record = {"query_id": name, "premises_status": premise_result.upper(), "status": status.upper(),
                  "expected": expected.upper(), "omitted_clause": omitted,
                  "probe": probe.sexpr(), "premises": [p.sexpr() for p in premises]}
        if status == "sat":
            model = s.model()
            record["witness"] = {str(x): str(model.eval(x, model_completion=True))
                for x in [prior] + [x for xs in variables.values() for x in xs]}
        results.append(record)
    return results


def source_example():
    import pyarrow.parquet as pq
    hashes = {}
    def pinned(path, expected):
        verified(path, expected)
        hashes[str(path.relative_to(ROOT))] = expected
        return load(path)
    bindings = pinned(BINDING / "event_source_bindings.json", load(BINDING / "RUN_MANIFEST.json")["output_hashes"]["event_source_bindings.json"])
    row = next(r for r in bindings["records"] if r["review_index"] == 18)
    alignment = pinned(ALIGNMENT / "scene_constraint_alignment.json", load(ALIGNMENT / "RUN_MANIFEST.json")["output_hashes"]["scene_constraint_alignment.json"])
    old = next(r for r in alignment["records"] if r["candidate_digest"] == row["candidate_digest"])
    annotation = pinned(ROOT / row["annotation_path"], row["annotation_sha256"])
    if annotation["video"]["clip_id"] != row["group_id"]:
        raise ValueError("annotation video mismatch")
    parquet = ROOT / "data/restricted/nvidia_physicalai/reasoning/ood_reasoning.parquet"
    expected = load(BINDING / "RESULT.json")["input_hashes"][str(parquet.relative_to(ROOT))]
    verified(parquet, expected)
    hashes[str(parquet.relative_to(ROOT))] = expected
    events = [e for clip in pq.read_table(parquet, filters=[("clip_id", "=", row["group_id"])]).to_pylist()
              for e in json.loads(clip["events"] or "[]") if int(e["event_start_timestamp"]) == row["event_timestamp_us"]]
    if len(events) != 1 or events[0]["coc"] != row["coc"]["text"]:
        raise ValueError("original CoC mismatch")
    geometry = pinned(GEOMETRY / "GEOMETRY_CANDIDATE_MANIFEST.json", load(GEOMETRY / "RUN_MANIFEST.json")["output_hashes"]["geometry_candidate_manifest"])
    geo = next(r for r in geometry["records"] if r["candidate_digest"] == row["candidate_digest"])
    frame = next(f for f in geo["frames"] if f["offset_s"] == 0)
    image = GEOMETRY / frame["overlay_path"]
    verified(image, frame["overlay_sha256"])
    hashes[str(image.relative_to(ROOT))] = frame["overlay_sha256"]
    video = ROOT / "data/restricted/nvidia_physicalai/internal-derived/m16-shortlist-v1" / ("event-" + row["candidate_digest"].split(":")[1]) / "camera_front_wide_120fov/video.mp4"
    verified(video, geo["source_video_sha256"])
    hashes[str(video.relative_to(ROOT))] = geo["source_video_sha256"]
    return {"review_index": 18, "geometry_folder_index": 26, "candidate_digest": row["candidate_digest"],
        "clip_id": row["group_id"], "event_timestamp_us": row["event_timestamp_us"], "upstream_split": row["upstream_split"],
        "coc": events[0]["coc"], "reasoning_event_start_frame": events[0]["event_start_frame"],
        "decoded_video_frame_index": frame["frame_index"], "decoded_video_timestamp_us": frame["timestamp_us"],
        "prior_observation": row["prior_observation"], "authority": old["authority"],
        "annotation_path": row["annotation_path"], "source_linked_person_ids": row["source_linked_person_ids"],
        "active_source_targets": row["active_source_targets"], "active_ego_actions": row["active_ego_actions"],
        "display_overlay": str(image.relative_to(ROOT)), "raw_video": str(video.relative_to(ROOT)),
        "source_complete": False, "publication_clearance": "NOT_ESTABLISHED"}, hashes


def execute(output):
    import z3
    scene, hashes = source_example()
    results = run_queries(output)
    write_json(output / "source_example.json", scene)
    cnl = "\n".join(f"[{c['id']}] {c['cnl']}" for c in CLAUSES)
    write_json(output / "cnl_correspondence.json", {"clauses": CLAUSES, "text": cnl, "gap_note": GAP_NOTE,
        "production_method": "MANUALLY_AUTHORED_PAIRS_DETERMINISTIC_ASSEMBLY_NOT_GENERAL_EBLC_RENDERER",
        "independent_semantic_audit": "PENDING"})
    write_json(output / "eblc_design_draft.json", {"status": "NON_EXECUTABLE_EBLC_DESIGN_PROJECTION",
        "not_an_accepted_eblc_program_schema": True, "subject": "ego", "target_candidate": "Agent3",
        "target_identity_confirmed": "UNKNOWN", "conflict_zone": None, "event_hazard_truth": "UNKNOWN",
        "normative_reference": "1968-ROAD-TRAFFIC:21", "operational_policy": "ILLUSTRATIVE_RESEARCH_PROPOSAL_NOT_APPROVED",
        "truth_domain": {"TRUE": 0, "FALSE": 1, "UNKNOWN": 2, "CONFLICT": 3},
        "horizon": 3, "time_meaning": "ABSTRACT_DECISIONS_NOT_VIDEO_FRAMES", "clauses": CLAUSES,
        "semantic_interpretation": "On unresolved or conflicting evidence retain previous activation; C3 reports review but does not block entry."})
    common_input = {"raw_video": scene["raw_video"], "decision_timestamp_us": scene["event_timestamp_us"],
        "frame_sampling": "NOT_FROZEN_PAST_AND_PRESENT_ONLY", "display_overlay_allowed": False,
        "question": "Explain the scene and relevant constraints, then select an action.",
        "illustrative_choices": {"A": "Wait outside the conflict zone", "B": "Enter the conflict zone"}}
    write_json(output / "training_example_preview.json", {
        "status": "ILLUSTRATIVE_NOT_TRAINABLE", "learning_export_allowed": False,
        "common_input": common_input, "action_gold": None,
        "original_target_components": {"coc": scene["coc"], "action": None},
        "enriched_target_components": {"coc": scene["coc"], "constraints": cnl, "action": None},
        "finalized_assistant_target": None, "is_validated_L3_example": False,
        "blockers": ["SOURCE_BINDING_INCOMPLETE", "UNKNOWN_POLICY_GAPS", "NO_EBLC_FRONTEND_FOR_THIS_DRAFT",
                     "CNL_SEMANTIC_AUDIT_PENDING", "ACTION_CONTRACT_AND_INDEPENDENT_GOLD_PENDING"]})
    result = {"status": "WORKED_EXAMPLE_REPRODUCED_WITH_EXPLICIT_GAPS", "project_id": "guardsynth-coc",
        "solver": "Z3", "solver_version": z3.get_version_string(), "horizon": 3,
        "query_count": len(results), "premise_sat_count": sum(r["premises_status"] == "SAT" for r in results),
        "sat_count": sum(r["status"] == "SAT" for r in results), "unsat_count": sum(r["status"] == "UNSAT" for r in results),
        "gap_queries": [r["query_id"] for r in results if "gap" in r["query_id"]], "queries": results,
        "eblc_frontend_executed": False, "real_scene_safety_verified": False,
        "training_export_count": 0, "learning_effect": "NOT_EVALUATED", "input_hashes": hashes}
    write_json(output / "RESULT.json", result)
    image_ref = os.path.relpath(ROOT / scene["display_overlay"], output)
    rows = "".join(f"<tr><td>{escape(r['query_id'])}</td><td>{r['premises_status']}</td><td>{r['status']}</td></tr>" for r in results)
    html = f'''<!doctype html><html lang="ko"><meta charset="utf-8"><title>#18 논문 예제</title>
<style>body{{font:17px/1.6 system-ui;max-width:1250px;margin:24px auto;padding:16px}}img{{width:100%}}pre{{white-space:pre-wrap;overflow-wrap:anywhere}}td,th{{border:1px solid #aaa;padding:6px}}table{{border-collapse:collapse}}dialog{{max-width:96vw;max-height:95vh}}dialog img{{width:90vw}}button{{cursor:pointer}}</style>
<h1>#18: CoC → 조건부 제약 → 논리 검증 → CNL → 학습 미리보기</h1>
<p>실제 source와 수작업 명세를 결합한 방법 설명용 예제. 자동 추출·EBLC frontend·실제 장면 안전·학습 효과의 검증 결과가 아닙니다.</p>
<button id="picture"><img src="{escape(image_ref)}" alt="#18 표시 이미지"></button>
<p>녹색은 기계 road 후보이며 ego lane/충돌 영역 확정이 아닙니다. 이미지 재배포 권한은 미확인입니다.</p>
<h2>1. 원본 CoC와 근거</h2><blockquote>{escape(scene['coc'])}</blockquote>
<pre>{escape(json.dumps(scene,ensure_ascii=False,indent=2))}</pre>
<h2>2–3. 수작업 명세와 실제 Z3 결과</h2><p>모든 전제는 별도로 SAT를 확인했습니다. UNKNOWN 반례는 숨기지 않았습니다.</p>
<table><tr><th>질의</th><th>전제</th><th>결과</th></tr>{rows}</table>
<p><a href="eblc_design_draft.json">명세 초안</a> · <a href="RESULT.json">전체 결과·반례</a></p>
<h2>4. 조항 대응 CNL</h2><pre>{escape(cnl)}</pre><p>{escape(GAP_NOTE)}</p>
<h2>5. 학습 데이터 미리보기</h2><p>원본 CoC + CNL + 독립 행동 정답을 assistant supervision으로 사용합니다. 현재 정답은 null이며 학습 export는 차단되어 있습니다.</p>
<p><a href="training_example_preview.json">입력/출력 구조 보기</a></p>
<dialog id="zoom"><button id="close">닫기 · 예제로 돌아가기</button><img src="{escape(image_ref)}" alt="확대 이미지"></dialog>
<script>const d=document.getElementById('zoom');document.getElementById('picture').onclick=()=>d.showModal();document.getElementById('close').onclick=()=>d.close();</script></html>'''
    (output / "worked_example.html").write_text(html, encoding="utf-8")
    (output / "REPORT_KO.md").write_text(
        "# 논문 예제 실행 결과\n\n#18의 원본 CoC·CASCADE·영상/표시 이미지 해시를 확인하고, 대화의 수작업 논리 모델을 재실행했다.\n\n"
        f"Z3 {z3.get_version_string()}, 3 abstract decisions, 11개 질의: SAT 6 / UNSAT 5, 모든 전제 SAT. "
        "UNKNOWN 초기 상태/다른 의무의 미확정 상태에서 진입하는 반례 2개를 보존했다. "
        "진입 금지 조항을 제거하는 mutation은 SAT로 위반을 재현했다.\n\n"
        "CNL은 수작업으로 작성한 조항 대응 문장의 결정론적 조립이며 기존 EBLC renderer 실행이 아니다. "
        "학습 preview의 action=null, finalized target=null, export=false. 실제 장면의 안전이나 학습 효과는 미판정이다.\n",
        encoding="utf-8")
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
        "created_at_utc": datetime.now(timezone.utc).isoformat(), "status": "RUNNING", "network_used": False,
        "code_hashes": {str(p.relative_to(ROOT)): digest(p) for p in (Path(__file__).resolve(), Path(__file__).with_name("align_reviews.py"))}}
    write_json(output / "RUN_MANIFEST.json", manifest)
    try:
        result = execute(output)
    except Exception as exc:
        manifest["status"] = "FAILED"
        write_json(output / "RESULT.json", {"status": "FAILED", "error": f"{type(exc).__name__}: {exc}"})
        write_json(output / "RUN_MANIFEST.json", manifest)
        raise
    manifest["status"] = result["status"]
    manifest["output_hashes"] = {p.name: digest(p) for p in output.iterdir() if p.name != "RUN_MANIFEST.json"}
    write_json(output / "RUN_MANIFEST.json", manifest)
    for path in output.iterdir():
        path.chmod(0o600)
    print(json.dumps({k: v for k, v in result.items() if k not in {"queries", "input_hashes"}}, indent=2))
    print(output)


if __name__ == "__main__":
    main()
