# GuardSynth NCA public release

Owner: `guardsynth-coc`. Status: validated sanitized distribution; publication status is in `RESULT.json`.

Download and extract [the reproducibility archive](guardsynth-nca-reproducibility-2026-10-21-002.tar.gz).
The included README explains metric recomputation, formal-check reruns, model prerequisites,
excluded restricted inputs and license boundaries. [File manifest](SOURCE_MANIFEST.json).
Code: [MIT](license-code.txt). Synthetic data/records: [CC BY 4.0](license-data.txt).

This is a frozen distribution, not a second maintained source tree. Source paths inside
the archive retain the project's original layout. The archive contains no model weights,
licensed road imagery, API credentials or server state. The versioned public folder provides an immutable release view; the default branch
will contain it after the paper-scoped PR is merged.
Host-specific home paths and GPU identifiers have been removed from exported copies.
The file manifest records both original and public hashes; original experiment records remain unchanged.

Validation records: [metrics](verification.json), [formal reruns and 16 tests](formal_verification.json), [public-content checks](public_content_review.json).

See the [paper-specific entry point](../README.md) for the publication scope. The uploaded archive SHA-256 was verified. The earlier repository-wide PR was superseded by a paper-scoped publication.
