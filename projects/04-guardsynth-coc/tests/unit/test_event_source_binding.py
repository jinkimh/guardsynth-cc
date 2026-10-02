"""Temporal, identity and claim-boundary regressions for source witnesses."""

from copy import deepcopy
from pathlib import Path
import sys
import unittest

ROOT = next(p for p in Path(__file__).resolve().parents if (p / "PROJECT_REGISTRY.json").is_file())
sys.path.insert(0, str(ROOT / "projects/04-guardsynth-coc/src"))
from guard_synth.event_source_binding import bind_event, interval, timestamp_us


class EventBindingTest(unittest.TestCase):
    def setUp(self):
        self.row = dict(candidate_digest="candidate-a", review_index=1, group_id="clip-a", upstream_split="train",
            event_timestamp_us=1_000_000, coc={"text": "Yield", "mixed_work_or_control_context": False},
            observation={"visual_temporal_observation": "HAZARD_VISIBLE"}, evidence_refs={}, structured_target_candidates=[])
        self.payload = dict(video={"clip_id": "clip-a", "duration_s": 3.0}, annotation={
            "ego_vehicle": {"actions": [{"id": "EgoAction1", "type": "fst:Yield", "start_timestamp": "0:0.0",
                "end_timestamp": "0:2.0", "because_of": ["AgentAction1"]}]},
            "agents": [{"id": "Agent1", "type": "Pedestrian (Adult)", "visibility_start_timestamp": "0:0.0",
                "visibility_end_timestamp": "0:2.0", "actions": [{"id": "AgentAction1", "action_type": "oxd:Walk",
                    "start_timestamp": "0:0.0", "end_timestamp": "0:2.0"}],
                "keypoints": [{"timestamp": "1.5", "x": 0.5, "y": 0.5}]}]})

    def bind(self):
        return bind_event(self.row, self.payload, "a" * 64)

    def test_exact_source_target_is_not_hazard_or_action_gold(self):
        r = self.bind()
        self.assertEqual(r["unique_source_linked_person_id"], "Agent1")
        self.assertEqual(r["event_hazard_truth"], "UNKNOWN")
        self.assertIsNone(r["selected_action_gold"])
        self.assertIsNone(r["semantic_conflict_zone"])
        self.assertFalse(r["learning_export_allowed"])
        self.assertEqual(r["sat_status"], "NOT_RUN")
        self.assertIn("/annotation/agents/0/actions/0", r["active_source_targets"][0]["evidence_ref"])

    def test_no_half_second_temporal_widening(self):
        self.payload["annotation"]["agents"][0]["actions"][0]["start_timestamp"] = "1.1"
        self.assertEqual(self.bind()["active_source_targets"], [])

    def test_inactive_parent_invalidates_active_child(self):
        self.payload["annotation"]["agents"][0]["visibility_start_timestamp"] = "1.1"
        self.assertEqual(self.bind()["active_source_targets"], [])

    def test_missing_interval_is_not_active(self):
        del self.payload["annotation"]["agents"][0]["actions"][0]["end_timestamp"]
        self.assertEqual(self.bind()["active_source_targets"], [])

    def test_missing_parent_interval_cannot_be_inferred_from_child(self):
        del self.payload["annotation"]["agents"][0]["visibility_start_timestamp"]
        del self.payload["annotation"]["agents"][0]["visibility_end_timestamp"]
        self.assertEqual(self.bind()["active_source_targets"], [])

    def test_future_keypoint_not_interpolated_or_used(self):
        point = self.bind()["active_actors"][0]["keypoints"][0]
        self.assertEqual(point["offset_us"], 500_000)
        self.assertFalse(point["usable_as_event_input"])
        self.assertFalse(point["used_as_polygon_or_track"])

    def test_future_ego_action_is_not_event_action(self):
        self.payload["annotation"]["ego_vehicle"]["actions"][0]["start_timestamp"] = "1.1"
        r = self.bind()
        self.assertEqual(r["active_ego_actions"], [])
        self.assertFalse(r["future_ego_actions_context_only"][0]["usable_as_event_input"])

    def test_multiple_person_targets_not_arbitrarily_selected(self):
        second = deepcopy(self.payload["annotation"]["agents"][0])
        second["id"] = "Agent2"
        second["actions"][0]["id"] = "AgentAction2"
        self.payload["annotation"]["agents"].append(second)
        self.payload["annotation"]["ego_vehicle"]["actions"][0]["because_of"].append("AgentAction2")
        self.assertIsNone(self.bind()["unique_source_linked_person_id"])

    def test_release_does_not_override_stop_signal(self):
        self.row["observation"]["visual_temporal_observation"] = "STATE_TRANSITION_VISIBLE"
        self.payload["annotation"]["agents"][0]["properties"] = [{"id": "Signal1", "start_timestamp": "0",
            "end_timestamp": "2", "property_type": "Signal", "signaling_details": {"intent": "Stop"}}]
        r = self.bind()
        self.assertTrue(r["release_control_check_required"])
        self.assertIsNone(r["selected_action_gold"])

    def test_duplicate_source_id_rejected(self):
        self.payload["annotation"]["agents"][0]["id"] = "AgentAction1"
        with self.assertRaisesRegex(ValueError, "duplicate source ID"):
            self.bind()

    def test_wrong_clip_rejected(self):
        self.payload["video"]["clip_id"] = "another-clip"
        with self.assertRaisesRegex(ValueError, "clip mismatch"):
            self.bind()

    def test_unresolved_reference_is_preserved(self):
        self.payload["annotation"]["ego_vehicle"]["actions"][0]["because_of"] = ["Missing"]
        self.assertEqual(self.bind()["event_causal_links"][0]["status"], "UNRESOLVED")

    def test_boundary_not_silently_shifted(self):
        r = interval({"start_timestamp": "1", "end_timestamp": "2"}, 1_000_000)
        self.assertTrue(r["contains_event"])
        self.assertTrue(r["event_on_boundary"])

    def test_timestamp_validation(self):
        self.assertEqual(timestamp_us("1:02.125001"), 62_125_001)
        self.assertIsNone(timestamp_us(None))
        for value in ("nan", "-1", "0:60", 1.0, "0.0000001"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                timestamp_us(value)
        with self.assertRaisesRegex(ValueError, "reversed"):
            interval({"start_timestamp": "2", "end_timestamp": "1"}, 1_000_000)

    def test_boolean_event_timestamp_rejected(self):
        self.row["event_timestamp_us"] = True
        with self.assertRaisesRegex(ValueError, "invalid binding input"):
            self.bind()

    def test_signal_outside_parent_interval_not_active(self):
        self.row["observation"]["visual_temporal_observation"] = "STATE_TRANSITION_VISIBLE"
        self.payload["annotation"]["traffic_lights"] = [{"id": "TL1", "visibility_start_timestamp": "0",
            "visibility_end_timestamp": "2", "signal_heads": [{"id": "Head1", "start_timestamp": "1.1",
            "end_timestamp": "2", "state_sequence": [{"id": "Red1", "color": "Red", "start_timestamp": "0", "end_timestamp": "2"}]}]}]
        self.assertFalse(self.bind()["release_control_check_required"])


if __name__ == "__main__":
    unittest.main()
