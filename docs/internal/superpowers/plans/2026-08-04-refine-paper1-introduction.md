# Paper 1 Introduction Refinement Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Align the introduction with the abstract and replace awkward English mixing with clear Korean terminology.

**Architecture:** Replace the prose, research questions, contribution list, and figure caption in `01-introduction.tex` using the approved design. Preserve all citations, four research questions, five contributions, and the scope limitation.

**Tech Stack:** LaTeX, XeLaTeX, Make

## Global Constraints

- Keep model names and the VLM, CoC, and Safety-Constrained CoC identifiers.
- Define technical terms once in Korean and English, then use Korean.
- Use a single hyphen in Korean compound terms such as `비전-언어`.
- Do not strengthen claims beyond the completed experiments.

---

### Task 1: Rewrite and verify the introduction

**Files:**
- Modify: `papers/paper1-safety-constrained-coc/latex-domestic/sections/01-introduction.tex`

**Interfaces:**
- Consumes: Approved introduction design and existing citations.
- Produces: Refined introduction and updated `main.pdf`.

- [x] **Step 1: Confirm the approved opening is absent.**
- [x] **Step 2: Replace the introduction with the approved wording.**
- [x] **Step 3: Verify citations, question/contribution counts, terminology, and `make all`.**
