# Research projects

Each child directory owns one research question and contains its documentation, maintained
code, tests, experiments, manuscript, and result index. The authoritative list is the root
[`PROJECT_REGISTRY.json`](../PROJECT_REGISTRY.json); summaries are in [`PROJECTS.md`](../PROJECTS.md).

Do not place loose files directly in this directory.

The two-digit prefix orders projects by research progression. It is not part of the stable
`project_id`; consult `PROJECT_REGISTRY.json` before adding or reordering a project.

Every project exposes the same planning and survey-management entry points:

```text
docs/plans/01_RESEARCH_PLAN_V01.md
docs/plans/02_PROJECT_MILESTONES.md
docs/plans/03_PROJECT_EXECUTION_TRACKER.md
docs/surveys/README.md
```

The research plan governs scope and success criteria, milestones refine the plan, and the
execution tracker identifies current work. Related-work surveys are formal inputs to the
research plan. The survey index records each maintained survey or note, its authority status,
and the decision it supports without inventing a hierarchy between unrelated topics.
