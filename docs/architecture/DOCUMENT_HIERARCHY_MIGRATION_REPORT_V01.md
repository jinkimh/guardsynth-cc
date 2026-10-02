# Research Document Hierarchy Migration Report V1

- Date: 2026-08-13
- Structure authority: [`PROJECT_STRUCTURE_CODEX.md`](PROJECT_STRUCTURE_CODEX.md)
- Naming authority: [`FILE_NAMING_CODEX.md`](FILE_NAMING_CODEX.md)
- Scope: maintained research, development, related-work, and project-entry documents
- Exclusions: immutable artifacts, archives, third-party trees, installed runtimes, licensed
  inputs, and external paper templates

## Outcome

All five registered research projects use the same governing planning set:

```text
01_RESEARCH_PLAN_V01.md
  -> 02_PROJECT_MILESTONES.md
    -> 03_PROJECT_EXECUTION_TRACKER.md
```

Every project now has a survey index and an explicit related-work input. Projects 01 and 02 use
`PLANNED` survey scaffolds because no completed systematic search could be verified. Project 03
uses a real two-stage local refinement sequence. Project 04 retains one integrated survey and
strategy document. Project 05 uses the active EB-M01 prior-art survey without asserting novelty
before the search protocol is complete.

## Rename map

The governing parent for every row is the owning project's research plan unless a more specific
parent is shown. Maintained references include plans, requirements, reports, source README files,
pipeline path literals, the platform report, survey indexes, and `MIGRATION_MAP.json`.

| Former path | Canonical path | Reason / immediate parent |
|---|---|---|
| `projects/01-safety-constrained-coc/docs/designs/COC_TRAJECTORY_EXPLORATION.md` | `projects/01-safety-constrained-coc/docs/surveys/COC_TRAJECTORY_EXPLORATION_NOTES.md` | exploratory literature notes, not a design / survey index |
| `projects/03-sequential-coc-verification/docs/designs/NATURAL_LANGUAGE_PROHIBITION_STUDY_V01.md` | `projects/03-sequential-coc-verification/docs/designs/NATURAL_LANGUAGE_PROHIBITION_STUDY_DESIGN_V01.md` | expose the design role / research plan |
| `projects/03-sequential-coc-verification/docs/decisions/MULTI_BACKEND_OPTIONS.md` | `projects/03-sequential-coc-verification/docs/decisions/MULTI_BACKEND_OPTIONS_DECISION.md` | expose the decision role / research plan |
| `projects/03-sequential-coc-verification/docs/decisions/UPPAAL_FIRST_OPTION.md` | `projects/03-sequential-coc-verification/docs/decisions/UPPAAL_FIRST_OPTION_DECISION.md` | expose the decision role / multi-backend decision |
| `projects/03-sequential-coc-verification/docs/surveys/2026-08-01-e2e-finetuning-model-checking-survey.md` | `projects/03-sequential-coc-verification/docs/surveys/01_RELATED_WORK_SURVEY_V01.md` | governing input of an actual survey refinement set / survey index |
| `projects/03-sequential-coc-verification/docs/surveys/METHOD_SELECTION_SURVEY.md` | `projects/03-sequential-coc-verification/docs/surveys/02_METHOD_SELECTION_SURVEY_V01.md` | method-selection refinement / related-work survey |
| `projects/04-guardsynth-coc/docs/designs/GEOMETRIC_SET_ASSOCIATION_V01.md` | `projects/04-guardsynth-coc/docs/designs/GEOMETRIC_SET_ASSOCIATION_DESIGN_V01.md` | expose the design role / research plan |
| `projects/04-guardsynth-coc/docs/designs/GUARDSYNTH_BASELINE_PROTOCOL_V01.md` | `projects/04-guardsynth-coc/docs/designs/GUARDSYNTH_BASELINE_PROTOCOL_DESIGN_V01.md` | expose the design role / M15 requirements |
| `projects/04-guardsynth-coc/docs/designs/GUARDSYNTH_COC_CONDITIONED_FRONTEND_V01.md` | `projects/04-guardsynth-coc/docs/designs/GUARDSYNTH_COC_CONDITIONED_FRONTEND_DESIGN_V01.md` | expose the design role / M14 requirements |
| `projects/04-guardsynth-coc/docs/designs/GUARDSYNTH_LABEL_LIGHT_GROUNDING_V01.md` | `projects/04-guardsynth-coc/docs/designs/GUARDSYNTH_LABEL_LIGHT_GROUNDING_DESIGN_V01.md` | expose the design role / research plan |
| `projects/04-guardsynth-coc/docs/designs/GUARDSYNTH_PROJECT_PORTAL_V01.md` | `projects/04-guardsynth-coc/docs/designs/GUARDSYNTH_PROJECT_PORTAL_DESIGN_V01.md` | expose the design role / project management entry points |
| `projects/04-guardsynth-coc/docs/designs/GUARDSYNTH_SCENE_EVIDENCE_REVIEW_UI_V01.md` | `projects/04-guardsynth-coc/docs/designs/GUARDSYNTH_SCENE_EVIDENCE_REVIEW_UI_DESIGN_V01.md` | expose the design role / research plan |
| `projects/04-guardsynth-coc/docs/designs/GUARDSYNTH_SOURCE_AWARE_GENERATOR_V01.md` | `projects/04-guardsynth-coc/docs/designs/GUARDSYNTH_SOURCE_AWARE_GENERATOR_DESIGN_V01.md` | expose the design role / research plan |
| `projects/04-guardsynth-coc/docs/designs/RULE_APPLICABILITY_EVIDENCE_V01.md` | `projects/04-guardsynth-coc/docs/designs/RULE_APPLICABILITY_EVIDENCE_DESIGN_V01.md` | expose the design role / research plan |
| `projects/04-guardsynth-coc/docs/designs/SIMULATED_SCENE_ASSURANCE_PROJECTION_V01.md` | `projects/04-guardsynth-coc/docs/designs/SIMULATED_SCENE_ASSURANCE_PROJECTION_DESIGN_V01.md` | expose the design role / M13 requirements |
| `projects/04-guardsynth-coc/docs/designs/VEHICLE_ASSURANCE_SOURCE_AUDIT_V01.md` | `projects/04-guardsynth-coc/docs/reports/VEHICLE_ASSURANCE_SOURCE_AUDIT_REPORT_V01.md` | completed audit evidence, not a design / research plan |
| `projects/04-guardsynth-coc/docs/decisions/ACTUAL_VEHICLE_VALIDATION_DEFERRAL_V01.md` | `projects/04-guardsynth-coc/docs/decisions/ACTUAL_VEHICLE_VALIDATION_DEFERRAL_DECISION_V01.md` | expose the decision role / research plan |
| `projects/04-guardsynth-coc/docs/decisions/GUARDSYNTH_KR_SCOPE_AND_SOURCE_POLICY_V01.md` | `projects/04-guardsynth-coc/docs/decisions/GUARDSYNTH_KR_SCOPE_AND_SOURCE_POLICY_DECISION_V01.md` | expose the decision role / research plan |
| `projects/04-guardsynth-coc/docs/reports/GUARDSYNTH_P0B_TERMINAL_DECISION_V01.md` | `projects/04-guardsynth-coc/docs/reports/GUARDSYNTH_P0B_TERMINAL_DECISION_REPORT_V01.md` | preserve report ownership while exposing its document class / milestone ledger |
| `projects/04-guardsynth-coc/docs/reports/GUARDSYNTH_PROJECT_STAGE_STATUS_V01.md` | `projects/04-guardsynth-coc/docs/reports/GUARDSYNTH_PROJECT_STAGE_STATUS_REPORT_V01.md` | expose the report role / execution tracker |
| `projects/04-guardsynth-coc/docs/reports/GUARDSYNTH_SOURCE_BOUNDARY_THOROUGH_TEST_V01.md` | `projects/04-guardsynth-coc/docs/reports/GUARDSYNTH_SOURCE_BOUNDARY_THOROUGH_TEST_REPORT_V01.md` | expose the report role / milestone ledger |
| `projects/04-guardsynth-coc/docs/surveys/CONTEXT_AWARE_GUARD_SYNTHESIS_SURVEY_AND_STRATEGY_V01.md` | `projects/04-guardsynth-coc/docs/surveys/GUARDSYNTH_RELATED_WORK_SURVEY_AND_RESEARCH_STRATEGY_V01.md` | identify the comprehensive canonical related-work input / research plan |
| `projects/05-eblc-language-verification/docs/decisions/PLATFORM_RESEARCH_SEPARATION_V01.md` | `projects/05-eblc-language-verification/docs/decisions/PLATFORM_RESEARCH_SEPARATION_DECISION_V01.md` | expose the decision role / research plan |

## Created documents

| Project | Document | Status | Reason |
|---|---|---|---|
| Safety-Constrained CoC | `docs/surveys/RELATED_WORK_SURVEY_V01.md` | `PLANNED` | canonical survey entry without fabricated findings |
| Specification Alignment | `docs/surveys/RELATED_WORK_SURVEY_V01.md` | `PLANNED` | canonical survey entry without fabricated findings |
| EBLC Language Verification | `docs/surveys/RELATED_WORK_SURVEY_V01.md` | `CURRENT`, in progress | EB-M01 prior-art and naming audit |

## Survey authority classification

| Project | Document | Classification |
|---|---|---|
| Safety-Constrained CoC | `RELATED_WORK_SURVEY_V01.md` | `PLANNED` |
| Safety-Constrained CoC | `COC_TRAJECTORY_EXPLORATION_NOTES.md` | `SUPPORTING` |
| Specification Alignment | `RELATED_WORK_SURVEY_V01.md` | `PLANNED` |
| Sequential CoC Verification | `01_RELATED_WORK_SURVEY_V01.md` | `CURRENT` |
| Sequential CoC Verification | `02_METHOD_SELECTION_SURVEY_V01.md` | `CURRENT` |
| GuardSynth-CoC | `GUARDSYNTH_RELATED_WORK_SURVEY_AND_RESEARCH_STRATEGY_V01.md` | `CURRENT` |
| GuardSynth-CoC | `COC_SHIELD_SURVEY_NOTES.md` | `HISTORICAL` |
| EBLC Language Verification | `RELATED_WORK_SURVEY_V01.md` | `CURRENT`, in progress |

No maintained survey is classified `SUPERSEDED`; therefore no replacement-link migration was
required.

## Intentionally retained names

- The common planning set already expressed the correct authority hierarchy and was not renamed.
- Paper tool files (`main.tex`, `references.bib`, `Makefile`) and external HWP, class, style, and
  font/template names retain their tool or provenance identity.
- Existing paper documents such as `WRITING_PLAN.md`, `SUBMISSION_MILESTONES.md`, and
  `CLAIM_EVIDENCE_AUDIT.md` already expose their role.
- Chronological `2026-07-31-coc-kg-model-checking-design.md` retains its date because it is an
  established dated design record and already ends in its role.
- EBLC implementation, specifications, and conformance evidence remain owned by
  `platforms/eblc-bcv/`; Project 05 links them and does not duplicate them.
- Immutable artifact and archive paths were not rewritten. Historical old paths are retained
  only as keys in `MIGRATION_MAP.json`.

## Pre-existing unrelated broken-link audit

After all renamed documents and canonical entry documents reached zero broken local Markdown
links, a broader read-only scan found 91 pre-existing links in 11 non-entry sources. They are
outside this naming migration and remain for a separate ownership-path cleanup:

| Source group | Broken links | Relationship to this migration |
|---|---:|---|
| six EBLC platform design, guide, report, and specification documents | 75 | older v2 relative paths; no document in this task was renamed there |
| `platforms/eblc-bcv/src/guard_synth_eblc/README.md` | 2 | older implementation README paths |
| `projects/01-safety-constrained-coc/experiments/alpamayo/README.md` | 4 | restricted data/artifact and moved experiment links |
| `projects/03-sequential-coc-verification/docs/designs/2026-07-31-coc-kg-model-checking-design.md` | 1 | retained dated record; unrelated experiment link |
| `projects/03-sequential-coc-verification/experiments/feasibility/README.md` | 8 | older data, third-party, artifact, and experiment paths |
| `projects/04-guardsynth-coc/docs/surveys/COC_SHIELD_SURVEY_NOTES.md` | 1 | historical note pointing to an old restricted result path |

These links do not block project README, STATUS, planning-set, survey-index, renamed-document,
metadata, or result-index entry points. The historical GuardSynth note was not rewritten because
its referenced result path is provenance-sensitive and the note is not canonical evidence.

## Enforcement

The naming checker now verifies the project planning set, role/directory agreement for
requirements, designs, decisions, and reports, forbidden status tokens, survey metadata,
consecutive local survey control prefixes, complete survey-index registration, current-survey
links from the research plan, and replacement links for future `SUPERSEDED` surveys. Structure
tests verify reciprocal planning links, canonical metadata, entry-point links, status fields,
survey registration, and current-survey plan inputs.
