# Release-reversal stress test

Frozen phase-complete policies are evaluated without retraining on feasible but unseen hazard reentry and re-occlusion schedules.

## Bank

- cases per stress type: 10
- total unique cases: 40
- model seeds: 42
- all cases are safe and complete under a current-state reference controller plus shield

## Overall mean across seeds

| Variant | unsafe | collision | completion | progress (m) | interventions | jerk |
|---|---:|---:|---:|---:|---:|---:|
| A_STATE | 0.575 | 0.300 | 1.000 | 25.277 | 0.000 | 1.730 |
| B_COC | 0.600 | 0.375 | 1.000 | 25.302 | 0.000 | 1.564 |
| C_CONTRACT | 0.200 | 0.150 | 1.000 | 25.329 | 0.000 | 2.526 |
| C2_PHASE_CONTRACT | 0.525 | 0.300 | 1.000 | 25.277 | 0.000 | 2.168 |
| D_CORRECT_CONTRACT | 0.100 | 0.050 | 1.000 | 25.185 | 9.125 | 2.796 |
| C_STALE_CONTRACT_0P4 | 0.425 | 0.250 | 1.000 | 25.234 | 0.000 | 2.590 |
| D_STALE_CONTRACT_0P4 | 0.425 | 0.150 | 1.000 | 25.303 | 9.875 | 2.680 |
| D_SHARED_SENSOR_LAG_0P4 | 0.425 | 0.150 | 1.000 | 25.325 | 9.850 | 2.677 |

Correct-contract results test unseen phase generalization. Stale-contract results test whether a 0.4-second delayed contract can negate or reverse safety gains.
This remains a 1D synthetic stress test, not a real-road or Alpamayo safety result.
