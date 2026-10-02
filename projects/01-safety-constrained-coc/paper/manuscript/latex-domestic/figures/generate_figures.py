#!/usr/bin/env python3
"""Generate reproducible paper figures and their CSV data sources."""

from __future__ import annotations

import csv
import json
import os
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/tmp/sccoc-matplotlib-cache")

import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Rectangle
import numpy as np


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
DATA = HERE / "data"
DATA.mkdir(parents=True, exist_ok=True)

TEMPORAL_JSON = ROOT / "artifacts/results/public/small-vlm-guard-v0/temporal-guard-multiseed-v0/summary.json"
MANEUVER_JSON = ROOT / "artifacts/results/public/small-vlm-guard-v0/maneuver-guard-multiseed-v0/summary.json"

BLUE = "#2878A0"
GREEN = "#28785A"
RED = "#A53737"
AMBER = "#B47823"
GRAY = "#777777"
LIGHT = "#EEF2F4"


def configure() -> None:
    candidates = [font.fname for font in font_manager.fontManager.ttflist if "NotoSansCJK" in font.fname]
    if candidates:
        font_manager.fontManager.addfont(candidates[0])
        family = font_manager.FontProperties(fname=candidates[0]).get_name()
        plt.rcParams["font.family"] = family
    plt.rcParams.update({
        "font.size": 8,
        "axes.titlesize": 9,
        "axes.labelsize": 8,
        "legend.fontsize": 7,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
        "axes.spines.top": False,
        "axes.spines.right": False,
    })


def write_csv(name: str, fieldnames: list[str], rows: list[dict[str, object]]) -> None:
    with (DATA / name).open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def save(fig: plt.Figure, stem: str) -> None:
    fig.savefig(HERE / f"{stem}.pdf", bbox_inches="tight")
    fig.savefig(HERE / f"{stem}.png", bbox_inches="tight", dpi=220)
    plt.close(fig)


def box(ax: plt.Axes, xy: tuple[float, float], width: float, height: float, text: str,
        face: str = LIGHT, edge: str = BLUE, size: float = 8) -> None:
    patch = FancyBboxPatch(xy, width, height, boxstyle="round,pad=0.02,rounding_size=0.03",
                           facecolor=face, edgecolor=edge, linewidth=1.2)
    ax.add_patch(patch)
    ax.text(xy[0] + width / 2, xy[1] + height / 2, text, ha="center", va="center", fontsize=size)


def arrow(ax: plt.Axes, start: tuple[float, float], end: tuple[float, float], color: str = GRAY) -> None:
    ax.add_patch(FancyArrowPatch(start, end, arrowstyle="-|>", mutation_scale=10,
                                 linewidth=1.1, color=color))


def figure_concept() -> None:
    fig, ax = plt.subplots(figsize=(7.1, 3.0))
    ax.set_xlim(0, 12); ax.set_ylim(0, 6); ax.axis("off")
    box(ax, (0.1, 3.8), 2.9, 1.25, "Requirement CoC\nYield, then proceed", "#E8F0F6", BLUE)
    box(ax, (0.1, 0.9), 2.9, 1.8, "Execution Guard\nstop offset ≤ 0\ndecel ≤ dmax\njerk ≤ jmax", "#EEF6EF", GREEN, 7.5)
    ax.add_patch(Rectangle((3.5, 0.55), 4.4, 4.9, facecolor="#F7F7F7", edgecolor="#AAAAAA"))
    ax.plot([5.7, 5.7], [0.7, 5.25], "--", color="#BBBBBB", lw=1)
    ax.plot([3.7, 7.7], [4.2, 4.2], color="#222222", lw=3)
    ax.text(3.7, 4.35, "stop line", fontsize=7)
    t = np.linspace(0, 1, 80)
    ax.plot(5.7 + 0.55*np.sin(np.pi*t), 0.8 + 4.15*t, color=RED, lw=2.5, label="late / violation")
    ax.plot(5.7 - 0.25*np.sin(np.pi*t), 0.8 + 3.25*t, color=GREEN, lw=2.5, label="smooth / admissible")
    ax.plot(5.7 - 0.65*np.sin(np.pi*t), 0.8 + 2.1*t, color=GRAY, lw=2.2, label="early / conservative")
    arrow(ax, (3.05, 4.4), (3.4, 4.4)); arrow(ax, (3.05, 1.8), (3.4, 2.2), GREEN)
    box(ax, (8.6, 3.6), 3.0, 1.35, "Requirement-only\n목표 충족 후보를 구별 못함", "#F6EEEE", RED)
    box(ax, (8.6, 1.15), 3.0, 1.45, "Safety-Constrained CoC\nGoal preserved\n+ Guard compliant", "#EEF6EF", GREEN)
    arrow(ax, (7.95, 4.25), (8.55, 4.25), RED); arrow(ax, (7.95, 2.0), (8.55, 2.0), GREEN)
    ax.legend(loc="lower center", ncol=3, frameon=False, bbox_to_anchor=(0.49, -0.02))
    save(fig, "fig01_concept")


def figure_pipeline() -> None:
    fig, ax = plt.subplots(figsize=(7.2, 2.55))
    ax.set_xlim(0, 14); ax.set_ylim(0.35, 5.35); ax.axis("off")
    box(ax, (0.2, 4.2), 2.1, 0.9, "Scene image", size=7.5)
    box(ax, (0.2, 2.7), 2.1, 0.9, "Requirement CoC", size=7.2)
    box(ax, (0.2, 1.2), 2.1, 0.9, "Execution Guard", "#EEF6EF", GREEN, 7.2)
    box(ax, (3.2, 2.1), 2.8, 1.7, "Qwen3-VL-2B\n+ LoRA", "#E8F0F6", BLUE, 9)
    for y in (4.65, 3.15, 1.65): arrow(ax, (2.35, y), (3.15, 2.95))
    box(ax, (6.9, 2.25), 2.2, 1.4, "Candidate\nA / B / C / D", "#FFF5E6", AMBER)
    arrow(ax, (6.05, 2.95), (6.85, 2.95))
    box(ax, (9.7, 2.0), 2.55, 1.9, "Independent verifier\nstop/gap/speed\ndecel/jerk/time", "#F0F0F0", GRAY, 7.2)
    arrow(ax, (9.15, 2.95), (9.65, 2.95))
    box(ax, (12.65, 3.65), 1.2, 1.0, "Violation", "#F6EEEE", RED, 7)
    box(ax, (12.65, 2.35), 1.2, 1.0, "Safe goal", "#EEF6EF", GREEN, 7)
    box(ax, (12.65, 1.05), 1.2, 1.0, "Pair acc.", "#E8F0F6", BLUE, 7)
    for y in (4.15, 2.85, 1.55): arrow(ax, (12.3, 2.95), (12.6, y))
    ax.text(4.6, 0.55, "Training control: correct contract-target pairing vs. shuffled pairing",
            ha="center", color=GRAY, fontsize=7.5)
    save(fig, "fig02_pipeline")


def figure_pair() -> None:
    current_gap_m = 7.2
    rows = [
        {
            "contract": "완화 계약",
            "min_gap_m": 5.5,
            "candidate_a_verdict": "허용",
            "selected_candidate": "후보 A",
            "reason": "현재 간격 7.2 m가 최소 간격 이상",
        },
        {
            "contract": "엄격 계약",
            "min_gap_m": 9.0,
            "candidate_a_verdict": "위반",
            "selected_candidate": "후보 B",
            "reason": "현재 간격 7.2 m가 최소 간격 미만",
        },
    ]
    write_csv(
        "paired_contract_example.csv",
        ["contract", "min_gap_m", "candidate_a_verdict", "selected_candidate", "reason"],
        rows,
    )

    fig, ax = plt.subplots(figsize=(8.2, 3.35), layout="constrained")
    ax.set_xlim(0, 15); ax.set_ylim(0, 6); ax.axis("off")
    ax.text(
        7.5,
        5.72,
        "고정 입력: 동일 장면 · 동일 CoC 목표 · 동일 궤적 후보",
        ha="center",
        va="center",
        weight="bold",
        fontsize=9,
    )

    # The scene is drawn once so the two contract rows cannot be mistaken for different scenes.
    ax.add_patch(Rectangle((0.2, 0.6), 4.15, 4.55, facecolor="#FAFAFA", edgecolor="#AAAAAA"))
    ax.text(2.28, 4.78, "두 계약에 공통으로 사용한\n차선 변경 장면", ha="center", va="center", weight="bold")
    ax.plot([0.65, 3.9], [1.55, 1.55], color="#555555", lw=5)
    ax.plot([0.65, 3.9], [3.65, 3.65], color="#555555", lw=5)
    ax.add_patch(Rectangle((0.95, 1.27), 0.72, 0.56, color=BLUE))
    ax.add_patch(Rectangle((2.95, 3.37), 0.72, 0.56, color=RED))
    ax.text(1.31, 1.02, "자차", ha="center", color=BLUE, weight="bold")
    ax.text(3.31, 4.08, "주변 차량", ha="center", color=RED, weight="bold")
    ax.add_patch(FancyArrowPatch((1.65, 1.68), (3.85, 3.35), arrowstyle="-|>", color=GREEN, lw=2.2))
    ax.annotate(
        f"현재 간격 {current_gap_m:.1f} m",
        xy=(2.7, 2.7),
        xytext=(0.75, 3.0),
        arrowprops={"arrowstyle": "-", "color": GRAY, "lw": 0.9},
        color=GRAY,
        fontsize=7.5,
    )

    ax.text(6.25, 4.78, "동일한 두 후보", ha="center", weight="bold")
    box(ax, (4.75, 3.1), 3.0, 1.05, "후보 A\n즉시 차선 변경", "#EEF6EF", GREEN, 8)
    box(ax, (4.75, 1.55), 3.0, 1.05, "후보 B\n중단 후 재시도", "#FFF5E6", AMBER, 8)

    ax.text(11.55, 4.78, "변경되는 최소 간격 계약과 판정", ha="center", weight="bold")
    for y, row, edge, face in zip((2.95, 0.75), rows, (GREEN, RED), ("#EEF6EF", "#F6EEEE")):
        ax.add_patch(FancyBboxPatch(
            (8.15, y), 6.55, 1.55,
            boxstyle="round,pad=0.04,rounding_size=0.05",
            facecolor=face, edgecolor=edge, linewidth=1.25,
        ))
        ax.text(8.45, y + 1.18, f"{row['contract']}: 최소 간격 ≥ {row['min_gap_m']:.1f} m", weight="bold")
        verdict_color = GREEN if row["candidate_a_verdict"] == "허용" else RED
        ax.text(
            8.45,
            y + 0.73,
            f"후보 A {row['candidate_a_verdict']}: {row['reason']}",
            color=verdict_color,
            fontsize=7.6,
        )
        ax.text(8.45, y + 0.28, f"최종 선택 → {row['selected_candidate']}", weight="bold", color=edge)

    arrow(ax, (7.8, 3.62), (8.1, 3.62), GREEN)
    arrow(ax, (7.8, 2.08), (8.1, 1.52), AMBER)
    save(fig, "fig03_paired_contract")


def extract_result_data() -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    temporal = json.loads(TEMPORAL_JSON.read_text(encoding="utf-8"))["aggregate"]
    temporal_names = [
        ("COC_ONLY", "Requirement"),
        ("INLINE_NL_CONSTRAINT", "Inline NL"),
        ("SEPARATE_NL_GUARD", "Separate NL"),
        ("SHUFFLED_GUARD", "Shuffled"),
        ("LOGIC_GUARD", "Logic"),
    ]
    temporal_rows: list[dict[str, object]] = []
    for key, label in temporal_names:
        split = temporal[key]["post_test"]
        temporal_rows.append({
            "condition": label,
            "guard_violation_mean": split["guard_violation_rate"]["mean"],
            "guard_violation_std": split["guard_violation_rate"]["pstdev"],
            "safe_goal_mean": split["safe_goal_completion_rate"]["mean"],
            "safe_goal_std": split["safe_goal_completion_rate"]["pstdev"],
            "pair_mean": split["contract_swap_pair_accuracy"]["mean"],
            "pair_std": split["contract_swap_pair_accuracy"]["pstdev"],
        })
    write_csv("temporal_multiseed.csv", list(temporal_rows[0]), temporal_rows)

    maneuver = json.loads(MANEUVER_JSON.read_text(encoding="utf-8"))["aggregate"]
    maneuver_rows: list[dict[str, object]] = []
    for condition in ("Requirement CoC", "Safety-Constrained CoC", "Shuffled constraint"):
        for split_name in ("test", "hard"):
            split = maneuver[condition][split_name]
            maneuver_rows.append({
                "condition": condition,
                "split": "Standard" if split_name == "test" else "Hard",
                "guard_violation_mean": split["guard_violation_rate"]["mean"],
                "guard_violation_std": split["guard_violation_rate"]["sample_std"],
                "safe_goal_mean": split["safe_goal_completion_rate"]["mean"],
                "safe_goal_std": split["safe_goal_completion_rate"]["sample_std"],
                "pair_mean": split["contract_swap_pair_accuracy"]["mean"],
                "pair_std": split["contract_swap_pair_accuracy"]["sample_std"],
            })
    write_csv("maneuver_multiseed.csv", list(maneuver_rows[0]), maneuver_rows)
    failure = json.loads(MANEUVER_JSON.read_text(encoding="utf-8"))["hard_failure_analysis"]["Safety-Constrained CoC"]
    failure_rows = [{"challenge": key, **value} for key, value in failure.items()]
    write_csv("hard_failure_by_challenge.csv", ["challenge", "examples", "wrong", "violations"], failure_rows)
    return temporal_rows, maneuver_rows


def figure_results() -> None:
    temporal, maneuver = extract_result_data()
    r1_rows = [
        {"contrast": "Sentence added vs. base CoC", "trajectory_change_m": 0.263,
         "source": "docs/reports/SAFETY_CONSTRAINED_COC_PROGRESS_REPORT_V01.md"},
        {"contrast": "Hold vs. opposite guard", "trajectory_change_m": 0.008,
         "source": "docs/reports/SAFETY_CONSTRAINED_COC_PROGRESS_REPORT_V01.md"},
    ]
    write_csv("r1_diagnostic.csv", ["contrast", "trajectory_change_m", "source"], r1_rows)

    fig, ax = plt.subplots(figsize=(4.8, 3.0), layout="constrained")
    vals = [row["trajectory_change_m"] for row in r1_rows]
    ax.bar([0, 1], vals, color=[BLUE, AMBER], width=0.65)
    ax.set_xticks([0, 1], ["문장 추가와\n기본 CoC 차이", "대기 가드와\n반대 가드 차이"])
    ax.set_ylabel("2초 후 궤적 변화량 (m)")
    ax.set_ylim(0, 0.31)
    for i, value in enumerate(vals):
        ax.text(i, value + 0.009, f"{value:.3f}", ha="center", fontsize=8)
    save(fig, "fig04_r1_diagnostic")

    fig, axes = plt.subplots(
        1,
        2,
        figsize=(8.0, 3.7),
        layout="constrained",
        gridspec_kw={"width_ratios": [1.12, 1]},
    )
    ax = axes[0]
    y = np.arange(len(temporal))
    height = 0.34
    gv = np.array([float(row["guard_violation_mean"]) for row in temporal])
    gs = np.array([float(row["guard_violation_std"]) for row in temporal])
    sg = np.array([float(row["safe_goal_mean"]) for row in temporal])
    ss = np.array([float(row["safe_goal_std"]) for row in temporal])
    ax.barh(y - height / 2, gv, height, xerr=gs, color=RED, label="가드 위반", capsize=2)
    ax.barh(y + height / 2, sg, height, xerr=ss, color=GREEN, label="가드 준수 목표 완료", capsize=2)
    ax.set_yticks(y, ["요구사항 전용형", "CoC 통합형", "가드 분리형", "대응을 섞은 가드", "논리식 가드"])
    ax.invert_yaxis()
    ax.set_xlim(0, 1.13)
    ax.set_xlabel("비율")
    ax.set_title("(a) 시간 조건 준수 (3회 반복)")
    ax.legend(frameon=False, loc="upper right")

    ax = axes[1]
    conditions = ["Requirement CoC", "Safety-Constrained CoC", "Shuffled constraint"]
    labels = ["요구사항 전용형", "Safety-Constrained CoC", "대응을 섞은 가드"]
    y = np.arange(3)
    height = 0.34
    standard = [next(float(r["pair_mean"]) for r in maneuver if r["condition"] == c and r["split"] == "Standard") for c in conditions]
    hard = [next(float(r["pair_mean"]) for r in maneuver if r["condition"] == c and r["split"] == "Hard") for c in conditions]
    ax.barh(y - height / 2, standard, height, color=BLUE, label="일반 평가")
    ax.barh(y + height / 2, hard, height, color=AMBER, label="어려운 표현 평가")
    ax.set_yticks(y, labels)
    ax.invert_yaxis()
    ax.set_xlim(0, 1.13)
    ax.set_xlabel("비율")
    ax.set_title("(b) 계약 전환 쌍 정확도")
    ax.legend(frameon=False, loc="lower right")
    save(fig, "fig05_temporal_pair")


def figure_typed_contract() -> None:
    stages = [
        {"stage": 1, "description": "자연어 Safety-Constrained CoC"},
        {"stage": 2, "description": "실행 가드 변환: 조건 종류, 비교 방향, 값, 단위, 대체 행동"},
        {"stage": 3, "description": "단위 통일: 600 cm → 6.0 m"},
        {"stage": 4, "description": "독립 검증기 또는 차단장치: 거리, 속도, 시간 조건 확인"},
    ]
    write_csv("typed_contract_stages.csv", ["stage", "description"], stages)

    fig, ax = plt.subplots(figsize=(3.65, 4.45))
    ax.set_xlim(0, 6); ax.set_ylim(0, 10); ax.axis("off")
    box(ax, (0.55, 8.25), 4.9, 1.0, "자연어 Safety-Constrained CoC", "#E8F0F6", BLUE, 7.5)
    arrow(ax, (3, 8.2), (3, 7.5))
    box(
        ax,
        (0.55, 6.05),
        4.9,
        1.35,
        "실행 가드 변환\n조건 종류 | 비교 방향 | 값 | 단위\n대체 행동",
        "#FFF5E6",
        AMBER,
        7.1,
    )
    arrow(ax, (3, 6.0), (3, 5.3))
    box(ax, (0.55, 4.0), 4.9, 1.2, "단위 통일\n600 cm → 6.0 m", "#EEF6EF", GREEN, 7.5)
    arrow(ax, (3, 3.95), (3, 3.25))
    box(
        ax,
        (0.55, 1.55),
        4.9,
        1.6,
        "독립 검증기 또는 차단장치\n거리 | 속도 | 시간 조건 확인",
        "#F0F0F0",
        GRAY,
        7.3,
    )
    ax.text(
        3,
        0.72,
        "모델: 행동 목표와 가드 해석\n검증기: 수치 경계 확인",
        ha="center",
        color=GRAY,
        fontsize=7.4,
    )
    save(fig, "fig05_typed_contract")


def figure_release_reversal() -> None:
    rows = [
        {"condition": "상태 전용", "unsafe": 0.466, "collision": 0.266},
        {"condition": "상태+CoC", "unsafe": 0.486, "collision": 0.273},
        {"condition": "동적 계약", "unsafe": 0.214, "collision": 0.143},
        {"condition": "단조 단계 계약", "unsafe": 0.379, "collision": 0.259},
        {"condition": "계약+차단장치", "unsafe": 0.048, "collision": 0.018},
        {"condition": "미래정보 상한", "unsafe": 0.000, "collision": 0.000},
        {"condition": "지연된 동적 계약", "unsafe": 0.481, "collision": 0.248},
        {"condition": "지연된 차단장치", "unsafe": 0.348, "collision": 0.163},
    ]
    source = "artifacts/results/public/contract-microworld-v2/pilot-release-reversal-2026-08-04-v1/DEEP_STRESS_ASSESSMENT_KO.md"
    for row in rows: row["source"] = source
    write_csv("release_reversal.csv", ["condition", "unsafe", "collision", "source"], rows)
    fig, axes = plt.subplots(
        1,
        2,
        figsize=(9.4, 3.8),
        layout="constrained",
        gridspec_kw={"width_ratios": [1.42, 1]},
    )
    ax = axes[0]
    y = np.arange(len(rows))
    height = 0.34
    ax.barh(y - height / 2, [float(r["unsafe"]) for r in rows], height, color=RED, label="가드 위반")
    ax.barh(y + height / 2, [float(r["collision"]) for r in rows], height, color=AMBER, label="충돌")
    ax.set_yticks(y, [str(r["condition"]) for r in rows])
    ax.invert_yaxis()
    ax.set_xlim(0, 0.56)
    ax.set_xlabel("비율")
    ax.legend(frameon=False, loc="upper right")
    ax.set_title("(a) 해제 후 재위험 상황")

    ax = axes[1]
    ax.set_xlim(0, 1.16)
    ax.set_ylim(0, 2.8)
    ax.axis("off")
    ax.plot([0.05, 1.02], [1.35, 1.35], color="#555555", lw=1.4)
    events = [
        (0.16, "t=0\n구역 비움·해제", BLUE, 1.82),
        (0.56, "t=0.6초\nego 진입", AMBER, 0.72),
        (0.88, "t=0.8초\n위험 재등장", RED, 1.82),
    ]
    for t, label, color, text_y in events:
        ax.plot([t, t], [1.08, 1.62], color=color, lw=2)
        ax.text(t, text_y, label, ha="center", va="center", color=color, fontsize=7, clip_on=True)
    ax.add_patch(FancyArrowPatch((0.88, 2.48), (0.88, 2.08), arrowstyle="-|>", color=RED))
    ax.text(0.88, 2.57, "해제 상태를 다시\n대기 상태로 바꿔야 함", ha="center", color=RED, fontsize=7.5, clip_on=True)
    ax.set_title("(b) 학습하지 않은 상태 전환")
    save(fig, "fig06_release_reversal")


def main() -> int:
    configure()
    figure_concept()
    figure_pipeline()
    figure_pair()
    figure_results()
    figure_typed_contract()
    figure_release_reversal()
    print(f"Generated figures and data under {HERE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
