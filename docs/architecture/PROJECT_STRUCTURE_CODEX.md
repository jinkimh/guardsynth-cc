# GuardSynth-CC Project Structure Codex

- Codex version: `v3.6`
- Effective date: `2026-08-12`
- Authority: repository-wide file placement and ownership
- Machine registry: [`PROJECT_REGISTRY.json`](../../PROJECT_REGISTRY.json)
- Agent entry point: [`AGENTS.md`](../../AGENTS.md)
- Naming authority: [`FILE_NAMING_CODEX.md`](FILE_NAMING_CODEX.md)

## 1. Governing idea

The repository is a monorepo of five research projects and one shared verification platform.
The unit of ownership is a research question, not a file type and not a paper number.

| Owner ID | Research responsibility |
|---|---|
| `safety-constrained-coc` | Does a supplied execution constraint improve goal-preserving VLM behavior? |
| `specification-alignment` | How do natural-language, structured, and executable specification interfaces differ? |
| `sequential-coc-verification` | Are sequential CoC annotations statefully and temporally consistent? |
| `guardsynth-coc` | Can CoC, scene, rule, provenance, and assurance inputs synthesize applicable constraints? |
| `eblc-language-verification` | Does EBLC provide traceable lifecycle semantics and verifiable multi-target lowering beyond simpler contract representations? |
| `eblc-bcv` | Shared EBLC language, Core lowering, runtime monitor, BCV, and SMT tooling |

EBLC is not the final GuardSynth research objective. Its reusable implementation remains a
platform consumed by GuardSynth, specification-alignment, and the independent EBLC language
verification research project. Project 05 owns the independent research question, evaluation,
and paper; it does not duplicate or absorb the platform implementation.

## 2. Canonical tree

```text
guardsynth-cc/
├── projects/
│   ├── 01-safety-constrained-coc/
│   ├── 02-specification-alignment/
│   ├── 03-sequential-coc-verification/
│   ├── 04-guardsynth-coc/
│   └── 05-eblc-language-verification/
├── platforms/
│   └── eblc-bcv/
├── shared/
├── apps/
│   └── research_portal/
├── artifacts/
│   ├── projects/<project-id>/<public|restricted|intermediate>/
│   ├── platforms/<platform-id>/<public|restricted|intermediate>/
│   └── results/                 # immutable pre-v3 historical runs only
├── data/                        # shared source data, separated by license
├── governance/
│   ├── superpowers/
│   └── worktrees/
├── archive/
│   └── agent-history/superpowers/
├── cli/                         # repository-wide compatibility and maintenance entry points
├── runtime/
├── third_party/
└── tests/structure/             # repository-wide policy tests only
```

### 2.1 Root namespace contract

Every root directory has one explicit role. A directory not listed here requires a Codex
decision before creation.

| Root | Allowed content | Forbidden content |
|---|---|---|
| `projects/` | one complete tree per research question | generic shared utilities |
| `platforms/` | reusable language/verification platforms | scene- or paper-specific logic |
| `apps/` | maintained web/desktop applications and their tests | experiment run output |
| `shared/` | code/schema with at least two real owners | speculative abstractions |
| `artifacts/` | generated immutable or intermediate outputs | maintained source code |
| `governance/` | repository policies and operating procedures | project research plans |
| `docs/` | repository architecture and migration records | project plans/reports/surveys |
| `data/` | license-separated shared inputs plus ownership catalog | generated reports |
| `runtime/` | installed solvers, environments, runtime catalog | maintained project source |
| `third_party/` | pinned upstream checkouts and ownership catalog | locally authored project code |
| `archive/` | immutable superseded/imported history | active plans or implementation |
| `cli/` | repository maintenance tools and temporary CLI shims | new domain pipelines |
| `src/` | temporary import shims only | new implementation |
| `experiments/` | temporary import shims only | new protocols or analyses |
| `tests/` | repository structure/governance tests only | project/platform behavior tests |
| `.superpowers/` | ignored disposable agent scratch | canonical documentation |
| `.worktrees/` | `README.md` and `registry.json` only | actual Git worktrees |
| `.agents/`, `.codex/` | local agent/tool configuration | research artifacts |

Generated caches such as `.pytest_cache/` and `.ruff_cache/` are ignored operational state and
are not project namespaces. `.git/` is Git-owned metadata.

Shared infrastructure is not ownerless. `data/`, `runtime/`, and `third_party/` each carry an
`OWNERSHIP.json` catalog that records which project/platform consumes every immediate child.

## 3. Standard project contract

Every `projects/<NN>-<project-id>/` has the following contract. `NN` is display and workflow
order; the stable logical owner remains the unnumbered `project_id` in `PROJECT.yaml` and
`PROJECT_REGISTRY.json`.

```text
README.md              human entry point and claim boundary
PROJECT.yaml           ownership, dependencies, canonical documents, artifact root
STATUS.md              current state, blocker, and next work only
docs/
  charter/             stable research question and non-goals
  requirements/        work-package inputs, outputs, tests, claim boundary
  plans/
    01_RESEARCH_PLAN_VNN.md      governing research scope and success criteria
    02_PROJECT_MILESTONES.md     ordered decomposition and evidence gates
    03_PROJECT_EXECUTION_TRACKER.md  current work and blockers
  designs/             interfaces, semantics, and experiment designs
  decisions/           alternatives and irreversible scope decisions
  reports/             curated multi-run reports, not raw runs
  surveys/
    README.md           authority/status index and relationship to the governing plan
    ...                 related-work inputs, novelty/method studies, and research notes
src/                   maintained project-specific implementation
pipelines/             project-specific user workflows
tests/                 unit, integration, and acceptance tests
experiments/           protocols, configs, fixtures, experiment-local analysis
paper/                 manuscript, figures, supplement, submission assets
results/RESULT_INDEX.md links to immutable artifact runs
```

Do not create a project file before choosing exactly one project owner. A file needed by two
projects is not automatically shared: keep it with the first real owner until a second real
consumer justifies promotion.

Every registered research project uses the same controlled planning set. The research plan is
the authority for scope and success criteria, the milestone ledger refines that plan, and the
execution tracker selects current work under both. `README.md`, `STATUS.md`, and `PROJECT.yaml`
must link to this set. Related-work surveys are formal inputs to research planning. Survey
documents remain in `docs/surveys/`; their `README.md` records authority status, upstream input,
and the planning or method decision each item informs. A current canonical survey is linked by
the research plan. Independent surveys are not assigned a false hierarchy merely for sorting;
only a real related-work-to-analysis-to-method-to-strategy refinement set receives local
two-digit prefixes. The File Naming Codex defines roles, metadata, versions, and exclusions.

## 4. Shared platform contract

`platforms/eblc-bcv/` owns reusable EBLC representations and operational semantics, typed
derivation and composition, Core lowering, runtime monitoring, BCV mutation workflows, and
SMT/Z3 compilation. It has its own `PLATFORM.yaml`, specifications, release notes, tests, and
artifact namespace. GuardSynth source retrieval, scene grounding, and applicability logic are
forbidden here. `projects/05-eblc-language-verification/` may evaluate and publish the platform,
but paper-specific protocols, baselines, analyses, and manuscripts belong to that project while
reusable code and conformance tests remain in the platform.

## 5. Document placement decision

Use this order:

1. Is it an immutable run output? Put it under the owner's artifact namespace.
2. Is it a paper source or submission asset? Put it in the owning project's `paper/`.
3. Is it a requirement, plan, design, decision, report, or survey for one research question?
   Put it in that project's corresponding `docs/` directory.
4. Is it repository architecture or governance? Put it in root `docs/architecture/` or
   `governance/`.
5. Is it temporary agent work? Keep it in ignored `.superpowers/` or `/tmp`; do not promote it.

The repository root, `docs/`, and `experiments/` are not general-purpose dumping grounds.

## 6. Results and reproducibility

New runs use:

```text
artifacts/projects/<project-id>/<class>/<experiment-id>/<run-id>/
artifacts/platforms/<platform-id>/<class>/<experiment-id>/<run-id>/
```

`<class>` is `public`, `restricted`, or `intermediate`. Final runs contain
`RUN_MANIFEST.json`, `RESULT.json`, and a scoped report when required. Runners must refuse to
overwrite an existing run ID.

Existing `artifacts/results/` and `artifacts/intermediate/` paths are immutable v2 history.
They may be read and indexed but must not receive new experiments after v3 adoption.

## 7. Compatibility roots

Legacy root packages and CLI namespaces may remain only as small forwarding shims during the
v3 transition. A shim must contain no domain logic and must name its canonical owner. New code
must import or execute the canonical project/platform location.

## 8. Superpowers artifact policy

Superpowers may create unlimited scratch material only under ignored `.superpowers/`.
Canonical promotion is limited to one final, human-reviewed document per required document
class and must be registered in `governance/superpowers/PROMOTIONS.json`. Task briefs, review
diffs, snapshots, hashes, and intermediate review packages are never promoted. See
[`governance/superpowers/README.md`](../../governance/superpowers/README.md).

## 9. Worktree policy

Worktrees are operational state, not project content. Actual Git worktrees live outside the
repository at `../guardsynth-cc-worktrees/<work-id>/`. Root `.worktrees/` contains only its
tracked policy README and registry. See
[`governance/worktrees/README.md`](../../governance/worktrees/README.md).

## 10. Enforcement

`tests/structure/test_project_layout.py` verifies project roots, registry ownership, forbidden
new legacy content, Superpowers separation, worktree policy, portal ownership, and canonical
links. `cli/checks/file_naming.py` audits maintained filenames. Any structural exception
requires a decision record and a Codex version update.
