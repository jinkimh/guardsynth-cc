"""Conditional subset, review separation and exposure are not scene/action certification."""

from copy import deepcopy
import json
from pathlib import Path
import re
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest

ROOT = next(p for p in Path(__file__).resolve().parents if (p / "PROJECT_REGISTRY.json").exists())
sys.path.insert(0, str(ROOT / "projects/04-guardsynth-coc/experiments/paper1_cnl_learning"))
import prepare_m17_preflight as entry


class PreflightTest(unittest.TestCase):
    def setUp(self):
        self.scene = {"candidate_digest": "candidate-sha256:" + "a" * 64,
            "event_timestamp_us": 10, "original_coc": "SECRET_COC", "machine_points": ["SECRET_POINT"],
            "frames": [{"timestamp_us": 9, "sha256": "hash", "data_url": "data:image/jpeg;base64,AA=="}]}
        self.answer = {"target_status": "CONFIRMED", "zone_status": "CONFIRMED", "ped_truth": "TRUE",
                       "zone_polygon": [[0, 0], [1, 0], [1, 1]], "target_point": [.5, .5]}

    def test_only_reported_known_pedestrian_relation_enters_subset(self):
        before = deepcopy(self.answer)
        contract = entry.build_contract(self.answer, self.scene, ["research-policy", "review"])
        self.assertEqual(self.answer, before)
        self.assertEqual([o["obligation_id"] for o in contract.raw["obligations"]], ["ped"])
        for value in ("UNKNOWN", "NOT_APPLICABLE", "CONFLICT"):
            with self.assertRaises(ValueError):
                entry.build_contract({**self.answer, "ped_truth": value}, self.scene, ["policy"])

    def test_actual_solver_premises_unknowns_and_mutation(self):
        for truth in ("TRUE", "FALSE"):
            contract = entry.build_contract({**self.answer, "ped_truth": truth}, self.scene, ["policy"])
            with TemporaryDirectory() as folder:
                models = entry.checks_for(contract, truth)
                for n, core in enumerate(models):
                    checks = entry.review.helpers.export_checks(core, Path(folder), "test" + str(n))
                    self.assertEqual(checks["matches_expected"], checks["query_count"])
                self.assertEqual(models[2]["queries"][0]["expected"], "SAT")

    def test_action_allowlist_and_no_answers_or_coc(self):
        packet = entry.action_packet(self.scene, self.answer, "development-p001")
        self.assertNotIn("SECRET", json.dumps(packet))
        self.assertNotIn("target_point", packet)
        self.assertNotIn("ped_truth", packet)
        self.assertNotIn("contract", packet)
        self.assertFalse(packet["gold_prefilled"])
        self.assertLessEqual(packet["frames"][-1]["timestamp_us"], packet["event_timestamp_us"])

    def test_packet_html_has_distinct_sample_export_and_valid_js(self):
        packet = entry.action_packet(self.scene, self.answer, "development-p001")
        with TemporaryDirectory() as temp:
            folder = Path(temp)
            entry.write_packet(folder, "action_review", packet, [self.scene["frames"][0]["data_url"]])
            html = (folder / "action_review.html").read_text()
            self.assertNotIn("SECRET", html)
            self.assertNotIn("CNL은 보행자 조건만", html)
            self.assertIn("'development-p001_'", html)
            script = re.search(r"<script>\s*(.*?)</script>", html, re.S)[1]
            result = subprocess.run(["node", "--check"], input=script, text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_exposed_clips_never_become_test_even_if_upstream_val(self):
        rows = [{"clip_id": "same", "candidate_digest": str(i), "upstream_split": "val"} for i in range(2)]
        ledger = entry.exposure_ledger(rows, [{"group_id": "same"}, {"group_id": "another"}])
        self.assertEqual(len(ledger["groups"]), 1)
        self.assertEqual(ledger["excluded_test_clip_ids"], ["another", "same"])
        self.assertFalse(ledger["groups"][0]["main_test_allowed"])
        self.assertIsNone(ledger["main_n"])
        self.assertEqual(ledger["fresh_test_scenes"], 0)

    def test_historical_review_numbers_are_not_geometry_candidate_numbers(self):
        self.assertEqual(entry.disposition({"review_index": 18, "geometry_index": 26}), "PRIOR_DEVELOPMENT_EXPORT")
        self.assertEqual(entry.disposition({"review_index": 47, "geometry_index": 73}), "PRIOR_UNOBSERVABLE_NO_REPEAT")
        self.assertEqual(entry.disposition({"review_index": None, "geometry_index": 18}), "REVIEWED_DEVELOPMENT_PENDING_GATES")


if __name__ == "__main__":
    unittest.main()
