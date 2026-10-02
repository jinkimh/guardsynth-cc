# EBLC Core → bounded SMT pipeline

This public pipeline validates a typed EBLC Core v0.1 JSON model, checks
unit/frame/time references, lowers it to project-local Z3 5.0.0, runs each
bounded query in isolation, and exports replayable SMT-LIB plus symbol/source
maps.

```bash
python3 -m cli.pipelines.eblc.core_smt_compile.run \
  --run-id core-smt-2026-08-08-v1
```

The default model is the synthetic P0b pedestrian conflict-zone fixture. SAT
means a bounded witness exists and UNSAT means no witness exists within this
encoding and horizon. Neither result is a traffic-law or vehicle-safety proof.
