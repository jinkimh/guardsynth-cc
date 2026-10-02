"""Denominator, causal-frame and admission boundaries for the 32-scene audit."""

import csv
from pathlib import Path
import sys
import unittest

ROOT = next(p for p in Path(__file__).resolve().parents if (p / "PROJECT_REGISTRY.json").exists())
sys.path.insert(0, str(ROOT / "projects/04-guardsynth-coc/experiments/paper1_cnl_learning"))
import audit_training_candidates as entry

RUN = entry.BASE / entry.EXPERIMENT / "candidate-readiness-2026-09-08-003"


class TrainingCandidateAuditTest(unittest.TestCase):
    def test_readiness_requires_every_gate(self):
        row = {"assets_verified": True, "prior_observation": "HAZARD_VISIBLE", "missing_codes": [],
               "source_accepted": True, "contract_cnl_linked": True,
               "independent_action_available": True, "cnl_review_available": True}
        self.assertEqual(entry.classify(row), "READY")
        for field in ("source_accepted", "contract_cnl_linked", "independent_action_available", "cnl_review_available"):
            altered = {**row, field: False}
            self.assertEqual(entry.classify(altered), "NEEDS_CONFIRMATION")
        self.assertEqual(entry.classify({**row, "missing_codes": ["ROAD_UNKNOWN"]}), "NEEDS_CONFIRMATION")
        self.assertEqual(entry.classify({**row, "prior_observation": "NOT_OBSERVABLE"}), "CURRENTLY_UNUSABLE")
        self.assertEqual(entry.classify({**row, "assets_verified": False}), "CURRENTLY_UNUSABLE")

    def test_causal_frame_never_uses_nearest_future(self):
        times = [{"frame_index": 0, "timestamp": 900}, {"frame_index": 1, "timestamp": 1001}]
        self.assertEqual(entry.select_causal_frame(times, 1000)["frame_index"], 0)
        self.assertEqual(entry.select_causal_frame(times, 1001)["frame_index"], 1)
        self.assertIsNone(entry.select_causal_frame(times, 899))
        with self.assertRaises(ValueError):
            entry.select_causal_frame(list(reversed(times)), 1000)

    def test_duplicate_candidates_rejected(self):
        with self.assertRaises(ValueError):
            entry.index_unique([{"candidate_digest": "test"}] * 2)

    def test_real_denominator_and_scene18_updates(self):
        records = entry.source.load(RUN / "candidate_readiness.json")["records"]
        self.assertEqual(len(entry.index_unique(records)), 32)
        self.assertEqual(sum(r["prior_observation"] is not None for r in records), 19)
        self.assertTrue(all(not r["learning_export_allowed"] for r in records))
        self.assertTrue(all(r["assets_verified"] for r in records))
        self.assertEqual(sum(r["asset_candidate_digest"] != r["candidate_digest"] for r in records), 4)
        self.assertTrue(all(r["causal_frame_offset_us"] <= 0 for r in records))
        row = next(r for r in records if r["review_index"] == 18)
        self.assertTrue(row["contract_cnl_linked"])
        self.assertTrue(row["independent_action_available"])
        self.assertTrue(row["reviewed_event_zone"])
        self.assertEqual(row["event_predicates"]["road"]["truth"], "UNKNOWN")
        self.assertEqual(row["status"], "NEEDS_CONFIRMATION")
        self.assertNotIn("EVENT_TARGET_ZONE_PREDICATES_UNCONFIRMED", row["missing_codes"])
        self.assertEqual(next(r for r in records if r["review_index"] == 47)["status"], "CURRENTLY_UNUSABLE")
        for index in (54, 56):
            self.assertIn("RELEASE_NOT_GLOBAL_PERMISSION", next(r for r in records if r["review_index"] == index)["missing_codes"])

    def test_group_quarantine_not_random_test_split(self):
        records = entry.source.load(RUN / "candidate_readiness.json")["records"]
        result = entry.split_audit(records)
        self.assertEqual(result["group_count"], 29)
        self.assertFalse(result["split_frozen"])
        self.assertEqual(result["test_assignments"], [])
        self.assertTrue(all(not g["test_allowed"] for g in result["groups"]))
        self.assertEqual(sum(len(g["candidate_digests"]) for g in result["groups"]), 32)

    def test_artifact_integrity_csv_and_immutable_output(self):
        entry.reviewed.revalidate_run(RUN)
        with (RUN / "candidate_readiness.csv").open(encoding="utf-8-sig") as stream:
            self.assertEqual(len(list(csv.DictReader(stream))), 32)
        with self.assertRaises(FileExistsError):
            entry.run(RUN)


if __name__ == "__main__":
    unittest.main()
