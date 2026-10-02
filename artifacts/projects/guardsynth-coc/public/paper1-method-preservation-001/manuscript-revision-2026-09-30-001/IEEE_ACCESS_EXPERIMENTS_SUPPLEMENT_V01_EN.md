# Experimental Supplement

## S1. Evaluation Objectives and Experimental Setup

We distinguish two questions. First, can correspondence checks on EBLC specifications and generated CNL identify supported errors? Second, does providing this CNL alongside CoC improve constraint-compliant action selection relative to CoC alone? The first question concerns the checkability of the specification pipeline; the second concerns action selection using explicit constraints. Neither question isolates a causal learning benefit of the verification algorithm itself.

The main conditions are P0, original CoC only; P1, CoC with the existing natural-language constraint; and P2, CoC with EBLC-generated CNL. P1 and P2 are both variants of our constraint-augmentation approach and are compared with P0. Their mutual comparison is secondary, examining whether high action-selection performance is also observed through the formalization pathway. All three conditions share images, action candidates, reference targets, and data splits.

**Table E1. Definitions of the primary comparison conditions**

| Condition and name | Content added to the original CoC | Comparison purpose |
|---|---|---|
| P0 — CoC only | No additional constraint; the original CoC supplies situation and action rationale | Baseline without an explicit behavioral constraint |
| P1 — CoC + existing natural-language constraint | The supplied synthetic rule expressed directly in the existing wording, without EBLC-to-CNL conversion | Existing constraint augmentation relative to P0 |
| P2 — CoC + EBLC-generated CNL | The same rule specified and checked through EBLC, then rendered as a natural-language constraint | Constraint augmentation through the formalization pathway relative to P0 |

All three conditions receive the same ordered images and action candidates. The distinction in Table E1 is the constraint text appended to CoC; both P1 and P2 receive it during training and evaluation. P2 supplies generated CNL to the model, not EBLC code or a SAT/UNSAT verdict. For example, P0 contains “Yield to the crossing pedestrian, then proceed through the intersection.” P1 appends the existing instruction to remain stopped for at least 0.5 s after clearance, while P2 appends the CNL instruction to enter only after the zone has remained clear for at least 0.5 s. These are explanatory excerpts of the temporal condition; both complete constraints also prohibit entry while occupied. P1 is therefore our existing natural-language constraint variant, not an external competing method, and P2 is the EBLC-generated variant studied here.

**Table E2. Data and training settings**

| Component | Setting | Comparison scope |
|---|---|---|
| Training split | 40 synthetic images; 960 rows per condition | Clearance times 6.0–9.9 s |
| Validation / test | 10 images and 240 rows per condition in each split | Clearance times 10.0–10.9 s / 11.0–11.9 s |
| Derived records | 3 candidate patterns × 4 label rotations × 2 contracts per image | The 24 rows are not independent scenes |
| Rules | Training waits of 0.5 / 1.5 s | Unseen-duration evaluation uses 0.8 / 1.8 s |
| Model | Qwen3-VL-2B-Instruct | Each condition starts from the same pretrained base |
| LoRA | Rank 8, alpha 16, dropout 0.05 | Language-attention q/k/v/o projections |
| Optimization | AdamW, learning rate 0.0002, weight decay 0.01 | bfloat16, SDPA; answer-token loss only |
| Training budget | Batch 2 × accumulation 8; 3 epochs; 180 updates | Matched examples and updates per condition and seed |
| Repeats and selection | Seeds 42, 17, 123; final checkpoint | No validation- or test-based checkpoint selection |

Images do not overlap across training, validation, and test splits. Paraphrase and unseen-duration evaluations reuse test images; the latter also shifts candidate entry times by 0.3 s. These variations therefore do not add independent road scenes. The main task uses a single-clearance synthetic environment without reoccupation, and waiting durations are supplied experimental rules. Candidate progress values are abstract utility scores, not measured travel distances or vehicle-control performance.

Inputs contain a temporally ordered visual representation, CoC, and action candidates. P1 and P2 receive constraint sentences during both training and evaluation. An independently implemented environment rule identifies the highest-progress admissible candidate as the reference target. Selected actions are also checked against EBLC, but solver verdicts and target labels are not input hints. P0 lacks the waiting duration, so identical inputs can have different targets under paired contracts. This information asymmetry is part of evaluating explicit constraint provision, not an equal-information intervention isolating verification. Input lengths also differ, so token counts and FLOPs are not matched across the main conditions.

Three additional conditions probe representation and binding: NATURAL_GUARD uses another natural-language formulation; SHUFFLED_GUARD shuffles the training correspondence between guards and examples; and LOGIC_GUARD uses logical text. LOGIC_GUARD is an input representation, not an internal solver. Six conditions and three seeds yield 18 fits and 3,240 updates. The 17,280 predictions across four evaluation sets include validation. Full-condition results are provided in the supplement.

## S2. Metrics and Statistical Units

Evaluation dimensions are checkability, action selection, nominal progress, and changes in conditions. Checkability is measured by detections, misses, and false rejections of valid inputs. The central behavioral metrics are optimal admissible-action accuracy, constraint-violation rate, and contract-pair accuracy.

Accuracy is the fraction of all evaluation records matching the independent reference target. Violation rate is the fraction selecting entry with $t_{entry}<t_{clear}+\Delta$; it is not a collision rate. Contract-pair accuracy is the fraction of pairs for which both contracts on the same scene and candidates receive correct selections. The 240 records per condition and seed form 120 pairs. An admissible but lower-progress choice is nonviolating but incorrect under the optimal-action target.

Auxiliary metrics are valid-label coverage, goal completion, compliant goal completion, and unnecessary waiting. Goal completion denotes selection of an entering candidate; compliant completion additionally requires no violation. Unnecessary waiting denotes selecting a stopped candidate when a progressing admissible candidate exists. Across the expanded evaluations, coverage and goal completion were 100%, and unnecessary waiting was 0%. Compliant completion is consequently the complement of violation rate here and is not counted as independent additional evidence of improvement.

Progress loss and early-entry shortfall are exploratory measures defined after viewing results. Conditional progress loss subtracts the selected score from the best admissible score, using only compliant selections as its denominator. Early-entry shortfall measures time remaining to the permission boundary among violations; when no violations occur, it is not applicable rather than zero. Neither measure estimates physical distance or collision severity.

Main tables and plots report three-seed means and population standard deviations (ddof=0). Existing conditional 95% confidence intervals in the supplement use 2,000 bootstrap resamples of clearance-time clusters, keeping candidate patterns, label rotations, and contract pairs together. These intervals are conditional on three seeds and ten test clusters, not estimates of uncertainty across all road environments or model populations. Seed standard deviation and cluster confidence intervals describe different variation and are not used interchangeably.

## S3. Specification and CNL Checking Results

### 1. SAT and UNSAT Outcomes for Unmodified Contracts

SMT outcomes are interpreted relative to the query purpose. SAT for the base contract establishes the existence of a satisfying assignment. In contrast, UNSAT for a contract conjoined with a forbidden action establishes their incompatibility: it is the expected exclusion of a violation, not necessarily a specification error.

Replaying the stored SMT queries yielded 76 SAT and 24 UNSAT outcomes among 100 boundary queries across four waiting durations, and eight SAT and four UNSAT outcomes among the methodology's 12 illustrative queries. Neither group produced an unexpected result or solver UNKNOWN. The expanded data contain 5,760 candidate-binding checks: 3,840 SAT and 1,920 UNSAT. Removing repeated assignments gives 960 distinct SMT assignments, with 540 SAT and 420 UNSAT. Thus, 1,920 UNSAT checks do not represent 1,920 distinct erroneous specifications. These candidate checks cover training, validation, and test splits and are distinct from violations in model predictions.

Of the 1,920 UNSAT checks including repetitions, 480 bind entry before clearance and 1,440 bind entry after clearance but before the required wait expires. Every candidate outcome agreed with the separate integer environment rule. Each of the 1,440 data rows retained at least one admissible entry candidate, and every reference action was SAT. This distinguishes successful exclusion from a contract that merely blocks all entry. Agreement supports correspondence between the specified contract and environment rule, not visual interpretation or the factual correctness of external evidence.

### 2. Injected Errors and Layer-Specific Outcomes

A separate balanced set of 192 injected-error and valid cases assesses which errors the specification/CNL pathway distinguishes. Table E3 identifies detection layers so that aggregate detection is not attributed to SAT alone. Valid cases are excluded from the error-detection denominator.

**Table E3. Injected errors, outcomes, and checking layers**

| Input type | Cases | Detected / missed | Detection layer or valid outcome |
|---|---|---|---|
| CNL negation change | 24 | 24 / 0 | CNL correspondence |
| CNL threshold change | 24 | 24 / 0 | CNL correspondence |
| Release-condition deletion | 24 | 24 / 0 | Core–environment comparison |
| Comparison reversal | 24 | 24 / 0 | Core–environment comparison |
| Specification threshold change | 24 | 24 / 0 | Source correspondence and Core comparison |
| Unit error | 24 | 24 / 0 | Schema check |
| Shared source/specification error | 24 | 0 / 24 | Trusted source changed together with specification |
| Valid contract | 24 | Not applicable | 24 accepted; 0 false rejections |

Bypassing checks accepts all 192 candidates. Applying the checks accepts 48: 24 valid contracts and 24 shared-source errors. All 144 cases in the six supported error categories are detected; including shared errors gives 144 detections among 168 erroneous cases, or 85.71%. Many incorrect contracts remain internally satisfiable, so satisfiability and source/text correspondence must be distinguished. This bounded injection study does not estimate natural error prevalence or semantic equivalence across unrestricted natural language.

### 3. Interpreting and Handling UNSAT Cases

Table E4 distinguishes intended action exclusion from discrepancies requiring correction. Counts in the injected-error rows refer to queries, not the erroneous contracts counted in Table E3. For example, each of 24 comparison-reversal contracts yields two discrepant boundary queries, giving 48 discrepancies. These are detected deliberate mutations, not unresolved errors remaining in the unmodified data.

**Table E4. SMT outcomes, interpretations, and corresponding handling**

| Query or mutation | Observed result | Interpretation | Handling |
|---|---|---|---|
| Clear at 11.000 s; wait 0.500 s; enter at 11.499 s | UNSAT | Unmodified contract excludes entry 1 ms early | Reject this candidate; do not relax the contract merely to obtain SAT |
| Same contract; enter at 11.500 or 11.501 s | SAT | Entry at and after the boundary is feasible | Retain alongside violation exclusion as evidence of release feasibility |
| Increase the required wait by 100 ms relative to its source | Expected SAT → UNSAT in 24 queries | Admissible behavior is overrestricted | Reconcile the threshold with its source, correct, and recheck |
| Reverse the admission comparison | Expected SAT → UNSAT in 24; expected UNSAT → SAT in 24 | Admission and prohibition boundaries are reversed | Correct the Core lowering/comparison and recheck both sides |
| Delete the release constraint | Expected UNSAT → SAT in 24 queries | Premature entry is incorrectly admitted | Restore the clause and recheck exclusion and release feasibility |

The first case has four conflicting conditions: an entry-gate clause requiring entry no earlier than clearance plus 500 ms, clearance at 11000 ms, entry at 11499 ms, and an assertion that entry occurs. Replaying this representative query with tracked assertions produced an UNSAT core containing all four; deleting any one made the remainder SAT. This is a deletion-minimal conflict set for this example, not a claim that minimum cores were automatically generated for every query. The common runner currently records outcomes and SMT expressions but does not persist UNSAT cores by default.

The handling principle follows the discrepancy. Matching expected and observed UNSAT is retained as evidence of exclusion. Unexpected UNSAT for an expected-SAT query calls for checking whether legitimate behavior has been blocked; UNSAT for the base contract calls for inspecting source bindings, conflicting clauses, and lowering. Unexpected SAT for an expected-UNSAT query calls for investigating a missing or reversed restriction. Solver UNKNOWN supports neither conclusion and is not treated as a pass. A discrepant contract should be withheld from approval/export until the cause is corrected and consistency, violation exclusion, and post-release feasibility are rechecked together. These are handling principles derived from the outcomes, not a claim of implemented automatic repair.

Human review should focus on source selection, the justification for a waiting duration, and target/zone binding when logs cannot settle them. Expected UNSAT alone does not justify repeating existing scene reviews. Conversely, a shared source/specification error can preserve both SAT and boundary agreement; evidence review must therefore remain separate from solver outcomes.

## S4. Action Selection Relative to CoC Alone

**Table E5. Main test performance. Percent, three-seed mean ± standard deviation**

| Condition | Accuracy | Violation | Compliant completion | Pair accuracy |
|---|---|---|---|---|
| P0 | 49.861 ± 0.196 | 19.167 ± 5.803 | 80.833 ± 5.803 | 0.000 ± 0.000 |
| P1 | 96.806 ± 1.712 | 1.389 ± 1.678 | 98.611 ± 1.678 | 93.611 ± 3.425 |
| P2 | 98.056 ± 1.534 | 0.833 ± 0.680 | 99.167 ± 0.680 | 96.111 ± 3.068 |

Relative to P0, accuracy increases by 46.944 percentage points for P1 and 48.194 points for P2. Violation rates decrease by 17.778 and 18.333 points, respectively. Both augmented conditions support selection consistent with explicit rules, and high performance is observed with EBLC-generated CNL. The differences include the benefit of supplying rule information and are not interpreted as causal gains from verification alone.

![Figure 6. Main behavioral metrics by seed](../../../artifacts/projects/guardsynth-coc/public/paper1-method-preservation-001/experiments-section-2026-09-30-002/figures/primary-metrics-en.png)

Figure 6. Panels show accuracy, violation rate, and contract-pair accuracy. Small marker shapes identify seeds, large diamonds show means, and vertical bars show ±1 standard deviation. Higher accuracy and pair accuracy are better; lower violation is better. The violation panel uses a different axis range to make small values readable. Bars do not represent confidence intervals or significance.

P0's zero pair accuracy reflects the construction in which identical inputs require different answers for two contracts; it should not be interpreted as a general absence of reasoning ability. P2 has higher mean performance than P1 but does not dominate every seed. For example, seed 42 has zero P1 violations and 0.833% P2 violations. The main interpretation concerns the benefits of P1 and P2 over P0, not uniform superiority or formal noninferiority between the constraint representations.

We also examine whether avoiding violations merely suppresses progress. None of the three conditions exhibits unnecessary waiting on the test set. Pooling three seeds gives 582, 710, and 714 compliant selections for P0, P1, and P2, with conditional mean progress losses of 7.096, 0.331, and 0.231 score units. There are 138, 10, and 6 violations, with mean shortfalls of 0.960, 0.910, and 0.700 s per violation. Denominators differ across conditions, and these small conditional samples do not establish the magnitude of physical risk reduction.

## S5. Condition Changes and Recorded Action Cases

The paraphrase evaluation supplies constraint wording not used during training. P1 and P2 receive the same held-out formulation in this evaluation, so their difference reflects processing of common wording after different training histories. P0 and LOGIC_GUARD inputs do not change in this set; repeated results are not independent evidence of paraphrase robustness for those conditions.

![Figure 7. Wording and temporal-condition changes](../../../artifacts/projects/guardsynth-coc/public/paper1-method-preservation-001/experiments-section-2026-09-30-002/figures/condition-shifts-en.png)

Figure 7. Accuracy and violation rates under the main test, paraphrase, and unseen-duration conditions. Points are three-seed means and bars are standard deviations. Connecting lines aid comparison rather than denote a continuous temporal trend. The same test images are reused.

Under paraphrasing, P1 accuracy and violation are 90.556% and 5.000%, compared with 96.944% and 1.250% for P2. Under unseen durations, both conditions achieve 96.667% accuracy, with violation rates of 2.222% and 1.528%. Improvements over P0 persist under these supplied-rule variations, but should not be extended to diverse road situations. Reoccupation, occlusion, and UNKNOWN observations are outside the main learning task's evaluation scope.

Figure 8 presents two cases selected from stored test predictions. The selection rule sorts seed-42 records by scene ID and contract level, then takes (a) the first case where P0 violates and P1/P2 both select correctly and (b) the first P2 violation. These are post-hoc explanatory cases, not a sample for estimating prevalence or representativeness.

![Figure 8. Recorded improvement and residual violation](../../../artifacts/projects/guardsynth-coc/public/paper1-method-preservation-001/experiments-section-2026-09-30-002/figures/action-cases-en.png)

Figure 8. Recorded predictions plotted at selected entry times. Red indicates entry forbidden by the contract; green indicates the time condition is met. The boundary is clearance time plus the 1.5-second wait. Marker labels give selected actions and times. This is a timeline of predictions, not an original video frame.

Case (a) clears at 11.0 s and permits entry from 12.5 s. P0 selects candidate C at 11.5 s, while P1 and P2 select the reference candidate D at 12.5 s. Case (b) clears at 11.4 s and permits entry from 12.9 s. P0 and P1 select reference B, but P2 selects A at 12.8 s, entering 0.1 s early. Candidate labels rotate, so D does not always mean waiting. The residual violation illustrates that an exact specified boundary does not guarantee compliance by every learned selection.

## S6. Auxiliary Comparisons and Specification-Based Cost Learning

In the six-condition comparison, SHUFFLED_GUARD attains 50.556% test accuracy and 19.722% violation, similar to P0. This control supports the importance of correct training-time guard/example binding; correctly bound guards are provided at evaluation. NATURAL_GUARD exceeds P2 on some conditions. LOGIC_GUARD attains 99.167% accuracy on the main test but 81.250% on unseen durations. We therefore emphasize constraint information and binding rather than universal superiority of one representation.

An additional experiment starts CE_ONLY and CE_EBLC from the same seed-specific P2 adapter and trains each for 60 updates. Data order, tokens, parameters, and updates are matched; CE_EBLC adds an auxiliary loss using violation and unnecessary-waiting costs to cross-entropy. This is not interaction-based or policy-gradient reinforcement learning. On ten separate synthetic images, canonical violations decrease from 0.556% to zero, while accuracy also decreases from 99.167% to 98.333%. Paraphrasing shows a similar tradeoff, whereas unseen-duration accuracy and violation improve together. Supplement S2 provides the full comparison and tradeoff plot.

## S7. Interpretation and Limitations

The results show that adding explicit constraints to CoC action rationales improves accuracy and compliance in a bounded synthetic selection task, while EBLC connects those constraints to a checkable representation and CNL. Specification quality and behavioral performance are evaluated through distinct evidence; improvements in the former are not asserted to automatically cause the latter.

External validity is limited. The main test contains ten distinct synthetic images and restricted candidate patterns, not continuous real-road trajectories, closed-loop control, or collision outcomes. Real-scene evidence-binding examples and development learning checks are not pooled into these performance results. The findings concern one VLM and a restricted LoRA configuration, not Alpamayo training or real-vehicle safety.

Internal validity requires attention to information availability and template reuse. P1/P2 receive constraints at evaluation while P0 lacks the duration. Consequently, this comparison alone establishes neither rule internalization without supplied constraints nor the degree of causal dependence on visual content. Separate implementations of specification checking and environment references can still share incorrect assumptions. CNL checks are limited to supported grammar and error types and do not automatically certify the original CoC's factual accuracy.

Statistical interpretation is also bounded. Three seeds and conditional intervals over few clusters do not replace large-population inference. Zero observed violations do not imply zero violation probability. Additional measures and case selection are labeled exploratory. Original operational criteria and verdicts remain in the supplement; effect sizes, variability, and residual errors are reported without selecting results according to improvement magnitude.

## Additional Temporal Analyses

### Six Conditions and Complete Numerical Records

Values below are three-seed means (%); A denotes accuracy and V violation rate. The linked CSV retains the validation set, pair/completion metrics, individual seeds, standard deviations, and conditional confidence intervals.

| Condition | Main test A / V | Paraphrase A / V | Unseen duration A / V |
|---|---|---|---|
| P0 | 49.861 / 19.167 | 49.861 / 19.167 | 49.861 / 18.472 |
| P1 | 96.806 / 1.389 | 90.556 / 5.000 | 96.667 / 2.222 |
| P2 | 98.056 / 0.833 | 96.944 / 1.250 | 96.667 / 1.528 |
| NATURAL_GUARD | 98.056 / 1.111 | 93.889 / 0.000 | 98.611 / 0.556 |
| SHUFFLED_GUARD | 50.556 / 19.722 | 51.250 / 19.028 | 50.972 / 18.889 |
| LOGIC_GUARD | 99.167 / 0.139 | 99.167 / 0.139 | 81.250 / 0.833 |

### Additional Cost Learning

The auxiliary objective is $L=L_{CE}+\lambda\sum_a p(a)c(a)$. Probabilities p(a) are normalized over the four candidate tokens; cost sums a weight of 1 for violation and 0.25 for unnecessary waiting. CE_ONLY uses λ=0 and CE_EBLC λ=1. The optimizer is reset, and PRE_ADAPTER denotes the model before additional training. Evaluation uses ten separate images with clearance times of 12.0–12.9 s. The 6,480 predictions include PRE_ADAPTER evaluations.

| Evaluation | Condition | Accuracy | Violation | Pair accuracy |
|---|---|---|---|---|
| Canonical | PRE_ADAPTER | 99.028 | 0.417 | 98.056 |
| Canonical | CE_ONLY | 99.167 | 0.556 | 98.333 |
| Canonical | CE_EBLC | 98.333 | 0.000 | 96.667 |
| Paraphrase | PRE_ADAPTER | 95.972 | 1.944 | 91.944 |
| Paraphrase | CE_ONLY | 97.639 | 1.806 | 95.278 |
| Paraphrase | CE_EBLC | 96.250 | 0.139 | 92.500 |
| Unseen duration | PRE_ADAPTER | 96.944 | 1.528 | 93.889 |
| Unseen duration | CE_ONLY | 98.611 | 1.250 | 97.222 |
| Unseen duration | CE_EBLC | 98.889 | 0.139 | 97.778 |

![Figure S1. Additional cost-learning tradeoff](../../../artifacts/projects/guardsynth-coc/public/paper1-method-preservation-001/experiments-section-2026-09-30-002/figures/cost-tradeoff-en.png)

Figure S1. Arrows connect CE_ONLY to CE_EBLC within each evaluation condition. Lower violation on the horizontal axis and higher accuracy on the vertical axis are preferable. Points are three-seed means; connections compare two training conditions rather than show optimization trajectories. Both axes are zoomed to display small differences.

### Processing Time and Reporting Criteria

CPU timings use 48 distinct bindings repeated three times per pathway. The construction/parsing/compilation/solve pathway has a mean of 3.462 ms, median of 3.524 ms, and p95 of 3.782 ms. Solving with reused compilation gives 2.322, 2.368, and 2.621 ms, respectively. These local timings exclude initialization, images, model inference, and I/O; they are not end-to-end data-production throughput or a vehicle real-time guarantee.

The original expansion protocol required P2 to reduce violations and increase compliant completion relative to P0 by at least 20 percentage points in every seed; its operational verdict was NOT_SUPPORTED. The cost experiment required a two-point canonical violation reduction, but CE_ONLY's baseline was already 0.556%, yielding the original INCONCLUSIVE verdict. Neither criterion nor verdict has been changed. After viewing results, the manuscript was organized to report effects of every magnitude and emphasize both constraint variants relative to P0 and specification checkability. This reporting focus is distinct from declaring success under the original criteria.

## Reproducibility Evidence

The following links identify source settings and numerical records for manuscript review and will connect to code/data availability in the integrated manuscript. Historical runs are not overwritten.

- [Frozen expanded-experiment protocol](../../../artifacts/projects/guardsynth-coc/public/paper1-method-preservation-001/temporal-expansion-protocol-2026-09-29-001/protocol.json)
- [All primary metrics and individual seeds](../../../artifacts/projects/guardsynth-coc/public/paper1-method-preservation-001/temporal-experiment-closure-2026-09-29-001/all_primary_metrics.csv)
- [Injected-error D4 records](../../../artifacts/projects/guardsynth-coc/public/paper1-temporal-diversity-001/diversity-analysis-2026-09-29-001/RESULT.json)
- [Additional behavioral metrics and timings](../../../artifacts/projects/guardsynth-coc/public/paper1-method-preservation-001/temporal-secondary-metrics-2026-09-29-001/RESULT.json)
- [Figure 8 selection rule and recorded predictions](../../../artifacts/projects/guardsynth-coc/public/paper1-method-preservation-001/experiments-section-2026-09-30-002/selected_cases.json)

- [SMT replay and UNSAT case audit](../../../artifacts/projects/guardsynth-coc/public/paper1-method-preservation-001/experiments-section-2026-09-30-002/unsat_review.json)


## S8. Additional Static and Maneuver Experiments

The additional experiments comprise P0, P1, P2, and shuffled associations over three optimization seeds: 24 fits, 2,160 optimizer updates, and 9,792 predictions. Candidate-binding checks comprise 5,088 queries: 3,432 SAT and 1,656 UNSAT. Static checks contribute 2,016 queries (1,512 SAT/504 UNSAT), and maneuver checks 3,072 (1,920 SAT/1,152 UNSAT). SMT and independently implemented task rules agree on all 9,792 model predictions. Candidate bindings and predictions are distinct counting units.

All fits start from the same Qwen3-VL-2B-Instruct base. LoRA rank/alpha/dropout are 8/16/0.05, AdamW learning rate is 0.0002 with weight decay 0.01, batch size 2 with accumulation 8, and training lasts three epochs. Final checkpoints follow 108 static or 72 maneuver updates per arm and seed. Data seed 20260930 is fixed; optimization seeds are 42, 17, and 123.

Static training has 576 rows, 96 scene IDs, and 18 distinct images; primary evaluation has 144 rows, 24 scene IDs, and 13 images. All 13 primary-test images occur in training; eight unseen-value images do not. Maneuver training has 384 rows/192 IDs and each evaluation 96 rows/48 IDs, using two repeated schematic images. Candidate measurements also appear in text. IDs and predictions are not independent videos.

Cells below report accuracy / violation / compliant completion / pair accuracy (%, three-seed means). Shuffling permutes P2 CNL within subtype during training only. Valid output and goal completion are 100%, and deadlock is 0%, in these conditions. Differences between accuracy and compliant completion reflect admissible but lower-progress selections.

### Static constraints

| Arm | Primary | Paraphrase | Unseen values |
|---|---|---|---|
| P0 | 50.00 / 24.31 / 75.69 / 0.00 | 50.00 / 24.31 / 75.69 / 0.00 | 50.00 / 22.92 / 77.08 / 0.00 |
| P1 | 100.00 / 0.00 / 100.00 / 100.00 | 93.29 / 0.00 / 100.00 / 86.57 | 99.54 / 0.00 / 100.00 / 99.07 |
| P2 | 100.00 / 0.00 / 100.00 / 100.00 | 80.32 / 7.87 / 92.13 / 60.65 | 97.22 / 0.23 / 99.77 / 94.44 |
| Shuffled | 50.69 / 23.84 / 76.16 / 3.70 | 50.23 / 24.77 / 75.23 / 0.46 | 49.31 / 25.00 / 75.00 / 3.70 |

### Stopping and lane changing

| Arm | Primary | Paraphrase | Unseen values |
|---|---|---|---|
| P0 | 50.00 / 30.90 / 69.10 / 0.00 | 50.00 / 30.90 / 69.10 / 0.00 | 50.00 / 30.90 / 69.10 / 0.00 |
| P1 | 100.00 / 0.00 / 100.00 / 100.00 | 100.00 / 0.00 / 100.00 / 100.00 | 100.00 / 0.00 / 100.00 / 100.00 |
| P2 | 98.96 / 0.00 / 100.00 / 97.92 | 97.92 / 2.08 / 97.92 / 95.83 | 98.96 / 0.00 / 100.00 / 97.92 |
| Shuffled | 49.65 / 30.56 / 69.44 / 2.08 | 52.43 / 26.74 / 73.26 / 5.56 | 49.65 / 30.90 / 69.10 / 2.78 |

### Combined hard maneuver conditions

| Arm | Accuracy / violation | Compliant completion / pair accuracy |
|---|---|---|
| P0 | 50.00 / 30.21 | 69.79 / 0.00 |
| P1 | 94.10 / 0.69 | 99.31 / 88.19 |
| P2 | 91.32 / 1.04 | 98.96 / 82.64 |
| Shuffled | 51.04 / 32.29 | 67.71 / 2.08 |

Paraphrasing changes wording for the same evaluation cases rather than introducing independent scenes. Hard conditions combine negation, clause order, equality boundaries, and m/cm units; they do not isolate individual causal effects. The source analysis retains 2,000 paired bootstrap replicates over numeric-configuration clusters and seeds.

## S9. Follow-Up Diagnostics of Existing Temporal Models

Nine existing P0/P1/P2 adapters produce 2,160 exploratory predictions without new training. Cells report accuracy / violation (%), converted from the source report's four-decimal rates. These distributions differ from the primary test and are not pooled with it.

| Diagnostic | P0 | P1 | P2 |
|---|---|---|---|
| D1/boundary | 50.00 / 33.33 | 95.83 / 4.17 | 95.83 / 2.78 |
| D1/clear_only | 50.00 / 22.22 | 100.00 / 0.00 | 98.61 / 1.39 |
| D1/duration_only | 50.00 / 20.83 | 98.61 / 1.39 | 97.22 / 2.78 |
| D1/joint | 50.00 / 22.22 | 100.00 / 0.00 | 98.61 / 1.39 |
| D2/canonical | 50.00 / 20.83 | 100.00 / 0.00 | 95.83 / 2.78 |
| D2/paraphrase1 | 50.00 / 20.83 | 98.61 / 0.00 | 97.22 / 2.78 |
| D2/paraphrase2 | 50.00 / 20.83 | 76.39 / 15.28 | 77.78 / 9.72 |
| D3/blank | 50.00 / 13.89 | 81.94 / 2.78 | 76.39 / 1.39 |
| D3/original | 50.00 / 22.22 | 100.00 / 0.00 | 98.61 / 1.39 |
| D3/swapped | 50.00 / 19.44 | 87.50 / 0.00 | 79.17 / 1.39 |

D1 changes boundaries, clearance instants, waits, or their combination; D2 changes wording; D3 uses original, blank, or swapped images. Swapping alters the visual premise, so its scores are not ordinary-input accuracy. P2 changes its choice on 25.00% of blank-image and 19.44% of swapped-image cases. Each diagnostic bundle contains only three semantic parameter groups. D4 reuses the existing 192 error-injection cases in S3 and is not counted again as new evidence.

## S10. Relationship to the Preceding Study and Reproducibility

We reevaluate the preceding study's three static types, temporal waiting, stopping, lane changing, contract pairs, shuffled associations, unseen values, and wording changes. Data, budgets, seed construction, and numeric-text precision differ, so this is task-family replication, not exact replication of earlier scores. Alpamayo preliminary diagnostics, separate closed-loop control, and maneuver image interventions were not rerun here.

This evidence bundle includes 18 temporal fits, six auxiliary-cost fits, and 24 additional static/maneuver fits. Reused data, validation rows, input interventions, and existing-adapter evaluations are not added as independent scenes. Frozen results and operational criteria remain unchanged. Main-versus-supplement placement was selected after result inspection according to relevance to the research questions.

- [Additional experiment metrics](../../../artifacts/projects/guardsynth-coc/public/paper1-method-preservation-001/experiments-section-2026-09-30-003/multitask_metrics.csv)
- [Additional experiment analysis](/home/jinhyun/prj_ws/prj_jin/guardsynth-cc-worktrees/guardsynth-additional-20260930/artifacts/projects/guardsynth-coc/public/paper1-method-preservation-001/multitask-contract-analysis-2026-09-30-001/REPORT_KO.md)
- [Diagnostic records](../../../artifacts/projects/guardsynth-coc/public/paper1-temporal-diversity-001/expanded-diagnostics-analysis-2026-09-30-001/RESULT.json)
