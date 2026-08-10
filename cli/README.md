# CLI pipelines

User-facing interfaces are grouped first by domain and then by purpose:

```text
cli/pipelines/<domain>/<purpose>/run.py
```

Current EBLC workflows are indexed in [`pipelines/eblc/README.md`](pipelines/eblc/README.md).
Reusable semantics stay under `src/`; runners only parse arguments, orchestrate modules, and
write artifacts.

Examples from the project root:

```bash
python3 -m cli.pipelines.eblc.p0b_schema_bcv.run --help
python3 -m cli.pipelines.eblc.scenario_validation.run --help
runtime/alpamayo/ar1_venv/bin/python -m cli.pipelines.eblc.restricted_scene_grounding.run --help
python3 -m cli.pipelines.maintenance.project_layout_audit.run --help
```

Repository-maintenance workflows are grouped under `cli/pipelines/maintenance/`; they are
separate from research-domain pipelines.

All runners use `cli.project_paths.project_root` so domain regrouping does not change path
resolution.
