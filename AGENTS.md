# Repository Instructions

## 0. Project Structure Codex (mandatory)

Before creating, moving, or renaming any file, read
[`docs/architecture/PROJECT_STRUCTURE_CODEX.md`](docs/architecture/PROJECT_STRUCTURE_CODEX.md).
That document is the canonical placement specification for this repository.
File and directory names must also follow
[`docs/architecture/FILE_NAMING_CODEX.md`](docs/architecture/FILE_NAMING_CODEX.md).

Mandatory placement rules:

- Research-question-specific material belongs to exactly one ordered directory under
  `projects/<NN>-<project-id>/`. The numeric prefix is display/workflow order only; use the
  unnumbered logical `project_id` for metadata and artifact ownership.
- Reusable EBLC/BCV/Core/SMT/runtime implementation belongs to `platforms/eblc-bcv/`.
- Independent EBLC language-verification protocols, analyses, and paper assets belong to
  `projects/05-eblc-language-verification/`; never copy the reusable platform implementation there.
- Cross-project utilities only belong to `shared/` after at least two real consumers exist.
- Repository applications belong to `apps/`; generated runs never belong there.
- New run output belongs to `artifacts/projects/<project-id>/...` or
  `artifacts/platforms/<platform-id>/...` according to its owner and license class.
- Do not add new canonical implementation, tests, plans, or papers to legacy root
  `src/`, `tests/`, `experiments/`, `papers/`, or domain folders under `docs/`.
  Those roots may contain only documented compatibility shims or historical material.
- Every new project file must be attributable to a `project_id` in
  `PROJECT_REGISTRY.json`. If ownership is unclear, stop and resolve ownership first.
- Do not create a new root directory unless it is first added to the root namespace contract in
  the Structure Codex and to `PROJECT_REGISTRY.json`.
- Shared inputs, runtimes, and upstream checkouts must also be registered in the corresponding
  `data/OWNERSHIP.json`, `runtime/OWNERSHIP.json`, or `third_party/OWNERSHIP.json` catalog.
- Before completing a file-creating task, run `python3 cli/checks/file_naming.py`. Do not add
  ad-hoc suffixes such as `new`, `final`, `latest`, `copy`, or `(1)`.

### Superpowers and agent-generated documents

- `.superpowers/` is ignored scratch state only. It is never a canonical documentation root.
- Do not copy task briefs, review diffs, review packages, snapshots, or progress logs into
  project `docs/`.
- Durable Superpowers outputs must be deliberately promoted to one project and one of:
  `docs/requirements/`, `docs/plans/`, `docs/designs/`, `docs/decisions/`, or
  `docs/reports/`. Promotion rules are in
  [`governance/superpowers/README.md`](governance/superpowers/README.md).
- Every promoted Superpowers document must be recorded in
  [`governance/superpowers/PROMOTIONS.json`](governance/superpowers/PROMOTIONS.json); do not
  promote progress logs or multiple near-duplicate plans.
- Historical Superpowers records belong only in `archive/agent-history/superpowers/`.

### Git worktrees

- Actual worktrees must be created outside this repository under the sibling directory
  `../guardsynth-cc-worktrees/<work-id>/`.
- Root `.worktrees/` is a policy/registry directory only; never create a Git worktree or
  research artifact inside it.
- Register and retire worktrees according to
  [`governance/worktrees/README.md`](governance/worktrees/README.md).

These behavioral guidelines reduce common coding-agent mistakes. Merge them
with project-specific instructions when needed. They intentionally favor
caution over speed; use judgment for trivial tasks.

## 1. Think Before Coding

Do not assume or hide confusion. Surface assumptions and tradeoffs before
implementing:

- State assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them instead of choosing silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop, name what is confusing, and ask.

## 2. Simplicity First

Write the minimum code that solves the requested problem. Do not add speculative
work:

- Add no features beyond what was asked.
- Do not introduce abstractions for single-use code.
- Do not add flexibility or configurability that was not requested.
- Do not add error handling for impossible scenarios.
- If 200 lines could be 50, rewrite and simplify.
- Ask: "Would a senior engineer say this is overcomplicated?" If so, simplify.

## 3. Surgical Changes

Touch only what the task requires, and clean up only changes introduced by the
task:

- Do not improve adjacent code, comments, or formatting.
- Do not refactor code that is not broken.
- Match the existing style, even if you would choose a different style.
- Mention unrelated dead code instead of deleting it.
- Remove imports, variables, and functions made unused by your own changes.
- Do not remove pre-existing dead code unless asked.
- Every changed line should trace directly to the user's request.

## 4. Goal-Driven Execution

Define verifiable success criteria and iterate until they are satisfied.
Translate requests into concrete checks, for example:

- "Add validation" becomes "Write tests for invalid inputs, then make them pass."
- "Fix the bug" becomes "Write a test that reproduces it, then make it pass."
- "Refactor X" becomes "Ensure tests pass before and after."

For multi-step tasks, state a brief plan in this form:

1. `[Step]` -> verify: `[check]`
2. `[Step]` -> verify: `[check]`
3. `[Step]` -> verify: `[check]`

Strong success criteria support independent execution. If the criteria are weak
or amount only to "make it work," clarify them before implementation.

These guidelines are working when diffs contain fewer unnecessary changes,
solutions avoid needless complexity, and clarifying questions happen before
implementation rather than after mistakes.
