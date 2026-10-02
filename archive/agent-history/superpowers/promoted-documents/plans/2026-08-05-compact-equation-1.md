# Compact Equation 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move the final constraint in Equation (1) onto its second line without changing the mathematical meaning.

**Architecture:** Edit only the `aligned` environment for Equation (1). Keep the objective on the first row and place both feasibility constraints on the second row.

**Tech Stack:** LaTeX, KCI domestic-journal template, Make

## Global Constraints

- Preserve the equation number and `eq:selection` label.
- Preserve both `Goal` and `Sat` constraints exactly.
- Do not change surrounding prose or later equations.

---

### Task 1: Compact Equation (1)

**Files:**
- Modify: `projects/safety-constrained-coc/paper/manuscript/latex-domestic/sections/03-problem.tex`
- Test: `projects/safety-constrained-coc/paper/manuscript/latex-domestic/main.pdf`

**Interfaces:**
- Consumes: the existing `aligned` form of Equation (1)
- Produces: a two-row equation with the objective followed by both constraints

- [x] **Step 1: Confirm the existing equation has three rows**

  Inspect the source and verify that `Goal` and `Sat` are on separate rows.

- [x] **Step 2: Merge the two constraint rows**

  Replace the two rows with:

  ```tex
  \mathrm{s.t.}\quad &\mathrm{Goal}(\tau,R)=1,\quad \mathrm{Sat}(\tau,G)=1.
  ```

- [x] **Step 3: Verify the source structure**

  Confirm that Equation (1) now has two rows and still contains both constraints.

- [x] **Step 4: Build and inspect the paper**

  Run `make all` in `projects/safety-constrained-coc/paper/manuscript/latex-domestic` and confirm a successful build with no undefined references or overfull boxes.
