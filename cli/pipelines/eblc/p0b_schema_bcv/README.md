# EBLC P0b schema and BCV pipeline

Runs the public synthetic P0b fixture through schema validation, canonical and
separate target agreement, controlled BCV mutations, and result-manifest
generation. The historical `experiments.eblc_p0b.run_p0b` module is retained
as a compatibility entry point.

## Solver runtime

The pipeline selects the isolated Z3 5.0.0 build below
`runtime/solvers/z3-5.0.0-x86_64-glibc-2.36` before importing the EBLC bounded
target. This overrides an older `z3` package available later on the active
interpreter's search path without modifying that environment. The selected
version and module path are written to the run manifest.

Set `GUARDSYNTH_Z3_PREFIX` to an alternative compatible Z3 5.0.0 prefix. The
pipeline fails on a missing installation, a version mismatch, or a different
Z3 native library that was already imported in the process.
