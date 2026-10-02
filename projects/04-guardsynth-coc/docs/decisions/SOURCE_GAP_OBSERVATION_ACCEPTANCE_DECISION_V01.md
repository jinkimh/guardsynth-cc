# Source-gap observation acceptance

- project_id: `guardsynth-coc`
- Date: 2026-09-28
- Authority: user approval to preserve existing reviews and proceed without a full repeat survey
- Governing plan: [01_RESEARCH_PLAN_V02.md](../plans/01_RESEARCH_PLAN_V02.md)
- Prior design: [development dataset and review](../designs/PAPER1_DEVELOPMENT_DATASET_AND_GAP_REVIEW_DESIGN_V01.md)

## Decision

Accept the 30 completed source-curation responses as reviewer observations, not action gold,
world-complete applicability judgments, verified geometry, or main-training admission.
Keep uploaded review and draft bytes, packet identity, timestamps and choices unchanged.
Observation review completion and formal source acceptance are separate statuses.

The legacy NOT_APPLICABLE choice conflated no visible evidence and actual nonapplicability.
Do not globally map old answers to either interpretation or use them to discharge obligations.
Keep the raw choice; assign UNRESOLVED_LEGACY_NOT_APPLICABLE to its interpretation until
scene-specific provenance resolves it. This is a machine-side limitation, not a demand that
reviewers label every unseen signal UNKNOWN or repeat all questionnaires.
TRUE/FALSE remain reported observations of the stated predicate, not verified labels, temporal
activation/release transitions, complete hazard absence, or ENTER_ZONE permission.
UNKNOWN and CONFLICT stay distinct. CoC is a claim to check, never the ground-truth answer.

## Explicit clarification from this conversation

- Speaker: submitting user (review JSON reviewer_id: Jin Hyun Kim; no new identity authentication)
- Date: 2026-09-28; exact message time not recorded
- Scene: list position 18 / candidate #59
- candidate_digest: `candidate-sha256:a832a5734000c2f4dcb712242c077189ec200b959d5529076f761b43fa27300d`
- User statement: “18번 / 후보 #59 - 현재 시점에서 신호가 보이지 않음”
- Interpretation: signal not observed at the judgment time; not proof that no applicable signal exists.
- Scope: signal only; no assertion about all signs, workers, or the whole observation window.

Record this separately; do not rewrite the submitted NOT_APPLICABLE answer, fabricate a
timestamp, or mark it as reviewer disagreement with CoC. The discrepancy needs source checking.
The user also states the remaining items were rechecked and the review is finished; this is
not blanket certification that every predicate, polygon or CoC is correct.

## Downstream work

First validate/pin the packet and complete responses, then build a machine work queue for every
scene (no failed/unknown-case exclusion). Reported confirmed target/zone plus TRUE/FALSE
pedestrian relation can enter a grounding audit queue, not an automatically accepted contract.
Other scenes enter an applicability/scope audit queue. No repeated source survey is generated.
Only a material, unresolved ambiguity that changes a proposed constraint/action may motivate a
targeted question after machine source checks. Independent action/CNL review remains a separate
requirement. Existing CoC-exposed reviewers are not silently relabelled independent.
Full source acceptance, contract/CNL admission, nominal action labels, main cohort freeze and
learning are not achieved by this intake. #18 development export and #47 abstention are unchanged.
