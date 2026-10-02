"""Integration test for the M16 treaty authority binding run."""

from __future__ import annotations

import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest


ROOT = next(
    parent
    for parent in Path(__file__).resolve().parents
    if (parent / "PROJECT_REGISTRY.json").is_file()
)
PIPELINE = ROOT / "projects/04-guardsynth-coc/pipelines/cli/m16_scene_acquisition"
if str(PIPELINE) not in sys.path:
    sys.path.insert(0, str(PIPELINE))


class M16TreatyAuthorityPipelineTest(unittest.TestCase):
    def test_current_98_event_frontier_receives_treaty_baseline(self) -> None:
        from bind_treaty_authority import execute

        frontier = ROOT / (
            "artifacts/projects/guardsynth-coc/restricted/"
            "guardsynth-m16-scene-acquisition-001/"
            "m16-geometry-source-frontier-2026-09-06-v1"
        )
        with TemporaryDirectory() as directory:
            output = Path(directory) / "authority"
            result = execute(
                frontier_run_dir=frontier,
                output_dir=output,
                run_id="m16-treaty-authority-binding-test-v1",
            )
            self.assertEqual(result["treaty_normative_baseline_bound_count"], 98)
            self.assertEqual(result["direct_treaty_rule_count"], 35)
            self.assertEqual(result["general_due_care_fallback_count"], 63)
            self.assertEqual(result["domestic_detail_required_count"], 63)
            self.assertEqual(result["domestic_legal_compliance_closed_count"], 0)
            self.assertEqual(result["eligible_scene_count"], 1)
            self.assertFalse(result["annotation_start_allowed"])

            audit = json.loads((output / "TREATY_AUTHORITY_AUDIT.json").read_text())
            self.assertEqual(len(audit["records"]), 98)
            self.assertTrue(
                all(
                    record["authority_status"]
                    == "AVAILABLE_TREATY_NORMATIVE_BASELINE"
                    for record in audit["records"]
                )
            )
            queue = json.loads((output / "SOURCE_ACQUISITION_QUEUE.json").read_text())
            self.assertNotIn(
                "BIND_JURISDICTION_MATCHED_AUTHORITY", queue["task_counts"]
            )
            self.assertEqual(queue["record_count"], 98)
            self.assertEqual(
                {path.name for path in output.iterdir()},
                {
                    "TREATY_AUTHORITY_AUDIT.json",
                    "SOURCE_ACQUISITION_QUEUE.json",
                    "RESULT.json",
                    "RUN_MANIFEST.json",
                    "REPORT_KO.md",
                },
            )


if __name__ == "__main__":
    unittest.main()
