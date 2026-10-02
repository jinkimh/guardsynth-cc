# KIEE CoC audit revision V01

- Owner: `sequential-coc-verification`.
- Governing revision design: [sections 10–12](../../../docs/designs/KIEE_REVIEW_RESPONSE_REEXPERIMENT_DESIGN_V01.md).
- Comparison baseline: original repository `latex-kiee-review-2022-coc-audit-10pages`, not the introduction-only worktree preview.
- This directory is the complete E6 revision. Original submission and experiment implementations are preserved.

## Deliverables

- [main.pdf](main.pdf): changes against the original submission in blue.
- [main-clean.pdf](main-clean.pdf): identical content with revision color removed.
- [Reviewer 1 response](response-to-reviewer-1.pdf): 6 Major + 3 Minor items.
- [Reviewer 2 response](response-to-reviewer-2.pdf): 8 items, including separate 1.1/1.2 answers.
- [Reviewer 3 response](response-to-reviewer-3.pdf): 11 items.
- Corresponding TeX sources are adjacent. `manuscript-locations.tex` is generated from the manuscript auxiliary labels; response blocks also identify the exact PDF pages containing their quoted revisions.

The article body, figures, tables, title, abstract and keywords were revised. Unchanged section headings, acknowledgments and existing bibliography entries keep their submitted color. Added bibliography entries are marked. All revised figures/tables explicitly carry the revision color; the clean copy changes color only.

## Build and verification

The completed build is recorded in `artifacts/projects/sequential-coc-verification/public/kiee-review-revision-001/manuscript-build-2026-10-01-001/`. To rebuild, set `COC_BUILD_DIR` to a new, nonexistent run directory under the same owner-scoped `kiee-review-revision-001/` artifact parent and run `python3 build.py` from this directory. The driver refuses existing output directories. It runs LuaLaTeX, BibTeX, and two additional LuaLaTeX passes for both article copies, then three LuaLaTeX passes for each response. Intermediates, logs and TeX cache stay in the chosen artifact directory; only deliverable PDFs are copied here.

After content or layout edits, revalidate response excerpt pages as well as generated section/table locations. The completed document validation checks all 28 excerpts against the PDF; their explicit page references are not automatically rewritten by the build.

The bundled style is reused unchanged. `fonts/` and `.texlive-local/` are relative links to the preserved adjacent submission assets. The build reads these assets and writes its cache to the artifact directory. Keep the adjacent baseline directory when rebuilding this source tree.

The artifact report records original-submission hashes, source comparison, build logs, document validation, preserved experiment references and naming results. Numerical verification recounts saved JSON/CSV and compares hashes; it does not rerun completed experiments. No human labels are filled in by the build.

## Claim and metadata boundary

This is a feasibility and traceability study on authored frames. Legacy first results (96/144, 48 failures) and condition-indexed post-development same-case retesting (144/144) are separate. The FSM also succeeds; automatic text is all UNKNOWN. Independent natural-error accuracy, human re-evaluation, general NLP, quantitative time bounds and vehicle safety are not established.

The manuscript ID and actual editorial revision round remain “confirmation needed”; `revision-v01` is a source version, not an invented editorial round. The prior 10-page baseline is not treated as a mandatory journal limit. The current official submission-guidance attachment could not be retrieved as PDF through the website links, so no unverified page requirement is asserted. No external submission, publication, messaging, merge or push was performed.
