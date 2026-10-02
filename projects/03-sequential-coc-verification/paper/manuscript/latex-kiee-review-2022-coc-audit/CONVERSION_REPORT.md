# KIEE anonymous-review copy: conversion and final audit

> Historical record: this report describes the initial 2026-08-05 format
> conversion.  Its title, abstract, page-count, hashes, and content-preservation
> statements are not specifications for the current revised manuscript.  The
> current publication copy is identified in `README.md` and `main.tex`.

## Scope and provenance

This directory is an independent, anonymous KIEE 2022 review-format copy of
the finalized manuscript. It was created from the following read-only inputs:

- Content source: `projects/03-sequential-coc-verification/paper/manuscript`
- KIEE format reference: `projects/01-safety-constrained-coc/paper/manuscript/latex-kiee-review-2022`
- Independent target: `projects/03-sequential-coc-verification/paper/manuscript/latex-kiee-review-2022-coc-audit`

The target owns regular-file copies of the manuscript shell, KIEE style,
bibliography, ten sections, five TikZ figures, local fonts and licenses, tests,
and build entry point. It has no source-relative TeX input or symbolic-link
dependency on either input directory. The source manuscript, reference
template, experiment code, JSON artifacts, and other research evidence were
not modified by this conversion.

Pre-conversion preservation manifests are retained outside the target at:

- `.superpowers/sdd/2026-08-05-kiee-coc-audit-copy/source-before.sha256`
- `.superpowers/sdd/2026-08-05-kiee-coc-audit-copy/template-before.sha256`

The final audit recomputes the content-source manifest while explicitly
excluding this nested target directory, so creating the review copy cannot
produce a false source-manuscript change.

## What the target contains

| Component | Target-owned artifact | Conversion status |
|---|---|---|
| KIEE document shell | `main.tex`, `kiee-review.sty`, `Makefile` | New KIEE anonymous-review shell; A4 two-column formatting |
| Front matter | `main.tex` | Approved bilingual title, English abstract, and six English keywords |
| Manuscript body | `sections/01-introduction.tex` through `sections/10-conclusion.tex` | Independent copies of all ten finalized sections |
| Figures | `figures/*.tex` (five files) | Independent, byte-identical TikZ figure copies |
| Bibliography | `references.bib` | Byte-for-byte independent copy of the finalized bibliography |
| Fonts | `fonts/NotoSerifCJKkr-Regular.otf`, `fonts/NotoSerifCJKkr-Bold.otf`, `fonts/OFL.txt` | Local reproducible CJK typography and font license |
| Checks | `tests/test_kiee_format.py` | Twelve structural/content-preservation checks |
| Build output | `main.pdf`, `main.aux`, `main.bbl`, `main.blg`, `main.log`, `main.out` | Retained reproducibility evidence because Git history is unavailable |

The KIEE style retains the reference-template geometry and typography:
A4; 18.01 mm left/right margins; 18.99 mm top/bottom margins; two columns;
8 mm column gap; 8.5 pt body type on 12.75 pt leading. The source is anonymous:
there is no `\\author` command.

## Front matter and caption adaptation

The English title is:

> *Auditing Temporal and Provenance Contracts in Reasoning-Augmented E2E Autonomous Driving Data: An Analysis with CoC-Nusc and UPPAAL*

The Korean title is:

> *추론 보강형 E2E 자율주행 데이터의 시간·출처 계약 감사: CoC-Nusc와 UPPAAL 기반 분석*

The English abstract is the approved 154-word text in `main.tex`. It contains
no citation, reference, footnote, or equation and ends with the explicit scope
boundary that the work neither establishes general CoC faithfulness nor proves
physical vehicle safety. The exact six keyword entries are: Autonomous driving;
End-to-end learning; Chain-of-Causation; Timed automata; Model checking; and
Data provenance.

The only semantic-format conversion inside copied sections is caption wrapping:

- 5 figure captions use `\\bifigcaption{Korean}{English}`;
- 18 table captions use `\\bitablecaption{Korean}{English}`;
- 0 compiled raw `\\caption{...}` commands remain.

Korean captions were retained verbatim as the first argument. English second
arguments use the approved mapping in the implementation plan. Apart from
these 23 bilingual caption wrappers, one KIEE layout-only change was necessary:
the long parquet path in Section 3 uses the breakable `\\path` interface rather
than an unbreakable monospaced run. No prose claim, table row, equation,
label, citation, reported value, research question, or limitation was changed.

## Content-preservation audit

The table records where the final target preserves the central evidence,
boundaries, and interpretations from the finalized source.

| Required content / limitation | Target location | Preserved interpretation |
|---|---|---|
| RQ1--RQ4 | `sections/01-introduction.tex`, lines 23--26 | Conversion, policy/deadline sensitivity, provenance/episode scope, and formal-observer value remain distinct questions. |
| `403 → 290 → 134` candidate path | `sections/03-data.tex`, lines 47--49; `sections/06-experiments.tex`, lines 18--20 | The audited cohort is a direction-explicit annotation-event subset, not all annotations or independent responses. |
| `134 = 125 + 4 + 5` routing | `sections/03-data.tex`, line 49; `sections/07-results.tex`, lines 65--76 | The five are review candidates under an exploratory calibrated rule, not confirmed defects. |
| `282 × 4 = 1,128` | `sections/06-experiments.tex`, lines 20 and 31--36; `sections/07-results.tex` | This remains flag/query serialization regression, not real fault detection. |
| 13-chain outputs | `sections/06-experiments.tex`, lines 48--50; `sections/07-results.tex`, lines 152--183 | A different parser and detector generate these outputs; they remain implementation smoke records only. |
| Upstream-revision limitation | `sections/03-data.tex`, line 53 | The Qwen/Qwen3.5-35B-A3B name is retained, but immutable model snapshot/tag/hash and labeler commit are unavailable. |
| Half-open deadline | `sections/04-problem.tex`, lines 16 and 58; `sections/07-results.tex`, line 100 | Response must start in `[τ_i, τ_i + D_i)`; equality at the deadline is not accepted. |
| Physical-safety disclaimer | `sections/01-introduction.tex`, line 37; `sections/04-problem.tex`, line 30; `sections/09-threats.tex`, lines 5--26; `sections/10-conclusion.tex`, line 8 | The audit is not a collision-avoidance, safe-distance, control-synthesis, closed-loop, or deployable-vehicle safety proof. |

The target also retains the separation between direct RQ evidence and weaker
implementation records: the `scene-0001` synthetic observer tests support
known-mutation discrimination, while the cohort serialization and 13-chain
records do not become general detector, faithfulness, or physical-safety claims.

## Vendored PGF/TikZ runtime and licenses

The host TeX Live 2022 installation lacked `tikz.sty`. To make the five
target-owned TikZ figures reproducibly buildable, the target vendors PGF 3.1.10
in `.texlive-local/` (506 regular files; approximately 6.3 MiB). The runtime
was installed with `tlmgr` from the frozen official TeX Live 2022 repository:

`https://ftp.math.utah.edu/pub/tex/historic/systems/texlive/2022/tlnet-final`

`.texlive-local/tlpkg/tlpobj/pgf.tlpobj` records PGF revision 65553 and license
metadata `lppl1.3c`, `gpl2`, and `fdl`. The referenced license directory
`.texlive-local/doc/generic/pgf/licenses/` contains the upstream umbrella
notice, GPL-2.0, LPPL-1.3c, GFDL-1.2, and the code/documentation manifests,
copied verbatim from official PGF Git tag 3.1.10,
commit `dceb378b263061856b9a21082e5dc6fffdcdf494` (Release 2023-01-15).
The target Makefile prepends this runtime through `TEXINPUTS` while retaining
normal TeX search paths. It is a required build dependency, not a cache.

## Fresh final verification

The following commands were run after this report was created. All build and
validation commands exited successfully; the empty diagnostic scan is wrapped
with `|| true` because a clean `grep` result otherwise exits with status 1.

| Check | Fresh command | Outcome |
|---|---|---|
| Structural/content tests | `python3 -m unittest -v projects/03-sequential-coc-verification/paper/manuscript/latex-kiee-review-2022-coc-audit/tests/test_kiee_format.py` | 12/12 passed in 0.064 s |
| Complete prescribed build | `make -C projects/03-sequential-coc-verification/paper/manuscript/latex-kiee-review-2022-coc-audit all` | LuaLaTeX → BibTeX → LuaLaTeX → LuaLaTeX completed; 14-page `main.pdf` (379,188 bytes) |
| Blocking log scan | `(grep -nE 'Undefined control sequence|Citation.*undefined|Reference.*undefined|There were undefined references|Overfull \\hbox|Overfull \\vbox|Emergency stop|Fatal error' .../main.log || true)` | 0 matches |
| PDF validation | `mutool info .../main.pdf` | Valid PDF-1.5; 14 pages; media box `[0 0 595.276 841.89]` (A4) |
| All-page render | `mutool draw -r 120 -o /tmp/kiee-coc-audit-task5-render-7lxmYt/page-%02d.png .../main.pdf 1-14` | 14/14 PNG files produced and inspected |
| Source/template preservation | recomputed SHA-256 manifests vs. the two preflight manifests | source: 30/30 unchanged; template: 71/71 unchanged |
| Independence | `find <target> -type l`; TeX source-relative input scan | 0 symbolic links; 0 escaping input/include/subfile references |

For this audit build, the PDF SHA-256 is
`0c6aa8d6088da0331761d7b92f586bc346ab78f5b129f2ddbe6775e5bf25f696`.
The PDF metadata contains build timestamps, so rebuild hashes are
timestamp-dependent and are not expected to be deterministic. Recompute this
checksum after every rebuild rather than treating this value as a permanent
artifact identifier.

### Page-by-page visual audit

All 14 freshly rendered pages were inspected at high detail. Pages 1--3 have
the anonymous bilingual title/abstract, early figures and Table 1--3 in normal
reading order; Korean glyphs, English text and bilingual captions are legible.
Pages 4--6 contain the provenance/data tables, equations and problem/method
text without clipping, overlap or isolated headings. Pages 7--8 show both wide
TikZ diagrams, Tables 7--9 and the experiment transition with readable labels,
caption order and in-bounds floats. Pages 9--12 contain Tables 10--18, results,
the routing figure and discussion/threats text; wide tables remain in bounds,
columns do not collide, and no avoidable blank column or float reversal was
observed. Pages 13--14 complete the conclusion and two-column bibliography
without clipping, broken Korean glyphs, overlap, or an unintended blank page.

The final log has 160 underfull hboxes and 9 underfull vboxes, attributable to
justified Korean prose, narrow table/listing cells, identifiers, and bibliography
entries in the required two-column format. It has 10 `LaTeX Font Warning`
lines: 8 specific substitution warnings and 2 summary warnings. They are
non-blocking and were visually audited; Noto Serif CJK KR has no
italic/small-cap face, and nearest available math sizes are selected. The log
has 0 missing-character notices. These are not undefined
commands/citations/references, overflow, clipping, or a layout collision.

## Reproducibility handoff

Run `make test` and `make all` from this directory. The final PDF is
`main.pdf`; the structural tests, log, bibliography output, source/template
manifests, and this report provide the audit trail in lieu of unavailable Git
history. Generated TeX/font caches are intentionally not retained; no cache
directory or archive is required to rebuild the target.
