# Chapter 6 Clarity Rewrite Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rewrite Chapter 6 with the terms established in Chapters 4–5 and connect every interpretation to a concrete experiment result.

**Architecture:** Preserve the seven discussion topics but replace English-heavy headings and prose with plain Korean explanations. Translate Figure 7 through the existing generator and verify the complete manuscript.

**Tech Stack:** LaTeX, Python, Matplotlib, unittest, XeLaTeX

## Global Constraints

- Preserve all scientific cautions and scope limitations.
- Use the terms basic CoC, execution guard, CoC-integrated form, paired contract, independent verifier, and shield consistently in Korean.
- Do not claim real-vehicle safety or the inherent superiority of natural language.
- Keep Figure 7 readable in one column.

---

### Task 1: Translate and simplify Figure 7

**Files:**
- Modify: `projects/safety-constrained-coc/paper/manuscript/latex-domestic/figures/test_generate_figures.py`
- Modify: `projects/safety-constrained-coc/paper/manuscript/latex-domestic/figures/generate_figures.py`

**Interfaces:**
- Produces: `fig05_typed_contract.png` and `fig05_typed_contract.pdf`

- [x] **Step 1:** Add a regression check for a readable Figure 7 output and its generated Korean stage data.
- [x] **Step 2:** Run the check and confirm the old English-only figure fails.
- [x] **Step 3:** Generate the four Korean stages using the approved Chapter 4–5 terms.
- [x] **Step 4:** Run the complete figure test suite and inspect the figure at original resolution.

### Task 2: Rewrite Chapter 6

**Files:**
- Modify: `projects/safety-constrained-coc/paper/manuscript/latex-domestic/sections/07-discussion.tex`

**Interfaces:**
- Consumes: Chapters 4–5 terminology and results
- Produces: seven plain-language discussion subsections and the revised Figure 7 caption

- [x] **Step 1:** Rewrite the CoC/guard role and CoC-integrated-form interpretation.
- [x] **Step 2:** Rewrite numerical verification and runtime-shield implications.
- [x] **Step 3:** Rewrite the three validity discussions as concrete scope questions.
- [x] **Step 4:** Remove unexplained English terminology and align Figure 7 references.

### Task 3: Verify the manuscript

**Files:**
- Test: `projects/safety-constrained-coc/paper/manuscript/latex-domestic/main.pdf`

**Interfaces:**
- Consumes: revised Chapter 6 and Figure 7
- Produces: compiled, visually checked manuscript

- [x] **Step 1:** Run the figure tests and full LaTeX build.
- [x] **Step 2:** Check errors, undefined references, and overfull boxes.
- [x] **Step 3:** Render and inspect every page containing Chapter 6.
- [x] **Step 4:** Confirm Chapter 7 does not begin before Figure 7 and Chapter 6 discussion are complete.
