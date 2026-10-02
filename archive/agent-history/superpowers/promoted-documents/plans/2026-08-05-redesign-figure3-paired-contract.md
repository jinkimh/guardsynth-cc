# Figure 3 Paired-Contract Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the ambiguous portrait Figure 3 with a readable Korean diagram that holds the scene and candidates fixed while changing only the minimum-gap contract.

**Architecture:** Extend the existing figure-generation regression test to assert the output layout and semantic CSV boundary. Refactor only `figure_pair()`, then align the Chapter 4 prose and caption with the visual data flow.

**Tech Stack:** Python, Matplotlib, unittest, LaTeX

## Global Constraints

- The scene and candidates appear once and remain fixed.
- Only the 5.5 m versus 9.0 m contract changes.
- Text, boxes, and arrows must not overlap.
- Do not claim what the requirement-only model selects inside the conceptual figure.

---

### Task 1: Protect the paired-contract figure interface

**Files:**
- Modify: `projects/safety-constrained-coc/paper/manuscript/latex-domestic/figures/test_generate_figures.py`
- Modify: `projects/safety-constrained-coc/paper/manuscript/latex-domestic/figures/generate_figures.py`

**Interfaces:**
- Consumes: two contract rows with fixed candidates A and B
- Produces: `fig03_paired_contract.png`, `fig03_paired_contract.pdf`, and `data/paired_contract_example.csv`

- [x] **Step 1:** Add a test requiring a width/height ratio above 1.8 and the two expected semantic CSV rows.
- [x] **Step 2:** Run the test and confirm it fails because the old figure is portrait and lacks candidate verdict fields.
- [x] **Step 3:** Replace `figure_pair()` with the approved shared-scene/shared-candidate layout.
- [x] **Step 4:** Run the full figure test suite and confirm it passes.
- [x] **Step 5:** Inspect Figure 3 at original resolution.

### Task 2: Align the paper explanation and verify the PDF

**Files:**
- Modify: `projects/safety-constrained-coc/paper/manuscript/latex-domestic/sections/04-method.tex`
- Test: `projects/safety-constrained-coc/paper/manuscript/latex-domestic/main.pdf`

**Interfaces:**
- Consumes: the redesigned Figure 3
- Produces: a consistent Korean explanation and compiled manuscript

- [x] **Step 1:** Rewrite the paired-contract paragraph and caption around fixed inputs, changed contract, verdict, and selected candidate.
- [x] **Step 2:** Build the complete paper.
- [x] **Step 3:** Check LaTeX errors, undefined references, and overfull boxes.
- [x] **Step 4:** Render and visually inspect the page containing Figure 3.
