# EBLC indexed collection compile pipeline

Expand a source-bearing actor–conflict-zone collection into a multi-contract
EBLC bundle, namespaced Core, SMT-LIB, and exact Z3 witnesses.

```bash
python3 -m cli.pipelines.eblc.indexed_collection_compile.run \
  --run-id <new-run-id>
```

Use `--collection path/to/collection.json` for another schema-valid collection.
An unresolved association is not partially compiled; the result records
`REVIEW_REQUIRED`, `UNSUPPORTED`, or `CONFLICT` with reason codes.
