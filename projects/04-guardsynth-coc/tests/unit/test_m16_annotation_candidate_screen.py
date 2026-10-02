"""TDD contract for fail-closed M16 CASCADE candidate screening."""

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

from guard_synth.m16_annotation_candidate_screen import (
    build_attrition_reserve,
    classify_annotation_candidate,
    deidentified_screen_summary,
    parse_cascade_timestamp_us,
    select_sensor_shortlist,
)


class M16AnnotationCandidateScreenTest(unittest.TestCase):
    def test_timestamp_parser_preserves_subsecond_precision(self) -> None:
        self.assertEqual(parse_cascade_timestamp_us("0:11.4"), 11_400_000)
        self.assertEqual(parse_cascade_timestamp_us("1:02.005"), 62_005_000)
        self.assertIsNone(parse_cascade_timestamp_us("unknown"))

    def test_slice_candidates_are_time_aligned_and_ambiguity_is_preserved(self) -> None:
        annotation = {
            "agents": [
                {
                    "type": "Pedestrian (Adult)",
                    "visibility_start_timestamp": "0:09.0",
                    "visibility_end_timestamp": "0:12.0",
                    "actions": [],
                },
                {
                    "type": "oxd:Car",
                    "visibility_start_timestamp": "0:09.0",
                    "visibility_end_timestamp": "0:12.0",
                    "actions": [
                        {
                            "action_type": "oxd:ChangeLane (right)",
                            "start_timestamp": "0:10.0",
                            "end_timestamp": "0:11.0",
                        }
                    ],
                },
            ],
            "ego_vehicle": {"actions": []},
            "traffic_lights": [],
            "traffic_objects": [],
        }
        result = classify_annotation_candidate(annotation, 10_500_000)
        self.assertEqual(
            result["candidate_slices"],
            ["PEDESTRIAN_CYCLIST_YIELD", "FOLLOWING_CUT_IN"],
        )
        self.assertFalse(result["final_outcome_assigned"])
        self.assertEqual(result["outcome_status"], "REVIEW_REQUIRED_SENSOR_VALIDATION")

    def test_restrictive_signal_or_stop_control_is_a_stop_signal_candidate(self) -> None:
        annotation = {
            "agents": [],
            "ego_vehicle": {"actions": []},
            "traffic_lights": [
                {
                    "visibility_start_timestamp": "0:01.0",
                    "visibility_end_timestamp": "0:08.0",
                    "signal_heads": [
                        {
                            "state_sequence": [
                                {
                                    "color": "Red",
                                    "start_timestamp": "0:03.0",
                                    "end_timestamp": "0:06.0",
                                }
                            ]
                        }
                    ],
                }
            ],
            "traffic_objects": [],
        }
        result = classify_annotation_candidate(annotation, 5_000_000)
        self.assertEqual(result["candidate_slices"], ["STOP_SIGNALS"])

    def test_permissive_signal_is_preserved_for_non_hazard_outcome_review(self) -> None:
        annotation = {
            "agents": [],
            "ego_vehicle": {"actions": []},
            "traffic_lights": [
                {
                    "visibility_start_timestamp": "0:01.0",
                    "visibility_end_timestamp": "0:08.0",
                    "signal_heads": [
                        {
                            "state_sequence": [
                                {
                                    "color": "Green",
                                    "start_timestamp": "0:03.0",
                                    "end_timestamp": "0:06.0",
                                }
                            ]
                        }
                    ],
                }
            ],
            "traffic_objects": [],
        }
        result = classify_annotation_candidate(annotation, 5_000_000)
        self.assertEqual(result["candidate_slices"], ["STOP_SIGNALS"])
        self.assertEqual(result["outcome_status"], "REVIEW_REQUIRED_SENSOR_VALIDATION")

    def test_out_of_window_or_generic_annotation_remains_unsupported(self) -> None:
        annotation = {
            "agents": [
                {
                    "type": "Pedestrian (Adult)",
                    "visibility_start_timestamp": "0:01.0",
                    "visibility_end_timestamp": "0:02.0",
                    "actions": [],
                }
            ],
            "ego_vehicle": {"actions": [{"type": "fst:DrivingInLane"}]},
            "traffic_lights": [],
            "traffic_objects": [],
        }
        result = classify_annotation_candidate(annotation, 10_000_000)
        self.assertEqual(result["candidate_slices"], [])
        self.assertEqual(result["classification_status"], "UNSUPPORTED_BY_ANNOTATION")

    def test_shortlist_is_unique_and_public_summary_has_no_raw_identifiers(self) -> None:
        candidates = [
            {
                "clip_id": f"private-{index}",
                "candidate_digest": f"candidate-sha256:{index:064x}",
                "candidate_slices": [slice_name],
                "sensor_feature_eligible": True,
                "country": "United States",
            }
            for index, slice_name in enumerate(
                (
                    "PEDESTRIAN_CYCLIST_YIELD",
                    "STOP_SIGNALS",
                    "FOLLOWING_CUT_IN",
                ),
                start=1,
            )
        ]
        shortlist = select_sensor_shortlist(candidates, per_slice=1)
        self.assertEqual(shortlist["selected_unique_clip_count"], 3)
        summary = deidentified_screen_summary(candidates, shortlist)
        text = repr(summary).lower()
        self.assertNotIn("clip_id", text)
        self.assertNotIn("private-", text)
        self.assertNotIn("coc", text)
        self.assertEqual(summary["final_outcome_assigned_count"], 0)

    def test_attrition_reserve_reuses_clip_assets_without_losing_distinct_events(self) -> None:
        def candidate(index: int, clip_id: str, slices: list[str]) -> dict[str, object]:
            return {
                "clip_id": clip_id,
                "candidate_digest": f"candidate-sha256:{index:064x}",
                "event_timestamp_us": index * 1_000_000,
                "candidate_slices": slices,
                "sensor_feature_eligible": True,
                "country": "United States",
                "chunk": index,
            }

        selected_pedestrian = candidate(1, "selected-a", ["PEDESTRIAN_CYCLIST_YIELD"])
        selected_stop = candidate(2, "selected-b", ["STOP_SIGNALS"])
        candidates = [
            selected_pedestrian,
            selected_stop,
            candidate(3, "selected-a", ["FOLLOWING_CUT_IN"]),
            candidate(4, "reserve-c", ["PEDESTRIAN_CYCLIST_YIELD", "STOP_SIGNALS"]),
            candidate(5, "reserve-c", ["STOP_SIGNALS"]),
            candidate(6, "reserve-d", ["FOLLOWING_CUT_IN"]),
            candidate(7, "unsupported", []),
        ]
        primary = {
            "records": [
                {**selected_pedestrian, "shortlist_slice": "PEDESTRIAN_CYCLIST_YIELD"},
                {**selected_stop, "shortlist_slice": "STOP_SIGNALS"},
            ]
        }

        reserve = build_attrition_reserve(candidates, primary)

        self.assertEqual(reserve["classified_event_count"], 6)
        self.assertEqual(reserve["classified_unique_clip_count"], 4)
        self.assertEqual(reserve["reserve_event_count"], 4)
        self.assertEqual(reserve["new_clip_materialization_count"], 2)
        self.assertEqual(reserve["new_clip_secondary_event_count"], 1)
        self.assertEqual(reserve["reused_materialized_clip_event_count"], 1)
        self.assertEqual(len(reserve["materialization_records"]), 2)
        tiers = {record["reserve_tier"] for record in reserve["records"]}
        self.assertEqual(
            tiers,
            {
                "NEW_CLIP_PRIMARY",
                "NEW_CLIP_SECONDARY_EVENT",
                "MATERIALIZED_CLIP_SECONDARY_EVENT",
            },
        )
        for record in reserve["records"]:
            self.assertIn("asset_candidate_digest", record)
            self.assertIn("reserve_slice", record)


if __name__ == "__main__":
    unittest.main()
