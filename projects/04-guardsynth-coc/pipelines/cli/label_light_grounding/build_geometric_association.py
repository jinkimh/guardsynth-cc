#!/usr/bin/env python3
"""Build source-linked multi-actor association evidence for one scene."""

from __future__ import annotations

import argparse
from datetime import date
import hashlib
import html
import json
from pathlib import Path
import sys
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from cli.project_paths import project_root


ROOT = project_root(__file__)
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from guard_synth.geometric_association import build_geometric_set_association


EXPERIMENT_ID = "GUARDSYNTH-GEOMETRIC-ASSOCIATION-001"
RESTRICTED_ROOT = ROOT / "artifacts/results/restricted"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _restricted(path: Path) -> Path:
    result = path.resolve()
    if not result.is_relative_to(ROOT.resolve()):
        raise ValueError("association inputs must remain inside the project")
    return result


def _write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    path.chmod(0o600)


def _polyline(samples: list[dict[str, Any]], color: str, label: str) -> str:
    def point(sample: dict[str, Any]) -> tuple[float, float]:
        x = 60.0 + float(sample["center_x_m"]) * 60.0
        y = 325.0 - float(sample["center_y_m"]) * 105.0
        return x, y

    points = [point(sample) for sample in samples]
    coords = " ".join(f"{x:.1f},{y:.1f}" for x, y in points)
    circles = "".join(
        f'<circle cx="{x:.1f}" cy="{y:.1f}" r="7" fill="{color}" />'
        for x, y in points
    )
    x, y = points[-1]
    return (
        f'<polyline points="{coords}" fill="none" stroke="{color}" '
        f'stroke-width="6" stroke-linecap="round" stroke-linejoin="round" />'
        f'{circles}<text x="{x + 12:.1f}" y="{y - 12:.1f}" fill="{color}" '
        f'font-size="24" font-weight="700">{html.escape(label)}</text>'
    )


def _review_html(evidence: dict[str, Any], candidates: list[dict[str, Any]]) -> str:
    colors = ("#ef4444", "#06b6d4", "#a855f7", "#f59e0b")
    labels = {
        candidate["track_id_sha256"]: f"Candidate {chr(65 + index)}"
        for index, candidate in enumerate(candidates)
    }
    tracks = "".join(
        _polyline(candidate["track_samples"], colors[index % len(colors)], f"Candidate {chr(65 + index)}")
        for index, candidate in enumerate(candidates)
        if candidate["track_id_sha256"] in evidence["associated_track_id_sha256"]
    )
    rows = "".join(
        "<tr>"
        f"<td>{labels[item['track_id_sha256']]}</td>"
        f"<td>{html.escape(str(item['label_class']))}</td>"
        f"<td>{item['overlap_sample_count']} / {item['track_sample_count']}</td>"
        f"<td>{item['first_overlap_timestamp_us']}</td>"
        f"<td>{item['last_overlap_timestamp_us']}</td>"
        "</tr>"
        for item in evidence["candidate_evaluations"]
    )
    zone = evidence["zone"]
    ego_front_px = 60.0 + float(evidence["vehicle_geometry"]["ego_front_extent_m"]) * 60.0
    return f"""<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>GuardSynth geometric association review</title>
<style>
body{{font-family:system-ui,sans-serif;margin:0;background:#f5f7fb;color:#18212f}}
main{{max-width:1500px;margin:auto;padding:24px}} section{{background:white;padding:24px;margin:18px 0;border-radius:14px}}
.plot{{width:100%;height:auto;border:1px solid #cbd5e1;background:#eef2f7}}
table{{border-collapse:collapse;width:100%}}th,td{{border:1px solid #cbd5e1;padding:10px;text-align:left}}
.boundary{{background:#fff7ed;border-left:6px solid #f97316}} code{{word-break:break-all}}
</style></head><body><main>
<h1>보행자–ego corridor association 근거</h1>
<section><h2>판정</h2>
<p><strong>{evidence['association_cardinality']}개 후보 모두</strong>가 관측 track window에서 ego corridor와 box overlap을 갖습니다.</p>
<p>target은 한 명이 아니라 <strong>SET({evidence['association_cardinality']})</strong>입니다. 최근접 후보 하나를 임의 선택하지 않았습니다.</p></section>
<section><h2>위에서 본 실제 track 수치</h2>
<svg class="plot" viewBox="0 0 1200 650" role="img" aria-label="ego corridor와 두 보행자 track의 평면도">
<rect x="60" y="213.2" width="1100" height="223.6" fill="#dbeafe" opacity="0.9" />
<line x1="60" y1="325" x2="1160" y2="325" stroke="#64748b" stroke-width="3" stroke-dasharray="12 10" />
<rect x="60" y="255" width="{ego_front_px - 60.0:.1f}" height="140" fill="#334155" rx="16" />
<text x="90" y="335" fill="white" font-size="28" font-weight="700">EGO</text>
<text x="500" y="195" fill="#1d4ed8" font-size="22">ego corridor y=[{zone['y_interval_m'][0]}, {zone['y_interval_m'][1]}] m</text>
<text x="900" y="610" fill="#334155" font-size="22">x forward →</text>
{tracks}
</svg>
<p>각 점은 공식 obstacle track의 시간 샘플입니다. 화면은 수치를 시각화한 것이며 카메라 의미 판독 결과가 아닙니다.</p></section>
<section><h2>후보별 계산</h2><table><thead><tr><th>후보</th><th>source label</th><th>overlap/전체 샘플</th><th>첫 overlap (µs)</th><th>마지막 overlap (µs)</th></tr></thead><tbody>{rows}</tbody></table></section>
<section><h2>판정 규칙</h2><p><code>{evidence['association_method']}</code></p>
<p>보행자 oriented 2-D bounding box의 횡방향 구간이 차량 폭으로 정의한 ego corridor와 겹치고, box가 ego 전방에 있는 샘플이 하나 이상이면 집합에 포함합니다.</p></section>
<section class="boundary"><h2>주장하지 않는 것</h2><p>이 결과는 CoC 문장의 지시 대상, 횡단보도/법적 zone, 보행 의도, 실제 충돌 확률, 차량 안전성을 입증하지 않습니다. 기하학적으로 관련된 track 집합만 고정합니다.</p></section>
</main></body></html>"""


def execute(
    *,
    obstacles_path: Path,
    adapter_path: Path,
    scene_ref: str,
    episode_index: int,
    event_index: int,
    adapter_candidate_index: int,
    output_dir: Path,
) -> tuple[Path, dict[str, Any]]:
    obstacles_path = _restricted(obstacles_path)
    adapter_path = _restricted(adapter_path)
    output_dir = _restricted(output_dir)
    if not obstacles_path.is_file() or not adapter_path.is_file():
        raise FileNotFoundError("association input is missing")
    if not output_dir.is_relative_to(RESTRICTED_ROOT.resolve()):
        raise ValueError("association result must remain under restricted results")
    if output_dir.exists():
        raise FileExistsError(f"refusing to overwrite existing output: {output_dir}")

    obstacles = json.loads(obstacles_path.read_text(encoding="utf-8"))
    adapter = json.loads(adapter_path.read_text(encoding="utf-8"))
    episode = obstacles["episodes"][episode_index]
    event = episode["events"][event_index]
    adapted = adapter["candidates"][adapter_candidate_index]
    expected_id = f"episode-{episode_index:02d}-event-{event_index:02d}"
    if adapted.get("candidate_id") != expected_id:
        raise ValueError("ADAPTER_CANDIDATE_EVENT_MISMATCH")
    source_hashes = sorted(
        hashlib.sha256(str(item["track_id"]).encode("utf-8")).hexdigest()
        for item in event["candidates"]
    )
    adapter_hashes = sorted(
        item["track_id_sha256"] for item in adapted["association_candidates"]
    )
    if source_hashes != adapter_hashes:
        raise ValueError("SOURCE_ADAPTER_TRACK_SET_MISMATCH")

    obstacle_sha = _sha256(obstacles_path)
    adapter_sha = _sha256(adapter_path)
    evidence = build_geometric_set_association(
        scene_ref=scene_ref,
        event_timestamp_us=int(event["timestamp_us"]),
        candidates=adapted["association_candidates"],
        ego_half_width_m=float(episode["vehicle_dimensions"]["width_m"]) / 2.0,
        ego_front_extent_m=float(
            episode["vehicle_dimensions"]["rear_axle_to_front_extent_m"]
        ),
        evidence_refs=[
            f"restricted-sha256:{obstacle_sha}#/episodes/{episode_index}/events/{event_index}",
            f"restricted-sha256:{adapter_sha}#/candidates/{adapter_candidate_index}/association_candidates",
        ],
    )
    if evidence["status"] != "AVAILABLE_SOURCE_LINKED":
        raise ValueError(evidence["reason_code"])

    output_dir.mkdir(parents=True)
    _write_json(output_dir / "ASSOCIATION_EVIDENCE.json", evidence)
    (output_dir / "ASSOCIATION_REVIEW.html").write_text(
        _review_html(evidence, adapted["association_candidates"]), encoding="utf-8"
    )
    result = {
        "experiment_id": EXPERIMENT_ID,
        "run_id": output_dir.name,
        "run_date": date.today().isoformat(),
        "status": "EXECUTED",
        "scene_ref": scene_ref,
        "association_status": evidence["status"],
        "association_cardinality": evidence["association_cardinality"],
        "target_kind": evidence["target_kind"],
        "raw_track_ids_included": False,
        "synthetic_value_fill_performed": False,
        "claim_scope": evidence["claim_scope"],
    }
    _write_json(output_dir / "RESULT.json", result)
    _write_json(output_dir / "RUN_MANIFEST.json", {
        **result,
        "input_class": "LICENSE_RESTRICTED",
        "input_hashes": {
            "obstacle_candidates": obstacle_sha,
            "adapter_result": adapter_sha,
        },
        "association_code_sha256": _sha256(ROOT / "projects/04-guardsynth-coc/src/guard_synth/geometric_association.py"),
        "cli_sha256": _sha256(Path(__file__).resolve()),
        "deterministic": True,
        "network_or_credential_use_performed": False,
    })
    (output_dir / "REPORT_KO.md").write_text(
        f"""# GuardSynth geometric association 결과

- 상태: **EXECUTED**
- 장면: `{scene_ref}`
- association: **SET({evidence['association_cardinality']})**
- 방법: `{evidence['association_method']}`
- 임의 최근접 단일 선택: **없음**
- 합성값 보충: **없음**

공식 obstacle track 전체 후보를 차량 폭으로 정의한 ego corridor와 비교했다. 이 장면의 두
보행자 후보 모두 관측 시간창에서 corridor와 oriented-box overlap을 가져 하나의 target 집합으로
연결됐다. `ASSOCIATION_REVIEW.html`은 동일 수치를 평면도로 표시한다.

이는 기하학적 track–corridor association이다. CoC 문장의 지시 대상, 횡단보도·법적 zone,
보행 의도, 충돌 확률 또는 차량 안전성을 검증한 결과가 아니다.
""",
        encoding="utf-8",
    )
    return output_dir, result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--obstacles", type=Path, required=True)
    parser.add_argument("--adapter-result", type=Path, required=True)
    parser.add_argument("--scene-ref", required=True)
    parser.add_argument("--episode-index", type=int, required=True)
    parser.add_argument("--event-index", type=int, required=True)
    parser.add_argument("--adapter-candidate-index", type=int, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    output, result = execute(
        obstacles_path=args.obstacles,
        adapter_path=args.adapter_result,
        scene_ref=args.scene_ref,
        episode_index=args.episode_index,
        event_index=args.event_index,
        adapter_candidate_index=args.adapter_candidate_index,
        output_dir=args.output_dir,
    )
    print(json.dumps({**result, "output": output.relative_to(ROOT).as_posix()}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
