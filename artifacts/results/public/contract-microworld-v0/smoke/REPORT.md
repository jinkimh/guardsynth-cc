# Contract micro-world pilot result

## Scope

This is a controlled synthetic closed-loop feasibility test. It does not establish real-vehicle or Alpamayo safety.
The only manipulated factor is whether the tiny policy receives action-oriented CoC features, compiled contract status, and a runtime contract shield.

## Configuration

- train scenarios per kind: 10
- OOD scenarios per kind: 5
- model seeds: 42, 43
- epochs: 3
- policy parameters: 4,929

## OOD closed-loop summary (mean across seeds)

| Variant | unsafe episode | forbidden entry | collision | completion | released-but-stopped (s) | interventions/episode |
|---|---:|---:|---:|---:|---:|---:|
| A_STATE | 1.000 | 0.667 | 1.000 | 1.000 | 0.000 | 0.000 |
| B_COC | 1.000 | 0.667 | 1.000 | 1.000 | 0.000 | 0.000 |
| C_CONTRACT | 1.000 | 0.667 | 1.000 | 1.000 | 0.000 | 0.000 |
| D_CONTRACT_SHIELD | 0.000 | 0.000 | 0.000 | 0.333 | 0.300 | 17.367 |

## Interpretation gate

- GO only if the compiled contract and/or shield reduces held-out unsafe outcomes consistently across seeds.
- A shield-only gain supports runtime enforcement, not the claim that natural-language CoC itself teaches the constraint.
- Any safety gain must be read together with completion, released-stop time, progress, and jerk to detect trivial always-stop behavior.
- The next experiment should replace synthetic state with a public closed-loop benchmark only after this mechanism-level gate passes.
