"""A completed PEFT run's provenance exception must not admit future paths."""

from fnmatch import fnmatch
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
PREFIX = "artifacts/projects/guardsynth-coc/restricted/guardsynth-eblc-learning-001/"


class CheckpointNamingExceptionTest(unittest.TestCase):
    def test_completed_run_exception_is_exact_and_manifest_bound(self):
        catalog = json.loads((ROOT / "docs/architecture/NAMING_EXCEPTIONS.json").read_text())
        matches = [item for item in catalog["exceptions"] if "paper1-vlm-smoke" in item["pattern"]]
        self.assertEqual(len(matches), 1)
        pattern = matches[0]["pattern"]
        run = PREFIX + "paper1-vlm-smoke-2026-09-06-002"
        self.assertEqual(pattern, run + "/adapters/L[0-3]")
        manifest = json.loads((ROOT / run / "RUN_MANIFEST.json").read_text())
        for arm in ("L0", "L1", "L2", "L3"):
            self.assertTrue(fnmatch(run + "/adapters/" + arm, pattern))
            self.assertTrue((ROOT / run / "adapters" / arm).is_dir())
            self.assertIn(f"adapters/{arm}/adapter_model.safetensors", manifest["output_hashes"])
        self.assertFalse(fnmatch(run + "/adapters/L4", pattern))
        self.assertFalse(fnmatch(PREFIX + "paper1-vlm-smoke-2026-09-06-003/adapters/L0", pattern))
        self.assertFalse(fnmatch(run + "/adapters/L0/EXTRA", pattern))


if __name__ == "__main__":
    unittest.main()
