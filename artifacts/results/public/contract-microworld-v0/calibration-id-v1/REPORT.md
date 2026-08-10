# Contract micro-world pilot result

## Scope

This is a controlled synthetic closed-loop feasibility test. It does not establish real-vehicle or Alpamayo safety.
The only manipulated factor is whether the tiny policy receives action-oriented CoC features, compiled contract status, and a runtime contract shield.

## Configuration

- train scenarios per kind: 50
- OOD scenarios per kind: 20
- model seeds: 42
- epochs: 20
- policy parameters: 4,929

## Closed-loop summary (mean across seeds)

| Split | Variant | unsafe episode | forbidden entry | collision | completion | released-but-stopped (s) | interventions/episode |
|---|---|---:|---:|---:|---:|---:|---:|
| ID | A_STATE | 0.067 | 0.050 | 0.017 | 0.750 | 0.023 | 0.000 |
| ID | B_COC | 0.067 | 0.050 | 0.017 | 0.783 | 0.030 | 0.000 |
| ID | C_CONTRACT | 0.000 | 0.000 | 0.000 | 1.000 | 0.067 | 0.000 |
| ID | D_CONTRACT_SHIELD | 0.000 | 0.000 | 0.000 | 1.000 | 0.067 | 0.583 |
| OOD | A_STATE | 1.000 | 0.667 | 1.000 | 0.883 | 0.000 | 0.000 |
| OOD | B_COC | 0.983 | 0.667 | 0.983 | 0.967 | 0.000 | 0.000 |
| OOD | C_CONTRACT | 0.083 | 0.017 | 0.083 | 1.000 | 0.130 | 0.000 |
| OOD | D_CONTRACT_SHIELD | 0.000 | 0.000 | 0.000 | 1.000 | 0.130 | 1.367 |

## Interpretation gate

- The A/B baselines must first succeed on ID scenes; otherwise an OOD gap can be explained by failed imitation rather than missing constraints.
- GO only if the compiled contract and/or shield reduces held-out unsafe outcomes consistently across seeds.
- A shield-only gain supports runtime enforcement, not the claim that natural-language CoC itself teaches the constraint.
- Any safety gain must be read together with completion, released-stop time, progress, and jerk to detect trivial always-stop behavior.
- The next experiment should replace synthetic state with a public closed-loop benchmark only after this mechanism-level gate passes.
