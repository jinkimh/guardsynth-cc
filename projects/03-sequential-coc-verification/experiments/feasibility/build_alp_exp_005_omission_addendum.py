#!/usr/bin/env python3
"""Build a static-first omission-only addendum for the unique-scene review."""

from __future__ import annotations

import base64
import html
import json
from pathlib import Path


ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "PROJECT_REGISTRY.json").is_file())
BATCH_ROOT = (
    ROOT
    / "artifacts/results/restricted/alp-exp-005"
    / "feasibility-batch-v0"
)
SOURCE_REVIEW = BATCH_ROOT / "unique-scene-grounding-v1"
SCENE_ROOT = BATCH_ROOT / "blind-review-v0/scene-inputs"
OUTPUT_ROOT = BATCH_ROOT / "omission-addendum-v1"
FIELDS = {
    "safety_relevant_omission": ["NONE", "MINOR", "CRITICAL", "UNCERTAIN"],
    "primary_visible_risk_addressed": ["YES", "PARTIAL", "NO", "NO_RELEVANT_RISK", "UNCERTAIN"],
    "overall_coc_completeness": ["COMPLETE", "PARTIAL", "INCOMPLETE", "UNCERTAIN"],
    "confidence": ["1", "2", "3"],
}
FIELD_NAMES = {
    "safety_relevant_omission": "CoC가 화면의 안전 관련 객체·위험을 누락했는가?",
    "primary_visible_risk_addressed": "CoC가 가장 중요한 가시적 위험을 다루는가?",
    "overall_coc_completeness": "가시적 장면에 대한 CoC의 전체 완전성",
    "confidence": "판단 신뢰도",
}
PRETTY = {
    "NONE": "누락 없음",
    "MINOR": "경미한 누락",
    "CRITICAL": "중요한 누락",
    "UNCERTAIN": "판단 유보",
    "YES": "충분히 다룸",
    "PARTIAL": "부분적으로 다룸",
    "NO": "다루지 못함",
    "NO_RELEVANT_RISK": "관련 위험 없음",
    "COMPLETE": "완전함",
    "INCOMPLETE": "불완전함",
    "1": "1 (낮음)",
    "2": "2 (중간)",
    "3": "3 (높음)",
}


def load_items() -> tuple[list[dict[str, str]], list[dict[str, object]]]:
    source_mapping = json.loads(
        (SOURCE_REVIEW / "adjudication-only/blind-mapping.json").read_text(encoding="utf-8")
    )
    items = []
    output_mapping = []
    for index, row in enumerate(source_mapping, start=1):
        review_id = f"UOM-{index:03d}"
        run_root = BATCH_ROOT / row["episode"] / f"seed-{row['seed']}"
        coc = (run_root / "generated_coc.txt").read_text(encoding="utf-8").strip()
        image = base64.b64encode(
            (SCENE_ROOT / f"{row['episode']}-model-input.jpg").read_bytes()
        ).decode("ascii")
        items.append(
            {
                "review_id": review_id,
                "coc": coc,
                "image": f"data:image/jpeg;base64,{image}",
            }
        )
        output_mapping.append(
            {
                "review_id": review_id,
                "source_grounding_review_id": row["review_id"],
                "episode": row["episode"],
                "seed": row["seed"],
            }
        )
    return items, output_mapping


def item_html(item: dict[str, str]) -> str:
    fieldsets = []
    for field, choices in FIELDS.items():
        options = "".join(
            f'<label><input type="radio" name="{field}" value="{value}"> '
            f"{html.escape(PRETTY[value])}</label>"
            for value in choices
        )
        fieldsets.append(
            f'<fieldset><legend>{html.escape(FIELD_NAMES[field])}</legend>'
            f'<div class="choices">{options}</div></fieldset>'
        )
    review_id = item["review_id"]
    return f'''<section class="item" data-review-id="{review_id}"><h2>{review_id}</h2>
<p class="coc">{html.escape(item["coc"])}</p>
<img class="scene" src="{item["image"]}" alt="{review_id} 모델 입력 프레임">
<form><div class="grid">{"".join(fieldsets)}</div><fieldset class="notes"><legend>누락 근거 메모</legend>
<textarea name="notes" maxlength="500" placeholder="경미/중요 누락 또는 판단 유보라면 객체와 위치를 기록하십시오."></textarea>
</fieldset></form></section>'''


def build_page(reviewer: str, items: list[dict[str, str]]) -> str:
    sections = "\n".join(item_html(item) for item in items)
    fields_json = json.dumps(FIELDS, separators=(",", ":"))
    ids_json = json.dumps([item["review_id"] for item in items], separators=(",", ":"))
    return f'''<!doctype html><html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; img-src data:; style-src 'unsafe-inline'; script-src 'unsafe-inline'">
<title>CoC 위험 누락 검토 {reviewer}</title><style>
:root{{--ink:#17202a;--muted:#66717d;--line:#d8dee6;--accent:#075985;--soft:#edf6f9;--ok:#166534;--bad:#9a3412}}*{{box-sizing:border-box}}
body{{margin:0;background:#f6f8fa;color:var(--ink);font-family:system-ui,-apple-system,"Noto Sans KR",sans-serif}}
header{{position:sticky;top:0;z-index:5;display:flex;gap:13px;align-items:center;padding:11px 18px;background:#fff;border-bottom:1px solid var(--line)}}
header h1{{font-size:18px;margin:0}}.grow{{flex:1}}button{{font:inherit;padding:9px 13px;border:0;border-radius:7px;background:var(--accent);color:#fff;cursor:pointer}}
main{{max-width:1500px;margin:16px auto;padding:0 18px 80px}}.instructions{{background:#fff;border:1px solid var(--line);border-radius:9px;padding:13px 16px;line-height:1.55}}
.warning{{color:var(--bad)}}.item{{background:#fff;border:1px solid var(--line);border-radius:10px;padding:18px;margin:18px 0}}.coc{{font-size:18px;line-height:1.6;padding:13px 15px;background:var(--soft);border-left:4px solid var(--accent)}}
.scene{{display:block;width:100%;height:auto;margin:12px 0 18px;border:1px solid var(--line)}}.grid{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px 18px}}
fieldset{{min-width:0;border:1px solid var(--line);border-radius:8px;padding:10px 12px 12px}}legend{{font-weight:700;padding:0 5px}}.choices{{display:flex;gap:8px 13px;flex-wrap:wrap}}label{{white-space:nowrap}}
.notes{{margin-top:12px}}textarea{{width:100%;min-height:70px;resize:vertical;padding:9px;font:inherit;border:1px solid #aab4bf;border-radius:7px}}progress{{width:220px;height:14px}}#saved.ok{{color:var(--ok)}}#saved.bad{{color:var(--bad)}}
@media(max-width:800px){{.grid{{grid-template-columns:1fr}}header{{position:static;flex-wrap:wrap}}}}</style></head><body>
<header><h1>CoC 가시적 위험 누락 · 검토자 {reviewer}</h1><progress id="progress" max="10"></progress><span id="progressText"></span><span id="saved"></span><span class="grow"></span><button id="export">CSV 저장</button></header>
<main><div class="instructions"><strong>이번 검토는 정확성이 아니라 누락만 평가합니다.</strong> 16개 입력 프레임에서 현재 운전 판단을 바꿀 수 있는 객체·위험을 CoC가 빠뜨렸는지 보십시오. 배경의 모든 차량·보행자를 열거할 필요는 없습니다. 미래 영상은 사용하지 않습니다. <span class="warning">종료 전 CSV를 저장하십시오.</span></div>{sections}</main>
<script>
const reviewer={json.dumps(reviewer)},fields={fields_json},reviewIds={ids_json},columns=["review_id",...Object.keys(fields),"notes"],storageKey=`alp-exp-005-omission-v1-${{reviewer}}`;let rows={{}};for(const id of reviewIds)rows[id]={{review_id:id}};
try{{const old=JSON.parse(localStorage.getItem(storageKey)||"{{}}");for(const id of reviewIds)Object.assign(rows[id],old[id]||{{}});}}catch(e){{}}
function complete(row){{return Object.keys(fields).every(k=>row[k]);}}function update(){{const done=reviewIds.filter(id=>complete(rows[id])).length;document.getElementById("progress").value=done;document.getElementById("progressText").textContent=`완료 ${{done}}/${{reviewIds.length}}`;}}
function save(){{for(const section of document.querySelectorAll(".item")){{const id=section.dataset.reviewId,fd=new FormData(section.querySelector("form")),row={{review_id:id}};for(const field of Object.keys(fields))row[field]=fd.get(field)||"";row.notes=fd.get("notes")||"";rows[id]=row;}}try{{localStorage.setItem(storageKey,JSON.stringify(rows));document.getElementById("saved").textContent="자동 저장됨";document.getElementById("saved").className="ok";}}catch(e){{document.getElementById("saved").textContent="자동 저장 불가";document.getElementById("saved").className="bad";}}update();}}
function restore(){{for(const section of document.querySelectorAll(".item")){{const row=rows[section.dataset.reviewId]||{{}};section.querySelectorAll("input[type=radio]").forEach(x=>x.checked=row[x.name]===x.value);section.querySelector("textarea").value=row.notes||"";}}update();}}
function cell(v){{const s=String(v??"");return /[",\\r\\n]/.test(s)?`"${{s.replace(/"/g,'""')}}"`:s;}}function exportCsv(){{save();const lines=[columns.join(",")];for(const id of reviewIds)lines.push(columns.map(c=>cell(rows[id][c]||"")).join(","));const blob=new Blob(["\\ufeff"+lines.join("\\r\\n")+"\\r\\n"],{{type:"text/csv;charset=utf-8"}});const a=document.createElement("a");a.href=URL.createObjectURL(blob);a.download=`omission_reviewer_${{reviewer}}.csv`;a.click();setTimeout(()=>URL.revokeObjectURL(a.href),1000);}}
document.addEventListener("change",save);document.addEventListener("input",save);document.getElementById("export").onclick=exportCsv;restore();
</script></body></html>'''


def main() -> int:
    items, mapping = load_items()
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True, mode=0o700)
    OUTPUT_ROOT.chmod(0o700)
    adjudication = OUTPUT_ROOT / "adjudication-only"
    adjudication.mkdir(parents=True, exist_ok=True, mode=0o700)
    adjudication.chmod(0o700)
    for reviewer in ("A", "B"):
        output = OUTPUT_ROOT / f"OMISSION_ADDENDUM_{reviewer}.html"
        output.write_text(build_page(reviewer, items), encoding="utf-8")
        output.chmod(0o600)
        print(f"wrote {output.relative_to(ROOT)} ({output.stat().st_size:,} bytes)")
    mapping_path = adjudication / "blind-mapping.json"
    mapping_path.write_text(json.dumps(mapping, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    mapping_path.chmod(0o600)
    readme = OUTPUT_ROOT / "README.md"
    readme.write_text(
        "# Omission-only addendum v1\n\n"
        "Classification: `LICENSE_RESTRICTED_INTERNAL_RESULT`\n\n"
        "Ten unique scenes, one fixed-seed CoC per scene. Review only visible, "
        "safety-relevant omissions. Do not relabel factual grounding and do not "
        "use future video or trajectory information. Reviewers A and B work independently.\n",
        encoding="utf-8",
    )
    readme.chmod(0o600)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
