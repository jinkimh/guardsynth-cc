# CoC safety-contract micro-world

## Purpose

This experiment tests one narrow mechanism-level hypothesis:

> Under successful-demonstration-only training, action-oriented CoC does not necessarily encode forbidden, hold, release, and uncertainty-fallback conditions. A compiled safety contract and a runtime contract shield may reduce held-out counterfactual violations.

It does **not** test Alpamayo, camera perception, real-vehicle safety, or the correctness of a language-to-contract parser.

## Scenarios

- `crosswalk`: YIELD intent; held-out pedestrians remain in or become occluded near the conflict zone.
- `stop_intersection`: STOP intent; held-out cross traffic clears late and can be occluded. A complete stop is stateful.
- `lead_brake`: DECELERATE intent; held-out lead vehicles brake earlier and harder than training examples.

All scenes use a deterministic 1D longitudinal point-mass kinematic world with a 0.2-second closed-loop update and a 12-second horizon. There is no lateral coordinate, steering, pedestrian geometry, or sensor rendering. The training data contains only trajectories from a contract-aware expert controller.

## Conditions

| ID | Policy input / enforcement |
|---|---|
| A | state only |
| B | state + action-intent CoC (`YIELD`, `STOP`, `DECELERATE`) |
| C | B + compiled dynamic contract status (`hold`, `release`, uncertainty fallback, stop completion, margin, speed cap) |
| D | C + deterministic runtime contract shield |

Condition C uses structured contract fields rather than natural language. Testing a natural-language compiler before establishing that the compiled contract is useful would confound parser error with contract utility.

## Environment

The current machine already has the required packages in the Alpamayo runtime. No new packages are downloaded.

```bash
export MPLCONFIGDIR=/tmp/coc-contract-mpl
runtime/alpamayo/ar1_venv/bin/python -m unittest \
  experiments.contract_micro_world.test_contract_micro_world

runtime/alpamayo/ar1_venv/bin/python \
  experiments/contract_micro_world/run_experiment.py \
  --output artifacts/results/public/contract-microworld-v0/pilot-2026-08-04
```

Standalone minimum dependencies are Python 3.11+, NumPy 2.x, and PyTorch 2.x. CPU execution is supported.

## Interpretation constraints

- A C-versus-B gain supports the utility of an already-compiled contract representation. It does not validate automatic extraction from CoC.
- A D-versus-C gain supports runtime enforcement. It does not show that CoC itself became safer.
- Reduced violations are meaningful only if completion, released-but-stopped time, progress, and jerk do not collapse into an always-stop policy.
- Synthetic results are a go/no-go gate for a public closed-loop benchmark, not an autonomous-driving safety claim.

## Phase-complete STOP replication

The v1 pilot had no successful training state in which a complete STOP was followed by a continued HOLD for cross traffic. The controlled replication preserves the original non-STOP training scenes and replaces only half of the STOP training scenes with `STOP -> HOLD -> RELEASE` demonstrations. It also compares the legacy contract with explicit temporal phase features and a shield.

```bash
runtime/alpamayo/ar1_venv/bin/python \
  experiments/contract_micro_world/run_phase_complete_experiment.py \
  --output artifacts/results/public/contract-microworld-v1/pilot-phase-complete-isolated-2026-08-04-v2 \
  --train-per-kind 200 --test-per-kind 100 --epochs 35 --seeds 42 43 44
```

The primary Korean assessment is in the run directory's `PHASE_COMPLETE_ASSESSMENT_KO.md`.

## Unseen release-reversal stress test

Frozen phase-complete policies are evaluated without retraining on pedestrian reentry, cross-traffic reappearance, and repeated occlusion. Correct, stale, reactive-shield, and perfect-lookahead upper-bound conditions are compared.

```bash
runtime/alpamayo/ar1_venv/bin/python \
  experiments/contract_micro_world/run_release_reversal_stress.py \
  --model-dir artifacts/results/public/contract-microworld-v1/pilot-phase-complete-isolated-2026-08-04-v2 \
  --output artifacts/results/public/contract-microworld-v2/pilot-release-reversal-2026-08-04-v1 \
  --per-type 100 --seeds 42 43 44
```
