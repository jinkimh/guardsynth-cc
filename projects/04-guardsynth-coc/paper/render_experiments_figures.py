"""Evidence-backed manuscript figures, owner guardsynth-coc; no training."""
from pathlib import Path
import csv
import hashlib
import json
import math
from statistics import mean, pstdev

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
from matplotlib.lines import Line2D

ROOT = next(p for p in Path(__file__).resolve().parents if (p / "PROJECT_REGISTRY.json").exists())
BASE = ROOT / "artifacts/projects/guardsynth-coc/public/paper1-method-preservation-001"
OUT = BASE / "experiments-section-2026-09-30-002"
assert not (OUT / "RESULT.json").exists(), "Completed runs are immutable"
FIG = OUT / "figures"
FIG.mkdir(parents=True, exist_ok=True)
SOURCES = {}


def read(path):
    SOURCES[str(path.relative_to(ROOT))] = hashlib.sha256(path.read_bytes()).hexdigest()
    return path.read_text()


def dump(name, value):
    (OUT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


rows = list(csv.DictReader(read(BASE / "temporal-experiment-closure-2026-09-29-001/all_primary_metrics.csv").splitlines()))
index = {(r["experiment"], r["split"], r["arm"], r["metric"]): r for r in rows}
SEEDS = (42, 17, 123)
ARMS = ("P0", "P1", "P2")
FIELDS = {"accuracy": "correct", "guard_violation_rate": "guard_violation",
          "hold_violation_rate": "hold_violation", "deadlock_rate": "deadlock",
          "goal_completion_rate": "goal_complete", "safe_goal_completion_rate": "safe_goal_complete",
          "coverage": "valid"}
predictions = {}
audited_rows = 0
for experiment, run in (("expansion", "temporal-expansion-learning-2026-09-29-001"),
                        ("cost", "temporal-cost-learning-2026-09-29-001")):
    groups = sorted({(r["split"], r["arm"]) for r in rows if r["experiment"] == experiment})
    for split, arm in groups:
        scores = {}
        for seed in SEEDS:
            path = BASE / run / f"{arm.lower()}-seed{seed}" / f"{split}.jsonl"
            records = [json.loads(s) for s in read(path).splitlines()]
            assert len(records) == 240, path
            predictions[experiment, split, arm, seed] = records
            pair_groups = {}
            for r in records:
                pair_groups.setdefault(r["scene_id"], []).append(r)
            assert len(pair_groups) == 120 and all(len(v) == 2 for v in pair_groups.values())
            scores[seed] = {metric: mean(float(r[field]) for r in records)
                            for metric, field in FIELDS.items()}
            scores[seed]["contract_swap_pair_accuracy"] = mean(
                float(all(r["correct"] for r in pair)) for pair in pair_groups.values())
            for metric, value in scores[seed].items():
                expected = float(index[experiment, split, arm, metric][f"seed{seed}"])
                assert math.isclose(value, expected, abs_tol=1e-12), (path, metric, value, expected)
            audited_rows += len(records)
        for metric in scores[SEEDS[0]]:
            expected = index[experiment, split, arm, metric]
            values = [scores[s][metric] for s in SEEDS]
            assert math.isclose(mean(values), float(expected["mean"]), abs_tol=1e-12)
            assert math.isclose(pstdev(values), float(expected["std_population"]), abs_tol=1e-12)

quality_path = ROOT / "artifacts/projects/guardsynth-coc/public/paper1-temporal-diversity-001/diversity-analysis-2026-09-29-001/RESULT.json"
quality = json.loads(read(quality_path))["D4"]
assert quality["candidate_count"] == 192
assert sum(x["detected"] for x in quality["by_type"].values()) == 144
assert quality["by_type"]["shared_source_error"]["misses"] == 24
assert quality["by_type"]["valid"]["false_rejections"] == 0
secondary = json.loads(read(BASE / "temporal-secondary-metrics-2026-09-29-001/RESULT.json"))
data = [json.loads(s) for s in read(BASE / "temporal-training-data-2026-09-29-001/test_paired.jsonl").splitlines()]
data_by_key = {(r["scene"]["scene_id"], r["contract_level"]): r for r in data}
by_arm = {a: {(r["scene_id"], r["contract_level"]): r
              for r in predictions["expansion", "test", a, 42]} for a in ARMS}
cases = []
for kind in ("improved", "residual_violation"):
    for key in sorted(by_arm["P0"]):
        p0, p1, p2 = [by_arm[a][key] for a in ARMS]
        qualifies = (p0["guard_violation"] and p1["correct"] and p2["correct"]
                     if kind == "improved" else p2["guard_violation"])
        if not qualifies:
            continue
        source = data_by_key[key]
        for a in ARMS:
            pred = by_arm[a][key]
            selected = next(c for c in source["scene"]["candidates"] if c["label"] == pred["prediction"])
            assert round(selected["entry_time"] * 1000) == pred["entry_ms"]
            assert pred["independent_target"] == source["reference_action"]
        cases.append({"kind": kind, "seed": 42, "record_id": source["id"],
                      "clear_ms": p2["clear_ms"], "duration_ms": source["required_clear_ms"],
                      "candidates": source["scene"]["candidates"], "reference_action": source["reference_action"],
                      "predictions": {a: by_arm[a][key] for a in ARMS}})
        break
assert len(cases) == 2
dump("selected_cases.json", {"selection": "Post-hoc; seed42 test sorted by scene_id and contract_level. First P0 violation with both P1/P2 correct; first P2 violation.",
                             "cases": cases})
dump("figure_data.json", {"metrics": rows, "selected_cases": cases,
                          "quality": quality, "secondary_test": secondary["results"]["test"]})

FONT = FontProperties(fname="/home/jinhyun/.local/share/fonts/NotoSansCJK-Regular.ttc")
plt.rcParams.update({"pdf.fonttype": 3, "ps.fonttype": 3, "font.size": 10,
                     "axes.spines.top": False, "axes.spines.right": False,
                     "axes.axisbelow": True})
COLORS = {"P0": "#64748B", "P1": "#C57927", "P2": "#167D8D"}


def metric(arm, split, name, experiment="expansion"):
    return index[experiment, split, arm, name]


def save(fig, name, lang):
    for ext in ("pdf", "png"):
        fig.savefig(FIG / f"{name}-{lang}.{ext}", dpi=170, bbox_inches="tight", pad_inches=.08)
    plt.close(fig)


for lang in ("ko", "en"):
    def tr(ko, en):
        return ko if lang == "ko" else en

    fig, axes = plt.subplots(1, 3, figsize=(8.5, 3.3))
    fig.subplots_adjust(left=.065, right=.985, top=.84, bottom=.24, wspace=.36)
    titles = [tr("정확도 ↑", "Accuracy ↑"), tr("제약 위반율 ↓", "Violation ↓"),
              tr("계약쌍 정확도 ↑", "Pair accuracy ↑")]
    for ax, name, title in zip(axes, ("accuracy", "guard_violation_rate", "contract_swap_pair_accuracy"), titles):
        for x, arm in enumerate(ARMS):
            r = metric(arm, "test", name)
            ax.errorbar(x, 100*float(r["mean"]), yerr=100*float(r["std_population"]),
                        fmt="D", ms=7, color=COLORS[arm], capsize=4, zorder=3)
            for dx, seed, marker in zip((-.17, 0, .17), SEEDS, ("o", "s", "^")):
                ax.scatter(x+dx, 100*float(r[f"seed{seed}"]), s=29, marker=marker,
                           facecolors="white", edgecolors=COLORS[arm], zorder=4)
        ax.set_xticks(range(3), ARMS)
        ax.set_xlim(-.45, 2.45)
        ax.set_ylim((-.7, 28) if name == "guard_violation_rate" else (-3, 105))
        ax.set_title(title, fontproperties=FONT, fontsize=11)
        ax.set_ylabel("%")
        ax.grid(axis="y", alpha=.2)
    handles = [Line2D([], [], marker=m, linestyle="", color="#334155", markerfacecolor="white",
                      label=f"seed {s}") for m,s in zip(("o","s","^"),SEEDS)]
    handles.append(Line2D([], [], marker="D", linestyle="-", color="#334155",
                          label=tr("평균 ± 표준편차", "Mean ± SD")))
    fig.legend(handles=handles, loc="lower center", ncol=4, prop=FONT, frameon=False)
    save(fig, "primary-metrics", lang)

    fig, axes = plt.subplots(1, 2, figsize=(8.5, 3.6))
    fig.subplots_adjust(left=.08, right=.98, top=.86, bottom=.26, wspace=.28)
    splits = ("test", "paraphrase", "unseen_duration")
    labels = [tr("기본 시험", "Main test"), tr("표현 변경", "Paraphrase"),
              tr("미학습 시간", "Unseen duration")]
    for ax, name, title in zip(axes, ("accuracy", "guard_violation_rate"), titles[:2]):
        for shift, arm in zip((-.07, 0, .07), ARMS):
            values = [100*float(metric(arm, s, name)["mean"]) for s in splits]
            errors = [100*float(metric(arm, s, name)["std_population"]) for s in splits]
            ax.errorbar([i+shift for i in range(3)], values, yerr=errors, fmt="o-",
                        color=COLORS[arm], capsize=3, ms=5, label=arm)
        ax.set_xticks(range(3), labels, fontproperties=FONT, fontsize=9)
        ax.set_ylabel("%")
        ax.set_ylim((-3.5, 28) if name == "guard_violation_rate" else (40, 104))
        ax.set_title(title, fontproperties=FONT, fontsize=11)
        ax.grid(axis="y", alpha=.2)
    fig.legend(*axes[0].get_legend_handles_labels(), loc="lower center", ncol=3, frameon=False)
    save(fig, "condition-shifts", lang)

    fig, axes = plt.subplots(2, 1, figsize=(8.5, 5.0))
    fig.subplots_adjust(left=.10, right=.84, top=.90, bottom=.11, hspace=.80)
    for ax, case, letter in zip(axes, cases, ("a", "b")):
        clear = case["clear_ms"]/1000
        edge = clear + case["duration_ms"]/1000
        ax.axvspan(clear-.25, edge, color="#F8E5E1")
        ax.axvspan(edge, edge+.4, color="#E3F2EA")
        ax.axvline(clear, ls=":", color="#64748B", lw=1)
        ax.axvline(edge, ls="--", color="#24754C", lw=1)
        for y, arm in zip((2,1,0), ARMS):
            pred = case["predictions"][arm]
            entry = pred["entry_ms"]/1000
            ax.plot(entry, y, marker="X" if pred["guard_violation"] else "o",
                    color=COLORS[arm], ms=8)
            ax.text(entry, y+.18, f'{pred["prediction"]} · {entry:.1f}s', fontsize=9,
                    ha="center", va="bottom")
            ax.text(edge+.45, y, tr("위반","Violation") if pred["guard_violation"] else tr("정답","Correct"),
                    fontproperties=FONT, fontsize=9, va="center", clip_on=False)
        ax.set(ylim=(-.45, 2.65), xlim=(clear-.25, edge+.4), yticks=(2,1,0), yticklabels=ARMS)
        # Selected times are annotated at each marker; keep close boundary ticks apart.
        ax.set_xticks((clear, clear+.5, edge))
        ax.set_xlabel(tr("진입 시각 (초)", "Entry time (s)"), fontproperties=FONT, fontsize=9)
        title = tr("개선 사례", "Improvement") if letter=="a" else tr("잔여 위반", "Residual violation")
        ax.set_title(f"({letter}) {title} · {case['record_id']} · "+tr("경계","boundary")+f" {edge:.1f}s",
                     fontproperties=FONT, fontsize=10, pad=12)
    save(fig, "action-cases", lang)

    fig, ax = plt.subplots(figsize=(7, 3.6))
    fig.subplots_adjust(left=.12, right=.97, top=.95, bottom=.24)
    for split, color, label in zip(("canonical","paraphrase","unseen_duration"),
                                  ("#167D8D","#C57927","#64748B"), labels):
        points=[]
        for arm, marker in (("CE_ONLY","o"),("CE_EBLC","D")):
            x=100*float(metric(arm,split,"guard_violation_rate","cost")["mean"])
            y=100*float(metric(arm,split,"accuracy","cost")["mean"])
            ax.scatter(x,y,color=color,marker=marker,s=65,zorder=3);points.append((x,y))
        ax.annotate("",xy=points[1],xytext=points[0],arrowprops={"arrowstyle":"->","color":color,"lw":1.4})
        ax.plot([],[],color=color,label=label)
    ax.set_xlabel(tr("제약 위반율 (%) ↓", "Violation rate (%) ↓"),fontproperties=FONT)
    ax.set_ylabel(tr("정확도 (%) ↑", "Accuracy (%) ↑"),fontproperties=FONT)
    ax.set(xlim=(-.15,2.05),ylim=(95.8,99.55))
    ax.grid(alpha=.2)
    ax.legend(prop=FONT,loc="lower right",frameon=False)
    fig.text(.5,.035,"○ CE_ONLY  →  ◆ CE_EBLC",ha="center",fontproperties=FONT,fontsize=10)
    save(fig,"cost-tradeoff",lang)

dump("evidence_manifest.json", {"project_id":"guardsynth-coc","sources_sha256":SOURCES})
dump("data_checks.json", {"predictions_reaggregated":audited_rows,
                          "csv_rows_checked":len(rows),"all_seed_mean_sd_values_match":True,
                          "pair_group_size":2,"quality_cases":192,"quality_detected_errors":144,
                          "quality_shared_errors_missed":24,"new_model_calls":0,
                          "selection_record_ids":[c["record_id"] for c in cases]})
print(json.dumps({"out":str(OUT),"predictions_checked":audited_rows,"cases":[c["record_id"] for c in cases]}))
