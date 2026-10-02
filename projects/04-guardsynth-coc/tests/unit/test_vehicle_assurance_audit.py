from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys
import unittest


ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "PROJECT_REGISTRY.json").is_file())
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from guard_synth.vehicle_assurance_audit import audit_vehicle_assurance_candidates


BINDING_KEY = "nvidia-rig-config-sha256:" + "a" * 64


def candidate(kind: str, **extra: object) -> dict:
    return {
        "candidate_id": kind.lower(),
        "source_kind": kind,
        "source_ref": "https://example.test/source",
        "source_sha256": "b" * 64,
        **extra,
    }


class VehicleAssuranceAuditTest(unittest.TestCase):
    def test_observed_egomotion_is_not_a_vehicle_guarantee(self) -> None:
        result = audit_vehicle_assurance_candidates(
            vehicle_binding_key=BINDING_KEY,
            candidates=[candidate("OBSERVED_EGOMOTION")],
        )
        self.assertEqual(result["status"], "REVIEW_REQUIRED")
        self.assertEqual(
            result["reason_code"],
            "MISSING_SOURCE_BEARING_VEHICLE_ASSURANCE_PROFILE",
        )
        self.assertEqual(
            result["rejected_candidates"][0]["reason_code"],
            "OBSERVATION_NOT_GUARANTEE",
        )
        self.assertFalse(result["contract_generation_allowed"])

    def test_platform_interface_documentation_is_not_vehicle_specific(self) -> None:
        result = audit_vehicle_assurance_candidates(
            vehicle_binding_key=BINDING_KEY,
            candidates=[candidate("PLATFORM_INTERFACE_DOCUMENTATION")],
        )
        self.assertEqual(result["status"], "REVIEW_REQUIRED")
        self.assertEqual(
            result["rejected_candidates"][0]["reason_code"],
            "INTERFACE_DOCUMENTATION_NOT_BOUND_ASSURANCE",
        )

    def test_derived_coc_latency_is_not_actuator_latency(self) -> None:
        result = audit_vehicle_assurance_candidates(
            vehicle_binding_key=BINDING_KEY,
            candidates=[candidate("DERIVED_COC_RESPONSE_LATENCY")],
        )
        self.assertEqual(
            result["rejected_candidates"][0]["reason_code"],
            "BEHAVIOR_RESPONSE_NOT_ACTUATOR_ASSURANCE",
        )

    def test_complete_validated_profile_is_accepted(self) -> None:
        result = audit_vehicle_assurance_candidates(
            vehicle_binding_key=BINDING_KEY,
            candidates=[candidate(
                "CONTROL_STACK_VALIDATED",
                vehicle_binding_key=BINDING_KEY,
                minimum_guaranteed_deceleration_mps2=3.0,
                maximum_command_to_deceleration_latency_s=0.2,
                maximum_abs_jerk_mps3=5.0,
                operating_conditions={"surface": "dry"},
                uncertainty_model={"confidence": 0.99},
                validation_method="CONTROLLED_BRAKE_TEST",
            )],
        )
        self.assertEqual(result["status"], "AVAILABLE_SOURCE_LINKED")
        self.assertTrue(result["contract_generation_allowed"])
        self.assertEqual(result["accepted_candidate_id"], "control_stack_validated")

    def test_binding_mismatch_is_rejected_without_mutating_input(self) -> None:
        candidates = [candidate(
            "OEM_VALIDATED",
            vehicle_binding_key="another-binding",
            minimum_guaranteed_deceleration_mps2=3.0,
            maximum_command_to_deceleration_latency_s=0.2,
            maximum_abs_jerk_mps3=5.0,
            operating_conditions={"surface": "dry"},
            uncertainty_model={"confidence": 0.99},
            validation_method="OEM_CERTIFICATION",
        )]
        before = deepcopy(candidates)
        result = audit_vehicle_assurance_candidates(
            vehicle_binding_key=BINDING_KEY,
            candidates=candidates,
        )
        self.assertEqual(result["status"], "REVIEW_REQUIRED")
        self.assertEqual(
            result["rejected_candidates"][0]["reason_code"],
            "VEHICLE_BINDING_MISMATCH",
        )
        self.assertEqual(candidates, before)


if __name__ == "__main__":
    unittest.main()
