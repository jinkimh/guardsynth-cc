# Source-gap completion and nonapplicable responses

- project_id: `guardsynth-coc`
- Date: 2026-09-09
- Authority: user's completion-count defect report and request not to require notes for nonapplicable items
- Base design: [development dataset and gap review](PAPER1_DEVELOPMENT_DATASET_AND_GAP_REVIEW_DESIGN_V01.md)

This amendment replaces only the blanket reason requirement in the source-only questionnaire.
Explicit NOT_APPLICABLE makes its associated note optional; the exported note stays empty,
not machine-written. UNKNOWN, CONFLICT and positive/negative observations still need reasons.
Target and zone status now also permit explicit NOT_APPLICABLE. No selection is not a response,
and no target is not silently converted to UNKNOWN, FALSE or an independent action label.
These are backward-compatible response-choice extensions: existing packet identity, draft key
and prior answers remain valid. Current UI and intake validators accept the same choices.

Completion counts input-valid human submissions, not source acceptance or training eligibility.
Show the count next to the completion button and all validation issues with Korean question
names; do not quietly report only a raw field name. Drawing-end is distinct from answer completion.
Repeated identical input events must not invalidate a completed answer; actual edits must.
Save completed state and preserve its count after reload. If browser storage fails, report that
explicitly and instruct JSON backup, rather than overwriting the warning with a success message.
No existing answers, point/polygon coordinates, paper gate or independent-gold requirement changes.
