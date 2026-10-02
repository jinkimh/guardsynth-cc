# Claim--Evidence Audit Ledger

## Scope and baseline record

This ledger is the evidence boundary for the domestic-journal revision. It distinguishes recorded or derived protocol evidence from synthetic tests and does not promote any entry to a physical-safety conclusion.

### Worktree snapshot

The requested `git status --short` and `git diff -- projects/03-sequential-coc-verification/paper/manuscript` commands could not be completed because this workspace has no Git metadata (`fatal: not a git repository`). Consequently, pre-existing modified and untracked files cannot be enumerated from Git in this environment. No pre-existing manuscript file was overwritten; this ledger is a newly created file.

### Final manuscript build record

On 2026-08-05, the manuscript was rebuilt directly with
`xelatex -> bibtex -> xelatex -> xelatex`. Because the base TeX installation
lacked `IEEEtran.cls`, Korean XeTeX support and the declared Noto Serif CJK
font, the missing Debian packages were downloaded and extracted only under
task-specific `/tmp` trees; the repository was not given vendored TeX
dependencies. The final `main.log` contains no undefined commands, citations,
references, or overfull boxes. Remaining warnings are benign font-shape
substitutions and underfull spacing notices.

`mutool info main.pdf` reports 15 pages with a 612 x 792 point media box
(US Letter). All 15 pages were rendered at 120 dpi with `mutool draw` and
visually inspected. No blank column, clipped table, overlapping label, broken
Korean glyph, or isolated section heading was observed.

### Artifact-path note

The requested `jq` executable is unavailable. JSON inspection with Node.js established that the cohort artifact uses top-level paths `.scene_count`, `.model_count`, and `.query_evaluation_count` (rather than the brief's illustrative `.summary.*` paths). The chain artifact likewise uses top-level `.result_count`, `.all_pass_count`, `.deadline_fail_count`, `.responded_fail_count`, and `.boundary_fail_count`.

| Claim ID | Manuscript claim | Direct artifact/evidence | Allowed interpretation | Prohibited interpretation | Final manuscript location | Status |
|---|---|---|---|---|---|---|
| CE-01 | The chunk-0 flow is 403 annotations, 290 quality-passing events, 134 included direction-explicit annotation-event candidate contracts, and 156 excluded ambiguous/non-directional/compound-intent events (`290=134+156`). | `artifacts/results/public/chunk-0000-94/weak-kinematic-cohort-result.json`: `.cohort.event_count=403`, `.cohort.trusted_event_count=290`, `.cohort.evaluable_contract_count=134`, and event-level `exclusion_reason`; upstream model identity in `data/baseline/coc_nusc/UPSTREAM_README.md`. | Inference is restricted to the English-regex direction-explicit subset; 134 is a single-event screen and repeated events may share one response onset. | That all 403 annotations were verified, that 134 are independent responses/episodes, or that the counts establish dataset-wide safety. | Sec. 3 input flow; Sec. 6 Block B; Sec. 7 RQ2; Sec. 9 external validity | qualified |
| CE-02 | The 134 candidates decompose as 130 speed-detector cases + 4 already-satisfied cases and route as `125+4+5` at `D=3` s. | `artifacts/results/public/chunk-0000-94/weak-kinematic-cohort-result.json`: `.cohort.evaluable_contract_count=134`, `.cohort.contract_pass_count=129`, `.cohort.contract_fail_count=5`; `video-review-result.json`: `.contract_revision` records 8 before, 5 after, the `speed <= 0.5 m/s` rule, and three reclassified event IDs. | This is a post-hoc, cohort-calibrated exploratory routing result; `D=3` s and `0.5 m/s` are not normative safety thresholds. | That the five candidates are real faults, that the 125+4 cases are safe, or that the routing supplies safety/risk labels. | Abstract; Secs. 3--4; Sec. 6 Block B; Sec. 7 RQ2; Secs. 8--10 | qualified |
| CE-03 | Selected repeated-decision cases reverse the `D=3` verdict under `preserve` versus `reset`. | `artifacts/results/public/remaining-candidates/uppaal-multi-property-verification-result.json` and `artifacts/results/public/scene-0074/uppaal-repeated-obligation-semantics-result.json`. | Repeat policy changes latency interpretation and must be specified; `preserve` is not uniquely correct. | That either policy is the correct controller requirement or that reversal proves a vehicle-control fault. | Sec. 1 example; Sec. 4 repeat semantics; Sec. 7 RQ2; Sec. 8 Q2; Sec. 9 measurement validity | qualified |
| CE-04 | Sensitivity uses 27 detector settings over the 130 speed-change cases. | `artifacts/results/public/chunk-0000-94/weak-kinematic-cohort-result.json`: `.contract` and `.cohort`; `artifacts/results/public/workshop-boost/workshop-experiment-results.json`: `.detector_ablation` records 130 cases and robustness buckets. | Detector agreement is a sensitivity/review signal for derived ego-motion evidence. | That 27 settings exhaust valid detectors or that one setting proves an actual violation. | Sec. 4 detector definition; Sec. 6 Block B; Sec. 7 RQ2/Table `tab:detector-sensitivity`; Sec. 9 | qualified |
| CE-05 | The cohort artifact records 282 generated variants. | `artifacts/results/public/chunk-0000-94/uppaal-cohort-verification-result.json`: `.model_count=282`; structure in `projects/03-sequential-coc-verification/experiments/uppaal/generate_cohort_models.py`. | The count is the scope of two-template serialized baseline/provenance/response variants. | That 282 physical scenarios or observer-level timed mutations were validated. | Sec. 5 model-family table; Sec. 6 Block B; Sec. 7 RQ1 | qualified |
| CE-06 | The cohort artifact records 1,128 query evaluations and oracle agreement. | `artifacts/results/public/chunk-0000-94/uppaal-cohort-verification-result.json`: `.query_evaluation_count=1128`, `.all_mutation_oracles_match=true`; `generate_cohort_models.py` directly sets violation Booleans and derives expected verdicts from variant labels. | This is flag/query serialization regression; observer-level timed mutation evidence is confined to `scene-0001`. | That 1,128 queries establish detection performance, validate all faults, or validate deployment behavior. | Sec. 6 Block B; Sec. 7 matrix/RQ1; Sec. 9 internal validity | qualified |
| CE-07 | A synthetic, non-atomic deduplication mutation can retain a response after removing its accepted trigger. | `artifacts/results/public/remaining-candidates/uppaal-multi-property-verification-result.json`; mutation construction in `projects/03-sequential-coc-verification/experiments/uppaal/generate_remaining_candidate_models.py`. | This is a preprocessing-lineage serialization/regression signal. | That an orphan response is a nominal label, naturally observed driving error, or safety incident. | Sec. 5 mutation oracle; Sec. 7 RQ2/table; Sec. 8 Q1; Sec. 9 | qualified |
| CE-08 | Without local continuity evidence, the boundary negative control discards a pending obligation instead of carrying it across scenes. | `artifacts/results/public/workshop-boost/local-scene-continuity-negative-control.json`; checker artifact `artifacts/results/public/scene-continuity-audit.json`. | The saved artifacts support the query-checkable independent-clip boundary policy. | That unrelated scenes form a continuous route or that boundary handling proves continuity. | Sec. 5 multi-scene extension; Sec. 6 Block C; Sec. 7 RQ3/Table `tab:boundary-negative-control` | supported |
| CE-09 | A distinct 13-chain implementation artifact records 4 all-query-pass, 9 non-all-query-pass, 8 deadline, 7 response-reachability, and 0 boundary flags. | `artifacts/results/public/multiscene-chain/uppaal-loop-batch-all-strict-1s.json`; `generate_multiscene_chain_model.py` (`W=1.0` s, `delta=0.7` m/s, no ratio, slow-first substring parser) and `generate_multiscene_loop_model.py` (`LoopSource`/`Monitor`). | Descriptive output of an implementation-specific pipeline smoke test only. | Any quantitative RQ/generalization claim under the shared detector contract, official trainval result, or object/hazard continuity claim. | Abstract boundary; Sec. 6 Block C; Sec. 7 matrix/RQ3 smoke table; Secs. 8--10 | qualified |
| CE-10 | The aggregate artifact records 13/13 script/UPPAAL agreement. | `artifacts/results/public/workshop-boost/workshop-experiment-results.json`: `.script_baseline_vs_uppaal_loop_batch.item_count=13`, `.comparable_all_match_count=13`. No executable baseline or per-item comparison artifact is preserved. | Only that the aggregate artifact records 13/13 agreement. | Independent implementation/per-item reproducibility, numerical superiority, or vehicle-safety assurance. | Sec. 7 matrix/RQ4; Sec. 8 Q3; Sec. 9 formalization limitation; conclusion | qualified |

## Interpretation guardrail

Every ledger item is limited to protocol-level consistency of a CoC decision, derived ego-motion response evidence, stated timing policy, and provenance handling. Missing relative-object state, actuator commands, vehicle dynamics, and closed-loop outcomes remain outside this ledger's evidence scope.

`D=3` s is an analysis setting, not a vehicle-safety threshold. Throughout this ledger, PASS means a specified contract pass and FAIL means a review candidate under the stated analysis policy; neither term denotes a safe or risky vehicle outcome.

## Final RQ coverage checklist

| RQ | Method | Experiment | Direct result | Explicit limitation | Complete |
|---|---|---|---|---|---|
| RQ1 | Sec. 5 evidence collection, contract compilation, model families and mutation oracle | Sec. 6 Block A | Sec. 7 RQ1 and result--claim matrix | Sec. 9: trajectory-conditioned CoC and `scene-0001` timed mutations only | yes |
| RQ2 | Sec. 4 half-open deadline, detector and repeat semantics; Sec. 5 router | Sec. 6 Block B | Sec. 7 RQ2, calibration, candidate and sensitivity tables | Sec. 9: direction-explicit subset, ego-speed proxy, post-hoc `0.5 m/s`, `D=3` s and policy dependence | yes |
| RQ3 | Sec. 5 boundary policy and multi-scene extension | Sec. 6 Block C | Sec. 7 RQ3 boundary negative control; 13-chain figures labeled smoke only | Sec. 9: unofficial mirror and mismatched chain parser/detector exclude chain counts from quantitative inference | yes |
| RQ4 | Sec. 5 distinct model families and traceable queries | Sec. 6 Block A plus implementation-smoke disclosure in Block C | Sec. 7 RQ4 qualitative model-family boundary; aggregate 13/13 record only | Sec. 8 Q3 and Sec. 9: no executable/per-item baseline and no unified model | yes |
