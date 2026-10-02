# EBLC Language Verification experiments

This directory owns paper-specific evaluation protocols, fixtures, baseline adapters, and
analyses. Reusable EBLC implementation and conformance tests remain in
[`platforms/eblc-bcv/`](../../../platforms/eblc-bcv/).

New completed runs must be written to
`artifacts/projects/eblc-language-verification/<public|restricted|intermediate>/` with immutable
run IDs and manifests. No experiment starts before the baseline, benchmark, oracle, and success
criteria are frozen under `EB-M02`.
