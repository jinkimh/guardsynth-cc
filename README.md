# Sequential consistency: executable research artifact

This tree contains authored symbolic inputs, executable checking code, UPPAAL
models/queries, and retained results. It is exported from maintained research
sources. It contains no natural CoC text, camera video, trajectory files,
individual human-review records, manuscript, peer-review letters, or Git history.

## Reproduce

Requirements: Python 3.10 or newer and a C++17 compiler named `c++`.
The default run uses only the Python standard library and the compiler:

```sh
python3 -B reproduce.py --output /tmp/consistency-reproduction
```

It verifies the file inventory, reconstructs all 144/81 authored inputs and model
files, reruns Python comparisons, and enumerates all 35,042,928 bounded sequences
plus the separate 5,256-case processing-fault control. Outputs must be written to
a new directory. The full bounded enumeration is native C++, not a UPPAAL search.

To rerun the actual model checker as well, supply your own working installation
of UPPAAL/verifyta (the retained runs used version 5.0.0):

```sh
python3 -B reproduce.py --output /tmp/consistency-with-solver --verifyta /path/to/verifyta
```

This additionally checks 144 original models, their 144 terminal-query diagnoses,
144 condition-linked models, and 162 boundary models. No solver executable,
license file, or third-party dataset is distributed here. The unused natural
table-reader functions in the original code need pandas and separately obtained
data; they are outside these reproduction commands. Its pandas import is deferred
in this export, without changing the checker or parser computations.

## Evidence and interpretation

| Material | What can be checked |
|---|---|
| `evidence/controlled` | All 144 authored text/frame cases; original full-history agreement 96/144; local/window comparisons; FSM 144/144; automatic parser yields UNKNOWN in all cases |
| `evidence/condition` | Same-case post-development retest, 144/144; issue location/obligation/reason records |
| `evidence/terminal` | Original prefix traces differ on uncertainty reasons in 24 cases; terminal-query diagnosis agrees in all 144 |
| `evidence/boundary` | All 81 authored cases; state carry 81/81 versus boundary reset 14/81 |
| `evidence/bounded` | 35,042,928 unselected sequences, zero disagreements; all 1,884 fault-control disagreements retained separately |

Inputs, labels, models and the separate formula evaluator share research
authorship. These are regression/feasibility and bounded implementation-conformance
results, not independent semantic gold, natural detection accuracy, or vehicle
safety evidence. The condition-linked and boundary models have different lifecycle
policies; they are not asserted to be equivalent. An explicit P2 release-command
input and quantitative timing guarantees are outside these primary models.

Natural 27-scene human agreement, trajectory comparison, the 134-event response
analysis and the original 40 regression pairs are excluded from full replay here:
their underlying natural/individual records are not distributed in this artifact.
No new human evaluation or natural accuracy claim is implied.

`artifact_manifest.json` records every exported file hash, original byte hashes,
and any export-only transformation. Original execution commands with workstation
paths are omitted from exported result records. Scientific inputs, expected labels,
predictions and measured results are preserved. The historical paper specification
and original run manifests are kept by the authors, rather than copied here.

The authors retain ownership of the supplied research material. This review
artifact does not add a separate open-source license; public redistribution terms
must be established separately. UPPAAL is supplied independently by the reader.
