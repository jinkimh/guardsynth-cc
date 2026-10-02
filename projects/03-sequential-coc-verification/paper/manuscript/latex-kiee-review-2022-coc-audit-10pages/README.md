# KIEE sequential-CoC state-consistency review copy

This directory is an independent anonymous-review copy of the finalized
manuscript titled *Stateful Consistency Verification of Sequential CoC
Annotations for E2E Autonomous Driving: A CoC-Nusc and UPPAAL Study*.

- Content source (read-only): `projects/03-sequential-coc-verification/paper/manuscript`
- KIEE 2022 format reference (read-only):
  `projects/01-safety-constrained-coc/paper/manuscript/latex-kiee-review-2022`
- Review-copy target: `projects/03-sequential-coc-verification/paper/manuscript/latex-kiee-review-2022-coc-audit`

The older source manuscript and reference template remain unchanged.  This
target is the current publication copy and owns
regular copies of its KIEE style, local Noto fonts and OFL license, bibliography,
sections, figures, tests, and build files.  It must not use symbolic links or
source-relative LaTeX inputs; every required source file is copied into this
directory as a regular file.

## Build and structural checks

Run the following commands from this directory:

```bash
make test
make all
```

`make all` runs the structural and editorial checks, then uses LuaLaTeX, BibTeX,
and two additional LuaLaTeX passes (or the equivalent `latexmk -lualatex`
workflow when it is available).  The ten sections
and five figures are target-owned regular files, and the figures are compiled
as local TikZ inputs; this copy does not depend on an external Python
figure-generation environment.

The host TeX Live 2022 installation did not include PGF/TikZ.  For a
self-contained build, the target therefore vendors the PGF 3.1.10 runtime in
`.texlive-local/` (506 regular files, about 6.3 MiB), installed with `tlmgr`
from the frozen official TeX Live 2022 repository at
`https://ftp.math.utah.edu/pub/tex/historic/systems/texlive/2022/tlnet-final`.
The exact TeX Live package metadata is retained at
`.texlive-local/tlpkg/tlpobj/pgf.tlpobj`; it records the upstream package
revision and the licenses `lppl1.3c`, `gpl2`, and `fdl`.  Individual PGF source
files also retain their copyright and dual-license headers.  Their references
to `doc/generic/pgf/licenses/LICENSE` are satisfied by the complete six-file
license directory copied verbatim from the official PGF Git tag `3.1.10`,
commit `dceb378b263061856b9a21082e5dc6fffdcdf494` (Release 3.1.10,
2023-01-15).  That directory contains the umbrella notice, GPL-2.0, LPPL-1.3c,
GFDL-1.2, and the code/documentation manifests.  The Makefile adds only this
local runtime to `TEXINPUTS`, while retaining the normal system and user TeX
search paths.

## Current evidence and scope boundaries

The central experiment samples 27 natural scene clusters from 90 trajectory-linked
multi-CoC scenes and reports both unanimous adjudicated textual consistency and
low pre-adjudication agreement (Fleiss' kappa 0.027).  The 40 synthetic
baseline--mutation pairs are postcondition-enforced rule fixtures, so their
40/40 stateful result is regression coverage rather than natural-error detection
accuracy.  The seven UPPAAL fixtures are generated from the same transition
semantics as the Python checker; 0/7 mismatches therefore establish limited
implementation agreement, not independent semantic verification.

The response-time, provenance, detector-sensitivity, and episode-expansion
analyses are auxiliary evidence.  In particular, the 282 generated models and
1,128 queries validate flag and query serialization, and the metadata-linked
13-chain output is only an implementation smoke test.  None of these results
establishes a natural CoC error rate, physical vehicle safety, or a learning
benefit.
