# KIEE CoC Audit Independent Copy Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an independent KIEE 2022 anonymous-review LaTeX copy of the finalized CoC temporal/provenance audit manuscript without changing either source manuscript or experiment evidence.

**Architecture:** The target directory owns its style, fonts, front matter, ten section files, five TikZ figures, bibliography, regression tests, build entry point, and validation report. Content is copied from the finalized manuscript, while layout interfaces and captions are adapted to the KIEE style; no source-relative inputs or symlinks are allowed.

**Tech Stack:** LuaLaTeX, BibTeX, extarticle, local Noto Serif CJK KR fonts, TikZ, Python unittest, GNU Make, MuPDF rendering

## Global Constraints

- Source manuscript is read-only: `projects/sequential-coc-verification/paper/manuscript`.
- Template reference is read-only: `projects/safety-constrained-coc/paper/manuscript/latex-kiee-review-2022`.
- Target is exactly `projects/sequential-coc-verification/paper/manuscript/latex-kiee-review-2022-coc-audit`.
- Do not create symlinks or relative `\input` references back to either source directory.
- Preserve the finalized RQ1--RQ4, all reported values, equations, artifact boundaries, and limitations.
- Do not change experiment code, JSON artifacts, or the source manuscript.
- Use A4, 18.01 mm left/right margins, 18.99 mm top/bottom margins, two columns, 8 mm column gap, 8.5 pt body and 12.75 pt leading.
- Produce an anonymous review copy with no `\author` command.
- English abstract must contain 50--200 words, no citation/reference/footnote/equation, and six English keywords.
- Every compiled figure and table must have a Korean-English bilingual caption.
- Build order is LuaLaTeX -> BibTeX -> LuaLaTeX -> LuaLaTeX.
- Completion requires zero undefined commands/citations/references, zero overfull boxes, a valid PDF, and visual inspection of every page.
- Git metadata is unavailable; do not initialize Git. Use task reports and filesystem comparisons instead of commits.

---

## File Responsibility Map

- `main.tex`: KIEE title block, English abstract, six keywords, ten section inputs and bibliography
- `kiee-review.sty`: KIEE geometry, fonts, bilingual caption macros, source-compatible colors/commands/TikZ configuration
- `sections/01-introduction.tex` through `sections/10-conclusion.tex`: independent copies of finalized content with KIEE bilingual captions
- `figures/*.tex`: independent copies of the five TikZ figures
- `references.bib`: complete independent bibliography copy
- `fonts/`: reproducible local font files and OFL license
- `tests/test_kiee_format.py`: structural, independence, content-preservation and caption regression tests
- `Makefile`: tests and reproducible LuaLaTeX/BibTeX build
- `README.md`: source provenance, independence, build and scope notes
- `CONVERSION_REPORT.md`: file comparison, tests, build diagnostics and full-page visual audit

---

### Task 1: Scaffold and Failing Format Tests

**Files:**
- Create: `projects/sequential-coc-verification/paper/manuscript/latex-kiee-review-2022-coc-audit/tests/test_kiee_format.py`
- Create directories: target root, `tests/`, `sections/`, `figures/`, `fonts/`

**Interfaces:**
- Consumes: approved design specification
- Produces: executable acceptance tests that Tasks 2–5 must satisfy

- [ ] **Step 1: Confirm the target is absent or non-conflicting**

Run:

```bash
find projects/sequential-coc-verification/paper/manuscript/latex-kiee-review-2022-coc-audit -maxdepth 2 -type f -print 2>/dev/null
```

Expected: no files. If files exist, inventory them in the task report and stop rather than overwrite unknown work.

- [ ] **Step 2: Create only the target directory skeleton**

Create the five target directories without copying source content. The source and template directories remain byte-for-byte unchanged.

- [ ] **Step 3: Write structural and content-preservation tests**

Implement standard-library `unittest` checks for:

```python
TARGET_SECTIONS = [
    "01-introduction.tex", "02-related-work.tex", "03-data.tex",
    "04-problem.tex", "05-method.tex", "06-experiments.tex",
    "07-results.tex", "08-discussion.tex", "09-threats.tex",
    "10-conclusion.tex",
]
REQUIRED_VALUES = ["403", "290", "134", "125", "1,128", "282"]
REQUIRED_SCOPE = [
    "스모크", "직렬화", "물리", "안전", "Qwen/Qwen3.5-35B-A3B"
]
```

Tests must assert geometry and column gap, no `\author`, local fonts/OFL,
50--200 English abstract words, exactly six keywords, all ten `\input`s,
presence of RQ1--RQ4 and required evidence strings, no source-relative inputs,
no symlinks anywhere under the target, and no raw `\caption{` in compiled
section files.

- [ ] **Step 4: Run the new tests and verify red state**

Run:

```bash
python3 -m unittest -v projects/sequential-coc-verification/paper/manuscript/latex-kiee-review-2022-coc-audit/tests/test_kiee_format.py
```

Expected: failures for missing `main.tex`, style, fonts, sections and captions; no import or syntax error in the test itself.

- [ ] **Step 5: Record the scaffold checkpoint**

Write Task 1 results to `CONVERSION_REPORT.md` after Task 5 creates the report; until then record them in the task report workspace. No Git commit is attempted.

---

### Task 2: KIEE Style, Front Matter, Build Entry Point, and Bibliography

**Files:**
- Create: `projects/sequential-coc-verification/paper/manuscript/latex-kiee-review-2022-coc-audit/kiee-review.sty`
- Create: `projects/sequential-coc-verification/paper/manuscript/latex-kiee-review-2022-coc-audit/main.tex`
- Create: `projects/sequential-coc-verification/paper/manuscript/latex-kiee-review-2022-coc-audit/Makefile`
- Create: `projects/sequential-coc-verification/paper/manuscript/latex-kiee-review-2022-coc-audit/README.md`
- Create: `projects/sequential-coc-verification/paper/manuscript/latex-kiee-review-2022-coc-audit/references.bib`
- Create: `projects/sequential-coc-verification/paper/manuscript/latex-kiee-review-2022-coc-audit/fonts/NotoSerifCJKkr-Regular.otf`
- Create: `projects/sequential-coc-verification/paper/manuscript/latex-kiee-review-2022-coc-audit/fonts/NotoSerifCJKkr-Bold.otf`
- Create: `projects/sequential-coc-verification/paper/manuscript/latex-kiee-review-2022-coc-audit/fonts/OFL.txt`

**Interfaces:**
- Consumes: Task 1 tests; template style/fonts; finalized source front matter and bibliography
- Produces: compilable KIEE document shell and all shared LaTeX interfaces

- [ ] **Step 1: Copy the approved template assets**

Copy `kiee-review.sty`, the two font files, `OFL.txt`, and the Makefile pattern
from the reference template into the target. Extend the copied style, rather
than the source manuscript, with TikZ and these exact source interfaces:

```tex
\usetikzlibrary{arrows.meta,positioning,fit,shapes.geometric,calc}
\definecolor{observed}{RGB}{40,120,90}
\definecolor{derived}{RGB}{40,95,160}
\definecolor{assumed}{RGB}{180,120,35}
\definecolor{blocked}{RGB}{165,55,55}
\definecolor{neutral}{RGB}{70,70,70}
\newcommand{\coc}{\textsc{CoC}\xspace}
\newcommand{\uppaal}{\textsc{UPPAAL}\xspace}
\newcommand{\unknown}{미상\xspace}
\newcommand{\preserve}{보존\xspace}
\newcommand{\reset}{재시작\xspace}
\newcommand{\dedup}{중복 제거\xspace}
```

Preserve the template geometry, fonts, caption macros and section formatting.

- [ ] **Step 2: Create exact KIEE front matter**

Use these titles:

```tex
\kieeenglishtitle{Auditing Temporal and Provenance Contracts in Reasoning-Augmented E2E Autonomous Driving Data: An Analysis with CoC-Nusc and UPPAAL}
\kieekoreantitle{추론 보강형 E2E 자율주행 데이터의 시간·출처 계약 감사: CoC-Nusc와 UPPAAL 기반 분석}
```

Use this English abstract verbatim:

```text
Reasoning-augmented end-to-end autonomous driving datasets pair sensor observations and recorded ego trajectories with retrospective Chain-of-Causation (CoC) annotations. Although useful as semantic supervision, these annotations do not by themselves define how repeated events, candidate deadlines, response evidence, or scene provenance should be interpreted. We present a pre-training audit that compiles timestamped CoC events and ego-motion evidence into candidate temporal contracts and UPPAAL observer models. In a single-event screen, 134 annotation-event candidate contracts were routed as 125 response-consistent cases, four already-satisfied cases, and five review candidates under an exploratory calibrated rule. A separate set of 282 generated models and 1,128 queries validates flag and query serialization rather than real fault detection. Metadata-linked 13-chain outputs use a different parser and detector and are retained only as an implementation smoke test. The results show how repeat policy, detector settings, deadlines, and provenance assumptions influence audit outcomes. They neither establish general CoC faithfulness nor prove physical vehicle safety.
```

Use exactly these six keywords:

```text
Autonomous driving, End-to-end learning, Chain-of-Causation, Timed automata, Model checking, Data provenance
```

- [ ] **Step 3: Include all ten sections and bibliography**

`main.tex` must input `sections/01-introduction` through
`sections/10-conclusion` in order, use `unsrt`, and render the bibliography at
8 pt. It must not contain `\author`.

- [ ] **Step 4: Copy the complete bibliography and document provenance**

Copy the finalized `references.bib` byte-for-byte. `README.md` must identify
the source and template paths, state that both remain unchanged, explain the
independent-copy rule, list `make`/`make test` commands, and repeat the
smoke-test/serialization/safety scope boundaries.

- [ ] **Step 5: Run the tests and verify only section/caption failures remain**

Run the unittest command from Task 1. Expected: geometry, front matter,
abstract, keyword, font, license and bibliography-shell checks pass; missing
section/caption checks still fail.

---

### Task 3: Independent Sections, Figures, and Bilingual Captions

**Files:**
- Create: all ten target `sections/*.tex`
- Create: target `figures/overview-pipeline.tex`
- Create: target `figures/annotation-flow.tex`
- Create: target `figures/method-pipeline.tex`
- Create: target `figures/uppaal-network.tex`
- Create: target `figures/training-routing.tex`

**Interfaces:**
- Consumes: finalized source sections/figures and Task 2 KIEE interfaces
- Produces: content-complete independent manuscript with bilingual captions

- [ ] **Step 1: Copy all finalized section and figure sources**

Copy the ten section files and five TikZ figures into the target. Verify they
are regular files, not symlinks, and contain no `../` input path.

- [ ] **Step 2: Convert all figure captions**

Use `\bifigcaption{Korean}{English}` with these English translations:

1. Procedure for transforming reasoning-augmented E2E driving data into temporal and provenance contract audit inputs.
2. Generation of CoC reasoning annotations and transformation into audit inputs.
3. Proposed method comprising an evidence collector, contract compiler, state observers, and result router.
4. Conceptual UPPAAL network corresponding to `scene-0001-normal`.
5. Proposed pre-training routing based on audit evidence.

Keep each existing Korean caption verbatim as the first argument.

- [ ] **Step 3: Convert every table caption**

Use `\bitablecaption{Korean}{English}` and map the table captions, in source
order, to:

1. Main terminology used in this paper.
2. Comparison of the primary reported evaluation and intervention units in recent VLA studies and this work.
3. Provenance hierarchy of the evaluation data.
4. Evidence levels and permitted claims.
5. Comparison of single-event screening and episode-level auditing.
6. Timed-automata skeleton corresponding to the network in Fig. `uppaal-network`.
7. UPPAAL model families by experiment.
8. Example transformation of `scene-0001` evidence into UPPAAL events; time is in seconds.
9. Mutation oracles and expected failed properties.
10. Recorded inputs and generated scope of the batch-audit block.
11. Experiment blocks, research questions, and interpretation boundaries.
12. Result-to-claim interpretation matrix.
13. Mutation-oracle results for `scene-0001`.
14. Policy- and deadline-based categorization of the five review candidates; physical safety is unknown for all cases.
15. Sensitivity across 27 response-detector configurations.
16. Results of the boundary-carryover negative control.
17. Metadata-mirror eligibility counts and 13-chain smoke outputs from a separate implementation.
18. Proposed pre-training routing according to audit evidence.

The embedded annotation-flow caption is a figure caption and uses the figure
mapping above. Preserve all Korean wording, row values, labels and references.

- [ ] **Step 4: Adapt only width and float mechanics**

Replace IEEE-specific assumptions only where KIEE compilation requires it.
Keep semantic content unchanged. Use `\scriptsize`, adjusted `L{}` widths,
`\resizebox`, `figure*`/`table*`, and `\raggedbottom` only to resolve actual
KIEE layout defects; do not delete rows, figures or explanatory text.

- [ ] **Step 5: Run the full format test suite**

Run the unittest command. Expected: all tests pass, including no raw captions,
all ten sections, RQ/value/scope preservation, no symlinks and no source-relative
inputs.

---

### Task 4: Full Build and Layout Correction

**Files:**
- Modify only as required: target `main.tex`, `kiee-review.sty`, `sections/*.tex`, `figures/*.tex`
- Generate: target `main.pdf`, `main.aux`, `main.bbl`, `main.blg`, `main.log`, `main.out`

**Interfaces:**
- Consumes: complete target manuscript from Task 3
- Produces: valid KIEE PDF with clean blocking diagnostics

- [ ] **Step 1: Run the prescribed build**

Run:

```bash
make -C projects/sequential-coc-verification/paper/manuscript/latex-kiee-review-2022-coc-audit all
```

Expected: tests pass and LuaLaTeX/BibTeX/LuaLaTeX/LuaLaTeX exit 0.

- [ ] **Step 2: Check blocking diagnostics**

Run:

```bash
grep -nE 'Undefined control sequence|Citation.*undefined|Reference.*undefined|There were undefined references|Overfull \\hbox|Overfull \\vbox|Emergency stop|Fatal error' projects/sequential-coc-verification/paper/manuscript/latex-kiee-review-2022-coc-audit/main.log
```

Expected: no matches. Fix the narrowest width/float/caption issue causing each
match and repeat the full build.

- [ ] **Step 3: Validate PDF and render every page**

Use `mutool info` to confirm a valid A4 PDF and page count. Render all pages at
120 dpi into a new `mktemp -d` directory; confirm rendered image count equals
PDF page count.

- [ ] **Step 4: Inspect every rendered page**

Check title/abstract, bilingual captions, Korean glyphs, float ordering,
tables, TikZ labels, bibliography, blank columns and isolated headings. For an
ambiguous figure/table, render that page again at 300 dpi before changing the
source. Rebuild after every source change.

- [ ] **Step 5: Re-run tests and diagnostics after the final visual edit**

Expected: all unittests pass; full build exit 0; no blocker diagnostics; all
pages inspected.

---

### Task 5: Independence Audit and Conversion Report

**Files:**
- Create: `projects/sequential-coc-verification/paper/manuscript/latex-kiee-review-2022-coc-audit/CONVERSION_REPORT.md`
- Verify: every target source and generated PDF

**Interfaces:**
- Consumes: final target manuscript/PDF and source/template snapshots
- Produces: auditable handoff proving independence, preservation and format compliance

- [ ] **Step 1: Audit target independence**

Use `find -type l` and source scans to prove no symlinks or `../` inputs exist.
Hash or compare the source/template files touched by the conversion workflow to
show they remain unchanged.

- [ ] **Step 2: Audit content preservation**

Record RQ1--RQ4, `403 -> 290 -> 134`, `134=125+4+5`, `282×4=1,128`, the
13-chain smoke-test boundary, upstream revision limitation, half-open deadline,
and physical-safety disclaimer locations in the target. Confirm they match the
finalized source manuscript.

- [ ] **Step 3: Write the conversion report**

Include: source/template/target paths, files created, exact front-matter word
and keyword counts, caption counts, test command/output, build commands/exit
codes, blocker-log count, PDF page size/count, page-by-page visual findings,
benign warnings, independence checks and the explicit statement that experiment
code/JSON/source manuscripts were not modified.

- [ ] **Step 4: Run final fresh verification**

Run tests, the complete build, blocker scan, `mutool info`, and fresh all-page
render after the report is written. Record only the fresh outputs.

- [ ] **Step 5: Preserve the workspace state**

Do not delete generated reports or build output because Git history is
unavailable. Report the final target links to the user.

---

## Final Acceptance Checklist

- [ ] Target exists at the exact approved path and is an independent regular-file copy.
- [ ] Both source manuscripts remain unchanged.
- [ ] KIEE geometry, typography, anonymous front matter and six keywords pass tests.
- [ ] English abstract is 50--200 words and preserves all necessary evidence boundaries.
- [ ] All ten sections, five figures, tables, equations, citations and limitations remain.
- [ ] Every compiled figure/table caption is Korean-English bilingual.
- [ ] Tests and full LuaLaTeX/BibTeX build pass.
- [ ] No undefined command/citation/reference or overfull box remains.
- [ ] PDF is valid A4 and every page is visually inspected.
- [ ] Conversion report records content preservation, independence and benign diagnostics.
