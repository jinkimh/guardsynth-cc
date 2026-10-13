# Sequential consistency: executable research artifact

This tree contains authored symbolic inputs, executable checking code, UPPAAL
models/queries, and retained results. It is exported from maintained research
sources, plus the original categorical human judgments under anonymous IDs.
It contains no natural CoC text, camera video, trajectory files, personal names,
free-text review notes, manuscript, peer-review letters, or original Git history.

## Reproduce

Requirements: Python 3.10 or newer and a C++17 compiler named `c++`.
The default run uses only the Python standard library and the compiler:

```sh
python3 -B reproduce.py --output /tmp/consistency-reproduction
```

It verifies the file inventory, regenerates the original 40 regression pairs byte
for byte, recomputes human Fleiss kappa and Gwet AC1, reconstructs all 144/81
authored inputs and model files, reruns Python comparisons, and enumerates all 35,042,928 bounded sequences
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
| `evidence/regression` | Original 40 structured reference/mutation pairs and deterministic generator; full-history 40/40 versus current-event 20/40 |
| `evidence/human` | Preserved Korean review instructions, anonymous 27-subject x 4-rater categorical judgments, agreement statistics and rater distributions |
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

The 40 pairs are controlled synthetic IR, not natural source sentences. Their
generator checks its expected postconditions using the checkers themselves; this
is a regression test, not an independent detection-accuracy experiment. The broad
natural-data pipeline drivers are unnecessary for replaying this generator.

The anonymous ratings retain the three original categorical fields, including
exact action-sequence strings. Subject IDs G01-G27 follow the preserved analysis
order and raters A-D match its distributions. Original review IDs, filenames,
initials, free-text notes and ID mappings are excluded. Release authorization for
the anonymous categorical table was confirmed before preparing this export.
The statistical functions are extracted unchanged from the maintained analysis;
the default replay verifies its retained coefficients and exact pair enumeration.

`evidence/human/REVIEW_PROTOCOL.md` is the unchanged retained instruction document.
Its historical WAITING status and two-form A/B saving instructions are preserved;
it is not evidence of all four raters' training or adjudication procedures. No new
human evaluation or natural semantic gold is implied. Trajectory comparison and
the 134-event response analysis cannot be fully replayed without separately
obtained source data. Historical model revisions, generation prompts/settings,
and the quality-score formula/threshold remain unrecoverable.

`artifact_manifest.json` records every exported file hash, original byte hashes,
and any export-only transformation. Original execution commands with workstation
paths are omitted from exported result records. Scientific inputs, expected labels,
predictions and measured results are preserved. The historical paper specification
and original run manifests are kept by the authors, rather than copied here.

The authors retain ownership of the supplied research material. This review
artifact does not add a separate open-source license; public redistribution terms
must be established separately. UPPAAL is supplied independently by the reader.
