# Paper-1 M16 to M17 machine preflight

- project_id: `guardsynth-coc`
- Date: 2026-09-28
- Authority: user requests nonstop work through M17, stopping only for indispensable human input
- Governing plan: [01_RESEARCH_PLAN_V02.md](../plans/01_RESEARCH_PLAN_V02.md)
- Gate: [02_PROJECT_MILESTONES.md](../plans/02_PROJECT_MILESTONES.md), M16 and M17
- Observation policy: [acceptance decision](../decisions/SOURCE_GAP_OBSERVATION_ACCEPTANCE_DECISION_V01.md)

## Machine checks

Pin the completed intake and original packet. Re-decode all thirty scenes' seven past frames
from their hash-verified videos using the existing sampling policy. Compare timestamp, frame
index, raw-pixel SHA and displayed JPEG SHA. Revalidate annotation and original CoC identities.
Normalize no human choices and interpolate no future points. Report source claims separately
from observations, including exact-event ego actions, controls and available actor anchors.
Point/polygon syntax is not semantic geometry validation; a person's centre need not lie inside
a road polygon. Do not infer contact-point overlap or metric distance from a centre point.

## Narrow conditional executable subset

Only confirmed target/zone plus reported TRUE/FALSE pedestrian occupancy produces a candidate
contract. Others remain in the denominator with a reason; this is not a judgement of data quality.
Use one pedestrian path-occupancy obligation, not a clone of #18's main-road obligation.
Rule hypothesis: if valid evidence confirms the specified person occupies/crosses the designated
entry path, prohibit entry into that area while the condition applies. This is a selected research
policy hypothesis, not a newly established legal requirement, general collision-risk model,
stopping-distance guarantee, or complete policy for the scene.

Reuse the shared versioned action-contract parser, Core lowering, SMT and CNL renderer.
In a separate, clearly conditional solver scenario, assume the reported relation is correct and
valid at offset 0. This does NOT mark observations formal_evidence_validated=true. Test base
consistency, current action alternatives, active state, unknown/invalid evidence and unobserved
prior/future freedom. No future states are observed; horizon 3 is abstract, not video frames.
Remove action_gate in a separate mutation and reproduce the unknown-entry counterexample.
The mutation is a software sensitivity test, not the actual L2 training baseline or E2 evaluation.

The CNL is a candidate translation of this narrow hypothetical contract. Its conditional entry
permission means only clearance of the declared pedestrian condition, never overall permission
in the actual scene. Road/control unknowns and legacy NOT_APPLICABLE remain outside the subset,
not discharged. Do not concatenate this text into training targets before scope and fidelity review.
No new world-complete contract, action gold, new training export or source acceptance is created.

## Independent review preparation and M17 boundary

Prepare neutral ACTION packet drafts for the same confirmed zones and exact same past frames;
no CoC, source answers, target points, generated CNL or solver outputs. They are provisional
development task audits, not main-study gold. Coordinator must accept task/zone/input adequacy
before assignment; two independent reviewers and separate disagreement adjudication remain
required. UNJUDGEABLE is valid and stays in the denominator. Known CoC/source-exposed reviewers
cannot supply independent action gold for these scenes. ACTION precedes any CNL/source exposure.
Prepare separate CNL packets with exact generated English, contract and query-free Core, not
solver verdicts. No prefilled answers; identity/expertise/independence needs human coordination.

Keep all 32 development candidates in group/exposure ledgers, retaining #18's prior development
export and #47's abstention. All 98 previously audited candidate clips are conservatively excluded
from future held-out tests. Upstream train/val is not a paper split. Main N, fresh held-out cohort,
independent labels, reliability, semantic fidelity and actual intrinsic comparisons are not fabricated.
M17-S01/S02 can gain preparatory software evidence but cannot close until their human gates pass.
