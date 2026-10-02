# Generated artifacts

New output is owner-scoped:

```text
projects/<project-id>/<public|restricted|intermediate>/<experiment-id>/<run-id>/
platforms/<platform-id>/<public|restricted|intermediate>/<experiment-id>/<run-id>/
```

Maintained source code never belongs here. Final runs are immutable and must include their run
manifest and result record; reruns use a new run ID.

`results/` and `intermediate/` are immutable pre-v3 history. They remain in place because moving
them would invalidate manifests and embedded reproduction paths. Their current owner mapping is
recorded in [`LEGACY_OWNERSHIP.json`](LEGACY_OWNERSHIP.json); no new run may be written there.
