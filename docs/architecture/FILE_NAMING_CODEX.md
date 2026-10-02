# GuardSynth-CC File Naming Codex

- Codex version: `v1.4`
- Effective date: `2026-08-13`
- Scope: maintained repository files and directories
- Structure authority: [`PROJECT_STRUCTURE_CODEX.md`](PROJECT_STRUCTURE_CODEX.md)
- Automated check: [`cli/checks/file_naming.py`](../../cli/checks/file_naming.py)

## 1. Purpose

Names must reveal a file's role without requiring its contents to be opened. This Codex is
mandatory for new and renamed files. It supplements the ownership and placement rules in the
Project Structure Codex; it does not change project ownership.

Immutable historical artifacts, archived material, licensed data, installed runtimes, and
pinned third-party source retain their original names for provenance and reproducibility.

## 2. Directory names

| Directory kind | Rule | Example |
|---|---|---|
| project directory | two-digit order plus lowercase ID | `04-guardsynth-coc` |
| logical project, platform, app ID | lowercase `kebab-case` | `guardsynth-coc` |
| Python package, pipeline, test, experiment | lowercase `snake_case` | `source_aware_generate` |
| document class | fixed lowercase plural | `requirements`, `designs`, `reports` |
| experiment/run ID | lowercase `kebab-case` with numeric suffix | `eblc-p0b-001` |
| hidden tool state | tool-defined dotted name | `.worktrees` |

Spaces, parentheses, `+`, non-ASCII characters, and suffixes such as `(1)` are forbidden in
maintained directory names.

Project directory numbers express the repository research progression. They are not part of
the stable `project_id`, import namespace, or artifact owner ID. Reordering requires an explicit
registry and Structure Codex update; do not insert an unregistered number ad hoc.

## 3. Maintained source and test files

- Python modules use `snake_case.py`.
- Tests use `test_<subject>.py`.
- Package entry points use `__init__.py`; CLI entry points use `run.py`.
- JavaScript and CSS use lowercase `snake_case` or a conventional single-word entry name.
- Maintained HTML templates use lowercase `snake_case.html`.
- JSON Schema files use `<subject>.schema.json`.
- Fixtures use `<subject>[_v<major>_<minor>].json`.
- Do not encode temporary states such as `new`, `final`, `latest`, `copy`, or `(1)` in names.
  Versioned interfaces use explicit `_v<major>_<minor>` suffixes.

## 4. Research and development documents

### 4.1 Role-bearing names

Canonical research and development documents use:

```text
<SUBJECT>_<ROLE>[_<QUALIFIER>][_V<two-digit-version>].md
```

The containing directory and filename role must agree. The normal roles are `REQUIREMENTS`,
`DESIGN`, `DECISION`, `SURVEY`, `ANALYSIS`, `REPORT`, `SPEC`, `RUNBOOK`, and `NOTES`. A name
need not be lengthened when a reserved filename or an established directory-local convention
already makes the role unambiguous.

Examples include `M16_EXPERT_PILOT_REQUIREMENTS.md`,
`SOURCE_AWARE_GENERATOR_DESIGN_V01.md`,
`ACTUAL_VEHICLE_VALIDATION_DEFERRAL_DECISION_V01.md`, and
`SEMANTIC_CONFORMANCE_REPORT_V01.md`.

### 4.2 Project planning control set

Every registered research project has exactly this set in `docs/plans/`:

```text
01_RESEARCH_PLAN_VNN.md
02_PROJECT_MILESTONES.md
03_PROJECT_EXECUTION_TRACKER.md
```

The number is authority and refinement order, not creation order or version. The research plan
owns the research question, hypothesis, scope, claim boundary, evaluation unit, baseline
direction, and success, reduction, stop, and pivot criteria. The milestone ledger decomposes
that authority into work packages, prerequisites, evidence gates, deliverables, and critical
path. The execution tracker records current work, blockers, the single next action, and state
transitions. A lower document may not silently change an upper document. Scope changes flow
from the research plan to milestones and then to the tracker. All three documents link to each
other, and exactly one two-digit-versioned research plan is allowed.

### 4.3 Related-work survey control

Related work is a governed input to research planning, not merely a bibliography. Every
project keeps `docs/surveys/README.md`, indexes every maintained survey or research note, and
classifies it as `CURRENT`, `SUPPORTING`, `HISTORICAL`, `SUPERSEDED`, or `PLANNED`. A
`SUPERSEDED` item must link to its replacement. A current research plan must link every
`CURRENT` canonical survey and say which question, baseline, method, or claim boundary it
supports.

Use one comprehensive document when literature review, novelty analysis, method comparison,
and strategy are genuinely integrated:

```text
RELATED_WORK_SURVEY_AND_RESEARCH_STRATEGY_V01.md
```

Use this local controlled set only when the material has real refinement stages:

```text
01_RELATED_WORK_SURVEY_V01.md
02_NOVELTY_GAP_ANALYSIS_V01.md
03_METHOD_SELECTION_SURVEY_V01.md
04_RESEARCH_STRATEGY_DECISION_V01.md
```

The local survey number does not place `docs/surveys/01_*` at the same authority as
`docs/plans/01_*`. Unused stages are not created merely to complete the visual sequence; if a
project has a shorter real sequence, the used numbers remain consecutive and their roles remain
accurate. Independent topics use `<SUBJECT>_SURVEY_VNN.md` without a prefix. Personal
exploration without a search protocol or inclusion/exclusion criteria uses
`<SUBJECT>_NOTES.md`. A dated survey name is allowed only when date is intrinsic to its identity:
`YYYY-MM-DD-lowercase-kebab-case-survey.md`.

A canonical survey records the following fields. Unknown historical facts are `unrecorded`,
`미기록`, or an explicit TODO, never invented:

```text
- 기준 연구계획:
- 조사 기준일:
- 검색 데이터베이스:
- 검색 범위:
- 포함 기준:
- 제외 기준:
- 현재 권위 상태:
- 직접 지원하는 연구 질문:
- 직접 지원하는 baseline 또는 방법 결정:
- 후속 문서:
```

The paper's related-work section is a summary output from this evidence base, not a competing
authority. A naming migration never fabricates freshness, novelty, or completion claims.

### 4.4 Numbering, versions, and reserved names

- Use uppercase `UPPER_SNAKE_CASE` for canonical Markdown documents.
- Use exactly two digits for controlled-set hierarchy prefixes. `00`, one-digit prefixes, and
  arbitrary visual-sort numbers are forbidden.
- Number only a real parent/refinement set. Parallel designs, decisions, and reports are not
  numbered.
- Encode document versions as `_V01`, `_V02`, and so on. `_V1` is forbidden.
- Do not use status tokens such as `FINAL`, `LATEST`, `NEW`, `COPY`, or `(1)` in names.
- Use `YYYY-MM-DD-lowercase-kebab-case.md` only for genuinely chronological records.
- Experiment-ID-prefixed operational documents use uppercase underscores, for example
  `ALP_EXP_005_REMOTE_RUNBOOK.md`.
- Reserved entry documents keep their conventional names: `README.md`, `STATUS.md`,
  `RESULT_INDEX.md`, `REPORT_KO.md`, `RUN_MANIFEST.json`, and `RESULT.json`.
- Language belongs in content or an optional terminal qualifier such as `_KO`, not mixed scripts
  in a filename.

Good examples:

```text
01_RESEARCH_PLAN_V01.md
02_PROJECT_MILESTONES.md
03_PROJECT_EXECUTION_TRACKER.md
RELATED_WORK_SURVEY_AND_RESEARCH_STRATEGY_V01.md
03_METHOD_SELECTION_SURVEY_V01.md
M16_EXPERT_PILOT_REQUIREMENTS.md
SOURCE_AWARE_GENERATOR_DESIGN_V01.md
ACTUAL_VEHICLE_VALIDATION_DEFERRAL_DECISION_V01.md
SEMANTIC_CONFORMANCE_REPORT_V01.md
```

Invalid examples:

```text
RESEARCH_PLAN_V1.md
1_RESEARCH_PLAN.md
PROJECT_MILESTONES_FINAL.md
latest_survey.md
new_design.md
report_copy.md
DESIGN_02.md
```

### 4.5 Atomic renames and exclusions

Before renaming, record the old path, new path, role reason, governing document, and all known
maintained references. Move the document and update Markdown links, code path literals, tests,
metadata, registries, portal links, migration maps, manifests, indexes, and paper build inputs as
one change. A public path needs an explicit compatibility or migration record.

Do not rewrite immutable completed runs, archive contents, third-party source, installed
runtimes, licensed inputs, or external templates to normalize a name or embedded historical
path. Their provenance takes priority. Pre-existing unrelated broken links are reported
separately; links caused by the rename and links blocking canonical entry points are fixed.

## 5. Papers and external templates

Authored paper sources use lowercase `kebab-case`, such as `03-problem.tex`, or conventional
entry names such as `main.tex`, `references.bib`, and `Makefile`. Planning and audit documents
inside a paper tree still use the document rule above. Upstream class/style/font files retain
their upstream names.

External editable templates imported into a maintained paper tree receive a short ASCII name
describing their role, for example `publication_review_template_2022.hwp`. The original title
and origin belong in the paper README or provenance metadata, not in a path.

## 6. Generated results

New artifact directory names follow the Structure Codex. Required result files are exactly:

- `RESULT.json`
- `RUN_MANIFEST.json`
- `REPORT_KO.md` when a Korean report is required

Generated filenames defined by an external tool or historical manifest are not renamed.
The automated check covers all new owner-scoped output under `artifacts/projects/` and
`artifacts/platforms/`. Immutable legacy output under `artifacts/results/` and
`artifacts/intermediate/` is excluded.

A completed run is never edited only to normalize a filename. Record a narrow exception for
an irregular path already fixed by its run manifest, and correct the producer so later runs
emit canonical names.

## 7. Enforcement and exceptions

Run:

```bash
python3 cli/checks/file_naming.py
```

The check covers maintained source, tests, documents, pipelines, applications, and paper
sources. It excludes immutable or externally controlled namespaces explicitly listed by the
checker. An exception requires all three:

1. an external interface or provenance reason;
2. a narrowly scoped entry in `NAMING_EXCEPTIONS.json`;
3. a structure test demonstrating that the exception still exists and remains scoped.

Do not weaken a general pattern to accommodate one irregular file.

Files with types not otherwise specified use a lowercase ASCII basename with `snake_case` or
`kebab-case`. The only generic reserved names are `.gitkeep`, `Makefile`, `PROJECT.yaml`, and
`PLATFORM.yaml`. Repository-root files are allowlisted; adding another root file requires a
Structure Codex change rather than silently extending the list.
