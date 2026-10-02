"""Regression checks for the local-only smoke and source-audit runner."""

import importlib.util
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = next(p for p in Path(__file__).resolve().parents if (p / "PROJECT_REGISTRY.json").is_file())
SPEC = importlib.util.spec_from_file_location(
    "paper1_cnl_learning_run", ROOT / "projects/04-guardsynth-coc/experiments/paper1_cnl_learning/run.py")
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


class Paper1RunnerTest(unittest.TestCase):
    def test_existing_run_is_not_overwritten(self):
        with TemporaryDirectory() as directory, patch.object(runner, "ROOT", Path(directory)):
            output = Path(directory) / "artifacts/projects/guardsynth-coc/restricted/guardsynth-eblc-learning-001/test-001"
            output.mkdir(parents=True)
            marker = output / "RESULT.json"
            marker.write_text("existing evidence")
            with patch.object(sys, "argv", ["run.py", "audit", "--run-id", "test-001"]):
                with self.assertRaises(FileExistsError):
                    runner.main()
            self.assertEqual(marker.read_text(), "existing evidence")

    def test_null_event_rows_are_counted_and_only_exact_time_links_pass(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            acquisition = root / "acquisition"
            cohort = acquisition / "m16-source-acquisition-2026-08-14-v18"
            cohort.mkdir(parents=True)
            candidate = dict(candidate_digest="c1", clip_id="clip1", event_timestamp_us=10,
                             shortlist_slice="PEDESTRIAN_CYCLIST_YIELD")
            runner.write_json(cohort / "SENSOR_MATERIALIZATION_SHORTLIST.json", {"records": [candidate]})
            runner.write_json(cohort / "ATTRITION_RESERVE_COHORT.json", {"records": []})
            previous = acquisition / "m16-cascade-structured-link-audit-2026-09-05-v1"
            previous.mkdir()
            runner.write_json(previous / "CASCADE_STRUCTURED_LINK_AUDIT.json", {"records": [dict(
                candidate_digest="c1", human_observation_status="COMPLETED", field_status={})]})
            reasoning = root / "data/restricted/nvidia_physicalai/reasoning/ood_reasoning.parquet"
            reasoning.parent.mkdir(parents=True); reasoning.write_bytes(b"fixture source bytes")
            rows = [dict(clip_id="clip0", events=None), dict(clip_id="clip1", split="train", feature="camera",
                    events=json.dumps([dict(event_start_timestamp=11, coc="one microsecond different")]))]
            parquet = ModuleType("pyarrow.parquet")
            parquet.read_table = lambda _: SimpleNamespace(num_rows=2, to_pylist=lambda: rows)
            arrow = ModuleType("pyarrow"); arrow.parquet = parquet
            with patch.dict(sys.modules, {"pyarrow": arrow, "pyarrow.parquet": parquet}), \
                    patch.object(runner, "ROOT", root), patch.object(runner, "ACQUISITION", acquisition):
                result = runner.source_audit(root)
            self.assertEqual(result["reasoning_rows_without_events"], 1)
            self.assertEqual(result["exact_coc_link_count"], 0)
            self.assertEqual(result["candidate_count"], 1)
            self.assertEqual(result["paper_cohort_eligibility"], "NOT_EVALUATED")

    @unittest.skipUnless(importlib.util.find_spec("transformers") and runner.MODEL_PATH.is_dir(),
                         "optional installed local VLM processor runtime")
    def test_actual_processor_masks_prompt_and_keeps_full_cnl_and_action(self):
        from transformers import AutoProcessor
        processor = AutoProcessor.from_pretrained(runner.MODEL_PATH, local_files_only=True)
        with TemporaryDirectory() as directory:
            examples = runner.software_examples(Path(directory))
            for example in examples:
                batch, prompt = runner.encode(processor, example)
                n = prompt["input_ids"].shape[1]
                self.assertTrue((batch["labels"][:, :n] == -100).all())
                self.assertTrue(batch["labels"][:, n:].equal(batch["input_ids"][:, n:]))
                self.assertGreater(batch["pixel_values"].numel(), 0)
                target = processor.tokenizer.decode(batch["labels"][0, n:])
                self.assertIn("ACTION: STOP", target)
                if example["arm"] in {"L2", "L3"}:
                    self.assertIn("SOURCE BUNDLE:", target)
                    self.assertIn("synthetic-pedestrian:P18", target)


if __name__ == "__main__":
    unittest.main()
