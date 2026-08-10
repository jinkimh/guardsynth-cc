# Experiments

This tree contains experiment definitions, local fixtures, analysis code, and historical
compatibility packages. Generated results no longer live here.

| Family | Purpose |
|---|---|
| `alpamayo/` | model-inference protocols and runbooks |
| `feasibility/` | CPU-side conformance and physical-feasibility studies |
| `logic/` | bounded temporal logic experiments |
| `uppaal/` | timed-automata generators, queries, and versioned model fixtures |
| `sequential_coc/` | sequential CoC contract experiments |
| `contract_micro_world/` | synthetic closed-loop contract experiments |
| `vlm_guard_learning/` | small-VLM guard learning experiments |
| `eblc_pilot/` | historical P0a mechanism pilot |
| `eblc_p0b/` | historical import/runner compatibility for the maintained public package |

Maintained EBLC code is in `src/guard_synth_eblc/`, maintained tests are in
`tests/guard_synth_eblc/`, and user workflows are in `cli/pipelines/eblc/`.

Output policy:

- regenerable intermediate output: `artifacts/intermediate/`
- public final results: `artifacts/results/public/`
- restricted final results: `artifacts/results/restricted/`

All commands run from the project root. Runners must refuse to overwrite an existing run ID.
