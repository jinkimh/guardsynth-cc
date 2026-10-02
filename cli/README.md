# Repository CLI

Root `cli/` owns repository-wide path, solver-runtime, manifest, and layout-maintenance tools.
The `cli/pipelines/guardsynth/` and `cli/pipelines/eblc/` namespaces are forwarding shims only.

Canonical domain workflows live at:

- `projects/04-guardsynth-coc/pipelines/cli/<purpose>/run.py`
- `platforms/eblc-bcv/pipelines/cli/<purpose>/run.py`

Repository maintenance workflows remain under `cli/pipelines/maintenance/`.
