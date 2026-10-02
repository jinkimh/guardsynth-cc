"""Real restricted-source and immutable output checks for event bindings."""

import importlib.util
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

ROOT = next(p for p in Path(__file__).resolve().parents if (p / "PROJECT_REGISTRY.json").is_file())
SPEC = importlib.util.spec_from_file_location("test_event_source_runner",
    ROOT / "projects/04-guardsynth-coc/experiments/paper1_cnl_learning/bind_event_sources.py")
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


class EventSourceRunnerTest(unittest.TestCase):
    def test_existing_run_refused(self):
        with TemporaryDirectory() as directory, patch.object(runner, "BASE", Path(directory)):
            target = Path(directory) / runner.EXPERIMENT / "test-001"
            target.mkdir(parents=True)
            marker = target / "RESULT.json"
            marker.write_text("immutable")
            with patch.object(sys, "argv", ["bind_event_sources.py", "--run-id", "test-001"]):
                with self.assertRaises(FileExistsError):
                    runner.main()
            self.assertEqual(marker.read_text(), "immutable")

    def test_real_source_exact_binding_and_release_control_checks(self):
        with TemporaryDirectory() as directory:
            result = runner.execute(Path(directory))
            rows = runner.load(Path(directory) / "event_source_bindings.json")["records"]
            self.assertEqual(result["candidate_count"], 32)
            self.assertEqual(result["reviewed_event_count"], 19)
            self.assertEqual(result["pinned_annotation_count"], 18)
            self.assertEqual(result["event_with_active_causal_target_count"], 9)
            self.assertEqual(result["event_with_unique_source_linked_person_count"], 6)
            self.assertEqual(result["release_control_check_review_indices"], [54, 56])
            self.assertEqual(result["window_target_set_changed_review_indices"], [47, 56])
            self.assertEqual(result["event_with_shared_lane_source_count"], 0)
            self.assertEqual(result["event_with_exact_person_keypoint_count"], 0)
            self.assertEqual(result["sat_query_count"], 0)
            self.assertEqual(result["learning_export_count"], 0)
            self.assertEqual(result["repeat_existing_survey_requested_count"], 0)
            for row in rows:
                self.assertEqual(row["event_hazard_truth"], "UNKNOWN")
                self.assertIsNone(row["selected_action_gold"])
                source = runner.load(ROOT / row["annotation_path"])
                for target in row["active_source_targets"]:
                    pointer = target["evidence_ref"].split("#", 1)[1]
                    node = source
                    for segment in pointer.split("/")[1:]:
                        node = node[int(segment)] if isinstance(node, list) else node[segment]
                    self.assertEqual(node["id"], target["source_ref_id"])
                    self.assertTrue(target["active_at_event"])
            release = next(r for r in rows if r["review_index"] == 56)
            self.assertEqual(release["visible_person_source_ids"], [])
            self.assertTrue(any(c.get("color") == "Red" for c in release["active_control_annotations"]))


if __name__ == "__main__":
    unittest.main()
