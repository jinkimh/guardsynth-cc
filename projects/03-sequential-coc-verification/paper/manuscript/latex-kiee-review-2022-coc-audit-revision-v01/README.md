# KIEE CoC audit revision V01

- Owner: `sequential-coc-verification`.
- Current state (2026-10-12): `REVIEW_RESPONSE_PACKAGE_READY`, with the evidence limitations below.
- Governing design: [current response plan and execution, section 13](../../../docs/designs/KIEE_REVIEW_RESPONSE_REEXPERIMENT_DESIGN_V01.md#13-장면-간-제약-시험을-포함한-전체-심사-대응-재계획--2026-10-12).
- Comparison baseline: the preserved adjacent `latex-kiee-review-2022-coc-audit-10pages` submission.

## Deliverables

- [Marked article](main.pdf), 14 pages; English abstract and Korean introduction and integrated boundary, agreement and conformance evidence.
- [Clean article](main-clean.pdf), 14 pages; identical normalized text with revision color removed.
- [Reviewer 1 response](response-to-reviewer-1.pdf), 10 pages, 6 Major + 3 Minor items.
- [Reviewer 2 response](response-to-reviewer-2.pdf), 9 pages, 8 items including separate 1.1/1.2 answers.
- [Reviewer 3 response](response-to-reviewer-3.pdf), 13 pages, 11 items. The original 27-row trajectory details remain in `response-trajectory-details.tex` and R3-11.
- [Current compilation and excerpt validation](document_validation.json): PASS; all 28 source excerpts occur in the current article and response PDFs; section/page references resolve. No undefined references/citations, missing characters or overfull boxes were reported.

The three reviewer comment blocks are preserved. Responses distinguish completed changes, partial responses and the feasibility alternative. Added material is blue relative to the preserved submission; the clean copy changes color only. The article still reports the initial 96/144 and 48 failures separately from the post-development same-case 144/144 retest and the FSM tie.

## Abstract and introduction update

The supplied English abstract and Korean introduction were incorporated on 2026-10-12. Eight cited references were added. The boundary reset result (14/81), textual-consistency Fleiss coefficient (0.0273009) and AC1 (0.3009355) were checked against retained result JSON. The scene-0051/scene-0052 example and 699 ms gap were checked against the retained chain profile; Drive the Thoughts reports 74% trajectory agreement within the reliable-reasoning subset. All 28 response excerpts and page references were resynchronized after the article changed.

## Evaluation data chapter

Chapter 3 now starts with an overview of the six evaluation datasets, including the legacy 40-pair regression set. Natural data provenance and selection are separated from the human review protocol and its record limitations. The annotation flow figure and duplicate experiment descriptions were removed from the body; the natural boundary-linking limitation is in section 9. The introduction qualifies the 699 ms gap as a fact of the retained linking record.

The original selector is preserved in the August 10 snapshot (`7634655`); its selection, tie-breaking and ID functions and fixed seed match the maintained source. The retained selection reanalysis verifies the original 27 review IDs, scene IDs and groups. This supports describing the procedure as a preserved original selector, without claiming prospective registration. The local public/restricted classification does not establish external release; the current reproduction package's external distribution scope and address remain unconfirmed.

The review-screen description is supported by the retained [review protocol, lines 11–12](../../../artifacts/restricted/sequential-coc-consistency-v1/review/REVIEW_PROTOCOL.md#L11), A/B standalone HTML pages and [packet manifest](../../../artifacts/restricted/sequential-coc-consistency-v1/review/packet-manifest.json). All four artifact byte counts and SHA-256 values match the manifest. The pages provide source CoC and time relative to each item's first event, with no separate video, trajectory, object/signal-state data or checker output. Candidate/control groups and source scene/window IDs are absent from both HTML files, including their scripts; the group mapping is stored separately in `adjudication-mapping.json`. The A/B orders differ, contain the same 27 IDs, and match the corresponding four original CSV export orders. The relevant item, rendering, ordering and protocol functions are unchanged from `7634655`. This confirms masking in the retained first-review interface, without establishing what participants knew outside that interface or reconstructing training/adjudication conduct. Chapter 3.3 and R1-M3, R1-m1 and R3-9 use that scope.

## Added evidence and limits

1. **X3a:** the original four reviewers' 27-scene labels reproduce the previous Fleiss coefficients. Time/action-sequence/text AC1 is 0.626706/0.322898/0.300936. Raw agreement, category distributions and the 39 observed action-sequence categories remain explicit. This is reanalysis, not improved human agreement. [Restricted report](../../../artifacts/restricted/kiee-review-revision-001/reviewer-agreement-2026-10-12-001/REPORT_KO.md).
2. **81 boundary cases:** the body now gives boundary semantics, inputs, state updates, actual queries, the 44/29/8 expected classes, confusion matrix and representative traces. Carrying obligations matches 81/81; resetting matches 14/81. This is an authored symbolic study and a memory ablation. [Report](../../../artifacts/public/cross-scene-constraints-001/cross-scene-constraints-2026-10-12-001/REPORT_KO.md).
3. **X2a:** predeclared finite Cartesian alphabets produced 35,042,928 cases with no state/issue/first-record mismatch between the fixed XML step code and a separately written prefix formula oracle. The separate 5,256-case P4 fault control preserves all 1,884 state mismatches. Execution is native C++ of the extracted step bodies, not a new UPPAAL search. Both paths share authorship and a specification; this is bounded implementation conformance and a **partial response to R3-7**. [Protocol and report](../../../artifacts/public/bounded-conformance-001/bounded-conformance-2026-10-12-001/REPORT_KO.md).

Natural semantic gold, external independent testing, human re-evaluation, general NLP, separate P2 release-command validation, quantitative time guarantees and vehicle safety are not established. The saved natural 13 chains/16 boundaries lack the identity, applicability and release-truth bindings needed for semantic evaluation. Reviewer qualifications/training/adjudication and past generation model/prompt records cannot be reconstructed. X2b/X3b/X4/X5/X6 remain unperformed; the new exhaustive boundary profile does not count as a separate FSM rerun of the 81 cases.

## Formal definitions and model scope

Chapter 4 separates notation and initialization, problem types and implementation scope, condition-linked updates, the boundary extension, and first-issue/response-time definitions. Model verdicts use **확정 모순 / 근거 부족 / 양립**; raw result codes, legacy interpretation uncertainty and natural trajectory labels are preserved. P2 has no explicit release-command input in either primary model. The legacy proxy rule and intentional P4 regression cases are explained in section 7.1; the exhaustive P4 state-fault control remains separate.

The condition-linked model retains evidence on creation, including evidence preceding creation or from an earlier lifecycle. The 144 cases contain no repeated same-ID creation; the exhaustive alphabet permits it. The boundary extension resets evidence on activation, handles linkage and evidence validity, and omits preconditions. Verified persistent links alone therefore do not make the models equivalent. The manuscript describes a restricted common domain and keeps each result tied to its own model. Experimental code, inputs, labels and measured results were not changed for this revision.

The original conformance manifest pins the earlier chapter 4 hash. Before the current rewrite, its exact bytes were retained as [frozen specification input](../../../artifacts/public/bounded-conformance-001/bounded-conformance-2026-10-12-001/specification_frozen.tex) (SHA-256 `dfe2c5375c850b97a0e3294c60fc919cd5a4a98fd5e20cfcd780a3b4bfddce9f`). The snapshot was added **after the experiment**, preserving an existing pinned input; it is not a new contemporaneous freeze. The original manifest and measurements remain unchanged. The input redirect is recorded in the repository artifact migration catalog; the current chapter is an editorial clarification of the two implemented semantics.

## Method chapter

Chapter 5 follows the introduction's three stages: event ordering, frame construction, and checking with source-linked records. The original six-state checker and its accumulated waiting-uncertainty policy are explained in section 7.3. The method retains the condition-linked model's input/state table, step pseudocode, Run/Done diagram and five actual queries with their meanings, as well as the boundary extension and the separate FSM comparison path.

The automatic path's 144/144 uncertain outputs appear at the start of section 5.2. Natural coverage uses the 399 unique source events in the retained 309 windows from 90 multi-event scenes; the four single-event scenes are outside these windows. The retained [compiler coverage](../../../artifacts/restricted/kiee-review-revision-001/reanalysis-2026-09-30-001/compiler_coverage.json) reproduces 230 source events with actions, 169 without, and 265 phases (219 parsed, 44 missing-target and 2 ambiguous-order). Recounting the same parser outputs gives zero `until` release conditions and ten `once/after` triggers. These are syntax-coverage counts, not semantic extraction accuracy.

The input-examples table separates the real scene-0051 deceleration sentence from the authored pedestrian example. The former has unknown release evidence and a legacy single-event output of `CONSISTENT`, shown as “양립 / 후속 진행 없음”; this is not an automatic contradiction-detection success. The authored example shows each complete two-event observation array and all five query results. The abstract now specifies that automatic extraction **accuracy** on natural CoC was not evaluated. R1-M2, R3-5 and R3-6 were updated and all excerpts resynchronized. No experimental source, inputs, expected labels or measured results were changed.

## Build and verification

Run from this directory:

```sh
python3 -B build.py
```

The default builds all five documents, updates article label locations, synchronizes all 28 response excerpts, locates their actual PDF pages, then verifies the compiled package. It uses LuaLaTeX, BibTeX and MuPDF (`mutool`) for text extraction. Specific names can be passed for a partial build; `python3 -B verify_documents.py` validates all five current PDFs afterward.

PDFs, aux/bibliography files, build logs and the local TeX cache stay beside these sources. The bundled fonts and `.texlive-local` assets depend on the preserved adjacent submission. The article has font-size/italic fallback and PDF bookmark-string warnings; they are recorded in the validation JSON. The three response builds have no remaining compiler warnings. The current data chapter and its overview/provenance tables on article pages 3–4 were visually checked. The rewritten chapter 4 scope/policy tables and equations on pages 4–5 were also visually checked. The method figure and parser/example/state/query tables, the section 4.4 qualification and the section 7.2 output mapping were visually checked after the terminology update. The method figure now appears on page 6, alongside section 5.1.

Legacy `CONTRADICTION`/`UNKNOWN`/`CONSISTENT` outputs are explicitly mapped to confirmed contradiction/insufficient evidence/compatibility for counting agreement in section 7.2. This counting convention does not equate all legacy interpretation or waiting uncertainty with the primary model's missing release evidence. P1–P4 names are aligned across the scope and regression tables. The original parser's four-action encoding is distinguished from the authored frame codes; the bounded enumerator maps YIELD to STOP code 0, whereas the 144-case encoder accepts STOP/WAIT/GO. The common-domain conditions in section 4.4 are explained from the update code, with direct cross-model execution comparison explicitly unperformed. Chapter 6 omits internal task names and revision-process prose. Experimental code, inputs, labels and measurements are unchanged.

The October 1 sealed build/validation runs describe their earlier revision and are historical evidence only. Current results are indexed once in the [project result index](../../../artifacts/RESULT_INDEX.md).

## Remaining author metadata

The manuscript ID and actual editorial revision round remain “confirmation needed”; `revision-v01` is a source version. No mandatory 10-page limit is inferred from the old directory name. No external submission, publication, messaging, commit or push was performed.
