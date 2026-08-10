# Rewrite Chapter 4 Method Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete Chapter 4 with an easy-to-follow explanation of Safety-Constrained CoC, paired contracts, candidate labels, model learning, independent verification, and scope.

**Architecture:** Rewrite the method chapter around the data flow shown in Figure 2. Move the brief metric list from Chapter 3 into the expanded method chapter and replace ambiguous micro-world A/B/C/D condition names in Chapters 5 and 6.

**Tech Stack:** LaTeX, KCI domestic-journal template, Make

## Global Constraints

- Prefer clear Korean terms and define necessary English terms once.
- Preserve the reported experiment design and numerical results.
- Do not claim real-vehicle safety guarantees.
- Explain that candidate letters are rotated and have no fixed behavioral meaning.

---

### Task 1: Rewrite the method chapter

**Files:**
- Modify: `papers/paper1-safety-constrained-coc/latex-domestic/sections/04-method.tex`
- Modify: `papers/paper1-safety-constrained-coc/latex-domestic/sections/03-problem.tex`

**Interfaces:**
- Consumes: the formal selection rule and guard taxonomy from Chapter 3
- Produces: a complete narrative method flowing into Chapter 5

- [x] **Step 1: Add the overall method flow and explain Figure 2**
- [x] **Step 2: Explain the five input representations in a comparison table**
- [x] **Step 3: Explain paired contracts and Figure 3**
- [x] **Step 4: Add a table explaining the four physical trajectory roles and rotating A/B/C/D labels**
- [x] **Step 5: Explain model training, target construction, and independent verification**
- [x] **Step 6: Define evaluation metrics and the runtime-safety boundary**

### Task 2: Remove the A/B/C/D naming collision

**Files:**
- Modify: `papers/paper1-safety-constrained-coc/latex-domestic/sections/05-experiments.tex`
- Modify: `papers/paper1-safety-constrained-coc/latex-domestic/sections/06-results.tex`

**Interfaces:**
- Consumes: the existing micro-world conditions A, B, C, C2, and D
- Produces: descriptive Korean condition names without changing values

- [x] **Step 1: Replace abbreviated condition names in the experiment description**
- [x] **Step 2: Replace abbreviated condition names in the result interpretation**

### Task 3: Build and inspect the manuscript

**Files:**
- Test: `papers/paper1-safety-constrained-coc/latex-domestic/main.pdf`

**Interfaces:**
- Consumes: the revised LaTeX sources
- Produces: a readable, fully referenced PDF

- [x] **Step 1: Run the full LaTeX build**
- [x] **Step 2: Check errors, undefined references, and overfull boxes**
- [x] **Step 3: Render and inspect all pages containing Chapter 4**
- [x] **Step 4: Re-read Chapter 4 for undefined terms and factual mismatches**
