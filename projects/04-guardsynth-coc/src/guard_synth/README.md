# GuardSynth public generation layer

`guard_synth` sits before the frozen EBLC execution language. Its first public
interface combines a catalogued RuleTemplate and PredicateSpec with a grounded
ContextGraph, vehicle assurance profile, and explicit compiler/composition
policy to produce an EBLC v0.2 program template and indexed collection.

The generator is deterministic and fail closed:

- CoC evidence remains `CLAIMED` and cannot activate a contract.
- Unknown evidence references fail request validation.
- Missing vehicle profile, geometry, transform, zone entry, unit, or frame
  produces `UNSUPPORTED` and no collection.
- Ambiguous target/zone or claim-only hazard produces `REVIEW_REQUIRED`.
- Conflicting evidence or duplicate target-zone binding produces `CONFLICT`.
- Only a source-complete request produces an indexed collection.

The current v0.1 slice uses catalog references and structured input. It does
not parse free-form CoC or natural-language rules. See the
[design](../../docs/designs/GUARDSYNTH_SOURCE_AWARE_GENERATOR_DESIGN_V01.md)
and purpose-named CLI under `projects/04-guardsynth-coc/pipelines/cli/source_aware_generate/`.

## Source-bearing catalog

`source_catalog.py` defines a jurisdiction-neutral catalog boundary. A catalog path must be
selected explicitly; there is no implicit country default. Each catalog declares its ISO-style
country code and allowlisted official-source hosts. `fixtures/source_catalog_kr_v0_1.json` is the
first historical instance, not the project-wide scope. The Republic of Korea instance contains 15 templates across
pedestrian/cyclist yield, stop/signals, and following/cut-in. Every rule closes
its source-claim, predicate, binder, lifecycle, and family references.

The catalog intentionally leaves a legally nonnumeric “necessary distance” as
`UNSUPPORTED`; it does not invent a vehicle bound. Its audit runner is
`projects/04-guardsynth-coc/pipelines/cli/source_catalog_audit/`.

## Real-scene source boundary

`assurance_registry.py` accepts only exact vehicle binding keys and
source-bearing profile records. It has no default vehicle values.
`source_authoring.py` converts fully grounded scene records to generator
requests and rejects missing association, geometry, verified transform, or
assurance evidence. The empty registry fixture intentionally contains no
numeric fallback.

The terminal readiness workflow is
`projects/04-guardsynth-coc/pipelines/cli/real_scene_readiness/`. Its 24 slots are an input
readiness audit, not 24 fabricated or validated scenes. See the
[P0b terminal decision](../../docs/reports/GUARDSYNTH_P0B_TERMINAL_DECISION_REPORT_V01.md).

`dry_run_readiness.py` defines the successor locked 24-slot plan: eight slots
per source-catalog slice and four repeated strata. The runner under
`projects/04-guardsynth-coc/pipelines/cli/twenty_four_scene_readiness/` reports missing real
inputs and performs no synthetic scene fill.

## Label-light scene grounding

`label_light_grounding.py` consumes existing detector/tracker/map/trajectory
proposals and separates them into auto-confirmed, minimal-review, unsupported,
and conflicting paths. Automatic confirmation requires a unique candidate,
an approved calibration record, and a confidence lower bound above an explicit
policy threshold. Confidence is never promoted to observed truth.

The purpose-named runner is
`projects/04-guardsynth-coc/pipelines/cli/label_light_grounding/`. See the
[label-light design](../../docs/designs/GUARDSYNTH_LABEL_LIGHT_GROUNDING_DESIGN_V01.md)
and [overall project stage](../../docs/reports/GUARDSYNTH_PROJECT_STAGE_STATUS_REPORT_V01.md).

## Scene-evidence review kit

`projects/04-guardsynth-coc/pipelines/cli/scene_evidence_review/` contains a self-contained,
network-closed HTML review tool for M13 scene candidates. It explains the
method with three synthetic diagrams and four worked examples, records all
scene/rule/assurance/lifecycle evidence groups, recommends a fail-closed
decision, and exports JSON/CSV without image bytes. Human review may resolve
an association ambiguity but cannot manufacture missing geometry, transform,
rule, or vehicle-assurance sources.

See the [review UI design](../../docs/designs/GUARDSYNTH_SCENE_EVIDENCE_REVIEW_UI_DESIGN_V01.md).

## Recorded-scene simulation projection

`simulated_scene_dry_run.py` keeps the recorded rig and the simulated vehicle
as distinct bindings. It permits the eight source-linked scene/rule fields to
drive an explicitly `SIMULATION_MODEL_SPECIFICATION` profile, but it does not
close the recorded vehicle's missing assurance field. The corresponding CLI is
`projects/04-guardsynth-coc/pipelines/cli/simulated_scene_dry_run/` and its boundary is defined
in the [simulation projection design](../../docs/designs/SIMULATED_SCENE_ASSURANCE_PROJECTION_DESIGN_V01.md).

## CoC-conditioned proposal front-end

`coc_conditioned_frontend.py` starts M14 without changing EBLC semantics. It
keeps CoC text as a hashed `CLAIMED` input, emits typed lexical concepts, and
combines them with four-valued scene predicates, explicit scene semantic tags,
and the source-bearing catalog. Missing predicates, stale/claimed facts,
conflicts, ambiguous target-zone bindings, unsupported jurisdiction, and
nonnumeric legal bounds remain fail-closed proposal outcomes.

The v0.1 output is a reviewable proposal. Graph, deterministic BM25, and a
caller-supplied dense retrieval interface are available. A source-separated
materializer carries the supported crosswalk proposal through GuardSynth,
single-contract EBLC, Core, and bounded Z3; legal/CoC references cannot source
the numeric stopping policy. General NLP, production dense retrieval, empirical
accuracy, and operational policy mappings for the other slices remain outside
the scoped M14 software completion. See the
[design](../../docs/designs/GUARDSYNTH_COC_CONDITIONED_FRONTEND_DESIGN_V01.md)
and CLI under `projects/04-guardsynth-coc/pipelines/cli/coc_conditioned_frontend/`.
