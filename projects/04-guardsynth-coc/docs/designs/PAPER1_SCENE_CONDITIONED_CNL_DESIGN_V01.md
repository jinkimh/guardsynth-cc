# Scene-conditioned CNL generation and claim review

- project_id: `guardsynth-coc`
- Date: 2026-09-08
- Scope: M14-R01-C5 observation → executable event → bilingual scene instructions; M16 review pending.

The prior renderer describes general contract semantics. Its translations/A-B comparison do
not instantiate the scene observation. Preserve those runs as software evidence, not completed
scene-specific CNL validation. The new project-owned renderer receives the parsed two-obligation
contract AND the reviewed event binding. It reuses the platform Core compiler and solver.

Generate four typed statements: review-attributed pedestrian observation, road observation
(including UNKNOWN/invalid/conflict), current entry instruction and conditional reassessment.
Never fill missing facts from arbitrary solver witnesses, future frames, CoC assertions or the
independent ACTION answer. Every sentence has binding paths, Core IDs and support-query IDs.
Observed facts are input assumptions, not facts proved by SAT. Instruction validity is conditional
on those assumptions and the explicit research policy, not law or physical safety.

Check satisfiable premises, allowed/forbidden current actions, contradictions of each observation,
review flag, and conditional next-decision clearance/entry/defer. Both prior road states remain
possible. Future clearance tests are hypothetical, not recorded future observations. Text scope
is the current decision and reassessment condition, not equivalence of the entire lifecycle.
UNKNOWN must never become absence of traffic. All-clear must permit but never force entry.

The dedicated scene screen displays the full generated Korean text first, source-reviewed quotes
and actual past-only frames with the confirmed t0 polygon, followed by four concrete claim checks.
Evidence statements, policy-derived actions and future conditions are labelled separately.
This is informed scene-CNL review, not blinded ACTION annotation or independent scene gold.
Answers indicate supported / unsupported-or-distorted / unjudgeable; no answers are preselected.
Respondents declare involvement in the source curation or generator. Record involved review
without counting it as independent. Keep existing ACTION submission intact, and record this
packet under a separate version/kind. No identity or expertise is authenticated by the software.

Expose no hashes as prose. Preserve full source and clause mapping in artifacts. A CoC+CNL
preview may be generated, explicitly blocked from training export: independent semantic review,
main split/eligibility, full source and independent-gold linkage remain unresolved. No VLM
training, paper effect or M16 closure is claimed. Korean review does not independently certify
the English training text or the general language compiler.
