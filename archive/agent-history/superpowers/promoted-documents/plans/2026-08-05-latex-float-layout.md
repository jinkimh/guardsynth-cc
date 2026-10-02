# LaTeX Figure and Table Layout Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reduce the large empty areas around pages 5–13, especially the sparse left column previously visible on page 8, while preserving full-width figures and tables.

**Architecture:** First remove the forced page boundary and relax top-float placement without changing content. Rebuild and inspect every page; only if the sparse-column symptom remains, replace the local `\raggedbottom` setting with normal balanced columns. Finally trim excess whitespace inside selected graphics at LaTeX inclusion time and verify float order, readability, and references.

**Tech Stack:** XeLaTeX, two-column LaTeX floats, Make, MuPDF

## Global Constraints

- Keep `figure*` and `table*` elements at two-column width.
- Do not change manuscript text, captions, figure/table numbering, or experimental values.
- Do not add `dblfloatfix` or `stfloats`.
- Do not reduce the printed text size inside figures or tables.
- A layout change is accepted only after every page in the rebuilt PDF is visually inspected.

---

### Task 1: Remove the forced page break and relax float placement

**Files:**
- Modify: `projects/safety-constrained-coc/paper/manuscript/latex-domestic/sections/04-method.tex`
- Modify: `projects/safety-constrained-coc/paper/manuscript/latex-domestic/sections/01-introduction.tex`
- Modify: `projects/safety-constrained-coc/paper/manuscript/latex-domestic/sections/05-experiments.tex`
- Test: `projects/safety-constrained-coc/paper/manuscript/latex-domestic/main.pdf`

**Interfaces:**
- Consumes: existing `figure*`, `table*`, and section order
- Produces: the same manuscript content with LaTeX free to continue Chapter 5 on the remaining page space

- [x] **Step 1:** Record the current 16-page PDF as the visual baseline by rendering pages 1–16 at 72 dpi to `/tmp/coc-layout-before/`.

Run:
```bash
mkdir -p /tmp/coc-layout-before
mutool draw -r 72 -o /tmp/coc-layout-before/page-%d.png main.pdf 1-16
```

- [x] **Step 2:** Delete the final `\clearpage` from `sections/04-method.tex` so Chapter 5 can begin in the remaining space after Chapter 4.

- [x] **Step 3:** Change `[t]` to `[!t]` on `figure*` and `table*` declarations in the three listed section files. Leave single-column tables and figures unchanged during this first pass.

- [x] **Step 4:** Build the manuscript.

Run:
```bash
make all
```

Expected: exit status 0 and `Output written on main.pdf`.

- [x] **Step 5:** Render the new PDF to `/tmp/coc-layout-pass1/` and compare the page containing the start of Chapter 5 with the baseline. Confirm that the previous page-8 sparse-column symptom is removed or materially reduced.

Run:
```bash
mkdir -p /tmp/coc-layout-pass1
mutool draw -r 72 -o /tmp/coc-layout-pass1/page-%d.png main.pdf 1-16
```

### Task 2: Balance columns only if the first pass remains sparse

**Files:**
- Modify conditionally: `projects/safety-constrained-coc/paper/manuscript/latex-domestic/main.tex`
- Test: `projects/safety-constrained-coc/paper/manuscript/latex-domestic/main.pdf`

**Interfaces:**
- Consumes: Task 1 PDF
- Produces: balanced 4–5장 columns without globally stretched discussion/conclusion pages

- [x] **Step 1:** Inspect the two columns on the page containing the start of Chapter 5. The first pass removed the imbalance, so the remaining steps in this task were skipped.

- [x] **Step 2:** Skip removing `\raggedbottom` because Task 1 already balanced the page containing the start of Chapter 5.

- [x] **Step 3:** Skip the second-pass build because no conditional source change was made.

Run:
```bash
make all
mkdir -p /tmp/coc-layout-pass2
mutool draw -r 72 -o /tmp/coc-layout-pass2/page-%d.png main.pdf 1-16
```

- [x] **Step 4:** Retain the Task 1 result and the existing `\raggedbottom` setting.

### Task 3: Remove internal graphic whitespace without resizing content

**Files:**
- Modify: `projects/safety-constrained-coc/paper/manuscript/latex-domestic/figures/generate_figures.py`
- Modify: `projects/safety-constrained-coc/paper/manuscript/latex-domestic/figures/test_generate_figures.py`
- Modify: `projects/safety-constrained-coc/paper/manuscript/latex-domestic/sections/07-discussion.tex`
- Test: `projects/safety-constrained-coc/paper/manuscript/latex-domestic/main.pdf`

**Interfaces:**
- Consumes: existing PNG graphics
- Produces: unchanged visible drawing content with less blank canvas around it

- [x] **Step 1:** Reduce figure 2's `figsize` and vertical coordinate range in `generate_figures.py`, and add a regression test requiring its width/height ratio to exceed 2.45.

- [x] **Step 2:** Add conservative `trim` and `clip` options to `fig05_typed_contract.png` while preserving its current width.

Use:
```tex
\includegraphics[width=0.94\columnwidth,trim=18 22 18 22,clip]{figures/fig05_typed_contract.png}
```

- [x] **Step 3:** Build and visually confirm that no box, arrow, axis label, legend, or caption content is clipped.

- [x] **Step 4:** Leave all other graphics untrimmed.

### Task 4: Top-align float groups and compact the bibliography

**Files:**
- Modify: `projects/safety-constrained-coc/paper/manuscript/latex-domestic/main.tex`
- Test: `projects/safety-constrained-coc/paper/manuscript/latex-domestic/main.pdf`

**Interfaces:**
- Consumes: Tasks 1–3 output
- Produces: top-aligned float groups and a 15-page PDF without an isolated final bibliography entry

- [x] **Step 1:** Set `\@fptop` and `\@dblfptop` to `0pt` so float-dominant pages start at the normal top margin rather than being vertically centered.

- [x] **Step 2:** Apply `\small` only inside a local group around `\bibliography{references}` so all references fit on the conclusion page.

- [x] **Step 3:** Build and confirm that pages 5 and 7 move upward and that the previous one-entry page 16 is removed.

### Task 5: Final verification

**Files:**
- Test: `projects/safety-constrained-coc/paper/manuscript/latex-domestic/main.log`
- Test: `projects/safety-constrained-coc/paper/manuscript/latex-domestic/main.pdf`

**Interfaces:**
- Consumes: Tasks 1–3 output
- Produces: final submission PDF

- [x] **Step 1:** Run a clean full build.

Run:
```bash
make all
```

- [x] **Step 2:** Verify zero fatal errors, undefined references/citations, and overfull boxes.

Run:
```bash
grep -c "LaTeX Error" main.log
grep -c "Undefined control sequence" main.log
grep -c "Reference .* undefined" main.log
grep -c "Citation .* undefined" main.log
grep -c "Overfull \\hbox" main.log
grep -c "Overfull \\vbox" main.log
```

Expected: six zero counts.

- [x] **Step 3:** Render all 15 final pages at 100 dpi and visually check float order, first-reference proximity, clipping, column balance, and the conclusion/reference transition.

Run:
```bash
mkdir -p /tmp/coc-layout-final
mutool draw -r 100 -o /tmp/coc-layout-final/page-%d.png main.pdf 1-16
```

- [x] **Step 4:** Record the accepted changes and completed checks in this plan by marking every executed checkbox.
