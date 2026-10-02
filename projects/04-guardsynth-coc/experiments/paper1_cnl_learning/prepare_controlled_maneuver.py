"""WITHDRAWN, unexecuted hypothetical-task prototype; primary study preserves original CoC."""

import argparse
import base64
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

ROOT = next(p for p in Path(__file__).resolve().parents if (p / "PROJECT_REGISTRY.json").is_file())
BASE = ROOT / "artifacts/projects/guardsynth-coc/restricted/guardsynth-paper1-training-readiness-001"
SOURCE = BASE / "source-gap-ui-2026-09-09-002"
PARENT = BASE / "conditional-candidates-2026-09-08-002"
DESIGN = ROOT / "projects/04-guardsynth-coc/docs/designs/PAPER1_CONTROLLED_MANEUVER_TASK_DESIGN_V01.md"
VERSION = "controlled-maneuver-v0.1"
INSTRUCTIONS = {
    "STRAIGHT": "가정: 에고 차량은 현재 차로에서 차로 변경이나 좌·우회전 없이 전방의 직진 경로로 진행하려고 합니다.",
    "RIGHT_TURN": "가정: 에고 차량은 바로 앞에 보이는 우회전 갈림길로 진행하려고 합니다.",
}
FITS = {"CLEAR", "NO_VISIBLE_ROUTE", "AMBIGUOUS"}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()


def task_for(scene):
    raise RuntimeError("WITHDRAWN: arbitrary maneuver assignment is not the original CoC study")
    clip = scene["clip_id"]
    assignment = sha((VERSION + '|' + clip).encode())
    maneuver = "STRAIGHT" if int(assignment[:2], 16) % 2 == 0 else "RIGHT_TURN"
    task_id = "task-" + sha(f"{VERSION}|{clip}|{scene['event_timestamp_us']}".encode())[:16]
    frames = []
    for f in scene["frames"]:
        if f["timestamp_us"] > scene["event_timestamp_us"]:
            raise ValueError("future frame")
        prefix = "data:image/jpeg;base64,"
        if not f["data_url"].startswith(prefix) or sha(base64.b64decode(f["data_url"][len(prefix):], validate=True)) != f["sha256"]:
            raise ValueError("image identity mismatch")
        frames.append({"timestamp_us": f["timestamp_us"], "sha256": f["sha256"]})
    if not frames or frames != sorted(frames, key=lambda f: f["timestamp_us"]):
        raise ValueError("missing/unordered frames")
    return {
        "task_version": VERSION, "task_id": task_id, "maneuver": maneuver,
        "instruction_ko": INSTRUCTIONS[maneuver], "event_timestamp_us": scene["event_timestamp_us"],
        "frames": frames, "intent_source": "EXPLICIT_HYPOTHETICAL_TASK_NOT_RECORDED_INTENT",
        "decision_scope": "NEXT_QUALITATIVE_DECISION_NOT_METRIC_ROLLOUT",
        "scene_fit": None, "context_frozen": False, "independent_action": None,
        "source_rebinding_required": True, "coc_context_check_required": True,
        "training_allowed": False,
    }


def validate_fit_submission(raw, packet, packet_sha):
    if not isinstance(raw, dict) or set(raw) != {"review_version", "packet_sha256", "reviewer_id", "records"}:
        raise ValueError("submission fields mismatch")
    if raw["review_version"] != packet["review_version"] or raw["packet_sha256"] != packet_sha:
        raise ValueError("different context packet")
    if not isinstance(raw["reviewer_id"], str) or not raw["reviewer_id"].strip() or len(raw["reviewer_id"]) > 8000:
        raise ValueError("missing reviewer")
    expected = {t["task_id"] for t in packet["tasks"]}
    if not isinstance(raw["records"], list) or len(raw["records"]) != len(expected):
        raise ValueError("all pilot tasks required")
    seen = set()
    for r in raw["records"]:
        if not isinstance(r, dict) or set(r) != {"task_id", "fit", "description", "reviewed_at"}:
            raise ValueError("record fields mismatch")
        if not isinstance(r["task_id"], str) or r["task_id"] not in expected or r["task_id"] in seen:
            raise ValueError("unknown/duplicate task")
        seen.add(r["task_id"])
        if r["fit"] not in FITS or not isinstance(r["description"], str) or not r["description"].strip() or len(r["description"]) > 8000:
            raise ValueError("fit and description required")
        if not isinstance(r["reviewed_at"], str) or datetime.fromisoformat(r["reviewed_at"].replace('Z', '+00:00')).tzinfo is None:
            raise ValueError("completion time with timezone required")
    return {"format_valid": True, "fit_counts": dict(Counter(r["fit"] for r in raw["records"])),
            "action_dispatch_allowed": False, "context_frozen": False, "learning_export_allowed": False,
            "scope": "COORDINATOR_FEEDBACK_REQUIRES_CUE_AND_APPLICABILITY_AUDIT"}


def prepare(output):
    raise RuntimeError("WITHDRAWN: use original CoC context audit; no output may be generated")
    if output.exists():
        raise FileExistsError(output)
    inputs = {}
    def pin(path, expected=None):
        data = path.read_bytes()
        if expected is not None and sha(data) != expected:
            raise ValueError("input hash mismatch")
        inputs[str(path.relative_to(ROOT))] = sha(data)
        return data
    def load_run(run, name):
        m = json.loads(pin(run / 'RUN_MANIFEST.json'))
        return json.loads(pin(run / name, m['output_hashes'][name]))
    source = load_run(SOURCE, 'source_gap_packet.json')
    rows = load_run(PARENT, 'candidate_readiness.json')['records']
    pin(DESIGN)
    scenes = source['scenes']
    drafts = [(task_for(s), s) for s in scenes]
    selected, clips = [], set()
    for task, scene in sorted(drafts, key=lambda pair: pair[0]['task_id']):
        if scene['clip_id'] not in clips and len(selected) < 3:
            selected.append((task, scene))
            clips.add(scene['clip_id'])
    if len(drafts) != 30 or len(rows) != 32 or len(selected) != 3:
        raise ValueError("development denominator mismatch")
    packet = {"review_version": "controlled-context-fit-review-v0.1", "kind": "CONTEXT_FIT_NOT_ACTION",
              "tasks": [t for t, _ in selected], "fit_choices": sorted(FITS),
              "method_approval": "USER_CONFIRMED", "scene_acceptance": False}
    packet_bytes = canonical(packet)
    packet_sha = sha(packet_bytes)
    display = {**packet, "packet_sha256": packet_sha,
               "images": {t['task_id']: [f['data_url'] for f in s['frames']] for t, s in selected}}
    by_candidate = {s['candidate_digest']: t for t, s in drafts}
    ledger = []
    for row in rows:
        t = by_candidate.get(row['candidate_digest'])
        ledger.append({"candidate_digest": row['candidate_digest'], "candidate_index": row['geometry_index'],
                       "clip_id": row['clip_id'], "task_id": t['task_id'] if t else None,
                       "disposition": "CONTEXT_DRAFT" if t else "HISTORICAL_NOT_RE_REQUESTED",
                       "main_test_allowed": False})
    result = {"project_id": "guardsynth-coc", "status": "METHOD_APPROVED_CONTEXT_FIT_PENDING",
              "method_approved": True, "approval_basis": "USER_CONVERSATION_CONFIRMATION",
              "retained_candidates": len(ledger), "draft_contexts": len(drafts),
              "verified_causal_frame_links": sum(len(t['frames']) for t, _ in drafts),
              "draft_maneuver_counts": dict(Counter(t['maneuver'] for t, _ in drafts)),
              "context_fit_pilot_tasks": len(selected), "action_reviews_requested": 0,
              "scene_contexts_accepted": 0, "independent_action_gold_created": 0,
              "new_training_scenes": 0, "prior_action_task_suspended": True,
              "source_observations_automatically_rebound": False, "main_split": "NOT_FROZEN",
              "note": "3_IS_USABILITY_PILOT_NOT_MAIN_N_OR_ACTION_LABEL_COUNT"}
    output.mkdir(parents=True)
    def write_json(name, value):
        (output / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
    (output / 'context_fit_packet.json').write_bytes(packet_bytes)
    write_json('controlled_task_drafts.json', {'tasks': [t for t, _ in drafts]})
    write_json('candidate_task_ledger.json', {'records': ledger})
    write_json('RESULT.json', result)
    template = Path(__file__).with_name('controlled_context_fit.html')
    (output / 'controlled_context_fit.html').write_text(template.read_text().replace('__CONTEXT_PACKET__', json.dumps(display, ensure_ascii=False).replace('<', '\\u003c')))
    (output / 'REPORT_KO.md').write_text(
        '# 가정 경로 통제 과제 준비\n\n'
        '사용자가 방법 전환을 승인했습니다. 장면별 경로 적절성·행동 정답·학습 적격성 승인은 아닙니다.\n\n'
        f'- 기존 32후보 보존, 30개 과제 초안·210개 원본 과거 프레임 연결 확인. 방향 배정 {result["draft_maneuver_counts"]}.\n'
        '- 진행 방향은 clip ID의 고정 해시 규칙으로 배정했습니다. 기존 CoC·답변·행동 주석·폴리곤을 사용하지 않았습니다.\n'
        '- 3개 서로 다른 영상만 질문 적절성 확인용으로 제공합니다. 정상/위험 클래스 구성이나 본 표본 수를 뜻하지 않습니다.\n'
        '- 담당자는 지시된 경로가 특정되는지와 도로상 위치 설명만 답합니다. 행동 정답을 묻지 않습니다.\n'
        '- 불명확/보이지 않는 경로를 보존하며, 원하는 행동 답변을 얻으려고 방향을 재배정하지 않습니다.\n'
        '- 독립 ACTION은 경로 설명의 답 유도 점검·문맥 동결·검토자 노출 재확인 뒤 진행합니다. Jonh에게 아직 전달하지 않습니다.\n'
        '- 새 가정 경로에는 기존 관찰/명세/CNL이 그대로 적용된다고 가정하지 않습니다. CoC 문맥 일치도 별도 확인합니다.\n'
        '- 이전 16건 설문은 중단 유지. 신규 행동 정답/학습 데이터 0. M16/M17 PARTIAL.\n')
    write_json('RUN_MANIFEST.json', {'project_id': 'guardsynth-coc', 'experiment_id': output.parent.name,
               'run_id': output.name, 'created_at_utc': datetime.now(timezone.utc).isoformat(),
               'status': result['status'], 'network_used': False, 'input_hashes': inputs,
               'code_hashes': {str(p.relative_to(ROOT)): sha(p.read_bytes()) for p in (Path(__file__), template)},
               'output_hashes': {p.name: sha(p.read_bytes()) for p in sorted(output.iterdir())}})
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, required=True)
    print(json.dumps(prepare(parser.parse_args().output_dir), ensure_ascii=False, indent=2))
