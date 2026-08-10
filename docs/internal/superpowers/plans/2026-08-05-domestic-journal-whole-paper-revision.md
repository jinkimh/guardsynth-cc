# Domestic Journal Whole-Paper Revision Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** CoC-Nusc와 UPPAAL 실험의 실제 증거 범위에 맞추어 국내 저널 원고의 제목, 연구 질문, 방법, 결과 해석과 한계를 하나의 시간·출처 계약 감사 논리로 재구성한다.

**Architecture:** `main.tex`은 제목·요약·주요어와 절 포함 관계를 담당하고, 열 개의 절 파일은 각각 문제 간극, 선행 연구, 증거, 계약, 관찰자, 실험, 결과, 활용, 타당성 위협과 결론을 담당한다. 모든 절은 네 연구 질문(RQ1 변환 타당성, RQ2 판정 민감도, RQ3 출처·에피소드, RQ4 정형화의 부가가치)에 연결하며, 원자료·합성 변이·메타데이터 미러의 증거 수준을 혼합하지 않는다.

**Tech Stack:** XeLaTeX, IEEEtran, BibTeX, TikZ, latexmk, GNU Make, shell 기반 정적 검사

## Global Constraints

- 승인된 설계는 `docs/superpowers/specs/2026-08-05-domestic-journal-whole-paper-revision-design.md`이다.
- 기존 실험 수치와 생성된 결과 파일은 변경하지 않고 새로운 실험도 추가하지 않는다.
- 중심 명제는 CoC의 일반적 충실도 또는 차량 안전성 검증이 아니라, 저장된 CoC-trajectory 주석의 시간·출처 계약 감사이다.
- `PASS/FAIL`은 `계약 통과/검토 후보`로 쓰며 안전/위험 레이블로 해석하지 않는다.
- $D=3$초는 규범적 안전 기한이 아니라 후보 시간 계약의 분석 설정이다.
- ego speed 기반 응답은 자차 움직임 응답 증거이며 액추에이터 명령이나 충돌 위험 측정이 아니다.
- 합성 변이 결과는 검사기 내부 타당성 자료이며 실제 데이터 오류 빈도 또는 일반 검출률이 아니다.
- 메타데이터 미러 기반 13개 체인은 예비 실험이며 공식 장기 시퀀스 gold set이 아니다.
- 수치는 `403 -> 290 -> 134 -> 130+4`, `134 = 125+4+5`, `282×4 = 1,128`로 모든 절에서 일치시킨다.
- 13개 strict chain 결과는 4개 체인 전체 질의 통과, 9개 체인 검토, 후보 기한 실패 8, 응답 도달성 실패 7, 경계 predicate 위반 0으로 쓴다.
- 최신 연구는 우선권을 주장하지 않고 각 논문의 보고 범위만 기술한다.
- 그림·표의 실험 수치와 의미를 바꾸지 않으며, 본문 배치와 설명만 새 RQ 구조에 맞춘다.
- 편집 과정에서 사용자 소유의 관련 없는 변경을 덮어쓰지 않는다.

---

## File Responsibility Map

- `papers/demestic-journal/main.tex`: 제목, 약 30% 축약한 요약, 주요어, 전역 명령과 절 포함 순서
- `papers/demestic-journal/sections/01-introduction.tex`: 최신 문제 간극, 중심 명제, 네 RQ와 기여
- `papers/demestic-journal/sections/02-related-work.tex`: 최신 8개 연구를 포함한 연구군 비교와 차별성
- `papers/demestic-journal/sections/03-data.tex`: CoC 생성 절차, 선택 흐름, 증거 수준과 구성 타당성
- `papers/demestic-journal/sections/04-problem.tex`: 후보 시간 계약, 감사 의무, 응답 증거와 반복 정책 정의
- `papers/demestic-journal/sections/05-method.tex`: 수집기, 계약 컴파일러, 상태 관찰자, 결과 router와 UPPAAL 역할
- `papers/demestic-journal/sections/06-experiments.tex`: A/B/C 세 실험 블록, RQ 대응, 독립변수·고정조건·출력
- `papers/demestic-journal/sections/07-results.tex`: RQ 순서의 결과와 주장-근거 행렬
- `papers/demestic-journal/sections/08-discussion.tex`: 학습 전 감사 활용, 안전 레이블과의 차이, 정형화의 가치
- `papers/demestic-journal/sections/09-threats.tex`: 여덟 종류의 타당성 위협
- `papers/demestic-journal/sections/10-conclusion.tex`: 문제·방법·결과·범위를 세 문단으로 종합
- `papers/demestic-journal/references.bib`: 최신 연구 8개와 기존 정형기법 참고문헌
- `papers/demestic-journal/main.pdf`: 최종 빌드 산출물

---

### Task 1: Baseline and Evidence Ledger

**Files:**
- Read: `papers/demestic-journal/main.tex`
- Read: `papers/demestic-journal/sections/01-introduction.tex` through `10-conclusion.tex`
- Read: `papers/demestic-journal/references.bib`
- Read: `artifacts/results/public/chunk-0000-94/uppaal-cohort-verification-result.json`
- Read: `artifacts/results/public/multiscene-chain/uppaal-loop-batch-all-strict-1s.json`
- Create: `papers/demestic-journal/CLAIM_EVIDENCE_AUDIT.md`

**Interfaces:**
- Consumes: approved whole-paper revision design and immutable experiment artifacts
- Produces: a single claim/evidence ledger used by Tasks 2–8

- [ ] **Step 1: Snapshot the existing worktree state**

Run:

```bash
git status --short
git diff -- papers/demestic-journal
```

Expected: record pre-existing modified and untracked files in `CLAIM_EVIDENCE_AUDIT.md`; do not discard, overwrite or automatically stage those changes.

- [ ] **Step 2: Record the current manuscript baseline**

Run:

```bash
cd papers/demestic-journal
make all
grep -E "Output written on|Warning|Overfull|Undefined" main.log
pdfinfo main.pdf | grep -E "Pages|Page size"
```

Expected: XeLaTeX completes; record page count, undefined references, and overfull boxes in `CLAIM_EVIDENCE_AUDIT.md` without treating pre-existing warnings as new failures.

- [ ] **Step 3: Verify the two result artifacts**

Run:

```bash
jq '{scenes:(.scenes // .items // [] | length), models:.summary.total_models, queries:.summary.total_query_evaluations}' artifacts/results/public/chunk-0000-94/uppaal-cohort-verification-result.json
jq '.summary // {items:(.items|length)}' artifacts/results/public/multiscene-chain/uppaal-loop-batch-all-strict-1s.json
```

Expected: the artifact fields support 94 scenes, 282 models, 1,128 query evaluations and the 13-chain totals used by the approved design. If field names differ, inspect with `jq 'keys'` and record the exact JSON paths rather than inferring values.

- [ ] **Step 4: Write the claim/evidence ledger**

Create `CLAIM_EVIDENCE_AUDIT.md` with these fixed columns:

```markdown
| Claim ID | Manuscript claim | Direct artifact/evidence | Allowed interpretation | Prohibited interpretation | Target section |
```

Include at minimum CE-01 through CE-10: selection flow, 125+4+5 routing, preserve/reset reversals, 27 detector settings, 282 mutation models, 1,128 queries, synthetic orphan response, local continuity negative control, 13-chain pilot, and script 13/13 agreement.

- [ ] **Step 5: Verify ledger arithmetic and prohibited terms**

Run:

```bash
grep -nE "403|290|134|130|125|282|1,128|13/13" papers/demestic-journal/CLAIM_EVIDENCE_AUDIT.md
grep -nE "안전 데이터|위험 데이터|실제 오류 검출률|차량 안전 보장" papers/demestic-journal/CLAIM_EVIDENCE_AUDIT.md
```

Expected: all required values are present; prohibited interpretations appear only in the `Prohibited interpretation` column.

- [ ] **Step 6: Commit the evidence baseline**

```bash
git add papers/demestic-journal/CLAIM_EVIDENCE_AUDIT.md
git commit -m "docs: audit evidence for domestic journal revision"
```

---

### Task 2: Title, Abstract, Introduction, and Research Questions

**Files:**
- Modify: `papers/demestic-journal/main.tex`
- Modify: `papers/demestic-journal/sections/01-introduction.tex`
- Read: `papers/demestic-journal/CLAIM_EVIDENCE_AUDIT.md`

**Interfaces:**
- Consumes: CE-01 through CE-10 and the four approved RQs
- Produces: the exact thesis and vocabulary followed by all later sections

- [ ] **Step 1: Establish a failing textual baseline**

Run:

```bash
grep -n "판단--반응 시간 일관성 검증" papers/demestic-journal/main.tex
grep -nE "연구 질문|RQ[1-5]" papers/demestic-journal/sections/01-introduction.tex
```

Expected: the old title is found and the introduction does not yet implement exactly four approved RQs.

- [ ] **Step 2: Replace the title and compress the abstract**

Set the title exactly to:

```tex
\title{추론 보강형 E2E 자율주행 데이터의 시간·출처 계약 감사: CoC-Nusc와 UPPAAL 기반 분석}
```

Rewrite the abstract as five functional units: problem, method, 94-scene result, sensitivity/13-chain pilot, and scope limitation. Preserve only the decisive figures `134`, `125+4+5`, `282`, `1,128`, and `13`; state explicitly that the result is a pre-training protocol audit rather than physical safety or independent CoC-faithfulness evidence.

- [ ] **Step 3: Rewrite the introduction around the residual research gap**

Use this argument order:

1. CoC supplies semantic supervision to reasoning-augmented E2E learning.
2. Recent work already evaluates grounding, faithfulness, interventions, perturbations and action correction.
3. The remaining problem is how retrospective timestamped annotations are combined under repeat, deadline, response-lineage and scene-provenance policies.
4. `scene-0001` motivates preserve/reset policy sensitivity without being called an unsafe case.
5. CoC is trajectory-conditioned retrospective annotation, so same-trajectory agreement is not independent causal validation.
6. State RQ1–RQ4 verbatim from the approved design and list one evidence-bounded contribution per RQ.

- [ ] **Step 4: Run terminology and RQ checks**

Run:

```bash
grep -n "시간·출처 계약 감사" papers/demestic-journal/main.tex
grep -nE "RQ1|RQ2|RQ3|RQ4" papers/demestic-journal/sections/01-introduction.tex
grep -nE "최초|유일|안전성을 보장|위험한 샘플" papers/demestic-journal/main.tex papers/demestic-journal/sections/01-introduction.tex
```

Expected: new title and four RQs are found; no priority or safety-guarantee claim is found.

- [ ] **Step 5: Build and commit**

```bash
make -C papers/demestic-journal all
git add papers/demestic-journal/main.tex papers/demestic-journal/sections/01-introduction.tex
git commit -m "docs: reframe domestic paper around contract auditing"
```

Expected: build succeeds without undefined references introduced by this task.

---

### Task 3: Related Work and Bibliography Refresh

**Files:**
- Modify: `papers/demestic-journal/sections/02-related-work.tex`
- Modify: `papers/demestic-journal/references.bib`

**Interfaces:**
- Consumes: the residual gap defined by Task 2
- Produces: exact BibTeX keys and the research-positioning table used by the introduction and discussion

- [ ] **Step 1: Confirm the eight current references are absent or incomplete**

Run:

```bash
grep -niE "2605.17268|2606.12706|2512.24426|2605.10744|2607.14727|2512.11891|2605.21446|2607.16938" papers/demestic-journal/references.bib
```

Expected: at least one required arXiv identifier is absent.

- [ ] **Step 2: Add verified BibTeX records**

Add entries for `Is VLA Reasoning Faithful?`, `VLADriveBench`, `Counterfactual VLA`, `C-CoT`, `WorkDrive`, `VLSA/AEGIS`, `Lost in Fog`, and `CVAA/Counter-nuScenes`. Copy title, complete author list, year and arXiv identifier from the official arXiv records; use stable keys referenced consistently in the prose.

- [ ] **Step 3: Rewrite related work in four research groups**

Organize the section as:

1. CoC faithfulness and action causality
2. Reasoning-based action correction and learning
3. Execution safety layers and formal assurance
4. Position of this work

State that VLSA/AEGIS concerns robot manipulation rather than autonomous driving. Describe differences as differences in the reported primary evaluation/intervention unit, not as claims that previous work omitted every temporal or provenance issue.

- [ ] **Step 4: Replace the comparison table schema**

Use the columns `연구군`, `주된 평가/개입 단위`, `모델 재추론·입력 개입`, `상태 기반 반복·기한 계약`, `장면 출처 검사`, `주장 범위`. Ensure the row for this paper says stored-annotation audit and does not claim superior safety.

- [ ] **Step 5: Verify citation resolution and wording**

Run:

```bash
make -C papers/demestic-journal all
grep -E "Citation.*undefined|There were undefined references" papers/demestic-journal/main.log
grep -nE "최초|유일|아무도|다루지 않았다" papers/demestic-journal/sections/02-related-work.tex
```

Expected: no undefined citations and no categorical priority/gap wording.

- [ ] **Step 6: Commit**

```bash
git add papers/demestic-journal/sections/02-related-work.tex papers/demestic-journal/references.bib
git commit -m "docs: position contract audit against recent VLA research"
```

---

### Task 4: Data Evidence and Contract Problem Definition

**Files:**
- Modify: `papers/demestic-journal/sections/03-data.tex`
- Modify: `papers/demestic-journal/sections/04-problem.tex`
- Modify only if labels require it: `papers/demestic-journal/figures/annotation-flow.tex`

**Interfaces:**
- Consumes: terminology and evidence ledger from Tasks 1–2
- Produces: evidence-level definitions used by method, experiments and results

- [ ] **Step 1: Locate ambiguous normative terms**

Run:

```bash
grep -nE "판단 사건|trusted|신뢰 사건|의무|response|PASS|FAIL|deadline|Deadline" papers/demestic-journal/sections/03-data.tex papers/demestic-journal/sections/04-problem.tex
```

Expected: terms needing evidence-level qualification are listed.

- [ ] **Step 2: Add the construction-validity warning and selection flow**

State that meta-actions are extracted from recorded trajectory before CoC generation and that CoC–same-trajectory agreement is therefore not independent causal evidence. Insert the exact flow:

```text
403 annotations -> 290 machine quality-passing annotations
-> 134 applicable longitudinal audit contracts
-> 130 speed-detector cases + 4 already-satisfied cases
```

Define `quality_pass` as a machine-generated input acceptance signal, not human gold. Describe the five-case visual check as AI visual triage of four front-camera frames, not independent human validation.

- [ ] **Step 3: Define the three-layer audit contract**

In the problem section distinguish:

1. parsed behavioral intent from the annotation,
2. researcher-selected candidate temporal contract,
3. ego-motion-derived response evidence.

Define $D_i$ as `candidate deadline`; define contract satisfaction as consistency under the selected audit semantics, not compliance with legal or physical safety obligations. Define preserve/reset/dedup as alternative annotation policies whose choice must be explicit.

- [ ] **Step 4: Normalize vocabulary across both files**

Replace unqualified `판단 사건` with `CoC 주석 사건` or `추론 주석 사건`; qualify retained code identifier `trusted` as audit-input acceptance; use `자차 움직임 응답 증거`; translate result states as `계약 통과/검토 후보`.

- [ ] **Step 5: Verify arithmetic, definitions and build**

Run:

```bash
grep -nE "403|290|134|130|already|이미 만족|후보 기한|자차 움직임 응답" papers/demestic-journal/sections/03-data.tex papers/demestic-journal/sections/04-problem.tex
grep -nE "인간 정답|human gold|법적 의무|안전 기한" papers/demestic-journal/sections/03-data.tex papers/demestic-journal/sections/04-problem.tex
make -C papers/demestic-journal all
```

Expected: selection numbers and qualifications are present; human-gold/legal-safety phrases occur only in explicit negations or limitations; build succeeds.

- [ ] **Step 6: Commit**

```bash
git add papers/demestic-journal/sections/03-data.tex papers/demestic-journal/sections/04-problem.tex papers/demestic-journal/figures/annotation-flow.tex
git commit -m "docs: define evidence levels and candidate audit contracts"
```

---

### Task 5: Method Reorganization and Formalization Scope

**Files:**
- Modify: `papers/demestic-journal/sections/05-method.tex`
- Modify if terminology or layout changes: `papers/demestic-journal/figures/method-pipeline.tex`
- Modify if terminology or layout changes: `papers/demestic-journal/figures/uppaal-network.tex`

**Interfaces:**
- Consumes: the three-layer contract definition from Task 4
- Produces: four method components and precise UPPAAL semantics tested in Tasks 6–7

- [ ] **Step 1: Check current method/component coverage**

Run:

```bash
grep -nE "수집|컴파일|관찰자|router|라우팅|결정적|replay|오라클" papers/demestic-journal/sections/05-method.tex
```

Expected: current prose does not yet expose all four components with their evidence boundaries.

- [ ] **Step 2: Reorganize the method into four components**

Define:

1. evidence collector: timestamp, text, quality and ego-motion,
2. contract compiler: intent, candidate deadline, repeat policy and response predicate,
3. state observer: obligation lifecycle, response matching, low-quality overwrite and scene boundary,
4. result router: contract pass, semantic/threshold-dependent review, insufficient provenance and synthetic mutation.

Keep the concrete `scene-0001` mapping after the general architecture as a traceable example.

- [ ] **Step 3: State the formalization boundary explicitly**

Explain before the automata details that the source automaton replays a deterministic recorded event stream; UPPAAL does not search the vehicle environment or synthesize a safe control. Explain that mutation oracles test checker internal validity and not real-world fault prevalence.

- [ ] **Step 4: Update figures and captions only where required**

Use the same four component names in prose, pipeline figure and UPPAAL-network caption. Ensure colors continue to distinguish observed, derived, assumed and blocked evidence. Do not add a visual unless the existing one materially clarifies state or data flow.

- [ ] **Step 5: Verify method terminology and LaTeX**

Run:

```bash
grep -nE "증거 수집기|계약 컴파일러|상태 관찰자|결과.*라우|결정적|합성 변이" papers/demestic-journal/sections/05-method.tex
grep -nE "안전 제어를 생성|실제 오류 검출률|환경을 탐색" papers/demestic-journal/sections/05-method.tex
make -C papers/demestic-journal all
```

Expected: all four components and deterministic-replay boundary are present; any searched overclaim occurs only in a negated scope statement; build succeeds.

- [ ] **Step 6: Commit**

```bash
git add papers/demestic-journal/sections/05-method.tex papers/demestic-journal/figures/method-pipeline.tex papers/demestic-journal/figures/uppaal-network.tex
git commit -m "docs: clarify observer architecture and formalization scope"
```

---

### Task 6: Experiment Design Around Three Evidence Blocks

**Files:**
- Modify: `papers/demestic-journal/sections/06-experiments.tex`

**Interfaces:**
- Consumes: four RQs and four method components
- Produces: A/B/C experiments with explicit controls and outputs referenced by the result section

- [ ] **Step 1: Confirm the old eight-experiment structure**

Run:

```bash
grep -n "\\subsection{실험" papers/demestic-journal/sections/06-experiments.tex
```

Expected: eight separately numbered experiment subsections are found.

- [ ] **Step 2: Replace them with Experiment Block A**

Name it `변환·검사기 타당성`. Include `scene-0001`, provenance/response synthetic mutations, chained synthetic protocol and timestamp-script baseline. State fixed event input, manipulated fault/policy, expected oracle and that the output supports RQ1/RQ4 only.

- [ ] **Step 3: Add Experiment Block B**

Name it `일괄 감사와 민감도`. Include 94-scene filtering, five review candidates, preserve/reset deadline sensitivity and 27 detector settings over 130 detector cases. Distinguish fixed recorded trajectories from varied audit semantics/thresholds; state that outputs are routing and sensitivity results for RQ2.

- [ ] **Step 4: Add Experiment Block C**

Name it `출처와 에피소드 확장`. Include local-scene independence negative control, synthetic boundary carryover and the 13-chain metadata-mirror pilot. Separate continuity eligibility from post-link temporal audit; state that results support RQ3 but not official sequence certification.

- [ ] **Step 5: Add an experiment-to-RQ table**

Use columns `실험 블록`, `고정 조건`, `조작·비교 조건`, `출력`, `대응 RQ`, `해석 범위`. Ensure every RQ has at least one block and every block has a prohibited extrapolation in its interpretation text.

- [ ] **Step 6: Verify structure and commit**

Run:

```bash
grep -nE "변환·검사기 타당성|일괄 감사와 민감도|출처와 에피소드 확장|RQ1|RQ2|RQ3|RQ4" papers/demestic-journal/sections/06-experiments.tex
make -C papers/demestic-journal all
```

Expected: three blocks and all four RQs are present; build succeeds.

```bash
git add papers/demestic-journal/sections/06-experiments.tex
git commit -m "docs: align experiments with four research questions"
```

---

### Task 7: Results Reordering and Claim–Evidence Matrix

**Files:**
- Modify: `papers/demestic-journal/sections/07-results.tex`
- Modify only for labels/layout required by reordered results: `papers/demestic-journal/figures/overview-pipeline.tex`

**Interfaces:**
- Consumes: experiment blocks from Task 6 and CE-01 through CE-10
- Produces: evidence-bounded answers to RQ1–RQ4

- [ ] **Step 1: Add the result interpretation matrix first**

Use rows for synthetic mutation agreement, 125+4 passes and five candidates, preserve/reset reversal, detector sensitivity, 13-chain pilot and script 13/13 agreement. Use columns `결과`, `직접 지지하는 주장`, `지지하지 않는 주장` and copy the allowed/prohibited interpretations from the approved design.

- [ ] **Step 2: Reorder detailed results by RQ**

Present:

1. RQ1: source/derived mapping and known synthetic-fault discrimination,
2. RQ2: selection flow, five candidates, repeat/deadline/detector sensitivity,
3. RQ3: local independence, boundary mutation and 13-chain pilot,
4. RQ4: script equivalence and the compositional/traceability value of UPPAAL.

Keep `scene-0028` and `scene-0074` as policy-reversal examples, not unsafe cases.

- [ ] **Step 3: Correct evidence labels and artifact provenance**

Describe orphan response as a synthetic non-atomic deduplication failure mode. Describe five-case frame review as AI triage. Cite `uppaal-loop-batch-all-strict-1s.json` conceptually as the source of the 13-chain totals; do not reuse a prior 10-item partial summary.

- [ ] **Step 4: Remove or demote weak exploratory claims**

Remove quantitative/causal claims based on small word-pattern groups such as speed bumps or parked vehicles. If retained, label them as a single exploratory observation without statistical inference.

- [ ] **Step 5: Run exact numerical and overclaim checks**

Run:

```bash
grep -nE "125|이미 만족|검토 후보 5|282|1,128|27|13/13|기한 실패 8|도달성 실패 7|경계.*0" papers/demestic-journal/sections/07-results.tex
grep -nE "unsafe|위험한 샘플|실제 오류|충돌 감소|검출률" papers/demestic-journal/sections/07-results.tex
make -C papers/demestic-journal all
```

Expected: all approved totals are present and consistent; searched overclaims occur only where the matrix explicitly says they are unsupported; build succeeds.

- [ ] **Step 6: Commit**

```bash
git add papers/demestic-journal/sections/07-results.tex papers/demestic-journal/figures/overview-pipeline.tex
git commit -m "docs: bind domestic paper results to direct evidence"
```

---

### Task 8: Discussion, Threats, Conclusion, and Final Paper Audit

**Files:**
- Modify: `papers/demestic-journal/sections/08-discussion.tex`
- Modify: `papers/demestic-journal/sections/09-threats.tex`
- Modify: `papers/demestic-journal/sections/10-conclusion.tex`
- Modify if routing vocabulary changes: `papers/demestic-journal/figures/training-routing.tex`
- Verify: `papers/demestic-journal/main.tex`
- Verify: `papers/demestic-journal/main.pdf`
- Update: `papers/demestic-journal/CLAIM_EVIDENCE_AUDIT.md`

**Interfaces:**
- Consumes: final RQ answers from Task 7
- Produces: bounded implications, consolidated validity threats, concise conclusion and validated PDF

- [ ] **Step 1: Rewrite the discussion around three questions**

Answer only: what the audit changes during training-data preparation; why pass/review are not safety labels; and why a formal observer remains useful when a timestamp script reproduces Boolean deadlines. Describe routing as a proposed policy whose learning benefit remains unevaluated. Use `약한 유지 후보`, `검토 후보`, `출처 불충분` rather than safe/unsafe routing.

- [ ] **Step 2: Consolidate eight validity threats**

Use this order: construction validity, measurement validity, contract validity, internal validity, external validity, review validity, provenance validity and formalization limitation. Include trajectory-conditioned CoC, ego-speed proxy, $D=3$s and policy dependence, parser/quality/detector dependence, 94-scene/134-contract scope, non-human visual triage, metadata mirror and deterministic replay.

- [ ] **Step 3: Rewrite the conclusion in three paragraphs**

Paragraph 1 states problem/method; paragraph 2 states policy sensitivity, typed review candidates and provenance-qualified episode auditing; paragraph 3 states that physical safety, general CoC faithfulness and learning improvement remain unproven and identifies official long-sequence data, independent trajectory verifier and closed-loop evaluation as later layers.

- [ ] **Step 4: Perform a full claim and vocabulary audit**

Run:

```bash
grep -RInE "최초|유일|완전한 안전|안전성을 보장|위험한 샘플|실제 오류 검출률" papers/demestic-journal/main.tex papers/demestic-journal/sections
grep -RInE "판단 사건|신뢰 사건|trusted event|제어 의무" papers/demestic-journal/main.tex papers/demestic-journal/sections
grep -RInE "403|290|134|130|125|282|1,128|13/13" papers/demestic-journal/main.tex papers/demestic-journal/sections
```

Expected: overclaims are absent except explicit negations; legacy terms are absent or locally qualified; numeric uses match the evidence ledger.

- [ ] **Step 5: Build from a clean auxiliary state and inspect logs**

Run:

```bash
make -C papers/demestic-journal clean
make -C papers/demestic-journal all
grep -E "Undefined control sequence|Citation.*undefined|Reference.*undefined|Overfull \\hbox|Overfull \\vbox" papers/demestic-journal/main.log
pdfinfo papers/demestic-journal/main.pdf | grep -E "Pages|Page size"
```

Expected: build succeeds with no undefined commands/citations/references and no overfull boxes. Record final page count and any benign warnings in the audit file.

- [ ] **Step 6: Visually inspect every PDF page**

Render pages with:

```bash
mkdir -p /tmp/domestic-journal-review
pdftoppm -png -r 120 papers/demestic-journal/main.pdf /tmp/domestic-journal-review/page
```

Inspect all rendered pages for blank columns, clipped tables, overlapping figure labels, broken Korean glyphs and isolated headings. Adjust only float placement, column widths, caption length or page-break controls needed to remove observed defects, then rebuild and re-inspect changed pages.

- [ ] **Step 7: Complete the evidence audit**

For CE-01 through CE-10, record the final section/table/figure location and mark each claim `supported`, `qualified`, or `removed`. Add a final checklist confirming the four RQs each have a method, experiment, result and limitation.

- [ ] **Step 8: Commit the completed revision**

```bash
git add papers/demestic-journal/main.tex \
  papers/demestic-journal/sections/01-introduction.tex \
  papers/demestic-journal/sections/02-related-work.tex \
  papers/demestic-journal/sections/03-data.tex \
  papers/demestic-journal/sections/04-problem.tex \
  papers/demestic-journal/sections/05-method.tex \
  papers/demestic-journal/sections/06-experiments.tex \
  papers/demestic-journal/sections/07-results.tex \
  papers/demestic-journal/sections/08-discussion.tex \
  papers/demestic-journal/sections/09-threats.tex \
  papers/demestic-journal/sections/10-conclusion.tex \
  papers/demestic-journal/figures/annotation-flow.tex \
  papers/demestic-journal/figures/method-pipeline.tex \
  papers/demestic-journal/figures/uppaal-network.tex \
  papers/demestic-journal/figures/overview-pipeline.tex \
  papers/demestic-journal/figures/training-routing.tex \
  papers/demestic-journal/references.bib \
  papers/demestic-journal/main.pdf \
  papers/demestic-journal/CLAIM_EVIDENCE_AUDIT.md
git commit -m "docs: complete evidence-bounded domestic journal revision"
```

---

## Final Acceptance Checklist

- [ ] The title, abstract, RQ1–RQ4, method, experiment blocks, results and conclusion use the same time·provenance contract-audit thesis.
- [ ] Abstract length is 25–35% shorter than the recorded baseline while retaining the decisive evidence and scope limitation.
- [ ] Each RQ maps to at least one method component, experiment block, direct result and explicit limitation.
- [ ] Selection and result arithmetic is consistent everywhere: `403 -> 290 -> 134 -> 130+4`, `134 = 125+4+5`, `282×4 = 1,128`.
- [ ] The 13-chain pilot always uses `4 all-query pass / 9 review / 8 candidate-deadline fail / 7 response-reachability fail / 0 boundary fail`.
- [ ] All eight recent works are cited using verified bibliographic metadata.
- [ ] No claim equates contract pass/review with physical safety/risk or synthetic mutation agreement with real-world detection rate.
- [ ] No claim says UPPAAL uniquely computes deterministic deadline results; its claimed value is explicit state lifecycle, composition and traceability.
- [ ] XeLaTeX/BibTeX completes without undefined references, citations or overfull boxes.
- [ ] Every PDF page has been visually checked for blank columns, clipping, overlap and unreadable labels.
