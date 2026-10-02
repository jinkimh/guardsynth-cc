#!/usr/bin/env python3
"""Build standalone blinded review apps for phase-aware CoC alignment."""

from __future__ import annotations

import base64
import html
import json
import random
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "PROJECT_REGISTRY.json").is_file())
BATCH_ROOT = (
    ROOT
    / "artifacts/results/restricted/alp-exp-005"
    / "feasibility-batch-v0"
)
ANALYSIS = BATCH_ROOT / "phase-aware-alignment-v1/analysis.json"
SCENE_ROOT = BATCH_ROOT / "blind-review-v0/scene-inputs"
OUTPUT_ROOT = BATCH_ROOT / "phase-aware-review-v1"
RANDOMIZATION_SEED = 20260803

FIELDS = {
    "response_phase": ["SUPPORTED", "CONTRADICTED", "UNCERTAIN"],
    "later_phase_relation": [
        "ALLOWED_OR_NOT_SPECIFIED",
        "CONTRADICTS_COC",
        "REQUIRES_RELEASE_EVIDENCE",
        "UNCERTAIN",
    ],
    "overall_action_alignment": ["CONSISTENT", "INCONSISTENT", "UNKNOWN"],
    "threshold_sensitive": ["YES", "NO", "UNCERTAIN"],
    "confidence": ["1", "2", "3"],
}

FIELD_NAMES = {
    "response_phase": "CoC가 말한 최초 response가 6.4초 trajectory 안에 나타나는가?",
    "later_phase_relation": "후속 재가속·복귀·차선변경은 CoC와 어떤 관계인가?",
    "overall_action_alignment": "CoC–trajectory 행동 정합성 최종 판정",
    "threshold_sensitive": "판정이 감속량·횡이동량 threshold에 민감한가?",
    "confidence": "판단 신뢰도",
}

PRETTY = {
    "SUPPORTED": "나타남",
    "CONTRADICTED": "나타나지 않음",
    "UNCERTAIN": "판단 유보",
    "ALLOWED_OR_NOT_SPECIFIED": "허용되거나 CoC가 후속 국면을 명시하지 않음",
    "CONTRADICTS_COC": "CoC와 모순",
    "REQUIRES_RELEASE_EVIDENCE": "hazard 해제·clearance 증거가 필요",
    "CONSISTENT": "정합",
    "INCONSISTENT": "불일치",
    "UNKNOWN": "증거 부족",
    "YES": "예",
    "NO": "아니오",
    "1": "1 (낮음)",
    "2": "2 (중간)",
    "3": "3 (높음)",
}


def encode(path: Path, mime: str) -> str:
    return f"data:{mime};base64," + base64.b64encode(path.read_bytes()).decode("ascii")


def temporal_series(
    points: np.ndarray, rotations: np.ndarray
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return time, signed along-heading speed and flattened future positions."""
    points = np.asarray(points, dtype=float).reshape(64, 3)
    rotations = np.asarray(rotations, dtype=float).reshape(64, 3, 3)
    time = np.arange(1, 65, dtype=float) * 0.1
    displacement = np.diff(np.vstack((np.zeros((1, 3)), points)), axis=0)[:, :2]
    future_heading = rotations[:, :2, 0]
    previous_heading = np.vstack((np.array([[1.0, 0.0]]), future_heading[:-1]))
    interval_heading = previous_heading + future_heading
    norms = np.linalg.norm(interval_heading, axis=1, keepdims=True)
    interval_heading = interval_heading / np.maximum(norms, 1e-12)
    signed_speed = np.sum(displacement * interval_heading, axis=1) / 0.1
    return time, signed_speed, points


def make_temporal_plot(points: np.ndarray, rotations: np.ndarray, output: Path) -> dict[str, float]:
    time, signed_speed, points = temporal_series(points, rotations)
    figure, axes = plt.subplots(2, 2, figsize=(12, 8))

    axes[0, 0].plot(time, points[:, 0], color="#1f77b4", linewidth=2)
    axes[0, 0].axhline(0, color="black", linewidth=0.8, linestyle="--")
    axes[0, 0].set(title="Forward position vs time", xlabel="Time from t0 (s)", ylabel="x (m; forward +)")

    axes[0, 1].plot(time, signed_speed, color="#ff7f0e", linewidth=2)
    axes[0, 1].axhline(0, color="black", linewidth=0.8, linestyle="--")
    axes[0, 1].fill_between(time, signed_speed, 0, where=signed_speed < 0, color="#dc2626", alpha=0.22, label="reverse")
    axes[0, 1].set(title="Signed longitudinal speed", xlabel="Time from t0 (s)", ylabel="m/s; forward +, reverse −")
    axes[0, 1].legend(fontsize=8)

    axes[1, 0].plot(time, points[:, 1], color="#2ca02c", linewidth=2)
    axes[1, 0].axhline(0, color="black", linewidth=0.8, linestyle="--")
    axes[1, 0].set(title="Lateral position vs time", xlabel="Time from t0 (s)", ylabel="y (m; left +)")

    scatter = axes[1, 1].scatter(points[:, 0], points[:, 1], c=time, cmap="viridis", s=18)
    axes[1, 1].plot(points[:, 0], points[:, 1], color="#64748b", linewidth=0.8, alpha=0.7)
    axes[1, 1].scatter([0], [0], color="black", marker="x", s=55, label="t0")
    axes[1, 1].scatter([points[-1, 0]], [points[-1, 1]], color="#dc2626", s=45, label="6.4 s")
    for second in range(1, 7):
        index = second * 10 - 1
        axes[1, 1].annotate(f"{second}s", (points[index, 0], points[index, 1]), fontsize=7)
    axes[1, 1].set(title="Plan view (color = time)", xlabel="x (m; forward +)", ylabel="y (m; left +)")
    axes[1, 1].legend(fontsize=8)
    figure.colorbar(scatter, ax=axes[1, 1], label="Time from t0 (s)")

    for axis in axes.flat:
        axis.grid(alpha=0.25)
    figure.tight_layout()
    figure.savefig(output, dpi=150)
    plt.close(figure)
    output.chmod(0o600)

    closest = int(np.argmin(np.abs(signed_speed)))
    reverse_indices = np.flatnonzero(signed_speed < -0.02)
    return {
        "closest_zero_speed_mps": float(signed_speed[closest]),
        "closest_zero_time_s": float(time[closest]),
        "minimum_signed_speed_mps": float(signed_speed.min()),
        "maximum_signed_speed_mps": float(signed_speed.max()),
        "reverse_onset_s": float(time[reverse_indices[0]]) if len(reverse_indices) else float("nan"),
        "terminal_x_m": float(points[-1, 0]),
        "minimum_lateral_m": float(points[:, 1].min()),
        "maximum_lateral_m": float(points[:, 1].max()),
    }


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
    return f'''<section class="item" data-review-id="{review_id}"><h2>{review_id} <span class="scene-id">{item["scene_key"]}</span></h2>
<h3>1. 모델이 생성한 CoC</h3><p class="coc">{html.escape(item["coc"])}</p>
<div class="scope"><strong>이 항목에서 판단할 것:</strong> 위 CoC가 요구한 최초 행동 반응이 아래 <em>predicted trajectory</em>에 나타나는가?<br>
<strong>판단하지 않을 것:</strong> 장면 설명의 진실성, 교통법규 위반, 충돌 위험, YIELD 대상의 미래 해제 여부.</div>
<h3>2. 모델 입력 장면 — t0 직전 0.3초, 4개 카메라</h3>
<p class="caption">장면 문맥 보조 자료입니다. <strong>미래 영상이 아니므로</strong> 보행자·교차 차량이 이후 사라졌는지는 알 수 없습니다.</p>
<img class="scene" src="{item["scene"]}" alt="{review_id} 모델 입력 16프레임">
<h3>3. 모델이 예측한 6.4초 trajectory</h3>
<p class="caption">세 시간 그래프와 시간 색상을 넣은 평면도입니다. Signed speed의 음수와 붉은 영역은 후진을 뜻합니다.</p>
<img class="plot" src="{item["plot"]}" alt="{review_id} predicted trajectory와 speed plot">
<table class="metrics"><caption>그래프 판독 보조 수치</caption><tbody>
<tr><th>t0 history 속도</th><td>{item["ego_speed_at_t0_mps"]} m/s</td><th>0에 가장 가까운 signed 속도</th><td>{item["closest_zero_speed_mps"]} m/s @ {item["closest_zero_time_s"]} s</td></tr>
<tr><th>signed 속도 범위</th><td>{item["minimum_signed_speed_mps"]}–{item["maximum_signed_speed_mps"]} m/s</td><th>후진 시작</th><td>{item["reverse_onset_s"]}</td></tr>
<tr><th>6.4초 x 위치</th><td>{item["terminal_x_m"]} m</td><th>predicted 횡방향 범위</th><td>{item["minimum_lateral_m"]}–{item["maximum_lateral_m"]} m</td></tr>
</tbody></table>
<h3>4. 판정</h3>
<form><div class="grid">{"".join(fieldsets)}</div><fieldset class="notes"><legend>판정 근거</legend>
<textarea name="notes" maxlength="800" placeholder="response 시간, 최저 속도, 최대 횡이동, 또는 추가로 필요한 release 증거를 기록하십시오."></textarea>
</fieldset></form></section>'''


def build_page(reviewer: str, items: list[dict[str, str]]) -> str:
    sections = "\n".join(item_html(item) for item in items)
    fields_json = json.dumps(FIELDS, separators=(",", ":"))
    ids_json = json.dumps([item["review_id"] for item in items], separators=(",", ":"))
    return f'''<!doctype html><html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; img-src data:; style-src 'unsafe-inline'; script-src 'unsafe-inline'">
<title>Phase-aware CoC review {reviewer}</title><style>
:root{{--ink:#17202a;--muted:#66717d;--line:#d8dee6;--accent:#1d4ed8;--soft:#eef4ff;--ok:#166534;--bad:#9a3412}}*{{box-sizing:border-box}}
body{{margin:0;background:#f6f8fa;color:var(--ink);font-family:system-ui,-apple-system,"Noto Sans KR",sans-serif}}
header{{position:sticky;top:0;z-index:5;display:flex;gap:13px;align-items:center;padding:11px 18px;background:#fff;border-bottom:1px solid var(--line)}}
header h1{{font-size:18px;margin:0}}.grow{{flex:1}}button{{font:inherit;padding:9px 13px;border:0;border-radius:7px;background:var(--accent);color:#fff;cursor:pointer}}
main{{max-width:1450px;margin:16px auto;padding:0 18px 80px}}.instructions{{background:#fff;border:1px solid var(--line);border-radius:9px;padding:13px 16px;line-height:1.58}}
.warning{{color:var(--bad)}}.item{{background:#fff;border:1px solid var(--line);border-radius:10px;padding:18px;margin:18px 0}}.coc{{font-size:18px;line-height:1.6;padding:13px 15px;background:var(--soft);border-left:4px solid var(--accent)}}
.scene-id{{font-size:14px;color:var(--muted);font-weight:500;margin-left:8px}}h3{{margin:24px 0 8px}}.scope{{line-height:1.55;padding:12px 14px;background:#fff8e6;border:1px solid #f2d18a;border-radius:8px}}.caption{{color:var(--muted);margin:7px 0}}
.scene,.plot{{display:block;width:100%;height:auto;margin:12px 0 18px;border:1px solid var(--line)}}.metrics{{width:100%;border-collapse:collapse;margin:8px 0 18px}}.metrics caption{{text-align:left;font-weight:700;margin-bottom:6px}}.metrics th,.metrics td{{border:1px solid var(--line);padding:8px 10px;text-align:left}}.metrics th{{background:#f3f5f7}}
.grid{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px 18px}}fieldset{{min-width:0;border:1px solid var(--line);border-radius:8px;padding:10px 12px 12px}}legend{{font-weight:700;padding:0 5px}}.choices{{display:flex;gap:8px 13px;flex-wrap:wrap}}label{{white-space:normal}}
.notes{{margin-top:12px}}textarea{{width:100%;min-height:76px;resize:vertical;padding:9px;font:inherit;border:1px solid #aab4bf;border-radius:7px}}progress{{width:220px;height:14px}}#saved.ok{{color:var(--ok)}}#saved.bad{{color:var(--bad)}}.script-warning{{margin:12px 18px;padding:12px 14px;border:2px solid #dc2626;background:#fff1f2;color:#881337;font-weight:700}}
@media(max-width:850px){{.grid{{grid-template-columns:1fr}}header{{position:static;flex-wrap:wrap}}}}</style></head><body>
<header><h1>Phase-aware CoC 검토 · {reviewer}</h1><progress id="progress" max="30" value="0"></progress><span id="progressText">초기화 중</span><span id="saved">스크립트 확인 중</span><span class="grow"></span><button type="button" id="export">CSV 저장</button></header>
<noscript><div class="script-warning">이 미리보기는 JavaScript를 차단했습니다. CSV 저장을 사용하려면 HTML 파일을 Chrome 또는 Firefox에서 직접 여십시오.</div></noscript>
<main><div class="instructions"><strong>이 검토의 질문은 하나입니다:</strong> “CoC가 말한 행동 반응이 모델의 predicted trajectory에 실제로 표현되어 있는가?”<ul><li><strong>STOP</strong>: 속도가 horizon 안에서 거의 0이 되는가?</li><li><strong>DECELERATE</strong>: 초기에 의미 있는 감속이 한 번이라도 나타나는가? 이후 재가속만으로 모순이라 하지 않습니다.</li><li><strong>LEFT/RIGHT NUDGE</strong>: 해당 방향 횡이동이 나타나는가? 이후 복귀는 허용합니다.</li><li><strong>YIELD/KEEP_DISTANCE</strong>: 감속 반응은 볼 수 있지만, 대상의 미래 점유·해제·간격은 이 자료에 없으므로 전체 판정은 원칙적으로 <code>UNKNOWN</code>입니다.</li></ul>장면 이미지는 t0까지의 모델 입력이며 미래가 아닙니다. 물리 충돌 여부와 CoC 장면 설명의 진실성은 여기서 판정하지 않습니다. <span class="warning">종료 전 CSV를 저장하십시오.</span></div>{sections}</main>
<script>
const reviewer={json.dumps(reviewer)},fields={fields_json},reviewIds={ids_json},columns=["review_id",...Object.keys(fields),"notes"],storageKey=`alp-exp-005-phase-v1-${{reviewer}}`;let rows={{}};for(const id of reviewIds)rows[id]={{review_id:id}};
try{{const old=JSON.parse(localStorage.getItem(storageKey)||"{{}}");for(const id of reviewIds)Object.assign(rows[id],old[id]||{{}});}}catch(e){{}}
function complete(row){{return Object.keys(fields).every(k=>row[k]);}}function update(){{const done=reviewIds.filter(id=>complete(rows[id])).length;document.getElementById("progress").value=done;document.getElementById("progressText").textContent=`완료 ${{done}}/${{reviewIds.length}}`;}}
function save(){{for(const section of document.querySelectorAll(".item")){{const id=section.dataset.reviewId,fd=new FormData(section.querySelector("form")),row={{review_id:id}};for(const field of Object.keys(fields))row[field]=fd.get(field)||"";row.notes=fd.get("notes")||"";rows[id]=row;}}try{{localStorage.setItem(storageKey,JSON.stringify(rows));document.getElementById("saved").textContent="자동 저장됨";document.getElementById("saved").className="ok";}}catch(e){{document.getElementById("saved").textContent="자동 저장 불가";document.getElementById("saved").className="bad";}}update();}}
function restore(){{for(const section of document.querySelectorAll(".item")){{const row=rows[section.dataset.reviewId]||{{}};section.querySelectorAll("input[type=radio]").forEach(x=>x.checked=row[x.name]===x.value);section.querySelector("textarea").value=row.notes||"";}}update();}}
function cell(v){{const s=String(v??"");return /[",\\r\\n]/.test(s)?`"${{s.replace(/"/g,'""')}}"`:s;}}function exportCsv(){{save();const lines=[columns.join(",")];for(const id of reviewIds)lines.push(columns.map(c=>cell(rows[id][c]||"")).join(","));const blob=new Blob(["\ufeff"+lines.join("\\r\\n")+"\\r\\n"],{{type:"text/csv;charset=utf-8"}});const a=document.createElement("a");a.href=URL.createObjectURL(blob);a.download=`phase_aware_reviewer_${{reviewer}}.csv`;a.click();setTimeout(()=>URL.revokeObjectURL(a.href),1000);}}
document.addEventListener("change",save);document.addEventListener("input",save);document.getElementById("export").onclick=exportCsv;restore();document.getElementById("saved").textContent="준비됨";document.getElementById("saved").className="ok";
</script></body></html>'''


def main() -> int:
    analysis = json.loads(ANALYSIS.read_text(encoding="utf-8"))
    candidates = list(analysis["runs"])
    random.Random(RANDOMIZATION_SEED).shuffle(candidates)
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True, mode=0o700)
    OUTPUT_ROOT.chmod(0o700)
    plots = OUTPUT_ROOT / "plots"
    plots.mkdir(parents=True, exist_ok=True, mode=0o700)
    adjudication = OUTPUT_ROOT / "adjudication-only"
    adjudication.mkdir(parents=True, exist_ok=True, mode=0o700)

    # Do not expose source episode identifiers in the reviewer-facing HTML.
    # The opaque scene IDs only let reviewers notice that three stochastic runs
    # share the same visual input; source IDs remain in adjudication-only.
    source_to_blind_scene = {
        f"episode-{index:02d}": f"SCN-{index + 1:03d}" for index in range(10)
    }
    scene_assets = {
        source_to_blind_scene[source_episode]: encode(
            SCENE_ROOT / f"{source_episode}-model-input.jpg", "image/jpeg"
        )
        for source_episode in source_to_blind_scene
    }
    items = []
    mapping = []
    for index, row in enumerate(candidates, start=1):
        review_id = f"PAR-{index:03d}"
        run_root = BATCH_ROOT / row["episode"] / f"seed-{row['seed']}"
        plot_path = plots / f"{review_id}.png"
        trajectory_file = np.load(run_root / "predicted_trajectory.npz")
        trajectory = trajectory_file["pred_xyz"]
        rotation = trajectory_file["pred_rot"]
        temporal_summary = make_temporal_plot(trajectory, rotation, plot_path)
        items.append(
            {
                "review_id": review_id,
                "coc": (run_root / "generated_coc.txt").read_text(encoding="utf-8").strip(),
                "scene_key": source_to_blind_scene[row["episode"]],
                "scene": scene_assets[source_to_blind_scene[row["episode"]]],
                "plot": encode(plot_path, "image/png"),
                "ego_speed_at_t0_mps": f'{row["trajectory_summary"]["ego_speed_at_t0_mps"]:.3f}',
                **{
                    key: ("없음" if np.isnan(value) else f"{value:.3f}" + (" s" if key == "reverse_onset_s" else ""))
                    for key, value in temporal_summary.items()
                },
            }
        )
        mapping.append(
            {
                "review_id": review_id,
                "blind_scene_id": source_to_blind_scene[row["episode"]],
                "episode": row["episode"],
                "seed": row["seed"],
                "automatic_phase_aware_verdict": row["phase_aware_verdict"],
            }
        )

    for reviewer in ("A", "B"):
        output = OUTPUT_ROOT / f"PHASE_AWARE_REVIEW_{reviewer}.html"
        output.write_text(build_page(reviewer, items), encoding="utf-8")
        output.chmod(0o600)
        print(f"wrote {output.relative_to(ROOT)} ({output.stat().st_size:,} bytes)")
    mapping_path = adjudication / "blind-mapping.json"
    mapping_path.write_text(json.dumps(mapping, indent=2, sort_keys=True) + "\n")
    mapping_path.chmod(0o600)
    manifest = {
        "experiment_id": "ALP-EXP-005-PHASE-AWARE-REVIEW-V1",
        "review_item_count": len(items),
        "unique_scene_count": 10,
        "runs_per_scene": 3,
        "randomization_seed": RANDOMIZATION_SEED,
        "reviewers": ["A", "B"],
        "review_scope": "CoC action response and later-phase alignment; not physical safety",
        "blinded_fields": ["episode", "seed", "automatic_phase_aware_verdict"],
        "publication_control": "LICENSE_RESTRICTED_INTERNAL_RESULT",
    }
    manifest_path = OUTPUT_ROOT / "packet-manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    manifest_path.chmod(0o600)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
