# EBLC typed derivation compile pipeline

Compile a typed, evidence-bearing numeric derivation DAG into an existing
high-level EBLC program's Core model and then into replayable Z3 SMT-LIB.

```bash
python3 -m cli.pipelines.eblc.derivation_compile.run \
  --run-id typed-derivation-2026-08-09-v1
```

Use `--spec` and `--program` for other schema-valid public inputs. Free-form
operation strings are not executed or guessed.
