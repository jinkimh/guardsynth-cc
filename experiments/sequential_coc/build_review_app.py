#!/usr/bin/env python3
"""Build a deterministic, blinded review packet for restricted natural windows."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import html
import json
import os
from pathlib import Path
import random
import re
import sys
import tempfile
from typing import Iterable, Sequence

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from experiments.sequential_coc.extract_windows import (
    NATURAL_WINDOWS_PATH,
    OUTPUT_DIR,
    TRANSITION_SOURCE_PATTERN,
    TRANSITION_TARGET_PATTERN,
    RawEventWindow,
    read_natural_windows,
)


REVIEW_DIR = OUTPUT_DIR / "review"
SELECTION_SEED = 20260806
REVIEW_SEEDS = {"A": 202608061, "B": 202608062}
CONTRACT_REVIEW_FIELDS = (
    "review_id",
    "temporal_requirement_explicit",
    "required_action_sequence",
    "textual_consistency",
    "notes",
)
CONTRACT_CHOICES = {
    "temporal_requirement_explicit": ("YES", "NO", "AMBIGUOUS"),
    "required_action_sequence": (
        "STOP_OR_HOLD",
        "YIELD_OR_DECELERATE",
        "ACCELERATE_OR_PROCEED",
        "MAINTAIN_SPEED",
        "OTHER",
        "AMBIGUOUS",
        "NO_EXPLICIT_ACTION",
    ),
    "textual_consistency": (
        "TEXTUAL_CONTRADICTION",
        "TEXTUALLY_CONSISTENT",
        "UNKNOWN_EXTERNAL_EVIDENCE_REQUIRED",
        "AMBIGUOUS_TEXT",
        "NOT_APPLICABLE_NO_TEMPORAL_REQUIREMENT",
    ),
}
FIELD_LABELS = {
    "temporal_requirement_explicit": "1. 시간적 요구가 명시되어 있습니까?",
    "required_action_sequence": "2. 요구 행동열은 무엇입니까?",
    "textual_consistency": "3. 텍스트 자체의 시간적 관계는 어떻습니까?",
}
FIELD_EXPLANATIONS = {
    "temporal_requirement_explicit": (
        "시간적 요구란 행동을 언제까지 유지하거나 언제 다음 행동으로 바꿀지 "
        "정하는 표현입니다. 예: ‘보행자가 지나갈 때까지 정지한다.’"
    ),
    "required_action_sequence": (
        "문장에 나온 행동의 의미 단계를 시간 순서대로 기록합니다. "
        "예: ‘정지한 다음 출발한다.’ → 정지·대기 → 가속·진행"
    ),
    "textual_consistency": (
        "앞뒤 문장을 함께 읽고 텍스트만으로 모순이 확정되는지 판단합니다. "
        "실제로 지나갔는지는 영상이나 상태 정보가 필요하면 외부 증거 필요를 고릅니다."
    ),
}
CHOICE_LABELS = {
    "temporal_requirement_explicit": {
        "YES": "예—유지·해제·행동 순서가 명시됨",
        "NO": "아니오—행동은 있지만 시간적 연결은 없음",
        "AMBIGUOUS": "모호함—문장만으로 시간적 요구를 정하기 어려움",
    },
    "textual_consistency": {
        "TEXTUAL_CONTRADICTION": "텍스트상 모순",
        "TEXTUALLY_CONSISTENT": "텍스트상 일관됨",
        "UNKNOWN_EXTERNAL_EVIDENCE_REQUIRED": "외부 증거 필요",
        "AMBIGUOUS_TEXT": "문장 자체가 모호함",
        "NOT_APPLICABLE_NO_TEMPORAL_REQUIREMENT": "시간적 요구가 없어 해당 없음",
    },
}
CHOICE_EXAMPLES = {
    "temporal_requirement_explicit": {
        "YES": "예: ‘차량이 지나갈 때까지 정지한다.’",
        "NO": "예: 서로 독립적인 두 행동만 나열됨",
        "AMBIGUOUS": "예: ‘상황에 맞게 적절히 행동한다.’",
    },
    "textual_consistency": {
        "TEXTUAL_CONTRADICTION": (
            "예: ‘신호가 녹색이 될 때까지 정지한다.’ 다음에 "
            "‘아직 적색이므로 출발한다.’"
        ),
        "TEXTUALLY_CONSISTENT": (
            "예: ‘차량이 지나갈 때까지 정지한다.’ 다음에 "
            "‘차량이 통과했으므로 출발한다.’"
        ),
        "UNKNOWN_EXTERNAL_EVIDENCE_REQUIRED": (
            "예: ‘보행자가 지나갈 때까지 정지한다.’ 다음에 ‘이제 출발한다.’"
        ),
        "AMBIGUOUS_TEXT": "예: 요구 행동이나 조건이 구체적이지 않음",
        "NOT_APPLICABLE_NO_TEMPORAL_REQUIREMENT": "예: 앞뒤 행동 사이의 유지·해제·순서 관계가 없음",
    },
}
ACTION_LABELS = {
    "STOP_OR_HOLD": "정지·대기",
    "YIELD_OR_DECELERATE": "양보·감속",
    "ACCELERATE_OR_PROCEED": "가속·진행",
    "MAINTAIN_SPEED": "현재 속도 유지",
    "OTHER": "기타 행동",
    "AMBIGUOUS": "행동열이 모호함",
    "NO_EXPLICIT_ACTION": "명시된 행동 없음",
}

_SOURCE = re.compile(TRANSITION_SOURCE_PATTERN, re.IGNORECASE)
_TARGET = re.compile(TRANSITION_TARGET_PATTERN, re.IGNORECASE)
_STOP = re.compile(r"\bstop\b", re.IGNORECASE)


@dataclass(frozen=True, slots=True)
class ReviewItem:
    review_id: str
    event_texts: tuple[str, ...]
    relative_times_s: tuple[float, ...]

    def __post_init__(self) -> None:
        if re.fullmatch(r"REV-[0-9a-f]{16}", self.review_id) is None:
            raise ValueError("review_id must be an opaque review digest")
        if not 2 <= len(self.event_texts) <= 4:
            raise ValueError("review items require two through four event texts")
        if len(self.event_texts) != len(self.relative_times_s):
            raise ValueError("event texts and relative times must align")
        if self.relative_times_s[0] != 0.0 or tuple(self.relative_times_s) != tuple(
            sorted(self.relative_times_s)
        ):
            raise ValueError("relative times must be sorted and begin at zero")


def _window_key(window: RawEventWindow) -> tuple[object, ...]:
    first = window.events[0]
    return (first.timestamp_us, first.original_position, window.window_id)


def _source_class(window: RawEventWindow) -> str:
    return "STOP" if _STOP.search(window.events[0].source_text) else "YIELD"


def _tie_break(candidate: RawEventWindow, control: RawEventWindow) -> str:
    value = f"{SELECTION_SEED}:{candidate.window_id}:{control.window_id}"
    return hashlib.sha256(value.encode("ascii")).hexdigest()


def _opaque_review_id(window: RawEventWindow) -> str:
    digest = hashlib.sha256(f"review-v1:{window.window_id}".encode("ascii")).hexdigest()
    return f"REV-{digest[:16]}"


def _to_item(window: RawEventWindow) -> ReviewItem:
    start = window.events[0].timestamp_us
    return ReviewItem(
        review_id=_opaque_review_id(window),
        event_texts=tuple(event.source_text for event in window.events),
        relative_times_s=tuple(round((event.timestamp_us - start) / 1_000_000, 6) for event in window.events),
    )


def select_review_items(
    windows: Iterable[RawEventWindow],
) -> tuple[list[ReviewItem], list[dict[str, object]], dict[str, int]]:
    """Select one candidate per candidate scene and matched controls without labels."""
    materialized = list(windows)
    if any(not isinstance(window, RawEventWindow) for window in materialized):
        raise TypeError("review selection requires RawEventWindow values")
    by_scene: dict[str, list[RawEventWindow]] = {}
    for window in materialized:
        by_scene.setdefault(window.cluster_id, []).append(window)
    for scene_windows in by_scene.values():
        scene_windows.sort(key=_window_key)

    candidate_windows = [
        window
        for window in materialized
        if _SOURCE.search(window.events[0].source_text)
        and _TARGET.search(window.events[1].source_text)
    ]
    candidate_scenes = {window.cluster_id for window in candidate_windows}
    selected_candidates = [
        min(
            (window for window in candidate_windows if window.cluster_id == scene_id),
            key=_window_key,
        )
        for scene_id in sorted(candidate_scenes)
    ]
    selected_candidates.sort(key=lambda window: (window.cluster_id, _window_key(window)))

    eligible_controls = []
    for scene_id, scene_windows in by_scene.items():
        if scene_id in candidate_scenes:
            continue
        eligible = [
            window
            for window in scene_windows
            if _SOURCE.search(window.events[0].source_text)
            and not _TARGET.search(window.events[1].source_text)
        ]
        if eligible:
            eligible_controls.append(min(eligible, key=_window_key))

    event_counts: dict[str, int] = {}
    for scene_id, scene_windows in by_scene.items():
        identities = {
            (
                event.timestamp_us,
                event.original_position,
                event.duplicate_occurrence,
                event.source_text_sha256,
            )
            for window in scene_windows
            for event in window.events
        }
        event_counts[scene_id] = len(identities)

    unused = list(eligible_controls)
    matched: list[tuple[RawEventWindow, RawEventWindow]] = []
    for candidate in selected_candidates:
        if not unused:
            break
        control = min(
            unused,
            key=lambda item: (
                abs(event_counts[candidate.cluster_id] - event_counts[item.cluster_id]),
                int(_source_class(candidate) != _source_class(item)),
                abs(candidate.events[0].original_position - item.events[0].original_position),
                _tie_break(candidate, item),
            ),
        )
        unused.remove(control)
        matched.append((candidate, control))

    selected_controls = [control for _, control in matched]
    selected = selected_candidates + selected_controls
    items = [_to_item(window) for window in selected]
    matched_by_control = {control.window_id: candidate for candidate, control in matched}
    mapping: list[dict[str, object]] = []
    for window in selected:
        is_candidate = window in selected_candidates
        candidate = window if is_candidate else matched_by_control[window.window_id]
        mapping.append(
            {
                "review_id": _opaque_review_id(window),
                "cluster_id": window.cluster_id,
                "window_id": window.window_id,
                "group": "CANDIDATE" if is_candidate else "CONTROL",
                "source_class": _source_class(window),
                "source_position": window.events[0].original_position,
                "scene_event_count": event_counts[window.cluster_id],
                "matched_candidate_review_id": _opaque_review_id(candidate),
            }
        )
    stats = {
        "candidate_raw_pairs": len(candidate_windows),
        "candidate_raw_scenes": len(candidate_scenes),
        "selected_candidate_windows": len(selected_candidates),
        "selected_candidate_scenes": len({window.cluster_id for window in selected_candidates}),
        "selected_control_windows": len(selected_controls),
        "selected_control_scenes": len({window.cluster_id for window in selected_controls}),
        "total_review_items": len(selected),
        "independent_clusters": len({window.cluster_id for window in selected}),
    }
    return items, mapping, stats


def order_for_reviewer(reviewer: str, items: Sequence[ReviewItem]) -> list[ReviewItem]:
    if reviewer not in REVIEW_SEEDS:
        raise ValueError("reviewer must be A or B")
    ordered = list(items)
    random.Random(REVIEW_SEEDS[reviewer]).shuffle(ordered)
    return ordered


def _item_html(item: ReviewItem) -> str:
    events = "".join(
        '<li><span class="relative">+{:.3f} s</span><p>{}</p></li>'.format(
            relative, html.escape(text, quote=True)
        )
        for text, relative in zip(item.event_texts, item.relative_times_s)
    )
    fieldsets = []
    for field in ("temporal_requirement_explicit", "textual_consistency"):
        choices = CONTRACT_CHOICES[field]
        options = "".join(
            '<label class="choice-card"><input type="radio" name="{}" value="{}">'
            '<span><strong>{} ({})</strong><small>{}</small></span></label>'.format(
                html.escape(field, quote=True),
                html.escape(choice, quote=True),
                html.escape(CHOICE_LABELS[field][choice]),
                html.escape(choice),
                html.escape(CHOICE_EXAMPLES[field][choice]),
            )
            for choice in choices
        )
        fieldsets.append(
            f'<fieldset><legend>{html.escape(FIELD_LABELS[field])}</legend>'
            f'<p class="question-help">{html.escape(FIELD_EXPLANATIONS[field])}</p>'
            f'<div class="choices">{options}</div></fieldset>'
        )
    action_buttons = "".join(
        '<button type="button" class="action-add" data-action="{}">{} ({})</button>'.format(
            html.escape(choice, quote=True),
            html.escape(ACTION_LABELS[choice]),
            html.escape(choice),
        )
        for choice in CONTRACT_CHOICES["required_action_sequence"]
    )
    action_fieldset = (
        '<fieldset class="action-sequence"><legend>'
        f'{html.escape(FIELD_LABELS["required_action_sequence"])}</legend>'
        f'<p class="question-help">{html.escape(FIELD_EXPLANATIONS["required_action_sequence"])}</p>'
        '<p class="field-help">행동 버튼을 의미 단계 순서대로 누르십시오. 같은 행동의 연속 반복은 한 번만 기록합니다.</p>'
        '<p class="shortcut-title"><strong>자주 쓰는 행동열 바로 선택</strong></p>'
        '<div class="sequence-shortcuts">'
        '<button type="button" class="sequence-shortcut" data-sequence="STOP_OR_HOLD&gt;ACCELERATE_OR_PROCEED">정지·유지 → 가속·진행</button>'
        '<button type="button" class="sequence-shortcut" data-sequence="YIELD_OR_DECELERATE&gt;ACCELERATE_OR_PROCEED">양보·감속 → 가속·진행</button>'
        '</div><p class="shortcut-title"><strong>직접 단계 추가</strong></p>'
        f'<div class="action-buttons">{action_buttons}</div>'
        '<input type="hidden" name="required_action_sequence" value="">'
        '<p class="sequence-output" aria-live="polite">아직 선택하지 않음</p>'
        '<div class="sequence-tools"><button type="button" class="action-undo">마지막 단계 취소</button>'
        '<button type="button" class="action-clear">전체 초기화</button></div></fieldset>'
    )
    return f'''<section class="item" data-review-id="{html.escape(item.review_id, quote=True)}">
<h2>{html.escape(item.review_id)}</h2><h3>제공된 사건 연속열</h3><ol class="events">{events}</ol>
<p class="evidence">제공 증거: CoC 텍스트와 첫 사건 기준 상대 시간만 제공됩니다. 텍스트에 없는 사실은 추정하지 마십시오.</p>
<form><div class="grid">{fieldsets[0]}{action_fieldset}{fieldsets[1]}</div><fieldset class="notes"><legend>판정 근거 메모 (선택)</legend><textarea name="notes" maxlength="1000"></textarea></fieldset></form>
</section>'''


def _embedded_guide_html() -> str:
    return '''<details class="guide" open><summary>판정 도움말과 합성 예제</summary>
<p><strong>목적:</strong> 자동 파서를 평가하는 것이 아니라, CoC 텍스트 자체에 시간적 요구와 모순이 있는지 독립적으로 판정합니다. 실제 상태나 안전을 추측하지 마십시오.</p>
<ol>
<li><strong>시간적 요구</strong>: 유지, 해제 또는 “먼저 A, 다음 B”와 같은 순서가 문장 사이 또는 한 문장 안에 명시됩니다.</li>
<li><strong>행동열</strong>: 행동 단계를 시간 순으로 누릅니다. STOP, STOP, ACCELERATE, ACCELERATE는 <strong>STOP_OR_HOLD&gt;ACCELERATE_OR_PROCEED</strong>로 기록합니다.</li>
<li><strong>TEXTUAL_CONTRADICTION</strong>: 텍스트만으로 두 요구가 함께 성립할 수 없습니다.</li>
<li><strong>TEXTUALLY_CONSISTENT</strong>: 텍스트에 명시된 유지·해제·순서 관계가 서로 맞습니다.</li>
<li><strong>UNKNOWN_EXTERNAL_EVIDENCE_REQUIRED</strong>: 문장은 이해되지만 실제 신호·객체·영상 상태가 있어야 모순 여부를 정할 수 있습니다.</li>
<li><strong>AMBIGUOUS_TEXT</strong>: 문장 자체가 모호합니다.</li>
<li><strong>NOT_APPLICABLE_NO_TEMPORAL_REQUIREMENT</strong>: 서로 이어지는 시간적 요구가 없습니다.</li>
</ol>
<div class="example"><strong>TEXTUAL_CONTRADICTION 예:</strong> “신호가 녹색이 될 때까지 정지한다.” → “신호가 아직 적색이므로 출발한다.” 해제 조건이 아직 거짓이라고 텍스트가 명시합니다.</div>
<div class="example"><strong>UNKNOWN_EXTERNAL_EVIDENCE_REQUIRED 예:</strong> “보행자가 지나갈 때까지 정지한다.” → “이제 출발한다.” 보행자가 실제로 지나갔는지 텍스트만으로 알 수 없습니다.</div>
<p><strong>빠른 구분:</strong> 문장 자체가 모호하면 <strong>AMBIGUOUS_TEXT</strong>, 표현은 명확하지만 실제 상태 증거가 필요하면 <strong>UNKNOWN_EXTERNAL_EVIDENCE_REQUIRED</strong>입니다.</p>
</details>'''


def build_contract_review_page(reviewer: str, items: Sequence[ReviewItem]) -> str:
    """Return a standalone page; source text is rendered only as escaped HTML."""
    if reviewer not in REVIEW_SEEDS:
        raise ValueError("reviewer must be A or B")
    sections = "\n".join(_item_html(item) for item in items)
    fields_json = json.dumps(CONTRACT_CHOICES, separators=(",", ":"))
    columns_json = json.dumps(list(CONTRACT_REVIEW_FIELDS), separators=(",", ":"))
    ids_json = json.dumps([item.review_id for item in items], separators=(",", ":"))
    filename = f"contract_review_{reviewer}.csv"
    guide = _embedded_guide_html()
    return f'''<!doctype html><html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; form-action 'none'; base-uri 'none'">
<title>연속 CoC 계약 구조 독립 검토 {reviewer}</title><style>
*{{box-sizing:border-box}}body{{margin:0;background:#f5f7fa;color:#17202a;font-family:system-ui,"Noto Sans KR",sans-serif}}header{{position:sticky;top:0;background:white;border-bottom:1px solid #ccd3dc;padding:12px 18px;display:flex;gap:12px;align-items:center;z-index:2}}header h1{{font-size:18px;margin:0}}header .grow{{flex:1}}button{{padding:9px 14px;border:0;border-radius:7px;background:#1d4ed8;color:white;font:inherit;cursor:pointer}}main{{max-width:1100px;margin:18px auto;padding:0 18px 70px}}.instructions,.item,.guide{{background:white;border:1px solid #d7dde5;border-radius:10px;padding:16px;margin:16px 0;line-height:1.55}}.guide summary{{cursor:pointer;font-weight:800;font-size:17px}}.guide .example{{margin:10px 0;padding:10px 12px;background:#eef4ff;border-left:4px solid #1d4ed8}}.warning,.evidence{{background:#fff8e6;border:1px solid #edcf83;border-radius:7px;padding:10px 12px}}.events{{padding-left:28px}}.events li{{margin:12px 0}}.events p{{background:#eef4ff;border-left:4px solid #1d4ed8;padding:12px;margin:5px 0;font-size:17px}}.relative{{color:#536170;font-weight:700}}.grid{{display:grid;grid-template-columns:1fr;gap:12px}}fieldset{{border:1px solid #ccd3dc;border-radius:8px;padding:12px}}legend{{font-weight:800;font-size:17px}}.choices,.action-buttons,.sequence-shortcuts,.sequence-tools{{display:flex;flex-wrap:wrap;gap:8px 14px}}.choices{{flex-direction:column}}.choice-card{{display:flex;align-items:flex-start;gap:8px;padding:10px;border:1px solid #cbd5e1;border-radius:7px;background:#f8fafc}}.choice-card span{{display:flex;flex-direction:column;gap:3px}}.choice-card small{{color:#475569;font-size:14px}}.question-help{{margin:2px 0 12px;padding:9px 11px;background:#f0fdf4;border-left:4px solid #16a34a}}.action-buttons button{{background:#334155}}.sequence-shortcuts button{{background:#047857;font-weight:800}}.sequence-tools button{{background:#64748b}}.sequence-output{{min-height:44px;padding:10px 12px;border:2px solid #1d4ed8;border-radius:7px;background:#eef4ff;font-weight:800;word-break:break-word}}.field-help{{margin:2px 0 10px;color:#475569}}.shortcut-title{{margin:12px 0 6px}}.notes{{margin-top:12px}}textarea{{width:100%;min-height:72px}}progress{{width:190px}}@media(max-width:760px){{header{{position:static;flex-wrap:wrap}}}}
</style></head><body><header><h1>계약 구조 독립 검토 · {reviewer}</h1><progress id="progress" max="{len(items)}" value="0"></progress><span id="progressText">0/{len(items)}</span><span id="saved">준비 중</span><span class="grow"></span><button id="export" type="button">CSV 저장</button></header>
<main><div class="instructions"><p><strong>독립 1차 검토:</strong> 다른 검토자와 상의하지 말고 CoC 텍스트 자체의 시간적 요구, 행동열, 일관성만 기록하십시오.</p><p class="warning">행동은 하나만 고르는 것이 아닙니다. 의미 단계가 바뀔 때마다 순서대로 추가하십시오. 실제 상태가 있어야 모순 여부를 알 수 있으면 <strong>UNKNOWN_EXTERNAL_EVIDENCE_REQUIRED</strong>를 선택하십시오.</p><p>교통법규 위반, 충돌 위험, 물리적 안전, 학습 성능 또는 실제 운전 결과를 판정하지 마십시오. 세 항목을 모두 완료한 뒤 CSV를 저장하십시오.</p></div>{guide}{sections}</main>
<script>
const reviewer={json.dumps(reviewer)},fields={fields_json},columns={columns_json},reviewIds={ids_json},storageKey=`sequential-coc-review-v1-${{reviewer}}`;let rows={{}};for(const id of reviewIds)rows[id]={{review_id:id}};
try{{const old=JSON.parse(localStorage.getItem(storageKey)||"{{}}");for(const id of reviewIds)Object.assign(rows[id],old[id]||{{}})}}catch(error){{}}
function complete(row){{return Object.keys(fields).every(key=>row[key])}}function update(){{const done=reviewIds.filter(id=>complete(rows[id])).length;document.getElementById("progress").value=done;document.getElementById("progressText").textContent=`완료 ${{done}}/${{reviewIds.length}}`}}
function save(){{for(const section of document.querySelectorAll(".item")){{const id=section.dataset.reviewId,form=new FormData(section.querySelector("form")),row={{review_id:id}};for(const field of Object.keys(fields))row[field]=form.get(field)||"";row.notes=form.get("notes")||"";rows[id]=row}}try{{localStorage.setItem(storageKey,JSON.stringify(rows));document.getElementById("saved").textContent="자동 저장됨"}}catch(error){{document.getElementById("saved").textContent="자동 저장 불가"}}update()}}
function renderSequence(section){{const input=section.querySelector('input[name="required_action_sequence"]'),output=section.querySelector(".sequence-output");output.textContent=input.value?input.value.split(">").join(" → "):"아직 선택하지 않음"}}
function appendAction(section,action){{const input=section.querySelector('input[name="required_action_sequence"]'),special=["AMBIGUOUS","NO_EXPLICIT_ACTION"];if(special.includes(action)){{input.value=action}}else{{let sequence=special.includes(input.value)||!input.value?[]:input.value.split(">");if(sequence[sequence.length-1]!==action)sequence.push(action);input.value=sequence.join(">")}}renderSequence(section);save()}}
function setActionSequence(section,sequence){{section.querySelector('input[name="required_action_sequence"]').value=sequence;renderSequence(section);save()}}
function undoAction(section){{const input=section.querySelector('input[name="required_action_sequence"]');if(["AMBIGUOUS","NO_EXPLICIT_ACTION"].includes(input.value))input.value="";else{{const sequence=input.value?input.value.split(">"):[];sequence.pop();input.value=sequence.join(">")}}renderSequence(section);save()}}
function clearAction(section){{section.querySelector('input[name="required_action_sequence"]').value="";renderSequence(section);save()}}
function restore(){{for(const section of document.querySelectorAll(".item")){{const row=rows[section.dataset.reviewId]||{{}};section.querySelectorAll('input[type="radio"]').forEach(input=>input.checked=row[input.name]===input.value);section.querySelector('input[name="required_action_sequence"]').value=row.required_action_sequence||"";section.querySelector("textarea").value=row.notes||"";renderSequence(section)}}update()}}
function cell(value){{const text=String(value??"");return /[",\\r\\n]/.test(text)?`"${{text.replace(/"/g,'""')}}"`:text}}function exportCsv(){{save();const lines=[columns.join(",")];for(const id of reviewIds)lines.push(columns.map(column=>cell(rows[id][column]||"")).join(","));const blob=new Blob(["\ufeff"+lines.join("\\r\\n")+"\\r\\n"],{{type:"text/csv;charset=utf-8"}});const anchor=document.createElement("a");anchor.href=URL.createObjectURL(blob);anchor.download={json.dumps(filename)};anchor.click();setTimeout(()=>URL.revokeObjectURL(anchor.href),1000)}}
document.addEventListener("click",event=>{{const section=event.target.closest(".item");if(!section)return;if(event.target.matches(".sequence-shortcut"))setActionSequence(section,event.target.dataset.sequence);if(event.target.matches(".action-add"))appendAction(section,event.target.dataset.action);if(event.target.matches(".action-undo"))undoAction(section);if(event.target.matches(".action-clear"))clearAction(section)}});document.addEventListener("change",save);document.addEventListener("input",save);document.getElementById("export").onclick=exportCsv;restore();document.getElementById("saved").textContent="준비됨";
</script></body></html>'''


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_restricted(path: Path, content: str) -> None:
    encoded = content.encode("utf-8")
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary_path = Path(temporary_name)
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        if temporary_path.read_bytes() != encoded:
            raise RuntimeError("restricted temporary artifact verification failed")
        if temporary_path.stat().st_mode & 0o777 != 0o600:
            raise RuntimeError("restricted temporary artifact mode verification failed")
        os.replace(temporary_path, path)
        directory_descriptor = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory_descriptor)
        finally:
            os.close(directory_descriptor)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()


def review_already_started(review_dir: Path) -> bool:
    if not review_dir.exists():
        return False
    return any(
        path.suffix.lower() == ".csv"
        for path in review_dir.iterdir()
        if path.is_file()
    )


def _protocol() -> str:
    return """# 검토자용 연속 CoC 시간 일관성 설문 프로토콜 — 한국어판

패킷 상태: `WAITING_FOR_CONTRACT_REVIEW`

## 1. 설문의 목적

이 설문은 자동 파서의 성능을 평가하지 않습니다. 연속된 CoC 텍스트 자체에
시간적으로 이어지는 요구가 있는지, 그 행동열이 무엇인지, 텍스트만으로 모순을
확정할 수 있는지를 독립적으로 판정합니다.

화면에는 CoC 텍스트와 첫 사건 기준 상대 시간만 있습니다. 영상, 그림, 궤적,
객체ㆍ신호 상태, 검사기ㆍUPPAAL 결과는 없습니다. 실제 사실을 추측하지 마십시오.

## 2. 세 가지 판정

### 2.1 `temporal_requirement_explicit`

문장 사이 또는 한 문장 안에 유지, 해제, “먼저 A, 다음 B” 같은 시간적 요구가
명시됐는지 판정합니다.

- `YES`: 시간적 연결이 명시되어 있습니다.
- `NO`: 행동은 있어도 서로 이어지는 시간적 요구는 없습니다.
- `AMBIGUOUS`: 문장 자체가 모호하여 정하기 어렵습니다.

### 2.2 `required_action_sequence`

텍스트가 요구하는 행동의 **의미 단계**를 시간 순서대로 버튼으로 추가합니다.
한 행동만 고르는 항목이 아닙니다. 같은 행동이 연속 반복되면 한 단계로 합칩니다.

- `STOP, STOP, ACCELERATE, ACCELERATE`
- 저장: `STOP_OR_HOLD>ACCELERATE_OR_PROCEED`

한 문장에 “정지한 다음 출발한다”라고 적혀 있어도 두 단계를 모두 기록합니다.
행동이 없으면 `NO_EXPLICIT_ACTION`, 행동 순서를 읽을 수 없으면 `AMBIGUOUS`를
단독으로 선택합니다. 잘못 누르면 마지막 단계 취소 또는 전체 초기화를 사용합니다.

### 2.3 `textual_consistency`

- `TEXTUAL_CONTRADICTION`: 문장만으로 시간적 요구의 충돌이 확정됩니다.
- `TEXTUALLY_CONSISTENT`: 텍스트에 명시된 유지ㆍ해제ㆍ순서 관계가 서로 맞습니다.
- `UNKNOWN_EXTERNAL_EVIDENCE_REQUIRED`: 문장은 이해되지만 실제 신호ㆍ객체ㆍ영상
  상태가 있어야 모순 여부를 정할 수 있습니다.
- `AMBIGUOUS_TEXT`: 문장 자체가 모호합니다.
- `NOT_APPLICABLE_NO_TEMPORAL_REQUIREMENT`: 서로 이어지는 시간적 요구가 없습니다.

## 3. 합성 예제

### 텍스트 모순

- 앞: “신호가 녹색이 될 때까지 정지한다.”
- 뒤: “신호가 아직 적색이므로 출발한다.”
- 행동열: `STOP_OR_HOLD>ACCELERATE_OR_PROCEED`
- 판정: `TEXTUAL_CONTRADICTION`

### 외부 증거 필요

- 앞: “보행자가 지나갈 때까지 정지한다.”
- 뒤: “이제 출발한다.”
- 행동열: `STOP_OR_HOLD>ACCELERATE_OR_PROCEED`
- 이유: 보행자가 실제로 지나갔는지 텍스트만으로 알 수 없습니다.
- 판정: `UNKNOWN_EXTERNAL_EVIDENCE_REQUIRED`

### 텍스트상 일관됨

- 앞: “오토바이가 지나갈 때까지 정지한다.”
- 뒤: “오토바이가 통과했으므로 출발한다.”
- 행동열: `STOP_OR_HOLD>ACCELERATE_OR_PROCEED`
- 판정: `TEXTUALLY_CONSISTENT`

표현 자체가 불분명하면 `AMBIGUOUS_TEXT`이고, 표현은 명확하지만 실제 상태 증거가
필요하면 `UNKNOWN_EXTERNAL_EVIDENCE_REQUIRED`입니다.

## 4. 세 문항 작성 예

다음 두 문장이 제시됐다고 가정합니다.

1. “보행자가 지나갈 때까지 정지한다.”
2. “이제 출발한다.”

작성 예는 다음과 같습니다.

- `시간적 요구=YES`: “~할 때까지”라는 유지ㆍ해제 조건이 있습니다.
- `행동열=STOP_OR_HOLD>ACCELERATE_OR_PROCEED`: 정지한 다음 진행합니다.
- `텍스트 관계=UNKNOWN_EXTERNAL_EVIDENCE_REQUIRED`: 보행자가 실제로 지나갔는지는
  영상이나 상태 정보가 필요합니다.

반대로 뒤 문장이 “보행자가 아직 횡단 중이므로 출발한다.”라고 명시하면 외부
증거 없이도 두 요구가 충돌하므로 `TEXTUAL_CONTRADICTION`입니다.

## 5. 판단하지 않는 것

- 차량이 실제로 정지하거나 출발했는지
- 보행자나 장애물이 실제로 사라졌는지
- 행동이 안전하거나 교통법규에 맞는지
- 사람 운전자의 행동이 정답 또는 최적인지
- 자동 파서가 텍스트를 잘 읽었는지

## 6. 저장 방법

세 판정 항목을 모두 입력해야 한 사례가 완료됩니다. 메모는 선택 사항입니다.
검토자 A는 `contract_review_A.csv`, 검토자 B는 `contract_review_B.csv`로 저장하고
`review/` 디렉터리에 둡니다. review ID나 CSV 헤더를 바꾸지 마십시오.

두 독립 CSV가 모두 준비된 뒤에만 불일치를 계산합니다. 합의 과정에서도 두 원본
CSV는 수정하거나 덮어쓰지 않습니다.
"""


def main() -> int:
    REVIEW_DIR.mkdir(parents=True, exist_ok=True, mode=0o700)
    REVIEW_DIR.chmod(0o700)
    if review_already_started(REVIEW_DIR):
        print(json.dumps({"packet_status": "REVIEW_ALREADY_STARTED"}, sort_keys=True))
        return 0
    items, mapping, stats = select_review_items(read_natural_windows(NATURAL_WINDOWS_PATH))
    protocol_path = REVIEW_DIR / "REVIEW_PROTOCOL.md"
    mapping_path = REVIEW_DIR / "adjudication-mapping.json"
    _write_restricted(protocol_path, _protocol())
    _write_restricted(mapping_path, json.dumps(mapping, indent=2, sort_keys=True) + "\n")
    artifact_paths = [protocol_path, mapping_path]
    for reviewer in ("A", "B"):
        path = REVIEW_DIR / f"REVIEW_{reviewer}.html"
        _write_restricted(
            path, build_contract_review_page(reviewer, order_for_reviewer(reviewer, items))
        )
        artifact_paths.append(path)
    manifest = {
        "packet_status": "WAITING_FOR_CONTRACT_REVIEW",
        "evidence_availability": "COC_TEXT_AND_RELATIVE_TIME_ONLY",
        "selection_seed": SELECTION_SEED,
        "review_order_seeds": REVIEW_SEEDS,
        "counts": stats,
        "failures": 0,
        "unknown": "NOT_APPLICABLE_NO_ACTUAL_STATE_JUDGMENT",
        "not_run": ["REVIEWER_ANSWERS", "AGREEMENT", "ADJUDICATION"],
        "artifacts": {
            path.name: {"bytes": path.stat().st_size, "sha256": _sha256(path)}
            for path in sorted(artifact_paths)
        },
    }
    packet_manifest = REVIEW_DIR / "packet-manifest.json"
    _write_restricted(packet_manifest, json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    print(
        json.dumps(
            {"packet_status": "WAITING_FOR_CONTRACT_REVIEW", "counts": stats}, sort_keys=True
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
