# Project layout v2

- Status: approved migration target
- Effective date: 2026-08-09
- Scope: entire `guardsynth-cc` workspace

## 1. Design goals

The repository uses one canonical location for each artifact class:

1. requirements, plans, designs, surveys, and human-readable reports live in `docs/`;
2. reusable publishable implementation lives in `src/`;
3. user-facing orchestration lives in domain-grouped `cli/pipelines/`;
4. experiment directories contain protocols, configurations, and experiment-local code, not results;
5. generated intermediate and final run artifacts live in `artifacts/`;
6. package-level regression tests live in `tests/`;
7. data, third-party sources, runtime environments, papers, and archives remain isolated.

## 2. Canonical top-level tree

```text
guardsynth-cc/
├── README.md
├── PROJECT_STRUCTURE.md          # short pointer to this document
├── docs/
│   ├── README.md                 # document index
│   ├── architecture/             # repository and system architecture
│   ├── requirements/             # implementation requirements and locked prompts
│   ├── plans/                    # active research/development plans
│   ├── designs/                  # technical and experiment designs
│   ├── decisions/                # method/tool choices and alternatives
│   ├── surveys/                  # literature and landscape surveys
│   ├── reports/                  # stable human-readable progress/verification reports
│   ├── notes/                    # non-authoritative exploratory notes
│   └── internal/                 # internal development history
├── src/                          # final reusable public code
├── cli/
│   └── pipelines/
│       └── <domain>/<purpose>/   # one run.py per user-facing workflow
├── tests/
│   └── <package>/                # package-level unit/integration/regression tests
├── experiments/
│   └── <family>/                 # protocols, fixtures, local analysis and legacy compatibility
├── artifacts/
│   ├── intermediate/             # regenerable compiler/model/export output
│   └── results/
│       ├── public/               # publishable synthetic/baseline results
│       └── restricted/           # access-controlled results
├── data/                         # source and derived input data, by license class
├── papers/                       # manuscripts and publication assets
├── runtime/                      # local solvers and execution environments
├── third_party/                  # pinned upstream sources
└── archive/                      # superseded or imported immutable material
```

## 3. Ownership rules

| Content | Canonical owner | Forbidden placement |
|---|---|---|
| research requirement or locked implementation prompt | `docs/requirements/` | `experiments/`, repository root |
| active research plan | `docs/plans/` | `research/`, `artifacts/` |
| operational/software design | `docs/designs/` or `docs/architecture/` | result directories |
| literature survey | `docs/surveys/` | active plan folders |
| stable narrative report | `docs/reports/` | `src/`, experiment source folders |
| reusable Python module | `src/<package>/` | `experiments/` except compatibility wrappers |
| CLI orchestration | `cli/pipelines/<domain>/<purpose>/run.py` | reusable semantics modules |
| package regression test | `tests/<package>/` | `src/` |
| experiment protocol/local analysis | `experiments/<family>/` | `src/` unless reusable |
| regenerable intermediate output | `artifacts/intermediate/` | `experiments/` |
| final run result and manifest | `artifacts/results/public|restricted/` | `experiments/` |

Experiment-local tests may remain beside tightly coupled historical experiment code. Tests for
the maintained `guard_synth_eblc` package are canonical under `tests/guard_synth_eblc/`.
The source-aware generation layer is owned by `src/guard_synth/` and its user-facing
workflows by `cli/pipelines/guardsynth/`; it must not be folded into the frozen EBLC
operational-semantics package.

## 4. Run directory contract

Every new run uses:

```text
artifacts/results/<class>/<experiment-id>/<run-id>/
├── RESULT.json
├── RUN_MANIFEST.json
├── REPORT_KO.md                  # when a narrative report is required
└── <domain-specific artifacts>
```

`<class>` is `public` or `restricted`. A runner must refuse to overwrite an existing run ID.
Intermediate output may be replaced only when its manifest explicitly marks it regenerable.

## 5. Migration mapping

| Previous path | Canonical v2 path |
|---|---|
| `research/plans/` | `docs/plans/` |
| `research/background/` | `docs/designs/` or `docs/surveys/` |
| `research/*REPORT*.md` | `docs/reports/` |
| root survey/working notes | `docs/surveys/` or `docs/notes/` |
| `experiments/results/baseline/` | `artifacts/results/public/` |
| `experiments/results/restricted/` | `artifacts/results/restricted/` |
| `experiments/eblc_p0b/test_*.py` | `tests/guard_synth_eblc/test_*.py` |
| `cli/pipelines/eblc_<purpose>/` | `cli/pipelines/eblc/<purpose>/` |

Historical result contents are immutable. Their recorded old paths remain historical facts;
`MIGRATION_MAP.json` maps them to the new physical locations.

Root-level solver distributions move to `runtime/solvers/`; their original zip/tar archives
move to `archive/installers/`.

## 6. Enforcement

`tests/structure/test_project_layout.py` enforces the canonical roots, rejects new result
directories under `experiments/`, verifies EBLC pipeline grouping, and checks that maintained
EBLC tests are not added back to the compatibility experiment package.

Run the complete migration audit with:

```bash
python3 -m cli.pipelines.maintenance.project_layout_audit.run --run-id <new-run-id>
```
