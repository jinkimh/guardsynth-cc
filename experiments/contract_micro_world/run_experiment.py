from __future__ import annotations

import argparse
import csv
import json
import os
import platform
import sys
from collections import defaultdict
from dataclasses import asdict
from pathlib import Path

import numpy as np
import torch

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from experiments.contract_micro_world.micro_world import (  # noqa: E402
    KINDS,
    collect_expert_transitions,
    rollout_policy,
    sample_scenario,
)
from experiments.contract_micro_world.models import policy_callable, train_policy  # noqa: E402


MODEL_VARIANTS = ("A_STATE", "B_COC", "C_CONTRACT")
EVAL_VARIANTS = ("A_STATE", "B_COC", "C_CONTRACT", "D_CONTRACT_SHIELD")


def scenario_bank(per_kind: int, split: str, seed: int):
    rng = np.random.default_rng(seed)
    return [sample_scenario(kind, rng, split) for kind in KINDS for _ in range(per_kind)]


def aggregate(rows):
    groups = defaultdict(list)
    for row in rows:
        groups[(row["seed"], row["variant"], row["split"], row["kind"])].append(row)
    result = []
    for (seed, variant, split, kind), items in sorted(groups.items()):
        n = len(items)
        result.append(
            {
                "seed": seed,
                "variant": variant,
                "split": split,
                "kind": kind,
                "episodes": n,
                "unsafe_rate": sum(x["unsafe"] for x in items) / n,
                "forbidden_entry_rate": sum(x["forbidden_entry"] for x in items) / n,
                "collision_rate": sum(x["collision"] for x in items) / n,
                "safe_gap_violation_rate": sum(x["safe_gap_violation"] for x in items) / n,
                "completion_rate": sum(x["completed"] for x in items) / n,
                "mean_progress_m": sum(x["progress"] for x in items) / n,
                "mean_released_stop_s": sum(x["released_stop_steps"] for x in items) / n * 0.2,
                "mean_interventions": sum(x["interventions"] for x in items) / n,
                "mean_abs_jerk": sum(x["mean_abs_jerk"] for x in items) / n,
            }
        )
    return result


def across_seed_summary(aggregates):
    result = []
    for split in ("ID", "OOD"):
        for variant in EVAL_VARIANTS:
            for kind in (*KINDS, "ALL"):
                selected = [
                    r
                    for r in aggregates
                    if r["split"] == split and r["variant"] == variant and (kind == "ALL" or r["kind"] == kind)
                ]
                if kind == "ALL":
                    by_seed = []
                    for seed in sorted({r["seed"] for r in selected}):
                        seed_rows = [r for r in selected if r["seed"] == seed]
                        by_seed.append(
                            {
                                metric: float(np.mean([x[metric] for x in seed_rows]))
                                for metric in (
                                    "unsafe_rate",
                                    "forbidden_entry_rate",
                                    "collision_rate",
                                    "safe_gap_violation_rate",
                                    "completion_rate",
                                    "mean_progress_m",
                                    "mean_released_stop_s",
                                    "mean_interventions",
                                    "mean_abs_jerk",
                                )
                            }
                        )
                else:
                    by_seed = selected
                entry = {"variant": variant, "split": split, "kind": kind, "seeds": len(by_seed)}
                for metric in (
                    "unsafe_rate",
                    "forbidden_entry_rate",
                    "collision_rate",
                    "safe_gap_violation_rate",
                    "completion_rate",
                    "mean_progress_m",
                    "mean_released_stop_s",
                    "mean_interventions",
                    "mean_abs_jerk",
                ):
                    values = [float(x[metric]) for x in by_seed]
                    entry[f"{metric}_mean"] = float(np.mean(values))
                    entry[f"{metric}_std"] = float(np.std(values, ddof=1)) if len(values) > 1 else 0.0
                result.append(entry)
    return result


def write_csv(path: Path, rows):
    if not rows:
        return
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def write_report(path: Path, config, summaries, training):
    overall = {(r["split"], r["variant"]): r for r in summaries if r["kind"] == "ALL"}
    parameter_counts = [summary["parameters"] for summary in training.values()]
    lines = [
        "# Contract micro-world pilot result",
        "",
        "## Scope",
        "",
        "This is a controlled synthetic closed-loop feasibility test. It does not establish real-vehicle or Alpamayo safety.",
        "The only manipulated factor is whether the tiny policy receives action-oriented CoC features, compiled contract status, and a runtime contract shield.",
        "",
        "## Configuration",
        "",
        f"- train scenarios per kind: {config['train_per_kind']}",
        f"- OOD scenarios per kind: {config['test_per_kind']}",
        f"- model seeds: {', '.join(map(str, config['seeds']))}",
        f"- epochs: {config['epochs']}",
        f"- policy parameters: {min(parameter_counts):,}--{max(parameter_counts):,}",
        "",
        "## Closed-loop summary (mean across seeds)",
        "",
        "| Split | Variant | unsafe episode | forbidden entry | collision | completion | released-but-stopped (s) | interventions/episode |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for split in ("ID", "OOD"):
        for variant in EVAL_VARIANTS:
            row = overall[(split, variant)]
            lines.append(
                f"| {split} | {variant} | {row['unsafe_rate_mean']:.3f} | {row['forbidden_entry_rate_mean']:.3f} | "
                f"{row['collision_rate_mean']:.3f} | {row['completion_rate_mean']:.3f} | "
                f"{row['mean_released_stop_s_mean']:.3f} | {row['mean_interventions_mean']:.3f} |"
            )
    lines.extend(
        [
            "",
            "## Interpretation gate",
            "",
            "- The A/B baselines must first succeed on ID scenes; otherwise an OOD gap can be explained by failed imitation rather than missing constraints.",
            "- GO only if the compiled contract and/or shield reduces held-out unsafe outcomes consistently across seeds.",
            "- A shield-only gain supports runtime enforcement, not the claim that natural-language CoC itself teaches the constraint.",
            "- Any safety gain must be read together with completion, released-stop time, progress, and jerk to detect trivial always-stop behavior.",
            "- The next experiment should replace synthetic state with a public closed-loop benchmark only after this mechanism-level gate passes.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--train-per-kind", type=int, default=200)
    parser.add_argument("--test-per-kind", type=int, default=100)
    parser.add_argument("--epochs", type=int, default=35)
    parser.add_argument("--seeds", type=int, nargs="+", default=[42, 43, 44])
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)

    train_scenarios = scenario_bank(args.train_per_kind, "train", 20260804)
    evaluation_banks = {
        "ID": scenario_bank(args.test_per_kind, "train", 20260805),
        "OOD": scenario_bank(args.test_per_kind, "ood", 20260806),
    }
    transitions = collect_expert_transitions(train_scenarios)
    rows = []
    training = {}
    for seed in args.seeds:
        models = {}
        for variant in MODEL_VARIANTS:
            model, summary = train_policy(transitions, variant, seed, epochs=args.epochs)
            models[variant] = model
            training[f"{seed}:{variant}"] = asdict(summary)
            torch.save(model.state_dict(), args.output / f"model-{variant}-seed-{seed}.pt")

        for variant in EVAL_VARIANTS:
            model_variant = "C_CONTRACT" if variant == "D_CONTRACT_SHIELD" else variant
            policy = policy_callable(models[model_variant])
            use_shield = variant == "D_CONTRACT_SHIELD"
            for split, scenarios in evaluation_banks.items():
                for episode_index, scenario in enumerate(scenarios):
                    metrics = rollout_policy(scenario, policy, model_variant, shield=use_shield)
                    rows.append(
                        {
                            "seed": seed,
                            "variant": variant,
                            "split": split,
                            "episode": episode_index,
                            "kind": scenario.kind,
                            **asdict(metrics),
                            "unsafe": metrics.unsafe,
                        }
                    )

    aggregates = aggregate(rows)
    summaries = across_seed_summary(aggregates)
    config = {
        "train_per_kind": args.train_per_kind,
        "test_per_kind": args.test_per_kind,
        "epochs": args.epochs,
        "seeds": args.seeds,
        "train_transitions": len(transitions),
        "python": platform.python_version(),
        "torch": torch.__version__,
        "numpy": np.__version__,
        "cuda_available": torch.cuda.is_available(),
        "hostname": platform.node(),
        "command": " ".join(sys.argv),
        "pid": os.getpid(),
    }
    write_csv(args.output / "episode_metrics.csv", rows)
    write_csv(args.output / "aggregate_by_seed.csv", aggregates)
    write_csv(args.output / "summary_across_seeds.csv", summaries)
    payload = {"config": config, "training": training, "summary": summaries}
    (args.output / "result.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    write_report(args.output / "REPORT.md", config, summaries, training)
    print(json.dumps({"output": str(args.output), "train_transitions": len(transitions)}, indent=2))


if __name__ == "__main__":
    main()
