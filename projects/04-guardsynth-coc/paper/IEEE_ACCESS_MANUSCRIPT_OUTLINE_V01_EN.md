# IEEE Access manuscript structure

This outline records the integrated author-review manuscript. The current title and abstract are in [the front matter](IEEE_ACCESS_TITLE_ABSTRACT_V01_EN.md); the full PDF is [here](../../../artifacts/projects/guardsynth-coc/public/paper1-method-preservation-001/manuscript-revision-2026-09-30-001/ieee-access-manuscript-en.pdf).

## Central contribution

Develop constraint-enhanced CoC systematically: select relevant content from CoC, scene evidence, and supplied rules; separate observations and assumptions; bind supported EBLC fields; verify logical properties; generate CNL and append it to original CoC. The manuscript preserves **task → constraint fields → actual formula → generated CNL → evaluation verdict**.

The preceding Safety-Constrained CoC manuscript already contributes natural-language guards, lifecycle elements, paired-contract evaluation, and the static/temporal/maneuver task families. This paper adds the source-to-specification-to-CNL development path and its supported checks. Reused task principles and new experimental executions are distinguished.

## Section responsibilities

| Section | Content | Evidence |
|---|---|---|
| I Introduction | Context, CoC limitation, prior/current contribution boundary | Preceding manuscript and current six-task results |
| II Related Work | Driving reasoning, traffic-rule logic, language/formalization | Primary sources; no unsupported feature-absence claims |
| III Background | Established CoC/VLM, SMT, CNL, and LoRA concepts | Existing theory, without claiming these as our contributions |
| IV Proposed Method | Inputs; EBLC semantics; why EBLC; source-to-field extraction; verification; CNL insertion; task-to-verdict map | Implemented profiles, exact generated clauses, boundary queries |
| V Experimental Setup | P0/P1/P2, data, budgets, reference rules, metrics | Same settings within each task family |
| VI Results | Six-task performance, contract pairs, shuffling, specification errors, unseen values | Frozen measured results; no new training |
| VII Discussion | Contribution, information conditions, evidence/logic/behavior distinction, limitations | Interpret results without verification-causality claims |
| VIII Conclusion | Method contribution and empirical scope | No new claims |

## Comparisons and boundaries

P0 is CoC alone, P1 adds our existing natural-language constraint, and P2 adds our EBLC-derived CNL. P1 and P2 receive constraints in both training and evaluation. Their difference is an internal representation/development-path comparison. P0 lacks the variable contract, so the primary effect includes additional information. No formal noninferiority or universal P2 superiority is claimed.

Supported specification error injection is included as quality evaluation. Separate EBLC test-generation or runtime-monitoring systems are not contributions here. Detailed seeds, intervals, paraphrases, combined hard conditions, image interventions, auxiliary costs, and archived operational criteria belong in the supplement. Favorable and unfavorable current results are preserved.

The integrated English PDF uses the official IEEE Access template. Author information and the preceding manuscript's publication metadata remain for author confirmation.
