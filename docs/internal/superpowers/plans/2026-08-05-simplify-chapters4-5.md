# Chapters 4–5 Clarity Rewrite Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rewrite Chapters 4 and 5 so each method and experiment is explained through motivation, controlled change, concrete outcome, meaning, and limitation without changing the scientific content.

**Architecture:** Preserve the LaTeX section structure, tables, figures, labels, and numerical results. Rewrite prose in place, then build and visually inspect the affected pages.

**Tech Stack:** LaTeX, XeLaTeX, Make

## Global Constraints

- Preserve every reported number, table, figure, label, and citation.
- Do not strengthen claims beyond candidate-selection experiments.
- Explain specialist terms at first use and prefer Korean wording where it remains precise.
- Keep the four-part experiment structure in Chapter 5.

---

### Task 1: Rewrite Chapter 4 method explanation

**Files:**
- Modify: `papers/paper1-safety-constrained-coc/latex-domestic/sections/04-method.tex`

**Interfaces:**
- Consumes: the current method, Figure 2–3, and Tables 2–5
- Produces: a plain-language explanation consistent with the unchanged method

- [x] **Step 1:** Rewrite the chapter introduction and end-to-end flow.
- [x] **Step 2:** Clarify the five input conditions and shuffled-control comparison.
- [x] **Step 3:** Replace Section 4.3 with the approved one-scene/two-problem explanation.
- [x] **Step 4:** Clarify candidate rotation, answer generation, metrics, and the boundary between learned compliance and real safety.
- [x] **Step 5:** Re-read all labels and references against the revised prose.

### Task 2: Rewrite Chapter 5 experiment explanation

**Files:**
- Modify: `papers/paper1-safety-constrained-coc/latex-domestic/sections/05-experiments.tex`

**Interfaces:**
- Consumes: unchanged experiment tables, figures, and numerical findings
- Produces: experiment narratives using purpose, comparison, result, meaning, and limitation

- [x] **Step 1:** Clarify how the sequence of experiments closes successive weaknesses.
- [x] **Step 2:** Rewrite the R1 diagnosis and minimum-learning experiment.
- [x] **Step 3:** Rewrite the static, temporal, and multi-maneuver experiments.
- [x] **Step 4:** Rewrite the closed-loop auxiliary experiment and distinguish it from the VLM tests.
- [x] **Step 5:** Verify every numerical token remains represented in the revised chapter.

### Task 3: Verify the manuscript

**Files:**
- Test: `papers/paper1-safety-constrained-coc/latex-domestic/main.pdf`

**Interfaces:**
- Consumes: revised Chapters 4 and 5
- Produces: a readable, warning-free compiled manuscript

- [x] **Step 1:** Run the complete LaTeX build.
- [x] **Step 2:** Check LaTeX errors, undefined references, and overfull boxes.
- [x] **Step 3:** Render every page containing Chapters 4 and 5.
- [x] **Step 4:** Visually inspect paragraph, table, figure, and caption flow.
