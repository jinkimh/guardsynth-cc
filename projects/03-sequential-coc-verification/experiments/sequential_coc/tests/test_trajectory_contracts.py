"""Synthetic tests for exploratory longitudinal trajectory consistency."""

from __future__ import annotations

import json
from pathlib import Path
import stat
import unittest

from experiments.sequential_coc.contract_ir import Action, EvidenceValue
from experiments.sequential_coc.tests.fixtures import event, hold_event
from experiments.sequential_coc.trajectory_contracts import (
    BASELINE_THRESHOLDS,
    LENIENT_THRESHOLDS,
    STRICT_THRESHOLDS,
    TRAJECTORY_RESULTS_PATH,
    ObservedAction,
    classify_observed_action,
    evaluate_trajectory_contract,
)


def trace(*speeds: float, step_s: float = 0.25) -> tuple[dict[str, float | int], ...]:
    return tuple(
        {
            "timestamp_us": round(index * step_s * 1_000_000),
            "signed_longitudinal_speed_mps": speed,
        }
        for index, speed in enumerate(speeds)
    )


class TrajectoryContractsTests(unittest.TestCase):
    def test_classifies_only_signed_longitudinal_speed_actions(self) -> None:
        cases = (
            (trace(0.2, 0.2, 0.2), ObservedAction.STOP_OR_HOLD),
            (trace(3.0, 2.9, 2.7), ObservedAction.YIELD_OR_DECELERATE),
            (trace(2.0, 2.02, 2.04), ObservedAction.MAINTAIN_SPEED),
            (trace(1.0, 1.1, 1.3), ObservedAction.ACCELERATE_OR_PROCEED),
        )
        for ego_trace, expected in cases:
            with self.subTest(expected=expected):
                self.assertEqual(
                    classify_observed_action(ego_trace, BASELINE_THRESHOLDS),
                    expected,
                )

        lateral_distraction = tuple(
            {**sample, "vy": (-1) ** index * 100.0}
            for index, sample in enumerate(trace(1.0, 1.1, 1.3))
        )
        self.assertEqual(
            classify_observed_action(lateral_distraction, BASELINE_THRESHOLDS),
            ObservedAction.ACCELERATE_OR_PROCEED,
        )

    def test_returns_unknown_when_direction_is_not_sustained(self) -> None:
        ego_trace = trace(1.0, 1.2, 1.0, 1.2, 1.2)
        self.assertEqual(
            classify_observed_action(ego_trace, BASELINE_THRESHOLDS),
            ObservedAction.UNKNOWN,
        )

    def test_evaluates_normal_and_mismatched_longitudinal_actions(self) -> None:
        accelerate = (event(action=Action.ACCELERATE_OR_PROCEED),)
        aligned = evaluate_trajectory_contract(
            accelerate, trace(1.0, 1.1, 1.3), BASELINE_THRESHOLDS
        )
        mismatch = evaluate_trajectory_contract(
            accelerate, trace(3.0, 2.9, 2.7), BASELINE_THRESHOLDS
        )
        self.assertEqual((aligned.verdict, aligned.reason), ("ALIGNED", "ACTION_MATCH"))
        self.assertEqual(
            (mismatch.verdict, mismatch.reason),
            ("NOT_ALIGNED", "LONGITUDINAL_ACTION_MISMATCH"),
        )

    def test_release_evidence_unknown_false_and_true_have_distinct_results(self) -> None:
        cases = (
            (
                EvidenceValue.UNKNOWN,
                ("UNKNOWN", "RELEASE_EVIDENCE_REQUIRED"),
            ),
            (
                EvidenceValue.FALSE,
                ("NOT_ALIGNED", "LONGITUDINAL_ACTION_MISMATCH"),
            ),
            (
                EvidenceValue.TRUE,
                ("ALIGNED", "RELEASE_CONFIRMED"),
            ),
        )
        for release, expected in cases:
            with self.subTest(release=release):
                events = (
                    hold_event(
                        release=release,
                        timestamp_us=0,
                        event_id=f"synthetic-hold-{release.value.lower()}",
                    ),
                )
                result = evaluate_trajectory_contract(
                    events, trace(0.0, 0.1, 0.4), BASELINE_THRESHOLDS
                )
                self.assertEqual((result.verdict, result.reason), expected)

    def test_threshold_boundary_and_named_sensitivity_profiles(self) -> None:
        boundary = trace(1.0, 1.05, 1.10)
        self.assertEqual(
            classify_observed_action(boundary, BASELINE_THRESHOLDS),
            ObservedAction.ACCELERATE_OR_PROCEED,
        )
        self.assertEqual(
            classify_observed_action(boundary, STRICT_THRESHOLDS),
            ObservedAction.MAINTAIN_SPEED,
        )
        self.assertEqual(
            classify_observed_action(boundary, LENIENT_THRESHOLDS),
            ObservedAction.ACCELERATE_OR_PROCEED,
        )

    def test_missing_signed_longitudinal_samples_are_unknown(self) -> None:
        result = evaluate_trajectory_contract(
            (event(action=Action.MAINTAIN_SPEED),),
            ({"timestamp_us": 0, "speed_mps": 1.0},),
            BASELINE_THRESHOLDS,
        )
        self.assertEqual(
            (result.verdict, result.reason),
            ("UNKNOWN", "SIGNED_LONGITUDINAL_TRACE_REQUIRED"),
        )

    def test_generated_results_have_exact_aggregate_only_schema(self) -> None:
        rows = [
            json.loads(line)
            for line in TRAJECTORY_RESULTS_PATH.read_text(encoding="utf-8").splitlines()
        ]
        self.assertEqual(len(rows), 1)
        scene_records = rows[0].pop("scene_records")
        self.assertEqual(len(scene_records), 94)
        scene_ids = {record["scene_cluster_id"] for record in scene_records}
        self.assertEqual(len(scene_ids), 94)
        self.assertTrue(all(scene_id.startswith("scene-") for scene_id in scene_ids))
        self.assertTrue(
            all("threshold_results" in record and "source_text" not in record for record in scene_records)
        )
        self.assertEqual(
            rows[0],
            {
                "sample_units": {"event": 403, "scene_cluster": 94},
                "linked_event_count": 403,
                "link_failure_reasons": {},
                "verdict_counts": {
                    "event": {
                        "baseline": {"ALIGNED": 107, "NOT_ALIGNED": 47, "UNKNOWN": 249},
                        "strict": {"ALIGNED": 71, "NOT_ALIGNED": 21, "UNKNOWN": 311},
                        "lenient": {"ALIGNED": 107, "NOT_ALIGNED": 48, "UNKNOWN": 248},
                    },
                    "scene_cluster": {
                        "baseline": {"ALIGNED": 6, "NOT_ALIGNED": 28, "UNKNOWN": 60},
                        "strict": {"ALIGNED": 2, "NOT_ALIGNED": 10, "UNKNOWN": 82},
                        "lenient": {"ALIGNED": 7, "NOT_ALIGNED": 29, "UNKNOWN": 58},
                    },
                },
                "verdict_change_counts": {"event": 78, "scene_cluster": 25},
            },
        )

        self.assertEqual(stat.S_IMODE(TRAJECTORY_RESULTS_PATH.stat().st_mode), 0o600)
        self.assertEqual(stat.S_IMODE(Path(TRAJECTORY_RESULTS_PATH.parent).stat().st_mode), 0o700)


if __name__ == "__main__":
    unittest.main()
