# Contract micro-world pilot result

## Scope

This is a controlled synthetic closed-loop feasibility test. It does not establish real-vehicle or Alpamayo safety.
The only manipulated factor is whether the tiny policy receives action-oriented CoC features, compiled contract status, and a runtime contract shield.

## Configuration

- train scenarios per kind: 200
- OOD scenarios per kind: 100
- model seeds: 42, 43, 44
- epochs: 35
- policy parameters: 4,929--5,505

## Closed-loop summary (mean across seeds)

| Split | Variant | unsafe episode | forbidden entry | collision | completion | released-but-stopped (s) | interventions/episode |
|---|---|---:|---:|---:|---:|---:|---:|
| ID | A_STATE | 0.000 | 0.000 | 0.000 | 1.000 | 0.067 | 0.000 |
| ID | B_COC | 0.000 | 0.000 | 0.000 | 1.000 | 0.067 | 0.000 |
| ID | C_CONTRACT | 0.000 | 0.000 | 0.000 | 1.000 | 0.067 | 0.000 |
| ID | D_CONTRACT_SHIELD | 0.000 | 0.000 | 0.000 | 1.000 | 0.067 | 1.110 |
| OOD | A_STATE | 0.264 | 0.239 | 0.264 | 0.992 | 0.060 | 0.000 |
| OOD | B_COC | 0.387 | 0.328 | 0.386 | 1.000 | 0.045 | 0.000 |
| OOD | C_CONTRACT | 0.078 | 0.071 | 0.078 | 1.000 | 0.096 | 0.000 |
| OOD | D_CONTRACT_SHIELD | 0.000 | 0.000 | 0.000 | 1.000 | 0.130 | 2.961 |

## Interpretation gate

- The A/B baselines must first succeed on ID scenes; otherwise an OOD gap can be explained by failed imitation rather than missing constraints.
- GO only if the compiled contract and/or shield reduces held-out unsafe outcomes consistently across seeds.
- A shield-only gain supports runtime enforcement, not the claim that natural-language CoC itself teaches the constraint.
- Any safety gain must be read together with completion, released-stop time, progress, and jerk to detect trivial always-stop behavior.
- The next experiment should replace synthetic state with a public closed-loop benchmark only after this mechanism-level gate passes.
