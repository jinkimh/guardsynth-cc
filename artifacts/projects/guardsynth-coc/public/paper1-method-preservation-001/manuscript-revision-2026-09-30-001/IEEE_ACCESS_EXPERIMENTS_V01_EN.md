# Experiments and Results

## A. Evaluation Objectives and Setup

We distinguish the behavioral effects of adding explicit constraints to CoC from the checkability of the EBLC-to-CNL development path. P1 and P2 are both our constraint-enhancement approaches. P1–P2 is an internal comparison of development paths, not a contest against an external method.

**Table E1. Comparison conditions and roles**

| Condition | Information added to CoC | Evaluation role |
|---|---|---|
| P0 | No additional constraint | CoC-only baseline |
| P1 | Existing natural-language behavioral constraint | Our preceding constraint-enhancement approach |
| P2 | CNL generated after specifying and checking the same rule in EBLC | Formally supported constraint-development path |

The conditions share images, candidates, reference labels, and splits. P1 and P2 receive constraints during training and evaluation; the P2 model receives CNL, not solver verdicts. Different contracts can assign different reference actions to an otherwise identical input, so P0 lacks information required to distinguish the pair. This evaluates supplied-constraint use rather than a causal training benefit under identical information.

We use Qwen3-VL-2B-Instruct with LoRA and seeds 42, 17, and 123. Within each task family, all arms use the same examples, three epochs, optimizer settings, and final-checkpoint policy. Temporal, static, and maneuver runs respectively use 960, 576, and 384 training rows and 180, 108, and 72 optimizer updates per fit. LoRA rank/alpha/dropout are 8/16/0.05; batch size is 2 with accumulation 8, AdamW learning rate 0.0002, and weight decay 0.01. Candidate scalars are supplied in text. The temporal family uses 40/10/10 distinct training/validation/test images; the static test reuses schematic images, and the maneuver family uses two repeated diagrams. Rows are not independent road scenes. Supplement S1 and S8 give split inventories and budgets.

The main metrics are **accuracy** against the highest-progress admissible candidate, **violation rate**, and **contract-pair accuracy**, which requires both members of a pair to be correct. An admissible but lower-progress choice is inaccurate without violating the contract. Tables show three-seed means; the main performance figure also shows individual seeds. Compliant completion is auxiliary and is not independent evidence when it equals one minus violation rate.

## B. Performance Across Behavioral Tasks

The six task rows correspond directly to Table M1: each prediction selects a candidate whose stored measurements are bound to that task's logical condition. Independent task rules determine admissibility and the reference choice; SMT checks the same bound candidate separately. Specification checks and prediction metrics therefore have different denominators.

**Table E2. Primary accuracy / violation rate, %, mean over three seeds**

| Task | P0 | P1 | P2 |
|---|---|---|---|
| Maximum speed | 50.00 / 24.31 | 100.00 / 0.00 | 100.00 / 0.00 |
| Minimum clearance | 50.00 / 24.31 | 100.00 / 0.00 | 100.00 / 0.00 |
| Minimum entry delay | 50.00 / 24.31 | 100.00 / 0.00 | 100.00 / 0.00 |
| Entry after clearance and waiting | 49.86 / 19.17 | 96.81 / 1.39 | 98.06 / 0.83 |
| Stopping | 50.00 / 23.61 | 100.00 / 0.00 | 100.00 / 0.00 |
| Lane change | 50.00 / 38.19 | 100.00 / 0.00 | 97.92 / 0.00 |

P1 and P2 have higher accuracy and lower violation rates than P0 for all six task types. Temporal accuracy gains over P0 are 46.94 and 48.19 percentage points for P1 and P2, with violation reductions of 17.78 and 18.33 points. P1 and P2 tie in the three static types and stopping. Residual P2 lane-change errors select admissible but lower-progress candidates; compliant completion is 100%. Temporal P2 compliant completion is 99.17%.

![Figure 6. Task-wise performance](../../../artifacts/projects/guardsynth-coc/public/paper1-method-preservation-001/manuscript-revision-2026-09-30-001/figures/task-performance-en.png)

Figure 6. Accuracy and violation rate by task. Large points are means and small points are individual seeds. Zero observed violations refer to the evaluated samples.

P2 does not exceed P1 under every seed and condition. We report the effects of both paths relative to P0; formal noninferiority between P1 and P2 is not tested.

## C. Contract Changes and Correct Association

Contract-pair accuracy is 0% for P0 in all three task families. In temporal, static, and maneuver families, respectively, P1 achieves 93.61%, 100%, and 100%, and P2 achieves 96.11%, 100%, and 97.92%. Constraint-conditioned models can change their selections when the rule changes while the visual input remains fixed. P0's low values must be interpreted with its missing contract information.

Shuffling training-time case–constraint associations while restoring correct constraints at evaluation gives accuracies of 50.56%, 50.69%, and 49.65%. Temporal shuffling uses natural-language guards, whereas new static and maneuver shuffling permutes P2 CNL within subtype; these are not pooled as one identical intervention. The results support the importance of correct case–constraint association beyond adding sentences alone.

![Figure 7. Contract pairs and association shuffling](../../../artifacts/projects/guardsynth-coc/public/paper1-method-preservation-001/manuscript-revision-2026-09-30-001/figures/contract-linkage-en.png)

Figure 7. Left: contract-pair accuracy. Right: action accuracy of P2 with correct associations versus shuffled training associations. Points are three-seed means; static and maneuver values aggregate their subtypes.

In one recorded prediction with clearance at 11.0 s and a 1.5 s wait, P0 chooses entry at 11.5 s, while P1 and P2 choose the admissible boundary at 12.5 s. Another P2 example enters 0.1 s too early. These post-hoc explanatory cases are detailed in Supplement S5.

## D. Checkability of Specifications and CNL

We inject errors involving negation, thresholds, release conditions, comparison direction, and units into the schema, evidence, Core, and CNL checking path. Supplement S3 reports the six supported types and their checking layers. This quality evaluation is distinct from model accuracy.

**Table E3. Specification and CNL checks**

| Input category | Count | Outcome |
|---|---|---|
| Six supported error types | 144 | 144 detected; 0 missed |
| Shared evidence–specification errors | 24 | 0 detected; 24 missed |
| Normal contracts | 24 | 24 accepted; 0 false alarms |

Detection across all 168 errors is 85.71%. These are multilayer checks, not the result of SAT solving alone. Errors shared by trusted evidence and specification can remain undetected; satisfiability and factual evidence validity are distinct.

All 100 temporal boundary queries match expected outcomes: 76 SAT, 24 UNSAT, and no UNKNOWN. Additional candidate checks and comparisons with model judgments appear in Supplement S8.

![Figure 8. SAT and UNSAT around an admissibility boundary](../../../artifacts/projects/guardsynth-coc/public/paper1-method-preservation-001/manuscript-revision-2026-09-30-001/figures/smt-boundary-en.png)

Figure 8. With clearance at 11.000 s and a 0.500 s wait, entry at 11.499 s is UNSAT; 11.500 s and 11.501 s are SAT. The 1 ms logical-time expansion does not imply vehicle-control precision.

UNSAT here excludes a prohibited action rather than counting a defective specification. By contrast, increasing an injected wait by 100 ms makes an originally permitted query UNSAT, while removing the release restriction makes a prohibited query SAT. Unexpected outcomes require reviewing the source, threshold, and clause, then rechecking both sides of the boundary. An inconsistent base contract or UNKNOWN is not accepted as verification evidence. Supplement S3 retains the representative conflict set and response rules.

## E. Unseen Conditions and Interpretation

**Table E4. Unseen numeric/time conditions: accuracy / violation rate, %, three-seed means**

| Task family | P0 | P1 | P2 |
|---|---|---|---|
| Temporal | 49.86 / 18.47 | 96.67 / 2.22 | 96.67 / 1.53 |
| Static | 50.00 / 22.92 | 99.54 / 0.00 | 97.22 / 0.23 |
| Maneuver | 50.00 / 30.90 | 100.00 / 0.00 | 98.96 / 0.00 |

Both constraint-enhancement paths outperform P0 on unseen numeric/time conditions. Sensitivity to new wording differs by task: static paraphrasing gives P2 accuracy of 80.32% and violation rate of 7.87%. Paraphrasing, combined hard conditions, image interventions, and specification-derived auxiliary-cost learning are secondary diagnostics; favorable and unfavorable outcomes are retained in the supplement.

The results concern supplied synthetic constraints and finite candidates. Textual scalars, repeated diagrams, one model, and three seeds limit claims about real-road visual understanding, closed-loop safety, or Alpamayo training. Constraint availability and the causal effect of verification are distinguished. Detailed variability, conditional intervals, and archived operational-criterion outcomes remain in the supplement.

Overall, multiple action tasks show benefits from constraint-enhanced CoC, while the EBLC-supported development path combines high action-selection performance with explicit checks of constraint errors and admissible/prohibited boundaries.
