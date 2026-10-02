"""TDD contract for the scene-evidence + simulated-vehicle execution path."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys
import unittest

from cli.solver_runtime import configure_project_z3


ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "PROJECT_REGISTRY.json").is_file())
configure_project_z3(ROOT)
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from guard_synth.simulated_scene_dry_run import (
    SimulationProjectionError,
    build_reference_translation_cases,
    build_simulated_generation_request,
    concrete_scene_t0_assignments,
    load_simulated_assurance_model,
    simulate_full_stop,
)
from guard_synth.simulated_scene_inventory import (
    REQUIRED_SCENE_FIELDS,
    build_scene_candidate_inventory,
)
from guard_synth.sim24_batch import build_sim24_terminal_batch
from guard_synth.geometric_association import build_geometric_set_association
from guard_synth.simulated_scene_evidence import (
    build_event_scene_source_closure,
    build_system_requirement_applicability,
)
from guard_synth.source_aware_generator import generate_from_request
from guard_synth_eblc.bundle_elaborator import elaborate_bundle
from guard_synth_eblc.indexed_collection import expand_indexed_collection
from guard_synth_eblc.schema_validation import load_json
from guard_synth_eblc.smt_compiler import compile_core_model, solve_assignment


MODEL = ROOT / "projects/04-guardsynth-coc/src/guard_synth/fixtures/simulated_assurance_profile_v0_1.json"
BASE_REQUEST = ROOT / "projects/04-guardsynth-coc/src/guard_synth/fixtures/source_aware_generation_request_p0b_v0_1.json"
REQUIREMENT = ROOT / "projects/04-guardsynth-coc/src/guard_synth/fixtures/simulated_corridor_requirement_v0_1.json"


def source_audit() -> dict:
    return {
        "scene_ref": "scene-01",
        "available_fields": [
            "timestamps",
            "ego_pose_and_speed",
            "relevant_actor_tracks",
            "target_zone_or_lane_association",
            "conflict_or_stop_geometry",
            "verified_coordinate_transform",
            "applicable_rule_source_refs",
            "exact_vehicle_binding",
        ],
        "missing_fields": ["source_bearing_vehicle_assurance_profile"],
        "source_complete": False,
        "contract_generation_allowed": False,
        "synthesized_required_values": [],
        "field_status": {
            "ego_pose_and_speed": {
                "speed_mps": 4.0,
                "evidence_ref": "restricted-sha256:ego#/state",
                "status": "AVAILABLE_SOURCE_LINKED",
            },
            "target_zone_or_lane_association": {
                "status": "AVAILABLE_SOURCE_LINKED",
                "evidence_ref": "restricted-sha256:association#/",
                "target_kind": "SET",
                "track_id_sha256": ["a" * 64, "b" * 64],
                "zone": {"coordinate_frame": "dataset_rig"},
            },
            "conflict_or_stop_geometry": {
                "status": "AVAILABLE_SOURCE_LINKED",
                "entry_x_m": 15.0,
                "evidence_ref": "restricted-sha256:geometry#/zone",
            },
            "verified_coordinate_transform": {
                "status": "AVAILABLE_SOURCE_LINKED",
                "evidence_ref": "restricted-sha256:transform#/matrix",
                "source_frame": "dataset_rig_at_event",
                "target_frame": "ego_at_model_t0",
            },
            "applicable_rule_source_refs": {
                "status": "AVAILABLE_SOURCE_LINKED",
                "applicability_verdict": "CONDITIONALLY_APPLICABLE",
                "evidence_ref": "restricted-sha256:rules#/",
                "rule_source_refs": [
                    {"source_id": "RULE-A", "official_url": "https://example.test/a"},
                    {"source_id": "RULE-B", "official_url": "https://example.test/b"},
                ],
            },
            "exact_vehicle_binding": {
                "status": "AVAILABLE_SOURCE_LINKED",
                "vehicle_binding_key": "recorded-rig:scene-01",
                "evidence_ref": "restricted-sha256:rig#/binding",
            },
        },
    }


def association() -> dict:
    return {
        "scene_ref": "scene-01",
        "event_timestamp_us": 11_300_000,
        "status": "AVAILABLE_SOURCE_LINKED",
        "target_kind": "SET",
        "associated_track_id_sha256": ["a" * 64, "b" * 64],
        "association_id": "sha256:" + "c" * 64,
        "evidence_refs": ["restricted-sha256:tracks#/event"],
        "collision_prediction_claimed": False,
        "vehicle_geometry": {"ego_front_extent_m": 4.0},
    }


def rule_evidence() -> dict:
    return {
        "scene_ref": "scene-01",
        "status": "AVAILABLE_SOURCE_LINKED",
        "applicability_verdict": "CONDITIONALLY_APPLICABLE",
        "rule_source_refs": [
            {"source_id": "RULE-A", "official_url": "https://example.test/a"},
            {"source_id": "RULE-B", "official_url": "https://example.test/b"},
        ],
        "numeric_vehicle_bound_derived": False,
    }


def coc_claim() -> dict:
    return {
        "present": True,
        "epistemic_kind": "CLAIMED",
        "text_included": False,
        "text_sha256": "d" * 64,
    }


class SimulatedAssuranceModelTest(unittest.TestCase):
    def test_delay_then_constant_deceleration_matches_closed_form(self) -> None:
        model = load_simulated_assurance_model(MODEL)
        trace = simulate_full_stop(model, initial_speed_mps=6.0)
        expected = 6.0 * model.response_time_s + 6.0**2 / (
            2.0 * model.maximum_service_deceleration_mps2
        )
        self.assertAlmostEqual(trace[-1]["position_m"], expected, places=9)
        self.assertEqual(trace[-1]["speed_mps"], 0.0)
        self.assertTrue(all(item["speed_mps"] >= 0 for item in trace))
        at_delay = next(item for item in trace if item["time_s"] == model.response_time_s)
        self.assertEqual(at_delay["speed_mps"], 6.0)

    def test_invalid_model_value_is_rejected(self) -> None:
        raw = load_json(MODEL)
        raw["parameters"]["maximum_service_deceleration_mps2"] = 0
        with self.assertRaisesRegex(ValueError, "deceleration"):
            load_simulated_assurance_model(raw)


class SimulatedSceneProjectionTest(unittest.TestCase):
    def test_eight_real_fields_plus_simulator_reaches_core_and_z3(self) -> None:
        authored = build_simulated_generation_request(
            base_request=load_json(BASE_REQUEST),
            source_audit=source_audit(),
            association_evidence=association(),
            rule_evidence=rule_evidence(),
            coc_claim_evidence=coc_claim(),
            model_source=MODEL,
            request_id="simulated_scene_01",
        )
        self.assertFalse(authored.real_vehicle_source_complete)
        self.assertTrue(authored.simulation_projection_source_complete)
        self.assertNotEqual(
            authored.recorded_vehicle_binding_key,
            authored.simulation_vehicle_binding_key,
        )
        self.assertEqual(
            authored.request.raw["vehicle_profile"]["evidence_ref"],
            authored.simulation_evidence_ref,
        )
        self.assertEqual(len(authored.request.raw["context_graph"]["coc_claims"]), 1)
        self.assertEqual(
            authored.request.raw["context_graph"]["coc_claims"][0]["evidence_ref"],
            "coc-sha256:" + "d" * 64,
        )
        self.assertEqual(authored.conditional_rule_source_refs, ("RULE-A", "RULE-B"))

        generated = generate_from_request(authored.request)
        self.assertEqual(generated.verdict, "VALIDATED")
        bundle = expand_indexed_collection(generated.collection).bundle
        compiled = compile_core_model(elaborate_bundle(bundle).core_model)
        solved = solve_assignment(
            compiled,
            concrete_scene_t0_assignments(
                source_audit(), association(), contract_count=2
            ),
        )
        self.assertEqual(solved["status"], "SAT")
        symbols = {
            (item["declaration"], item["time"]): item["smt_symbol"]
            for item in compiled.symbol_table["symbols"]
        }
        self.assertEqual(solved["witness"][symbols[("c0__state", 1)]], "ACTIVE")
        self.assertEqual(solved["witness"][symbols[("c1__verdict", 0)]], "VALIDATED")
        self.assertNotIn(
            "RULE-A",
            generated.program_template.raw["predicate"]["evidence_refs"],
        )

        translation = build_reference_translation_cases(
            source_audit=source_audit(),
            association_evidence=association(),
            model_source=MODEL,
            collection=generated.collection.raw,
        )
        self.assertEqual(translation["contract_count"], 2)
        self.assertEqual(translation["canonical_runtime_agreement"], 1.0)
        self.assertEqual(translation["canonical_bounded_target_agreement"], 1.0)
        self.assertTrue(
            all(
                record["canonical"]["lifecycle"] == ["ACTIVE"]
                and record["canonical"]["verdict"] == "VALIDATED"
                and record["canonical"]["violations"] == []
                for record in translation["records"]
            )
        )

    def test_projection_does_not_close_the_recorded_vehicle_gap(self) -> None:
        authored = build_simulated_generation_request(
            base_request=load_json(BASE_REQUEST),
            source_audit=source_audit(),
            association_evidence=association(),
            rule_evidence=rule_evidence(),
            coc_claim_evidence=coc_claim(),
            model_source=MODEL,
            request_id="simulated_scene_01",
        )
        self.assertEqual(
            authored.remaining_real_vehicle_gaps,
            ("source_bearing_vehicle_assurance_profile",),
        )
        self.assertEqual(authored.profile_source_class, "SIMULATION_MODEL_SPECIFICATION")

    def test_projection_rejects_any_additional_scene_gap(self) -> None:
        audit = source_audit()
        audit["missing_fields"].append("verified_coordinate_transform")
        audit["available_fields"].remove("verified_coordinate_transform")
        with self.assertRaisesRegex(SimulationProjectionError, "SCENE_FIELDS_INCOMPLETE"):
            build_simulated_generation_request(
                base_request=load_json(BASE_REQUEST),
                source_audit=audit,
                association_evidence=association(),
                rule_evidence=rule_evidence(),
                coc_claim_evidence=coc_claim(),
                model_source=MODEL,
                request_id="rejected_projection",
            )

    def test_projection_rejects_scene_mismatch(self) -> None:
        evidence = deepcopy(association())
        evidence["scene_ref"] = "different-scene"
        with self.assertRaisesRegex(SimulationProjectionError, "SCENE_REF_MISMATCH"):
            build_simulated_generation_request(
                base_request=load_json(BASE_REQUEST),
                source_audit=source_audit(),
                association_evidence=evidence,
                rule_evidence=rule_evidence(),
                coc_claim_evidence=coc_claim(),
                model_source=MODEL,
                request_id="rejected_projection",
            )

    def test_projection_rejects_exposed_or_unverified_coc_claim(self) -> None:
        exposed = coc_claim()
        exposed["text_included"] = True
        with self.assertRaisesRegex(
            SimulationProjectionError,
            "INVALID_OR_EXPOSED_COC_CLAIM_EVIDENCE",
        ):
            build_simulated_generation_request(
                base_request=load_json(BASE_REQUEST),
                source_audit=source_audit(),
                association_evidence=association(),
                rule_evidence=rule_evidence(),
                coc_claim_evidence=exposed,
                model_source=MODEL,
                request_id="rejected_projection",
            )


class SimulatedSceneInventoryTest(unittest.TestCase):
    def test_inventory_merges_calibration_overlap_and_never_fills_fields(self) -> None:
        packet = {
            "packet_id": "packet-1",
            "selection_hints": {"candidate_slices": ["PEDESTRIAN_CYCLIST_YIELD"]},
            "source_closure": {"missing_fields": [
                "timestamps", "ego_pose_and_speed", "relevant_actor_tracks",
                "target_zone_or_lane_association", "conflict_or_stop_geometry",
                "verified_coordinate_transform", "applicable_rule_source_refs",
                "exact_vehicle_binding", "source_bearing_vehicle_assurance_profile",
            ]},
        }
        candidate = {
            "candidate_id": "event-1",
            "context_graph": {"timestamp_s": 1.0, "ego_speed_mps": 2.0, "zone_entry_x_m": 4.0},
            "ego_state": {"speed_mps": 2.0},
            "association_candidates": [{"track_samples": [{"timestamp_s": 1.0}]}],
            "conflict_zone": {"entry_x_m": 4.0},
        }
        audit = {
            "packet_id": "packet-1",
            "available_fields": list(REQUIRED_SCENE_FIELDS),
            "field_status": {"conflict_or_stop_geometry": {
                "evidence_ref": "restricted-sha256:x#/candidates/0/conflict_zone"
            }},
        }
        result = build_scene_candidate_inventory(
            {"packets": [packet]}, {"candidates": [candidate]}, audit
        )
        self.assertEqual(result["candidate_count"], 1)
        self.assertEqual(result["simulation_projection_ready_count"], 1)
        self.assertFalse(result["raw_identifiers_included"])
        self.assertFalse(result["synthetic_scene_fill_performed"])
        self.assertNotIn("event-1", str(result))

    def test_event_closure_upgrades_matching_adapter_candidate(self) -> None:
        packet = {
            "packet_id": "packet-1",
            "selection_hints": {"candidate_slices": ["PEDESTRIAN_CYCLIST_YIELD"]},
            "source_closure": {"missing_fields": list(REQUIRED_SCENE_FIELDS)},
        }
        candidates = [
            {"candidate_id": "event-1", "context_graph": {}},
            {"candidate_id": "event-2", "context_graph": {}},
        ]
        audit = {
            "packet_id": "packet-1",
            "available_fields": list(REQUIRED_SCENE_FIELDS),
            "field_status": {"conflict_or_stop_geometry": {
                "evidence_ref": "restricted-sha256:x#/candidates/0/conflict_zone"
            }},
        }
        closure = {
            "adapter_candidate_index": 1,
            "available_fields": list(REQUIRED_SCENE_FIELDS),
            "synthesized_required_values": [],
        }
        result = build_scene_candidate_inventory(
            {"packets": [packet]},
            {"candidates": candidates},
            audit,
            event_closures=[closure],
        )
        self.assertEqual(result["candidate_count"], 2)
        self.assertEqual(result["simulation_projection_ready_count"], 2)
        self.assertTrue(
            any(
                "DERIVED_EVENT_SOURCE_CLOSURE" in item["evidence_classes"]
                for item in result["candidates"]
            )
        )


class Sim24BatchTest(unittest.TestCase):
    def test_shortfall_is_terminal_decision_not_24_scene_success(self) -> None:
        inventory = {
            "candidate_count": 3,
            "simulation_projection_ready_count": 2,
            "synthetic_scene_fill_performed": False,
            "candidates": [
                {"candidate_ref": "c1", "simulation_projection_ready": True,
                 "missing_scene_fields": []},
                {"candidate_ref": "c2", "simulation_projection_ready": True,
                 "missing_scene_fields": []},
                {"candidate_ref": "c3", "simulation_projection_ready": False,
                 "missing_scene_fields": ["timestamps"]},
            ],
        }
        closures = [
            {"scene_ref": "s1", "available_fields": list(REQUIRED_SCENE_FIELDS),
             "missing_fields": ["source_bearing_vehicle_assurance_profile"],
             "synthesized_required_values": []},
            {"scene_ref": "s2", "available_fields": list(REQUIRED_SCENE_FIELDS),
             "missing_fields": ["source_bearing_vehicle_assurance_profile"],
             "synthesized_required_values": []},
        ]
        executions = []
        for scene_ref in ("s1", "s2"):
            executions.append({
                "result": {
                    "scene_ref": scene_ref,
                    "status": "EXECUTED",
                    "contract_count": 1,
                    "gates": {"distinct_vehicle_bindings": True},
                    "canonical_runtime_recorded_frame_agreement": 1.0,
                    "canonical_bounded_recorded_frame_agreement": 1.0,
                    "canonical_core_recorded_frame_agreement": 1.0,
                    "z3_query_agreement": 1.0,
                    "direct_z3_smtlib_replay_agreement": 1.0,
                },
                "translation": {"trace_count": 1},
            })
        batch = build_sim24_terminal_batch(
            inventory=inventory,
            closures=closures,
            executions=executions,
            target_scene_count=24,
        )
        self.assertEqual(batch["BATCH_RESULT.json"]["executed_scene_count"], 2)
        self.assertFalse(batch["BATCH_RESULT.json"]["empirical_24_scene_gate_passed"])
        self.assertTrue(batch["BATCH_RESULT.json"]["terminal_condition_met"])
        self.assertEqual(batch["ABSTENTION_RESULTS.json"]["total_shortfall"], 22)
        self.assertEqual(batch["ABSTENTION_RESULTS.json"]["inventoried_unready"], 1)
        self.assertEqual(batch["ABSTENTION_RESULTS.json"]["absent_candidate_slots"], 21)


class SimulatedSceneEvidenceTest(unittest.TestCase):
    def _candidate(self) -> dict:
        actors = []
        for track in ("a" * 64, "b" * 64):
            actors.append({
                "track_id_sha256": track,
                "label_class": "person",
                "track_samples": [{
                    "timestamp_us": 1_000_000,
                    "center_x_m": 12.0,
                    "center_y_m": 0.0,
                    "half_extent_x_m": 0.5,
                    "half_extent_y_m": 0.5,
                }],
            })
        return {
            "candidate_id": "scene-01",
            "clip_id_sha256": "e" * 64,
            "raw_clip_id_included": False,
            "context_schema_valid": True,
            "context_graph": {"timestamp_s": 1.0},
            "ego_state": {
                "pose_relative_t0_m": [1.0, 0.0, 0.0],
                "speed_mps": 3.0,
                "relative_time_s": 1.0,
                "derivation": "RECORDED_FUTURE",
            },
            "association_candidates": actors,
        }

    def _association(self, candidate: dict) -> dict:
        return build_geometric_set_association(
            scene_ref="scene-01",
            event_timestamp_us=1_000_000,
            candidates=candidate["association_candidates"],
            ego_half_width_m=1.0,
            ego_front_extent_m=4.0,
            evidence_refs=["restricted-sha256:actors#/event"],
        )

    def _source_bundle(self) -> dict:
        return {
            "source_bundle_version": "guardsynth-nvidia-scene-source-bundle-v0.1",
            "scene_ref": "scene-01",
            "clip_id_sha256": "e" * 64,
            "coordinate_transform": {
                "status": "AVAILABLE_SOURCE_LINKED",
                "source_frame": "dataset_rig_at_event",
                "target_frame": "ego_at_model_t0",
                "event_timestamp_us": 1_000_000,
                "matrix_4x4": [
                    [1.0, 0.0, 0.0, 1.0],
                    [0.0, 1.0, 0.0, 0.0],
                    [0.0, 0.0, 1.0, 0.0],
                    [0.0, 0.0, 0.0, 1.0],
                ],
                "inverse_closure_max_abs_error": 0.0,
            },
            "vehicle_binding": {
                "status": "AVAILABLE_SOURCE_LINKED",
                "vehicle_binding_key": "nvidia-rig-config-sha256:" + "f" * 64,
                "binding_scope": "DATASET_CLIP_RIG_CONFIGURATION_NOT_VIN",
                "components": {"clip_id_sha256": "e" * 64},
            },
        }

    def test_event_closure_has_eight_fields_and_preserves_vehicle_gap(self) -> None:
        candidate = self._candidate()
        association = self._association(candidate)
        applicability = build_system_requirement_applicability(
            scene_ref="scene-01",
            association=association,
            requirement_path=REQUIREMENT,
        )
        closure = build_event_scene_source_closure(
            scene_ref="scene-01",
            adapter_candidate=candidate,
            adapter_candidate_index=0,
            adapter_sha256="1" * 64,
            source_bundle=self._source_bundle(),
            source_bundle_sha256="2" * 64,
            association=association,
            association_sha256="3" * 64,
            applicability=applicability,
            applicability_sha256="4" * 64,
        )
        self.assertEqual(len(closure["available_fields"]), 8)
        self.assertEqual(
            closure["missing_fields"],
            ["source_bearing_vehicle_assurance_profile"],
        )
        self.assertTrue(closure["simulation_projection_allowed"])
        self.assertFalse(closure["source_complete"])
        self.assertFalse(closure["legal_authority_claimed"])
        self.assertEqual(closure["synthesized_required_values"], [])

    def test_event_closure_rejects_wrong_event_transform(self) -> None:
        candidate = self._candidate()
        association = self._association(candidate)
        applicability = build_system_requirement_applicability(
            scene_ref="scene-01",
            association=association,
            requirement_path=REQUIREMENT,
        )
        bundle = self._source_bundle()
        bundle["coordinate_transform"]["event_timestamp_us"] += 1
        with self.assertRaisesRegex(ValueError, "SOURCE_BUNDLE_SCENE_OR_CLIP_MISMATCH"):
            build_event_scene_source_closure(
                scene_ref="scene-01",
                adapter_candidate=candidate,
                adapter_candidate_index=0,
                adapter_sha256="1" * 64,
                source_bundle=bundle,
                source_bundle_sha256="2" * 64,
                association=association,
                association_sha256="3" * 64,
                applicability=applicability,
                applicability_sha256="4" * 64,
            )


if __name__ == "__main__":
    unittest.main()
