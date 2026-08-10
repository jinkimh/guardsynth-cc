from __future__ import annotations

import argparse
import csv
import json
import platform
import sys
from collections import defaultdict
from dataclasses import asdict
from pathlib import Path

import numpy as np
import torch
from torch import nn

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from experiments.contract_micro_world.micro_world import (  # noqa: E402
    COC_DIM,
    CONTRACT_DIM,
    DT,
    KINDS,
    STATE_DIM,
    EpisodeMetrics,
    Scenario,
    apply_contract_shield,
    base_observation,
    clip_action,
    coc_features,
    collect_expert_transitions,
    contract_features,
    contract_status,
    distance_measure,
    evaluate_transition,
    expert_action,
    hazard_active,
    initial_state,
    is_visible,
    lead_safe_gap,
    sample_scenario,
    step,
)
from experiments.contract_micro_world.models import TinyPolicy  # noqa: E402
from experiments.contract_micro_world.run_experiment import scenario_bank as v1_scenario_bank  # noqa: E402


PHASES = ("APPROACH", "STOP_DWELL", "HOLD", "RELEASED")
PHASE_DIM = len(PHASES) + 1  # one-hot plus stop-dwell progress
MODEL_VARIANTS = ("A_STATE", "B_COC", "C_LEGACY_CONTRACT", "C2_PHASE_CONTRACT")
EVAL_VARIANTS = (*MODEL_VARIANTS, "D_PHASE_SHIELD")


def stop_phase(state) -> str | None:
    if state.scenario.kind != "stop_intersection":
        return None
    if state.has_stopped:
        if hazard_active(state) or not is_visible(state):
            return "HOLD"
        return "RELEASED"
    if state.stopped_steps > 0:
        return "STOP_DWELL"
    return "APPROACH"


def phase_features(state) -> np.ndarray:
    result = np.zeros(PHASE_DIM, dtype=np.float32)
    phase = stop_phase(state)
    if phase is not None:
        result[PHASES.index(phase)] = 1.0
        result[-1] = min(1.0, state.stopped_steps / 2.0)
    return result


def featurize_phase(state, variant: str) -> np.ndarray:
    base = base_observation(state)
    if variant == "A_STATE":
        return base
    with_coc = np.concatenate([base, coc_features(state)])
    if variant == "B_COC":
        return with_coc
    with_contract = np.concatenate([with_coc, contract_features(state)])
    if variant == "C_LEGACY_CONTRACT":
        return with_contract
    if variant == "C2_PHASE_CONTRACT":
        return np.concatenate([with_contract, phase_features(state)])
    raise ValueError(variant)


def sample_phase_complete_stop(rng: np.random.Generator) -> Scenario:
    # These are successful demonstrations with a real post-stop HOLD phase.
    return Scenario(
        kind="stop_intersection",
        initial_distance=float(rng.uniform(12.0, 20.0)),
        ego_speed=float(rng.uniform(5.0, 7.0)),
        hazard_clear_time=float(rng.uniform(5.2, 7.0)),
    )


def scenario_bank(per_kind: int, split: str, seed: int):
    if split == "ood":
        return v1_scenario_bank(per_kind, "ood", seed)
    base = v1_scenario_bank(per_kind, "train", seed)
    if split == "id":
        return base
    if split != "train":
        raise ValueError(split)
    # Preserve every v1 scene except the second half of STOP. This isolates the
    # phase-coverage intervention from non-STOP sampling changes.
    rng = np.random.default_rng(20260807)
    stop_start = per_kind
    for offset in range(per_kind // 2, per_kind):
        base[stop_start + offset] = sample_phase_complete_stop(rng)
    return base


def phase_coverage(transitions) -> dict[str, int]:
    counts = {phase: 0 for phase in PHASES}
    for state, _ in transitions:
        phase = stop_phase(state)
        if phase is not None:
            counts[phase] += 1
    return counts


def independent_evaluate_transition(before, after, metrics: EpisodeMetrics) -> None:
    """Evaluation oracle that does not call contract_status or the shield.

    The oracle uses direct scene truth and crossing geometry. Unknown visibility is
    a rule violation when crossing, but not itself a physical collision. Unlike
    v1, positions before x=0 are never called a conflict-zone collision.
    """
    kind = before.scenario.kind
    if kind != "lead_brake":
        crossed_entry = before.ego_x < 0.0 <= after.ego_x
        active_before = before.t < before.scenario.hazard_clear_time
        visible_before = not (
            before.scenario.occlusion_start <= before.t < before.scenario.occlusion_end
        )
        if crossed_entry:
            if kind == "crosswalk" and (active_before or not visible_before):
                metrics.forbidden_entry = True
            if kind == "stop_intersection" and (
                not before.has_stopped or active_before or not visible_before
            ):
                metrics.forbidden_entry = True
        active_after = after.t < after.scenario.hazard_clear_time
        if 0.0 <= after.ego_x <= 4.0 and active_after:
            metrics.collision = True
        released = not active_before and visible_before
        if kind == "stop_intersection":
            released = released and before.has_stopped
        if released and after.ego_v < 0.5:
            metrics.released_stop_steps += 1
        return

    gap = after.lead_x - after.ego_x
    if gap <= 0.0:
        metrics.collision = True
    # Independent service-distance metric expressed directly from state.
    closing = max(0.0, after.ego_v - after.lead_v)
    required_gap = 2.0 + 1.25 * after.ego_v + closing * closing / (2.0 * 2.5)
    if gap < required_gap:
        metrics.safe_gap_violation = True


def rollout(scenario, policy, model_variant: str, shield: bool):
    state = initial_state(scenario)
    initial_x = state.ego_x
    actions = []
    metrics = EpisodeMetrics()
    while not state.done:
        proposed = float(policy(featurize_phase(state, model_variant)))
        action, intervened = apply_contract_shield(state, proposed) if shield else (clip_action(proposed), False)
        metrics.interventions += int(intervened)
        new_state = step(state, action)
        independent_evaluate_transition(state, new_state, metrics)
        actions.append(action)
        state = new_state
    metrics.progress = state.ego_x - initial_x
    metrics.completed = (scenario.kind == "lead_brake" and not metrics.collision) or state.ego_x >= 8.0
    if len(actions) > 1:
        metrics.mean_abs_jerk = float(np.mean(np.abs(np.diff(actions))) / DT)
    return metrics


def train_policy(transitions, variant: str, seed: int, epochs: int, batch_size: int = 512):
    torch.manual_seed(seed)
    np.random.seed(seed)
    x_np = np.stack([featurize_phase(state, variant) for state, _ in transitions]).astype(np.float32)
    y_np = np.asarray([action for _, action in transitions], dtype=np.float32)
    x, y = torch.from_numpy(x_np), torch.from_numpy(y_np)
    model = TinyPolicy(x.shape[1])
    optimizer = torch.optim.AdamW(model.parameters(), lr=2e-3, weight_decay=1e-5)
    generator = torch.Generator().manual_seed(seed + 1000)
    final_loss = float("nan")
    model.train()
    for _ in range(epochs):
        permutation = torch.randperm(len(x), generator=generator)
        total = 0.0
        for start in range(0, len(x), batch_size):
            index = permutation[start : start + batch_size]
            loss = nn.functional.smooth_l1_loss(model(x[index]), y[index])
            optimizer.zero_grad(set_to_none=True)
            loss.backward()
            optimizer.step()
            total += float(loss.detach()) * len(index)
        final_loss = total / len(x)
    model.eval()
    return model, {
        "final_loss": final_loss,
        "epochs": epochs,
        "examples": len(x),
        "parameters": sum(p.numel() for p in model.parameters()),
        "input_dim": x.shape[1],
    }


def policy_callable(model):
    def predict(features):
        with torch.no_grad():
            return float(model(torch.from_numpy(features.astype(np.float32)).unsqueeze(0)).item())

    return predict


def aggregate(rows):
    groups = defaultdict(list)
    for row in rows:
        groups[(row["seed"], row["variant"], row["split"], row["kind"])].append(row)
    output = []
    for (seed, variant, split, kind), items in sorted(groups.items()):
        n = len(items)
        output.append(
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
                "mean_released_stop_s": sum(x["released_stop_steps"] for x in items) / n * DT,
                "mean_interventions": sum(x["interventions"] for x in items) / n,
                "mean_abs_jerk": sum(x["mean_abs_jerk"] for x in items) / n,
            }
        )
    return output


def summarize(aggregates):
    metrics = (
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
    output = []
    for split in ("ID", "OOD"):
        for variant in EVAL_VARIANTS:
            for kind in (*KINDS, "ALL"):
                selected = [r for r in aggregates if r["split"] == split and r["variant"] == variant]
                if kind != "ALL":
                    selected = [r for r in selected if r["kind"] == kind]
                else:
                    selected = [
                        {metric: float(np.mean([r[metric] for r in selected if r["seed"] == seed])) for metric in metrics}
                        for seed in sorted({r["seed"] for r in selected})
                    ]
                row = {"variant": variant, "split": split, "kind": kind, "seeds": len(selected)}
                for metric in metrics:
                    values = [float(r[metric]) for r in selected]
                    row[f"{metric}_mean"] = float(np.mean(values))
                    row[f"{metric}_std"] = float(np.std(values, ddof=1)) if len(values) > 1 else 0.0
                output.append(row)
    return output


def write_csv(path, rows):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def write_report(path, config, summary):
    overall = {(r["split"], r["variant"]): r for r in summary if r["kind"] == "ALL"}
    stop = {(r["split"], r["variant"]): r for r in summary if r["kind"] == "stop_intersection"}
    lines = [
        "# Phase-complete STOP contract experiment",
        "",
        "## Change from v1",
        "",
        "- Added successful post-stop HOLD demonstrations to every training condition.",
        "- Added C2 with explicit APPROACH/STOP_DWELL/HOLD/RELEASED phase features.",
        "- Removed the v1 pre-line collision proxy and used a direct crossing oracle that does not call contract_status.",
        "- D reuses C2 and adds the deterministic runtime shield.",
        "",
        "## Training phase coverage",
        "",
        *[f"- {phase}: {count}" for phase, count in config["phase_coverage"].items()],
        "",
        "## Mean across three seeds",
        "",
        "| Split | Variant | all unsafe | STOP unsafe | completion | progress (m) | jerk | interventions |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for split in ("ID", "OOD"):
        for variant in EVAL_VARIANTS:
            a, s = overall[(split, variant)], stop[(split, variant)]
            lines.append(
                f"| {split} | {variant} | {a['unsafe_rate_mean']:.3f} | {s['unsafe_rate_mean']:.3f} | "
                f"{a['completion_rate_mean']:.3f} | {a['mean_progress_m_mean']:.3f} | "
                f"{a['mean_abs_jerk_mean']:.3f} | {a['mean_interventions_mean']:.3f} |"
            )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "If A/B improve after phase-complete demonstrations, ordinary imitation data can correct the missing phase in this bank.",
            "A C2-versus-C difference would support explicit phase features; no difference means the added phase input was not necessary here.",
            "A D-versus-C2 difference would support runtime enforcement; interventions without fewer violations indicate conservatism instead.",
            "This remains a synthetic mechanism test and does not establish real-road or Alpamayo safety.",
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

    training_scenarios = scenario_bank(args.train_per_kind, "train", 20260804)
    transitions = collect_expert_transitions(training_scenarios)
    coverage = phase_coverage(transitions)
    if coverage["HOLD"] == 0:
        raise RuntimeError("phase-complete training bank has no post-stop HOLD states")
    evaluation = {
        "ID": scenario_bank(args.test_per_kind, "id", 20260805),
        # Keep the original v1 OOD bank for direct comparability.
        "OOD": scenario_bank(args.test_per_kind, "ood", 20260806),
    }
    rows, training = [], {}
    for seed in args.seeds:
        models = {}
        for variant in MODEL_VARIANTS:
            model, details = train_policy(transitions, variant, seed, args.epochs)
            models[variant] = model
            training[f"{seed}:{variant}"] = details
            torch.save(model.state_dict(), args.output / f"model-{variant}-seed-{seed}.pt")
        for variant in EVAL_VARIANTS:
            model_variant = "C2_PHASE_CONTRACT" if variant == "D_PHASE_SHIELD" else variant
            policy = policy_callable(models[model_variant])
            for split, scenarios in evaluation.items():
                for episode, scenario in enumerate(scenarios):
                    metrics = rollout(scenario, policy, model_variant, variant == "D_PHASE_SHIELD")
                    rows.append(
                        {
                            "seed": seed,
                            "variant": variant,
                            "split": split,
                            "episode": episode,
                            "kind": scenario.kind,
                            **asdict(metrics),
                            "unsafe": metrics.unsafe,
                        }
                    )
    aggregates = aggregate(rows)
    summary = summarize(aggregates)
    config = {
        "train_per_kind": args.train_per_kind,
        "test_per_kind": args.test_per_kind,
        "epochs": args.epochs,
        "seeds": args.seeds,
        "train_transitions": len(transitions),
        "phase_coverage": coverage,
        "python": platform.python_version(),
        "torch": torch.__version__,
        "numpy": np.__version__,
        "cuda_available": torch.cuda.is_available(),
        "command": " ".join(sys.argv),
    }
    write_csv(args.output / "episode_metrics.csv", rows)
    write_csv(args.output / "aggregate_by_seed.csv", aggregates)
    write_csv(args.output / "summary_across_seeds.csv", summary)
    (args.output / "result.json").write_text(
        json.dumps({"config": config, "training": training, "summary": summary}, indent=2), encoding="utf-8"
    )
    write_report(args.output / "REPORT.md", config, summary)
    print(json.dumps({"output": str(args.output), "config": config}, indent=2))


if __name__ == "__main__":
    main()
