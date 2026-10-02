# Problem Definition Expansion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Explain how Table 1 guard types compose into concrete Safety-Constrained CoCs.

**Architecture:** Refine Section 3 terminology, retain the constrained trajectory-selection formulation, and add a composition rule plus pedestrian-yield and lane-change examples after Table 1. Clarify that Table 1 is a guard library rather than an automatic complete safety specification.

**Tech Stack:** LaTeX, XeLaTeX, Make

## Global Constraints

- Preserve Equation 1, the Table 1 label, and the existing evaluation metrics.
- Map each concrete S-C CoC example to relevant Table 1 guard types.
- Do not imply that every guard type applies to every scene or that the taxonomy is a complete road-safety specification.

---

### Task 1: Expand Section 3 and verify the paper

**Files:**
- Modify: `projects/safety-constrained-coc/paper/manuscript/latex-domestic/sections/03-problem.tex`

**Interfaces:**
- Consumes: Existing selection formulation and Table 1 taxonomy.
- Produces: A compositional definition, two concrete S-C CoC examples, and updated `main.pdf`.

- [x] **Step 1: Confirm the new example subsection is absent.**
- [x] **Step 2: Rewrite Section 3 with the composition rule and examples.**
- [x] **Step 3: Verify labels, examples, guard mappings, and `make all`.**
