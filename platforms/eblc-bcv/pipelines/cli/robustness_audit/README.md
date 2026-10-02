# EBLC robustness audit

Runs deterministic adversarial probes that are intentionally broader than the
locked P0b success suite. A successful audit execution may report gaps; those
gaps are not converted into passing expectations.

```bash
python3 -m cli.pipelines.eblc.robustness_audit.run --run-id <new-run-id>
```
