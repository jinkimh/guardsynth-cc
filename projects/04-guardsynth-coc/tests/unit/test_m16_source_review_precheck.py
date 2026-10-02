"""Fail-closed source-review precheck tests for the M16 classified pool."""

from __future__ import annotations

from pathlib import Path
import sys
import unittest


ROOT = next(
    parent
    for parent in Path(__file__).resolve().parents
    if (parent / "PROJECT_REGISTRY.json").is_file()
)
SRC = ROOT / "projects/04-guardsynth-coc/src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from guard_synth.m16_source_review_precheck import (
    audit_calibration_variant_sources,
    build_human_source_review_packet,
    build_source_review_precheck,
    public_source_review_precheck_summary,
)


def queue_record(digest: str, status: str) -> dict:
    return {
        "candidate_digest": digest,
        "shortlist_slice": "FOLLOWING_CUT_IN",
        "country": "Example Country",
        "association_review_status": status,
        "coordinate_transform_status": (
            "REVIEW_REQUIRED_ONLINE_OFFLINE_VARIANT_SELECTION"
        ),
        "rule_scope_status": "REVIEW_REQUIRED_JURISDICTION_MATCHED_AUTHORITY",
        "outcome_status": "REVIEW_REQUIRED_LIFECYCLE_WITNESS",
        "final_outcome_assigned": False,
    }


class M16SourceReviewPrecheckTest(unittest.TestCase):
    def test_calibration_audit_does_not_invent_a_selection_rule(self) -> None:
        result = audit_calibration_variant_sources([
            {
                "source_id": "dataset-card",
                "official_source": True,
                "offline_optimized_feature_documented": True,
                "general_variant_selection_rule_documented": False,
                "maps_included": False,
            },
            {
                "source_id": "devkit",
                "official_source": True,
                "offline_optimized_feature_documented": False,
                "general_variant_selection_rule_documented": False,
                "offline_calibration_reader_supported": False,
            },
        ])
        self.assertEqual(result["decision"], "NO_GENERAL_SELECTION_RULE_FAIL_CLOSED")
        self.assertEqual(result["auto_closable_transform_count"], 0)
        self.assertTrue(result["open_maps_explicitly_absent"])

    def test_precheck_separates_reviewable_and_source_acquisition_records(self) -> None:
        primary = {
            "records": [
                queue_record("a" * 64, "REVIEWABLE_ACTOR_ASSOCIATION_LANE_MISSING"),
                queue_record("b" * 64, "INSUFFICIENT_SOURCE_GEOMETRY_FOR_ASSOCIATION"),
            ]
        }
        reserve = {
            "records": [
                {
                    **queue_record(
                        "c" * 64,
                        "REVIEWABLE_CONTROL_ASSOCIATION_LANE_MISSING",
                    ),
                    "reserve_slice": "STOP_SIGNALS",
                }
            ]
        }
        audit = {"decision": "NO_GENERAL_SELECTION_RULE_FAIL_CLOSED"}
        result = build_source_review_precheck(primary, reserve, audit)
        self.assertEqual(result["classified_event_count"], 3)
        self.assertEqual(result["human_review_packet_count"], 2)
        self.assertEqual(result["association_source_acquisition_required_count"], 1)
        self.assertEqual(result["coordinate_transform_auto_closable_count"], 0)
        self.assertEqual(result["source_complete_8_of_8_count"], 0)
        self.assertEqual(result["final_outcome_assigned_count"], 0)
        self.assertTrue(all(not item["source_complete"] for item in result["records"]))

    def test_missing_lane_or_zone_still_requires_geometry_source(self) -> None:
        primary = {
            "records": [
                queue_record("a" * 64, "REVIEWABLE_ACTOR_ZONE_ASSOCIATION"),
                queue_record("b" * 64, "REVIEWABLE_ACTOR_ASSOCIATION_ZONE_MISSING"),
            ]
        }
        result = build_source_review_precheck(
            primary,
            {"records": []},
            {"decision": "NO_GENERAL_SELECTION_RULE_FAIL_CLOSED"},
        )
        by_digest = {item["candidate_digest"]: item for item in result["records"]}
        self.assertFalse(by_digest["a" * 64]["geometry_source_required"])
        self.assertTrue(by_digest["b" * 64]["geometry_source_required"])

    def test_duplicate_candidate_is_rejected(self) -> None:
        record = queue_record("a" * 64, "REVIEWABLE_ACTOR_ZONE_ASSOCIATION")
        with self.assertRaisesRegex(ValueError, "DUPLICATE_CANDIDATE_DIGEST"):
            build_source_review_precheck(
                {"records": [record]},
                {"records": [{**record, "reserve_slice": "FOLLOWING_CUT_IN"}]},
                {"decision": "NO_GENERAL_SELECTION_RULE_FAIL_CLOSED"},
            )

    def test_public_summary_contains_no_record_identifiers(self) -> None:
        result = build_source_review_precheck(
            {
                "records": [
                    queue_record("a" * 64, "REVIEWABLE_ACTOR_ZONE_ASSOCIATION")
                ]
            },
            {"records": []},
            {"decision": "NO_GENERAL_SELECTION_RULE_FAIL_CLOSED"},
        )
        public = public_source_review_precheck_summary(result)
        self.assertNotIn("records", public)
        self.assertNotIn("candidate_digest", str(public))
        self.assertEqual(public["human_review_packet_count"], 1)

    def test_human_packet_contains_only_prechecked_reviewable_records(self) -> None:
        result = build_source_review_precheck(
            {
                "records": [
                    queue_record("a" * 64, "REVIEWABLE_ACTOR_ZONE_ASSOCIATION"),
                    queue_record(
                        "b" * 64,
                        "INSUFFICIENT_SOURCE_GEOMETRY_FOR_ASSOCIATION",
                    ),
                ]
            },
            {"records": []},
            {"decision": "NO_GENERAL_SELECTION_RULE_FAIL_CLOSED"},
        )
        packet = build_human_source_review_packet(result)
        self.assertEqual(packet["record_count"], 1)
        self.assertEqual(packet["review_completion_status"], "NOT_STARTED")
        self.assertFalse(packet["records"][0]["human_review_completed"])
        self.assertEqual(
            set(packet["records"][0]["required_review_fields"]),
            {
                "visual_association_observation",
                "visual_temporal_observation",
                "reviewer_id",
                "notes",
            },
        )
        serialized = str(packet["records"][0]["required_review_fields"])
        for curator_field in (
            "evidence_ref",
            "authority",
            "jurisdiction",
            "rule_precondition",
            "rule_exception",
            "source_complete",
            "final_decision",
        ):
            self.assertNotIn(curator_field, serialized)


if __name__ == "__main__":
    unittest.main()
