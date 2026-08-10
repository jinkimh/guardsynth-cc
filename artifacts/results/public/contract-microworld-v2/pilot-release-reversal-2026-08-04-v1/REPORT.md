# Release-reversal stress test

Frozen phase-complete policies are evaluated without retraining on feasible but unseen hazard reentry and re-occlusion schedules.

## Bank

- cases per stress type: 100
- total unique cases: 400
- model seeds: 42, 43, 44
- all cases are safe and complete under a current-state reference controller plus shield

## Overall mean across seeds

| Variant | unsafe | collision | completion | progress (m) | interventions | jerk |
|---|---:|---:|---:|---:|---:|---:|
| A_STATE | 0.466 | 0.266 | 1.000 | 25.026 | 0.000 | 1.680 |
| B_COC | 0.486 | 0.273 | 1.000 | 25.064 | 0.000 | 1.573 |
| C_CONTRACT | 0.214 | 0.143 | 1.000 | 25.055 | 0.000 | 2.451 |
| C2_PHASE_CONTRACT | 0.379 | 0.259 | 1.000 | 25.026 | 0.000 | 2.222 |
| D_CORRECT_CONTRACT | 0.048 | 0.018 | 1.000 | 25.025 | 9.935 | 2.758 |
| D_ORACLE_LOOKAHEAD_0P8 | 0.001 | 0.000 | 1.000 | 24.905 | 8.789 | 2.185 |
| D_ORACLE_LOOKAHEAD_1P2 | 0.000 | 0.000 | 1.000 | 24.897 | 8.863 | 1.955 |
| C_STALE_CONTRACT_0P4 | 0.481 | 0.248 | 1.000 | 25.020 | 0.000 | 2.608 |
| D_STALE_CONTRACT_0P4 | 0.347 | 0.163 | 1.000 | 25.057 | 10.399 | 2.696 |
| D_SHARED_SENSOR_LAG_0P4 | 0.349 | 0.164 | 1.000 | 25.046 | 10.373 | 2.684 |

Correct-contract results test unseen phase generalization. Oracle-lookahead shields are non-deployable upper bounds for future-aware contracts. Stale-contract results test whether a 0.4-second delayed contract can negate or reverse safety gains.
This remains a 1D synthetic stress test, not a real-road or Alpamayo safety result.
