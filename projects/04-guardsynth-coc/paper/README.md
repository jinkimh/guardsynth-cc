# GuardSynth manuscript

Current content revision: `manuscript-revision-2026-09-30-001`; English-only layout update: `manuscript-layout-2026-09-30-001`. Korean and supplementary PDFs are unchanged. Earlier PDF snapshots remain preserved.

The current English version was updated in place at the author's request to add concise overviews to Related Work, Background, Proposed Method, Experimental Setup, Results, and Discussion. Introduction and Conclusion are unchanged. No new output directory was created. For explicitly authorized in-place revisions, use the current recipe's `--update-current` option; its checks allow only these six overview paragraphs in addition to the recorded layout changes.

| Document | Korean | English |
|---|---|---|
| Integrated manuscript | [PDF](../../../artifacts/projects/guardsynth-coc/public/paper1-method-preservation-001/manuscript-revision-2026-09-30-001/ieee-access-manuscript-ko.pdf) | [IEEE Access PDF](../../../artifacts/projects/guardsynth-coc/public/paper1-method-preservation-001/manuscript-layout-2026-09-30-001/ieee-access-manuscript-en.pdf) |
| Detailed experiments | [Source](IEEE_ACCESS_EXPERIMENTS_SUPPLEMENT_V01_KO.md) · [PDF](../../../artifacts/projects/guardsynth-coc/public/paper1-method-preservation-001/manuscript-revision-2026-09-30-001/ieee-access-experiments-supplement-v01-ko.pdf) | [Source](IEEE_ACCESS_EXPERIMENTS_SUPPLEMENT_V01_EN.md) · [PDF](../../../artifacts/projects/guardsynth-coc/public/paper1-method-preservation-001/manuscript-revision-2026-09-30-001/ieee-access-experiments-supplement-v01-en.pdf) |
| Methodology | [Source](IEEE_ACCESS_METHODOLOGY_V01_KO.md) | [Source](IEEE_ACCESS_METHODOLOGY_V01_EN.md) |
| Experimental main text | [Source](IEEE_ACCESS_EXPERIMENTS_V01_KO.md) | [Source](IEEE_ACCESS_EXPERIMENTS_V01_EN.md) |
| Discussion | [Source](IEEE_ACCESS_DISCUSSION_V01_KO.md) | [Source](IEEE_ACCESS_DISCUSSION_V01_EN.md) |

The section Markdown files are the editable authoring sources. `main.tex` is the synchronized English integration entry point; it no longer contains the historical temporal-only draft. [Build snapshot](../../../artifacts/projects/guardsynth-coc/public/paper1-method-preservation-001/manuscript-revision-2026-09-30-001/build_manuscript.py) and [source manifest](../../../artifacts/projects/guardsynth-coc/public/paper1-method-preservation-001/manuscript-revision-2026-09-30-001/RUN_MANIFEST.json) record inputs. English uses the official IEEE Access template; Korean is a two-column author-review edition.

## Contribution and terminology

- CoC means Chain of Causation; EBLC means Evidence-Bound Lifecycle Contracts; CNL means Controlled Natural Language.
- P0: CoC alone. P1: our existing natural-language constraints appended to CoC. P2: the same rule content developed through EBLC, checks, and CNL generation.
- The primary empirical comparison is P1/P2 versus P0. P1–P2 is an internal development-path comparison, not competition with an external method.
- The method explicitly follows **task → constraint fields → actual logical condition → generated CNL → evaluation verdict**.
- Scene measurements, supplied rules, and modeling assumptions have separate roles. CNL follows the original CoC in the requirement text; labels and solver verdicts are not model-input hints.
- Supported specification error injection is in scope as a quality evaluation. EBLC test-generation systems, runtime monitoring, real-road extraction validation, and vehicle deployment remain outside this paper.

## Preceding manuscript

The author identified [revision v01](../../01-safety-constrained-coc/paper/manuscript/latex-kiee-review-2022-revision-v01/main.pdf), titled *Guard-Aware Trajectory Candidate Selection for Vision-Language Autonomous Driving: Safety-Constrained Chain-of-Causation*, as the preceding manuscript. It already proposes natural-language guards, lifecycle elements, paired contracts, and the task families. The present contribution develops a traceable source/field/logic/CNL interface. Reused generators and scoring principles are distinguished from newly executed experiments. Publication details are pending; no DOI, publication year, or venue is invented.

## Source organization

I Introduction; II Related Work; III Background; IV Proposed Method; V Experimental Setup; VI Results; VII Discussion; VIII Conclusion. The experimental Markdown contains both V and VI and is split at subsection B during integration. Bibliographic numbers and table numbers are global in the integrated PDF; local standalone-section labels remain in editable Markdown.

The earlier methods/settings package is a detailed historical evidence package, not the authority for the current prose or table layout. Current claims are governed by the maintained sections and their frozen source records.

## Remaining author checks

Confirm the author list, affiliations, biographies, funding, preceding manuscript citation, and disclosures of related submission/publication. AI drafting assistance is disclosed in the integrated draft. This is an author-review manuscript, not an assertion of submission readiness. Experiments and archived operational criteria have not been changed.

## Build and verification

The current English layout is reproduced by [build_layout.py](../../../artifacts/projects/guardsynth-coc/public/paper1-method-preservation-001/manuscript-layout-2026-09-30-001/build_layout.py). It reads `main.tex`, preserves the previous snapshot, checks substantive text/caption equality and Korean-file hashes, then compiles only English. Figures 6–7 are narrower, figure 8 and table 11 fit one column, and end-page columns are reflowed. It does not regenerate bilingual Markdown or experimental results.

To compile the synchronized English `main.tex`, run `pdflatex -interaction=nonstopmode -halt-on-error /home/jinhyun/prj_ws/prj_jin/guardsynth-cc/projects/04-guardsynth-coc/paper/main.tex` twice **from the revision artifact directory** linked above. That directory contains the official IEEE Access class, fonts, styles, and figures. The parent IEEEtran class is retained in `ieee-access-template/`; see its provenance README. Paths in this author-review snapshot are local absolute paths; prepare a portable source bundle before submission.

The frozen build recipe records bilingual generation; it intentionally refuses to overwrite a completed run containing `RESULT.json`. Use a new run for later revisions. [Verification report](../../../artifacts/projects/guardsynth-coc/public/paper1-method-preservation-001/manuscript-revision-2026-09-30-001/REPORT_KO.md) records checks and remaining warnings.
