"""Development source acceptance is distinct from completion and independent gold."""

from copy import deepcopy
from pathlib import Path
import sys
import unittest

ROOT = next(p for p in Path(__file__).resolve().parents if (p / "PROJECT_REGISTRY.json").is_file())
sys.path.insert(0, str(ROOT / "projects/04-guardsynth-coc/src"))
from guard_synth.source_acceptance import VERSION, validate_review, polygon


def fixture():
    return {"review_version": VERSION, "packet_sha256": "a"*64, "candidate_digest": "synthetic:candidate",
        "event_timestamp_us": 100, "reviewer_id": "SYNTHETIC_TEST_NOT_HUMAN", "reviewed_at": "2026-09-08T00:00:00Z",
        "target_identity": "CONFIRMED_AGENT3", "target_point": [.4,.5], "zone_status": "CONFIRMED",
        "zone_polygon": [[.1,.1],[.8,.1],[.8,.8],[.1,.8]], "road_context": "CONFIRMED",
        "ped_truth": "TRUE", "road_truth": "FALSE", "ped_reason": "synthetic observation", "road_reason": "synthetic clearance"}


class SourceAcceptanceTest(unittest.TestCase):
    def check(self, r):
        return validate_review(r, {"candidate_digest": "synthetic:candidate", "event_timestamp_us": 100}, "a"*64)

    def test_review_acceptance_never_exports_or_becomes_gold(self):
        result = self.check(fixture())
        self.assertTrue(result["source_accepted_for_development"])
        self.assertFalse(result["learning_export_allowed"])
        self.assertIsNone(result["independent_action_gold"])
        self.assertEqual(result["independent_cnl_audit"], "PENDING")

    def test_unknown_conflict_and_unbound_inputs_remain_invalid(self):
        for field,value,oid in (("ped_truth","UNKNOWN","ped"),("road_truth","CONFLICT","road"),
            ("target_identity","UNCERTAIN","ped"),("zone_status","UNCERTAIN","ped"),("road_context","UNCERTAIN","road")):
            r=fixture();r[field]=value
            result=self.check(r)
            self.assertTrue(result["review_completed"])
            self.assertFalse(result["source_accepted_for_development"])
            self.assertFalse(result["event_predicates"][oid]["evidence_valid"])

    def test_packet_tampering_rejected(self):
        for field,value in (("packet_sha256","b"*64),("event_timestamp_us",101),("candidate_digest","other"),("review_version","other")):
            r=fixture();r[field]=value
            with self.assertRaises(ValueError):self.check(r)

    def test_bad_fields_and_missing_reasons_rejected(self):
        for field,value in (("reviewer_id",""),("ped_reason"," "),("road_truth","CLEAR"),("reviewed_at","2026-09-08"),
                            ("zone_polygon",None),("target_point",[True,.3]),("target_point",[float('nan'),.5])):
            r=fixture();r[field]=value
            with self.assertRaises(ValueError):self.check(r)
        r=fixture();r["action_gold"]="ENTER_ZONE"
        with self.assertRaises(ValueError):self.check(r)

    def test_bad_polygons_rejected(self):
        for p in ([], [[0,0],[1,1]], [[0,0],[.5,.5],[1,1]], [[0,0],[1,0],[0,1],[1,1]],
                  [[0,0],[1,0],[1,1],[.5,0],[0,1]], [[0,0],[1,0],[1,1],[0,0]], [[0,0],[2,0],[0,1]]):
            with self.subTest(p=p),self.assertRaises(ValueError):polygon(p)

    def test_unobservable_submission_can_omit_geometry(self):
        r=fixture();r.update(target_identity="UNCERTAIN",target_point=None,zone_status="UNCERTAIN",zone_polygon=[],
                             road_context="UNCERTAIN",ped_truth="UNKNOWN",road_truth="UNKNOWN")
        result=self.check(r)
        self.assertTrue(result["review_completed"])
        self.assertFalse(result["source_accepted_for_development"])

    def test_confirmed_geometry_requires_coordinates(self):
        for field,value in (("target_point",None),("zone_polygon",[])):
            r=fixture();r[field]=value
            with self.assertRaises(ValueError):self.check(r)


if __name__ == "__main__":unittest.main()
