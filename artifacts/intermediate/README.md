# Intermediate artifacts

This directory is for regenerable pipeline output that is consumed by a later stage but is not
a final result. Each subdirectory must identify its producing pipeline and input manifest.

Do not place hand-authored source, requirements, plans, or final reports here.

- `uppaal-models/`: generated UPPAAL XML, queries, and generation profiles; producer code remains
  in `experiments/uppaal/`.
