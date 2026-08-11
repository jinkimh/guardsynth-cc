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
[design](../../docs/designs/guard-synth-coc/GUARDSYNTH_SOURCE_AWARE_GENERATOR_V01.md)
and purpose-named CLI under `cli/pipelines/guardsynth/source_aware_generate/`.

## Source-bearing catalog

`source_catalog.py` and `fixtures/source_catalog_kr_v0_1.json` add the first
actual-source catalog boundary without replacing the legacy synthetic pilot
fixture. The Republic of Korea catalog contains 15 templates across
pedestrian/cyclist yield, stop/signals, and following/cut-in. Every rule closes
its source-claim, predicate, binder, lifecycle, and family references.

The catalog intentionally leaves a legally nonnumeric “necessary distance” as
`UNSUPPORTED`; it does not invent a vehicle bound. Its audit runner is
`cli/pipelines/guardsynth/source_catalog_audit/`.

## Real-scene source boundary

`assurance_registry.py` accepts only exact vehicle binding keys and
source-bearing profile records. It has no default vehicle values.
`source_authoring.py` converts fully grounded scene records to generator
requests and rejects missing association, geometry, verified transform, or
assurance evidence. The empty registry fixture intentionally contains no
numeric fallback.

The terminal readiness workflow is
`cli/pipelines/guardsynth/real_scene_readiness/`. Its 24 slots are an input
readiness audit, not 24 fabricated or validated scenes. See the
[P0b terminal decision](../../docs/reports/GUARDSYNTH_P0B_TERMINAL_DECISION_V1.md).

`dry_run_readiness.py` defines the successor locked 24-slot plan: eight slots
per source-catalog slice and four repeated strata. The runner under
`cli/pipelines/guardsynth/twenty_four_scene_readiness/` reports missing real
inputs and performs no synthetic scene fill.

## Label-light scene grounding

`label_light_grounding.py` consumes existing detector/tracker/map/trajectory
proposals and separates them into auto-confirmed, minimal-review, unsupported,
and conflicting paths. Automatic confirmation requires a unique candidate,
an approved calibration record, and a confidence lower bound above an explicit
policy threshold. Confidence is never promoted to observed truth.

The purpose-named runner is
`cli/pipelines/guardsynth/label_light_grounding/`. See the
[label-light design](../../docs/designs/guard-synth-coc/GUARDSYNTH_LABEL_LIGHT_GROUNDING_V01.md)
and [overall project stage](../../docs/reports/GUARDSYNTH_PROJECT_STAGE_STATUS_V1.md).

## Scene-evidence review kit

`cli/pipelines/guardsynth/scene_evidence_review/` contains a self-contained,
network-closed HTML review tool for M13 scene candidates. It explains the
method with three synthetic diagrams and four worked examples, records all
scene/rule/assurance/lifecycle evidence groups, recommends a fail-closed
decision, and exports JSON/CSV without image bytes. Human review may resolve
an association ambiguity but cannot manufacture missing geometry, transform,
rule, or vehicle-assurance sources.

See the [review UI design](../../docs/designs/guard-synth-coc/GUARDSYNTH_SCENE_EVIDENCE_REVIEW_UI_V01.md).
