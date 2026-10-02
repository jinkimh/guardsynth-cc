"""Integration contract for the M16 CASCADE structured-link audit."""

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


class M16CascadeStructuredLinkPipelineTest(unittest.TestCase):
    def test_real_98_event_links_are_audited_without_empty_human_review(self) -> None:
        from audit_cascade_structured_links import execute

        with TemporaryDirectory() as directory:
            root = Path(directory)
            restricted = root / "restricted"
            public = root / "public"
            result = execute(
                restricted_output_dir=restricted,
                public_output_dir=public,
                run_id="m16-cascade-structured-link-test-v1",
            )
            self.assertEqual(result["classified_event_count"], 98)
            self.assertEqual(result["cascade_annotation_hash_verified_count"], 98)
            self.assertEqual(result["relevant_actor_or_control_state_closed_count"], 70)
            self.assertEqual(result["target_zone_or_lane_association_closed_count"], 1)
            self.assertEqual(result["new_source_complete_8_of_8_count"], 0)
            self.assertEqual(result["eligible_scene_count"], 1)
            self.assertFalse(result["curator_review_screen_generated"])
            self.assertFalse(result["annotation_start_allowed"])

            work = json.loads(
                (restricted / "SOURCE_GEOMETRY_ACQUISITION_MANIFEST.json").read_text()
            )
            self.assertEqual(work["remaining_event_counts"]["relevant_actor_or_control_state"], 28)
            self.assertEqual(work["remaining_event_counts"]["target_zone_or_lane_association"], 97)
            self.assertTrue(work["empty_or_unsourced_review_prohibited"])

            public_text = "\n".join(
                path.read_text(encoding="utf-8")
                for path in public.iterdir()
                if path.suffix in {".json", ".md"}
            )
            self.assertNotIn("candidate-sha256", public_text)
            self.assertNotIn("clip_id", public_text)
            self.assertNotIn("AgentAction", public_text)
            self.assertNotIn("/home/", public_text)


if __name__ == "__main__":
    unittest.main()
