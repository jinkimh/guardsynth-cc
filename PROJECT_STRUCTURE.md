# Project structure

The canonical repository layout is defined in
[Project layout v2](docs/architecture/PROJECT_LAYOUT_V2.md).

```text
docs/          requirements, plans, designs, decisions, surveys, reports
src/           maintained reusable public implementation
cli/           domain-grouped user-facing pipelines
tests/         maintained package-level unit/integration/regression tests
experiments/   experiment protocols, fixtures, and experiment-local code
artifacts/     generated intermediate output and final run results
data/          source/derived input data separated by license class
papers/        manuscripts and publication assets
runtime/       local solvers and execution environments
third_party/   pinned upstream sources
archive/       immutable imported or superseded material
```

Key rules:

- New results go to `artifacts/results/public|restricted/<experiment-id>/<run-id>/`.
- New regenerable outputs go to `artifacts/intermediate/`.
- New EBLC pipelines go to `cli/pipelines/eblc/<purpose>/`.
- New GuardSynth generation pipelines go to `cli/pipelines/guardsynth/<purpose>/`;
  reusable generator code goes to `src/guard_synth/`, separate from frozen EBLC semantics.
- Real-scene source authoring and assurance lookup remain in `src/guard_synth/`;
  restricted scene contents remain under `artifacts/results/restricted/`.
- New maintained EBLC tests go to `tests/guard_synth_eblc/`.
- Do not create a new top-level `research/` or `experiments/results/` directory.

The old-to-new path table is
[MIGRATION_MAP.json](docs/architecture/MIGRATION_MAP.json).
