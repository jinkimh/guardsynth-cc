# File Naming Audit V1

- Date: 2026-08-12
- Naming Codex: [`FILE_NAMING_CODEX.md`](FILE_NAMING_CODEX.md)
- Scope: maintained repository source, tests, documents, pipelines, applications, and papers

## Outcome

The first repository-wide naming audit is complete. Maintained files and directories now have
an executable naming contract. Historical artifacts, archives, data, installed runtimes, and
third-party trees are excluded from renaming because their paths carry provenance or external
interface meaning.

## Corrections

| Former path | Disposition |
|---|---|
| `projects/01-safety-constrained-coc/paper/manuscript/Template_File_for_Publication_...(2022).hwp` | renamed to `publication_review_template_2022.hwp` |
| `cli/checks/build_manifest.py.orig` | removed from the maintained CLI and archived under `archive/agent-history/legacy-backups/` |

The normalization pass also renamed 17 single-digit-version documents to two-digit versions,
three maintained HTML templates to lowercase `snake_case`, and two experiment operational
documents from uppercase hyphenated names to `UPPER_SNAKE_CASE`. All maintained references
were updated with the files.

The HWP row intentionally abbreviates the former non-ASCII filename. Its file content was not
changed.

## Enforced conventions

- owner IDs and run IDs: lowercase `kebab-case`;
- Python packages, modules, tests, pipelines, and experiments: lowercase `snake_case`;
- canonical research documents: uppercase `UPPER_SNAKE_CASE` with explicit version suffixes;
- chronological records: `YYYY-MM-DD-lowercase-kebab-case.md`;
- JSON Schema: `<subject>.schema.json`;
- no spaces, parentheses, non-ASCII path components, numbered-copy suffixes, or active `.orig`
  and `.bak` files;
- external fonts, LaTeX classes, and styles are narrowly excepted in
  [`NAMING_EXCEPTIONS.json`](NAMING_EXCEPTIONS.json).

## Verification

Run `python3 cli/checks/file_naming.py --json` for the current counts and violations. The same
audit runs as part of `tests/structure/test_project_layout.py`, so new irregular names fail the
repository structure gate.

The final post-rename regression is recorded in
[`layout-v3-2026-08-12-v5`](../../artifacts/projects/guardsynth-coc/public/project-layout-refactor-001/layout-v3-2026-08-12-v5/REPORT_KO.md).
It passed 18/18 structure checks, 133/133 EBLC tests, 170/170 GuardSynth tests, 11/11
micro-world tests, 166/166 Sequential CoC tests, 12/12 bounded logic/SMT tests, 7/7 P0a
tests, 14/14 UPPAAL model-generation tests, eight domain CLI checks, and all four portal
tests. The separately executed portal suite passed 4/4 tests. After recording the immutable
v5 audit, the naming audit covered 806 maintained files and 209 maintained directories with
zero violations.
