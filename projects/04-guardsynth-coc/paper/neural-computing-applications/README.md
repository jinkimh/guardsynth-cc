# Neural Computing and Applications format draft

The active Introduction is [01-introduction-v03-en.tex](01-introduction-v03-en.tex),
translated from the author's revised Korean text on 2026-10-17 and included by
main.tex. It distinguishes constraint compliance from objective-based candidate
selection and defines the preferred-selection score as a percentage of binary
preferred-candidate matches. The preceding
[01-introduction-v02-en.tex](01-introduction-v02-en.tex),
[01-introduction-v01-en.tex](01-introduction-v01-en.tex), and
[01-introduction.tex](01-introduction.tex) are preserved unchanged. Only the
active file is included in the manuscript. The audits below record the sources
and claim boundaries checked for the Introduction. The active Conclusion is
[07-conclusion-v02-en.tex](07-conclusion-v02-en.tex), translated from the revised
Korean conclusion on 2026-10-15 and aligned with the current Introduction and
terminology on 2026-10-17. It is included by main.tex. The preceding
[07-conclusion.tex](07-conclusion.tex) is preserved unchanged. The revision
connects training for rule-dependent choice, constraint case/source
correspondence, and meaning preservation versus model use.

Owner: `guardsynth-coc`. Prepared: 2026-10-09.

For LaTeX Workshop, the active chapters and `main.tex` point to
[ncaa-manuscript-en.tex](ncaa-manuscript-en.tex), a small build entry point
that inputs the sole manuscript source, `main.tex`. Its basename matches
`ncaa-manuscript-en.pdf`, so the root-based View command (`Ctrl+Alt+V`) resolves
the correct output. Its magic comments run `make all`, preserving the
Makefile's local TeX dependency paths; plain `pdflatex` without those paths
can fail to find `cuted.sty`. Build with `Ctrl+Alt+B` from an active manuscript
editor, then view with `Ctrl+Alt+V`. No repository-wide PDF jobname is set.

This separate format draft contains the manuscript title, abstract, keywords,
Introduction, Related Work, Method, Experimental Setup, Results, Discussion, and Conclusion. On 2026-10-09 the title, abstract, keywords, and Introduction were revised
for this journal and now differ from the source manuscript; numerical results are
unchanged. Entries `r6`, `r7`, `r8`, and `r14` were copied from the source bibliography,
and nuScenes, PhysicalAI, and Qwen3-VL references were added. A rewritten Related Work
section is kept in [02-related-work.tex](02-related-work.tex) and included with `\input`;
it reuses `r5`, `r10`, and `r13` and adds fifteen external references. Section references are
converted from IEEE Roman numerals to Springer decimal numbering. The Conclusion
is maintained in [07-conclusion-v02-en.tex](07-conclusion-v02-en.tex).
The author order is Jin Hyun Kim, Yon Vanommeslaeghe, Rahul Mangharam,
Seung Hyun Kong, and Insup Lee. The two additional coauthors were
added on 2026-10-20 at the author's request. Seung Hyun Kong and Insup Lee
are designated as corresponding authors. The author has confirmed all five
authors' participation, final-manuscript approval, author order, and contributions.
Author metadata
is included in both the manuscript and supplementary information; this is not a complete submission.
The preceding-manuscript reference `r4` identifies Jin Hyun Kim as author;
its year and publication status remain pending confirmation.

## Review alignment: claims, checker names, and uncertainty (2026-10-17)

The title now specifies **CoC-Augmented Candidate Selection**: the trained model
selects supplied candidate labels and does not generate CoC or trajectories.
The abstract and Introduction distinguish the broader motivation of interacting
constraints and traffic-rule exceptions from the evaluated single-constraint
learning specifications. Reported learning checks are satisfiability, candidate
admissibility, and logic–rule comparison; the property-query explanation and
qualitative lifecycle checks remain separate.

The continuation claim about fewer violations before position-hold training is
limited to interval-maximum inputs. The fresh-adapter inference-time-rule
comparison is explicitly relative to adapters fine-tuned in a rule-free format;
Discussion records the unresolved contribution of input-format adaptation.
Observation and modeling-assumption errors were not injected. Evidence
correspondence, sentence correspondence, and the added boundary probes are
identified as post-training evaluation additions throughout.

Checker names, P1 natural-language guards, fault names, and jointly wrong
evidence–specification controls are consistent across the main text and
supplement. S6 six-task sample SDs were recomputed with the n−1 denominator
from unrounded per-seed rates in
[the archived temporal-expansion results](../../artifacts/public/paper1-method-preservation-001/temporal-expansion-learning-2026-09-29-001/RESULT.json).
The immutable population-SD fields remain unchanged. Means, counts, prediction
rates, and experimental protocols are unchanged; no new training was run.

## Document-grounded composition diagnostic (2026-10-17)

The main-text composition examples now distinguish documented policy/guidance
from authored states, candidate requests, objectives, and motion assumptions.
The [source catalog](../../artifacts/public/paper1-constraint-composition-001/document-grounded-composition-2026-10-17-002/SOURCE_CATALOG.json)
records eight inspected official documents and two UNECE candidates excluded
because direct official-text retrieval was blocked. NTSB suppression, FHWA
signal timing, Waymo autonomous-driving interlocks, and the restricted Rule 129
exception supply the four executable families. Natural-language and formal
conditions appear together in Method Table `tab:method-composition-sources`.

The [new result](../../artifacts/public/paper1-constraint-composition-001/document-grounded-composition-2026-10-17-002/RESULT.json)
and [source review/report](../../artifacts/public/paper1-constraint-composition-001/document-grounded-composition-2026-10-17-002/REPORT_KO.md)
cover 176 authored configurations, 58 UNSAT and 118 SAT, with 896 queries and
832 independently checked SAT witnesses. Twelve conflicts require three
groups; six other braking cases are already incompatible without suppression.
This is not an accident reconstruction, an estimate of operational conflict
frequency, or a claim that actual laws are mutually inconsistent. Emergency
trigger eligibility, jerk, complete regulations, and scene truth are outside
the evaluated models. Source metadata/paraphrases are preserved, rather than
byte-for-byte original PDF snapshots.

The [runner](../../experiments/paper1_cnl_learning/document_grounded_composition.py)
and [protocol](../../experiments/paper1_cnl_learning/document_grounded_composition_protocol_v0_1.json)
reuse the unmodified Core/SMT execution path. The earlier synthetic diagnostic
below remains a distinct boundary-control task in Supplementary Section S13;
its arbitrary operator deadlines are not represented as real instructions.

## Earlier synthetic source-composition diagnostic (2026-10-17)

A separate post-training logical diagnostic now evaluates combinations of
supplied source conditions; the VLM learning experiments still use individual
constraints. The maintained [runner](../../experiments/paper1_cnl_learning/constraint_composition.py)
and [protocol](../../experiments/paper1_cnl_learning/constraint_composition_protocol_v0_1.json)
reuse the entry/hold learning lowerers and unchanged platform SMT compiler.
[The frozen result](../../artifacts/public/paper1-constraint-composition-001/constraint-composition-2026-10-17-001/RESULT.json)
and [report with source-by-source natural/formal tables](../../artifacts/public/paper1-constraint-composition-001/constraint-composition-2026-10-17-001/REPORT_KO.md)
record all contexts, subsets, witnesses, source IDs, and hashes.

The earlier run uses distinct authored synthetic policy/operator/assumption
records, retained in its frozen case records and report.
Setup and Results use `sec:setup-composition` and `sec:results-composition`;
Supplementary Section S13 records the reference conditions and reproducibility
files. The diagnostic is separate from fault injection and behavioral scores.
It demonstrates bounded incompatibility detection, including conflicts missed
by pairwise checks; legal exceptions, real-world source validity, and continuous
driving safety remain outside its scope. Earlier review notes below predate
this added diagnostic and describe the then single-constraint evaluation.

## Sources

- Content: [current English manuscript](../ieee-access/main.tex) and [bibliography](../ieee-access/references.bib).
- Journal instructions: https://link.springer.com/journal/521/submission-guidelines
- Author metadata: Jin Hyun Kim's name, department, university, email, and street address were
  supplied by the author. Insup Lee's department and email were checked against
  [Penn's faculty listing](https://curf.upenn.edu/rd/internet-medical-things-and-cyber-physical-systems),
  with the address corroborated by a [Penn-hosted publication](https://repository.upenn.edu/bitstreams/5ee907f0-3998-4ba0-8318-8bbb6efcf4f7/download).
  Seung Hyun Kong's email and the Munji-campus address were checked against his
  [KAIST faculty page](https://mo.kaist.ac.kr/en/professor/gong-seung-hyun/);
  the [school website](https://mo.kaist.ac.kr/en/) and
  [curriculum page](https://mo.kaist.ac.kr/education/curriculum/) confirm the school name and postal code.
- Additional coauthors (2026-10-20): Yon Vanommeslaeghe's name, ESE department,
  email, and address were supplied by the author. Rahul Mangharam's ESE
  affiliation and `rahulm@seas.upenn.edu` were verified against his
  [Penn xLAB faculty page](https://xlab.upenn.edu/team/rahul/).
  The [official xLAB contact page](https://xlab.upenn.edu/contact/) confirms
  the ESE mailing address, 200 South 33rd Street, Philadelphia, PA 19104, USA;
  it is shared as affiliation 2 by the two added authors. The office address
  at 3330 Walnut Street is distinct from that departmental mailing address.
- Official template page: https://www.springernature.com/gp/authors/campaigns/latex-author-support
- Download: https://cms-resources.apps.public.k8s.springernature.io/springer-cms/rest/v1/content/18782940/data/v12
- Template release: v3.1, December 2024, as linked by the publisher on 2026-10-09.
- Original ZIP: [template/springer-article-template.zip](template/springer-article-template.zip)
- ZIP SHA-256: `812e76dcaa9c28dc1bff1fb6065d51729b67d4ea140552a05088317414a3ecae`
- Unmodified upstream files: `sn-jnl.cls`, `sn-basic.bst`,
  [template/sn-article.tex](template/sn-article.tex), and
  [template/user-manual.pdf](template/user-manual.pdf).

The document uses `sn-basic` with the `Numbered` option, following the journal's
numbered reference instructions. Class and bibliography-style bytes are unchanged
from the downloaded archive. No journal submission or publication decision is made
by creating this format draft.

## Introduction motivating cases and terminology (2026-10-17)

The v03 Introduction adds three primary sources and reorganizes the
contributions into constraint construction, checking and CNL generation, and
separate behavioral and fault-injection evaluations.

| Citation key | Primary source and evidence location | Supported use and boundary |
|---|---|---|
| NTSB2019Tempe | [NTSB/HAR-19/03](https://www.ntsb.gov/investigations/AccidentReports/Reports/HAR1903.pdf), printed pp. 13–17 and 40–41 | Emergency recognition 1.2 s before impact, 1 s braking suppression ending about 0.2 s before impact, and the absence of maximum allowed braking solely for mitigation. The report supports examining interactions between response timing and safety requirements; it does not establish a formal UNSAT result or attribute the entire accident to constraint composition. Publication year is 2019; the accident occurred in 2018. |
| Cruise2023Recall23E086 | [Manufacturer-submitted NHTSA recall report 23E-086](https://static.nhtsa.gov/odi/rcl/2023/RCLRPT-23E086-7725.PDF), pp. 2–4 | Initial stop followed by a pullover that dragged the pedestrian; collision incorrectly characterized as lateral. The author is Cruise LLC, and NHTSA hosts the filing. Submitted November 7, 2023; the accident occurred October 2, 2023. |
| DfT2015HighwayCode129 | [Official Highway Code](https://www.gov.uk/guidance/the-highway-code/general-rules-techniques-and-advice-for-all-drivers-and-riders-103-to-158), Rule 129 | Prohibition on crossing double white lines with the nearer line solid, with an exception for passing a stationary vehicle when necessary and the road is clear. The omitted-exception consequence is an illustrative inference, not a reported accident. The online manual was first published October 1, 2015, and its displayed update is October 22, 2025; accessed October 17, 2026. |

These cases motivate checking. The reported experiments remain restricted to
the supported specifications and synthetic candidate-selection tasks; no
accident reconstruction or general vehicle-dynamics verification is claimed.
The preferred-selection score retains the same binary reference-label-match
calculation in the archived records. The terminology authority is
[BEHAVIORAL_CONSTRAINT_TERMINOLOGY_NOTES_V01.md](BEHAVIORAL_CONSTRAINT_TERMINOLOGY_NOTES_V01.md).
The active manuscript, tables, figure annotations, and supplementary information
now use its preferred-selection score and constraint-compliance definitions.

## Manuscript terminology and structure alignment (2026-10-17)

The terminology notes incorporate the author's decision to use
**preferred-selection score**, without shortening it to accuracy. PSS is the
mean of binary preferred-candidate matches expressed as a percentage; it is not
a continuous action-quality score. Constraint violation rate (CVR) and rule-pair
accuracy (RPA) remain separate metrics. Constraint-compliant completion is an
auxiliary outcome. Frozen experimental records and their field names are
unchanged.

Section 3 distinguishes supplied behavioral rules, behavioral constraints,
admissible candidates, the supplied synthetic progress score, and reference
labels. The reported learning-specification checks assess satisfiability and
candidate admissibility; they do not optimize progress or establish observation
truth. The setup defines metrics before training and comparison designs.
Results place the common-CNL and training-matched fresh-adapter evaluations
together, followed by continuation, six-task rule use, rule-pair results, and
reasoning controls. Tables retain their numerical cells and labels; automatic
section, equation, and table references follow the reordered material.

Discussion follows constraint construction and checking, specification--sentence
correspondence, and learning conditional selection, then limitations. It makes
clear that the supervised comparisons do not establish superiority over
reinforcement learning, and that the accident examples motivate broader checks
than the supported task specifications evaluate. The Conclusion follows the
same construction, checking, and separate behavioral-evaluation contributions.
The abstract uses the same terminology and remains below 250 words.

## Introduction reference audit (2026-10-15)

Scope: all 12 distinct external references cited in
01-introduction-v02-en.tex. Titles, author information, years, identifiers,
and the supported statements were checked against the primary sources below.
The four added 2026 references are cited as arXiv preprints; no conference or
journal acceptance is inferred. The published nl2spec record and nuScenes
proceedings metadata were completed in references.bib.

| Citation key | Primary source and evidence location | Supported use and boundary |
|---|---|---|
| r1 | [Alpamayo-R1, v2](https://arxiv.org/html/2511.00088v2), abstract and Sections 4–5 | CoC ties observed causal factors to decisions; supervised fine-tuning and reinforcement learning connect reasoning and trajectory prediction. First posted in 2025, revised in 2026. CoC is an example of language reasoning, not a name assigned to every VLM. |
| Wang2026DriveWLA | [DriveWLA, v1](https://arxiv.org/html/2610.17903v1), Sections 1 and 4.1 | Joint future-dynamics, semantic, and trajectory modeling. Posted 2026-10-13. Section 4.1 uses language hidden states without generating text, so it is not cited as a CoC or explanation-generating system. |
| Yan2026ADMemo | [AD-Memo, v1](https://arxiv.org/html/2609.38641v1), abstract and Section 3.1 | Language memory of driving-relevant objects becomes future input. Posted 2026-09-29. This supports decisions across observations, not an unrestricted long-term memory guarantee. |
| Jia2026Bench2DriveVL | [Bench2Drive-VL, v1](https://arxiv.org/html/2604.01259v1), abstract and Section III | Closed-loop evaluation connects VLM reasoning and actions to an interactive driving simulator. Posted 2026-04-01. This is an evaluation framework, not a safety guarantee. |
| You2026Language2Drive | [Language2Drive, v1](https://arxiv.org/html/2610.16634v1), Sections 1, 2.2, and 3 | Matched initial contexts with changed feasible instructions reveal one-sided successes. Posted 2026-10-12. Initial conditions are fixed; subsequent observations evolve with each action. Paired evaluation is not claimed as our invention. |
| r18 | [Drive the Thoughts, v1](https://arxiv.org/html/2608.29583v1), Section V and Table I | The reliable subset contains 100 pairs: 74 consistent and 26 inconsistent. The Introduction's 74% is agreement within this subset, not overall agreement or a road-failure rate. Posted 2026-08-30; evaluated model is Alpamayo 1.5. |
| nvidia2025physicalai | [NVIDIA dataset card](https://huggingface.co/datasets/nvidia/PhysicalAI-Autonomous-Vehicles), Version History and Dataset Owner | Identifies the PhysicalAI input source. Version 25.10 is the initial release, supporting 2025. The card does not establish our diagnostic outcomes or the third-party nuScenes conversion. |
| caesar2020nuscenes | [CVF proceedings record](https://openaccess.thecvf.com/content_CVPR_2020/html/Caesar_nuScenes_A_Multimodal_Dataset_for_Autonomous_Driving_CVPR_2020_paper.html) and accepted paper | CVPR 2020, pp. 11621–11631; all ten authors checked. Identifies the source dataset, not a second model or a native reproduction of Alpamayo on nuScenes. |
| r9 | [Springer CAV 2023 record](https://link.springer.com/chapter/10.1007/978-3-031-37703-7_18) and [author-hosted paper](https://cs.stanford.edu/people/trippel/pubs/cosler_CAV23.pdf), Sections 1 and 3 | Interactive correction of language-fragment/subformula correspondences. LNCS 13965, pp. 383–396, DOI 10.1007/978-3-031-37703-7_18, published 2023-07-18. No claim that it lacks all checks or supports arbitrary semantic equivalence. |
| Xu2018 | [ICML/PMLR record and paper](https://proceedings.mlr.press/v80/xu18h.html), abstract and loss definition | A loss encouraging consistency with logical output constraints; ICML 2018, PMLR 80, pp. 5502–5511. It is not an inference-time output restriction or unconditional compliance guarantee. |
| Wei2022 | [FLAN paper, v5](https://arxiv.org/html/2109.01652v5), abstract and Sections 2–3; [ICLR proceedings record](https://openreview.net/forum?id=gEZrGCozdqR) | Instruction tuning improves zero-shot performance on unseen task types in the reported experiments. ICLR 2022; preprint first posted in 2021. The full text was checked through arXiv because direct OpenReview access presented a browser challenge. |
| qwen2025qwen3vl2b | [Official model card](https://huggingface.co/Qwen/Qwen3-VL-2B-Instruct) and [README history](https://huggingface.co/Qwen/Qwen3-VL-2B-Instruct/commits/main/README.md) | Identifies the 2B instruction model used in our study. README history contains October 2025 commits. The citation is to this checkpoint's card, not a different Qwen technical report or evidence for our fine-tuning results. |

The Introduction's own measurements were checked separately against the
[baseline analysis](../../artifacts/public/paper1-vlm-constraint-baselines-001/vlm-constraint-baseline-analysis-2026-10-12-001/RESULT.json)
and the [learning-specification fault record](../../artifacts/public/paper1-learning-specification-faults-001/learning-specification-faults-2026-10-12-001/RESULT.json).
The 1.56% maximum violation and 86.98% minimum rule-pair accuracy refer to
three-seed means for the fresh CE+CNL pedestrian-entry and two position-hold
conditions. The 288 detected supported faults, 48 accepted valid cases, and
48 missed joint errors are separate specification outcomes. External dataset
and model citations do not serve as evidence for these measurements.
Detailed Alpamayo counts remain in Supplementary Section S1 and their archived
diagnostic reports; the Introduction retains only a short motivating observation.

## Method figures

`render_method_figures.py` writes `figures/method-flow.pdf` (process diagram) and
`figures/input-examples.pdf` (two archived test inputs reproduced verbatim: pedestrian
clearance `test-11000-500` and position hold `test-000-0-2000-interval_maxima`). It needs
matplotlib and Pillow, for example `runtime/alpamayo/ar1_venv/bin/python render_method_figures.py`.

## Edit and build

Edit [main.tex](main.tex), the included section files, and
[references.bib](references.bib), then run:

```sh
make -C projects/04-guardsynth-coc/paper/neural-computing-applications
```

The recipe uses `pdflatex`, `bibtex`, and two further `pdflatex` passes; it does not
require `latexmk`. The working PDF and all auxiliary/log files stay in this directory
beside `main.tex`. Rebuilding updates the same `ncaa-manuscript-en.*` files.

The current minimal TeX Live installation also needs `cuted`, `threeparttable`,
`appendix`, `wrapfig`, and `vruler`. Local build copies in the ignored
`.texlive-local/` directory were extracted without modification from Debian's
`texlive-latex-extra` package (2022.20230122-4); the Makefile searches that directory.
A full TeX Live installation can supply these packages directly.

[PDF preview](ncaa-manuscript-en.pdf).


## Writing conventions and verification (2026-10-09)

Apply these conventions to subsequent revisions of this draft:

- Attach citations to the supported statement with a nonbreaking space, group
  related keys, and place sentence punctuation after the citation:
  `~\cite{r1,r2,r3}.` Avoid detached citations and redundant separate commands.
- When a sentence names an author, attach the citation to that author:
  `Turpin et al.~\cite{Turpin2023} show ...`. Keep method descriptions and
  attribution linked to the appropriate individual reference.
- Use plain sentences and define acronyms at first use in both the abstract and
  the main text, where applicable.
- Identify whether a rule is supplied during training, evaluation, or both.
  Keep Alpamayo trajectory-generation diagnostics distinct from synthetic Qwen
  candidate-selection experiments.
- Distinguish the 2 s and 0.5 s position-hold durations from post-clearance waiting
  rules. Report accuracy separately from violations, with counts and denominators.
- Describe the 0.087 m result as a mean XY trajectory difference, averaged over
  three seeds for each input and rule-input route; it is not a bound on individual
  predictions or a difference between mean positions.
- Use qualified conclusions such as “suggest … should” when warranted by scope.
  Separate the methodological difficulties from limitations of related work.
- Connect reported results to the relevant section. Explain how components
  (i)–(iii) address the three difficulties, and state the empirical findings in
  contribution 3 without implying that specification checks guarantee compliance.
- Compare with the cited traffic-rule, regulation-retrieval, and translation work
  (`r6`, `r7`, `r8`) within their actual scopes. Verify new bibliography metadata
  against primary sources before using it.
- Concentrate the Related Work discussion of GuardSynth's differences in Sections
  2.2, 2.4, and 2.5; keep the Introduction's literature overview brief. Explain
  P1 as direct natural-language constraint augmentation and P2 as the checked
  EBLC-to-CNL path, without attributing behavioral gains to checking alone.

Checked against primary sources:

- `r4`: the [preceding manuscript](../../../01-safety-constrained-coc/paper/manuscript/latex-kiee-review-2022-revision-v02/main.tex)
  has the same title. Its [publication front matter](../../../01-safety-constrained-coc/paper/manuscript/latex-kiee-review-2022-revision-v02/kiee-publication.sty)
  and [author biography](../../../01-safety-constrained-coc/paper/manuscript/latex-kiee-review-2022-revision-v02/sections/09-author-biography.tex)
  identify the sole author as Jin Hyun Kim. The year 2022 in the directory name
  refers to the KIEE template, not the publication year. No confirmed publication
  year, volume, issue, pages, or DOI is recorded in that manuscript.
- `Wei2022`: [FLAN paper](https://arxiv.org/abs/2109.01652) and its
  [ICLR 2022 proceedings record](https://openreview.net/forum?id=gEZrGCozdqR)
  support instruction tuning for generalization to unseen task types. The
  conference year is 2022, although the preprint first appeared in 2021.
- `Hsieh2023`: [ACL Findings record and paper](https://aclanthology.org/2023.findings-acl.507/)
  confirm 2023, pages 8003--8017, and DOI `10.18653/v1/2023.findings-acl.507`.
  Rationales are auxiliary prediction targets, rather than constraint sentences
  supplied as model inputs. Section 2.4 preserves this distinction.
- `Guan2024`: [Deliberative Alignment, Sections 2.2–2.3](https://arxiv.org/html/2412.16339v2)
  uses category-specific versions of a reusable safety policy for completion
  generation and filtering. The policy text is removed from prompts used for
  supervised fine-tuning. Do not describe its training examples as all receiving
  identical policy text. Section 2.4 contrasts this with scene-bound constraint
  instances linked to observations, supplied rules, and assumptions for CoC.

- `caesar2020nuscenes`: CVPR 2020, pp. 11621–11631, confirmed by the
  [CVF proceedings page](https://openaccess.thecvf.com/content_CVPR_2020/html/Caesar_nuScenes_A_Multimodal_Dataset_for_Autonomous_Driving_CVPR_2020_paper.html).
  The existing [arXiv URL](https://arxiv.org/abs/1903.11027) resolves to the same
  work; the preprint's 2019 posting does not change the proceedings year.
- `nvidia2025physicalai`: the
  [official dataset card](https://huggingface.co/datasets/nvidia/PhysicalAI-Autonomous-Vehicles)
  lists version 25.10 as the initial release, supporting year 2025. The card is
  updated over time; this year refers to initial release, not the latest revision.
- `qwen2025qwen3vl2b`: the
  [official model card](https://huggingface.co/Qwen/Qwen3-VL-2B-Instruct) resolves,
  and the [official repository](https://github.com/QwenLM/Qwen3-VL#news) records
  the 2B Instruct release on 2025-10-21, supporting year 2025.
- The [position-hold training report](../../artifacts/public/paper1-position-hold-training-001/position-hold-training-2026-10-08-001/REPORT_KO.md)
  confirms `after_test / interval_maxima / 2.0s` violations of 22/192, 1/192,
  and 0/192 for P0/P1/P2. At 0.5 s, P0 has zero violations but 129/192 correct
  selections, compared with 172/192 and 182/192 for P1/P2. Zero violations do
  not imply full selection accuracy.
- The [converted nuScenes speed report](../../artifacts/restricted/alpamayo-nuscenes-speed-limits-001/speed-limits-2026-10-08-001/REPORT_KO.md)
  gives a largest input–route mean XY difference of 0.0868 m, rounded to 0.087 m.

Footnote 1 stays in the Introduction; the diagnostic protocol is now in Supplementary
Section S1. Reference `r4` still has no confirmed
year or publication metadata. Keep its unpublished status and the known BibTeX
warning rather than guessing a year. This journal draft remains independent of the
parent manuscript's wording.

## Planned section structure

The planned order is Introduction, Related Work, Method, Experimental Setup,
Results, Discussion, and Conclusion (Sections 1–7), without a standalone Background
or Preliminaries section. The roadmap and results references use that planned order.
The current PDF includes Introduction, Related Work, Method, Experimental Setup, Results, Discussion, and Conclusion. The Method was
reintroduced on 2026-10-12 at the author's request from the supplied Korean revision;
Experimental Setup and Results were added from the revised Korean drafts;
Discussion and Conclusion were added from the revised Korean drafts.


## Method integration and verification (2026-10-12)

The English Method is maintained in [03-method.tex](03-method.tex). Its eight
subsections follow the supplied Korean revision. Four tables and two native
LaTeX diagrams use labels and cross-references; implementation version names
and raw schema identifiers are omitted from the semantic specification example.
References `r11` and `r12` are reused from the parent bibliography.

Checked against the maintained experiment sources:

- The pedestrian-entry and position-hold renderers require structural
  validation. Logical outcomes are checked separately; the Method does not
  claim a common solver-controlled rendering or export gate.
- Every interval-maximum candidate description contains both the 0.5 s and
  2.0 s maxima, regardless of the active hold rule. The reference calculation
  uses the original integer coordinates.
- The position-hold P1 template and original CoC differ from the pedestrian
  task. All position-hold conditions receive identical P2 rule text at evaluation;
  the six-task P0 receives no constraint text at training or evaluation.
- The four-layer, 192-case fault-injection evaluation uses a separate temporal
  specification, rather than the pedestrian-entry or position-hold specifications
  used for training. The Abstract and Introduction now identify that scope.
- The explanatory counterexample query includes the specification together with
  the violating condition. The 1 ms learning-specification boundary checks and
  100 ms fault-injection boundary checks remain distinct.

The initial Method integration did not perform new training or fault injection.

## Learning-specification fault injection (2026-10-12)

A subsequent [384-case evaluation](../../artifacts/public/paper1-learning-specification-faults-001/learning-specification-faults-2026-10-12-001/REPORT_KO.md)
tests the actual pedestrian-entry and position-hold specifications used to produce
learning inputs. Each task uses 12 archived contexts under two durations: 24 valid
cases, 144 supported faults, and 24 jointly wrong source--specification controls.
The full suite accepts all valid cases and detects all supported faults; it misses
all joint-error controls. The Abstract, Introduction, contribution 3, and Method
now report this follow-up separately from the initial 192-case experiment.

Existing validators, lowering, renderers, and the SMT compiler are unaltered.
Source correspondence, fixed-grammar sentence parsers, and independent rule probes
were added for the follow-up; do not attribute these additional checks to historical
training runs. The structural/satisfiability/logic--rule subset detects 96/144 faults
per task, and the full suite detects 144/144. No VLM training, inference, or human
labeling was performed. These repeated contexts contain only two distinct rule
settings per task; the experiment does not establish population-level detection
rates or continuous-trajectory safety. The run retains its frozen protocol,
input/output hashes, per-mutation records, and 7,392 concrete probe verdicts.

## Experimental Setup integration (2026-10-12)

Section 4 is maintained in [04-experimental-setup.tex](04-experimental-setup.tex).
Its seven subsections distinguish the fresh-adapter 2-by-2 study (E2), historical
position-hold continuation, the six-task comparison, and pretrained 2B/8B evaluation
(E1). Tables 6--8 cover dataset sizes, information conditions, and the principles
shared with related approaches. Results were integrated subsequently as Section 5.

The text preserves arm-specific versus common-CNL evaluation, identifies the
512-token E1 evaluation as post-hoc, and defines semantic loss over conditional
A--D logits at the first supervised token without restricting generation.
The four-duration temporal record contains 4 satisfiability and 96 boundary-candidate
queries, rather than 100 boundary queries. Rule-free input ceilings are 50% for
the six tasks and 75% for position holding. The reasoning controls produce 1,440
scored predictions per method and 2,880 in total.

References `r16` and `r17` are reused from the IEEE bibliography; the official
8B model card is added as `qwen2025qwen3vl8b`. The Qwen release repository records
the 8B release on 2025-10-15. Detailed procedures are now in the NCA supplementary document described below.

## Results integration (2026-10-12)

Section 5 is maintained in [05-results.tex](05-results.tex). Its ten subsections
follow the supplied Korean revision. Tables 9--15 separate common-CNL evaluation,
pretrained 8B, historical continuation, training-input-matched semantic loss,
the six-task comparison, robustness, and alternative representations. The two
figures reference existing canonical experiment PDFs directly, without copying
them into this paper tree.

The fresh-adapter values, standard deviations, rule-pair scores, and E1 cap-hit
counts are checked against the [completed baseline analysis](../../artifacts/public/paper1-vlm-constraint-baselines-001/vlm-constraint-baseline-analysis-2026-10-12-001/RESULT.json).
The 8B rule-pair values in Table 18 and Supplementary Section S7 are already
recorded in the [original experiment result](../../artifacts/public/paper1-vlm-constraint-baselines-001/vlm-constraint-baselines-2026-10-12-001/RESULT.json),
under `per_seed_metrics` with `model = pretrained_8b`, `evaluation = arm_input`,
and no `duration_ms` field (both durations combined). The separate graph-analysis result omits these fields
for pretrained models. The existing `metrics` function in
[run_vlm_constraint_baselines.py](../../experiments/paper1_external_methods/run_vlm_constraint_baselines.py)
groups rows by `pair_id`, requires two rows per pair, and counts a pair as
correct only when both predictions are correct. Recomputing from
[the archived 8B predictions](../../artifacts/public/paper1-vlm-constraint-baselines-001/vlm-constraint-baselines-2026-10-12-001/pretrained_8b/predictions.jsonl)
reproduces 1/120 pedestrian-entry pairs (0.83%), 33/64 interval-maximum
position-hold pairs (51.56%), and 15/64 XY pairs (23.44%). The same calculation
reproduces the three-seed CE+CNL means of 96.94%, 92.71%, and 86.98%.
Both the original result and 8B prediction file match their archived manifest
hashes. These records provide the calculation provenance without an additional
analysis run or any change to the archived outputs.
Continuation counts use the [position-hold training record](../../artifacts/public/paper1-position-hold-training-001/position-hold-training-2026-10-08-001/REPORT_KO.md).
The six-task, representation, wording, reasoning-prompt, and image-intervention
results use the existing IEEE evidence bundle. The 384-case learning-specification
fault injection is reported separately from the original four-duration temporal
query record. Correspondence checks added after training are not treated as a
cause of the behavioral improvement.

The English text does not infer statistical equivalence from seed standard
deviations. Rule-free input ceilings are explicitly distinguished from the
common-CNL evaluation, where those ceilings no longer constrain identifiability.
Model-size comparisons retain their task-adaptation and output-truncation limits.
The untrained 2B scores and diagnostic strata remain documented in their source
records and in Supplementary Section S7.

## Setup--results coverage corrections (2026-10-13)

The Section 4--5 coverage review was reconciled with the frozen records. Section 4
now distinguishes 720 pedestrian-entry predictions from 384 position-hold
predictions per representation in each fresh-adapter condition. Section 5 reports zero
answer-extraction failures for the fine-tuned evaluations, the 5,376 position-hold
SMT/reference correspondences, and unchanged primary-test violations under a
10 mm tolerance (minimum prohibited overshoot: 22 mm). Regression tolerance
results remain separate.

Supplementary Section S6 adds three individual-seed tables: six primary tasks,
pedestrian-entry representations/robustness, and static/maneuver robustness.
The retained tables contain 54 condition rows, 162 seed cells, and 486 accuracy/violation/
rule-pair values extracted from `temporal-expansion-learning-2026-09-29-001/RESULT.json`
and `multitask-contract-analysis-2026-09-30-001/RESULT.json` under the canonical
`paper1-method-preservation-001` experiment. Protocols confirm seed order
42, 17, 123, and each archived mean was checked against its three seed values.
The supplementary reference to the obsolete Section 4.7 now points to Section 5.9.
No experiment was rerun and no archived measurement was changed.

Section 4 notation was revised on 2026-10-13: candidate-label sets use
`\mathcal{Y}` and `\mathcal{Y}_C`, while `\mathcal{L}` denotes losses.
Reader-facing study names replace internal E1/E2 codes. The obsolete
paragraph-level continuation label was removed and its Section 5 reference
now points to Section 4.4. Figure 3 crops the archived plot's internal-code
heading at inclusion time; its caption supplies the same evaluation context
and the canonical experiment PDF is unaltered.

## Supplementary information (2026-10-13)

[supplementary-information.tex](supplementary-information.tex) is a separate document
(S1–S12) built by `make` together with the manuscript. It adapts the IEEE experimental
supplement to NCA terminology and adds the fresh-adapter seed values, the pretrained-VLM
results, and task-level reasoning-prompt results. Seed-level, pretrained-VLM, reasoning,
regression, and continuation tables were generated from the archived `RESULT.json` and
`comparison_metrics.csv` records and rounded half up to two decimals. Fresh-adapter
standard deviations are sample standard deviations (n−1); the IEEE six-task values are
population standard deviations. Main-text citations use "Supplementary Section S#".

Supplement tidy-up (2026-10-13): S4 is now "Additional Specification Checks",
separating candidate-binding checks in the six-task learning data from the earlier
fault injection on the expression-diversity specification; the duplicated 100-query
and 12-query counts were removed (the former is reported in main-text Section 5.9).
References to main-text sections use `xr-hyper` labels imported from
`ncaa-manuscript-en.aux`, so `make` must build the manuscript before the supplement.
S1 specifies both speed-limit levels and distinguishes the full 6.4 s XY-difference
average from the first-two-second violation window. S12 lists the native-execution
record and restricted diagnostic/lifecycle records as well as the public learning records.

## Discussion integration (2026-10-13)

Section 6 is maintained in [06-discussion.tex](06-discussion.tex), translated
from the author's fourth Korean revision. Its four subsections cover training
constraints and rule-dependent selection, the additional value of checkability,
checked meaning versus learned interpretation, and limitations/future work.
Equation, method, and result references use existing LaTeX labels. The text
retains the 106/79/77 regression violations and distinguishes the post-training
correspondence checks from the behavioral training comparisons. Deliberative
Alignment is described consistently with Section 2.4: reusable policy text is
used in data generation/filtering and removed from supervised fine-tuning inputs.
The author-review notes appended to the Korean draft are not manuscript content.
No results or experiment protocols were changed. The preceding Section 7 is
preserved in [07-conclusion.tex](07-conclusion.tex); the active revision is
[07-conclusion-v02-en.tex](07-conclusion-v02-en.tex). Its controlled comparison
is restricted to CE-only conditions, and source- and sentence-correspondence
checks are identified as having been added after training.



## Removal of shuffled-association results (2026-10-16)

The active manuscript and supplementary information omit the shuffled
case--constraint controls, their setup descriptions, and claims based on them.
Section 5.6 and its table retain rule-pair accuracy; the representation comparison
retains natural-language guards, EBLC-derived CNL, and logical text. The abstract,
Introduction v02, discussion, and Conclusion v02 no longer cite shuffled training
as evidence for the development path. Twelve supplementary result rows were
removed, including ten rows from the three individual-seed tables.
Archived experiment records and preserved earlier introduction/conclusion drafts
are unchanged. No experiment was rerun and no retained measurement was changed.
