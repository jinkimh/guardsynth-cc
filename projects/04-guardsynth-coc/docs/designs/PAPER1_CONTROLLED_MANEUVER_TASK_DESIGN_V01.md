# Paper-1 controlled maneuver task: development preparation

- project_id: `guardsynth-coc`
- Date: 2026-09-28
- Authority: user explicitly approved a stated hypothetical maneuver task after the route audit
- Governing plan: [01_RESEARCH_PLAN_V02.md](../plans/01_RESEARCH_PLAN_V02.md)
- Previous decision: [ACTION suspension](../decisions/PAPER1_ACTION_TASK_REDESIGN_DECISION_V01.md)
- Status: WITHDRAWN_UNEXECUTED; not the primary study; producer disabled
- Superseded by: [original-context preservation](../decisions/PAPER1_ORIGINAL_CONTEXT_PRESERVATION_DECISION_V01.md)

The preliminary approval above was followed by the user's explicit rejection of changing the
original CoC task. The following text is an unexecuted proposal retained for history, not an
instruction to generate hypothetical routes, request its pilot or replace the main experiment.

## Claim and question

The input stipulates a maneuver. It does not recover the recorded driver's intent. We evaluate
visual action selection under that instruction, not actual vehicle control or whole-trip safety.
Future ACTION question: given this explicitly hypothetical route and frames available up to t0,
should ego begin/continue progressing on that route at the next qualitative decision, hold
progress, or is the information insufficient? PROCEED does not mean accelerate, complete the
whole maneuver, or a guarantee of safety. HOLD does not prescribe abrupt braking.
This is a one-decision qualitative endpoint, not an invented metric time horizon or rollout.

The two draft instructions are:

- STRAIGHT: proceed forward from the current lane without taking a left/right turn or changing
  lanes. A road that bends with no identifiable straight continuation may be ambiguous.
- RIGHT_TURN: take the visible right-turn branch immediately ahead. If none is visible, there
  are several ambiguous branches, or ego already completed the turn, do not invent a route.

## Outcome-independent draft construction

Reuse the thirty existing causal-frame sequences only as development inputs; retain the other
two candidates as prior-development/prior-unobservable in the original 32-candidate denominator.
Do not select just the old sixteen pedestrian hypotheses or the eight reported-clear scenes.
The cohort remains source-selected/exposed; this does not make it a representative main cohort.

Choose one draft maneuver per clip by SHA256 of `controlled-maneuver-v0.1|<clip_id>`:
even first byte selects STRAIGHT, odd selects RIGHT_TURN. This fixed design convention is not
a learned route predictor, observed-intent extraction, class balancing or causal randomization.
Changing source answers, polygons, CoC, actions or solver verdicts cannot change assignment.
Rejects remain in the denominator; no reroll or silent alternate maneuver to obtain desired labels.

Initial usability preview: sort task IDs and take the first three distinct clips. Three is only
a bounded interface/task-interpretability check, not main N, power evidence or three action labels.
Do not ask all thirty to repeat their old source survey. Remaining draft contexts stay undispatched.

## Scene fit before ACTION

Show the coordinator unmarked original causal frames plus the assigned instruction. Ask only:
is the specified route identifiable from these frames? CLEAR, NO_VISIBLE_ROUTE or AMBIGUOUS,
with a short route description/reason. CLEAR requires a neutral landmark description so that
another person can identify the same continuation/branch. Person positions and hazard polygons
are not route anchors. A pedestrian or red light obstructing a route does not make the route
nonexistent: route identifiability is distinct from permission to proceed.

No default fits, action answers, route descriptions, independence declarations or completion
timestamps are manufactured. Save/restore drafts under a new packet identity; never import old
ACTION or source answers into this form. Validation means well-formed coordinator feedback only.
Before scene-context freeze, inspect descriptions for answer cues and unresolved geometry or
time ambiguity. Even CLEAR does not automatically authorize ACTION dispatch or training.

Coordinator exposure is recorded separately; the coordinator cannot subsequently supply
independent action gold for that task. Recheck Jonh's exposure before a new assignment.
The new context packet must be frozen before ACTION; all ACTION must precede CNL/source exposure.
One reviewer still provides only development evidence, not the unchanged formal two-reviewer gate.

## Rebinding and fair comparison

A different stipulated route can change target relevance and constraint applicability. Existing
polygons, TRUE/FALSE, contracts, solver runs, CNL, labels and the #18 export are historical results,
not automatically portable to the new task. Require explicit same-context evidence binding and
fresh applicability validation before reusing any of them. No old policy-driven DEFER becomes gold.

Give identical frozen route text, frame selection and task question to every L0–L3 arm and the
independent evaluator. Keep original CoC immutable: incompatible actual-maneuver CoC must be
flagged/excluded or handled by a separately approved transformation, not silently rewritten or
contradictorily concatenated. This cross-context consistency gate is pending, not waived.

Freeze cohort/splits/labels and normal-progress plus hold/abstention coverage before main training.
Retain prior exposed-clip exclusions, report coverage and always-hold diagnostics, and evaluate
normal-progress preservation as well as violations. No invented balanced action labels, main N,
new held-out cases, completed training or M16/M17 closure follows from this preparation.
