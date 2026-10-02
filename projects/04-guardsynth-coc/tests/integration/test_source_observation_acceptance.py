"""Observation intake must not manufacture nonapplicability or independent action gold."""

from copy import deepcopy
from pathlib import Path
import sys
import unittest

ROOT = next(p for p in Path(__file__).resolve().parents if (p / "PROJECT_REGISTRY.json").exists())
sys.path.insert(0, str(ROOT / "projects/04-guardsynth-coc/experiments/paper1_cnl_learning"))
import accept_source_observations as audit


class ObservationAcceptanceTest(unittest.TestCase):
    def setUp(self):
        self.scene = {"candidate_digest": "synthetic", "event_timestamp_us": 1,
                      "label": "SYNTHETIC TEST", "original_coc": "Stop for a signal."}
        self.answer = {"candidate_digest": "synthetic", "event_timestamp_us": 1,
            **{f: "NOT_APPLICABLE" for f in audit.entry.CHOICES},
            **{f: "" for f in audit.entry.TEXTS}, "target_point": None,
            "zone_polygon": [], "reviewed_at": "2026-09-28T00:00:00+00:00"}
        self.response = {"review_version": audit.entry.VERSION, "packet_sha256": "test",
                         "reviewer_id": "SYNTHETIC", "records": [self.answer]}
        self.draft = {**deepcopy(self.response), "kind": "DRAFT", "completed": ["synthetic"]}

    def test_legacy_absence_is_never_clearance(self):
        before = deepcopy(self.answer)
        row = audit.interpret(self.answer, self.scene)
        self.assertEqual(self.answer, before)
        self.assertTrue(all(f["interpretation"] == "UNRESOLVED_LEGACY_NOT_APPLICABLE"
                            for f in row["field_interpretations"].values()))
        self.assertIsNone(row["formal_predicates"])
        self.assertIsNone(row["independent_action_gold"])
        self.assertFalse(row["main_training_allowed"])
        self.assertFalse(row["repeat_source_survey_requested"])

    def test_unknown_and_conflict_are_preserved_not_corrected_by_coc(self):
        for value in ("TRUE", "FALSE", "UNKNOWN", "CONFLICT"):
            row = audit.interpret({**self.answer, "control_truth": value}, self.scene)
            self.assertEqual(row["field_interpretations"]["control_truth"]["interpretation"], "REPORTED_" + value)
            self.assertFalse(row["field_interpretations"]["control_truth"]["formal_evidence_validated"])

    def test_clarification_only_for_exact_scene_and_only_signal(self):
        self.assertIsNone(audit.interpret(self.answer, self.scene)["user_clarification"])
        scene = {**self.scene, "candidate_digest": audit.SCENE59}
        row = audit.interpret({**self.answer, "candidate_digest": audit.SCENE59}, scene)
        self.assertEqual(row["user_clarification"]["applies_to"], "SIGNAL_ONLY_NOT_ALL_CONTROLS")
        self.assertEqual(row["raw_answer"]["control_context"], "NOT_APPLICABLE")

    def test_complete_response_required_and_draft_must_match(self):
        packet = {"scenes": [self.scene]}
        audit.validate_submission(packet, "test", self.response, self.draft)
        for field, value in (("records", []), ("completed", []), ("reviewer_id", "OTHER")):
            with self.subTest(field=field), self.assertRaises(ValueError):
                audit.validate_submission(packet, "test", self.response, {**self.draft, field: value})
        with self.assertRaises(ValueError):
            audit.validate_submission(packet, "wrong", self.response, self.draft)
        with self.assertRaises(ValueError):
            audit.validate_submission(packet, "test", {**self.response, "records": []}, self.draft)


if __name__ == "__main__":
    unittest.main()
