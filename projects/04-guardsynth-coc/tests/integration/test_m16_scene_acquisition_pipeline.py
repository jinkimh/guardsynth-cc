"""Integration contract for the restricted M16 local-data acquisition audit."""

from __future__ import annotations

import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest


ROOT = next(
    parent
    for parent in Path(__file__).resolve().parents
    if (parent / "PROJECT_REGISTRY.json").is_file()
)
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

class M16SceneAcquisitionPipelineTest(unittest.TestCase):
    def test_local_audit_reindexes_events_and_reaudits_prior_four(self) -> None:
        from cli.project_paths import project_root

        self.assertEqual(project_root(__file__), ROOT)
        pipeline_dir = ROOT / "projects/04-guardsynth-coc/pipelines/cli/m16_scene_acquisition"
        if str(pipeline_dir) not in sys.path:
            sys.path.insert(0, str(pipeline_dir))
        from run import execute

        with TemporaryDirectory() as directory:
            restricted = Path(directory) / "restricted"
            public = Path(directory) / "public"
            result = execute(
                restricted_output_dir=restricted,
                public_output_dir=public,
                run_id="m16-source-acquisition-test-v1",
                test_results=[],
            )
            self.assertEqual(result["status"], "PARTIAL_DATA_ACQUISITION")
            self.assertEqual(result["candidate_source_record_count"], 33)
            self.assertEqual(result["source_alias_deduplicated_count"], 10)
            self.assertEqual(result["distinct_candidate_count"], 23)
            self.assertEqual(result["prior_eligible_reaudited_count"], 4)
            self.assertEqual(result["source_complete_8_of_8_count"], 3)
            self.assertEqual(result["eligible_scene_count"], 1)
            self.assertEqual(result["newly_eligible_count"], 0)
            self.assertEqual(result["licensed_candidate_event_count"], 135)
            self.assertEqual(result["sensor_eligible_candidate_clip_count"], 106)
            self.assertEqual(result["locally_materialized_additional_candidate_count"], 0)
            self.assertEqual(
                result["acquisition_session_status"],
                "ATTRITION_RESERVE_MATERIALIZED_SOURCE_REVIEW_REQUIRED",
            )
            self.assertEqual(result["annotation_classified_event_count"], 98)
            self.assertEqual(result["annotation_unsupported_event_count"], 37)
            self.assertEqual(result["sensor_shortlist_unique_clip_count"], 59)
            self.assertEqual(result["sensor_shortlist_unique_chunk_count"], 57)
            self.assertEqual(result["estimated_sensor_package_count"], 228)
            self.assertEqual(result["classified_unique_clip_count"], 81)
            self.assertEqual(result["attrition_reserve_event_count"], 39)
            self.assertEqual(result["attrition_reserve_new_clip_count"], 22)
            self.assertEqual(result["attrition_reserve_reused_clip_event_count"], 10)
            self.assertEqual(
                result["attrition_reserve_new_clip_secondary_event_count"], 7
            )
            self.assertEqual(result["materialized_sensor_candidate_count"], 59)
            self.assertEqual(result["materialized_sensor_member_count"], 354)
            self.assertEqual(result["sensor_temporal_closure_candidate_count"], 59)
            self.assertEqual(result["sensor_source_complete_8_of_8_candidate_count"], 0)
            self.assertEqual(result["sensor_final_outcome_assigned_count"], 0)
            self.assertTrue(result["raw_video_copied"])
            self.assertEqual(result["calibration_candidate_count"], 59)
            self.assertEqual(result["calibration_candidate_feature_count"], 295)
            self.assertEqual(result["recorded_rig_binding_available_count"], 59)
            self.assertEqual(result["verified_coordinate_transform_count"], 0)
            self.assertEqual(result["calibration_variant_review_count"], 59)
            self.assertEqual(result["reserve_materialized_sensor_clip_count"], 22)
            self.assertEqual(result["reserve_materialized_sensor_member_count"], 132)
            self.assertEqual(
                result["reserve_sensor_temporal_closure_candidate_count"], 22
            )
            self.assertEqual(result["reserve_calibration_candidate_count"], 22)
            self.assertEqual(result["reserve_calibration_feature_count"], 110)
            self.assertEqual(result["total_materialized_sensor_unique_clip_count"], 81)
            self.assertEqual(result["total_materialized_sensor_member_count"], 486)
            self.assertEqual(result["total_materialized_sensor_bytes"], 1_448_583_496)
            self.assertEqual(
                result["total_materialized_calibration_feature_count"], 405
            )
            self.assertEqual(result["total_materialized_calibration_bytes"], 3_337_630)
            self.assertEqual(result["classified_event_temporal_closure_count"], 98)
            self.assertEqual(result["classified_event_calibration_closure_count"], 98)
            self.assertEqual(
                result["classified_event_recorded_rig_binding_count"], 98
            )
            self.assertEqual(result["classified_event_verified_transform_count"], 0)
            self.assertEqual(result["classified_event_source_complete_8_of_8_count"], 0)
            self.assertEqual(result["classified_event_final_outcome_assigned_count"], 0)
            self.assertEqual(result["source_review_precheck_status"], "COMPLETE")
            self.assertEqual(result["source_review_human_packet_count"], 60)
            self.assertEqual(
                result["source_review_geometry_source_required_count"], 98
            )
            self.assertEqual(
                result["calibration_variant_source_decision"],
                "NO_GENERAL_SELECTION_RULE_FAIL_CLOSED",
            )
            self.assertFalse(result["annotation_start_allowed"])
            scope = json.loads(
                (restricted / "SCOPE_COMPATIBILITY_AUDIT.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(scope["jurisdiction_source_compatible_count"], 2)
            self.assertEqual(
                scope["excluded_jurisdiction_or_odd_mismatch_count"], 0
            )
            self.assertEqual(
                scope["review_required_jurisdiction_evidence_count"], 2
            )
            self.assertEqual(
                sum(
                    record["cross_field_temporal_consistency"] is False
                    for record in scope["prior_records"]
                ),
                1,
            )
            expected = {
                "RESULT.json",
                "RUN_MANIFEST.json",
                "REPORT_KO.md",
                "SCENE_ELIGIBILITY_MANIFEST.json",
                "SCENE_SOURCE_CLOSURE.json",
                "SLOT_BINDING_MANIFEST.json",
                "SCOPE_COMPATIBILITY_AUDIT.json",
                "ACQUISITION_GAP_MANIFEST.json",
                "LICENSED_CANDIDATE_SCREEN.json",
                "ANNOTATION_CANDIDATE_SCREEN.json",
                "SENSOR_MATERIALIZATION_SHORTLIST.json",
                "ATTRITION_RESERVE_COHORT.json",
                "SENSOR_RESERVE_SHORTLIST.json",
                "SENSOR_MATERIALIZATION_AUDIT.json",
                "SENSOR_EVIDENCE_AUDIT.json",
                "CALIBRATION_MATERIALIZATION_AUDIT.json",
                "CALIBRATION_ASSOCIATION_AUDIT.json",
                "ASSOCIATION_REVIEW_QUEUE.json",
                "RESERVE_SENSOR_MATERIALIZATION_AUDIT.json",
                "RESERVE_SENSOR_EVIDENCE_AUDIT.json",
                "RESERVE_CALIBRATION_MATERIALIZATION_AUDIT.json",
                "RESERVE_CALIBRATION_ASSOCIATION_AUDIT.json",
                "RESERVE_ASSOCIATION_REVIEW_QUEUE.json",
                "ATTRITION_RESERVE_EVIDENCE_AUDIT.json",
                "ATTRITION_RESERVE_REVIEW_QUEUE.json",
                "CALIBRATION_VARIANT_SOURCE_AUDIT.json",
                "SOURCE_REVIEW_PRECHECK.json",
                "HUMAN_SOURCE_REVIEW_PACKET.json",
                "PILOT_PREFLIGHT.json",
                "TRANSLATION_RESULTS.json",
            }
            self.assertTrue(expected.issubset({path.name for path in restricted.iterdir()}))
            public_text = "\n".join(
                path.read_text(encoding="utf-8")
                for path in public.iterdir()
                if path.suffix in {".json", ".md"}
            )
            self.assertNotIn("/home/", public_text)
            self.assertNotIn("file://", public_text)
            self.assertNotIn("clip_id", public_text.lower())
            public_result = json.loads((public / "RESULT.json").read_text(encoding="utf-8"))
            self.assertEqual(public_result["eligible_scene_count"], 1)
            public_screen = json.loads(
                (public / "ANNOTATION_CANDIDATE_SCREEN.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertNotIn("records", public_screen)
            self.assertEqual(public_screen["classified_event_count"], 98)
            self.assertEqual(
                public_screen["sensor_download_status"],
                "MATERIALIZED_SELECTED_MEMBERS_ONLY",
            )
            public_reserve = json.loads(
                (public / "ATTRITION_RESERVE_COHORT.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(public_reserve["reserve_event_count"], 39)
            self.assertEqual(public_reserve["new_clip_materialization_count"], 22)
            self.assertNotIn("records", public_reserve)
            self.assertNotIn("materialization_records", public_reserve)
            public_reserve_audit = json.loads(
                (public / "ATTRITION_RESERVE_EVIDENCE_AUDIT.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(
                public_reserve_audit["audited_reserve_event_count"], 39
            )
            self.assertEqual(public_reserve_audit["temporal_closure_event_count"], 39)
            self.assertNotIn("records", public_reserve_audit)
            public_sensor = json.loads(
                (public / "SENSOR_EVIDENCE_AUDIT.json").read_text(encoding="utf-8")
            )
            self.assertNotIn("records", public_sensor)
            self.assertEqual(public_sensor["temporal_closure_candidate_count"], 59)
            public_calibration = json.loads(
                (public / "CALIBRATION_ASSOCIATION_AUDIT.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertNotIn("records", public_calibration)
            self.assertEqual(public_calibration["calibration_5_of_5_candidate_count"], 59)
            public_precheck = json.loads(
                (public / "SOURCE_REVIEW_PRECHECK.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertNotIn("records", public_precheck)
            self.assertEqual(public_precheck["human_review_packet_count"], 60)
            self.assertEqual(public_precheck["geometry_source_required_count"], 98)
            restricted_packet = json.loads(
                (restricted / "HUMAN_SOURCE_REVIEW_PACKET.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(restricted_packet["record_count"], 60)
            self.assertEqual(
                restricted_packet["review_completion_status"], "NOT_STARTED"
            )


if __name__ == "__main__":
    unittest.main()
