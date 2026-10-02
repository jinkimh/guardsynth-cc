# Project Structure Codex v3 migration report

- Effective date: 2026-08-12
- Structure Codex: `v3.3`
- Scope: repository ownership and path refactor; no research claim change

## Outcome

The repository is now organized by research-question owner instead of global file type.
GuardSynth-CoC, Safety-Constrained CoC, Sequential CoC Verification, and Specification
Alignment each have a complete project tree. Reusable EBLC/BCV code and tests have a separate
platform owner. The portal is an application rather than an experiment.

## Main migrations

| Former location | Canonical owner |
|---|---|
| `papers/paper1-*` | `projects/01-safety-constrained-coc/paper/manuscript/` |
| `papers/paper2-*` | `projects/02-specification-alignment/paper/manuscript/` |
| `papers/paper3-*` | `projects/03-sequential-coc-verification/paper/manuscript/` |
| `src/guard_synth/` | `projects/04-guardsynth-coc/src/guard_synth/` |
| `src/guard_synth_eblc/` | `platforms/eblc-bcv/src/guard_synth_eblc/` |
| GuardSynth pipelines/tests/experiments | `projects/04-guardsynth-coc/` |
| EBLC pipelines/tests/experiments | `platforms/eblc-bcv/` |
| sequential and UPPAAL experiments | `projects/03-sequential-coc-verification/experiments/` |
| VLM guard-learning experiments | `projects/01-safety-constrained-coc/experiments/` |
| project plans/designs/reports/surveys | each owner's `docs/` tree |
| `project_portal/` | `apps/research_portal/` |
| `docs/internal/superpowers/` | canonical items promoted to owners; history archived |

Root `src/`, `experiments/`, and domain CLI directories retain forwarding shims only. Root
`tests/` retains repository-policy tests only.

## Ordered project navigation

Structure Codex v3.3 prefixes the four project directories with `01` through `04` in research
progression order. Logical `project_id` values and artifact owner paths remain unnumbered and
stable. Project-internal functional directories such as `docs`, `src`, `tests`, `experiments`,
and `paper` remain unnumbered because they describe roles rather than temporal stages.

## Result preservation

Existing `artifacts/results/` and `artifacts/intermediate/` paths are immutable v2 history and
were not bulk-moved, because their manifests and embedded paths are part of reproducibility.
All new runs use owner-scoped paths under `artifacts/projects/` or `artifacts/platforms/`.

## Enforcement

`tests/structure/test_project_layout.py` checks root namespace registration, project contracts,
canonical source ownership, compatibility-only roots, Superpowers separation, worktree
placement, shared-infrastructure catalogs, and entry-document links.

## Verification record

The original ownership audit is stored at
[`layout-v3-2026-08-12-v1`](../../artifacts/projects/guardsynth-coc/public/project-layout-refactor-001/layout-v3-2026-08-12-v1/REPORT_KO.md).
It recorded `EXECUTED`, 17/17 structure checks, 133/133 EBLC tests, 170/170
GuardSynth tests, 11/11 Safety-Constrained CoC micro-world tests, 166/166 Sequential CoC
tests, 12/12 bounded logic/SMT tests, 7/7 P0a tests, 14/14 UPPAAL model-generation tests,
8/8 domain CLI checks, and zero broken canonical Markdown links. The real `verifyta`
equivalence test remains explicitly skipped when an UPPAAL license is unavailable.

Structure Codex v3.2 added the repository-wide File Naming Codex and names audit. Structure
Codex v3.3 additionally orders the canonical project directories by research progression. The
final post-ordering audit is stored at
[`layout-v3-2026-08-12-v5`](../../artifacts/projects/guardsynth-coc/public/project-layout-refactor-001/layout-v3-2026-08-12-v5/REPORT_KO.md)
under the same immutable experiment namespace.
