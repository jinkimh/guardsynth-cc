# EBLC composition compile pipeline

Compile a high-level multi-contract EBLC bundle through typed Core to bounded
SMT, export replayable artifacts, and run canonical/Core-SMT composition
agreement scenarios.

```bash
python3 -m cli.pipelines.eblc.composition_compile.run \
  --program-version eblc-program-v0.2 \
  --run-id <new-run-id>
```

The generated public example defaults to program v0.2 and preserves its typed
stopping-distance derivation through contract namespacing, Core, SMT-LIB, and
Z3. Use `--program-version eblc-program-v0.1` for the compatibility example.
Pass `--bundle path/to/bundle.json` to compile another schema-valid bundle.
Custom bundles are compiled and replayed; the built-in synthetic scenario
matrix remains the regression oracle and is not a vehicle-safety claim.
