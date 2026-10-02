# Research project index

The repository contains five research projects and one shared verification platform. File
placement is governed by the [Project Structure Codex](docs/architecture/PROJECT_STRUCTURE_CODEX.md).

| Order | Owner | Purpose | Entry point |
|---:|---|---|---|
| 01 | Safety-Constrained CoC | Constraint-conditioned goal-preserving behavior | [`projects/01-safety-constrained-coc/`](projects/01-safety-constrained-coc/) |
| 02 | Specification Alignment | Natural, structured, and executable specification interfaces | [`projects/02-specification-alignment/`](projects/02-specification-alignment/) |
| 03 | Sequential CoC Verification | Stateful consistency of sequential CoC annotations | [`projects/03-sequential-coc-verification/`](projects/03-sequential-coc-verification/) |
| 04 | GuardSynth-CoC | Evidence-grounded constraint synthesis | [`projects/04-guardsynth-coc/`](projects/04-guardsynth-coc/) |
| 05 | EBLC Language Verification | Independent language, lowering, and BCV evaluation | [`projects/05-eblc-language-verification/`](projects/05-eblc-language-verification/) |
| — | EBLC/BCV platform | Shared contract language and verification backend | [`platforms/eblc-bcv/`](platforms/eblc-bcv/) |

Paper numbering is publication metadata, not directory ownership.
Project directory numbering represents research progression and is registered separately from
the stable owner ID.

Project 05 owns the independent EBLC research question and paper. The reusable implementation
continues to live in `platforms/eblc-bcv/`, which is also consumed directly by projects 02 and 04.
