# Public source packages

`src/` contains reusable, publishable library code. Experiment orchestration,
result writing, and command-line argument parsing do not belong here.

- `guard_synth_eblc/`: schema-driven EBLC representations, binding,
  operational semantics, runtime/bounded targets, BCV mutations, and adapters

Run user-facing workflows through the purpose-named modules under
`cli/pipelines/`.
