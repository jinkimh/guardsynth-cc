"""Read-only correspondence output and immutable-run regression checks."""

import importlib.util
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

ROOT = next(p for p in Path(__file__).resolve().parents if (p / "PROJECT_REGISTRY.json").is_file())
SPEC = importlib.util.spec_from_file_location(
    "test_alignment_runner", ROOT / "projects/04-guardsynth-coc/experiments/paper1_cnl_learning/align_reviews.py")
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


class AlignmentRunnerTest(unittest.TestCase):
    def test_existing_run_refused_before_source_reads(self):
        with TemporaryDirectory() as directory, patch.object(runner, "BASE", Path(directory)):
            target = Path(directory) / runner.EXPERIMENT / "test-001"
            target.mkdir(parents=True)
            marker = target / "RESULT.json"; marker.write_text("immutable")
            with patch.object(sys, "argv", ["align_reviews.py", "--run-id", "test-001"]):
                with self.assertRaises(FileExistsError):
                    runner.main()
            self.assertEqual(marker.read_text(), "immutable")

    def test_read_only_html_escapes_sources_and_returns_from_zoom(self):
        row = dict(candidate_digest="a", review_index=1, coc={"text": "<script>alert(1)</script>"},
                   observation={"visual_temporal_observation": "HAZARD_VISIBLE", "visual_association_observation": "CLEAR_VISIBLE", "notes": "<unsafe>"},
                   geometry={"assessment": "CONFIRMED", "polygon_count": 0},
                   draft={"text_ko": "conditional only"}, field_correspondence={}, issues=[])
        html = runner.render_table([row], {"a": {"image_data_url": "data:image/jpeg;base64,AA=="}})
        self.assertNotIn("<script>alert(1)</script>", html)
        self.assertIn("&lt;unsafe&gt;", html)
        self.assertIn("d.showModal()", html)
        self.assertIn("d.close()", html)
        self.assertNotIn("<form", html)
        self.assertIn("새 설문이 아니며", html)

    def test_hash_mismatch_rejected(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "source.json"; path.write_text("changed")
            with self.assertRaisesRegex(ValueError, "source hash changed"):
                runner.verified(path, "0" * 64)

    @unittest.skipUnless(importlib.util.find_spec("pyarrow"), "optional local data runtime")
    def test_real_source_reuse_keeps_denominator_and_blocks_fake_sat(self):
        with TemporaryDirectory() as directory:
            result = runner.execute(Path(directory))
            self.assertEqual(result["candidate_count"], 32)
            self.assertEqual(result["prior_observation_reused_count"], 19)
            self.assertEqual(result["no_prior_observation_count"], 13)
            self.assertEqual(result["conditional_draft_count"], 18)
            self.assertEqual(result["sat_query_count"], 0)
            self.assertEqual(result["learning_export_count"], 0)
            self.assertEqual(result["repeat_existing_survey_requested_count"], 0)
            self.assertTrue(result["review_integrity"]["json_csv_match"])
            self.assertEqual(result["review_integrity"]["human_review_completed_count"], 60)


if __name__ == "__main__":
    unittest.main()
