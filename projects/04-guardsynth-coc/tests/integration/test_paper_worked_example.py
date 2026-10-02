"""Reproducible paper example, explicit gaps and no accidental training export."""

import importlib.util
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

ROOT = next(p for p in Path(__file__).resolve().parents if (p / "PROJECT_REGISTRY.json").is_file())
SPEC = importlib.util.spec_from_file_location("test_paper_example",
    ROOT / "projects/04-guardsynth-coc/experiments/paper1_cnl_learning/worked_example.py")
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


class PaperExampleTest(unittest.TestCase):
    def test_existing_run_is_immutable(self):
        with TemporaryDirectory() as d, patch.object(runner, "BASE", Path(d)):
            target = Path(d) / runner.EXPERIMENT / "test-001"
            target.mkdir(parents=True)
            with patch.object(sys, "argv", ["worked_example.py", "--run-id", "test-001"]):
                with self.assertRaises(FileExistsError):
                    runner.main()

    def test_invalid_run_id_is_rejected(self):
        with patch.object(sys, "argv", ["worked_example.py", "--run-id", "../overwrite"]):
            with self.assertRaises(SystemExit):
                runner.main()

    def test_source_provenance_and_frame_index_distinction(self):
        scene, hashes = runner.source_example()
        self.assertEqual(scene["review_index"], 18)
        self.assertEqual(scene["geometry_folder_index"], 26)
        self.assertEqual(scene["event_timestamp_us"], 9788430)
        self.assertEqual(scene["source_linked_person_ids"], ["Agent3"])
        self.assertEqual(scene["reasoning_event_start_frame"], 99)
        self.assertEqual(scene["decoded_video_frame_index"], 297)
        self.assertIn(scene["raw_video"], hashes)
        self.assertIn(scene["display_overlay"], hashes)
        self.assertFalse(scene["source_complete"])

    def test_full_example_keeps_gaps_and_blocks_training(self):
        import z3
        with TemporaryDirectory() as d:
            output = Path(d)
            result = runner.execute(output)
            self.assertEqual((result["query_count"], result["premise_sat_count"], result["sat_count"], result["unsat_count"]), (11, 11, 6, 5))
            self.assertFalse(result["eblc_frontend_executed"])
            self.assertEqual(result["training_export_count"], 0)
            self.assertEqual(len(result["gap_queries"]), 2)
            self.assertEqual(len(list(output.glob("*.smt2"))), 22)
            for record in result["queries"]:
                for suffix, expected in (("_premises", "SAT"), ("", record["status"])):
                    solver = z3.Solver()
                    solver.from_file(str(output / (record["query_id"] + suffix + ".smt2")))
                    self.assertEqual(str(solver.check()).upper(), expected)
            preview = runner.load(output / "training_example_preview.json")
            self.assertIsNone(preview["action_gold"])
            self.assertIsNone(preview["finalized_assistant_target"])
            self.assertFalse(preview["learning_export_allowed"])
            self.assertFalse(preview["is_validated_L3_example"])
            self.assertFalse(preview["common_input"]["display_overlay_allowed"])
            self.assertEqual(preview["original_target_components"]["coc"], preview["enriched_target_components"]["coc"])
            cnl = runner.load(output / "cnl_correspondence.json")
            self.assertEqual([c["id"] for c in cnl["clauses"]], ["C1", "C2", "C3", "C4", "C5"])
            self.assertEqual(cnl["independent_semantic_audit"], "PENDING")
            self.assertEqual(preview["enriched_target_components"]["constraints"], cnl["text"])
            html = (output / "worked_example.html").read_text()
            self.assertIn("d.showModal()", html)
            self.assertIn("d.close()", html)


if __name__ == "__main__":
    unittest.main()
