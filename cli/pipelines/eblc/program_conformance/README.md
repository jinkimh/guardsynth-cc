# High-level EBLC elaboration and conformance

This public pipeline performs:

```text
evidence-bearing EBLC program
  → semantic elaborator
  → typed bounded Core IR
  → generic Z3 compiler
  → generated finite-trace comparison with the canonical interpreter
```

Run from the repository root:

```bash
python3 -m cli.pipelines.eblc.program_conformance.run \
  --run-id elaboration-conformance-2026-08-08-v1
```

The default input is synthetic and the agreement result is not an independent
safety oracle or a vehicle-safety proof.

The same pipeline accepts the v0.2 fixture with an embedded typed stopping
derivation:

```bash
python3 -m cli.pipelines.eblc.program_conformance.run \
  --program src/guard_synth_eblc/fixtures/eblc_program_p0b_v0_2.json \
  --run-id <new-run-id>
```
