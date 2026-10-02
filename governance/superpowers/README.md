# Superpowers output governance

Superpowers work products are divided into scratch state, promoted project documents, and
historical agent records.

## Scratch state

All task briefs, progress logs, review diffs, review packages, snapshots, and temporary hashes
remain under ignored `.superpowers/sdd/<work-id>/`. They are disposable and are not linked from
canonical project documentation.

## Promotion

A durable output may be promoted only after human review and only when it has:

1. exactly one owner from `PROJECT_REGISTRY.json`;
2. exactly one document class: requirement, plan, design, decision, report, or survey;
3. a stable descriptive name without agent/task numbering;
4. no copied review diffs, snapshots, or hidden source trees;
5. links to immutable execution artifacts instead of embedded result copies.

Promoted documents go directly to `projects/<owner>/docs/<class>/` or, for reusable EBLC work,
`platforms/eblc-bcv/docs/<class>/`. Never create `docs/internal/superpowers/` again.
Record each promotion in [`PROMOTIONS.json`](PROMOTIONS.json) and complete the
[`PROMOTION_CHECKLIST.md`](PROMOTION_CHECKLIST.md) review. A single work ID may normally
promote at most one document per document class. Revisions update that canonical document;
they do not create timestamped copies.

## Historical records

Previously promoted Superpowers documents that are not canonical project documents live under
`archive/agent-history/superpowers/`. They are read-only development history.
