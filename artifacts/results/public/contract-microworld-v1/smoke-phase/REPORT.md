# Phase-complete STOP contract experiment

## Change from v1

- Added successful post-stop HOLD demonstrations to every training condition.
- Added C2 with explicit APPROACH/STOP_DWELL/HOLD/RELEASED phase features.
- Removed the v1 pre-line collision proxy and used a direct crossing oracle that does not call contract_status.
- D reuses C2 and adds the deterministic runtime shield.

## Training phase coverage

- APPROACH: 374
- STOP_DWELL: 20
- HOLD: 147
- RELEASED: 360

## Mean across three seeds

| Split | Variant | all unsafe | STOP unsafe | completion | progress (m) | jerk | interventions |
|---|---|---:|---:|---:|---:|---:|---:|
| ID | A_STATE | 0.467 | 1.000 | 1.000 | 47.736 | 0.150 | 0.000 |
| ID | B_COC | 0.467 | 1.000 | 1.000 | 47.915 | 0.113 | 0.000 |
| ID | C_LEGACY_CONTRACT | 0.300 | 0.900 | 0.667 | 45.770 | 0.332 | 0.000 |
| ID | C2_PHASE_CONTRACT | 0.067 | 0.000 | 0.767 | 43.943 | 0.188 | 0.000 |
| ID | D_PHASE_SHIELD | 0.000 | 0.000 | 0.767 | 43.723 | 0.450 | 0.867 |
| OOD | A_STATE | 1.000 | 1.000 | 1.000 | 29.159 | 0.200 | 0.000 |
| OOD | B_COC | 1.000 | 1.000 | 1.000 | 29.191 | 0.134 | 0.000 |
| OOD | C_LEGACY_CONTRACT | 0.767 | 0.800 | 0.767 | 27.091 | 0.309 | 0.000 |
| OOD | C2_PHASE_CONTRACT | 0.733 | 0.200 | 0.767 | 25.883 | 0.278 | 0.000 |
| OOD | D_PHASE_SHIELD | 0.000 | 0.000 | 0.767 | 25.112 | 0.775 | 5.067 |

## Interpretation

A/B gains after phase-complete demonstrations support correction through ordinary imitation data.
C2 gains over C isolate the value of explicit temporal phase representation.
D gains over C2 isolate runtime enforcement within this micro-world.
This remains a synthetic mechanism test and does not establish real-road or Alpamayo safety.
