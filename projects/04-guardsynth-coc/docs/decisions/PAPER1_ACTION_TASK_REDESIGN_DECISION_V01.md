# Paper-1 action task redesign decision

- project_id: `guardsynth-coc`
- Date: 2026-09-28
- Authority: user requests next work after identifying answer cueing in the yellow-zone task
- Governing plan: [01_RESEARCH_PLAN_V02.md](../plans/01_RESEARCH_PLAN_V02.md)
- Status: old 16-scene ACTION task SUSPENDED; replacement task NOT_FROZEN

## What is retained and what is stopped

Retain the completed 30 source observations, drawn geometry, conditional EBLC/CNL outputs,
solver checks, historical one-scene export and all immutable runs. Do not solicit another full
source survey. Suspend the 16-scene yellow-zone ACTION questionnaire and its coordinator preview
on their existing portal URLs. Allow backup of the existing browser draft without modifying it.
Saved answers, if supplied, remain historical development feedback, not independent main gold.
No already-open/offline page can be remotely revoked; request reload and stop new responses.

This supersedes only the dispatch/task-neutrality assumption in the pinned
[M17 preflight design](../designs/PAPER1_M17_MACHINE_PREFLIGHT_DESIGN_V01.md).
Its source replay and conditional solver results remain valid within their original assumptions.
Jonh's nomination/nonexposure report is retained, but assignment is suspended. Recheck actual
exposure before any replacement review; do not assume the previous declaration still holds.

## Defect and correction

The source questionnaire asked for an area where ego's entry path and a target's motion could
meet, using CoC and prior observations. Passing that same polygon as a neutral intended-entry
region conflates a source-curated conflict region with an independently specified task route.
Masking only text answers does not remove this potential cue. Hiding the polygon alone does
not fix event selection, route ambiguity, or the missing normal-progress reference.

Audit actual labels before claiming all sixteen are hazards. Source FALSE means only the
reviewer's reported pedestrian relation, not overall permission, verified clearance of other
controls, or an independent normal-action label. Keep TRUE/FALSE/UNKNOWN/NOT_APPLICABLE and
all candidates in the denominator. Neither observed driving nor solver SAT is action gold.

## Replacement task prerequisites

1. Freeze task context independently of hazard labels/CNL: decision time, intended maneuver,
   reference horizon and evidence provenance. A logged route must have been available by t0.
   Full-clip ego-action annotation, future trajectory, braking, current speed or an annotator's
   hazard polygon cannot be silently promoted to pre-decision intended route.
2. If authentic route input is unavailable, choose explicitly between acquiring it and a
   controlled, stated-maneuver benchmark. The latter is a new hypothetical task, not recovered
   driver intent, and requires approval, feasibility checks and equal input to all learning arms.
   Do not automatically convert DrivingInLane to STRAIGHT or Stop to DEFER gold.
3. Screen progress, hold and unjudgeable opportunities without manufacturing balanced labels.
   Source FALSE cases are a screening queue only. Check other controls and task applicability;
   missing/NOT_APPLICABLE evidence is not automatic clearance. Freeze selection before labels.
4. ACTION reviewers receive unmarked causal frames and the frozen task context, not source
   answers, CoC, generated constraints or outcomes. Preserve UNJUDGEABLE. Do not ask a new
   review until the task is interpretable and its provenance is accepted.
5. Evaluate violation and normal-progress preservation separately, report abstention/coverage
   on the same denominator, and include an always-defer diagnostic. Source annotation balance
   alone is not evaluation balance. Keep clip grouping/exposure exclusions and test lock.

No replacement main N, class quota or frame horizon is invented here. One available reviewer
supports development audit only; the existing formal two-reviewer/reliability gates are not
weakened. M16/M17 remain PARTIAL; M18 training/M20 effectiveness remain downstream.

## Immediate machine work and human boundary

Audit all 32 linked candidates and 30 observations against original annotation hashes. Inventory
local route-like metadata and distinguish observed maneuver from pre-decision route evidence.
List the eight reported pedestrian-clear candidates if confirmed by the audit, preserving their
other-control gaps. Report only the inspected scope, not absence from the entire upstream dataset.
No independent visual route validation is claimed. After this audit, a human must supply route
provenance or approve a clearly hypothetical task definition before new ACTION collection.
