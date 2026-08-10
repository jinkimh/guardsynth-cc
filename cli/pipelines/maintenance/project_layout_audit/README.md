# Project layout audit

Run from the repository root:

```bash
python3 -m cli.pipelines.maintenance.project_layout_audit.run \
  --run-id layout-v2-2026-08-09-v4
```

The runner refuses to overwrite an existing result and writes only to
`artifacts/results/public/project-layout-refactor-001/<run-id>/`.
