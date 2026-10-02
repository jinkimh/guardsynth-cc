# Source-aware GuardSynth generation

This public pipeline converts a validated RuleTemplate reference, grounded
ContextGraph, vehicle assurance profile, and explicit compiler/composition
policy into an EBLC v0.2 program template and indexed actor–zone collection.

```bash
python3 -m cli.pipelines.guardsynth.source_aware_generate.run
```

CoC evidence remains `CLAIMED` and is never used as activation evidence.
Missing or ambiguous association, geometry, transform, observation, or vehicle
profile input produces a verdict/reason artifact and no executable collection.
