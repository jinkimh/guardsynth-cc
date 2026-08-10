# EBLC-P0b schema-driven vertical slice

## Scope

`EBLC-P0B-001` implements a schema-driven pedestrian conflict-zone contract, a canonical interpreter, a separately coded runtime target, a bounded target, translation validation, and controlled BCV mutations. The rule and vehicle profile are explicitly synthetic. This package does not implement traffic law, production perception, or a real-vehicle safety guarantee.

## Semantic authority

- `schemas/*.json` defines syntax only.
- `types.py` defines immutable representations only.
- `semantics.py` is the sole operational source of truth.
- `runtime_monitor.py` independently reimplements the target and does not import canonical semantic functions.
- `z3_bounded_checker.py` uses the project-local Z3 5.0.0 selected by the P0b CLI. It encodes fixed traces and the four bounded queries with `z3.Solver`. `finite_state_enumerator.py` remains an explicitly named non-SMT fallback when Z3 is unavailable.

The canonical transition meaning is:

```text
INACTIVE + TRUE                         -> ACTIVE
INACTIVE + UNKNOWN                      -> CANDIDATE / REVIEW_REQUIRED
ACTIVE|MAINTAINED|REACTIVATED + TRUE    -> MAINTAINED
live + one fresh FALSE                  -> MAINTAINED
live + sourced consecutive FALSE count  -> RELEASED
RELEASED + TRUE                         -> REACTIVATED
scope/version expiry                    -> EXPIRED
live + fresh UNKNOWN                    -> MAINTAINED only with approved fallback
CONFLICT                                -> CONFLICT verdict; no truth-value closure
```

Activation is visible as `ACTIVE` in the same observation step after binding. `RELEASED` permits reactivation; `EXPIRED` does not. A boundary equality at the stop position is admissible and a value greater than it by more than `1e-9` violates the invariant. Fact age above the smaller fact/PredicateSpec freshness budget fails to `UNKNOWN`. A `CLAIMED` CoC fact also evaluates as `UNKNOWN`; it is never promoted to `OBSERVED`.

Trace verdict precedence is `CONFLICT > UNSUPPORTED > REVIEW_REQUIRED > VALIDATED`. Trace acceptance is a bounded contract-conformance result: it requires no invariant/deadlock violation and excludes `CONFLICT`/`UNSUPPORTED`; it is not a safety verdict. Hard physical/system classes and service/preference classes use an explicit partial `overrides` relation rather than scalar weights.

Before lifecycle execution, schema/semantics v0.2 applies a fail-closed input
contract. Non-finite JSON/profile/scene values, empty traces, decreasing frame
timestamps, invalid numeric ranges, and invalid bound-contract numerics produce
`UNSUPPORTED` with reason codes such as `NONFINITE_SCENE_VALUE`, `EMPTY_TRACE`,
or `NONMONOTONIC_TIMESTAMPS`. The bound-contract schema requires all numeric
parameters actually consumed by the monitors. Canonical, runtime, Z3, and the
enumerator encode these checks separately so a shared validator cannot mask a
translation defect.

## Layout

- `../../src/guard_synth_eblc/`: maintained public library, schemas, and fixtures
- `../../src/guard_synth_eblc/adapters/`: synthetic and restricted-derived input adapters
- `../../cli/pipelines/eblc/p0b_schema_bcv/`: public P0b evaluation interface
- `../../cli/pipelines/eblc/restricted_scene_grounding/`: restricted adapter interface
- `../../tests/guard_synth_eblc/`: maintained unit, integration, and regression tests
- remaining Python modules: historical import compatibility wrappers only

The data-gap pivot subsequently extended `real_scene_adapter.py` with a read-only join over existing derived obstacle events and recorded ego futures. It emits hashed partial ContextGraphs only. Dynamic VRU occupancy is a geometric zone, not a legal crosswalk, and ambiguous target association or missing vehicle assurance remains explicit.

## Reproduce

From the project root:

```bash
python3 -m unittest experiments.eblc_pilot.test_pilot -v
python3 -m unittest discover -s tests/guard_synth_eblc -p 'test_*.py' -v
python3 -m cli.pipelines.eblc.robustness_audit.run --run-id <new-run-id>
python3 -m cli.pipelines.eblc.p0b_schema_bcv.run --run-id <new-run-id>
runtime/alpamayo/ar1_venv/bin/python -m cli.pipelines.eblc.restricted_scene_grounding.run --run-id <new-run-id>
```

The runner refuses to overwrite an existing run directory. Public synthetic results go to `artifacts/results/public/eblc-p0b-001/`; restricted asset-readiness results go to `artifacts/results/restricted/eblc-p0b-001/` without copying raw input.

The previous `python3 -m experiments.eblc_p0b...` entry points remain available
only to reproduce earlier commands. New automation should use `cli/pipelines/`.

The robustness audit is deliberately broader than the locked success suite.
It reports invalid-input gaps as gaps instead of changing their expected
outcomes to match the implementation.
