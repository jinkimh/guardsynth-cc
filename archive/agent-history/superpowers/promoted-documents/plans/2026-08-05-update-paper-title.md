# Update Paper Title Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the ambiguous goal-preservation phrase with a title that directly states safety improvement as the purpose and execution guards as the mechanism.

**Architecture:** Change only the Korean title text in `main.tex`; preserve the line break before the proposed method name and leave the paper content unchanged.

**Tech Stack:** LaTeX, KCI domestic-journal template, Make

## Global Constraints

- Use the approved title: `비전-언어 자율주행 모델의 안전성 향상을 위한 실행 가드: Safety-Constrained Chain-of-Causation`.
- Preserve `Safety-Constrained Chain-of-Causation` exactly.
- Verify the rendered title does not overflow or break awkwardly.

---

### Task 1: Replace and verify the paper title

**Files:**
- Modify: `projects/safety-constrained-coc/paper/manuscript/latex-domestic/main.tex`
- Test: `projects/safety-constrained-coc/paper/manuscript/latex-domestic/main.pdf`

**Interfaces:**
- Consumes: the approved Korean and English title text
- Produces: the rebuilt domestic-journal manuscript PDF

- [x] **Step 1: Replace the title in `main.tex`**
- [x] **Step 2: Build the complete manuscript with `make all`**
- [x] **Step 3: Check LaTeX errors, undefined references, and overfull boxes**
- [x] **Step 4: Inspect the rendered first page**
