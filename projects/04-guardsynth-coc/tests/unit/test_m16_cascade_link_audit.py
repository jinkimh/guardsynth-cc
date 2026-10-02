"""CASCADE structured-link source audit contracts for M16."""

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

from guard_synth.m16_cascade_link_audit import (
    apply_cascade_link_audit,
    audit_cascade_event_links,
    public_cascade_link_audit_summary,
)


def _annotation(*, containment: bool = True) -> dict:
    relation = {
        "id": "AgentContainment1",
        "env_id": "Environment1",
        "lane_number": "1",
        "start_timestamp": "0:0.0",
        "end_timestamp": "0:2.0",
    }
    ego = {
        "actions": [{
            "id": "EgoAction1",
            "type": "fst:Yield",
            "because_of": ["AgentAction1"],
            "start_timestamp": "0:0.0",
            "end_timestamp": "0:2.0",
        }],
    }
    agent = {
        "id": "Agent1",
        "type": "Pedestrian (Adult)",
        "visibility_start_timestamp": "0:0.0",
        "visibility_end_timestamp": "0:2.0",
        "actions": [{
            "id": "AgentAction1",
            "action_type": "Cross",
            "start_timestamp": "0:0.0",
            "end_timestamp": "0:2.0",
        }],
    }
    if containment:
        ego["containment"] = [{**relation, "id": "EgoContainment1"}]
        agent["containment"] = [relation]
    return {
        "ego_vehicle": ego,
        "agents": [agent],
        "environments": [{
            "id": "Environment1",
            "type": "oxd:Road",
            "num_lanes": 1,
            "start_timestamp": "0:0.0",
            "end_timestamp": "0:2.0",
        }],
        "traffic_objects": [],
        "traffic_lights": [],
    }


class M16CascadeLinkAuditTest(unittest.TestCase):
    def test_active_causal_target_and_shared_containment_are_source_linked(self) -> None:
        result = audit_cascade_event_links(
            annotation=_annotation(),
            event_timestamp_us=1_000_000,
            scene_slice="PEDESTRIAN_CYCLIST_YIELD",
            annotation_sha256="a" * 64,
        )
        self.assertEqual(
            result["relevant_actor_or_control_state_status"],
            "AVAILABLE_SOURCE_LINKED_SET",
        )
        self.assertEqual(
            result["target_zone_or_lane_association_status"],
            "AVAILABLE_SOURCE_LINKED_CONTAINMENT_SET",
        )
        self.assertEqual(result["active_source_target_count"], 1)
        self.assertEqual(result["shared_lane_or_zone_target_count"], 1)

    def test_relation_does_not_invent_missing_containment(self) -> None:
        result = audit_cascade_event_links(
            annotation=_annotation(containment=False),
            event_timestamp_us=1_000_000,
            scene_slice="PEDESTRIAN_CYCLIST_YIELD",
            annotation_sha256="a" * 64,
        )
        self.assertEqual(
            result["relevant_actor_or_control_state_status"],
            "AVAILABLE_SOURCE_LINKED_SET",
        )
        self.assertEqual(
            result["target_zone_or_lane_association_status"],
            "REVIEW_REQUIRED_SOURCE_GEOMETRY",
        )

    def test_unresolved_source_link_is_conflict(self) -> None:
        annotation = _annotation()
        annotation["ego_vehicle"]["actions"][0]["because_of"] = ["MissingAction1"]
        result = audit_cascade_event_links(
            annotation=annotation,
            event_timestamp_us=1_000_000,
            scene_slice="PEDESTRIAN_CYCLIST_YIELD",
            annotation_sha256="a" * 64,
        )
        self.assertEqual(
            result["relevant_actor_or_control_state_status"],
            "CONFLICT_UNRESOLVED_SOURCE_LINK",
        )
        self.assertEqual(result["unresolved_source_link_count"], 1)

    def test_audit_updates_only_supported_fields(self) -> None:
        digest = "candidate-sha256:" + "b" * 64
        prior = {
            "classified_event_count": 1,
            "records": [{
                "candidate_digest": digest,
                "field_status": {
                    "relevant_actor_or_control_state": "REVIEW_REQUIRED_SOURCE_ASSOCIATION",
                    "target_zone_or_lane_association": "REVIEW_REQUIRED_SOURCE_GEOMETRY",
                    "conflict_stop_or_following_geometry": "REVIEW_REQUIRED_SOURCE_GEOMETRY",
                    "applicable_rule_scope": "REVIEW_REQUIRED_JURISDICTION_MATCHED_AUTHORITY",
                },
                "source_complete": False,
                "eligible": False,
            }],
            "remaining_field_event_counts": {
                "relevant_actor_or_control_state": 1,
                "target_zone_or_lane_association": 1,
                "conflict_stop_or_following_geometry": 1,
                "applicable_rule_scope": 1,
                "outcome_lifecycle_witness": 1,
            },
        }
        linked = audit_cascade_event_links(
            annotation=_annotation(),
            event_timestamp_us=1_000_000,
            scene_slice="PEDESTRIAN_CYCLIST_YIELD",
            annotation_sha256="a" * 64,
        )
        result = apply_cascade_link_audit(prior, {digest: linked})
        self.assertEqual(result["relevant_actor_or_control_state_closed_count"], 1)
        self.assertEqual(result["target_zone_or_lane_association_closed_count"], 1)
        self.assertEqual(result["remaining_field_event_counts"]["relevant_actor_or_control_state"], 0)
        self.assertEqual(result["remaining_field_event_counts"]["target_zone_or_lane_association"], 0)
        self.assertEqual(result["remaining_field_event_counts"]["conflict_stop_or_following_geometry"], 1)
        self.assertFalse(result["records"][0]["source_complete"])

    def test_public_summary_excludes_records(self) -> None:
        public = public_cascade_link_audit_summary({
            "records": [{"candidate_digest": "candidate-sha256:" + "c" * 64}],
            "classified_event_count": 1,
        })
        self.assertNotIn("records", public)
        self.assertNotIn("candidate-sha256", str(public))


if __name__ == "__main__":
    unittest.main()
