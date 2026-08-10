# Phase-complete STOP contract experiment

## Change from v1

- Added successful post-stop HOLD demonstrations to every training condition.
- Added C2 with explicit APPROACH/STOP_DWELL/HOLD/RELEASED phase features.
- Removed the v1 pre-line collision proxy and used a direct crossing oracle that does not call contract_status.
- D reuses C2 and adds the deterministic runtime shield.

## Training phase coverage

- APPROACH: 3766
- STOP_DWELL: 200
- HOLD: 1404
- RELEASED: 3600

## Mean across three seeds

| Split | Variant | all unsafe | STOP unsafe | completion | progress (m) | jerk | interventions |
|---|---|---:|---:|---:|---:|---:|---:|
| ID | A_STATE | 0.000 | 0.000 | 1.000 | 46.317 | 1.319 | 0.000 |
| ID | B_COC | 0.000 | 0.000 | 1.000 | 46.355 | 1.334 | 0.000 |
| ID | C_LEGACY_CONTRACT | 0.000 | 0.000 | 1.000 | 46.423 | 2.753 | 0.000 |
| ID | C2_PHASE_CONTRACT | 0.000 | 0.000 | 1.000 | 46.427 | 2.716 | 0.000 |
| ID | D_PHASE_SHIELD | 0.000 | 0.000 | 1.000 | 46.352 | 2.781 | 1.269 |
| OOD | A_STATE | 0.026 | 0.000 | 1.000 | 28.111 | 1.954 | 0.000 |
| OOD | B_COC | 0.014 | 0.000 | 1.000 | 28.166 | 2.342 | 0.000 |
| OOD | C_LEGACY_CONTRACT | 0.000 | 0.000 | 1.000 | 28.135 | 3.561 | 0.000 |
| OOD | C2_PHASE_CONTRACT | 0.000 | 0.000 | 1.000 | 28.083 | 3.402 | 0.000 |
| OOD | D_PHASE_SHIELD | 0.000 | 0.000 | 1.000 | 28.005 | 3.442 | 2.539 |

## Interpretation

All A/B/C/C2 policies reduced STOP forbidden entry to zero after post-stop HOLD demonstrations were added. This supports correction through ordinary successful imitation data within the finite test bank.
C2 did not improve any binary safety metric over legacy C, so this run does not establish an independent benefit from explicit phase one-hot features.
D did not improve any binary safety metric over C2 but intervened 2.539 times per OOD episode on average, indicating conservative enforcement cost in this bank.
This remains a synthetic mechanism test and does not establish real-road or Alpamayo safety.
