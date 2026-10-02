#!/usr/bin/env python3
"""Build offline, single-file blind labeling apps for reviewers A and B."""

from __future__ import annotations

import base64
import json
from pathlib import Path


ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "PROJECT_REGISTRY.json").is_file())
REVIEW_ROOT = (
    ROOT
    / "artifacts/results/restricted/alp-exp-005"
    / "feasibility-batch-v0/blind-review-v0"
)
FIELDS = {
    "stated_longitudinal": [
        "STOP", "DECELERATE", "YIELD", "ACCELERATE", "MAINTAIN_SPEED", "NONE", "UNCLEAR"
    ],
    "stated_lateral": ["LEFT", "RIGHT", "KEEP_LANE", "NONE", "UNCLEAR"],
    "trajectory_longitudinal": [
        "STOP", "DECELERATE", "YIELD", "ACCELERATE", "MAINTAIN_SPEED", "NONE", "UNCLEAR"
    ],
    "trajectory_lateral": ["LEFT", "RIGHT", "KEEP_LANE", "UNCLEAR"],
    "consistency": ["CONSISTENT", "INCONSISTENT", "UNCERTAIN"],
    "temporal_ambiguity": ["YES", "NO"],
    "confidence": ["1", "2", "3"],
}


HTML_TEMPLATE = r'''<!doctype html>
<html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; img-src data:; style-src 'unsafe-inline'; script-src 'unsafe-inline'">
<title>오프라인 CoC 블라인드 레이블링</title>
<style>
:root { --ink:#17202a; --muted:#66717d; --line:#d8dee6; --accent:#075985;
  --soft:#edf6f9; --good:#166534; --bad:#9a3412; }
*{box-sizing:border-box} body{margin:0;background:#f6f8fa;color:var(--ink);
font-family:system-ui,-apple-system,"Noto Sans KR",sans-serif}
header{position:sticky;top:0;z-index:4;display:flex;align-items:center;gap:10px;flex-wrap:wrap;
padding:11px 18px;background:#fff;border-bottom:1px solid var(--line)}
header h1{font-size:18px;margin:0}.grow{flex:1}button,.button,select{font:inherit;padding:8px 11px;
border:1px solid #a9b4bf;border-radius:7px;background:#fff;color:inherit;cursor:pointer}
button.primary{background:var(--accent);border-color:var(--accent);color:#fff}button:disabled{opacity:.45}
main{max-width:1160px;margin:18px auto;padding:0 18px 80px}.status{display:flex;gap:12px;
align-items:center;color:var(--muted);margin-bottom:10px}progress{width:220px;height:14px}
.notice{font-size:14px;color:var(--bad)}.panel{background:#fff;border:1px solid var(--line);
border-radius:10px;padding:18px;box-shadow:0 1px 2px #0000000a}.coc{font-size:18px;line-height:1.65;
white-space:pre-wrap;padding:14px 16px;background:var(--soft);border-left:4px solid var(--accent)}
.plot{display:block;width:100%;max-width:1000px;margin:12px auto 20px}.grid{display:grid;
grid-template-columns:repeat(2,minmax(0,1fr));gap:14px 22px}fieldset{min-width:0;border:1px solid var(--line);
border-radius:8px;padding:10px 12px 12px}legend{font-weight:700;padding:0 5px}.choices{display:flex;
gap:7px 12px;flex-wrap:wrap}.choice{white-space:nowrap}textarea{width:100%;min-height:78px;resize:vertical;
padding:9px;font:inherit;border:1px solid #aab4bf;border-radius:7px}.footer{display:flex;align-items:center;
gap:10px;margin-top:16px}#saved.good{color:var(--good)}#saved.bad{color:var(--bad)}
.instructions{font-size:14px;background:#fff;border:1px solid var(--line);border-radius:8px;padding:10px 14px;margin-bottom:12px}
@media(max-width:760px){.grid{grid-template-columns:1fr}header{position:static}}
</style></head><body>
<header><h1>오프라인 CoC–Trajectory 레이블링 · 검토자 <span id="reviewer"></span></h1>
<span class="grow"></span><label>항목 <select id="jump"></select></label>
<button id="importButton" type="button">CSV 불러오기</button><input id="importFile" type="file" accept=".csv,text/csv" hidden>
<button id="exportButton" class="primary" type="button">CSV 저장</button></header>
<main><div class="status"><progress id="progress" max="1"></progress><span id="progressText"></span>
<span id="saved"></span></div>
<div class="instructions"><strong>평가 범위:</strong> CoC가 말한 동작이 예측 6.4초 궤적에 표현되는지만 판단하십시오.
장면의 사실성이나 숨겨진 평가 정보를 추측하지 마십시오. 이 파일은 네트워크 요청을 하지 않습니다.</div>
<p class="notice">브라우저 저장소에 자동 임시 저장됩니다. 작업 종료 전 반드시 ‘CSV 저장’을 눌러 결과 파일을 보관하십시오.</p>
<section class="panel"><h2 id="reviewId"></h2><p class="coc" id="coc"></p>
<img class="plot" id="plot" alt="예측 궤적 및 속도 도표">
<form id="form"><div class="grid" id="fields"></div><fieldset style="margin-top:14px"><legend>메모</legend>
<textarea name="notes" maxlength="500" placeholder="판단 유보의 이유나 판단 근거를 짧게 기록하십시오."></textarea>
</fieldset></form><div class="footer"><button id="prev" type="button">← 이전</button>
<button id="next" class="primary" type="button">다음 →</button><span class="grow"></span>
<span>Alt+← / Alt+→로 이동할 수 있습니다.</span></div></section></main>
<script>
const reviewer=__REVIEWER__;
const items=__ITEMS__;
const choices=__FIELDS__;
const columns=["review_id",...Object.keys(choices),"notes"];
const storageKey=`alp-exp-005-blind-review-v0-${reviewer}`;
const fieldNames={stated_longitudinal:"CoC 종방향 동작",stated_lateral:"CoC 횡방향 동작",
trajectory_longitudinal:"궤적 종방향 동작",trajectory_lateral:"궤적 횡방향 동작",
consistency:"CoC–궤적 일치",temporal_ambiguity:"시간적 모호성",confidence:"판단 신뢰도"};
const pretty={STOP:"정지",DECELERATE:"감속",YIELD:"양보",ACCELERATE:"가속",
MAINTAIN_SPEED:"속도 유지",NONE:"언급 없음",UNCLEAR:"불명확",LEFT:"좌측",RIGHT:"우측",
KEEP_LANE:"차선 유지",CONSISTENT:"일치",INCONSISTENT:"불일치",UNCERTAIN:"판단 유보",
YES:"예",NO:"아니오","1":"1 (낮음)","2":"2 (중간)","3":"3 (높음)"};
let index=0, rows={};
function blankRows(){const out={};for(const x of items){out[x.review_id]={review_id:x.review_id};}return out;}
function loadLocal(){rows=blankRows();try{const value=localStorage.getItem(storageKey);if(value){const saved=JSON.parse(value);for(const id in rows)Object.assign(rows[id],saved[id]||{});}}catch(e){showSaved("브라우저 자동 저장을 사용할 수 없음",false);}}
function saveLocal(){try{localStorage.setItem(storageKey,JSON.stringify(rows));showSaved("자동 저장됨",true);}catch(e){showSaved("자동 저장 실패 — CSV로 저장하십시오",false);}}
function showSaved(text,good){const x=document.getElementById("saved");x.textContent=text;x.className=good?"good":"bad";}
function escapeHtml(s){return String(s).replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));}
function buildFields(){const root=document.getElementById("fields");for(const [field,values] of Object.entries(choices)){
const fs=document.createElement("fieldset");fs.innerHTML=`<legend>${escapeHtml(fieldNames[field])}</legend>`;
const box=document.createElement("div");box.className="choices";for(const value of values){const label=document.createElement("label");
label.className="choice";label.innerHTML=`<input type="radio" name="${field}" value="${value}"> ${escapeHtml(pretty[value]||value)}`;
box.appendChild(label);}fs.appendChild(box);root.appendChild(fs);}}
function capture(){const id=items[index].review_id,row={review_id:id},fd=new FormData(document.getElementById("form"));
for(const field of Object.keys(choices))row[field]=fd.get(field)||"";row.notes=fd.get("notes")||"";rows[id]=row;saveLocal();updateProgress();}
function complete(row){return Object.keys(choices).every(k=>row[k]);}
function updateProgress(){const done=items.filter(x=>complete(rows[x.review_id]||{})).length;
document.getElementById("progress").max=items.length;document.getElementById("progress").value=done;
document.getElementById("progressText").textContent=`완료 ${done}/${items.length}`;}
function render(){const item=items[index],row=rows[item.review_id]||{};document.getElementById("reviewId").textContent=item.review_id;
document.getElementById("coc").textContent=item.coc;document.getElementById("plot").src=item.image;
document.getElementById("jump").value=String(index);document.querySelectorAll("input[type=radio]").forEach(x=>x.checked=row[x.name]===x.value);
document.querySelector("textarea").value=row.notes||"";document.getElementById("prev").disabled=index===0;
document.getElementById("next").disabled=index===items.length-1;updateProgress();window.scrollTo({top:0,behavior:"smooth"});}
function csvCell(value){const s=String(value??"");return /[",\r\n]/.test(s)?`"${s.replace(/"/g,'""')}"`:s;}
function exportCsv(){capture();const lines=[columns.join(",")];for(const item of items){const row=rows[item.review_id]||{};
lines.push(columns.map(c=>csvCell(row[c]||"")).join(","));}const blob=new Blob(["\ufeff"+lines.join("\r\n")+"\r\n"],{type:"text/csv;charset=utf-8"});
const a=document.createElement("a");a.href=URL.createObjectURL(blob);a.download=`reviewer_${reviewer}.csv`;a.click();setTimeout(()=>URL.revokeObjectURL(a.href),1000);showSaved("CSV 저장 완료",true);}
function parseCsv(text){const table=[],row=[];let cell="",quoted=false;for(let i=0;i<text.length;i++){const c=text[i];if(quoted){if(c==='"'&&text[i+1]==='"'){cell+='"';i++;}else if(c==='"')quoted=false;else cell+=c;}else if(c==='"')quoted=true;else if(c===','){row.push(cell);cell="";}else if(c==='\n'){row.push(cell.replace(/\r$/, ""));table.push(row.splice(0));cell="";}else cell+=c;}if(cell||row.length){row.push(cell);table.push(row);}return table;}
function importCsv(file){const reader=new FileReader();reader.onload=()=>{try{const table=parseCsv(String(reader.result).replace(/^\ufeff/,""));
const header=table.shift();if(!header||header.join("|")!==columns.join("|"))throw new Error("열 구성이 맞지 않습니다.");
const imported=blankRows();for(const values of table){if(!values.length||!values[0])continue;const row={};header.forEach((h,i)=>row[h]=values[i]||"");
if(!(row.review_id in imported))throw new Error(`알 수 없는 항목: ${row.review_id}`);imported[row.review_id]=row;}rows=imported;saveLocal();render();showSaved("CSV 불러오기 완료",true);}catch(e){showSaved(`CSV 오류: ${e.message}`,false);}};reader.readAsText(file);}
function init(){document.getElementById("reviewer").textContent=reviewer;buildFields();loadLocal();const jump=document.getElementById("jump");
items.forEach((x,i)=>{const o=document.createElement("option");o.value=i;o.textContent=x.review_id;jump.appendChild(o);});
document.getElementById("form").addEventListener("change",capture);document.querySelector("textarea").addEventListener("input",capture);
jump.onchange=()=>{capture();index=Number(jump.value);render();};document.getElementById("prev").onclick=()=>{capture();index--;render();};
document.getElementById("next").onclick=()=>{capture();index++;render();};document.getElementById("exportButton").onclick=exportCsv;
document.getElementById("importButton").onclick=()=>document.getElementById("importFile").click();document.getElementById("importFile").onchange=e=>{if(e.target.files[0])importCsv(e.target.files[0]);};
document.addEventListener("keydown",e=>{if(e.altKey&&e.key==="ArrowLeft"&&!document.getElementById("prev").disabled)document.getElementById("prev").click();if(e.altKey&&e.key==="ArrowRight"&&!document.getElementById("next").disabled)document.getElementById("next").click();});render();}
init();
</script></body></html>'''


def build_items() -> list[dict[str, str]]:
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
        image = base64.b64encode((REVIEW_ROOT / "plots" / f"{review_id}.png").read_bytes()).decode()
        items.append({"review_id": review_id, "coc": coc, "image": f"data:image/png;base64,{image}"})
    return sorted(items, key=lambda item: item["review_id"])


def javascript_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c")


def main() -> int:
    items = build_items()
    for reviewer in ("A", "B"):
        page = HTML_TEMPLATE.replace("__REVIEWER__", javascript_json(reviewer))
        page = page.replace("__ITEMS__", javascript_json(items))
        page = page.replace("__FIELDS__", javascript_json(FIELDS))
        output = REVIEW_ROOT / f"LABELING_APP_{reviewer}_STANDALONE.html"
        output.write_text(page, encoding="utf-8")
        output.chmod(0o600)
        print(f"wrote {output.relative_to(ROOT)} ({output.stat().st_size:,} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
