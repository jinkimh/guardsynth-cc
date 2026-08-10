#!/usr/bin/env python3
"""Build offline, static-first CoC scene-grounding labeling applications."""

from __future__ import annotations

import base64
import html
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
REVIEW_ROOT = (
    ROOT
    / "artifacts/results/restricted/alp-exp-005"
    / "feasibility-batch-v0/blind-review-v0"
)
FIELDS = {
    "mentioned_entities_visible": [
        "ALL_VISIBLE", "PARTIAL_VISIBLE", "NONE_VISIBLE", "NO_ENTITY_CLAIM", "UNCLEAR"
    ],
    "described_relations_supported": [
        "SUPPORTED", "CONTRADICTED", "NOT_EVALUABLE", "NO_RELATION_CLAIM", "UNCLEAR"
    ],
    "stated_action_visually_justified": ["SUPPORTED", "NOT_SUPPORTED", "NOT_EVALUABLE", "UNCLEAR"],
    "overall_grounding": ["SUPPORTED", "PARTIAL", "UNSUPPORTED", "UNCERTAIN"],
    "confidence": ["1", "2", "3"],
}
FIELD_NAMES = {
    "mentioned_entities_visible": "언급된 객체가 입력 프레임에서 보이는가?",
    "described_relations_supported": "CoC의 공간·상호작용 관계가 지지되는가?",
    "stated_action_visually_justified": "CoC가 제시한 동작이 시각적으로 정당화되는가?",
    "overall_grounding": "전체 CoC 장면 grounding",
    "confidence": "판단 신뢰도",
}
PRETTY = {
    "ALL_VISIBLE": "모두 보임",
    "PARTIAL_VISIBLE": "일부만 보임",
    "NONE_VISIBLE": "보이지 않음",
    "NO_ENTITY_CLAIM": "객체 주장 없음",
    "SUPPORTED": "지지됨",
    "CONTRADICTED": "모순됨",
    "NOT_SUPPORTED": "지지되지 않음",
    "NOT_EVALUABLE": "평가 불가",
    "NO_RELATION_CLAIM": "관계 주장 없음",
    "UNCLEAR": "불명확",
    "PARTIAL": "부분 지지",
    "UNSUPPORTED": "지지되지 않음",
    "UNCERTAIN": "판단 유보",
    "1": "1 (낮음)",
    "2": "2 (중간)",
    "3": "3 (높음)",
}


def load_items() -> list[dict[str, str]]:
    mapping = json.loads(
        (REVIEW_ROOT / "adjudication-only/blind-mapping.json").read_text(encoding="utf-8")
    )
    batch_root = REVIEW_ROOT.parent
    items = []
    for row in mapping:
        review_id = row["review_id"]
        coc = (
            batch_root / row["episode"] / f"seed-{row['seed']}" / "generated_coc.txt"
        ).read_text(encoding="utf-8").strip()
        scene_path = REVIEW_ROOT / "scene-inputs" / f"{row['episode']}-model-input.jpg"
        scene = base64.b64encode(scene_path.read_bytes()).decode("ascii")
        items.append(
            {
                "review_id": review_id,
                "coc": coc,
                "scene": f"data:image/jpeg;base64,{scene}",
            }
        )
    return sorted(items, key=lambda item: item["review_id"])


def item_html(item: dict[str, str]) -> str:
    fields = []
    for field, choices in FIELDS.items():
        options = "".join(
            f'<label><input type="radio" name="{field}" value="{choice}"> '
            f"{html.escape(PRETTY[choice])}</label>"
            for choice in choices
        )
        fields.append(
            f'<fieldset><legend>{html.escape(FIELD_NAMES[field])}</legend>'
            f'<div class="choices">{options}</div></fieldset>'
        )
    review_id = item["review_id"]
    return f'''<section class="item" id="{review_id}" data-review-id="{review_id}">
<h2>{review_id}</h2>
<p class="coc">{html.escape(item["coc"])}</p>
<p class="caption">Alpamayo가 실제로 본 입력: 4개 카메라 × t0 직전 4개 시점</p>
<img class="scene" src="{item["scene"]}" alt="{review_id} 다중 카메라 입력 프레임">
<form><div class="grid">{"".join(fields)}</div>
<fieldset class="notes"><legend>메모</legend><textarea name="notes" maxlength="500"
placeholder="보이는 객체와 보이지 않는 객체, 모순 또는 판단 유보의 이유를 기록하십시오."></textarea></fieldset>
</form></section>'''


def build_page(reviewer: str, items: list[dict[str, str]]) -> str:
    fields_json = json.dumps(FIELDS, separators=(",", ":"))
    review_ids_json = json.dumps([item["review_id"] for item in items], separators=(",", ":"))
    sections = "\n".join(item_html(item) for item in items)
    return f'''<!doctype html><html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; img-src data:; style-src 'unsafe-inline'; script-src 'unsafe-inline'">
<title>CoC 장면 Grounding 블라인드 검토 {reviewer}</title><style>
:root{{--ink:#17202a;--muted:#66717d;--line:#d8dee6;--accent:#075985;--soft:#edf6f9;--ok:#166534;--bad:#9a3412}}
*{{box-sizing:border-box}}body{{margin:0;background:#f6f8fa;color:var(--ink);font-family:system-ui,-apple-system,"Noto Sans KR",sans-serif}}
header{{position:sticky;top:0;z-index:5;display:flex;gap:14px;align-items:center;padding:11px 18px;background:#fff;border-bottom:1px solid var(--line)}}
header h1{{font-size:18px;margin:0}}.grow{{flex:1}}button{{font:inherit;padding:9px 13px;border:1px solid var(--accent);border-radius:7px;background:var(--accent);color:#fff;cursor:pointer}}
main{{max-width:1500px;margin:16px auto;padding:0 18px 80px}}.instructions{{background:#fff;border:1px solid var(--line);border-radius:9px;padding:13px 16px;line-height:1.55}}
.warning{{color:var(--bad)}}.item{{background:#fff;border:1px solid var(--line);border-radius:10px;padding:18px;margin:18px 0;box-shadow:0 1px 2px #0000000a}}
.coc{{font-size:18px;line-height:1.6;white-space:pre-wrap;padding:13px 15px;background:var(--soft);border-left:4px solid var(--accent)}}
.caption{{color:var(--muted)}}.scene{{display:block;width:100%;height:auto;margin:10px auto 18px;border:1px solid var(--line)}}
.grid{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px 18px}}fieldset{{min-width:0;border:1px solid var(--line);border-radius:8px;padding:10px 12px 12px}}
legend{{font-weight:700;padding:0 5px}}.choices{{display:flex;gap:8px 13px;flex-wrap:wrap}}label{{white-space:nowrap}}.notes{{margin-top:12px}}textarea{{width:100%;min-height:70px;resize:vertical;padding:9px;font:inherit;border:1px solid #aab4bf;border-radius:7px}}
#saved.ok{{color:var(--ok)}}#saved.bad{{color:var(--bad)}}progress{{width:220px;height:14px}}@media(max-width:800px){{.grid{{grid-template-columns:1fr}}header{{position:static;flex-wrap:wrap}}}}
</style></head><body><header><h1>CoC 장면 Grounding · 검토자 {reviewer}</h1><progress id="progress" max="14"></progress><span id="progressText"></span><span id="saved"></span><span class="grow"></span><button id="export">CSV 저장</button></header>
<main><div class="instructions"><strong>판단 대상:</strong> CoC의 객체·관계·행동 근거가 모델이 실제로 본 16개 입력 프레임에서 지지되는지 평가합니다.
미래 영상과 예측·정답 trajectory는 보지 않습니다. <span class="warning">작업 종료 전 반드시 CSV 저장을 누르십시오.</span></div>{sections}</main>
<script>
const reviewer={json.dumps(reviewer)}, fields={fields_json}, reviewIds={review_ids_json};
const columns=["review_id",...Object.keys(fields),"notes"], storageKey=`alp-exp-005-grounding-v0-${{reviewer}}`;
let rows={{}};for(const id of reviewIds)rows[id]={{review_id:id}};
try{{const old=JSON.parse(localStorage.getItem(storageKey)||"{{}}");for(const id of reviewIds)Object.assign(rows[id],old[id]||{{}});}}catch(e){{}}
function complete(row){{return Object.keys(fields).every(k=>row[k]);}}
function update(){{const done=reviewIds.filter(id=>complete(rows[id])).length;document.getElementById("progress").value=done;document.getElementById("progressText").textContent=`완료 ${{done}}/${{reviewIds.length}}`;}}
function save(){{for(const section of document.querySelectorAll(".item")){{const id=section.dataset.reviewId,fd=new FormData(section.querySelector("form")),row={{review_id:id}};for(const field of Object.keys(fields))row[field]=fd.get(field)||"";row.notes=fd.get("notes")||"";rows[id]=row;}}try{{localStorage.setItem(storageKey,JSON.stringify(rows));document.getElementById("saved").textContent="자동 저장됨";document.getElementById("saved").className="ok";}}catch(e){{document.getElementById("saved").textContent="자동 저장 불가 — CSV 저장 필요";document.getElementById("saved").className="bad";}}update();}}
function restore(){{for(const section of document.querySelectorAll(".item")){{const row=rows[section.dataset.reviewId]||{{}};section.querySelectorAll("input[type=radio]").forEach(x=>x.checked=row[x.name]===x.value);section.querySelector("textarea").value=row.notes||"";}}update();}}
function cell(v){{const s=String(v??"");return /[",\\r\\n]/.test(s)?`"${{s.replace(/"/g,'""')}}"`:s;}}
function exportCsv(){{save();const lines=[columns.join(",")];for(const id of reviewIds)lines.push(columns.map(c=>cell(rows[id][c]||"")).join(","));const blob=new Blob(["\\ufeff"+lines.join("\\r\\n")+"\\r\\n"],{{type:"text/csv;charset=utf-8"}});const a=document.createElement("a");a.href=URL.createObjectURL(blob);a.download=`grounding_reviewer_${{reviewer}}.csv`;a.click();setTimeout(()=>URL.revokeObjectURL(a.href),1000);}}
document.addEventListener("change",save);document.addEventListener("input",save);document.getElementById("export").onclick=exportCsv;restore();
</script></body></html>'''


def main() -> int:
    items = load_items()
    for reviewer in ("A", "B"):
        output = REVIEW_ROOT / f"GROUNDING_APP_{reviewer}_STANDALONE.html"
        output.write_text(build_page(reviewer, items), encoding="utf-8")
        output.chmod(0o600)
        print(f"wrote {output.relative_to(ROOT)} ({output.stat().st_size:,} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
