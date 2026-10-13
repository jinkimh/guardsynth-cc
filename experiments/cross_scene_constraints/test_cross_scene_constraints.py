"""Semantic boundary cases; the experiment additionally runs the real solver."""
import importlib.util
from pathlib import Path
import unittest

SPEC = importlib.util.spec_from_file_location("cross_scene_constraints", Path(__file__).with_name("run.py"))
API = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(API)


class CrossSceneConstraintsTests(unittest.TestCase):
    def setUp(self):
        self.cases = {c["case_id"]: c for c in API.build_cases()}

    def test_factorial_labels_cover_mixed_known_and_unknown(self):
        self.assertEqual(len(self.cases), 81)
        self.assertEqual(self.cases["joint-3scenes-u-f-t"]["expected"]["verdict"], "CONTRADICTION")
        self.assertEqual(self.cases["joint-3scenes-u-f-t"]["expected"]["obligation_id"], "signal")
        self.assertEqual(self.cases["joint-2scenes-u-t-t"]["expected"]["verdict"], "UNKNOWN")
        self.assertEqual(self.cases["joint-2scenes-t-t-t"]["expected"]["verdict"], "CONSISTENT")

    def test_wrong_target_is_not_release_evidence(self):
        encoded = API.encode(self.cases["pedestrian-wrong-entity-release"]["events"])
        self.assertEqual(encoded["observations"][-1], -1)

    def test_boundary_identity_and_evidence_validity_are_separate(self):
        held = API.encode(self.cases["signal-held-across-boundary"]["events"])
        expired = API.encode(self.cases["signal-evidence-expired"]["events"])
        uncertain = API.encode(self.cases["signal-identity-uncertain"]["events"])
        self.assertEqual((held["carry"][-1], held["persist"][-1]), (1, 1))
        self.assertEqual((expired["carry"][-1], expired["persist"][-1]), (1, 0))
        self.assertEqual((uncertain["carry"][-1], uncertain["persist"][-1]), (-1, 0))

    def test_missing_boundary_proof_does_not_confirm_identity(self):
        events = [API.frame("a", "STOP", "pedestrian"), API.frame("b", "GO")]
        for i, e in enumerate(events):
            e["event_id"] = str(i)
        self.assertEqual(API.encode(events)["carry"], [2, -1])

    def test_reset_baseline_changes_boundary_policy_only(self):
        events = self.cases["joint-3scenes-f-f-f"]["events"]
        full, reset = API.encode(events), API.encode(events, True)
        for key in ("event_ids", "obligation_ids", "actions", "creates", "observations"):
            self.assertEqual(full[key], reset[key])
        self.assertEqual(full["carry"][-3:], [1, 1, 1])
        self.assertEqual(reset["carry"][-3:], [0, 0, 0])

    def test_reactivation_retains_creation_after_boundary(self):
        encoded = API.encode(self.cases["obstacle-reactivated-unknown"]["events"])
        self.assertEqual(encoded["creates"], [0, -1, 0, -1])
        self.assertEqual(encoded["observations"], [0, 1, -1, -1])

    def test_partial_solver_output_is_rejected(self):
        with self.assertRaises(ValueError):
            API.parse_result("Formula is satisfied.", {})


if __name__ == "__main__":
    unittest.main()
