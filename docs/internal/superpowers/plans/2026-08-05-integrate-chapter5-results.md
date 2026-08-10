# Integrate Chapter 5 Experiments and Results Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce a self-contained Chapter 5 that explains every experiment, result, and interpretation, with readable tables and non-overlapping figures.

**Architecture:** Merge the compiled content of Chapters 5 and 6 into `05-experiments.tex`, remove the separate results input from `main.tex`, and regenerate result figures from the existing JSON/CSV sources using wider horizontal layouts.

**Tech Stack:** LaTeX, Python, Matplotlib, unittest, Make

## Global Constraints

- Preserve all reported numerical values and caveats.
- Use Korean condition names where possible.
- Do not claim real-vehicle safety from synthetic candidate-selection experiments.
- Every experiment subsection must state purpose, comparison, result, and meaning.
- No figure text, tick label, legend, or annotation may overlap.

---

### Task 1: Add figure-generation regression checks

**Files:**
- Create: `papers/paper1-safety-constrained-coc/latex-domestic/figures/test_generate_figures.py`
- Modify: `papers/paper1-safety-constrained-coc/latex-domestic/figures/generate_figures.py`

**Interfaces:**
- Consumes: existing temporal and maneuver JSON summaries
- Produces: separate R1, temporal/pair, and release-reversal figures with descriptive labels

- [x] **Step 1: Write checks for the new output files, wide layouts, and descriptive release-reversal labels**
- [x] **Step 2: Run the checks and confirm they fail against the old figure layout**
- [x] **Step 3: Refactor the figure generator and create the new figures**
- [x] **Step 4: Run the checks and confirm they pass**
- [x] **Step 5: Inspect every regenerated figure at original resolution**

### Task 2: Integrate experiment design and results

**Files:**
- Modify: `papers/paper1-safety-constrained-coc/latex-domestic/sections/05-experiments.tex`
- Modify: `papers/paper1-safety-constrained-coc/latex-domestic/main.tex`
- Retain uncompiled source: `papers/paper1-safety-constrained-coc/latex-domestic/sections/06-results.tex`

**Interfaces:**
- Consumes: the current experiment design and reported result values
- Produces: one compiled `실험 및 결과` chapter

- [x] **Step 1: Add an overall experiment summary table**
- [x] **Step 2: Rewrite each experiment using purpose, comparison, result, and meaning paragraphs**
- [x] **Step 3: Move detailed result tables and new figures next to their experiments**
- [x] **Step 4: Remove the separate results input from `main.tex`**
- [x] **Step 5: Verify every numerical claim against the old results chapter**

### Task 3: Build and visually inspect the paper

**Files:**
- Test: `papers/paper1-safety-constrained-coc/latex-domestic/main.pdf`

**Interfaces:**
- Consumes: the integrated LaTeX chapter and regenerated figures
- Produces: the final compiled manuscript

- [x] **Step 1: Run the complete LaTeX build**
- [x] **Step 2: Check errors, undefined references, and overfull boxes**
- [x] **Step 3: Render every page containing Chapter 5 and inspect table/figure placement**
- [x] **Step 4: Re-read the chapter for result-meaning continuity and unnecessary axis explanations**
