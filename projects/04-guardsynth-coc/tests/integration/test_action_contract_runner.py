"""Actual pinned source, shared compiler/CNL and immutable execution checks."""

from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = next(p for p in Path(__file__).resolve().parents if (p / "PROJECT_REGISTRY.json").is_file())
ENTRY = ROOT / "projects/04-guardsynth-coc/experiments/paper1_cnl_learning/action_contract.py"
spec = importlib.util.spec_from_file_location("paper_action_contract_runner", ENTRY)
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


class ActionContractRunnerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.output = Path(cls.temp.name) / "scene18-test-001"
        cls.result = runner.run(cls.output)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def read(self, name):
        return json.loads((self.output / name).read_text())

    def test_real_source_never_becomes_gold_or_export(self):
        scene = self.read("source_example.json")
        self.assertEqual(scene["source_linked_person_ids"], ["Agent3"])
        self.assertEqual(scene["review_index"], 18)
        self.assertFalse(self.result["source_gate"]["source_bound"])
        self.assertFalse(self.result["source_gate"]["learning_export_allowed"])
        self.assertIsNone(self.result["action_gold"])
        self.assertEqual(self.result["training_exports"], 0)
        self.assertEqual(self.result["source_gate"]["event_predicates"]["ped"], {"truth": "UNKNOWN", "evidence_valid": False})

    def test_mismatched_task_identity_rejected(self):
        scene = self.read("source_example.json")
        for field, value in (("review_index", 19), ("event_timestamp_us", 0), ("source_linked_person_ids", ["Agent2"])):
            changed = deepcopy(scene); changed[field] = value
            with self.assertRaises(ValueError):
                runner.prepare_scene18_contract(changed, policy_ref="test:policy", source_refs=["test:policy"])

    def test_compiler_queries_cnl_and_nonvacuous_mutation(self):
        checks = self.read("query_checks.json")
        self.assertEqual(checks["query_count"], 25)
        self.assertEqual(checks["matches_expected"], 25)
        probes = [r for r in checks["results"] if not r["query_id"].endswith("_premises") and r["query_id"] != "base_consistency"]
        self.assertEqual(sum(r["status"] == "UNSAT" for r in probes), 9)
        self.assertTrue(all(r["status"] == "SAT" for r in self.read("mutation_checks.json")["results"]))
        self.assertTrue(all((self.output / r["smt2_file"]).is_file() for r in checks["results"]))
        self.assertEqual(self.read("core_model.json")["grammar_version"], "eblc-core-v0.1")
        self.assertEqual(self.read("cnl_mapping.json")["source_kind"], "ACTION_CONTRACT")
        self.assertIn("UNBOUND", (self.output / "constraints.txt").read_text())

    def test_hashes_and_immutable_run(self):
        manifest = self.read("RUN_MANIFEST.json")
        for field in ("input_hashes", "code_hashes"):
            for path, sha in manifest[field].items():
                self.assertEqual(runner.digest(ROOT / path), sha)
        for name, sha in manifest["output_hashes"].items():
            self.assertEqual(runner.digest(self.output / name), sha)
        with self.assertRaises(FileExistsError):
            runner.run(self.output)


if __name__ == "__main__":
    unittest.main()
