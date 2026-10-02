# EBLC pipelines

| Purpose | Module |
|---|---|
| schema, translation and BCV P0b | `cli.pipelines.eblc.p0b_schema_bcv.run` |
| adversarial robustness audit | `cli.pipelines.eblc.robustness_audit.run` |
| Core-to-SMT compilation | `cli.pipelines.eblc.core_smt_compile.run` |
| high-level v0.1/v0.2 program elaboration and conformance | `cli.pipelines.eblc.program_conformance.run` |
| multi-contract composition and high-level-to-SMT | `cli.pipelines.eblc.composition_compile.run` |
| typed numeric derivation to Core/SMT | `cli.pipelines.eblc.derivation_compile.run` |
| multi-angle scenario validation | `cli.pipelines.eblc.scenario_validation.run` |
| scoped v0.2 release, CNL projection and final regression | `cli.pipelines.eblc.release_candidate.run` |
| restricted derived-scene grounding | `cli.pipelines.eblc.restricted_scene_grounding.run` |

Reusable semantics belong in `platforms/eblc-bcv/src/guard_synth_eblc`, not in these runners.
