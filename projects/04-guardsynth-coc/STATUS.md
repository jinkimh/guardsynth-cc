# Status

- Reporting amendment (user request after inspecting outcomes, 2026-09-29): report all planned
  arms/seeds/suites, including small gains, no gains, regressions and uncertainty. The per-seed20pp
  threshold is not a publication/progress gate. Preserve frozen criteria and original verdicts;
  do not relabel NOT_SUPPORTED as success. See
  [reporting policy](docs/decisions/PAPER1_METHOD_PRESERVATION_AND_LABELING_DECISION_V01.md).
  Full manuscript/result-table integration remains to be done; this amendment does not change training.

- State: `M18_CONTROLLED_EXPERIMENTS_CLOSED_M20_INTEGRATION_PENDING`
- Current closure (2026-09-29): [full experiment audit and tables](../../artifacts/projects/guardsynth-coc/public/paper1-method-preservation-001/temporal-experiment-closure-2026-09-29-001/REPORT_KO.md).
  Expanded18/18 fits:3,240 updates and17,280 predictions. Cost6/6 additional fits:360 updates,
  6,480 predictions including three pre-adapter baselines. Secondary metrics are complete.
  All seed metrics recomputed, paired budgets and checkpoint changes checked,296 unique source-file
  hashes verified;49 temporal/secondary regression tests pass. No new training or model calls in closure.
  Preserve expanded NOT_SUPPORTED and cost INCONCLUSIVE frozen verdicts; execution completion is not
  hypothesis confirmation. Cost reduced violations but lowered optimal-action accuracy in two suites.
  Next: integrate all results, uncertainty and failures into M20 manuscript/supplement. Prior real-road
  M16/formal60 gaps remain separate; Studio is not an experiment-closure gate.

## Historical registration and execution notes

The queued/running counts below are dated execution history, superseded by the closure above.

- User-approved next experiment: [EBLC cost learning](docs/designs/PAPER1_EBLC_COST_LEARNING_DESIGN_V01.md).
  Preserve current18 fits; afterward compare same-seed P2 continuation with CE-only versus
  CE+expected EBLC violation/deadlock cost,60 updates each ×3 seeds. This is supervised cost
  regularization, NOT RL. `temporal-cost-protocol-2026-09-29-001` is now frozen:10 new images,
  three240-row suites;6 new fits/360 updates and6,480 predictions including pre-adapter baselines planned.
  Cost/queue tests16 pass, actual action-token alignment/gradient direction/zero-coefficient equivalence
  and real checkpoint-delta checks included. Performance regression overrides no-headroom classification.
  tmux `guardsynth-temporal-cost-20260929` is active, waiting for all upstream18 fits COMPLETE;
  queue state: `temporal-cost-queue-2026-09-29-001/RESULT.json`. Actual cost training updates0 at registration.
  No repeated approval/survey is needed; do not confuse queued cost training with completion.
- Additional training/evaluation authorized: frozen `temporal-expansion-protocol-2026-09-29-001`.
  Preserve all five prior conditions and add EBLC/CNL:6 arms ×3 seeds,180 updates/fit,
  18 planned checkpoints; validation/test/paraphrase/unseen-duration each240 predictions/fit
  (17,280 planned total). Prior7 metrics plus coverage, per-seed SD and paired clear-time cluster CI.
  Fixed final checkpoint, no validation/test tuning; executable EBLC action tests cross-check the
  independent environment scorer. Better performance is not assumed; negative results are retained.
- Execution: tmux `guardsynth-temporal-expansion-20260929` runs a durable resource queue.
  `temporal-expansion-queue-2026-09-29-001/RESULT.json` records live queue state. The first GPU2
  launch was refused before run/model allocation because an unrelated project took that GPU.
  Queue checks GPU2/4 every30seconds and starts `temporal-expansion-learning-2026-09-29-001`
  automatically when idle. GPU4 became idle after prior-adapter diversity evaluation and the queue
  launched the expanded run there. Supervision confirmed P0/seed42 completed180 updates and all
  four evaluation splits (960 predictions):1/18 fits complete at this check. No completion is inferred
  for remaining fits. `temporal-expansion-learning-2026-09-29-001/RESULT.json` and `progress.json`
  are live authority. No existing workload was interrupted; no duplicate training was launched.
- Additional training data: `temporal-training-data-2026-09-29-001` is DATA_READY_NOT_TRAINED.
  Paired rows train960 / validation240 / test240, each exported for P0/P1/P2 (4,320 arm rows).
  Actual unique synthetic images40/10/10; these are numeric/candidate variants, not1,440 road scenes.
  Prior and cross-split pixel overlap0. All5,760 candidate bindings agree between executable
  EBLC/Core/Z3 and independent environment rules (960 distinct SMT assignments); no new weight updates.
  All5 input/76 output hashes, all paired loaders/targets and actual visual processor/loss masks for
  all3 arms pass. New5 tests plus9 primary regression tests pass; naming retains the known5 issues.
  Code: `experiments/paper1_cnl_learning/temporal_training_data.py`; the new frozen six-arm protocol
  consumes this dataset, not old primary seed-generated training rows.
- User clarification: verification targets the quality of constraints inserted into CoC, not an
  additional causal VLM performance gain. Evaluate constraint-error detection separately from
  learning-effect preservation; do not certify whole-CoC factual correctness from SAT.
- User-requested next work: [diversity follow-up](docs/designs/PAPER1_TEMPORAL_DIVERSITY_DESIGN_V01.md).
  D1–D4 COMPLETE in `paper1-temporal-diversity-001/diversity-{protocol,inference,analysis}-2026-09-29-001`.
  Nine frozen adapters,2,160 scored rows/1,476 unique-input model calls, zero retraining.
  New profile v0.2 leaves primary v0.1 unchanged; expansion-dataset pixel overlap0.
  D1 P2 safe completion: new clear .8194, duration1.0000,
  joint .7222, boundary .8472. New-time robustness is limited despite prior standard success.
  D2 second paraphrase P2 safe completion .9583/accuracy .7917. D3 blank/swap changes P2 choices
  .2639/.3056; swapped-image-implied accuracy .0972/violation .8750. Image sensitivity is not reliable grounding.
  Executable Core tests:2,160 model-selected source bindings (462 UNSAT,1,698 SAT) plus216 image-implied
  bindings; independent environment disagreements0. SAT holding is not route completion.
  D4 same192 candidates:144 supported errors detected,24 valid accepted/false rejections0,
  24 shared-source-error controls missed. Layer checks support constraint quality, not whole-CoC truth.
  Paired seed/semantic-group CIs and all negative results retained; only3 groups per diagnostic stratum.
  New6-page manuscript snapshot `temporal-paper-2026-09-29-002` preserves the prior snapshot001.
  Verification:24 temporal tests pass (including expansion/data regressions); all36 diversity output
  hashes and frozen input hashes pass. Primary completed outputs and new training dataset remain intact.
  New paper compiles without warnings; diff passes and naming retains only the known5 unrelated issues.
- Current user-approved scope: [v2.4 method-preservation decision](docs/decisions/PAPER1_METHOD_PRESERVATION_AND_LABELING_DECISION_V01.md).
  The controlled P0/P1/P2 comparison is complete; real-road/no-guard-at-test/four-arm extensions
  and historical strict gates below remain separate. No new human decision blocks this completed run.
- `temporal-protocol-2026-09-29-001`: frozen criteria/seeds/budget before new outcomes;2,016 paired
  records,100 Core/SMT boundary queries. P2 renderer consumes supplied source durations, never action
  answers. P0/P1 reuse prior task inputs as replication controls; P1/P2 prompt strings are distinct.
- `temporal-learning-2026-09-29-001`: COMPLETE,3 paired seeds ×3 arms ×72 updates =648 updates;
  nine distinct adapters,224 tensors/adapter including112 nonzero LoRA B matrices;2,592 valid predictions.
- `temporal-analysis-2026-09-29-001`: all per-seed frozen point criteria pass on both standard splits.
  Benchmark violation/safe completion P0 .3194/.6806, P1 .0000/1.0000, P2 .0000/1.0000.
  New-seed P0 .3160/.6840; P1/P2 .0000/1.0000. P2-P0 violation difference -.3160,
  template-cluster95%CI[-.4348,-.1832]; P2-P1 difference0. No formal noninferiority claim.
  Unseen-time safe completion P0/P1/P2 .6250/.6389/1.0000; accuracy .5000/.6250/.8993.
  Deadlock0 and coverage1 throughout. Prior Project01 unseen .625/.649 remains separately attributed.
- Exact boundary: only6 distinct storyboard images and24 P0 image/candidate inputs. New seeds reuse
  templates, not fresh visual environments. This supports controlled effect preservation, not
  automatic road grounding, verification-only causal benefit, or training-only causal attribution.
- M20: `paper/main.tex` now contains actual results, figure, criteria and limitations;4-page PDF at
  `temporal-paper-2026-09-29-001/main.pdf`. Venue/citation/manuscript refinement remains; not submitted.
- Verification:43 focused/regression tests pass,100 SMT queries pass, paper compiles without layout
  or unresolved-reference warnings. Naming retains only5 pre-existing unrelated violations; diff check passes.
- All100 output hashes across the four new protocol/learning/analysis/paper runs and their input
  hashes verified. Training process exited; GPU4 returned to0MiB/0% after completion.
- Next task: refine the result-linked method manuscript and its citations under v2.4; no repeated
  survey, smoke or large real-road cohort is a prerequisite. Original road answers/held cases remain intact.
- Earlier road-development execution history follows; its pending flags do not reopen the approved primary scope.
- Approval follow-through verification:34 tests pass,38 processor/mask rows pass,43 output hashes
  across6 new/prior runs verified. Diff check passes; naming retains the known5 unrelated violations.
- User approval received: exact reply "네" to the two STOP common-consequence CNL meanings and
  their limited development-supervision use. See [decision](docs/decisions/PAPER1_STOP_COMMON_CONSEQUENCE_ADMISSION_DECISION_V01.md).
  `stop-common-consequence-acceptance-2026-09-29-001` records one USER_CONVERSATION reply,
  two version/source/text-hash-bound receipts and two scoped policies. No new Jonh attestation,
  authenticated identity, full-document viewing log or utterance timestamp is fabricated.
- `m18-cohort-feasibility-2026-09-29-006`: mechanical2 / actual scoped CNL acceptance2 /
  policy2 / development training eligible2 (#7/#68 only), main-test eligible0. The earlier pending
  question is resolved; no repeat approval needed. Projection version name and legacy v0.1 remain unchanged.
- `speed-development-packaging-2026-09-29-003`:38 paired staging rows retain the full denominator;
  admitted train export is L0=2/L3=2 rows (4 total), original split/CoC/ACTION/masks preserved.
  `train_speed_development.py` implements the existing proposed72 updates/arm/seed, three paired seeds,
  same two admitted scenes and frozen blind five-scene evaluation. This is exploratory development,
  not main-study completion. Actual launch refused before model allocation because GPU4 was occupied
  (1,093MiB,1% at the attempt); other GPUs also had allocations. New weight updates/checkpoints0.
  Next step is resource-safe launch using the command in the execution tracker, not a new CNL approval.
- Earlier continuation history follows; its zero-receipt/admission statements describe the pre-approval runs.
- Final verification for this continuation:31 focused/regression tests pass,54 proposal SMT queries
  pass,38 processor/mask checks pass,79 immutable output hashes across10 runs verified (including
  original intake/STOP acceptance/scene18 smoke). Diff check passes; naming reports only the known5
  unrelated baseline violations. All inference/provider processes exited; no GPU workloads touched.
- Completed result: `pretrained-speed-evaluation-2026-09-29-001` scores19/19 valid base-Qwen
  predictions on133 frames/17 exposed development clips. All-development reference rates:
  inappropriate10/16 (95% clip CI .400–.857), normal-progress2/8 (.000–.667),
  unnecessary-stop7/12 (.286–.900). Three selected references are masked/undetermined, not relabelled.
  Original evaluation partition5: inappropriate2/4, progress1/3, unnecessary-stop2/3; all CIs[0,1].
  This is PRETRAINED DEVELOPMENT BASELINE, zero updates, not trained L0/fresh main test/improvement.
  Safety violation and physical goal completion remain NOT_EVALUATED; appropriateness is not safety gold.
- Current bounded execution (2026-09-29): evidence-driven admission separates mechanical checks,
  actual human CNL receipt and research-policy scope; no candidate-index rejection table remains.
  `m18-cohort-feasibility-2026-09-29-005`: mechanical2, human receipt0, speed-policy scope0,
  training eligible0. Positive synthetic receipts and negative source/text/version/scope drift are tested;
  fixtures confer no real approval. #7/#68 both occupy the ORIGINAL train partition.
- `stop-common-consequence-2026-09-29-001` under readiness: separately versioned proposal,
  two source-linked Korean CNL documents and54 SMT checks. MOVING/STATIONARY share only
  START_OR_ACCELERATE exclusion. Observed motion remains UNKNOWN; v0.1 semantics unchanged.
  Concrete human question concerns these exact texts and their limited development use, not repeated
  ACTION/STOP observations or blanket data approval. No main admission or positive safety claim.
- `speed-development-packaging-2026-09-29-002`: L0/L3 staging19 rows/arm,38 actual processor
  checks pass, original CoCs and three masked fields/arm preserved. Source-bound CNL available2;
  staging is not training admission.002 uses the exact common-consequence CNL hashes from005;
  001 preserves the previous v0.1 conditional texts. Original17clip split retained (14 train/5 evaluation rows).
  Five development evaluation rows have existing ACTION references; main-test eligibility is separate.
- `pretrained-speed-development-2026-09-29-002`: fixed blind prompt,133 causal frames, resize640,
  greedy base Qwen without adapters; CPU4 threads after all GPUs were occupied.19 predictions complete,
  no weights updated; model inference1763.91seconds. Run001 is an unexecuted prepared protocol superseded before any predictions
  by002 to add the resource-safe CPU execution path. No prompt/sampling tuning from outputs.
- `speed-source-providers-2026-09-29-001`: actual local Qwen L1 direct-NL and L2 independent
  structured-candidate generation complete for19 scenes/38 requests; no ACTION targets/reasons/CoC
  in provider inputs. L2 syntax/provenance checks and common rendering do not certify semantics.
  L1 outputs11/abstentions8; L2 parse-valid1/invalid18 (identifier17/kind1). These source-only
  prototypes do not satisfy the main same-CoC/image context requirement.
  `matched-speed-providers-2026-09-29-001` supplies unchanged CoC+same seven frames+source for
  #7/#68:4 outputs complete, L1 text1/abstention1, L2 malformed2; full19 denominator retained.
  Provider format failures are a machine/model-output gap, distinct from missing source observations
  and actual human fidelity/scope decisions. Raw outputs are not repaired or admitted.
- Current 48-hour priority (manuscript included): first two hours determine performance-cohort
  viability; stop optional source/platform expansion and repeated smoke. Current eligible counts:
  reviewed entry development1 (scene18/candidate26), speed training0/19, independent main evaluation0.
  Batched human decisions pending: #7/#68 scoped speed conditional admission and CNL fidelity.
  Entry-only admission is not silently extended. Two STOP cases alone lack normal-progress coverage.
- `real-development-smoke-2026-09-29-001` under `guardsynth-eblc-learning-001` completes actual
  Qwen3-VL-2B real-image L0/L3 updates1/arm, total2, on rechecked idle physical GPU4.
  Both adapters/logs saved; paired initialization, 3,211,264 trainable parameters,224 changed tensors/arm.
  Image tokens2040, assistant-only target tokens31/142, no truncation. This one-scene entry-task
  launch is not speed learning, efficacy or the 48-hour deliverable. No further smoke repetitions.
- `real-development-preflight-2026-09-29-001`: existing accepted export2 arm rows/1 scene verified.
  `m18-cohort-feasibility-2026-09-29-001`: admission/source/provider audit and independent ACTION
  scorer with coverage/per-scene outputs/clip uncertainty. Hash-only17clip development partition12/5
  locked before model predictions; eligible speed rows0 means performance execution remains blocked.
  Fresh reasoning leads1659 are unlabelled, not main-test eligibility. Local motion time convention
  resolves to clip-relative microseconds; unit/error/zero-speed semantics remain unsupported.
- Prior Project01 actual Qwen LoRA results/adapters15 (5conditions×3seeds,72updates each) audited.
  Historical RUN_MANIFEST files are absent; primary result.json/adapter evidence is preserved.
  Prior inference-visible supplied guards are not current Project04 L3/no-gold-at-test evidence.
  Main four-arm gate, L1/L2 qualified-output coverage, violation AND normal-progress requirements remain.
  Verification: new development-path tests5 pass; preflight24/smoke31/cohort91 manifest hashes pass,
  diff check passes, naming retains only the known5 violations. GPU4 returned to0MiB after exit.
  ACTION-only diagnostics identify8 normal-progress-reference rows and12 stop-inappropriate rows;
  their source/CNL admission is still missing, not their ACTION responses. Always-stop scores are
  software diagnostics, not VLM or safety-violation results.
  Current source findings follow below; M16/M17 PARTIAL, M18 development launch PARTIAL/main effect
  NOT_EVALUATED. Next is viable matched L0/L3 cohort, then L1/L2 attribution; no oracle-at-test switch.
- Current STOP source acceptance (2026-09-29): `stop-control-source-acceptance-2026-09-29-001`
  records the user's exact #7/#68 statements as USER_CONVERSATION; exact utterance time is null,
  not a new authenticated Jonh attestation. See [source decision](docs/decisions/PAPER1_STOP_CONTROL_SOURCE_CONFIRMATION_DECISION_V01.md).
  The two worker STOP-paddle instructions to ego are accepted scoped development premises:
  applicability TRUE / evidence_valid true; motion remains UNKNOWN. Scene-local control targets
  do not certify CASCADE physical identity. #68 red-light claim is separate and unconfirmed.
  Actual Core2 / 24 SMT queries and hypothetical motion Core4 / 48 queries pass; scene CNL2 with
  field/source/hash mapping generated. New3 + existing source8 regression tests pass.
  All current action verdicts remain UNRESOLVED under the unchanged UNKNOWN-motion semantics.
  Other17 rows, original ACTION19/3 masks and immutable runs are unchanged. No repeat STOP question.
  Remaining: motion units/clock/error/zero-speed interpretation, optional CASCADE physical identity,
  independent CNL fidelity, other-scene source gaps, original disagreements and split/power.
  Single-reviewer ACTION count remains MET; M16/M17 PARTIAL, no new survey/UI or main training.
- Current source execution (2026-09-29): `speed-source-binding-2026-09-29-001` binds 19 scenes /
  17 clips from existing source observations, raw CASCADE and raw egomotion; ACTION answers/reasons
  are not generation inputs. Eleven reported target anchors link to original image hashes;
  ten scenes have active CASCADE controls and all nineteen have a past raw velocity sample
  (1,086–9,802us before the event). Same-clip events retain distinct timestamps/sample selections.
  Thirteen Core models pin reported source predicates separately from speed applicability;
  130 source-binding SMT checks pass. New regression tests 8 + existing speed execution tests 3 pass;
  intake hashes 82 and source-run hashes 89 verified. Naming retains only the five known violations.
  This closes mechanical source association, not physical target identity, event motion certification
  or a source-to-speed normative rule. Exact field/ref/failure reasons are in the run JSON/report.
  Its pending #7/#68 source question is resolved by the subsequent acceptance above;
  #68 STOP paddle remains separate from the original red-light claim. Other source/motion,
  CNL fidelity, disagreements, split/power and main-training gates remain unresolved.
- Current ACTION reviewer policy: [single-reviewer decision](docs/decisions/PAPER1_SINGLE_REVIEWER_ACTION_DECISION_V01.md)
  accepts Jonh's existing 19 responses as scoped Paper-1 ACTION references. Reviewer-count requirement
  is MET; no second reviewer/repeat ACTION/adjudication is required for this scope.
  Inter-rater reliability: `NOT_MEASURED_SINGLE_REVIEWER`; no consensus-gold claim.
  `speed-source-binding-policy-update-2026-09-29-001` records this subsequent policy without rewriting
  the source run or original answers. Historical strict60/phase2/source-guard protocols remain separate.
  Held #79/#81, 32-candidate denominator, 81 exposed-clip exclusions and all three masks remain.
  M16/M17 PARTIAL; no new UI/survey/training/export/commit/push.
- Completed ACTION intake (2026-09-29): `speed-action-intake-2026-09-29-001` accepts all 19 real
  Jonh development responses / 76 judgments / 19 reasons, preserving both uploads byte-for-byte.
  Machine-readable evaluation inputs and targets: 19 rows each, 17 clip groups, 133 causal images.
  Three scope-limited fields are masked without relabelling (#68 stop-intent deceleration, #86/#94
  low-speed start); 73 unmasked fields include 72 definite and one undetermined judgment.
  These are single-reviewer development references, not 72 training scenes or formal gold.
  Conditional CNL replay/mapping passes for 13 reviewed scenes; 130 UNKNOWN-premise SMT checks pass.
  Six scenes have no speed contract. Two repeated CNL semantic templates are indexed, not reviewed.
  Source action disagreement candidates #52/#55/#60 remain in the denominator with original CoC intact.
  ACTION collection/intake is COMPLETE; no repeat ACTION or new questionnaire is requested.
  Next machine task is source-grounded speed applicability binding, without using ACTION answers
  to generate constraints. Current conditional contracts still lack scene premises/target binding.
  Subsequent single-reviewer ACTION policy above satisfies reviewer count; source/CNL acceptance and
  main training remain incomplete. Historical two-reviewer statements below describe prior scope.
- Submission follow-up (2026-09-29): final/draft JSON files are present with matching 19-scene answers;
  read-only checks found 76 valid action judgments, 19 reasons and matching assignment/packet identity.
  `speed-action-clarification-2026-09-29-001` records user-conversation clarification: #68 means braking
  toward a full stop, #86/#94 mean low-speed starting, not unrestricted acceleration while moving.
  Raw choices are unchanged; no normalized labels/gold or motion-state facts are inferred.
  This clarification is not a new authenticated reviewer attestation. Formal intake/semantic mapping
  remain pending; earlier zero-response counts below describe publication-time state.
- Current UI-only update (2026-09-29): `speed-action-ui-2026-09-29-001` adds per-scene draft save,
  completion/next buttons and current-scene status. Missing judgments/reason block completion;
  browser storage failure blocks completion/advance with a JSON-backup message.
  Served at the same reviewer URL via `portal-2026-09-29-002`. Original assignment ID, packet hash,
  localStorage key, answer schema and completion criteria are unchanged; existing drafts remain compatible.
  Two Chromium workflows (file and live HTTP) pass scene completion, incomplete blocking,
  final-scene guidance, zoom, reload and JSON restore/export in disposable test contexts.
  Assignment/UI tests 2 and portal regression tests 5 pass; naming retains only five known violations.
  No question/choice changes, reassignment or reviewer responses created. Final JSON still requires delivery.
- Current assignment/publication (2026-09-29): explicit user "네.." approves the exact 19 scenes
  for Jonh and publication after browser checks. `speed-action-assigned-2026-09-29-001` records
  actual assignment 19 / action slots 76, reusing the accepted self-report and development criteria.
  #79/#81 remain held. Published via port8766, portal run `portal-2026-09-29-001`.
  Reviewer-only URL: `http://127.0.0.1:8766/reviews/paper1_speed_action_jonh.html`.
  Coordinator list: `http://127.0.0.1:8766/reviews.html`; do not give it to Jonh before ACTION completion.
  No CoC/answers/polygons/machine verdicts/CNL or links to them appear in the direct ACTION page.
  Real Chromium checks use disposable profiles and test-only downloads outside the submission folder.
  Responses/gold/training remain 0; final JSON download is not server receipt.
  Submission folder: `artifacts/projects/guardsynth-coc/restricted/guardsynth-paper1-training-readiness-001/speed-action-submission-2026-09-29-001/`.
  All 19 ACTION precede any CNL/source exposure; one-reviewer development review does not satisfy the two-reviewer formal gate.
  Existing suspended URLs and immutable runs remain unchanged. M16/M17 PARTIAL; no main freeze.
  Publication receipt/screenshots: `speed-action-publication-2026-09-29-001` (two real Chromium workflows passed).
- Current reviewer preparation (2026-09-29): `speed-action-assignment-preparation-2026-09-29-001`
  accepts Jonh's own no-exposure answer relayed by the user: "아니요", then "네" confirming
  that the user is conveying Jonh's answer. This is a conversational reviewer self-report;
  exact declaration time remains null, with no identity/signature/webform/access-log authentication.
  Do not repeat that question or the two accepted development decisions.
  Proposed assignment: Jonh, 19 development ACTION scenes / 76 action judgments; #79/#81 held.
  Prepared a separate blind preview with causal frames, empty responses, local draft save/restore.
  Preview is not dispatched or registered in the portal; draft saves are not accepted submissions.
  Its exact 19-scene assignment/publication proposal is now approved and executed above.
  ACTION for all assigned scenes precedes CNL/source exposure. One reviewer does not meet the formal two-reviewer gate.
  Actual assignment count unset, dispatch/responses/gold/training 0; M16/M17 PARTIAL.
  See [preparation report](../../artifacts/projects/guardsynth-coc/restricted/guardsynth-paper1-training-readiness-001/speed-action-assignment-preparation-2026-09-29-001/REPORT_KO.md).
- Current approval and execution (2026-09-28): both development semantics and blinded common
  input accepted by the user's explicit follow-up; see [approval record](docs/decisions/PAPER1_SPEED_DEVELOPMENT_APPROVAL_DECISION_V01.md).
  `speed-contract-execution-2026-09-28-001` produces 15 conditional speed contracts/CNL documents.
  Shared Core/SMT: 626 synthetic queries, 6 mutation queries, 150 scene-UNKNOWN queries match expected.
  Final validation: 35 tests pass, 139 manifest hashes verified; naming has only the five known baseline violations.
  This validates the accepted development semantics, not scene applicability, action gold or CNL human fidelity.
  All 21 original CoCs/observations remain; #79/#81 are held pending context confirmation.
  Prepares 19 unassigned blind inputs / 133 causal JPEGs, with no CoC/answers/polygons/machine verdicts.
  No portal registration, assignment or dispatch; empty declaration/response templates are not responses.
  Its declaration prerequisite is now recorded above; actual assignment/dispatch approval remains pending.
  Do not re-request the two accepted decisions. Independent speed gold 0/21, CNL reviews 0,
  training 0; main endpoint/cohort/gold/split NOT_FROZEN; M16/M17 PARTIAL, two-reviewer gate unchanged.
  Current [execution design](docs/designs/PAPER1_SPEED_CLAUSE_BINDING_DESIGN_V02.md); V01 and prior runs preserved.
- Prior proposal continuation (2026-09-28): `speed-clause-binding-2026-09-28-001`
  preserves 21 observations/CoCs and links 11 existing entry contracts without translating them
  into speed rules. Exact source action spans yield 9 reduction/6 stop clause proposals;
  6 have no proposed clause, and Resume/Adapt #48/#50/#85/#94 have no single-action mapping.
  Executes 48 synthetic interface cases / 192 action verdicts; 8 new regression tests pass.
  This is an unaccepted proposal, not speed SMT, scene applicability or independent gold.
  All 21 scene verdicts remain UNRESOLVED; speed gold 0/21, dispatch/training 0.
  Its requested reduction/stop and common-input judgments are now accepted above,
  including holding route-sensitive #79/#81 pending context acceptance.
  Jonh's relayed self-report is now accepted above; a separate assignment decision remains required.
  M16/M17 PARTIAL; two-reviewer formal gate, 32-candidate denominator and 81 test exclusions retained.
  See [proposal and decision questions](docs/designs/PAPER1_SPEED_CLAUSE_BINDING_DESIGN_V01.md).
- Prior authorized preparation (2026-09-28): `longitudinal-endpoint-preparation-2026-09-28-002`
  reuses all 21 existing source answers unchanged and verifies 147 causal JPEGs / 19 clips.
  A four-action speed endpoint draft distinguishes maintain, decelerate, stop/wait, start/accelerate;
  multiple appropriate actions and undetermined judgments are allowed. Draft inputs contain only
  common instructions and past-frame references, not CoC/answers/polygons/machine verdicts.
  Reported UNKNOWN in 7 scenes, legacy NOT_APPLICABLE in 21, control FALSE in 4, source-claim
  checks in 3 and route-sensitive context in 2 are overlapping machine flags, not survey counts.
  #86/#94 slow notes and control FALSE are preserved; entry clearance is not speed release.
  New speed-action gold is 0/21; all 21 may ultimately need independent action judgment if admitted.
  That is not a repeat source survey. Actual assignment count remains unset; dispatch/training 0.
  Its next machine binding step is now prepared above; policy/input acceptance remains pending.
  Preparation authorized by user; main endpoint/cohort/gold/split NOT_FROZEN.
  See [speed endpoint design](docs/designs/PAPER1_LONGITUDINAL_ENDPOINT_DESIGN_V01.md).
- Prior full candidate coverage (2026-09-28): `remaining-action-coverage-2026-09-28-001`
  completes the remaining 22 source/action and AI visual audits: 20 scenes x 4 past frames,
  plus last-causal frame replay for candidates #26/#73 (video-review #18/#47). Combined coverage
  is 32 candidates / 29 clips, 122 frame occurrences / 119 unique JPEGs; not continuous video
  validation or independent human gold. Integrity/replay/denominator checks: 146 passed.
  Original action axes: longitudinal 21, lateral steering 6, lane change 1, yield unresolved 4.
  Proposed primary: longitudinal 21 candidates / 19 clips, NOT accepted eligibility or frozen cohort.
  #59 signal remains unobserved; #68 visible STOP paddle is not certified as the CoC's red light.
  Same-clip pairs #37/#84, #53/#59, #86/#94 stay grouped. Prior answers and #18 export unchanged.
  Subsequent user approval authorizes preparation above, not source acceptance or main-study freeze.
  No repeat source survey, new gold, training or arbitrary route.
- Prior frame/endpoint triage (2026-09-28): `m17-context-frame-audit-2026-09-28-001`
  checks 10 context candidates / 9 clips, 70 causal JPEG/time identities. AI visually inspected
  40 frame occurrences / 39 unique JPEGs, not continuous video or independent human gold.
  Eight environment descriptions are visually compatible, #79 remains partial, and #66's
  lane-change phrase leaks the original lateral answer. #88 has potential CoC/current-frame
  tension (red lights/pedestrian visible; signal applicability unresolved), not a certified CoC error.
  #86/#94 share one clip. Endpoint triage: longitudinal 5, lateral path 4, lane change 1;
  not admission counts or an expansion to all action families. New gold/training 0.
  See [endpoint draft](docs/designs/PAPER1_ORIGINAL_ACTION_ENDPOINT_DESIGN_V01.md).
  Remaining candidate coverage is completed above; endpoint/candidate-set acceptance stays open.
- Current direction (2026-09-28): preserve the original CoC/scene task and matched L0–L3
  constraint-learning comparison. Arbitrary maneuver assignment WITHDRAWN and producer blocked;
  its prototype was not executed. No new questionnaire, route assignment or training launched.
  `m17-original-coc-context-audit-2026-09-28-002` verifies 32 original CoC hashes/source bindings.
  Exact context fragments: 10; lateral-action-only cues: 2; no explicit path in lexical screen: 20.
  These are screening counts, not verified routes or eligibility. Source recommendations include
  deceleration 9, stop 6, yield 4, speed recovery/acceleration 5, lateral steering 6, lane change 1,
  speed adaptation 1. They cannot all be relabelled ENTER_ZONE/DEFER_ENTRY. New gold/training 0.
  The 10-candidate AI frame check is now recorded above; independent context/endpoint acceptance remains open.
  See [original-context decision](docs/decisions/PAPER1_ORIGINAL_CONTEXT_PRESERVATION_DECISION_V01.md).
- Prior suspension (still effective, 2026-09-28): yellow-zone ACTION review 16 and its coordinator preview
  SUSPENDED due to task cueing/route ambiguity. Existing observations, polygons, code and
  immutable runs retained; existing URLs now offer draft backup only. Do not repeat the survey.
  `m17-action-task-audit-2026-09-28-001` audits 32 annotations/bindings and 30 observations.
  The 16 source relations are TRUE 8/FALSE 8, not sixteen confirmed hazards. FALSE 8 are only
  screening candidates (#1, #48, #64, #66, #70, #79, #85, #88), not independent proceed labels.
  Pre-decision intended-route provenance established in the audited inputs: 0/32. Source turn
  claims #27/#81 are retrospective actions, not route commands. No new visual route validation.
  The hypothetical-task alternative is now withdrawn. Replacement questionnaire is not ready;
  lack of pre-decision route logs is not proof that no source task context is usable.
  See [task redesign decision](docs/decisions/PAPER1_ACTION_TASK_REDESIGN_DECISION_V01.md).
- Prior reviewer coordination (now suspended, 2026-09-28): one available reviewer, `Jonh`, nominated for 16
  development ACTION packets. The user confirms no prior CoC/answers/CNL/model-output exposure;
  this is not Jonh's own declaration or authenticated independence. Dispatch remains blocked on
  coordinator task/zone/input acceptance. No answers received; all ACTION must precede CNL.
  One-reviewer development audit does not meet or replace the existing two-reviewer formal gate.
- Prior ACTION answer UI (superseded by suspension, 2026-09-28): `m17-action-review-ui-2026-09-28-001` adds a separate
  16-scene form with explicit declaration, action/reason, completion counts, local draft recovery
  and batch JSON export/import. The coordinator preview now links to it. No acceptance or
  responses are inferred from preparing the form; no training/gold eligibility changes.
- Prior machine preflight (2026-09-28): `m17-machine-preflight-2026-09-28-002` replays
  30 scenes/210 past frames from pinned videos and checks CoC/annotation/time identities.
  Sixteen pedestrian-only conditional contracts/CNL documents pass 256/256 SMT queries;
  16 removed-gate UNKNOWN counterexamples reproduce. These are hypotheses, not source certification.
  Fourteen others remain in the denominator: occupancy unresolved 2, control task outside subset 9,
  target/zone/applicability unresolved 3. No observer answers or absent controls were inferred.
  Provisional ACTION packets 16 (two reviewer slots each), CNL packets 16 (64 clauses) are prepared,
  not dispatched or answered. Jonh is nominated only; coordinator acceptance is required before dispatch.
  M17 preparation is PARTIAL: 32 candidates/29 development clips retained; 81 previously exposed
  clips excluded from future test. Main N, fresh test, empirical intrinsic quality and gold remain open.
  See [M17 preflight design](docs/designs/PAPER1_M17_MACHINE_PREFLIGHT_DESIGN_V01.md).
- Latest substage (2026-09-28): 30/30 source observations received from Jin Hyun Kim;
  final/draft match and required fields, geometry syntax, packet/time identities pass.
  `source-observation-intake-2026-09-28-001` preserves both uploaded files byte-for-byte.
  Machine queue: grounding audit 16, applicability/scope audit 14 (not eligibility counts).
  122 legacy NOT_APPLICABLE fields retain unresolved interpretation; #59 signal-not-observed
  clarification is separate, not proof of no applicable control. No repeat source survey requested.
  See [observation acceptance](docs/decisions/SOURCE_GAP_OBSERVATION_ACCEPTANCE_DECISION_V01.md).
- Milestone completion: `M16 PARTIAL`; conditional development admitted 1/32;
  pending 30, currently unusable 1; full source verified 0, main cohort NOT_FROZEN;
  development SFT export 1 scene / 2 arm records (L0/L3), main training data 0;
  previous strict formal-60 eligibility 1/60 retained, not reclassified as a pass
- Active scope: C1 constraint usefulness, C2 source-grounded extraction, C3 EBLC verification
  and faithful natural-language rendering, C4 actual CoC+CNL training effectiveness
- Mandatory learner: a VLM receiving actual images/video and text, with full or internal-adapter
  fine-tuning. Frozen-VLM external-scorer training, text-only learning, prompting and SAT-only
  evidence cannot satisfy M18/M20. Held-out visual action/trajectory performance is required
- Paper-1 path: M12 → M14/M15 → M16 → M17 → M18 → M20. Full M13/strict60,
  broad B0–B13/OOD, M18 runtime expansion, M19/E5, E6 and M21 are deferred to phase 2
- Scope decision: [paper/deployment split](docs/decisions/PAPER_AND_DEPLOYMENT_SCOPE_DECISION_V01.md)
- Consistency audit: `COMPLETE` for document/code inspection and planning amendments only;
  R01–R10 remediation execution is not complete. Historical M00–M15 scoped/terminal results remain
  intact. The 1/60 count is the previous audit result, not re-certified in this audit
- Next prerequisite: `M12-R01 / GS-P0-SOURCE-REQUAL-001 PARTIAL`, limited to the selected
  paper-1 task/clauses/sources; the prior full-program audit is superseded in scope, not erased. See
  [consistency audit](docs/reports/MILESTONE_CONSISTENCY_AUDIT_REPORT_V01.md)
- Latest completed software substage (2026-09-08): `M12-R01-A` development policy and
  `M14-R01-A/B` qualitative contract → existing Core/SMT → common CNL renderer are complete.
  #18 pinned-source run passes 25/25 queries (12 non-vacuous premises, 12 probes, base SAT);
  removing the entry gate reproduces the UNKNOWN counterexample. Platform tests also check
  all 256 two-obligation truth/validity/prior combinations. One conditional contract/CNL,
  zero source-verified contracts or training exports. See [action contract design](docs/designs/PAPER1_ACTION_CONTRACT_DESIGN_V01.md).
- Latest completed machine substage: `M14-R01-C1` / remaining `M12-R01` source acceptance audit
  revalidated 32 candidates, 19 prior observations/13 deferred, and actual geometry exports.
  Both 98-record geometry JSON uploads contain zero stored polygons; review completion is retained.
  #18 has 21 past-only native-resolution display frames and an exact t0 PNG; its first video frame
  is -111570us versus the annotation point at 0us, explicitly context-only, not a time-aligned anchor.
  Source acceptance validator and one-scene review packet are ready; 14 new tests pass.
- Latest human source review: #18 submission by Jin Hyun Kim and subsequent user clarification
  are recorded in `scene18-source-clarification-2026-09-08-001`. Target/zone and pedestrian TRUE
  are retained; road TRUE becomes UNKNOWN because other-vehicle movement was not confirmed.
  Original upload is unchanged. Review completed 1, full source acceptance false, training exports 0.
- Latest completed event substage: `M14-R01-C2/C3` partial evidence → Core/SMT → common CNL,
  with 10/10 expected checks in `reviewed-scene18-execution-2026-09-08-001`.
  One observed event: pedestrian TRUE/valid, road UNKNOWN/invalid. Premises SAT, entry UNSAT,
  defer SAT; prior/future states remain unobserved. Independent ACTION/CNL packets are ready,
  with no independent responses at preparation time; full source-verified contracts and training exports remain 0.
- Latest ACTION intake: `scene18-action-intake-2026-09-08-001` records Jun Choi's actual
  DEFER_ENTRY response, because a pedestrian appears in the vehicle's path. Packet/source hashes
  and required fields pass. Independent eligibility is based on declaration and known-exposure
  checks, not authenticated identity or verified expertise. At ACTION intake: ACTION 1, CNL 0;
  no main-test or training-export promotion. Road UNKNOWN remains unchanged.
- Latest software substage: `M14-R01-C5` now connects actual event observations to natural
  language, not only generic lifecycle explanations. `scene18-conditioned-cnl-2026-09-08-002`
  generates four bilingual statements with binding/Core/query mappings; 12/12 checks match.
  Pedestrian TRUE/valid and road UNKNOWN/invalid yield a current defer-entry instruction and a
  separately labelled later-clearance condition. Ten new integration/UI-state tests pass.
  CoC+CNL insertion is a blocked preview, not training export. 001 is preserved; 002 adds explicit
  ego-subject and timestamp-type rejection without changing this scene's generated text.
- Latest CNL intake: `scene18-cnl-intake-2026-09-08-001` records Jun Choi's Korean SCENE_CNL
  response: all four statements SUPPORTED; declared independence/known-exposure checks pass.
  `scene18-review-linkage-2026-09-08-001` verifies matching frames/time/zone, regenerates the
  exact text from contract/source without ACTION labels, and passes 12/12 queries. Declared
  ACTION time precedes CNL; timestamps alone do not authenticate blinding or expertise.
- Latest English feedback: the user identified Jun Choi for the conversation statement that
  all English text reads with the same meaning. Recorded in `scene18-training-preflight-2026-09-08-001`;
  prior SCENE_CNL involvement declaration is reused, not a new attestation or authenticated identity.
  One overall meaning opinion, not four invented questionnaire responses or general renderer proof.
- Latest real-input preflight: same original event image/CoC and independent development ACTION
  feed two L0/L3-format previews. Local pinned Qwen3-VL processor emits identical 2148-token prompts,
  31 versus 142 supervised tokens, real image tensors, and assistant-only loss masks without truncation.
  One frame at t0-34us is used; this is not equivalent to the 21-frame review or frozen main sampling.
  No weights loaded/updated, no L1/L2 real provider or four-arm comparison, no training export.
- Previous strict candidate audit: `candidate-readiness-2026-09-08-003` covers all 32 candidates / 29 clips:
  READY 0, NEEDS_CONFIRMATION 31, CURRENTLY_UNUSABLE 1 (#47 prior NOT_OBSERVABLE, not permanent deletion).
  CoC/annotation/video/causal pixels verified 32/32; 19 observations and 32 geometry reviews reused.
  Four asset aliases resolved; 12 nearest display frames are after t0, so separately decoded last
  causal frames are recorded without changing the old review images. #18's new point/zone and
  ACTION/CNL remain linked with road UNKNOWN. All 32 inherit prior-development test exclusion;
  no train/dev/test assignment or training export. Gap list separates machine, protocol and human work.
- Previous conditional admission: `conditional-candidates-2026-09-08-002` completes exact source
  bindings for all 32: existing 19 replay identically, 13 added with no invented observations.
  [Approved research criteria](docs/decisions/PAPER1_CONDITIONAL_DATA_ADMISSION_DECISION_V01.md)
  separate full-source resolution, conditional development admission and main-study approval.
  #18 is conditionally admitted with road UNKNOWN retained; 30 pending and #47 currently unusable.
  Original CoC, source decisions and prior submissions are unchanged. Mixed-control scope remains
  unresolved; the #18 contract is not copied to other scenes. Nominal-entry labels 0, fresh test 0,
  real training exports 0, optimizer steps 0. This completes source-binding automation, not all ML work.
- Latest data preparation: `development-data-2026-09-08-001` exports one real scene (#18)
  as L0/L3 development SFT JSONL (two records, not two scenes), with copied input image,
  exact original CoC, independent development action and reviewed CNL. Local processor/mask checks pass.
  This downstream user-authorized development export does not rewrite prior export=false artifacts
  or admit main training. One-frame input is not equivalent to 21-frame review; no effect claim.
  Main-training scenes 0, nominal action gold 0, optimizer steps 0. See
  [dataset/review design](docs/designs/PAPER1_DEVELOPMENT_DATASET_AND_GAP_REVIEW_DESIGN_V01.md).
- Completed source review: 30 formally pending scenes have actual past-frame target/zone/condition
  forms, draft restore and partial completed-answer export. Prior no-visible-hazard 4 scenes
  are prioritized, not labelled ENTER_ZONE. #18 reused and #47 not re-requested. These exposed
  source answers must not become independent action gold. All 30 responses are now received;
  observation completion does not close formal source acceptance or action/CNL review.
  Portal UI uses `source-gap-ui-2026-09-09-002`, preserving the exact packet/draft identity
  and project-relative submission path. It adds target-point deletion without deleting the zone
  or other answers; affected target confirmation/completion is cleared. Dataset bytes are unchanged.
  Completion counts are visible beside the button, failures name the missing questions, and
  explicit NOT_APPLICABLE permits empty notes. UNKNOWN still needs a reason; no automatic answers.
- Next single task: `M12-R01 / M16` source-grounded speed applicability binding after completed ACTION intake;
  preserve original CoC context and keep the received ACTION references out of constraint generation. Main cohort/gold/split
  remain NOT_FROZEN. UNKNOWN-preserving admission policy does not turn policy output into gold.
  ACTION 1, Korean scene-CNL 1, attributed
  English opinion 1, formal English questionnaires 0, full source verified 0, development export 1 scene,
  main training exports 0.
  See [review separation](docs/designs/PAPER1_INDEPENDENT_DEVELOPMENT_REVIEW_DESIGN_V01.md).
  Do not request the same drawing again or turn UNKNOWN-policy DEFER_ENTRY into gold.
- Mandatory planned learning study: `M18 / GS-P5-LEARNING-001 / E4-L`,
  `QUEUED_NOT_EXECUTED`. EBLC→CNL must enter actual CoC training supervision; four arms and
  at least three paired training seeds compare violations and nominal task-success with matched
  model/data/budgets and no inference-time oracle guard/shield. Runtime evaluation is phase 2
- Paper gate: M20 requires actual E4-L checkpoints, training/compute logs and an independent
  evaluation report. Negative/inconclusive results are reportable; an unexecuted protocol is not
  a substitute. See [learning requirements](docs/requirements/M18_EBLC_LEARNING_EFFECT_REQUIREMENTS_V01.md)
  and [scope decision](docs/decisions/EBLC_LEARNING_EVALUATION_DECISION_V01.md)
- Supporting paper asset: [scene-18 worked illustration](paper/examples/SCENE18_PIPELINE_EXAMPLE_REPORT_V01.md)
  now includes pinned inputs, a manually encoded 3-decision SMT model, 11 queries with two
  explicit UNKNOWN gaps, clause/CNL correspondence and a blocked training preview. A one-page
  manuscript insert is prepared. Its manual model remains historical; the new versioned
  action-contract execution above supersedes its software gap only. Independent fidelity,
  action gold and learning remain incomplete. This does not close M12/M14/M16/M18/M20
- Previous completed source substage: exact declared CASCADE intervals audited for 19 reviewed events
  against 18 pinned annotations. Nine events have active causal actor/control targets; six have
  one source-linked person ID (not reviewer-confirmed identity or hazard truth). Release examples
  #54/#56 retain concurrent control annotations. No time widening, future-point interpolation,
  action-gold copying, EBLC/SAT execution or learning export. See the execution report below
- Previous completed review substage: existing video observations reused for 19/32 selected pedestrian
  development events, with original CoC, geometry and source references revalidated. Eighteen
  conditional review-derived drafts and one unobservable abstention are recorded; 13 events
  without prior video answers remain in the denominator. This is not independent model accuracy,
  verified EBLC/CNL or training data. No repeat survey requested; exact executable binding pending
- Previous completed software substage: paper-1 source inventory links original CoC to 98/98 prior events;
  32 pedestrian/cyclist-yield development candidates selected. Four-arm synthetic software
  smoke actually updates internal Qwen3-VL-2B LoRA weights from identical initialization.
  All four adapters are saved; 18 new integration tests pass. This is not real-scene E4-L training
  or effect evidence. See [execution report](docs/reports/PAPER1_CNL_LEARNING_READINESS_REPORT_V01.md)
- Previous completed substage: a restricted 60-scene expert workbench combines 60/60 pinned
  lane/drivable overlays, 60 low-confidence ego-corridor proposals, 33 event-near CASCADE target
  anchors across 24 scenes, 23 separately marked context-only anchors, eight pedestrian event-zone
  proposals, and the prior 60-scene video observation as a provenance-labelled draft
- Current incomplete stages: paper-1 clause/source/action/eligibility freeze, real-data arm
  providers and independent gold/semantic audit contracts. The CNL training software path now
  runs; existing strict60 UI/validator is not yet adapted
- Evidence: 33 local source records were reduced to 23 distinct events; 3 are source-complete,
  but only 1 has resolved scene jurisdiction and compatible authority, while 2 retain UNKNOWN
  jurisdiction and 1 prior record has a cross-event timestamp/evidence conflict
- Boundary: previous strict cohort 1/60; source acquisition/review is not independent gold,
  actual CNL training or vehicle-safety evidence; the new paper-1 denominator is not yet frozen
- Jurisdiction policy: no country whitelist or implicit KR default. Each scene country selects a
  treaty framework for which it is a recorded party. This closes only the M16 international-treaty
  normative-baseline gate; it does not claim domestic legal compliance
- Evidence: 2,066 licensed annotations are local; 135 aligned events yielded 98 slice candidates,
  37 unsupported events, and 38 multi-slice ambiguities without assigning any final outcome
- Sensor evidence: 81 unique clips, 486 selected members, and 1,448,583,496 bytes; all 98
  classified events have four-stream temporal closure without full-package download
- Calibration evidence: 405 selected feature rows and 3,337,630 bytes; 5/5 calibration and
  recorded-rig binding are available for all 98 classified events
- Initial review queue: actor/lane 24, actor/zone 19, control/lane 17, insufficient source geometry 38
- Source-review precheck: `COMPLETE`; 60 records completed the deliberately narrowed human video-
  observation review. The later structured-link audit reduced remaining actor/control source work
  to 28/98 and lane/zone association work to 97/98 without auto-promoting a complete scene
- Human video observation: `COMPLETE` 60/60 by one reviewer; JSON/CSV and all packet/image
  references match. Country, rule, source-ref and source-complete decisions remain excluded and
  this result does not change the 1/60 eligible-scene count
- Calibration/transform: NVIDIA NCore commit `59c698d206da92b406a4f72619fce3b3a2c64bfd`
  selects offline PhysicalAI egomotion/extrinsics for 98/98. The M16 event-anchor decision then binds
  review event timestamp as scene t0 and numerically verifies the coordinate transform for 98/98
- CASCADE structured links: relevant actor/control source set 70/98 and strict target lane
  containment 1/98; no unsourced curator decision or new complete scene was created
- Machine geometry candidates: 98/98 events and 490/490 frames generated from 81 hash-verified
  videos in `camera_front_wide_120fov_pixel`; curator review complete 98/98. Accepted masks are
  source-bound for 61 events/610 files, but semantic rig-frame geometry source field updates remain 0
- Active review status: #18 source, ACTION, Korean scene-CNL and attributed English feedback
  are recorded; those screens remain references, not repeat requests. The 30-scene source-gap
  review is complete/received; its screen is retained for reference, not a repeat request.
  Prior strict60 is historical
- Review boundary: this screen is source curation, not independent formal guard gold. Prior machine
  proposal/answer exposure must be recorded; gold annotation and assistance-utility cohorts must
  be separated before new formal review. Existing submissions remain reusable source observations
- Blocker: scene-grounded speed premises for 13 conditional contracts and missing contracts for 6 scenes;
  remaining source/target acceptance and concurrent-control scope, missing nominal-entry
  labels/fresh test, main gold/cohort, real L1/L2 providers and matched budgets remain pending.
  #18 road UNKNOWN is preserved and no longer a blanket conditional-development blocker.
  English meaning feedback is recorded but does not certify general renderer fidelity. The #18 source review stores
  confirmed point/polygon data; the earlier 98-record geometry uploads remain unchanged
- Next: M12-R01 / M16: source-grounded speed applicability binding; ACTION intake complete and original CoC context preserved. No repeat survey requested.
  Arbitrary routes are withdrawn and the previous 16 packets stay suspended; main cohort/gold/split freeze and
  real four-arm providers with matched budgets remain downstream.
  Full source-verified contracts and main training exports remain zero; development SFT export is 1 scene
- Next work-package requirements: [`docs/requirements/P0_SOURCE_CATALOG_REQUIREMENTS.md`](docs/requirements/P0_SOURCE_CATALOG_REQUIREMENTS.md)
- Scope decision: [`docs/decisions/GUARDSYNTH_MULTI_JURISDICTION_PILOT_SCOPE_DECISION_V01.md`](docs/decisions/GUARDSYNTH_MULTI_JURISDICTION_PILOT_SCOPE_DECISION_V01.md)
- Treaty baseline decision: [`docs/decisions/M16_INTERNATIONAL_TREATY_BASELINE_DECISION_V01.md`](docs/decisions/M16_INTERNATIONAL_TREATY_BASELINE_DECISION_V01.md)
- Event-anchor decision: [`docs/decisions/M16_REVIEW_EVENT_ANCHOR_DECISION_V01.md`](docs/decisions/M16_REVIEW_EVENT_ANCHOR_DECISION_V01.md)
- Governing plan: [`docs/plans/01_RESEARCH_PLAN_V02.md`](docs/plans/01_RESEARCH_PLAN_V02.md)
- Current execution: [`docs/plans/03_PROJECT_EXECUTION_TRACKER.md`](docs/plans/03_PROJECT_EXECUTION_TRACKER.md)
