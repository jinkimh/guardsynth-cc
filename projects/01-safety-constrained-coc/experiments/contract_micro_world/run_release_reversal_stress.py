from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import defaultdict
from dataclasses import asdict, dataclass, replace
from pathlib import Path

import numpy as np
import torch

if __package__ in {None, ""}:
    sys.path.insert(0, str(next(parent for parent in Path(__file__).resolve().parents if (parent / "PROJECT_REGISTRY.json").is_file())))

from experiments.contract_micro_world.micro_world import (  # noqa: E402
    COC_DIM,
    CONTRACT_DIM,
    DT,
    HORIZON_STEPS,
    STATE_DIM,
    EpisodeMetrics,
    Scenario,
    apply_contract_shield,
    base_observation,
    clip_action,
    coc_features,
    contract_features,
    expert_action,
    hazard_active,
    initial_state,
    is_visible,
    step,
)
from experiments.contract_micro_world.models import TinyPolicy  # noqa: E402
from experiments.contract_micro_world.run_phase_complete_experiment import (  # noqa: E402
    PHASE_DIM,
    phase_features,
)


STRESS_TYPES = (
    "crosswalk_reentry",
    "stop_cross_traffic_reappearance",
    "crosswalk_reocclusion",
    "stop_reocclusion",
)
EVAL_VARIANTS = (
    "A_STATE",
    "B_COC",
    "C_CONTRACT",
    "C2_PHASE_CONTRACT",
    "D_CORRECT_CONTRACT",
    "D_ORACLE_LOOKAHEAD_0P8",
    "D_ORACLE_LOOKAHEAD_1P2",
    "C_STALE_CONTRACT_0P4",
    "D_STALE_CONTRACT_0P4",
    "D_SHARED_SENSOR_LAG_0P4",
)


@dataclass(frozen=True)
class StressCase:
    case_id: int
    stress_type: str
    scenario: Scenario
    reversal_time: float
    reversal_end: float
    reference_x_at_reversal: float


def _observed_state(state, lag: float):
    return replace(state, t=max(0.0, state.t - lag))


def _future_risk_state(state, lookahead: float):
    """Perfect-schedule upper bound, not a deployable predictor."""
    steps = int(round(lookahead / DT))
    for offset in range(steps + 1):
        candidate = replace(state, t=state.t + offset * DT)
        if hazard_active(candidate) or not is_visible(candidate):
            return candidate
    return state


def stress_features(state, model_variant: str, contract_lag: float = 0.0, sensor_lag: float = 0.0):
    sensor_state = _observed_state(state, sensor_lag)
    base = base_observation(sensor_state)
    # Preserve the true elapsed-time feature; only hazard/visibility evidence is delayed.
    base[-1] = state.t / (DT * HORIZON_STEPS)
    if model_variant == "A_STATE":
        return base
    with_coc = np.concatenate([base, coc_features(state)])
    if model_variant == "B_COC":
        return with_coc
    contract_state = _observed_state(state, contract_lag)
    with_contract = np.concatenate([with_coc, contract_features(contract_state)])
    if model_variant == "C_CONTRACT":
        return with_contract
    if model_variant == "C2_PHASE_CONTRACT":
        return np.concatenate([with_contract, phase_features(contract_state)])
    raise ValueError(model_variant)


def independent_stress_oracle(before, after, metrics: EpisodeMetrics):
    crossed_entry = before.ego_x < 0.0 <= after.ego_x
    active_before = hazard_active(before)
    visible_before = is_visible(before)
    if crossed_entry:
        if before.scenario.kind == "crosswalk" and (active_before or not visible_before):
            metrics.forbidden_entry = True
        if before.scenario.kind == "stop_intersection" and (
            not before.has_stopped or active_before or not visible_before
        ):
            metrics.forbidden_entry = True
    if 0.0 <= after.ego_x <= 4.0 and hazard_active(after):
        metrics.collision = True
    released = not active_before and visible_before
    if before.scenario.kind == "stop_intersection":
        released = released and before.has_stopped
    if released and after.ego_v < 0.5:
        metrics.released_stop_steps += 1


def rollout_controller(scenario, controller):
    state = initial_state(scenario)
    metrics = EpisodeMetrics()
    initial_x = state.ego_x
    actions = []
    while not state.done:
        action, intervened = controller(state)
        metrics.interventions += int(intervened)
        new_state = step(state, action)
        independent_stress_oracle(state, new_state, metrics)
        actions.append(action)
        state = new_state
    metrics.progress = state.ego_x - initial_x
    metrics.completed = state.ego_x >= 8.0
    if len(actions) > 1:
        metrics.mean_abs_jerk = float(np.mean(np.abs(np.diff(actions))) / DT)
    return metrics


def reference_check(scenario: Scenario, reversal_time: float):
    state = initial_state(scenario)
    x_at_reversal = None
    stopped_at_reversal = False
    metrics = EpisodeMetrics()
    initial_x = state.ego_x
    actions = []
    while not state.done:
        if x_at_reversal is None and state.t >= reversal_time - DT / 2:
            x_at_reversal = state.ego_x
            stopped_at_reversal = state.has_stopped
        proposed = expert_action(state)
        action, intervened = apply_contract_shield(state, proposed)
        metrics.interventions += int(intervened)
        new_state = step(state, action)
        independent_stress_oracle(state, new_state, metrics)
        actions.append(action)
        state = new_state
    metrics.progress = state.ego_x - initial_x
    metrics.completed = state.ego_x >= 8.0
    if len(actions) > 1:
        metrics.mean_abs_jerk = float(np.mean(np.abs(np.diff(actions))) / DT)
    return metrics, float(x_at_reversal if x_at_reversal is not None else state.ego_x), stopped_at_reversal


def candidate_scenario(stress_type: str, rng: np.random.Generator):
    if stress_type == "crosswalk_reentry":
        first_end = float(rng.uniform(2.2, 3.5))
        reversal = first_end + float(rng.uniform(0.4, 1.6))
        reversal_end = reversal + float(rng.uniform(1.2, 2.8))
        scenario = Scenario(
            kind="crosswalk",
            initial_distance=float(rng.uniform(12.0, 22.0)),
            ego_speed=float(rng.uniform(5.0, 8.0)),
            hazard_intervals=((0.0, first_end), (reversal, reversal_end)),
        )
        return scenario, reversal, reversal_end

    if stress_type == "stop_cross_traffic_reappearance":
        first_end = float(rng.uniform(2.0, 3.0))
        reversal = float(rng.uniform(4.0, 5.8))
        reversal_end = reversal + float(rng.uniform(1.2, 2.6))
        scenario = Scenario(
            kind="stop_intersection",
            initial_distance=float(rng.uniform(12.0, 20.0)),
            ego_speed=float(rng.uniform(5.0, 7.5)),
            hazard_intervals=((0.0, first_end), (reversal, reversal_end)),
        )
        return scenario, reversal, reversal_end

    if stress_type == "crosswalk_reocclusion":
        first_end = float(rng.uniform(2.0, 3.2))
        reversal = first_end + float(rng.uniform(0.4, 1.5))
        reversal_end = reversal + float(rng.uniform(1.0, 2.4))
        scenario = Scenario(
            kind="crosswalk",
            initial_distance=float(rng.uniform(12.0, 22.0)),
            ego_speed=float(rng.uniform(5.0, 8.0)),
            hazard_intervals=((0.0, first_end),),
            occlusion_intervals=((reversal, reversal_end),),
        )
        return scenario, reversal, reversal_end

    first_end = float(rng.uniform(2.0, 3.0))
    reversal = float(rng.uniform(4.0, 5.8))
    reversal_end = reversal + float(rng.uniform(1.0, 2.4))
    scenario = Scenario(
        kind="stop_intersection",
        initial_distance=float(rng.uniform(12.0, 20.0)),
        ego_speed=float(rng.uniform(5.0, 7.5)),
        hazard_intervals=((0.0, first_end),),
        occlusion_intervals=((reversal, reversal_end),),
    )
    return scenario, reversal, reversal_end


def build_stress_bank(per_type: int, seed: int):
    rng = np.random.default_rng(seed)
    cases = []
    attempts = defaultdict(int)
    for stress_type in STRESS_TYPES:
        accepted = 0
        while accepted < per_type:
            attempts[stress_type] += 1
            if attempts[stress_type] > per_type * 500:
                raise RuntimeError(f"could not build feasible bank for {stress_type}")
            scenario, reversal, reversal_end = candidate_scenario(stress_type, rng)
            reference, x_at_reversal, stopped = reference_check(scenario, reversal)
            relevant_position = -5.0 <= x_at_reversal <= 1.0
            if scenario.kind == "stop_intersection":
                relevant_position = relevant_position and stopped
            if reference.unsafe or not reference.completed or not relevant_position:
                continue
            cases.append(
                StressCase(
                    case_id=len(cases),
                    stress_type=stress_type,
                    scenario=scenario,
                    reversal_time=reversal,
                    reversal_end=reversal_end,
                    reference_x_at_reversal=x_at_reversal,
                )
            )
            accepted += 1
    return cases, dict(attempts)


def load_policy(model_dir: Path, model_variant: str, seed: int):
    input_dims = {
        "A_STATE": STATE_DIM,
        "B_COC": STATE_DIM + COC_DIM,
        "C_CONTRACT": STATE_DIM + COC_DIM + CONTRACT_DIM,
        "C2_PHASE_CONTRACT": STATE_DIM + COC_DIM + CONTRACT_DIM + PHASE_DIM,
    }
    file_variant = {
        "A_STATE": "A_STATE",
        "B_COC": "B_COC",
        "C_CONTRACT": "C_LEGACY_CONTRACT",
        "C2_PHASE_CONTRACT": "C2_PHASE_CONTRACT",
    }[model_variant]
    model = TinyPolicy(input_dims[model_variant])
    model.load_state_dict(
        torch.load(model_dir / f"model-{file_variant}-seed-{seed}.pt", map_location="cpu", weights_only=True)
    )
    model.eval()

    def predict(features):
        with torch.no_grad():
            return float(model(torch.from_numpy(features.astype(np.float32)).unsqueeze(0)).item())

    return predict


def variant_controller(state, variant, policies):
    if variant == "A_STATE":
        return clip_action(policies["A_STATE"](stress_features(state, "A_STATE"))), False
    if variant == "B_COC":
        return clip_action(policies["B_COC"](stress_features(state, "B_COC"))), False
    if variant == "C_CONTRACT":
        return clip_action(policies["C_CONTRACT"](stress_features(state, "C_CONTRACT"))), False
    if variant == "C2_PHASE_CONTRACT":
        return clip_action(policies["C2_PHASE_CONTRACT"](stress_features(state, "C2_PHASE_CONTRACT"))), False
    if variant == "D_CORRECT_CONTRACT":
        proposed = policies["C2_PHASE_CONTRACT"](stress_features(state, "C2_PHASE_CONTRACT"))
        return apply_contract_shield(state, proposed)
    if variant in {"D_ORACLE_LOOKAHEAD_0P8", "D_ORACLE_LOOKAHEAD_1P2"}:
        lookahead = 0.8 if variant.endswith("0P8") else 1.2
        proposed = policies["C2_PHASE_CONTRACT"](stress_features(state, "C2_PHASE_CONTRACT"))
        return apply_contract_shield(_future_risk_state(state, lookahead), proposed)
    if variant == "C_STALE_CONTRACT_0P4":
        proposed = policies["C_CONTRACT"](stress_features(state, "C_CONTRACT", contract_lag=0.4))
        return clip_action(proposed), False
    if variant == "D_STALE_CONTRACT_0P4":
        proposed = policies["C2_PHASE_CONTRACT"](
            stress_features(state, "C2_PHASE_CONTRACT", contract_lag=0.4)
        )
        return apply_contract_shield(_observed_state(state, 0.4), proposed)
    if variant == "D_SHARED_SENSOR_LAG_0P4":
        proposed = policies["C2_PHASE_CONTRACT"](
            stress_features(state, "C2_PHASE_CONTRACT", contract_lag=0.4, sensor_lag=0.4)
        )
        return apply_contract_shield(_observed_state(state, 0.4), proposed)
    raise ValueError(variant)


def aggregate(rows):
    groups = defaultdict(list)
    for row in rows:
        groups[(row["seed"], row["variant"], row["stress_type"])].append(row)
    output = []
    for (seed, variant, stress_type), items in sorted(groups.items()):
        n = len(items)
        output.append(
            {
                "seed": seed,
                "variant": variant,
                "stress_type": stress_type,
                "episodes": n,
                "unsafe_rate": sum(x["unsafe"] for x in items) / n,
                "forbidden_entry_rate": sum(x["forbidden_entry"] for x in items) / n,
                "collision_rate": sum(x["collision"] for x in items) / n,
                "completion_rate": sum(x["completed"] for x in items) / n,
                "mean_progress_m": sum(x["progress"] for x in items) / n,
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
        "completion_rate",
        "mean_progress_m",
        "mean_interventions",
        "mean_abs_jerk",
    )
    output = []
    for variant in EVAL_VARIANTS:
        for stress_type in (*STRESS_TYPES, "ALL"):
            selected = [r for r in aggregates if r["variant"] == variant]
            if stress_type != "ALL":
                selected = [r for r in selected if r["stress_type"] == stress_type]
            else:
                selected = [
                    {m: float(np.mean([r[m] for r in selected if r["seed"] == seed])) for m in metrics}
                    for seed in sorted({r["seed"] for r in selected})
                ]
            row = {"variant": variant, "stress_type": stress_type, "seeds": len(selected)}
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
    overall = {r["variant"]: r for r in summary if r["stress_type"] == "ALL"}
    lines = [
        "# Release-reversal stress test",
        "",
        "Frozen phase-complete policies are evaluated without retraining on feasible but unseen hazard reentry and re-occlusion schedules.",
        "",
        "## Bank",
        "",
        f"- cases per stress type: {config['per_type']}",
        f"- total unique cases: {config['cases']}",
        f"- model seeds: {', '.join(map(str, config['seeds']))}",
        "- all cases are safe and complete under a current-state reference controller plus shield",
        "",
        "## Overall mean across seeds",
        "",
        "| Variant | unsafe | collision | completion | progress (m) | interventions | jerk |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for variant in EVAL_VARIANTS:
        row = overall[variant]
        lines.append(
            f"| {variant} | {row['unsafe_rate_mean']:.3f} | {row['collision_rate_mean']:.3f} | "
            f"{row['completion_rate_mean']:.3f} | {row['mean_progress_m_mean']:.3f} | "
            f"{row['mean_interventions_mean']:.3f} | {row['mean_abs_jerk_mean']:.3f} |"
        )
    lines.extend(
        [
            "",
        "Correct-contract results test unseen phase generalization. Oracle-lookahead shields are non-deployable upper bounds for future-aware contracts. Stale-contract results test whether a 0.4-second delayed contract can negate or reverse safety gains.",
            "This remains a 1D synthetic stress test, not a real-road or Alpamayo safety result.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--per-type", type=int, default=100)
    parser.add_argument("--seeds", type=int, nargs="+", default=[42, 43, 44])
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    cases, attempts = build_stress_bank(args.per_type, 20260809)
    rows = []
    for seed in args.seeds:
        policies = {
            variant: load_policy(args.model_dir, variant, seed)
            for variant in ("A_STATE", "B_COC", "C_CONTRACT", "C2_PHASE_CONTRACT")
        }
        for variant in EVAL_VARIANTS:
            for case in cases:
                metrics = rollout_controller(
                    case.scenario,
                    lambda state, v=variant, p=policies: variant_controller(state, v, p),
                )
                rows.append(
                    {
                        "seed": seed,
                        "variant": variant,
                        "case_id": case.case_id,
                        "stress_type": case.stress_type,
                        "reversal_time": case.reversal_time,
                        "reversal_end": case.reversal_end,
                        "reference_x_at_reversal": case.reference_x_at_reversal,
                        **asdict(metrics),
                        "unsafe": metrics.unsafe,
                    }
                )
    aggregates = aggregate(rows)
    summary = summarize(aggregates)
    config = {
        "per_type": args.per_type,
        "cases": len(cases),
        "seeds": args.seeds,
        "attempts": attempts,
        "model_dir": str(args.model_dir),
        "stress_seed": 20260809,
    }
    case_rows = [
        {
            "case_id": case.case_id,
            "stress_type": case.stress_type,
            "kind": case.scenario.kind,
            "initial_distance": case.scenario.initial_distance,
            "ego_speed": case.scenario.ego_speed,
            "reversal_time": case.reversal_time,
            "reversal_end": case.reversal_end,
            "reference_x_at_reversal": case.reference_x_at_reversal,
            "hazard_intervals": repr(case.scenario.hazard_intervals),
            "occlusion_intervals": repr(case.scenario.occlusion_intervals),
        }
        for case in cases
    ]
    write_csv(args.output / "stress_cases.csv", case_rows)
    write_csv(args.output / "episode_metrics.csv", rows)
    write_csv(args.output / "aggregate_by_seed.csv", aggregates)
    write_csv(args.output / "summary_across_seeds.csv", summary)
    (args.output / "result.json").write_text(
        json.dumps({"config": config, "summary": summary}, indent=2), encoding="utf-8"
    )
    write_report(args.output / "REPORT.md", config, summary)
    print(json.dumps({"output": str(args.output), "config": config}, indent=2))


if __name__ == "__main__":
    main()
