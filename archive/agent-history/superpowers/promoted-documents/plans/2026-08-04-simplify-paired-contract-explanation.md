# Paired-Contract Explanation Simplification Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rewrite the paired-contract benchmark paragraph in plain Korean without changing its experimental meaning.

**Architecture:** Replace one paragraph in the introduction. Explain the controlled variables, the changed execution condition, why scene memorization fails, and how guard compliance is isolated.

**Tech Stack:** LaTeX, XeLaTeX, Make

## Global Constraints

- Preserve the paired-contract benchmark logic.
- Replace unexplained permissive/restrictive terminology with plain-language descriptions.
- Preserve the distinction between behavior-goal recognition and guard compliance.

---

### Task 1: Rewrite and verify the paragraph

**Files:**
- Modify: `projects/safety-constrained-coc/paper/manuscript/latex-domestic/sections/01-introduction.tex`

**Interfaces:**
- Consumes: Approved Korean replacement paragraph.
- Produces: Updated introduction and `main.pdf`.

- [x] **Step 1: Confirm the revised paragraph is absent.**
- [x] **Step 2: Replace the existing paired-contract explanation.**
- [x] **Step 3: Verify replacement and run `make all`.**
