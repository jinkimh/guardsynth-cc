# Phase-complete STOP contract experiment

## Change from v1

- Added successful post-stop HOLD demonstrations to every training condition.
- Added C2 with explicit APPROACH/STOP_DWELL/HOLD/RELEASED phase features.
- Removed the v1 pre-line collision proxy and used a direct crossing oracle that does not call contract_status.
- D reuses C2 and adds the deterministic runtime shield.

## Training phase coverage

- APPROACH: 3818
- STOP_DWELL: 200
- HOLD: 1343
- RELEASED: 3600

## Mean across three seeds

| Split | Variant | all unsafe | STOP unsafe | completion | progress (m) | jerk | interventions |
|---|---|---:|---:|---:|---:|---:|---:|
| ID | A_STATE | 0.000 | 0.000 | 1.000 | 45.713 | 1.290 | 0.000 |
| ID | B_COC | 0.000 | 0.000 | 1.000 | 45.719 | 1.310 | 0.000 |
| ID | C_LEGACY_CONTRACT | 0.000 | 0.000 | 1.000 | 45.804 | 2.755 | 0.000 |
| ID | C2_PHASE_CONTRACT | 0.000 | 0.000 | 1.000 | 45.781 | 2.754 | 0.000 |
| ID | D_PHASE_SHIELD | 0.000 | 0.000 | 1.000 | 45.696 | 2.821 | 2.266 |
| OOD | A_STATE | 0.000 | 0.000 | 1.000 | 28.147 | 2.044 | 0.000 |
| OOD | B_COC | 0.028 | 0.000 | 1.000 | 28.196 | 2.172 | 0.000 |
| OOD | C_LEGACY_CONTRACT | 0.000 | 0.000 | 1.000 | 28.134 | 3.614 | 0.000 |
| OOD | C2_PHASE_CONTRACT | 0.000 | 0.000 | 1.000 | 28.096 | 3.399 | 0.000 |
| OOD | D_PHASE_SHIELD | 0.000 | 0.000 | 1.000 | 28.023 | 3.462 | 2.467 |

## Interpretation

A/B gains after phase-complete demonstrations support correction through ordinary imitation data.
C2 gains over C isolate the value of explicit temporal phase representation.
D gains over C2 isolate runtime enforcement within this micro-world.
This remains a synthetic mechanism test and does not establish real-road or Alpamayo safety.
