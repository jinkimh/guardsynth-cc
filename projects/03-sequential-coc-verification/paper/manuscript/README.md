# Domestic-journal manuscript status

The current review revision, clean manuscript, and three reviewer responses are in
[latex-kiee-review-2022-coc-audit-revision-v01/](latex-kiee-review-2022-coc-audit-revision-v01/README.md).
That directory includes the TeX sources and rebuild instructions. Its supporting
records are under `artifacts/projects/sequential-coc-verification/`.

The earlier KIEE anonymous-review copy is retained in
`latex-kiee-review-2022-coc-audit/`.  Its title is *Stateful Consistency
Verification of Sequential CoC Annotations for E2E Autonomous Driving: A
CoC-Nusc and UPPAAL Study*.

The top-level IEEEtran source and `main.pdf` are an older, narrower
response-time/provenance version retained for history.  They must not be used
as the current claim or result specification.  Terminology that could be
misread as medical or supervised-label language has nevertheless been cleaned
up in both source copies.  The retained top-level PDF is historical and was not
regenerated; use the review-revision directory linked above for the revised PDFs.

Build the earlier anonymous-review copy with:

```bash
cd latex-kiee-review-2022-coc-audit
make all
```
