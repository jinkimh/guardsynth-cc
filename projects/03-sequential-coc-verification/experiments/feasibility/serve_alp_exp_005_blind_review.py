#!/usr/bin/env python3
"""Serve one reviewer's blinded CoC labeling UI over a local HTTP endpoint.

The server intentionally exposes neither the blind mapping nor the other
reviewer's labels.  Its default loopback binding is designed for SSH port
forwarding from a remote workstation.
"""

from __future__ import annotations

import argparse
import base64
import csv
import hmac
import json
import os
import re
import secrets
import ssl
import tempfile
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "PROJECT_REGISTRY.json").is_file())
DEFAULT_REVIEW_ROOT = (
    ROOT
    / "artifacts/results/restricted/alp-exp-005"
    / "feasibility-batch-v0/blind-review-v0"
)
REVIEW_COLUMNS = [
    "review_id",
    "stated_longitudinal",
    "stated_lateral",
    "trajectory_longitudinal",
    "trajectory_lateral",
    "consistency",
    "temporal_ambiguity",
    "confidence",
    "notes",
]
CHOICES = {
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
PLOT_RE = re.compile(r"^/plots/(REV-\d{3}\.png)$")


APP_HTML = r"""<!doctype html>
<html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>CoC–Trajectory 블라인드 레이블링</title>
<style>
:root { color-scheme: light; --ink:#17202a; --muted:#68727d; --line:#d8dee6;
  --accent:#075985; --soft:#f0f7fa; --ok:#166534; --warn:#9a3412; }
* { box-sizing:border-box; }
body { margin:0; font-family:system-ui,-apple-system,"Noto Sans KR",sans-serif;
  color:var(--ink); background:#f6f8fa; }
header { position:sticky; top:0; z-index:3; padding:12px 20px; background:#fff;
  border-bottom:1px solid var(--line); display:flex; align-items:center; gap:16px; flex-wrap:wrap; }
header h1 { font-size:18px; margin:0; }
.grow { flex:1; }
button,.button,select { border:1px solid #aab4bf; border-radius:7px; background:#fff;
  padding:8px 12px; font:inherit; color:inherit; cursor:pointer; text-decoration:none; }
button.primary { color:#fff; background:var(--accent); border-color:var(--accent); }
button:disabled { opacity:.45; cursor:not-allowed; }
main { max-width:1180px; margin:18px auto; padding:0 18px 80px; }
.statusbar { display:flex; gap:16px; align-items:center; margin-bottom:12px; color:var(--muted); }
progress { width:220px; height:14px; }
.panel { background:#fff; border:1px solid var(--line); border-radius:10px; padding:18px;
  box-shadow:0 1px 2px rgba(0,0,0,.04); }
.coc { font-size:18px; line-height:1.65; background:var(--soft); border-left:4px solid var(--accent);
  padding:14px 16px; white-space:pre-wrap; }
.plot { display:block; width:100%; max-width:1000px; margin:12px auto 20px; }
.grid { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:14px 22px; }
fieldset { border:1px solid var(--line); border-radius:8px; padding:10px 12px 12px; min-width:0; }
legend { font-weight:700; padding:0 5px; }
.choices { display:flex; flex-wrap:wrap; gap:7px 12px; }
label.choice { white-space:nowrap; }
textarea { width:100%; min-height:78px; resize:vertical; padding:9px; font:inherit;
  border:1px solid #aab4bf; border-radius:7px; }
.footer { display:flex; align-items:center; gap:10px; margin-top:16px; }
#saveState { color:var(--muted); }
#saveState.ok { color:var(--ok); }
#saveState.bad { color:var(--warn); }
.notice { color:var(--warn); font-size:14px; }
@media (max-width:760px) { .grid { grid-template-columns:1fr; } header { position:static; } }
</style></head><body>
<header>
  <h1>CoC–Trajectory 블라인드 레이블링 · 검토자 <span id="reviewer"></span></h1>
  <span class="grow"></span>
  <label>항목 <select id="itemSelect"></select></label>
  <a class="button" href="/api/export">CSV 내려받기</a>
</header>
<main>
  <div class="statusbar"><progress id="progress" max="1" value="0"></progress>
    <span id="progressText"></span><span id="saveState"></span></div>
  <p class="notice">장면 진실, GT trajectory, minADE를 추측하지 마십시오. CoC가 말한 동작과 예측 궤적의 일치만 평가합니다.</p>
  <section class="panel">
    <h2 id="reviewId"></h2>
    <p class="coc" id="coc"></p>
    <img class="plot" id="plot" alt="예측 궤적 및 속도 도표">
    <form id="form"><div class="grid" id="fields"></div>
      <fieldset style="margin-top:14px"><legend>메모</legend>
        <textarea name="notes" maxlength="500" placeholder="UNCERTAIN인 이유나 판단 근거를 짧게 기록하십시오."></textarea>
      </fieldset>
    </form>
    <div class="footer">
      <button id="prev" type="button">← 이전</button>
      <button id="next" class="primary" type="button">다음 →</button>
      <span class="grow"></span><span>변경 사항은 서버에 자동 저장됩니다.</span>
    </div>
  </section>
</main>
<script>
const labels = {
  stated_longitudinal:"CoC 종방향 동작", stated_lateral:"CoC 횡방향 동작",
  trajectory_longitudinal:"궤적 종방향 동작", trajectory_lateral:"궤적 횡방향 동작",
  consistency:"CoC–궤적 일치", temporal_ambiguity:"시간적 모호성", confidence:"판단 신뢰도"
};
const pretty = {
  STOP:"정지", DECELERATE:"감속", YIELD:"양보", ACCELERATE:"가속",
  MAINTAIN_SPEED:"속도 유지", NONE:"언급 없음", UNCLEAR:"불명확",
  LEFT:"좌측", RIGHT:"우측", KEEP_LANE:"차선 유지",
  CONSISTENT:"일치", INCONSISTENT:"불일치", UNCERTAIN:"판단 유보",
  YES:"예", NO:"아니오", "1":"1 (낮음)", "2":"2 (중간)", "3":"3 (높음)"
};
let state, index=0, timer=null;
const required = Object.keys(labels);
function esc(s){ return String(s).replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c])); }
function complete(row){ return required.every(k=>row[k]); }
function buildFields(){
  const root=document.getElementById("fields"); root.innerHTML="";
  for(const [field, choices] of Object.entries(state.choices)){
    const fs=document.createElement("fieldset"); fs.innerHTML=`<legend>${esc(labels[field])}</legend>`;
    const box=document.createElement("div"); box.className="choices";
    for(const value of choices){
      const label=document.createElement("label"); label.className="choice";
      label.innerHTML=`<input type="radio" name="${esc(field)}" value="${esc(value)}"> ${esc(pretty[value]||value)}`;
      box.appendChild(label);
    }
    fs.appendChild(box); root.appendChild(fs);
  }
}
function formData(){
  const out={}; const fd=new FormData(document.getElementById("form"));
  for(const key of required) out[key]=fd.get(key)||"";
  out.notes=fd.get("notes")||""; return out;
}
function render(){
  const item=state.items[index], row=state.labels[item.review_id]||{};
  document.getElementById("reviewId").textContent=item.review_id;
  document.getElementById("coc").textContent=item.coc;
  document.getElementById("plot").src=item.image_url;
  document.getElementById("itemSelect").value=String(index);
  document.querySelectorAll("input[type=radio]").forEach(x=>x.checked=row[x.name]===x.value);
  document.querySelector("textarea[name=notes]").value=row.notes||"";
  document.getElementById("prev").disabled=index===0;
  document.getElementById("next").disabled=index===state.items.length-1;
  updateProgress(); window.scrollTo({top:0,behavior:"smooth"});
}
function updateProgress(){
  const done=state.items.filter(x=>complete(state.labels[x.review_id]||{})).length;
  document.getElementById("progress").max=state.items.length;
  document.getElementById("progress").value=done;
  document.getElementById("progressText").textContent=`완료 ${done}/${state.items.length}`;
}
async function save(){
  clearTimeout(timer); const item=state.items[index], body=formData();
  const status=document.getElementById("saveState"); status.textContent="저장 중…"; status.className="";
  try{
    const response=await fetch(`/api/labels/${item.review_id}`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(body)});
    if(!response.ok) throw new Error(await response.text());
    state.labels[item.review_id]=body; status.textContent="저장됨"; status.className="ok"; updateProgress();
  }catch(e){ status.textContent="저장 실패 — 다시 시도하십시오"; status.className="bad"; console.error(e); }
}
function schedule(){ clearTimeout(timer); timer=setTimeout(save,350); }
async function init(){
  const response=await fetch("/api/state"); if(!response.ok) throw new Error("상태를 읽을 수 없습니다.");
  state=await response.json(); document.getElementById("reviewer").textContent=state.reviewer;
  buildFields(); const select=document.getElementById("itemSelect");
  state.items.forEach((x,i)=>{ const o=document.createElement("option"); o.value=i; o.textContent=x.review_id; select.appendChild(o); });
  select.onchange=async()=>{ await save(); index=Number(select.value); render(); };
  document.getElementById("form").addEventListener("change",schedule);
  document.querySelector("textarea").addEventListener("input",schedule);
  document.getElementById("prev").onclick=async()=>{ await save(); index--; render(); };
  document.getElementById("next").onclick=async()=>{ await save(); index++; render(); };
  document.addEventListener("keydown",e=>{ if(e.altKey&&e.key==="ArrowLeft") document.getElementById("prev").click(); if(e.altKey&&e.key==="ArrowRight") document.getElementById("next").click(); });
  render();
}
init().catch(e=>{ document.body.textContent=e.message; });
</script></body></html>
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reviewer", required=True, choices=("A", "B"))
    parser.add_argument("--review-root", type=Path, default=DEFAULT_REVIEW_ROOT)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--access-token", help="Basic-auth password; a random token is generated if omitted")
    parser.add_argument("--tls-cert", type=Path, help="PEM certificate for HTTPS")
    parser.add_argument("--tls-key", type=Path, help="PEM private key for HTTPS")
    parser.add_argument(
        "--allow-non-loopback",
        action="store_true",
        help="Required to bind beyond localhost; use only behind HTTPS or another secure tunnel",
    )
    return parser.parse_args()


def load_csv(path: Path) -> dict[str, dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as stream:
        return {row["review_id"]: row for row in csv.DictReader(stream)}


def write_csv_atomic(path: Path, rows: dict[str, dict[str, str]]) -> None:
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", newline="", dir=path.parent, prefix=f".{path.name}.", delete=False
    ) as stream:
        temporary = Path(stream.name)
        writer = csv.DictWriter(stream, fieldnames=REVIEW_COLUMNS)
        writer.writeheader()
        for review_id in sorted(rows):
            writer.writerow({column: rows[review_id].get(column, "") for column in REVIEW_COLUMNS})
    temporary.chmod(0o600)
    os.replace(temporary, path)


def validate_label(payload: Any) -> dict[str, str]:
    if not isinstance(payload, dict):
        raise ValueError("JSON object required")
    result: dict[str, str] = {}
    for field, choices in CHOICES.items():
        value = payload.get(field, "")
        if value and value not in choices:
            raise ValueError(f"Invalid {field}")
        result[field] = value
    notes = payload.get("notes", "")
    if not isinstance(notes, str) or len(notes) > 500:
        raise ValueError("notes must be at most 500 characters")
    result["notes"] = notes
    return result


def build_items(review_root: Path) -> list[dict[str, str]]:
    mapping_path = review_root / "adjudication-only/blind-mapping.json"
    mapping = json.loads(mapping_path.read_text(encoding="utf-8"))
    batch_root = review_root.parent
    items = []
    for row in mapping:
        review_id = row["review_id"]
        coc_path = batch_root / row["episode"] / f"seed-{row['seed']}" / "generated_coc.txt"
        items.append(
            {
                "review_id": review_id,
                "coc": coc_path.read_text(encoding="utf-8").strip(),
                "image_url": f"/plots/{review_id}.png",
            }
        )
    return sorted(items, key=lambda item: item["review_id"])


def make_handler(
    *, review_root: Path, reviewer: str, access_token: str
) -> type[BaseHTTPRequestHandler]:
    csv_path = review_root / f"reviewer_{reviewer}.csv"
    items = build_items(review_root)
    valid_ids = {item["review_id"] for item in items}
    username = f"reviewer-{reviewer.lower()}"

    class ReviewHandler(BaseHTTPRequestHandler):
        server_version = "BlindReview/1.0"

        def log_message(self, format: str, *args: Any) -> None:
            super().log_message(format, *args)

        def authenticated(self) -> bool:
            header = self.headers.get("Authorization", "")
            if not header.startswith("Basic "):
                return False
            try:
                decoded = base64.b64decode(header[6:], validate=True).decode("utf-8")
                supplied_user, supplied_token = decoded.split(":", 1)
            except (ValueError, UnicodeDecodeError):
                return False
            return hmac.compare_digest(supplied_user, username) and hmac.compare_digest(
                supplied_token, access_token
            )

        def require_auth(self) -> bool:
            if self.authenticated():
                return True
            self.send_response(HTTPStatus.UNAUTHORIZED)
            self.send_header("WWW-Authenticate", f'Basic realm="CoC blind reviewer {reviewer}"')
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            return False

        def send_bytes(self, body: bytes, content_type: str, status: HTTPStatus = HTTPStatus.OK) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header(
                "Content-Security-Policy",
                "default-src 'self'; img-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'",
            )
            self.end_headers()
            self.wfile.write(body)

        def send_json(self, value: Any, status: HTTPStatus = HTTPStatus.OK) -> None:
            self.send_bytes(
                json.dumps(value, ensure_ascii=False).encode("utf-8"),
                "application/json; charset=utf-8",
                status,
            )

        def do_GET(self) -> None:
            if not self.require_auth():
                return
            path = urlparse(self.path).path
            if path == "/":
                self.send_bytes(APP_HTML.encode("utf-8"), "text/html; charset=utf-8")
                return
            if path == "/api/state":
                self.send_json(
                    {
                        "reviewer": reviewer,
                        "choices": CHOICES,
                        "items": items,
                        "labels": load_csv(csv_path),
                    }
                )
                return
            if path == "/api/export":
                body = csv_path.read_bytes()
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", "text/csv; charset=utf-8")
                self.send_header("Content-Disposition", f'attachment; filename="reviewer_{reviewer}.csv"')
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(body)
                return
            match = PLOT_RE.fullmatch(path)
            if match and match.group(1)[:-4] in valid_ids:
                self.send_bytes((review_root / "plots" / match.group(1)).read_bytes(), "image/png")
                return
            self.send_json({"error": "not found"}, HTTPStatus.NOT_FOUND)

        def do_POST(self) -> None:
            if not self.require_auth():
                return
            path = urlparse(self.path).path
            match = re.fullmatch(r"/api/labels/(REV-\d{3})", path)
            if not match or match.group(1) not in valid_ids:
                self.send_json({"error": "not found"}, HTTPStatus.NOT_FOUND)
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if length > 4096:
                    raise ValueError("request too large")
                payload = json.loads(self.rfile.read(length))
                label = validate_label(payload)
                rows = load_csv(csv_path)
                rows[match.group(1)].update(label)
                write_csv_atomic(csv_path, rows)
            except (ValueError, json.JSONDecodeError) as error:
                self.send_json({"error": str(error)}, HTTPStatus.BAD_REQUEST)
                return
            self.send_json({"saved": True, "review_id": match.group(1)})

    return ReviewHandler


def main() -> int:
    args = parse_args()
    if args.host not in {"127.0.0.1", "localhost", "::1"} and not args.allow_non_loopback:
        raise SystemExit("Refusing non-loopback binding without --allow-non-loopback")
    if bool(args.tls_cert) != bool(args.tls_key):
        raise SystemExit("--tls-cert and --tls-key must be supplied together")
    if args.host not in {"127.0.0.1", "localhost", "::1"} and not args.tls_cert:
        raise SystemExit("Refusing non-loopback Basic auth without HTTPS")
    if not args.review_root.is_dir():
        raise SystemExit(f"Review root not found: {args.review_root}")
    token = args.access_token or secrets.token_urlsafe(18)
    handler = make_handler(
        review_root=args.review_root.resolve(), reviewer=args.reviewer, access_token=token
    )
    server = ThreadingHTTPServer((args.host, args.port), handler)
    scheme = "http"
    if args.tls_cert:
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.minimum_version = ssl.TLSVersion.TLSv1_2
        context.load_cert_chain(args.tls_cert, args.tls_key)
        server.socket = context.wrap_socket(server.socket, server_side=True)
        scheme = "https"
    print("CoC blind labeling server")
    print(f"  reviewer: {args.reviewer}")
    print(f"  URL:      {scheme}://{args.host}:{args.port}/")
    print(f"  username: reviewer-{args.reviewer.lower()}")
    print(f"  password: {token}")
    if args.host in {"127.0.0.1", "localhost", "::1"}:
        print("Use an SSH tunnel to reach this loopback-only service remotely.")
    else:
        print("Restricted HTTPS endpoint: share the URL and credentials only with the assigned reviewer.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
