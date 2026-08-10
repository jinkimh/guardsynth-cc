# EBLC scenario validation

Runs the public EBLC implementation through schema/program negative tests,
lifecycle policy variants, numeric boundary matrices, independent runtime/Z3/
enumerator agreement, Core-SMT conformance, robustness regression, and P0a
compatibility regression.

```bash
python3 -m cli.pipelines.eblc.scenario_validation.run --run-id <new-run-id>
```

The output is a deterministic synthetic software-validation artifact. It is
not evidence of legal correctness or vehicle safety.
