"""Prepare a coordinator-only ACTION preview; never authorize dispatch or create labels."""

from __future__ import annotations

import argparse
import base64
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re


ROOT = next(p for p in Path(__file__).resolve().parents if (p / "PROJECT_REGISTRY.json").is_file())
PACKET_KEYS = {
    "review_version", "kind", "sample_id", "event_timestamp_us", "zone_polygon",
    "frames", "choices", "scope", "gold_prefilled",
}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_action(source: Path, record: dict, hashes: dict) -> tuple[dict, dict]:
    paths = [record["action_packet"], record["action_page"]]
    contents = {}
    for name in paths:
        path = (source / name).resolve()
        if not path.is_relative_to(source.resolve()):
            raise ValueError("packet path escapes preflight")
        contents[name] = path.read_bytes()
        if sha(contents[name]) != hashes[name]:
            raise ValueError("preflight output hash mismatch")
    packet = json.loads(contents[paths[0]])
    if set(packet) != PACKET_KEYS or packet["kind"] != "ACTION" or packet["gold_prefilled"] is not False:
        raise ValueError("not an unlabelled ACTION packet")
    match = re.search(r'<script id="packet" type="application/json">(.*?)</script>', contents[paths[1]].decode(), re.S)
    if match is None:
        raise ValueError("missing display packet")
    display = json.loads(match.group(1))
    if set(display) != PACKET_KEYS | {"packet_sha256", "images"}:
        raise ValueError("unexpected display fields")
    if {k: display[k] for k in PACKET_KEYS} != packet or display["packet_sha256"] != sha(contents[paths[0]]):
        raise ValueError("display differs from ACTION packet")
    if packet["sample_id"] != record["sample_id"] or len(display["images"]) != len(packet["frames"]):
        raise ValueError("scene/frame identity mismatch")
    for frame, image in zip(packet["frames"], display["images"]):
        prefix = "data:image/jpeg;base64,"
        if not image.startswith(prefix) or sha(base64.b64decode(image[len(prefix):], validate=True)) != frame["sha256"]:
            raise ValueError("display image hash mismatch")
        if frame["timestamp_us"] > packet["event_timestamp_us"]:
            raise ValueError("future frame in ACTION packet")
    return display, {str((source / name).relative_to(ROOT)): hashes[name] for name in paths}


def prepare(source: Path, output: Path, reviewer: str, *, answer_form: bool = False) -> dict:
    source, output = source.resolve(), output.resolve()
    if output.exists():
        raise FileExistsError(output)
    if not reviewer.strip():
        raise ValueError("reviewer is required")
    manifest_path = source / "RUN_MANIFEST.json"
    manifest = json.loads(manifest_path.read_text())
    coordination_path = source / "review_coordination.json"
    if sha(coordination_path.read_bytes()) != manifest["output_hashes"]["review_coordination.json"]:
        raise ValueError("coordination hash mismatch")
    records = json.loads(coordination_path.read_text())["records"]
    displays, inputs = [], {str(p.relative_to(ROOT)): sha(p.read_bytes()) for p in (manifest_path, coordination_path)}
    for record in records:
        display, pinned = load_action(source, record, manifest["output_hashes"])
        displays.append(display)
        inputs.update(pinned)
    if len(displays) != 16 or len({p["sample_id"] for p in displays}) != 16:
        raise ValueError("expected sixteen distinct ACTION packets")
    template = Path(__file__).with_name("action_assignment_preview.html")
    form_template = Path(__file__).with_name("action_review_form.html")
    result = {
        "project_id": "guardsynth-coc", "status": "NOMINATED_PENDING_COORDINATOR_ACCEPTANCE",
        "reviewer_id": reviewer, "available_reviewers": 1,
        "nonexposure_basis": "USER_CONFIRMATION_IN_CONVERSATION",
        "reviewer_self_declaration": None, "identity_or_expertise_authenticated": False,
        "coordinator_acceptance": None, "dispatch_authorized": False,
        "scope": "SINGLE_REVIEWER_DEVELOPMENT_AUDIT_ONLY",
        "formal_required_action_reviewers": 2, "formal_second_reviewer": None,
        "formal_gate_changed": False, "action_responses": 0, "cnl_responses": 0,
        "new_training_scenes": 0, "main_gold_created": 0,
        "order": "ALL_ACTION_SUBMISSIONS_BEFORE_CNL_OR_SOURCE_EXPOSURE",
        "sample_ids": [p["sample_id"] for p in displays],
        "source_run": str(source.relative_to(ROOT)),
    }
    output.mkdir(parents=True)
    def write_json(name: str, value: dict) -> None:
        (output / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
    write_json("RESULT.json", result)
    payload = json.dumps(displays, ensure_ascii=False).replace("<", "\\u003c")
    preview = template.read_text().replace("__ACTION_PACKETS__", payload)
    if answer_form:
        bundle_sha256 = sha(json.dumps([p["packet_sha256"] for p in displays]).encode())
        result["answer_form_prepared"] = True
        result["bundle_sha256"] = bundle_sha256
        write_json("RESULT.json", result)
        form = re.sub(
            r'<h1>.*?(?=<div class="toolbar">)',
            '<h1>독립 행동 검토 · 16장면</h1>'
            '<p class="note">담당자가 질문·영역을 확인한 후 배정된 검토자가 작성합니다. '
            '이 화면 준비는 담당자 승인이나 정답 확정이 아닙니다. 1인 개발용 검토입니다.</p>'
            '<p><b>판단 시점까지 보이는 장면을 근거로, 에고 차량이 지금 노란 영역에 진입해도 되는가?</b><br>'
            '영상을 확인하고 아래에서 행동과 이유를 입력한 뒤 <b>이 장면 답변 완료</b>를 누르세요. '
            '진행 방향·영역·시야가 불명확하면 추측하지 말고 판단 불가를 선택하고 이유를 적어 주세요. '
            '영상 속 차량이 실제로 한 행동을 복사하는 질문은 아닙니다.</p>'
            '<p><a href="#reviewForm">답변 입력으로 이동</a> · <b id="completionTop">완료 0/16</b></p>',
            preview, count=1, flags=re.S,
        ).replace('<title>담당자 확인 · 16장면 행동 검토 준비</title>', '<title>독립 행동 검토 · 답변 입력</title>')
        fragment = form_template.read_text().replace("__ASSIGNED_REVIEWER__", json.dumps(reviewer).replace("<", "\\u003c"))
        fragment = fragment.replace("__BUNDLE_SHA256__", json.dumps(bundle_sha256))
        (output / "action_review.html").write_text(form.replace('</html>', fragment + '</html>'))
        preview = preview.replace('<h1>', '<p><a href="paper1_action_review.html">검토자 답변 입력 화면 열기 →</a></p><h1>', 1)
    (output / "action_assignment_preview.html").write_text(preview)
    (output / "REPORT_KO.md").write_text(
        "# 독립 행동 검토 배정 예약\n\n"
        f"- 검토자 표기: {reviewer}. 사용자에 의한 기존 자료 미노출 확인을 기록했습니다.\n"
        "- 16장면 개발용 행동 검토 후보이며, 본인 선언·실제 답변·담당자 승인은 아직 없습니다.\n"
        "- 담당자는 미리보기에서 질문·노란 영역·판단 시점까지의 입력이 적절한지 확인해야 합니다.\n"
        + ("- 담당자 미리보기와 별도의 행동 답변 화면을 준비했습니다. 승인 상태는 변경하지 않았습니다.\n"
         if answer_form else "- 이 화면에는 답변 입력 기능이 없으며, 검토자에게 아직 전달하지 않습니다.\n")
        + "- 담당자 승인 후 ACTION만 먼저 제공하고, 16건 답변 제출 후 CNL을 제공합니다.\n"
        "- 1인 결과는 개발용입니다. 2인 검토·불일치 조정 등 기존 정식 gate는 미충족이며 변경하지 않았습니다.\n"
        "- 원본 관찰·명세·설문·미리보기 입력은 수정하지 않았습니다. 신규 학습 데이터/정답 0건.\n"
    )
    write_json("RUN_MANIFEST.json", {
        "project_id": "guardsynth-coc", "experiment_id": output.parent.name,
        "run_id": output.name, "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": result["status"], "network_used": False, "input_hashes": inputs,
        "code_hashes": {str(p.relative_to(ROOT)): sha(p.read_bytes()) for p in
                        ((Path(__file__), template, form_template) if answer_form else (Path(__file__), template))},
        "output_hashes": {p.name: sha(p.read_bytes()) for p in sorted(output.iterdir())},
    })
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--reviewer", required=True)
    parser.add_argument("--answer-form", action="store_true")
    args = parser.parse_args()
    print(json.dumps(prepare(args.source, args.output_dir, args.reviewer, answer_form=args.answer_form), ensure_ascii=False, indent=2))
