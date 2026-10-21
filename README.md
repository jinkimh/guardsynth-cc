# GuardSynth-CC research monorepo

This repository contains related but distinct research projects about Chain-of-Causation
(CoC), constraint-conditioned driving, sequential verification, and evidence-grounded contract
synthesis. EBLC/BCV is the shared executable-contract platform used by those projects.

## Start here

- [Research project index](PROJECTS.md)
- [Project Structure Codex v3](docs/architecture/PROJECT_STRUCTURE_CODEX.md)
- [Research document naming and hierarchy](docs/architecture/FILE_NAMING_CODEX.md)
- [Machine-readable project registry](PROJECT_REGISTRY.json)
- [GuardSynth-CoC status](projects/04-guardsynth-coc/STATUS.md)
- [EBLC language-verification research status](projects/05-eblc-language-verification/STATUS.md)
- [Research and review portal](apps/research_portal/README.md)

## Owner-oriented layout

```text
projects/      five research-question owners, each with docs/code/tests/experiments/paper
platforms/     reusable EBLC/BCV language and verification backend
apps/          repository applications
shared/        genuinely cross-owner utilities
artifacts/     owner-scoped new outputs plus immutable legacy runs
governance/    Superpowers and worktree policies
docs/          repository architecture only
data/          license-separated shared inputs
runtime/       pinned local execution environments and solvers
third_party/   pinned upstream checkouts
archive/       immutable historical material
```

Root `src/`, `experiments/`, and domain CLI namespaces are compatibility shims only. New domain
content must be placed under its project or platform. Root `tests/` contains repository-policy
tests only.

## Reproducibility and restricted data

- New runs use `artifacts/projects/<project-id>/<class>/...` or
  `artifacts/platforms/<platform-id>/<class>/...`.
- Existing `artifacts/results/` and `artifacts/intermediate/` are immutable pre-v3 history.
- Restricted NVIDIA-derived data and outputs must remain in restricted namespaces.
- Actual-vehicle validation is deferred until the research, paper, and patent stages described
  by the GuardSynth project decision records.

The exact public-manifest exclusion policy is implemented in
[`cli/checks/build_manifest.py`](cli/checks/build_manifest.py).

## GuardSynth NCA reproducibility package

The frozen [source, synthetic data and prediction records](projects/04-guardsynth-coc/artifacts/public/paper1-reproducibility-release-001/github-release-2026-10-21-002/README.md) include a standard-library metric verifier and formal-check reproduction instructions. Code in this distribution is MIT; synthetic data and generated records are CC BY 4.0. Licenses are scoped to this distribution, not the entire monorepo. Host home paths and GPU identifiers are removed from exported copies. Model weights and restricted road imagery are excluded.
