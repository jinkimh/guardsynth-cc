# GuardSynth: paper-specific reproducibility materials

Project owner: `guardsynth-coc`.

This folder accompanies **GuardSynth: Checkable Behavioral Constraints for
CoC-Augmented Candidate Selection**. It is the entry point for the code,
synthetic data, protocols, and archived predictions used in this paper.

## Download and reproduce

The validated distribution is
[github-release-2026-10-21-002](github-release-2026-10-21-002/README.md).

- [Download the reproducibility archive](github-release-2026-10-21-002/guardsynth-nca-reproducibility-2026-10-21-002.tar.gz).
- [File inventory and SHA-256 digests](github-release-2026-10-21-002/SOURCE_MANIFEST.json).
- [Independent metric recomputation](github-release-2026-10-21-002/verification.json).
- [Formal-check reruns and unit controls](github-release-2026-10-21-002/formal_verification.json).
- [Public-content checks](github-release-2026-10-21-002/public_content_review.json).

Extract the archive and run from the extracted `guardsynth-nca` directory:

```sh
python3 projects/04-guardsynth-coc/pipelines/cli/paper_release/verify.py --root .
```

This command uses the Python standard library to check the file digests and
recompute the central candidate-selection results. The extracted README gives
the dependencies and commands for rerunning the formal checks and GPU experiments.

## Scope

The distribution contains this paper's selected experimental source, synthetic
inputs, predictions, and checking results. Reused scene generators and Core/SMT
dependencies retain their original paths inside the archive. They are included
only as dependencies of these experiments; other projects' manuscripts,
research outputs, repository applications, and API-server state are not part of
the package.

Model weights and licensed road-scene inputs for the Alpamayo diagnostics
are excluded. Obtain those inputs from their original providers under the
applicable terms. Host-specific paths and GPU identifiers have been removed
from exported copies; local original experiment records are preserved.

## Licenses

Original code in this distribution: [MIT](github-release-2026-10-21-002/license-code.txt).
Synthetic data and generated experiment records:
[CC BY 4.0](github-release-2026-10-21-002/license-data.txt).
Third-party references and dependencies retain their own terms. These licenses
apply to the specified distribution, not to the entire parent repository.
