"""Integration contract for M16 event-anchor transform closure."""

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


class M16EventAnchorTransformPipelineTest(unittest.TestCase):
    def test_real_98_event_offline_transforms_are_closed_fail_closed(self) -> None:
        from finalize_event_anchor_transforms import execute

        with TemporaryDirectory() as directory:
            root = Path(directory)
            restricted = root / "restricted"
            public = root / "public"
            result = execute(
                restricted_output_dir=restricted,
                public_output_dir=public,
                run_id="m16-event-anchor-transform-test-v1",
            )
            self.assertEqual(result["classified_event_count"], 98)
            self.assertEqual(result["verified_coordinate_transform_count"], 98)
            self.assertEqual(result["event_anchor_binding_count"], 98)
            self.assertEqual(result["new_source_complete_8_of_8_count"], 0)
            self.assertEqual(result["eligible_scene_count"], 1)
            self.assertEqual(result["total_scene_shortfall"], 59)
            self.assertFalse(result["annotation_start_allowed"])

            audit = json.loads(
                (restricted / "EVENT_ANCHOR_TRANSFORM_AUDIT.json").read_text()
            )
            self.assertEqual(len(audit["records"]), 98)
            self.assertTrue(all(
                item["field_status"]["verified_coordinate_transform"]
                == "AVAILABLE_SOURCE_LINKED"
                for item in audit["records"]
            ))
            self.assertTrue(all(not item["source_complete"] for item in audit["records"]))

            public_text = "\n".join(
                path.read_text(encoding="utf-8")
                for path in public.iterdir()
                if path.suffix in {".json", ".md"}
            )
            self.assertNotIn("candidate-sha256", public_text)
            self.assertNotIn("clip_id", public_text)
            self.assertNotIn("matrix_4x4", public_text)
            self.assertNotIn("/home/", public_text)


if __name__ == "__main__":
    unittest.main()
