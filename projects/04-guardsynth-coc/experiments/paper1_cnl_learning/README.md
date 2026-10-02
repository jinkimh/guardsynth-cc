# Paper-1 CoC/CNL learning development harness

Owner: `guardsynth-coc`. Protocol: `v2.3-cnl-supervision`.

## Actual speed ACTION intake and development evaluation bank (2026-09-29)

`intake_speed_actions.py --run-id <unused-numeric-suffix-id>` validates the received Jonh final/draft,
assignment and image identities, preserves the raw files, and exports separate
`development_action_inputs.jsonl` / `development_action_targets.jsonl` (19 rows each).
Current result: `guardsynth-paper1-training-readiness-001/speed-action-intake-2026-09-29-001`.
Three clarified action fields are masked, not relabelled; one other judgment is undetermined.
The callable `score_development(targets, predictions)` scores the remaining72 definite judgments.
Each prediction is `{"sample_id": "...", "action_assessments": {<four action codes>: <assessment>}}`;
preserve input order and all19 samples. Prediction abstention stays in the definite-label denominator.
This bank is development-only, not a main test or SFT export. Never feed target reasons, original
CoC or coordinator comparisons to the blind action input. Existing packet references provide the
same causal images as the human review; no new exposure or human answers are generated.

## M17 machine preflight (human gates pending)

`prepare_m17_preflight.py --run-id <unused-numeric-suffix-id>` replays the thirty reviewed scenes,
generates the supported pedestrian-only conditional contracts through shared Core/SMT/CNL,
and prepares separate provisional ACTION/CNL packets plus a group/exposure ledger.
Current run: `guardsynth-paper1-training-readiness-001/m17-machine-preflight-2026-09-28-002`.
Read `REPORT_KO.md` and `review_coordination.json` before assigning reviewers. Never send an
ACTION reviewer the whole directory, CNL, source audit or solver results before their response.
The two ACTION reviewer slots are unassigned; coordinator task/zone acceptance is still needed.
This is not a full-scene policy, main training export, independent gold or M17 completion.
See [design](../../docs/designs/PAPER1_M17_MACHINE_PREFLIGHT_DESIGN_V01.md).

## Completed source observation intake (2026-09-28)

`accept_source_observations.py --run-id <unused-numeric-suffix-id> --packet <packet.json>
--review <completed-review.json> --draft <draft.json>` validates full packet coverage and
final/draft agreement, preserves both uploads byte-for-byte and writes interpretation plus
machine work queues. Current run: `guardsynth-paper1-training-readiness-001/source-observation-intake-2026-09-28-001`.
Thirty observations are received, not independent actions or main training examples. Legacy
NOT_APPLICABLE does not prove absence of an obligation. The pinned #59 user clarification
is signal-only and must not be reused for another scene. See the
[acceptance decision](../../docs/decisions/SOURCE_GAP_OBSERVATION_ACCEPTANCE_DECISION_V01.md).

## Actual scene-conditioned CNL (current task)

`generate_scene_cnl.py` passes the actual reviewed event binding and contract to a project-owned
renderer which executes the shared Core/SMT checks before emitting text. Current immutable run:
`guardsynth-paper1-reviewed-contract-001/scene18-conditioned-cnl-2026-09-08-002`.
It emits four Korean/English statements, 12 checks, claim-source mapping, a scene/evidence/text
review page and a blocked CoC+CNL preview. 001 is retained; 002 adds explicit subject/time validation.

```bash
runtime/alpamayo/ar1_venv/bin/python projects/04-guardsynth-coc/experiments/paper1_cnl_learning/generate_scene_cnl.py --run-id scene18-conditioned-cnl-2026-09-08-003
runtime/alpamayo/ar1_venv/bin/python -m unittest discover -s projects/04-guardsynth-coc/tests/integration -p test_scene_conditioned_cnl.py -q
```

Use an unused ID. Intake uses `execute_reviewed_contract.py --review <scene18_scene_cnl_review.json>
--packet <current-run>/scene18_scene_cnl_review_packet.json --run-id <unused-intake-id>`.
SCENE_CNL is an informed claim review, not blind ACTION gold. Prior generic CNL responses are
not transferable. English text/full lifecycle fidelity and training remain unapproved.
The portal preserves the old `scene18_independent_cnl_review.html` URL but serves the new page.
[Design](../../docs/designs/PAPER1_SCENE_CONDITIONED_CNL_DESIGN_V01.md).

## Generic contract review (historical, not the current scene-CNL task)

The previous generic CNL screen used the versioned Korean presentation:
`guardsynth-paper1-reviewed-contract-001/scene18-cnl-korean-review-2026-09-08-002`.
`localize_cnl_review.py --run-id <unused-run-id>` preserves the original packet fields and adds
Korean assistance. For its response, use that run's `scene18_independent_cnl_review_packet.json`
with `execute_reviewed_contract.py --review ... --packet ... --run-id ...`.
The ACTION packet remains in the original execution run. Full hashes stay in metadata/downloads;
the body uses source names. The three behavioral cards pair actual Core rules with actual
renderer excerpts; identity/source metadata are not questions. Original five clause IDs remain
in the packet and the reviewed subset is explicit. [Scope](../../docs/designs/PAPER1_PAIRED_CNL_REVIEW_DESIGN_V01.md).

`execute_reviewed_contract.py` replays the source submission and separate user clarification,
binds one observed event to the shared Core compiler and emits common CNL plus separate
ACTION/CNL review pages. Current immutable run:
`guardsynth-paper1-reviewed-contract-001/reviewed-scene18-execution-2026-09-08-001`.
Pedestrian TRUE/valid, road UNKNOWN/invalid; 10 expected solver checks pass. No independent
answer or training export is inferred. [Reviewer separation](../../docs/designs/PAPER1_INDEPENDENT_DEVELOPMENT_REVIEW_DESIGN_V01.md).

```bash
runtime/alpamayo/ar1_venv/bin/python projects/04-guardsynth-coc/experiments/paper1_cnl_learning/execute_reviewed_contract.py --run-id reviewed-scene18-execution-2026-09-08-002
runtime/alpamayo/ar1_venv/bin/python -m unittest discover -s projects/04-guardsynth-coc/tests/unit -p test_independent_development_review.py -q
runtime/alpamayo/ar1_venv/bin/python -m unittest discover -s projects/04-guardsynth-coc/tests/integration -p test_reviewed_action_contract.py -q
```

Always use an unused run ID. For real human intake, pair `--review <export.json>` with
`--packet <execution-run>/scene18_independent_action_review_packet.json` (or the CNL packet)
and a new intake run ID. Known source exposure cannot be overridden by an independence
checkbox. Identity/qualification and additional exposure require coordinator verification.
Record UNKNOWN/unjudgeable or disagreement; do not silently fabricate affirmative gold.

## Source acceptance / one-scene human handoff (completed source review)

`prepare_source_review.py` audits existing sources and produces a self-contained #18 source
confirmation screen. This is not an independent action-gold screen. Current run is
`guardsynth-paper1-source-acceptance-001/scene18-source-acceptance-2026-09-08-003` under the
project's restricted root; 001 and failed 002 are preserved. See [acceptance design](../../docs/designs/PAPER1_SOURCE_ACCEPTANCE_DESIGN_V01.md).

```bash
runtime/alpamayo/ar1_venv/bin/python projects/04-guardsynth-coc/experiments/paper1_cnl_learning/prepare_source_review.py --run-id scene18-source-acceptance-2026-09-08-004
runtime/alpamayo/ar1_venv/bin/python -m unittest discover -s projects/04-guardsynth-coc/tests/unit -p test_source_acceptance.py -q
runtime/alpamayo/ar1_venv/bin/python -m unittest discover -s projects/04-guardsynth-coc/tests/integration -p test_source_acceptance_runner.py -q
```

After a real human submission, use paired `--review <export.json>` and
`--packet <preparation-run>/source_review_packet.json` with an unused intake run ID.
The intake verifies pinned sources/frames and preserves a human-declared development verdict;
it never emits independent action gold or a training export. UNKNOWN submissions are recorded,
not rejected as unfinished surveys. Synthetic test responses exist only in temporary test dirs.

## Executable conditional action subset (2026-09-08)

`action_contract.py` revalidates #18 inputs and executes a versioned qualitative contract through
the shared EBLC Core compiler and CNL renderer. It does not use the old handwritten Z3 model.
The current adapter is pinned to #18, not a general CoC extractor. Missing target/zone/predicate
acceptance and independent action gold remain explicit; no training export is produced.

```bash
runtime/alpamayo/ar1_venv/bin/python projects/04-guardsynth-coc/experiments/paper1_cnl_learning/action_contract.py --run-id scene18-action-contract-2026-09-08-003
runtime/alpamayo/ar1_venv/bin/python -m unittest discover -s platforms/eblc-bcv/tests/unit -p test_action_contract.py -q
runtime/alpamayo/ar1_venv/bin/python -m unittest discover -s projects/04-guardsynth-coc/tests/integration -p test_action_contract_runner.py -q
```

Use an unused ID. Outputs belong to `guardsynth-paper1-action-contract-001` in this project's
restricted artifact root. Completed run 002 contains 25 expected checks, two mutation checks,
Core/schema/CNL provenance and a blocked source gate. [Policy](../../docs/designs/PAPER1_ACTION_CONTRACT_DESIGN_V01.md).

## Existing numeric/synthetic learning harness

This runner audits existing licensed CoC links and tests the actual local VLM training path.
It does **not** launch a confirmatory E4-L study or admit examples to a paper test set.
The four-arm software smoke uses one labelled **synthetic diagram/fixture**, one seed and
one update per arm. Its L1 provider is a synthetic-policy projection only; its clean L2/L3
renderings coincide. These are not real-data baseline results or a verification-benefit test.

From repository root:

```bash
runtime/alpamayo/ar1_venv/bin/python projects/04-guardsynth-coc/experiments/paper1_cnl_learning/run.py audit --run-id paper1-source-audit-2026-09-06-003
runtime/alpamayo/ar1_venv/bin/python projects/04-guardsynth-coc/experiments/paper1_cnl_learning/run.py software-smoke --run-id paper1-vlm-smoke-2026-09-06-004 --device cuda:1
runtime/alpamayo/ar1_venv/bin/python -m unittest discover -s projects/04-guardsynth-coc/tests/integration -p 'test_*cnl*py' -v
```

Choose an unused run ID and a free authorized GPU. In the current agent sandbox, GPU access
requires an approved execution outside the sandbox; do not install or change drivers.
All model loading is `local_files_only=True`. The default cached snapshot is Qwen3-VL-2B-Instruct
revision `89644892e4d85e24eaac8bacfd4f463576704203`. File hashes pin actual model bytes;
an overridden model path is not certified to match the default revision.

Outputs are private owner-scoped runs under
`artifacts/projects/guardsynth-coc/restricted/guardsynth-eblc-learning-001/<run-id>/`.
Existing IDs are refused. Runs record source/model/code hashes, assistant-only masks, input
and target tokens, actual LoRA deltas, adapter weights and a zero-pixel diagnostic. The latter
checks sensitivity to visual tensors, **not correct visual grounding**. No held-out action
metrics, statistical confidence intervals or matched-compute claim are manufactured.

The current semantic gate checks source-generation status, expansion, Core compilation,
base satisfiability and supported compiler queries. It does not replace independent evidence
validation, source-clause admissibility, bounded lifecycle mutation tests or CNL semantic review.
Do not train on review contact sheets containing future frames, proposal overlays or answers.

Current design and next gates:
[paper-1 development design](../../docs/designs/PAPER1_CNL_LEARNING_DESIGN_V01.md),
[execution report](../../docs/reports/PAPER1_CNL_LEARNING_READINESS_REPORT_V01.md).

## Reuse existing scene reviews

```bash
runtime/alpamayo/ar1_venv/bin/python projects/04-guardsynth-coc/experiments/paper1_cnl_learning/align_reviews.py --run-id reviewed-scene-alignment-2026-09-07-002
runtime/alpamayo/ar1_venv/bin/python -m unittest discover -s projects/04-guardsynth-coc/tests/unit -p test_review_constraint_alignment.py -v
runtime/alpamayo/ar1_venv/bin/python -m unittest discover -s projects/04-guardsynth-coc/tests/integration -p test_review_alignment_runner.py -v
```

This CPU-only runner revalidates the existing video JSON/CSV and packet/image hashes, the
geometry JSON/CSV and frame/mask hashes, and the exact original CoC links. It emits 19
reviewed-scene correspondences and retains 13 not-yet-video-reviewed candidates in the
32-scene denominator. Its HTML is read-only, with modal image zoom/return, not a new survey.
Outputs belong to the separate restricted `guardsynth-review-constraint-alignment-001` family.

The conditional drafts reuse human answers; they are not independent model predictions,
verified EBLC/CNL, or training exports. Window-level hazard absence is not a PROCEED label,
and a transition note does not supply an exact release time. Mixed worker/traffic-control
CoC context is explicitly marked. Missing executable inputs remain blocked rather than
receiving synthetic metric values or an implicit KR rule.

## Bind exact event sources

```bash
python3 projects/04-guardsynth-coc/experiments/paper1_cnl_learning/bind_event_sources.py --run-id event-source-binding-2026-09-07-003
python3 -m unittest discover -s projects/04-guardsynth-coc/tests/unit -p test_event_source_binding.py -v
python3 -m unittest discover -s projects/04-guardsynth-coc/tests/integration -p test_event_source_binding_runner.py -v
```

This CPU-only step revalidates the correspondence's inputs and hashes the original CASCADE
annotations against the earlier structured audit. It records exact closed-interval witnesses,
causal target IDs, active controls, source keypoint offsets, and future-action context separately.
It neither widens timestamps by 500 ms nor interpolates points into event geometry. All 32
development candidates remain represented. Unique source-linked people are not automatically
reviewer-confirmed targets, hazards or action gold. The output is restricted JSON/report with
an immutable manifest; it does not call EBLC, SAT, the CNL renderer or a learning exporter.

## Refresh scene CNL review UI without changing answers

`audit_training_candidates.py --run-id candidate-readiness-2026-09-08-003` audits the 32 selected
development candidates (choose an unused ID for reruns). It preserves all rows and original
reviews, resolves registered video asset aliases, hashes/decode-checks causal frames separately
from historical nearest-frame overlays, and links the newer scene18 evidence. Outputs include
readiness JSON/CSV/HTML, missing-evidence work groups and clip-level quarantine, not a random
train/test split. Unreviewed development candidates are not fresh held-out data. No extra survey,
ground truth, source acceptance or training export is inferred. Regression: `test_training_candidate_audit.py`.

`prepare_scene_training.py --run-id <unused-run-id> --reviewer <name> --statement <actual-statement>`
records conversation-attributed English feedback and prepares an actual-scene CPU processor
preflight using the local pinned learning runtime. It reuses only the same reviewer's prior
participation declaration and records that provenance; it does not invent a fresh attestation,
review time, or per-clause questionnaire. L0/L3-format previews use one causal frame, original
CoC and the independent development ACTION. They remain explicitly preview-only/export=false;
real L1/L2 providers, source/target/split and equal token/compute budgets remain unresolved.
No model weights are loaded. Use `test_scene_training_preflight.py` for boundary regression checks.

After packet-bound ACTION and Korean SCENE_CNL intake, run
`link_scene_reviews.py --run-id scene18-review-linkage-2026-09-08-001` with the project Python
runtime to reproduce the development linkage audit (choose an unused run ID for reruns).
It revalidates both intakes, matches frames/time/zone, and regenerates text from source/contract
without action labels. Its report pairs the actual Korean/English text for the remaining human
English review. Recorded response order does not prove blinding; no source, main-test or training
gate is promoted. Tests: `test_scene_review_linkage.py` in the project integration suite.

For a scene CNL review **UI-only** repair, use `generate_scene_cnl.py --run-id <unused-run-id>
--refresh-review-from <existing-scene-cnl-run>`. This revalidates the source artifacts and
embedded frames, retains packet/document/coordination bytes and the browser draft key, and
renders the current template into a new immutable run. It does not generate new statements,
accept human answers, or advance a research gate. The save handler reads current form values;
required name, participation, four judgements and reason are reported individually when missing.

## Export development data and prepare missing-source review

Current run: `guardsynth-paper1-training-readiness-001/development-data-2026-09-08-001` under restricted artifacts.
`l0_development.jsonl` and `l3_development.jsonl` are one record each of the SAME real scene #18.
They use the existing `build_example`/`encode` format: actual image/task input and assistant-only
CoC/[CNL]/independent development action target. Image paths are absolute to this local run;
do not move files without rebuilding hashes. `split=dev` means exposed development use, never
held-out evaluation. Main training is not approved; L1/L2, main labels/sampling/splits remain pending.

```bash
runtime/alpamayo/ar1_venv/bin/python projects/04-guardsynth-coc/experiments/paper1_cnl_learning/prepare_development_dataset.py --run-id development-data-2026-09-08-002
runtime/alpamayo/ar1_venv/bin/python -m unittest discover -s projects/04-guardsynth-coc/tests/integration -p test_development_dataset.py -v
```

Use an unused run ID. `source_gap_review.html` contains 30 actual source-only forms; responses
can cover a subset. Store `paper1_source_gap_review.json` in the displayed submission folder.
Intake uses the same runner with `--run-id <unused-intake-id> --packet <source_gap_packet.json>
--review <paper1_source_gap_review.json>`. It records validated source answers without promoting
them to actions, CNL or training admission. Confirmed zones then feed a separately blinded ACTION
review. Draft files are not accepted as completed responses. #18/#47 are not requested again.
For UI-only changes, use `--refresh-review-from <existing-run-directory>` with an unused run ID.
The deployed UI run is `source-gap-ui-2026-09-09-002`; its packet is byte-identical to the data run
and retains the browser draft key. The submission location is shown relative to the repository.
The target-point delete button clears only the point and its confirmation, invalidates that scene's
completion, and saves the draft. Zone/other answers remain. Regression check:
`node projects/04-guardsynth-coc/tests/integration/test_source_gap_point_delete.js`.
This test also checks completion 0/30 → 1/30 → 2/30, persistence and nonapplicable blank notes.
The [completion UI amendment](../../docs/designs/SOURCE_GAP_COMPLETION_UI_DESIGN_V01.md)
permits blank notes only with an explicit NOT_APPLICABLE selection; UNKNOWN still requires reasons.

## Complete source bindings and assess conditional development admission

```bash
runtime/alpamayo/ar1_venv/bin/python projects/04-guardsynth-coc/experiments/paper1_cnl_learning/complete_candidate_bindings.py --run-id conditional-candidates-2026-09-08-003
runtime/alpamayo/ar1_venv/bin/python -m unittest discover -s projects/04-guardsynth-coc/tests/integration -p test_conditional_admission.py -v
```

Use an unused run ID; the current completed result is `conditional-candidates-2026-09-08-002`.
The runner replays 19 existing bindings, extends 13 source-only records without human answers,
and applies the approved UNKNOWN-preserving policy separately from full-source/main approval.
Current conditional candidates 1, pending 30, unusable 1. Full-source/main approval, nominal labels,
fresh tests, learning exports and optimizer steps remain zero. The work queue is not a ready survey.

## Reproduce the paper worked illustration

```bash
runtime/alpamayo/ar1_venv/bin/python projects/04-guardsynth-coc/experiments/paper1_cnl_learning/worked_example.py --run-id scene18-pipeline-example-2026-09-08-003
runtime/alpamayo/ar1_venv/bin/python -m unittest discover -s projects/04-guardsynth-coc/tests/integration -p test_paper_worked_example.py -v
```

This separate illustration **does run Z3**, but directly encodes a manually authored logical
projection of the conversational draft; it does not use the production EBLC frontend. Three
abstract decisions are not measured video frames. Eleven satisfiable-premise checks precede
eleven queries: 6 SAT / 5 UNSAT, including two explicit UNKNOWN-policy gaps and a C4-removal
mutation. Both the premises and full queries are saved as 22 SMT-LIB files for replay.

The output family is restricted `guardsynth-paper-worked-example-001`. `source_example.json`
pins the original CoC/annotation/video/display image. `cnl_correspondence.json` preserves manually
authored clause/CNL pairs. `training_example_preview.json` has null action/finalized target and
export=false. The read-only HTML references the existing overlay without copying it into the paper.
These are not real-scene safety, independent semantic-fidelity or learning-effect results.

[Detailed example and publication boundaries](../../paper/examples/SCENE18_PIPELINE_EXAMPLE_REPORT_V01.md),
[English manuscript insert](../../paper/examples/scene18-worked-example.tex),
[compiled one-page preview](../../../../artifacts/projects/guardsynth-coc/restricted/guardsynth-paper-worked-example-001/scene18-paper-preview-2026-09-08-001/scene18-example-preview.pdf).

## Current v2.4 temporal preservation execution

The approved primary protocol is `paper1-method-preservation-v0.1`.
`temporal_preservation.py` imports the Project01 world read-only, validates a restricted supplied
single-clear-transition contract, lowers to shared EBLC Core/SMT, and renders P2 from contract
fields only. It is not automatic road-source extraction. `train_temporal_preservation.py` reuses
Project01's actual Qwen visual collator/LoRA trainer with matched P0/P1/P2 budgets and checks
that the selected physical GPU is idle before loading the model. It refuses existing run IDs.

Frozen artifacts reside at `artifacts/projects/guardsynth-coc/public/paper1-method-preservation-001/`.
`temporal-protocol-2026-09-29-001` fixes three paired seeds,72 updates per arm/seed, criterion
thresholds, prompts, supplied contracts, source hashes, and2,016 paired records. Only six
unique storyboard images exist across standard and unseen-time conditions. New generator seeds
are samples from reused templates, not independent environment confirmation. No LLM-expanded
labels are used in this controlled run; therefore no fabricated human audit is recorded.

```bash
runtime/alpamayo/ar1_venv/bin/python -m unittest discover -s projects/04-guardsynth-coc/tests -p 'test_temporal_preservation*.py' -v
runtime/alpamayo/ar1_venv/bin/python projects/04-guardsynth-coc/experiments/paper1_cnl_learning/analyze_temporal_preservation.py --run-id temporal-learning-2026-09-29-001 --protocol-id temporal-protocol-2026-09-29-001 --analysis-id temporal-analysis-2026-09-29-002
```

All nine fits and analysis001 are complete. The command uses a fresh analysis ID to preserve001;
incomplete rows are rejected. Metrics use an
independent environment-rule implementation. Identical weak P1/P2 controls fail the frozen
level criteria. Template-cluster intervals do not establish general environmental power or
formal noninferiority. Historical real-road no-guard-at-test/four-arm workflows above remain
separate follow-up consumers and are not silently relaxed.

## Frozen D1–D4 follow-up

`temporal_diversity.py`, `run_temporal_diversity.py`, and `analyze_temporal_diversity.py`
implement the separate v0.2 numeric profile, immutable paired inputs, reused-adapter inference,
Core-bound behavior tests and independent scoring. Frozen files must not be changed to tune on
`diversity-protocol-2026-09-29-001`. The completed inference has2,160 scored rows/1,476 actual
model calls; D4 audits the same192 candidate records with and without layered verification.
New-time failures and shared-source-error misses are retained. No expanded training uses these holdouts.

```bash
runtime/alpamayo/ar1_venv/bin/python -m unittest discover -s projects/04-guardsynth-coc/tests -p test_temporal_diversity.py -v
runtime/alpamayo/ar1_venv/bin/python projects/04-guardsynth-coc/experiments/paper1_cnl_learning/analyze_temporal_diversity.py --protocol-id diversity-protocol-2026-09-29-001 --run-id diversity-inference-2026-09-29-001 --analysis-id diversity-analysis-2026-09-29-002
tmux capture-pane -p -t guardsynth-temporal-expansion-20260929:0.0 -S -30
```

The final command only monitors the separate authorized six-arm training. Do not launch a
duplicate fit or overwrite its queue/run. `progress.json` records actual updates; planned18
checkpoints/17,280 predictions are not completion evidence.
