# Paper 1 Abstract Results Refinement Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the abstract's dense metric list with one representative comparison and a concise interpretation.

**Architecture:** Modify only the result-and-limitation sentences in the abstract. Preserve the reported effect, tested maneuver scope, unit-conversion failure mode, and external-validity limitation.

**Tech Stack:** LaTeX, XeLaTeX, Make

## Global Constraints

- Retain only the representative `31.9\%` to `0\%` guard-violation comparison.
- State that goal completion was preserved without repeating its exact score.
- Mention stop/driving and lane-change tasks, unit-conversion errors, and the need for an independent trajectory verifier.

---

### Task 1: Refine and verify the abstract result summary

**Files:**
- Modify: `papers/paper1-safety-constrained-coc/latex-domestic/main.tex`

**Interfaces:**
- Consumes: Results already reported in the paper and the approved wording specification.
- Produces: A concise abstract and an updated `main.pdf`.

- [x] **Step 1: Replace the metric-heavy sentences with the approved summary.**
- [x] **Step 2: Confirm the abstract contains the representative comparison and no old metric list.**
- [x] **Step 3: Run `make all` and require exit status 0.**
