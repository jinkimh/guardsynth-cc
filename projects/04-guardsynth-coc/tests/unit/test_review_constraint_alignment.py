"""Window-level human review must never become fabricated event/metric gold."""

from copy import deepcopy
import hashlib
from pathlib import Path
import sys
import unittest

ROOT = next(p for p in Path(__file__).resolve().parents if (p / "PROJECT_REGISTRY.json").is_file())
sys.path.insert(0, str(ROOT / "projects/04-guardsynth-coc/src"))
from guard_synth.review_constraint_alignment import FAMILY, align_reviewed_scene, index_records


def inputs(state="HAZARD_VISIBLE", coc="Yield to the pedestrian crossing the road."):
    common = dict(candidate_digest="candidate:test", slice=FAMILY, event_timestamp_us=100,
                  source_video_sha256="video-hash")
    return dict(
        scene={**common, "group_id": "clip1", "upstream_split": "train", "coc_sha256": hashlib.sha256(coc.encode()).hexdigest()},
        coc=coc,
        observation={**common, "review_index": 1, "visual_association_observation": "CLEAR_VISIBLE",
                     "visual_temporal_observation": state, "notes": "", "image_sha256": "image-hash"},
        geometry={**common, "machine_geometry_assessment": "ACCEPTABLE_VISIBLE_CANDIDATE",
                  "geometry_disposition": "CONFIRM_MACHINE_CANDIDATE", "normalized_pixel_polygons": {}},
        structured={**common, "cascade_structured_link_audit": {"event_timestamp_us": 100, "active_source_targets": [
            {"parent_entity_id": "Agent1", "source_category": "ACTOR"}]}},
        authority={**common, "authority_status": "AVAILABLE_TREATY_NORMATIVE_BASELINE", "rule_strength": "GENERAL_DUE_CARE_FALLBACK",
                   "article_refs": ["source:article"], "rule_summary": "General care only", "legal_compliance_claim": "NOT_PERMITTED"},
        evidence_refs={name: "sha256:test#" + name for name in ("coc", "observation", "geometry", "structured", "authority")},
    )


class ReviewConstraintAlignmentTest(unittest.TestCase):
    def test_hazard_observation_reused_but_not_t0_truth(self):
        row = align_reviewed_scene(**inputs())
        self.assertTrue(row["observation_reused"])
        self.assertFalse(row["repeat_existing_survey_requested"])
        self.assertEqual(row["draft"]["event_activation_truth"], "UNKNOWN")
        self.assertIsNone(row["draft"]["target_entity_id"])
        self.assertIsNone(row["draft"]["numeric_parameters"])
        self.assertIsNone(row["draft"]["selected_action"])

    def test_no_visible_hazard_does_not_grant_proceed_or_call_coc_wrong(self):
        row = align_reviewed_scene(**inputs("NO_HAZARD_VISIBLE", "Decelerate for pedestrians on the sidewalk."))
        self.assertEqual(row["draft"]["kind"], "AVOID_UNSUPPORTED_ACTIVATION")
        self.assertIsNone(row["draft"]["selected_action"])
        self.assertEqual(row["comparison_status"], "OBSERVATION_REUSE_NOT_INDEPENDENT_ACCURACY_EVALUATION")

    def test_transition_note_is_preserved_not_invented_clear_frame_count(self):
        args = inputs("STATE_TRANSITION_VISIBLE")
        args["observation"]["notes"] = "보행자가 도로에서 벗어나고 있음"
        row = align_reviewed_scene(**args)
        self.assertEqual(row["observation"]["notes"], args["observation"]["notes"])
        self.assertEqual(row["field_correspondence"]["lifecycle.release"], "TRANSITION_NOTE_ONLY")
        self.assertNotIn("release_clear_frames", row["draft"])

    def test_transition_without_note_rejected(self):
        with self.assertRaisesRegex(ValueError, "transition note"):
            align_reviewed_scene(**inputs("STATE_TRANSITION_VISIBLE"))

    def test_unobservable_remains_abstention(self):
        args = inputs("NOT_OBSERVABLE")
        args["observation"]["visual_association_observation"] = "NOT_OBSERVABLE"
        row = align_reviewed_scene(**args)
        self.assertIsNone(row["draft"])
        self.assertFalse(row["learning_export_allowed"])

    def test_coc_worker_context_is_claimed_not_promoted_to_observation(self):
        row = align_reviewed_scene(**inputs(coc="Steer right following worker guidance and traffic cones."))
        self.assertTrue(row["coc"]["mixed_work_or_control_context"])
        for match in row["coc"]["context_matches"]:
            start, end = match["span"]
            self.assertEqual(row["coc"]["text"][start:end], match["matched_text"])
            self.assertEqual(match["epistemic_kind"], "CLAIMED")
        self.assertIsNone(row["draft"]["selected_action"])

    def test_polygons_count_as_submitted_without_metric_promotion(self):
        args = inputs()
        args["geometry"]["normalized_pixel_polygons"] = {"ego_lane_zone": [[[0., 0.], [1., 0.], [1., 1.]]]}
        row = align_reviewed_scene(**args)
        self.assertTrue(row["geometry"]["polygon_submission_completed"])
        self.assertFalse(row["geometry"]["metric_geometry_inferred"])

    def test_inputs_not_mutated(self):
        args = inputs(); original = deepcopy(args)
        align_reviewed_scene(**args)
        self.assertEqual(args, original)

    def test_no_fake_eblc_sat_or_cnl(self):
        row = align_reviewed_scene(**inputs())
        self.assertFalse(row["eblc_preflight"]["program_generated"])
        self.assertEqual(row["eblc_preflight"]["sat_status"], "NOT_RUN")
        self.assertEqual(row["eblc_preflight"]["cnl_status"], "NOT_RENDERED_FROM_EBLC")

    def test_mismatched_source_id_rejected(self):
        args = inputs(); args["structured"]["candidate_digest"] = "another"
        with self.assertRaisesRegex(ValueError, "cross-scene"):
            align_reviewed_scene(**args)

    def test_timestamp_mismatch_rejected(self):
        args = inputs(); args["authority"]["event_timestamp_us"] += 1
        with self.assertRaisesRegex(ValueError, "timestamp"):
            align_reviewed_scene(**args)

    def test_video_mismatch_rejected(self):
        args = inputs(); args["authority"]["source_video_sha256"] = "another-video"
        with self.assertRaisesRegex(ValueError, "source video"):
            align_reviewed_scene(**args)

    def test_changed_coc_rejected(self):
        args = inputs(); args["coc"] = "different"
        with self.assertRaisesRegex(ValueError, "CoC content"):
            align_reviewed_scene(**args)

    def test_unknown_review_value_rejected(self):
        with self.assertRaisesRegex(ValueError, "unsupported observation"):
            align_reviewed_scene(**inputs("MADE_UP"))

    def test_duplicate_candidate_rejected(self):
        with self.assertRaisesRegex(ValueError, "duplicate"):
            index_records([{"candidate_digest": "a"}, {"candidate_digest": "a"}])


if __name__ == "__main__":
    unittest.main()
