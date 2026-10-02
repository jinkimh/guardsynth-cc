# GuardSynth EBLC public core

This package is the maintained public implementation of EBLC v0 and bounded
BCV. It contains reusable code and package resources, not experiment results.

## Boundaries

- `types.py`: representations only
- `schemas/`: public JSON syntax contracts
- `fixtures/`: public synthetic examples
- `catalog.py`, `binders.py`: source-aware catalog loading and partial binding
- `semantics.py`: canonical operational source of truth
- `runtime_monitor.py`: separately coded runtime target
- `z3_bounded_checker.py`: actual Z3 fixed-trace encoding and symbolic queries
- `finite_state_enumerator.py`: explicitly named non-SMT fallback
- `translation_validator.py`: cross-target agreement
- `mutations.py`: controlled under/overconstraint suite
- `schemas/eblc_core_ir.schema.json`: typed bounded EBLC Core v0.1 syntax
- `core_ir.py`: Core JSON parser and fail-closed sort/unit/frame/time checker
- `smt_compiler.py`: domain-neutral Core-to-Z3 lowering and SMT-LIB export
- `schemas/eblc_program.schema.json`, `schemas/eblc_program_v0_2.schema.json`,
  `program.py`: versioned evidence-bearing high-level contract syntax and
  fail-closed validation
- `elaborator.py`: high-level freshness, epistemic, lifecycle, verdict,
  invariant, stopping-bound, and progress policies to Core expressions
- `conformance.py`: generated finite-trace canonical/Core-SMT comparison
- `schemas/eblc_bundle.schema.json`, `composition.py`: high-level bundle syntax
  and canonical non-scalar multi-contract resolution
- `bundle_elaborator.py`: namespaced multi-program expansion plus composition
  clauses from high-level bundle to the existing typed Core
- `bundle_conformance.py`: canonical composition/Core-SMT finite-trace agreement
- `schemas/eblc_indexed_collection.schema.json`, `indexed_collection.py`:
  fail-closed actor–zone association collection and deterministic bundle expansion
- `schemas/derivation_spec.schema.json`, `derivation.py`: typed numeric DAG
  validation and standalone/base-Core symbolic replay
- `cnl_renderer.py`: deterministic one-way program/bundle projection to
  controlled natural language with field/evidence mapping and SHA-256 binding
- `adapters/`: source-specific input conversion; missing fields are preserved

## EBLC Core v0.1 compilation boundary

The first public compiler grammar covers typed `BOOL`, `INT`, `REAL`, and
finite `ENUM` declarations; time-varying and constant symbols; source-bearing
lifecycle clause categories; Boolean/arithmetic/comparison expressions;
`ite`; and bounded `always`, `eventually`, and `until`. Clause enforcement is
explicit (`INITIAL`, `EACH_FRAME`, `EACH_TRANSITION`, `TRACE`, or
`DECLARATIVE`).

The type checker rejects unknown variables/enums, horizon overflow, invalid
constant offsets, incompatible units, and incompatible coordinate frames. The
SMT compiler creates time-indexed symbols, enum-domain constraints, bounded
temporal expansions, and nonzero-denominator definedness constraints. It
exports common and per-query SMT-LIB, a symbol table, a clause/query source map,
and a query/witness manifest.

`DECLARATIVE` formulas are properties to be queried; they are not silently
asserted as assumptions. This avoids proving a safety property merely because
the same property was inserted into the base model.

The locked low-level example is `fixtures/eblc_core_p0b.json`, and the Core CLI
is `cli.pipelines.eblc.core_smt_compile`. The high-level example
`fixtures/eblc_program_p0b.json` contains policy and evidence but no Core formula
AST; `elaborator.py` generates those formulas. The v0.2 example
`fixtures/eblc_program_p0b_v0_2.json` additionally embeds its executable typed
numeric derivation. Both use `cli.pipelines.eblc.program_conformance`.

The generated suite compares post-step lifecycle, clear counter, verdict,
entry/speed/deadlock violations, and progress permission against the canonical
interpreter. It includes four-valued truth products, epistemic/freshness cases,
binding failures, and numeric boundaries. The elaborator is derived from the
canonical specification, so this is translation evidence rather than an
independent safety oracle.

The purpose-named `cli.pipelines.eblc.scenario_validation` pipeline adds a
44-case unit/integration matrix over negative schema/program inputs, lifecycle
policy variants, and before/equal/after numeric boundaries. Policy and boundary
traces are compared across canonical, separately coded runtime, bounded Z3,
Core-SMT, and the explicitly non-SMT enumerator. Binary-float execution uses a
`1e-15` representation-noise guard in addition to, and much smaller than, the
semantic `1e-9` epsilon so an ideal-real equality is not changed by subtraction
roundoff.

Program v0.1 remains supported as the legacy single-contract unit, and program
v0.2 is the current typed-derivation unit. Bundle v0.1 composes two or more
programs of either version over a finite action domain. Priority is a sourced partial order:
`HARD > SERVICE > PREFERENCE`, augmented by acyclic explicit contract
overrides. It is never compiled to a scalar weight. Selected contracts jointly
restrict actions by set intersection. An empty intersection among at least two
selected hard contracts is `CONFLICT`; another empty intersection is
`REVIEW_REQUIRED`. Lower-priority contracts cannot override higher-priority
contracts, and equal-priority ambiguity is preserved unless explicitly
resolved.

The bundle elaborator namespaces each single-program Core model and generates
selected-contract, admissible-action, composition-verdict, and false-deadlock
clauses. Therefore the public path is now high-level bundle → typed Core v0.1 →
bounded Z3 SMT. The language still does not define unbounded temporal semantics,
continuous/hybrid dynamics, quantifiers, arbitrary user-defined derivation
operations, or a complete natural-language-to-EBLC generator.

## Typed derivation compiler v0.1

The companion `eblc-derivation-v0.1` input replaces executable free-form
operation strings with a finite typed DAG. It supports sourced numeric values,
references to existing Core variables, `ADD`, `SUB`, `MUL`, `DIV`, `NEG`,
`MIN`, and `MAX`, and explicit output-to-Core bindings. Unknown references,
cycles, invalid arity/evidence, incompatible units/frames, time-varying output
errors, and division definedness fail closed.

For the synthetic P0b companion example the compiler explicitly replaces the static
`bind_stop_position` clause with `0.0 m - 1.5 m = -1.5 m`; Z3 returns the exact
rational witness `-3/2`, and all eight locked canonical/Core-SMT traces remain
aligned.

`eblc-program-v0.2` now embeds the typed derivation directly. Its public fixture
expands stop position, epsilon-adjusted/clamped speed, response distance,
squared speed, twice-deceleration, braking distance, and total stopping
distance in one source-bearing graph. The generated speed-violation clause
consumes the `stopping_distance` output instead of rebuilding the formula in
Python. At adjusted speed `6 m/s`, Z3 returns exact witnesses
`stop_position = -3/2 m` and `stopping_distance = 9 m`. Program v0.1 remains
supported unchanged. For v0.2 bundles, each derivation declaration, output
clause, and variable reference is contract-namespaced before Core→SMT lowering.
Division definedness is preserved per contract and frame. In the locked
two-contract witness Z3 independently returns stopping distances `9 m` and
`3 m`, with 18 nonzero-denominator assertions over two contracts and nine
frames. Free-form operation text is never executed or guessed.

## Indexed actor–zone collection v0.1

The indexed collection references one validated program v0.2 template and
supplies two or more grounded instances. Every `BOUND` instance requires a
target, conflict zone, zone-geometry evidence, coordinate-transform evidence,
and a sourced zone-entry quantity with matching unit/frame. Expansion rewrites
the template binding and typed `zone_entry_x` symbol before ordinary bundle
namespacing and Core→SMT compilation.

`AMBIGUOUS`, `UNSUPPORTED`, and `CONFLICT` instances carry candidates and reason
codes but no bound geometry. The compiler never drops only the unresolved
instance: the complete collection abstains with precedence
`CONFLICT > UNSUPPORTED > REVIEW_REQUIRED`. The locked two-actor/two-zone
fixture produces exact stop positions `-3/2` and `21/2`; an ambiguous target
probe produces `REVIEW_REQUIRED` and no bundle.

## Fail-closed input contract

EBLC schema v0.2 rejects non-finite JSON numbers and requires every numeric
parameter consumed by runtime semantics, including the derivation DAG,
predicate freshness, braking response, deceleration, and position uncertainty.
The binder returns `UNSUPPORTED` for non-finite scene or vehicle-profile input.

The canonical, runtime, Z3, and enumerator targets independently reject empty
traces, decreasing frame timestamps, non-finite/range-invalid scene values, and
invalid bound-contract numerics. They return `UNSUPPORTED` with an explicit
reason code and do not advance lifecycle state. Target implementations remain
separate; agreement is tested with the same locked negative fixtures.

The package does not assert traffic-law correctness or real-vehicle safety.
The NVIDIA-derived adapter code is publishable, but its input and result data
remain restricted and are never packaged under `src/`.

## v0.2 scoped release boundary

EBLC v0.2 is feature-complete as a scoped release candidate for bounded
discrete contracts: evidence and observability, lifecycle, typed derivation,
non-scalar composition, indexed actor–zone expansion, Core/SMT translation,
BCV, and deterministic CNL projection. The structured program/bundle remains
the execution authority; `EBLC-CNL-EN-v0.1` is only a one-way model-facing
view and never supplies missing values or evidence.

General exception algebra, quantifiers, unbounded/continuous dynamics and the
source-aware natural-language/CoC generator are not silently folded into v0.2.
The first structured generator slice now lives separately in `projects/04-guardsynth-coc/src/guard_synth`;
free-form CoC parsing remains future work. See the
[language specification](../../docs/specifications/eblc/EBLC_LANGUAGE_SPEC_V02.md),
[user guide](../../docs/guides/eblc/EBLC_USER_GUIDE_V02.md), and
[traceability matrix](../../docs/reports/EBLC_REQUIREMENT_TRACEABILITY_V02.md).
