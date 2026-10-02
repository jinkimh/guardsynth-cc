"""Fail-closed tests for real-scene source authoring and readiness."""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import sys
import unittest


ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "PROJECT_REGISTRY.json").is_file())
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from guard_synth.assurance_registry import (
    AssuranceRegistryValidationError,
    parse_assurance_registry,
)
from guard_synth.source_authoring import (
    GroundedSceneValidationError,
    assess_scene_readiness,
    author_generation_request,
)
from guard_synth.source_aware_generator import generate_from_request, parse_generation_request
from guard_synth_eblc.schema_validation import load_json


REQUEST_FIXTURE = ROOT / "projects/04-guardsynth-coc/src/guard_synth/fixtures/source_aware_generation_request_p0b_v0_1.json"
EMPTY_REGISTRY = ROOT / "projects/04-guardsynth-coc/src/guard_synth/fixtures/vehicle_assurance_registry_empty_v0_1.json"


def registry_raw() -> dict:
    return {
        "registry_version": "guardsynth-vehicle-assurance-registry-v0.1",
        "registry_id": "synthetic_test_registry",
        "profiles": [{
            "profile_id": "profile_test_v1",
            "vehicle_binding_key": "vehicle:test-platform",
            "maximum_service_deceleration_mps2": 3.0,
            "response_time_s": 0.5,
            "position_uncertainty_m": 0.5,
            "evidence": {
                "evidence_ref": "TEST-VEHICLE-ASSURANCE-v1",
                "source_class": "CONTROLLED_TEST_REPORT",
                "uri": "urn:test:vehicle-assurance:v1",
                "version": "1",
                "sha256": "a" * 64,
                "scope": "SYNTHETIC_TEST_ONLY_NOT_REAL_VEHICLE_ASSURANCE"
            }
        }]
    }


def grounded_scene(ordinal: int) -> dict:
    suffix = str(ordinal)
    return {
        "scene_ref": f"scene:{suffix}",
        "instance_id": f"scene_{suffix}",
        "contract_id": f"C{ordinal}",
        "timestamp_s": 0.0,
        "hazard": {
            "truth": "TRUE",
            "epistemic_kind": "OBSERVED",
            "evidence_ref": f"OBS-{suffix}",
            "timestamp_s": 0.0,
            "maximum_age_s": 0.2,
        },
        "association": {
            "target_entity_id": f"pedestrian:{suffix}",
            "zone_id": f"zone:{suffix}",
            "evidence_ref": f"ASSOC-{suffix}",
        },
        "zone_geometry": {
            "entry_x_m": float(ordinal * 10),
            "frame": "ego_path_s",
            "evidence_ref": f"GEOM-{suffix}",
        },
        "coordinate_transform": {
            "verified": True,
            "evidence_ref": f"TF-{suffix}",
        },
        "vehicle_binding_key": "vehicle:test-platform",
        "assurance_scope": "SYNTHETIC_TEST_ONLY_NOT_REAL_VEHICLE_ASSURANCE",
        "reason_codes": [],
    }


class AssuranceRegistryTest(unittest.TestCase):
    def test_empty_registry_has_no_implicit_default(self) -> None:
        registry = parse_assurance_registry(load_json(EMPTY_REGISTRY))
        self.assertIsNone(registry.resolve("vehicle:any"))
        self.assertEqual(registry.profiles, ())

    def test_exact_profile_binding_preserves_source(self) -> None:
        profile = parse_assurance_registry(registry_raw()).resolve("vehicle:test-platform")
        self.assertIsNotNone(profile)
        self.assertEqual(profile.evidence.evidence_ref, "TEST-VEHICLE-ASSURANCE-v1")
        self.assertEqual(profile.maximum_service_deceleration_mps2, 3.0)

    def test_duplicate_binding_is_rejected(self) -> None:
        raw = registry_raw()
        raw["profiles"].append(deepcopy(raw["profiles"][0]))
        raw["profiles"][1]["profile_id"] = "duplicate_profile"
        with self.assertRaisesRegex(AssuranceRegistryValidationError, "duplicate"):
            parse_assurance_registry(raw)


class SourceAuthoringTest(unittest.TestCase):
    def test_two_complete_scenes_author_executable_request(self) -> None:
        base = load_json(REQUEST_FIXTURE)
        registry = parse_assurance_registry(registry_raw())
        raw = author_generation_request(
            base_request=base,
            grounded_scenes=[grounded_scene(0), grounded_scene(1)],
            registry=registry,
            request_id="authored_two_scene_request",
        )
        result = generate_from_request(parse_generation_request(raw))
        self.assertEqual(result.verdict, "VALIDATED")
        self.assertEqual(len(result.collection.instances), 2)
        self.assertNotIn("P0B-SYNTHETIC-VEHICLE-PROFILE-v0", raw["source_refs"])
        self.assertNotIn("P0B-SYNTHETIC-OBSERVATION-A-v0", raw["source_refs"])
        self.assertEqual(raw["context_graph"]["coc_claims"], [])
        self.assertIn("TEST-VEHICLE-ASSURANCE-v1", raw["source_refs"])

    def test_missing_verified_transform_is_not_authored(self) -> None:
        scene = grounded_scene(0)
        scene["coordinate_transform"]["verified"] = False
        with self.assertRaisesRegex(GroundedSceneValidationError, "UNVERIFIED_COORDINATE_TRANSFORM"):
            author_generation_request(
                base_request=load_json(REQUEST_FIXTURE),
                grounded_scenes=[scene, grounded_scene(1)],
                registry=parse_assurance_registry(registry_raw()),
                request_id="rejected_request",
            )

    def test_missing_assurance_profile_is_not_authored(self) -> None:
        with self.assertRaisesRegex(GroundedSceneValidationError, "MISSING_VEHICLE_ASSURANCE_PROFILE"):
            author_generation_request(
                base_request=load_json(REQUEST_FIXTURE),
                grounded_scenes=[grounded_scene(0), grounded_scene(1)],
                registry=parse_assurance_registry(load_json(EMPTY_REGISTRY)),
                request_id="rejected_request",
            )

    def test_readiness_matrix_does_not_fabricate_missing_slots(self) -> None:
        adapter = {
            "vru_event_count": 2,
            "candidates": [{
                "target_binding": {"verdict": "REVIEW_REQUIRED"},
                "contract_binding": {
                    "verdict": "UNSUPPORTED",
                    "reason_codes": ["AMBIGUOUS_TARGET", "MISSING_VEHICLE_ASSURANCE_PROFILE"],
                },
            }],
            "data_gaps": [{"reason_code": "EVENT_OUTSIDE_RECORDED_FUTURE_HORIZON"}],
        }
        result = assess_scene_readiness(
            adapter, parse_assurance_registry(load_json(EMPTY_REGISTRY)), target_slots=24
        )
        self.assertEqual(result["slot_count"], 24)
        self.assertEqual(result["actual_candidate_event_count"], 2)
        self.assertEqual(result["source_complete_scene_count"], 0)
        self.assertEqual(result["missing_scene_input_slot_count"], 22)
        self.assertEqual(result["decision"], "DATA_GAP_PIVOT")
        self.assertFalse(result["twenty_four_scene_execution_completed"])
        self.assertFalse(result["synthetic_scene_fill_performed"])

    def test_current_restricted_bundle_remains_fail_closed(self) -> None:
        prior = ROOT / "artifacts/results/restricted/eblc-p0b-001/p0b-restricted-grounding-multiview-2026-08-08-v1/ADAPTER_RESULT.json"
        if not prior.is_file():
            self.skipTest("restricted derived adapter artifact not present")
        adapter = load_json(prior)
        result = assess_scene_readiness(
            adapter, parse_assurance_registry(load_json(EMPTY_REGISTRY)), target_slots=24
        )
        self.assertEqual(result["source_complete_scene_count"], 0)
        self.assertEqual(result["actual_candidate_event_count"], 5)
        self.assertEqual(result["missing_scene_input_slot_count"], 19)
        self.assertEqual(result["decision"], "DATA_GAP_PIVOT")
        self.assertNotIn("clip_id", json.dumps(result))
        self.assertNotIn("candidate_id", json.dumps(result))


if __name__ == "__main__":
    unittest.main()
