# Figure 1 Explanation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the approved interpretation of Figure 1 to the introduction.

**Architecture:** Insert one paragraph immediately after the Figure 1 environment. Preserve the existing figure, label, caption, and following paired-contract explanation.

**Tech Stack:** LaTeX, XeLaTeX, Make

## Global Constraints

- Explain the red, gray, and green trajectory candidates.
- Connect requirement-only CoC to Safety-Constrained CoC without claiming complete safety.
- Use the existing straight-double-quote convention.

---

### Task 1: Add and verify the Figure 1 explanation

**Files:**
- Modify: `papers/paper1-safety-constrained-coc/latex-domestic/sections/01-introduction.tex`

**Interfaces:**
- Consumes: Existing `fig:concept` label and approved Korean paragraph.
- Produces: Updated introduction and `main.pdf`.

- [x] **Step 1: Confirm the explanation is absent.**
- [x] **Step 2: Insert the paragraph after Figure 1.**
- [x] **Step 3: Verify the reference and run `make all`.**
