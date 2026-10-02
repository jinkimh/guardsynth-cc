# EBLC/BCV platform

Reusable EBLC language, typed derivation and composition, canonical semantics, runtime monitor,
Core lowering, BCV mutation workflows, and bounded SMT/Z3 tooling. Scene retrieval and
GuardSynth applicability logic are outside this platform.

The independent research question, comparative evaluation, and manuscript for EBLC are owned by
[`projects/05-eblc-language-verification/`](../../projects/05-eblc-language-verification/).
Reusable implementation and conformance tests remain here.

- Qualitative action subset: [`action_contract.py`](src/guard_synth_eblc/action_contract.py)
  parses `eblc-action-contract-v0.1` and lowers to existing Core/SMT; the common CNL renderer
  supports the same contract. This is a bounded two-action development policy, not a change to
  numeric EBLC programs or a source-certification/vehicle-safety claim. Scene binding stays in Project 04.

- Status: [`STATUS.md`](STATUS.md)
- Results: [`results/RESULT_INDEX.md`](results/RESULT_INDEX.md)
