# KIEE HWP Review LaTeX Format Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Build an independent anonymous KIEE review-format LaTeX copy from the current paper without modifying `latex-domestic/`.

**Architecture:** Copy the current manuscript into `latex-kiee-review-2022/`, isolate all format rules in `kiee-review.sty`, and replace the front matter and captions only in the copy. Bundle official Noto Serif CJK KR fonts and validate format geometry, bilingual captions, build output, visual layout, and source-tree checksums.

**Tech Stack:** LuaLaTeX, BibTeX, `fontspec`, `geometry`, Python unittest/pytest, MuPDF

## Global Constraints

- Do not write to `papers/paper1-safety-constrained-coc/latex-domestic/`.
- Create a fully independent `papers/paper1-safety-constrained-coc/latex-kiee-review-2022/` tree.
- Use A4 with 18.01 mm left/right margins, 18.99 mm top/bottom margins, and an 8.0 mm column gap.
- Use anonymous review front matter with no author, affiliation, or corresponding-author data.
- Use an English Abstract of 50–200 words and 5–6 English Key Words.
- Preserve Korean body text, equations, experimental values, labels, and citation keys.
- Print Korean and English captions for every compiled figure and table.
- Bundle Noto Serif CJK KR and its SIL Open Font License.
- Do not delete content merely to satisfy the template's recommended page range.

---

### Task 1: Record the original and create the independent tree

**Files:**
- Read: `papers/paper1-safety-constrained-coc/latex-domestic/**`
- Create: `papers/paper1-safety-constrained-coc/latex-kiee-review-2022/**`
- Create: `/tmp/latex-domestic-before.sha256`

**Interfaces:**
- Consumes: the complete current `latex-domestic/` manuscript
- Produces: an independent byte-for-byte starting copy plus an immutable checksum baseline

- [x] **Step 1:** Record hashes of every original source and figure asset.

Run:
```bash
find papers/paper1-safety-constrained-coc/latex-domestic -type f ! -name 'main.aux' ! -name 'main.bbl' ! -name 'main.blg' ! -name 'main.log' ! -name 'main.out' ! -name 'main.pdf' -print0 | sort -z | xargs -0 sha256sum > /tmp/latex-domestic-before.sha256
```

- [x] **Step 2:** Verify that the target directory does not already exist. The failing precondition is intentional: no file may be overwritten silently.

Run:
```bash
test ! -e papers/paper1-safety-constrained-coc/latex-kiee-review-2022
```

- [x] **Step 3:** Copy `latex-domestic/` to `latex-kiee-review-2022/` and remove only copied build artifacts from the new directory.

- [x] **Step 4:** Confirm that no symbolic links point back into `latex-domestic/`.

Run:
```bash
find papers/paper1-safety-constrained-coc/latex-kiee-review-2022 -type l
```

Expected: no output.

### Task 2: Bundle the official serif font and create format regression tests

**Files:**
- Create: `papers/paper1-safety-constrained-coc/latex-kiee-review-2022/fonts/NotoSerifCJKkr-Regular.otf`
- Create: `papers/paper1-safety-constrained-coc/latex-kiee-review-2022/fonts/NotoSerifCJKkr-Bold.otf`
- Create: `papers/paper1-safety-constrained-coc/latex-kiee-review-2022/fonts/OFL.txt`
- Create: `papers/paper1-safety-constrained-coc/latex-kiee-review-2022/tests/test_kiee_format.py`

**Interfaces:**
- Consumes: official `notofonts/noto-cjk` Korean Serif OTF files and LICENSE
- Produces: local font assets and executable tests for geometry, anonymity, abstract length, and bilingual captions

- [x] **Step 1:** Download the Regular and Bold Korean Serif OTF files and `Serif/LICENSE` from the official `notofonts/noto-cjk` repository. Use these official paths:

```text
https://raw.githubusercontent.com/notofonts/noto-cjk/main/Serif/OTF/Korean/NotoSerifCJKkr-Regular.otf
https://raw.githubusercontent.com/notofonts/noto-cjk/main/Serif/OTF/Korean/NotoSerifCJKkr-Bold.otf
https://raw.githubusercontent.com/notofonts/noto-cjk/main/Serif/LICENSE
```

- [x] **Step 2:** Write tests that fail until the new style and front matter exist. The tests must assert:

```python
assert "left=18.01mm" in style
assert "right=18.01mm" in style
assert "top=18.99mm" in style
assert "bottom=18.99mm" in style
assert r"\setlength{\columnsep}{8mm}" in style
assert r"\newcommand{\bifigcaption}" in style
assert r"\newcommand{\bitablecaption}" in style
assert "\\author{" not in main
assert 50 <= abstract_word_count <= 200
assert compiled_caption_count == bilingual_caption_count
```

- [x] **Step 3:** Run the new test and observe failure because `kiee-review.sty` and the new front matter do not yet exist.

Run:
```bash
python3 -m pytest tests/test_kiee_format.py -q
```

Expected: FAIL on missing style/front-matter requirements.

### Task 3: Implement the KIEE page and typography style

**Files:**
- Create: `papers/paper1-safety-constrained-coc/latex-kiee-review-2022/kiee-review.sty`
- Modify: `papers/paper1-safety-constrained-coc/latex-kiee-review-2022/main.tex`

**Interfaces:**
- Consumes: local OTF files and the copied article structure
- Produces: `\makekieefrontmatter`, `\bifigcaption{ko}{en}`, and `\bitablecaption{ko}{en}`

- [x] **Step 1:** Replace the class fallback with `\documentclass[8.5pt,twocolumn]{extarticle}` when `extarticle.cls` exists and `\documentclass[9pt,twocolumn]{article}` otherwise.

- [x] **Step 2:** Implement `kiee-review.sty` with:

```tex
\RequirePackage[a4paper,left=18.01mm,right=18.01mm,top=18.99mm,bottom=18.99mm,headsep=10mm,footskip=10mm]{geometry}
\setlength{\columnsep}{8mm}
\setmainfont[Path=fonts/,UprightFont=NotoSerifCJKkr-Regular.otf,BoldFont=NotoSerifCJKkr-Bold.otf]{Noto Serif CJK KR}
\setmainhangulfont[Path=fonts/,UprightFont=NotoSerifCJKkr-Regular.otf,BoldFont=NotoSerifCJKkr-Bold.otf]{Noto Serif CJK KR}
\linespread{1.15}
```

`\linespread{1.15}` is used with 8.5 pt text to approximate the HWP 150% baseline while avoiding double application of font leading; the rendered baseline distance must be checked visually.

- [x] **Step 3:** Define section formats at 9 pt bold and subsection formats at 8.5 pt bold, numbered as `1` and `1.1`.

- [x] **Step 4:** Define bilingual caption commands. The Korean and English lines share one figure/table number and one `\label`; table captions stay above and figure captions below.

- [x] **Step 5:** Define a one-column front-matter block using `\twocolumn[...]` with 16 pt English title, 14 pt Korean title, 8.5 pt Abstract, and 8.5 pt Key Words.

- [x] **Step 6:** Run `tests/test_kiee_format.py` and verify that geometry and command-definition assertions pass while abstract/caption assertions still fail.

### Task 4: Replace the anonymous front matter

**Files:**
- Modify: `papers/paper1-safety-constrained-coc/latex-kiee-review-2022/main.tex`

**Interfaces:**
- Consumes: `\makekieefrontmatter` from Task 3
- Produces: English/Korean titles, a compliant English Abstract, and six Key Words

- [x] **Step 1:** Set the English title to:

```text
Execution Guards for Improving Safety in Vision-Language Autonomous Driving Models: Safety-Constrained Chain-of-Causation
```

- [x] **Step 2:** Preserve the Korean title:

```text
비전-언어 자율주행 모델의 안전성 향상을 위한 실행 가드: Safety-Constrained Chain-of-Causation
```

- [x] **Step 3:** Use this 147-word Abstract:

```text
Reasoning-oriented vision-language models for autonomous driving use Chain-of-Causation (CoC) traces to connect scene understanding with trajectory prediction. However, requirement-centered CoC statements describe what the vehicle should achieve without fully specifying execution boundaries such as stop lines, minimum clearances, or hold-and-release conditions. This paper proposes Safety-Constrained CoC, which combines the original behavioral objective with explicit execution guards, and introduces a paired-contract benchmark that changes only the guard while preserving the scene, objective, and trajectory candidates. In three-seed experiments with a LoRA-tuned Qwen3-VL-2B-Instruct model, the guard-violation rate in the temporal task decreased from 31.9 percent to zero while safe goal completion and paired-contract accuracy remained perfect. The improvement also appeared in stopping, starting, and lane-change tasks. Errors under harder wording were concentrated in unit-conversion expressions. These results show that a small VLM can learn execution guards without abandoning the intended CoC objective, although they do not establish real-vehicle safety.
```

- [x] **Step 4:** Set six Key Words:

```text
Autonomous driving, Vision-language model, Chain-of-Causation, Execution guard, Trajectory selection, Safety constraint
```

- [x] **Step 5:** Remove the old Korean abstract, `\author`, `\date`, `\maketitle`, and `IEEEkeywords` block from the copy only.

- [x] **Step 6:** Run the format test and confirm anonymity and Abstract word-count checks pass.

### Task 5: Convert every compiled caption to bilingual form

**Files:**
- Modify: `sections/01-introduction.tex`
- Modify: `sections/03-problem.tex`
- Modify: `sections/04-method.tex`
- Modify: `sections/05-experiments.tex`
- Modify: `sections/07-discussion.tex`

**Interfaces:**
- Consumes: existing Korean captions and bilingual macros from Task 3
- Produces: 7 bilingual figure captions and 9 bilingual table captions

- [x] **Step 1:** Replace each compiled figure `\caption{...}` with `\bifigcaption{Korean}{English}`. Use these English meanings in figure order:

1. Comparison of requirement-only CoC and Safety-Constrained CoC with execution guards.
2. Safety-Constrained CoC input, trajectory-candidate selection, and independent verification pipeline.
3. Paired-contract lane-change example with fixed scene, objective, current gap, and candidates but different minimum-gap contracts.
4. Alpamayo-R1 pre-training diagnostic comparing response to added text and response to opposite guard meanings.
5. Results for temporal conditions and multiple driving maneuvers.
6. Auxiliary closed-loop experiment for risk reappearance after release.
7. Four-stage use of a natural-language execution guard in runtime verification.

- [x] **Step 2:** Replace each compiled table `\caption{...}` with `\bitablecaption{Korean}{English}`. Use these English meanings in table order:

1. Types of execution guards in Safety-Constrained CoC.
2. Five representations of CoC and execution guards given to the model.
3. Four trajectory roles in the temporal task and example contract judgments.
4. Main values checked by the independent verifier.
5. Main evaluation metrics and their meanings.
6. Compared conditions, representative results, and interpretation of the main experiments.
7. Separation results for static candidates that achieve the same CoC objective.
8. Three-run mean and standard deviation for stop-hold-release-go temporal conditions.
9. General and hard-expression results for multiple driving maneuvers, reported as three-run mean and standard deviation.

- [x] **Step 3:** Ensure `\label` remains immediately after the bilingual caption command so references keep the same numbers.

- [x] **Step 4:** Run `tests/test_kiee_format.py`; expected result is all format tests passing.

### Task 6: Build documentation and verify the independent manuscript

**Files:**
- Modify: `papers/paper1-safety-constrained-coc/latex-kiee-review-2022/Makefile`
- Modify: `papers/paper1-safety-constrained-coc/latex-kiee-review-2022/README.md`
- Test: `papers/paper1-safety-constrained-coc/latex-kiee-review-2022/main.pdf`

**Interfaces:**
- Consumes: Tasks 1–5 output
- Produces: reproducible PDF, build instructions, and original-tree preservation evidence

- [x] **Step 1:** Update the Makefile to use the existing project venv for figures and XeLaTeX/BibTeX for `main.pdf`.

- [x] **Step 2:** Document HWP-derived dimensions, anonymous-review behavior, local font/OFL source, build commands, and the distinction from `latex-domestic/` in README.md.

- [x] **Step 3:** Build figures, run all tests, and build the full manuscript.

Run:
```bash
make figures
python3 -m pytest tests figures/test_generate_figures.py -q
make all
```

- [x] **Step 4:** Verify zero fatal errors, undefined references/citations, and overfull boxes in `main.log`.

- [x] **Step 5:** Recompute original checksums and compare them with `/tmp/latex-domestic-before.sha256`.

Run:
```bash
find ../latex-domestic -type f ! -name 'main.aux' ! -name 'main.bbl' ! -name 'main.blg' ! -name 'main.log' ! -name 'main.out' ! -name 'main.pdf' -print0 | sort -z | xargs -0 sha256sum > /tmp/latex-domestic-after.sha256
diff -u /tmp/latex-domestic-before.sha256 /tmp/latex-domestic-after.sha256
```

Expected: no diff.

- [x] **Step 6:** Render every output page and visually inspect the HWP-style first page, 8 mm columns, bilingual captions, float placement, clipping, and the conclusion/reference transition.

Run:
```bash
mkdir -p /tmp/kiee-review-pages
mutool draw -r 120 -o /tmp/kiee-review-pages/page-%d.png main.pdf
```

- [x] **Step 7:** Mark every completed checklist item in this plan and report the new PDF path and any remaining format limitations.

## Implementation Notes

- The workspace is not a Git repository, so the approved independent-directory strategy was used without a worktree or branch integration step.
- The installed TeX distribution provides `extarticle` and LuaLaTeX but not `kotex`/`xetexko`. The implementation therefore uses `extarticle[9pt]`, applies an explicit 8.5 pt/12.75 pt body baseline, and loads the bundled Korean OTF files directly with `fontspec`.
- A writable project-local `.texlive-cache/` is used because the execution sandbox does not permit writes to the user TeX cache.
- The source regression tests are runnable with the Python standard library; the full figure and format suite uses the existing project virtual environment.
- Visual inspection covered all 11 rendered pages. The final page contains only the remaining three references and consequently has normal unused space after the bibliography ends.
