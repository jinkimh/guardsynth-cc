# CoC–Guard Distinction Sentence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add one abstract sentence explaining how Safety-Constrained CoC differs from requirement-only CoC.

**Architecture:** Insert the approved sentence immediately after the method-and-benchmark proposal sentence in `main.tex`. Do not change any reported results or limitations.

**Tech Stack:** LaTeX, XeLaTeX, Make

## Global Constraints

- Use the approved contrast between what behavior to achieve and when that behavior is permitted, prohibited, or released.
- Keep the addition to one sentence.

---

### Task 1: Add and verify the distinction sentence

**Files:**
- Modify: `projects/safety-constrained-coc/paper/manuscript/latex-domestic/main.tex`

**Interfaces:**
- Consumes: The approved Korean sentence and existing abstract.
- Produces: Updated abstract and `main.pdf`.

- [x] **Step 1: Confirm the sentence is absent before editing.**
- [x] **Step 2: Insert the approved sentence after the proposal sentence.**
- [x] **Step 3: Confirm exactly one occurrence and run `make all`.**
