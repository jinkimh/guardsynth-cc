"""Fail-closed post-review source-closure audit contracts for M16."""

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

from guard_synth.m16_post_review_source_closure import (
    audit_ncore_offline_variant_rule,
    build_post_review_source_closure,
    public_post_review_source_closure_summary,
)


def _precheck_record(digest: str, *, review_ready: bool = True) -> dict:
    return {
        "candidate_digest": digest,
        "cohort_role": "PRIMARY",
        "source_queue_artifact": "ASSOCIATION_REVIEW_QUEUE.json",
        "source_queue_record_index": 0,
        "slice": "FOLLOWING_CUT_IN",
        "country": "United States",
        "association_precheck_status": (
            "REVIEWABLE_ACTOR_ASSOCIATION_LANE_MISSING"
            if review_ready
            else "INSUFFICIENT_SOURCE_GEOMETRY_FOR_ASSOCIATION"
        ),
        "human_review_packet_ready": review_ready,
        "geometry_source_required": True,
    }


def _review_record(digest: str) -> dict:
    return {
        "candidate_digest": digest,
        "review_index": 1,
        "slice": "FOLLOWING_CUT_IN",
        "image_sha256": "f" * 64,
        "reviewer_id": "reviewer",
        "visual_association_observation": "CLEAR_VISIBLE",
        "visual_temporal_observation": "HAZARD_VISIBLE",
        "notes": "",
        "image_bytes_included": False,
    }


class M16PostReviewSourceClosureTest(unittest.TestCase):
    def test_official_ncore_source_closes_variant_rule_only(self) -> None:
        source = '''
        # The non-offline (raw) variants of these features are currently not supported
        REQUIRED_OFFLINE_FEATURES: list[str] = [
            "egomotion", "sensor_extrinsics", "camera_intrinsics", "lidar_intrinsics"
        ]
        def _prefer_offline_feature(self, base_name: str) -> str:
            offline = f"{base_name}.offline"
            if offline in self._feature_names:
                return offline
            return base_name
        '''
        result = audit_ncore_offline_variant_rule(
            source,
            commit_sha="a" * 40,
            source_sha256="b" * 64,
            source_url="https://github.com/NVIDIA/ncore/blob/" + "a" * 40 + "/data_provider.py",
        )
        self.assertEqual(result["decision"], "OFFLINE_VARIANT_RULE_SOURCE_LINKED")
        self.assertEqual(result["selected_variant"], "offline")
        self.assertFalse(result["coordinate_transform_verified"])

    def test_rule_rejects_unpinned_or_incomplete_source(self) -> None:
        with self.assertRaisesRegex(ValueError, "PINNED_OFFICIAL_NCORE_SOURCE_REQUIRED"):
            audit_ncore_offline_variant_rule(
                "REQUIRED_OFFLINE_FEATURES = []",
                commit_sha="main",
                source_sha256="b" * 64,
                source_url="https://github.com/NVIDIA/ncore/blob/main/data_provider.py",
            )

    def test_completed_observation_does_not_upgrade_source_fields(self) -> None:
        reviewed = "candidate-sha256:" + "a" * 64
        source_first = "candidate-sha256:" + "b" * 64
        result = build_post_review_source_closure(
            precheck={
                "classified_event_count": 2,
                "human_review_packet_count": 1,
                "records": [
                    _precheck_record(reviewed),
                    _precheck_record(source_first, review_ready=False),
                ],
            },
            review_export={"records": [_review_record(reviewed)]},
            review_summary={
                "status": "HUMAN_VIDEO_OBSERVATION_COMPLETE",
                "review_record_count": 1,
                "human_review_completed_count": 1,
                "packet_hash_match": True,
                "candidate_order_match": True,
                "image_hash_match": True,
                "json_csv_match": True,
            },
            variant_rule={
                "decision": "OFFLINE_VARIANT_RULE_SOURCE_LINKED",
                "selected_variant": "offline",
            },
            evidence_counts={
                "temporal_closure": 2,
                "calibration_5_of_5": 2,
                "recorded_rig_binding": 2,
            },
        )
        self.assertEqual(result["classified_event_count"], 2)
        self.assertEqual(result["human_observation_completed_count"], 1)
        self.assertEqual(result["calibration_variant_selection_closed_count"], 2)
        self.assertEqual(result["verified_coordinate_transform_count"], 0)
        self.assertEqual(result["source_complete_8_of_8_count"], 0)
        self.assertEqual(result["newly_eligible_scene_count"], 0)
        self.assertEqual(
            result["records"][0]["association_source_status"],
            "SOURCE_GEOMETRY_REQUIRED_AFTER_CLEAR_VISUAL_OBSERVATION",
        )
        self.assertEqual(
            result["records"][1]["human_observation_status"],
            "NOT_REQUESTED_SOURCE_GEOMETRY_FIRST",
        )
        self.assertTrue(all(not item["source_complete"] for item in result["records"]))

    def test_missing_or_extra_review_record_is_rejected(self) -> None:
        digest = "candidate-sha256:" + "a" * 64
        with self.assertRaisesRegex(ValueError, "HUMAN_REVIEW_CANDIDATE_SET_MISMATCH"):
            build_post_review_source_closure(
                precheck={
                    "classified_event_count": 1,
                    "human_review_packet_count": 1,
                    "records": [_precheck_record(digest)],
                },
                review_export={"records": []},
                review_summary={
                    "status": "HUMAN_VIDEO_OBSERVATION_COMPLETE",
                    "review_record_count": 0,
                    "human_review_completed_count": 0,
                    "packet_hash_match": True,
                    "candidate_order_match": True,
                    "image_hash_match": True,
                    "json_csv_match": True,
                },
                variant_rule={
                    "decision": "OFFLINE_VARIANT_RULE_SOURCE_LINKED",
                    "selected_variant": "offline",
                },
                evidence_counts={
                    "temporal_closure": 1,
                    "calibration_5_of_5": 1,
                    "recorded_rig_binding": 1,
                },
            )

    def test_public_summary_contains_no_candidate_or_reviewer_identifier(self) -> None:
        digest = "candidate-sha256:" + "a" * 64
        result = build_post_review_source_closure(
            precheck={
                "classified_event_count": 1,
                "human_review_packet_count": 1,
                "records": [_precheck_record(digest)],
            },
            review_export={"records": [_review_record(digest)]},
            review_summary={
                "status": "HUMAN_VIDEO_OBSERVATION_COMPLETE",
                "review_record_count": 1,
                "human_review_completed_count": 1,
                "packet_hash_match": True,
                "candidate_order_match": True,
                "image_hash_match": True,
                "json_csv_match": True,
            },
            variant_rule={
                "decision": "OFFLINE_VARIANT_RULE_SOURCE_LINKED",
                "selected_variant": "offline",
            },
            evidence_counts={
                "temporal_closure": 1,
                "calibration_5_of_5": 1,
                "recorded_rig_binding": 1,
            },
        )
        public = public_post_review_source_closure_summary(result)
        self.assertNotIn("records", public)
        self.assertNotIn("candidate-sha256", str(public))
        self.assertNotIn("reviewer", str(public).lower())


if __name__ == "__main__":
    unittest.main()
