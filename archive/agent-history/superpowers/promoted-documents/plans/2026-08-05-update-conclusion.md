# Conclusion Update Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Align the conclusion with the abstract, introduction research questions, experiment results, and discussion scope.

**Architecture:** Replace the English-heavy two-paragraph conclusion with three Korean-centered paragraphs covering problem/proposal, findings, and limitations/future work. Preserve the manuscript structure and verify the final page layout.

**Tech Stack:** LaTeX, XeLaTeX, Make

## Global Constraints

- Use terminology already defined in Chapters 4–6.
- Include the key temporal and hard-expression results.
- Do not claim real-vehicle safety or trained Alpamayo-R1 performance.
- Keep the conclusion concise enough to fit before the references without an isolated fragment.

---

### Task 1: Rewrite and verify the conclusion

**Files:**
- Modify: `projects/safety-constrained-coc/paper/manuscript/latex-domestic/sections/08-conclusion.tex`
- Test: `projects/safety-constrained-coc/paper/manuscript/latex-domestic/main.pdf`

**Interfaces:**
- Consumes: abstract, introduction RQs, Chapter 5 results, Chapter 6 scope
- Produces: a three-paragraph conclusion aligned with the manuscript

- [x] **Step 1:** Rewrite the problem and proposal paragraph.
- [x] **Step 2:** Add the main experimental findings and their interpretation.
- [x] **Step 3:** Add scope limitations and concrete next steps.
- [x] **Step 4:** Build the full manuscript and inspect the conclusion/reference transition.
