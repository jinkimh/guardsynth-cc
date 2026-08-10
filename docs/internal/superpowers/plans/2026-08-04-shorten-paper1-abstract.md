# Paper 1 Abstract Shortening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reduce the Korean abstract to about half its current length and open with the role of CoC in training driving VLMs such as Alpamayo-R1.

**Architecture:** Modify only the abstract in `main.tex`. Preserve the proposal, the most important multi-seed evidence, the hard-test result, and the scope limitation while removing duplicated task and metric descriptions.

**Tech Stack:** LaTeX, Make

## Global Constraints

- Begin with CoC as an intermediate reasoning signal connecting scene understanding to trajectory generation in R1-like VLM training.
- Preserve the temporal requirement-only baseline and proposed-method violation rates.
- Retain the actual-vehicle-safety limitation and verifier requirement.

---

### Task 1: Shorten and verify the abstract

**Files:**
- Modify: `papers/paper1-safety-constrained-coc/latex-domestic/main.tex`

**Interfaces:**
- Consumes: Existing Korean abstract and reported experiment values.
- Produces: A shorter Korean abstract compiled into the existing paper PDF.

- [x] **Step 1: Replace the abstract while preserving the key numerical evidence.**
- [x] **Step 2: Compare the before/after character counts and confirm the new opening sentence.**
- [x] **Step 3: Run `make all` in the LaTeX directory and require exit status 0.**
