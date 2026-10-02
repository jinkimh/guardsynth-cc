# EBLC v0.2 release candidate

This pipeline freezes the scoped EBLC v0.2 language/tooling baseline. It
renders program and bundle fixtures to deterministic controlled natural
language, exports field-to-clause maps, executes the complete public regression
suite, and records the supported/deferred requirement boundary.

```bash
python3 -m cli.pipelines.eblc.release_candidate.run
```

The CNL output is a one-way prompt projection. Structured EBLC remains the
execution authority.
