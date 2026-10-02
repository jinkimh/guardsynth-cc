"""Conditional admission must not invent evidence, labels or main-study readiness."""

from copy import deepcopy
from pathlib import Path
import sys
import unittest

ROOT = next(p for p in Path(__file__).resolve().parents if (p / "PROJECT_REGISTRY.json").exists())
sys.path.insert(0, str(ROOT / "projects/04-guardsynth-coc/experiments/paper1_cnl_learning"))
import complete_candidate_bindings as entry
from guard_synth.conditional_admission import assess_conditional_candidate

RUN = entry.audit.BASE / entry.audit.EXPERIMENT / "conditional-candidates-2026-09-08-002"


class ConditionalAdmissionTest(unittest.TestCase):
    def setUp(self):
        self.row = deepcopy(next(r for r in entry.r.load(entry.PRIOR / "candidate_readiness.json")["records"] if r["review_index"] == 18))
        self.options = dict(english_meaning_recorded=True, supported_scope=True,
                            solver_checks_passed=True, permitted_actions=["DEFER_ENTRY"])

    def assess(self, row=None, **options):
        return assess_conditional_candidate(self.row if row is None else row, **{**self.options, **options})

    def test_unknown_preserved_not_full_source_or_main(self):
        original = deepcopy(self.row)
        result = self.assess()
        self.assertTrue(result["conditional_development_admissible"])
        for key in ("all_predicates_resolved", "source_accepted_unchanged", "nominal_entry_label_available", "main_study_admissible", "learning_export_allowed"):
            self.assertFalse(result[key], key)
        self.assertEqual(self.row, original)
        self.assertEqual(self.row["event_predicates"]["road"], {"truth": "UNKNOWN", "evidence_valid": False})

    def test_missing_linkage_and_reviews_rejected(self):
        for key in ("assets_verified", "contract_cnl_linked", "independent_action_available", "cnl_review_available"):
            for invalid in (False, None, "true", 1):
                with self.subTest(key=key, invalid=invalid):
                    self.assertFalse(self.assess({**self.row, key: invalid})["conditional_development_admissible"])

    def test_required_scope_solver_and_english(self):
        for key in ("english_meaning_recorded", "supported_scope", "solver_checks_passed"):
            self.assertFalse(self.assess(**{key: False})["conditional_development_admissible"])

    def test_missing_or_degenerate_geometry(self):
        for key, value in (("reviewed_event_target", None), ("reviewed_event_zone", None),
                           ("reviewed_event_zone", [[0, 0], [.5, .5], [1, 1]])):
            result = self.assess({**self.row, key: value})
            self.assertIn("CONFIRMED_TARGET_ZONE_REQUIRED", result["reasons"])

    def test_unknown_only_and_malformed_predicates_fail_closed(self):
        for predicates in (None, {}, {"ped": {"truth": "TRUE", "evidence_valid": True}},
                           {"ped": {"truth": [], "evidence_valid": True}, "road": self.row["event_predicates"]["road"]},
                           {p: {"truth": "UNKNOWN", "evidence_valid": False} for p in ("ped", "road")},
                           {p: {"truth": "TRUE", "evidence_valid": "true"} for p in ("ped", "road")}):
            self.assertIn("CONFIRMED_EVENT_EVIDENCE_REQUIRED", self.assess({**self.row, "event_predicates": predicates})["reasons"])

    def test_action_disagreement_requires_adjudication(self):
        result = self.assess({**self.row, "independent_development_action": "ENTER_ZONE"})
        self.assertIn("ACTION_SPEC_ADJUDICATION_REQUIRED", result["reasons"])
        for action in (None, [], "NOT_OBSERVABLE"):
            self.assertIn("INDEPENDENT_ACTION_LABEL_REQUIRED", self.assess({**self.row, "independent_development_action": action})["reasons"])

    def test_unobservable_not_automatically_resolved(self):
        self.assertIn("PRIOR_UNOBSERVABLE_NOT_RESOLVED", self.assess({**self.row, "prior_observation": "NOT_OBSERVABLE"})["reasons"])

    def test_synthetic_nominal_label_still_not_main_admission(self):
        row = {**self.row, "event_predicates": {p: {"truth": "FALSE", "evidence_valid": True} for p in ("ped", "road")},
               "independent_development_action": "ENTER_ZONE"}
        result = self.assess(row, permitted_actions=["ENTER_ZONE", "DEFER_ENTRY"])
        self.assertTrue(result["nominal_entry_label_available"])
        self.assertFalse(result["main_study_admissible"])
        self.assertFalse(result["learning_export_allowed"])

    def test_source_only_inputs_have_no_inferred_observations(self):
        row = next(r for r in entry.r.load(entry.PRIOR / "candidate_readiness.json")["records"] if r["review_index"] is None)
        structured = {"cascade_structured_link_audit": {"active_source_targets": []}}
        prepared = entry.source_only_row(row, structured)
        self.assertTrue(all(v is None for v in prepared["observation"].values()))
        self.assertIsNone(prepared["review_index"])
        self.assertIsNone(prepared["evidence_refs"]["observation"])
        self.assertEqual(prepared["coc"]["text"], row["original_coc"])

    def test_real_run_denominator_and_no_training(self):
        rows = entry.r.load(RUN / "candidate_readiness.json")["records"]
        result = entry.r.load(RUN / "RESULT.json")
        self.assertEqual(len(entry.audit.index_unique(rows)), 32)
        self.assertEqual((result["conditional_development_admitted"], result["pending_count"], result["currently_unusable_count"]), (1, 30, 1))
        for key in ("main_training_admitted", "nominal_entry_label_count", "fresh_test_candidates", "training_exports", "new_human_answers_inferred", "optimizer_steps", "full_source_verified_count"):
            self.assertEqual(result[key], 0, key)
        self.assertTrue(all(r["exact_event_source_audit"] and not r["learning_export_allowed"] for r in rows))
        admitted = next(r for r in rows if r["status"] == "CONDITIONAL_DEVELOPMENT_ADMITTED")
        self.assertEqual(admitted["review_index"], 18)
        self.assertEqual(admitted["event_predicates"], self.row["event_predicates"])
        self.assertEqual(sum(r["prior_observation"] is None for r in rows), 13)
        self.assertEqual(next(r for r in rows if r["review_index"] == 47)["status"], "CURRENTLY_UNUSABLE")

    def test_real_bindings_preserve_nineteen_old_records(self):
        old = entry.audit.index_unique(entry.r.load(entry.audit.source.BINDING / "event_source_bindings.json")["records"])
        current = entry.audit.index_unique(entry.r.load(RUN / "event_source_bindings.json")["records"])
        self.assertEqual(len(old), 19)
        for key, value in old.items():
            self.assertEqual(current[key], value)
        added = [value for key, value in current.items() if key not in old]
        self.assertEqual(len(added), 13)
        self.assertTrue(all(r["observation_status"] == "NOT_COLLECTED_NO_HUMAN_VALUE_INFERRED" for r in added))

    def test_queue_is_not_answered_or_ready_survey(self):
        queue = entry.r.load(RUN / "human_work_queue.json")
        self.assertTrue(queue["not_a_ready_survey"])
        self.assertEqual(len(queue["records"]), 30)
        self.assertTrue(all(r["answers"] is None and not r["review_packet_ready"] for r in queue["records"]))

    def test_hashes_and_completed_output_protected(self):
        entry.r.revalidate_run(RUN)
        with self.assertRaises(FileExistsError):
            entry.run(RUN)


if __name__ == "__main__":
    unittest.main()
