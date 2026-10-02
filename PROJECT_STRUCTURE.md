# Project structure

The canonical repository layout is defined in the
[Project Structure Codex v3](docs/architecture/PROJECT_STRUCTURE_CODEX.md).
The machine-readable owner list is [PROJECT_REGISTRY.json](PROJECT_REGISTRY.json).
File and directory names are governed by the
[File Naming Codex](docs/architecture/FILE_NAMING_CODEX.md).

```text
projects/      ordered `<NN>-<project-id>` directory per research question
platforms/     reusable language and verification platforms
shared/        utilities with at least two real consumers
apps/          repository applications such as the research portal
artifacts/     owner-scoped generated outputs and immutable legacy runs
governance/    Superpowers and Git worktree policies
docs/          repository architecture and cross-project governance only
src/           temporary import shims; no new domain implementation
cli/           repository maintenance and temporary CLI shims
tests/         repository structure and governance tests only
experiments/   temporary experiment shims; no new experiment implementation
data/          source/derived input data separated by license class
runtime/       local solvers and execution environments
third_party/   pinned upstream sources
archive/       immutable imported or superseded material
```

Key rules:

- Choose one owner in `PROJECT_REGISTRY.json` before creating a file.
- Keep every project's controlled planning set as `01_RESEARCH_PLAN_VNN.md` →
  `02_PROJECT_MILESTONES.md` → `03_PROJECT_EXECUTION_TRACKER.md`, and index its surveys in
  `docs/surveys/README.md`. Current related-work surveys are formal research-plan inputs; only
  real refinement sets receive local hierarchy numbers.
- Name every maintained file according to `FILE_NAMING_CODEX.md` and run
  `python3 cli/checks/file_naming.py` before completion.
- New results go to `artifacts/projects/<project-id>/<class>/...` or
  `artifacts/platforms/<platform-id>/<class>/...`.
- `artifacts/results/` and `artifacts/intermediate/` are immutable v2 history.
- New EBLC pipelines go to `platforms/eblc-bcv/pipelines/cli/<purpose>/`.
- Independent EBLC paper protocols, analyses, and manuscript assets go to
  `projects/05-eblc-language-verification/` and depend on the platform without copying it.
- New GuardSynth generation pipelines go to `projects/04-guardsynth-coc/pipelines/cli/<purpose>/`;
  reusable generator code goes to `projects/04-guardsynth-coc/src/guard_synth/`, separate from frozen EBLC semantics.
- The repository-wide research/review web application is owned by `apps/research_portal/`, not an
  experiment pipeline. New portal runs use `artifacts/projects/guardsynth-coc/restricted/`.
- Real-scene source authoring and assurance lookup remain in `projects/04-guardsynth-coc/src/guard_synth/`;
  restricted scene contents remain under `artifacts/results/restricted/`.
- EBLC tests belong to `platforms/eblc-bcv/tests/`; GuardSynth tests belong to
  `projects/04-guardsynth-coc/tests/`; portal tests belong to `apps/research_portal/tests/`.
- Superpowers scratch files stay in ignored `.superpowers/`; promoted documents follow
  `governance/superpowers/README.md`.
- Real worktrees live at `../guardsynth-cc-worktrees/`; root `.worktrees/` is registry-only.
- Do not create a new top-level `research/` or `experiments/results/` directory.

The v2 historical path table is [MIGRATION_MAP.json](docs/architecture/MIGRATION_MAP.json).
