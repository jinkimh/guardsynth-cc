# GuardSynth-CoC

This is the current central research project. It combines CoC and scene context with external
rule/system evidence, target-zone grounding, and assurance inputs to generate constraints. EBLC
is its output platform, not its final research objective.

The first paper focuses on source-grounded extraction → EBLC verification → faithful natural-language
constraints in CoC training → matched-budget learning effects. Broad runtime/Alpamayo integration,
full-cohort expansion and actual-vehicle validation are phase-2 development, not paper-1 gates.
See the [scope decision](docs/decisions/PAPER_AND_DEPLOYMENT_SCOPE_DECISION_V01.md).
Actual multimodal VLM fine-tuning and held-out visual action evaluation are mandatory for the
first paper; a frozen VLM with only an external scorer trained is not a substitute.

Reusable EBLC execution is provided by [`platforms/eblc-bcv/`](../../platforms/eblc-bcv/).
The independent EBLC language and verification paper is managed by
[`projects/05-eblc-language-verification/`](../05-eblc-language-verification/); GuardSynth remains
the application and synthesis project.

- Status: [`STATUS.md`](STATUS.md)
- Research plan: [`docs/plans/01_RESEARCH_PLAN_V02.md`](docs/plans/01_RESEARCH_PLAN_V02.md)
- Milestones: [`docs/plans/02_PROJECT_MILESTONES.md`](docs/plans/02_PROJECT_MILESTONES.md)
- Execution tracker: [`docs/plans/03_PROJECT_EXECUTION_TRACKER.md`](docs/plans/03_PROJECT_EXECUTION_TRACKER.md)
- Surveys: [`docs/surveys/README.md`](docs/surveys/README.md)
- Results: [`results/RESULT_INDEX.md`](results/RESULT_INDEX.md)
- Engineering subproject: **GuardSynth Studio — CoC & EBLC Data Workbench**
  ([requirements](docs/requirements/GUARDSYNTH_STUDIO_REQUIREMENTS_V01.md),
  [design](docs/designs/GUARDSYNTH_STUDIO_DESIGN_V01.md),
  [design verification](docs/reports/GUARDSYNTH_STUDIO_DESIGN_VERIFICATION_REPORT_V01.md),
  [application](../../apps/guardsynth_studio/README.md),
  [implementation verification](docs/reports/GUARDSYNTH_STUDIO_IMPLEMENTATION_VERIFICATION_REPORT_V01.md)).
  Design approved; local implementation verified. Actual VLM provider acceptance remains pending; no new paper gate.
