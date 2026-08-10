# Generated artifacts

- `intermediate/`: regenerable compiler exports, generated models, temporary indexes, and dry-run products
- `results/public/`: publishable synthetic and baseline run results
- `results/restricted/`: access-controlled model/data-derived run results

Experiment source code must not be added here. Every final run is stored under
`results/<class>/<experiment-id>/<run-id>/` and must include a manifest. Existing result
directories are immutable; use a new run ID for reruns.
