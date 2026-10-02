# Development dataset export and missing-source review

- project_id: `guardsynth-coc`
- Date: 2026-09-08
- Authority: user request to create the data needed for training
- Governing plan: [01_RESEARCH_PLAN_V02.md](../plans/01_RESEARCH_PLAN_V02.md)
- Admission basis: [conditional development policy](../decisions/PAPER1_CONDITIONAL_DATA_ADMISSION_DECISION_V01.md)

## Development export boundary

The prior conditional-admission run is immutable and did not authorize export by itself.
This downstream step, explicitly requested by the user, permits an actual local development
SFT dataset for its one admitted scene, #18. It does not change main-study admission.
Export L0 (original CoC + independently reviewed development action) and L3 (the same plus
the exact reviewed English CNL). These are two arm records of ONE scene, not two scenes.
No invented L1/L2 provider, nominal label, train/test split or main-study approval is added.

Revalidate prior input/output identities and regenerate the scene CNL from the contract and
effective source binding. The original CoC, reviewed action and UNKNOWN are preserved.
The last causal image used by the earlier processor preflight is copied into the dataset.
The prompt contains image, task and zone/action choices, never CoC, CNL or the selected label.
CoC, CNL and action appear only in assistant supervision. Check actual local processor encoding,
common prompts, assistant-only masks and no truncation. Main training and evaluation flags stay
false. This one-frame development input is not equivalent to the 21-frame action review;
the single reviewed label is not newly validated for the one-frame information set. It cannot
support an effect estimate or main sampling decision. No optimizer steps are part of this export.

## Source-only gap review

Prepare the 30 pending scenes, retain #18's prior answers, and do not re-request #47's
unobservable review. Keep all 32 cases in the disposition manifest. Sort prior NO_HAZARD_VISIBLE
cases first solely to investigate nominal coverage, not to label them nominal or discard failures.
Record selection priority before receiving new answers. All cases remain development-only.

Show original CoC/prior observations as reusable source context, not independent action gold.
Show up to seven native-resolution past frames spanning available context, including the last
causal frame. Sparse stills are not continuous motion evidence; UNKNOWN is valid if insufficient.
Machine target points may be shown only from exact-event keypoints, labelled as unconfirmed
annotation proposals. Never interpolate a future point or use lane masks as confirmed conflict
zones. Existing uploads contain no stored polygons for these scenes; don't infer browser history.

Ask only for missing target/zone, pedestrian relation, road-yield applicability/evidence and
concurrent control applicability/evidence. Road context can be absent; don't force every scene
into #18's merge task. Nonapplicable, unknown and conflict remain distinct. Polygon/point input
is required only when a corresponding confirmation is selected. Each condition needs a reason.
Mixed controls remain outside the executable subset until mapped and supported; no automatic
contract cloning. Partial exports must be supported, with packet identity and per-scene completion.
Answer validation preserves unknowns; intake never automatically labels actions or admits data.

## Subsequent human and machine steps

After source intake, generate ACTION packets using the confirmed zone and matched visual inputs,
without CoC/source answers/CNL/machine action. Obtain separate declared-independent actions
and adjudicate disagreements; these source reviewers are exposed, not independent action gold.
Generate actual supported CNL after source/contract validation, then request statement fidelity
review. Main four-arm providers, nominal labels, fresh tests, power/splits and matched budgets
remain required. No questionnaire asserts safety or asks reviewers to supply legal authority.
