"""Fail-closed tests for M16 materialized sensor evidence."""

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

from guard_synth.m16_sensor_evidence_audit import (
    audit_timestamp_series,
    field_status,
    public_sensor_audit_summary,
)


class M16SensorEvidenceAuditTest(unittest.TestCase):
    def test_timestamp_coverage_is_source_derived(self) -> None:
        result = audit_timestamp_series([0, 1_000_000, 2_000_000], 1_100_000)
        self.assertTrue(result["event_covered"])
        self.assertEqual(result["nearest_event_delta_us"], 100_000)
        invalid = audit_timestamp_series([0, 2, 1], 1)
        self.assertFalse(invalid["event_covered"])

    def test_sensor_only_fields_fail_closed_at_two_of_eight(self) -> None:
        statuses = field_status(temporal_closure=True, ego_speed_finite=True)
        self.assertEqual(
            sum(status == "AVAILABLE_SOURCE_LINKED" for status in statuses.values()), 2
        )
        self.assertIn(
            "UNSUPPORTED_CALIBRATION_RIG_BINDING_NOT_MATERIALIZED",
            statuses.values(),
        )

    def test_public_summary_never_promotes_outcome_or_eligibility(self) -> None:
        statuses = field_status(temporal_closure=True, ego_speed_finite=True)
        summary = public_sensor_audit_summary([{
            "member_closure": "6_OF_6",
            "temporal_closure": True,
            "source_complete": False,
            "field_status": statuses,
        }])
        self.assertEqual(summary["source_complete_8_of_8_candidate_count"], 0)
        self.assertEqual(summary["newly_eligible_candidate_count"], 0)
        self.assertEqual(summary["final_outcome_assigned_count"], 0)


if __name__ == "__main__":
    unittest.main()
