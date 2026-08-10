"""Adversarial and 24-contract tests for the GuardSynth source boundary."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys
import unittest

from cli.solver_runtime import configure_project_z3


ROOT = Path(__file__).resolve().parents[2]
configure_project_z3(ROOT)
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
from guard_synth_eblc.bundle_elaborator import elaborate_bundle
from guard_synth_eblc.indexed_collection import expand_indexed_collection
from guard_synth_eblc.schema_validation import SchemaValidationError, load_json
from guard_synth_eblc.smt_compiler import compile_core_model, solve_assignment


REQUEST = ROOT / "src/guard_synth/fixtures/source_aware_generation_request_p0b_v0_1.json"
SCOPE = "SYNTHETIC_TEST_ONLY_NOT_REAL_VEHICLE_ASSURANCE"


def registry_raw() -> dict:
    return {
        "registry_version": "guardsynth-vehicle-assurance-registry-v0.1",
        "registry_id": "adversarial_test_registry",
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
                "sha256": "b" * 64,
                "scope": SCOPE,
            },
        }],
    }


def scene(ordinal: int) -> dict:
    suffix = str(ordinal)
    return {
        "scene_ref": f"scene:{suffix}",
        "instance_id": f"scene_{suffix}",
        "contract_id": f"C{ordinal}",
        "timestamp_s": 0.0,
        "hazard": {
            "truth": "TRUE", "epistemic_kind": "OBSERVED",
            "evidence_ref": f"OBS-{suffix}", "timestamp_s": 0.0,
            "maximum_age_s": 0.2,
        },
        "association": {
            "target_entity_id": f"pedestrian:{suffix}",
            "zone_id": f"zone:{suffix}", "evidence_ref": f"ASSOC-{suffix}",
        },
        "zone_geometry": {
            "entry_x_m": float(ordinal * 10), "frame": "ego_path_s",
            "evidence_ref": f"GEOM-{suffix}",
        },
        "coordinate_transform": {"verified": True, "evidence_ref": f"TF-{suffix}"},
        "vehicle_binding_key": "vehicle:test-platform",
        "assurance_scope": SCOPE,
        "reason_codes": [],
    }


def readiness_candidate(ordinal: int) -> dict:
    return {
        "context_schema_valid": True,
        "context_graph": {
            "timestamp_s": 0.0,
            "hazard_fact": {
                "truth": "TRUE", "epistemic_kind": "OBSERVED",
                "source": f"OBS-{ordinal}", "timestamp_s": 0.0,
                "maximum_age_s": 0.2,
            },
            "ego_front_x_m": 0.0,
            "ego_speed_mps": 0.0,
            "zone_entry_x_m": float(ordinal),
            "target_entity_id": f"target:{ordinal}",
            "zone_id": f"zone:{ordinal}",
            "coordinate_frame": "ego_path_s", "distance_unit": "m",
        },
        "target_binding": {
            "verdict": "VALIDATED", "association_evidence_refs": [f"ASSOC-{ordinal}"],
        },
        "conflict_zone": {"source_fields": ["derived.longitudinal_gap_m"]},
        "coordinate_transform": {"verified": True, "evidence_ref": f"TF-{ordinal}"},
        "vehicle_binding_key": "vehicle:test-platform",
        "assurance_scope": SCOPE,
        "contract_binding": {"verdict": "VALIDATED", "reason_codes": []},
    }


class AssuranceRegistryAdversarialTest(unittest.TestCase):
    def test_invalid_numeric_and_digest_values_fail_closed(self) -> None:
        mutations = (
            ("maximum_service_deceleration_mps2", 0.0, AssuranceRegistryValidationError),
            ("maximum_service_deceleration_mps2", float("nan"), SchemaValidationError),
            ("response_time_s", -0.1, SchemaValidationError),
            ("position_uncertainty_m", float("inf"), SchemaValidationError),
        )
        for field, value, error in mutations:
            with self.subTest(field=field, value=value):
                raw = registry_raw()
                raw["profiles"][0][field] = value
                with self.assertRaises(error):
                    parse_assurance_registry(raw)
        for digest in ("a" * 63, "A" * 64, "g" * 64):
            with self.subTest(digest=digest[:2]):
                raw = registry_raw()
                raw["profiles"][0]["evidence"]["sha256"] = digest
                with self.assertRaises((AssuranceRegistryValidationError, SchemaValidationError)):
                    parse_assurance_registry(raw)

    def test_blank_source_fields_and_non_uri_fail_closed(self) -> None:
        for field in ("profile_id", "vehicle_binding_key"):
            raw = registry_raw()
            raw["profiles"][0][field] = "   "
            with self.subTest(field=field), self.assertRaises(AssuranceRegistryValidationError):
                parse_assurance_registry(raw)
        for field in ("evidence_ref", "version", "scope"):
            raw = registry_raw()
            raw["profiles"][0]["evidence"][field] = "   "
            with self.subTest(field=field), self.assertRaises(AssuranceRegistryValidationError):
                parse_assurance_registry(raw)
        raw = registry_raw()
        raw["profiles"][0]["evidence"]["uri"] = "not-a-uri"
        with self.assertRaisesRegex(AssuranceRegistryValidationError, "URI"):
            parse_assurance_registry(raw)
        raw = registry_raw()
        raw["profiles"][0]["evidence"]["uri"] = "javascript:alert(1)"
        with self.assertRaisesRegex(AssuranceRegistryValidationError, "URI"):
            parse_assurance_registry(raw)

    def test_all_registry_uniqueness_axes_are_enforced(self) -> None:
        for path, value in (
            (("profile_id",), "profile_test_v1"),
            (("vehicle_binding_key",), "vehicle:test-platform"),
            (("evidence", "evidence_ref"), "TEST-VEHICLE-ASSURANCE-v1"),
        ):
            raw = registry_raw()
            duplicate = deepcopy(raw["profiles"][0])
            duplicate["profile_id"] = "profile_second"
            duplicate["vehicle_binding_key"] = "vehicle:second"
            duplicate["evidence"]["evidence_ref"] = "TEST-VEHICLE-ASSURANCE-v2"
            target = duplicate
            for key in path[:-1]:
                target = target[key]
            target[path[-1]] = value
            raw["profiles"].append(duplicate)
            with self.subTest(path=path), self.assertRaisesRegex(AssuranceRegistryValidationError, "duplicate"):
                parse_assurance_registry(raw)


class SourceAuthoringAdversarialTest(unittest.TestCase):
    def setUp(self) -> None:
        self.base = load_json(REQUEST)
        self.registry = parse_assurance_registry(registry_raw())

    def author(self, scenes: list[dict]) -> dict:
        return author_generation_request(
            base_request=self.base, grounded_scenes=scenes,
            registry=self.registry, request_id="adversarial_authored_request",
        )

    def test_each_required_scene_evidence_class_fails_closed(self) -> None:
        mutations = {
            "MISSING_HAZARD_EVIDENCE": lambda item: item["hazard"].update(evidence_ref=""),
            "MISSING_OR_AMBIGUOUS_TARGET_ZONE_ASSOCIATION": lambda item: item["association"].update(target_entity_id=""),
            "MISSING_CONFLICT_ZONE_GEOMETRY": lambda item: item["zone_geometry"].update(evidence_ref=""),
            "MISSING_COORDINATE_TRANSFORM": lambda item: item["coordinate_transform"].update(evidence_ref=""),
            "UNVERIFIED_COORDINATE_TRANSFORM": lambda item: item["coordinate_transform"].update(verified=False),
            "MISSING_VEHICLE_ASSURANCE_PROFILE": lambda item: item.update(vehicle_binding_key="vehicle:unknown"),
            "ASSURANCE_SCOPE_MISMATCH": lambda item: item.update(assurance_scope="REAL_ODD_NOT_SYNTHETIC"),
        }
        for reason, mutate in mutations.items():
            values = [scene(0), scene(1)]
            mutate(values[0])
            with self.subTest(reason=reason), self.assertRaisesRegex(GroundedSceneValidationError, reason):
                self.author(values)

    def test_generator_rejections_do_not_escape_authoring_boundary(self) -> None:
        mutations = (
            lambda item: item["hazard"].update(epistemic_kind="CLAIMED"),
            lambda item: item["hazard"].update(timestamp_s=1.0),
            lambda item: item["zone_geometry"].update(frame="wrong_frame"),
            lambda item: item.update(contract_id="C1"),
        )
        for mutate in mutations:
            values = [scene(0), scene(1)]
            mutate(values[0])
            with self.subTest(mutation=mutate), self.assertRaises(GroundedSceneValidationError):
                self.author(values)

    def test_mixed_vehicle_profiles_are_rejected_even_when_each_exists(self) -> None:
        raw_registry = registry_raw()
        second = deepcopy(raw_registry["profiles"][0])
        second["profile_id"] = "profile_test_v2"
        second["vehicle_binding_key"] = "vehicle:second-platform"
        second["evidence"]["evidence_ref"] = "TEST-VEHICLE-ASSURANCE-v2"
        second["evidence"]["sha256"] = "c" * 64
        registry = parse_assurance_registry({
            **raw_registry, "profiles": [raw_registry["profiles"][0], second],
        })
        values = [scene(0), scene(1)]
        values[1]["vehicle_binding_key"] = "vehicle:second-platform"
        with self.assertRaisesRegex(GroundedSceneValidationError, "MIXED_OR_MISSING_VEHICLE_BINDING"):
            author_generation_request(
                base_request=self.base, grounded_scenes=values, registry=registry,
                request_id="mixed_vehicle_request",
            )

    def test_authored_request_has_only_current_context_and_profile_sources(self) -> None:
        left = self.author([scene(0), scene(1)])
        right = self.author([scene(0), scene(1)])
        self.assertEqual(left, right)
        stale = {
            ref for ref in left["source_refs"]
            if ref.startswith("P0B-SYNTHETIC-OBSERVATION")
            or ref.startswith("P0B-SYNTHETIC-ASSOCIATION")
            or ref.startswith("P0B-SYNTHETIC-ZONE-GEOMETRY")
            or ref == "P0B-SYNTHETIC-VEHICLE-PROFILE-v0"
        }
        self.assertEqual(stale, set())
        parsed = parse_generation_request(left)
        self.assertEqual(generate_from_request(parsed).verdict, "VALIDATED")

    def test_twenty_four_contracts_reach_real_z3(self) -> None:
        raw = self.author([scene(index) for index in range(24)])
        generated = generate_from_request(parse_generation_request(raw))
        self.assertEqual(generated.verdict, "VALIDATED")
        expansion = expand_indexed_collection(generated.collection)
        self.assertEqual(expansion.verdict, "VALIDATED")
        compiled = compile_core_model(elaborate_bundle(expansion.bundle).core_model)
        solved = solve_assignment(compiled, {})
        self.assertEqual(solved["status"], "SAT")
        self.assertEqual(len(expansion.bundle.contracts), 24)
        symbols = {
            (item["declaration"], item["time"]): item["smt_symbol"]
            for item in compiled.symbol_table["symbols"]
        }
        self.assertEqual(solved["witness"][symbols[("c23__stop_position", None)]], "457/2")


class ReadinessAccountingAdversarialTest(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = parse_assurance_registry(registry_raw())

    def test_adapter_count_mismatch_fails_closed_in_both_directions(self) -> None:
        for declared in (0, 2):
            adapter = {
                "vru_event_count": declared,
                "candidates": [readiness_candidate(0)],
                "data_gaps": [],
            }
            with self.subTest(declared=declared), self.assertRaisesRegex(ValueError, "accounting"):
                assess_scene_readiness(adapter, self.registry, target_slots=24)

    def test_invalid_target_slot_count_fails_closed(self) -> None:
        for slots in (0, -1, True):
            with self.subTest(slots=slots), self.assertRaises(ValueError):
                assess_scene_readiness({"candidates": [], "data_gaps": []}, self.registry, target_slots=slots)

    def test_shallow_validity_flags_cannot_make_a_scene_source_complete(self) -> None:
        shallow = {
            "context_schema_valid": True,
            "target_binding": {"verdict": "VALIDATED"},
            "contract_binding": {"verdict": "VALIDATED", "reason_codes": []},
            "vehicle_binding_key": "vehicle:test-platform",
            "assurance_scope": SCOPE,
            "coordinate_transform": {"verified": True, "evidence_ref": "TF"},
        }
        result = assess_scene_readiness(
            {"vru_event_count": 1, "candidates": [shallow], "data_gaps": []},
            self.registry, target_slots=24,
        )
        self.assertEqual(result["source_complete_scene_count"], 0)
        self.assertIn("MISSING_HAZARD_EVIDENCE", result["slots"][0]["reason_codes"])
        self.assertIn("MISSING_CONFLICT_ZONE_GEOMETRY", result["slots"][0]["reason_codes"])

    def test_context_schema_is_revalidated_instead_of_trusting_flag(self) -> None:
        candidate = readiness_candidate(0)
        candidate["context_graph"]["timestamp_s"] = "not-a-number"
        result = assess_scene_readiness(
            {"vru_event_count": 1, "candidates": [candidate], "data_gaps": []},
            self.registry, target_slots=1,
        )
        self.assertEqual(result["source_complete_scene_count"], 0)
        self.assertIn("INVALID_OR_UNVALIDATED_CONTEXT_GRAPH", result["slots"][0]["reason_codes"])

    def test_twenty_four_complete_inputs_pass_readiness_but_not_execution_claim(self) -> None:
        candidates = [readiness_candidate(index) for index in range(24)]
        result = assess_scene_readiness(
            {"vru_event_count": 24, "candidates": candidates, "data_gaps": []},
            self.registry, target_slots=24,
        )
        self.assertEqual(result["source_complete_scene_count"], 24)
        self.assertTrue(result["twenty_four_scene_readiness_gate_passed"])
        self.assertFalse(result["twenty_four_scene_execution_completed"])
        self.assertEqual(result["decision"], "P0B_GO")
        self.assertEqual(len(result["slots"]), 24)

    def test_readiness_output_contains_no_input_identifiers(self) -> None:
        candidate = readiness_candidate(0)
        candidate["clip_id"] = "restricted-raw-clip"
        candidate["candidate_id"] = "restricted-candidate"
        result = assess_scene_readiness(
            {"vru_event_count": 1, "candidates": [candidate], "data_gaps": []},
            self.registry, target_slots=1,
        )
        rendered = str(result)
        self.assertNotIn("restricted-raw-clip", rendered)
        self.assertNotIn("restricted-candidate", rendered)


if __name__ == "__main__":
    unittest.main()
