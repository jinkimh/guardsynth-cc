# Abstract Scope Simplification Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the abstract's detailed unit-conversion and verifier discussion with a clear statement of the demonstrated effect and experimental scope.

**Architecture:** Modify only the closing sentences of the abstract in `main.tex`. Keep the cross-task finding, learning interpretation, and external-validity limitation.

**Tech Stack:** LaTeX, XeLaTeX, Make

## Global Constraints

- Remove unit-conversion and independent-verifier details from the abstract.
- Preserve the limitation that actual vehicle safety remains unverified.
- Use the user-approved three-sentence wording.

---

### Task 1: Simplify and verify the abstract ending

**Files:**
- Modify: `papers/paper1-safety-constrained-coc/latex-domestic/main.tex`

**Interfaces:**
- Consumes: Approved Korean abstract ending.
- Produces: Updated abstract and `main.pdf`.

- [x] **Step 1: Confirm the revised scope sentence is initially absent.**
- [x] **Step 2: Replace the detailed closing sentences with the approved text.**
- [x] **Step 3: Verify the new text, confirm removed phrases are absent, and run `make all`.**
