"""Declared independent review never substitutes for source or learning gates."""

from pathlib import Path
import sys
import unittest

ROOT=next(p for p in Path(__file__).resolve().parents if (p/"PROJECT_REGISTRY.json").is_file())
sys.path.insert(0,str(ROOT/"projects/04-guardsynth-coc/src"))
from guard_synth.independent_development_review import VERSION,validate_independent_review


class IndependentReviewTest(unittest.TestCase):
    def fixture(self,kind="ACTION"):
        packet={"kind":kind,"clause_ids":["a","b"]}
        response={"review_version":VERSION,"packet_sha256":"a"*64,"kind":kind,"reviewer_id":"SYNTHETIC_OTHER",
            "reviewed_at":"2026-09-08T00:00:00Z","independence":"INDEPENDENT",
            "answers":{"action":"DEFER_ENTRY"} if kind=="ACTION" else {"a":"MATCH","b":"MATCH"},"reason":"synthetic fixture only"}
        return packet,response

    def test_declared_independent_development_not_test_or_export(self):
        p,r=self.fixture();v=validate_independent_review(r,p,"a"*64)
        self.assertTrue(v["judgement_available"]);self.assertFalse(v["main_test_eligibility"]);self.assertFalse(v["learning_export_allowed"])

    def test_known_exposure_cannot_be_overridden_by_checkbox(self):
        p,r=self.fixture();r["reviewer_id"]="  jin  hyun kim "
        v=validate_independent_review(r,p,"a"*64,known_exposed_reviewer_ids=["Jin Hyun Kim"])
        self.assertTrue(v["known_exposure_conflict"]);self.assertFalse(v["independence_eligible"])

    def test_uncertain_or_exposed_review_is_recorded_not_independent(self):
        for choice in ("UNCERTAIN","EXPOSED_OR_INVOLVED"):
            p,r=self.fixture();r["independence"]=choice;v=validate_independent_review(r,p,"a"*64)
            self.assertTrue(v["review_completed"]);self.assertFalse(v["judgement_available"])

    def test_unjudgeable_not_a_positive_gold_label(self):
        p,r=self.fixture();r["answers"]["action"]="UNJUDGEABLE"
        self.assertFalse(validate_independent_review(r,p,"a"*64)["judgement_available"])

    def test_cnl_mismatch_is_preserved_not_turned_into_match(self):
        p,r=self.fixture("CNL");r["answers"]["b"]="MISMATCH";v=validate_independent_review(r,p,"a"*64)
        self.assertTrue(v["judgement_available"]);self.assertEqual(v["answers"]["b"],"MISMATCH")

    def test_wrong_packet_incomplete_or_invalid_answers_rejected(self):
        for field,value in (("packet_sha256","bad"),("reason",""),("independence","AUTO"),("reviewed_at","2026-09-08"),
            ("answers",{"action":"SAT"}),("answers",{})):
            p,r=self.fixture();r[field]=value
            with self.assertRaises(ValueError):validate_independent_review(r,p,"a"*64)


if __name__=="__main__":unittest.main()
