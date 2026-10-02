from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest


ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "PROJECT_REGISTRY.json").is_file())
TEST_ROOT = ROOT / "projects/04-guardsynth-coc/tests"
if str(TEST_ROOT) not in sys.path:
    sys.path.insert(0, str(TEST_ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from guard_synth.label_light_grounding import convert_image_review_export
from guard_synth.scene_source_closure import audit_calibration_scene_source
from fixtures.review_exports import image_review_export


class CalibrationSceneSourceAuditTest(unittest.TestCase):
    def _fixture(self, root: Path) -> tuple[dict, dict, Path]:
        image = root / "source" / "scene-001.jpg"
        image.parent.mkdir()
        image.write_bytes(b"restricted-derived-image")
        image_sha = hashlib.sha256(image.read_bytes()).hexdigest()
        sidecar = [{
            "image": image.name,
            "absolute_timestamps_us": [1000000, 1100000],
            "relative_times_s": [0.0, 0.1],
            "camera_order": ["front", "front"],
            "dataset_revision": "test-revision",
            "episode": "test-episode",
            "publication_control": "LICENSE_RESTRICTED",
            "source": "derived-test",
        }]
        (image.parent / "media-manifest.json").write_text(json.dumps(sidecar))
        embedded = {
            "input_class": "LICENSE_RESTRICTED",
            "images": [{
                "filename": image.name,
                "sha256": image_sha,
                "byte_count": image.stat().st_size,
                "mime_type": "image/jpeg",
            }],
        }
        packet = convert_image_review_export(image_review_export(), "a" * 64)[0]
        return packet, embedded, root

    def test_hash_linked_sidecar_recovers_only_sourced_timestamps(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            packet, embedded, source_root = self._fixture(Path(tmp))
            audit = audit_calibration_scene_source(packet, embedded, source_root)

        self.assertEqual(audit["field_status"]["timestamps"]["status"], "AVAILABLE_SOURCE_LINKED")
        self.assertEqual(audit["field_status"]["timestamps"]["values_us"], [1000000, 1100000])
        self.assertEqual(len(audit["missing_fields"]), 8)
        self.assertFalse(audit["source_complete"])
        self.assertFalse(audit["contract_generation_allowed"])
        self.assertEqual(audit["synthesized_required_values"], [])
        self.assertFalse(audit["raw_source_paths_included"])

    def test_multicamera_timestamp_matrix_is_preserved(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            packet, embedded, source_root = self._fixture(Path(tmp))
            sidecar = source_root / "source" / "media-manifest.json"
            raw = json.loads(sidecar.read_text())
            raw[0]["absolute_timestamps_us"] = [
                [1000000, 1000001],
                [1100000, 1100001],
            ]
            raw[0]["camera_order"] = ["front", "side"]
            sidecar.write_text(json.dumps(raw))

            audit = audit_calibration_scene_source(packet, embedded, source_root)

        self.assertEqual(audit["field_status"]["timestamps"]["status"], "AVAILABLE_SOURCE_LINKED")
        self.assertEqual(
            audit["field_status"]["timestamps"]["values_us"],
            [[1000000, 1000001], [1100000, 1100001]],
        )

    def test_unique_derived_adapter_event_adds_ego_and_geometry_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            packet, embedded, source_root = self._fixture(Path(tmp))
            adapter = {
                "candidates": [{
                    "candidate_id": "test-episode-event-00",
                    "context_schema_valid": True,
                    "ego_state": {
                        "pose_relative_t0_m": [1.0, 0.0, 0.0],
                        "speed_mps": 2.0,
                        "relative_time_s": 0.5,
                        "derivation": "RECORDED_FUTURE_LINEAR_INTERPOLATION_AND_FINITE_DIFFERENCE",
                    },
                    "conflict_zone": {
                        "kind": "DYNAMIC_VRU_OCCUPANCY_NEAR_BOUNDARY_1D",
                        "entry_x_m": 5.0,
                        "lateral_center_m": 0.2,
                        "source_fields": ["recorded.field"],
                        "crosswalk_or_legal_zone_claimed": False,
                    },
                    "target_binding": {
                        "verdict": "REVIEW_REQUIRED",
                        "ambiguity_reason": "MULTIPLE_FORWARD_CORRIDOR_CANDIDATES",
                        "candidate_count": 2,
                        "track_id_sha256": "d" * 64,
                    },
                }],
            }
            audit = audit_calibration_scene_source(
                packet,
                embedded,
                source_root,
                adapter_result=adapter,
                adapter_document_sha256="b" * 64,
            )

        self.assertEqual(
            audit["available_fields"],
            ["timestamps", "ego_pose_and_speed", "conflict_or_stop_geometry"],
        )
        self.assertEqual(len(audit["missing_fields"]), 6)
        self.assertIn("target_zone_or_lane_association", audit["missing_fields"])
        self.assertEqual(
            audit["association_readiness"]["declared_candidate_count"], 2
        )
        self.assertEqual(
            audit["association_readiness"]["serialized_candidate_record_count"], 1
        )
        self.assertFalse(audit["association_readiness"]["all_candidates_preserved"])
        self.assertFalse(audit["association_readiness"]["review_ui_allowed"])
        self.assertEqual(
            audit["association_readiness"]["reason_code"],
            "ALL_ACTOR_CANDIDATES_NOT_PRESERVED",
        )
        self.assertFalse(audit["contract_generation_allowed"])

    def test_multiple_adapter_events_are_not_silently_selected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            packet, embedded, source_root = self._fixture(Path(tmp))
            adapter = {"candidates": [
                {"candidate_id": "test-episode-event-00"},
                {"candidate_id": "test-episode-event-01"},
            ]}
            audit = audit_calibration_scene_source(
                packet,
                embedded,
                source_root,
                adapter_result=adapter,
                adapter_document_sha256="c" * 64,
            )

        self.assertEqual(audit["available_fields"], ["timestamps"])
        self.assertIn("AMBIGUOUS_DERIVED_ADAPTER_EVENT", audit["reason_codes"])

    def test_complete_candidate_set_enables_review_but_does_not_validate_binding(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            packet, embedded, source_root = self._fixture(Path(tmp))
            adapter = {
                "candidates": [{
                    "candidate_id": "test-episode-event-00",
                    "target_binding": {
                        "candidate_count": 2,
                        "track_id_sha256": "e" * 64,
                    },
                    "association_candidates": [
                        {
                            "track_id_sha256": value * 64,
                            "track_samples": [{"timestamp_us": 1}],
                        }
                        for value in ("e", "f")
                    ],
                }],
            }
            audit = audit_calibration_scene_source(
                packet,
                embedded,
                source_root,
                adapter_result=adapter,
                adapter_document_sha256="a" * 64,
            )

        self.assertTrue(audit["association_readiness"]["review_ui_allowed"])
        self.assertTrue(audit["association_readiness"]["all_candidates_preserved"])
        self.assertEqual(
            audit["field_status"]["relevant_actor_tracks"]["status"],
            "AVAILABLE_SOURCE_LINKED",
        )
        self.assertEqual(
            audit["field_status"]["relevant_actor_tracks"]["candidate_count"], 2
        )
        self.assertEqual(
            audit["field_status"]["relevant_actor_tracks"]["identity_form"],
            "SHA256",
        )
        self.assertIn("relevant_actor_tracks", audit["available_fields"])
        self.assertIn("target_zone_or_lane_association", audit["missing_fields"])
        self.assertFalse(audit["contract_generation_allowed"])

    def test_source_bundle_adds_transform_and_clip_rig_binding_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            packet, embedded, source_root = self._fixture(Path(tmp))
            bundle = {
                "source_bundle_version": "guardsynth-nvidia-scene-source-bundle-v0.1",
                "scene_ref": packet["scene_ref"],
                "coordinate_transform": {
                    "status": "AVAILABLE_SOURCE_LINKED",
                    "source_frame": "dataset_rig_at_event",
                    "target_frame": "ego_at_model_t0",
                    "matrix_4x4": [
                        [1.0, 0.0, 0.0, 1.0],
                        [0.0, 1.0, 0.0, 0.0],
                        [0.0, 0.0, 1.0, 0.0],
                        [0.0, 0.0, 0.0, 1.0],
                    ],
                    "inverse_closure_max_abs_error": 0.0,
                    "evidence_refs": ["dataset:egomotion", "devkit:frame-semantics"],
                },
                "vehicle_binding": {
                    "status": "AVAILABLE_SOURCE_LINKED",
                    "vehicle_binding_key": "nvidia-rig-config-sha256:" + "a" * 64,
                    "binding_scope": "DATASET_CLIP_RIG_CONFIGURATION_NOT_VIN",
                    "evidence_refs": ["dataset:metadata", "dataset:calibration"],
                },
            }
            audit = audit_calibration_scene_source(
                packet,
                embedded,
                source_root,
                scene_source_bundle=bundle,
                scene_source_bundle_sha256="f" * 64,
            )

        self.assertEqual(
            audit["field_status"]["verified_coordinate_transform"]["status"],
            "AVAILABLE_SOURCE_LINKED",
        )
        self.assertEqual(
            audit["field_status"]["exact_vehicle_binding"]["status"],
            "AVAILABLE_SOURCE_LINKED",
        )
        self.assertIn("applicable_rule_source_refs", audit["missing_fields"])
        self.assertIn("source_bearing_vehicle_assurance_profile", audit["missing_fields"])

    def test_source_linked_geometric_set_association_closes_association_field(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            packet, embedded, source_root = self._fixture(Path(tmp))
            association = {
                "association_version": "guardsynth-geometric-set-association-v0.1",
                "scene_ref": packet["scene_ref"],
                "status": "AVAILABLE_SOURCE_LINKED",
                "target_kind": "SET",
                "association_cardinality": 2,
                "associated_track_id_sha256": ["a" * 64, "b" * 64],
                "association_method": "OBSERVED_ORIENTED_BBOX_EGO_CORRIDOR_OVERLAP",
                "zone": {
                    "kind": "DYNAMIC_MULTI_ACTOR_EGO_CORRIDOR_OVERLAP",
                    "coordinate_frame": "dataset_rig",
                    "x_interval_m": [9.0, 12.0],
                    "y_interval_m": [-1.0, 1.0],
                    "time_interval_us": [1_000_000, 1_200_000],
                },
                "evidence_refs": ["restricted-sha256:" + "c" * 64 + "#/event"],
                "crosswalk_or_legal_zone_claimed": False,
                "collision_prediction_claimed": False,
            }
            audit = audit_calibration_scene_source(
                packet,
                embedded,
                source_root,
                association_evidence=association,
                association_evidence_sha256="d" * 64,
            )

        self.assertEqual(
            audit["field_status"]["target_zone_or_lane_association"]["status"],
            "AVAILABLE_SOURCE_LINKED",
        )
        self.assertIn("target_zone_or_lane_association", audit["available_fields"])
        self.assertNotIn("target_zone_or_lane_association", audit["missing_fields"])
        self.assertEqual(
            audit["field_status"]["target_zone_or_lane_association"][
                "association_cardinality"
            ],
            2,
        )

    def test_source_linked_rule_applicability_closes_rule_source_field(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            packet, embedded, source_root = self._fixture(Path(tmp))
            evidence = {
                "rule_applicability_version": "guardsynth-rule-applicability-v0.1",
                "scene_ref": packet["scene_ref"],
                "status": "AVAILABLE_SOURCE_LINKED",
                "applicability_verdict": "CONDITIONALLY_APPLICABLE",
                "primary_rule_source_id": "CA-VEH-21950",
                "jurisdiction_binding": {
                    "country": "United States",
                    "administrative_area": "California",
                    "locality": "San Francisco",
                    "status": "INFERRED_HIGH_CONFIDENCE_NOT_DATASET_GPS",
                    "independent_dataset_gps_confirmation": False,
                },
                "rule_source_refs": [{
                    "source_id": "CA-VEH-21950",
                    "authority": "California Legislature",
                    "jurisdiction": "California",
                    "section": "Vehicle Code 21950",
                    "official_url": "https://leginfo.legislature.ca.gov/example",
                    "snapshot_sha256": "a" * 64,
                    "role": "PRIMARY_CROSSWALK_YIELD_DUE_CARE",
                }],
                "observed_applicability_conditions": [
                    "HUMAN_REVIEWED_CROSSWALK_VISIBLE",
                    "SOURCE_LINKED_ACTOR_SET_IN_EGO_CORRIDOR",
                ],
                "unsourced_normative_or_numeric_value_count": 0,
                "vehicle_safety_validated": False,
            }
            audit = audit_calibration_scene_source(
                packet,
                embedded,
                source_root,
                rule_applicability_evidence=evidence,
                rule_applicability_evidence_sha256="b" * 64,
            )

        self.assertEqual(
            audit["field_status"]["applicable_rule_source_refs"]["status"],
            "AVAILABLE_SOURCE_LINKED",
        )
        self.assertIn("applicable_rule_source_refs", audit["available_fields"])
        self.assertNotIn("applicable_rule_source_refs", audit["missing_fields"])
        self.assertFalse(
            audit["field_status"]["applicable_rule_source_refs"][
                "independent_dataset_gps_confirmation"
            ]
        )

    def test_duplicate_hash_matches_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            packet, embedded, source_root = self._fixture(Path(tmp))
            duplicate = source_root / "copy" / "scene-001.jpg"
            duplicate.parent.mkdir()
            duplicate.write_bytes(b"restricted-derived-image")
            audit = audit_calibration_scene_source(packet, embedded, source_root)

        self.assertEqual(audit["field_status"]["timestamps"]["status"], "REVIEW_REQUIRED")
        self.assertIn("AMBIGUOUS_HASH_LINKED_IMAGE_SOURCE", audit["reason_codes"])
        self.assertEqual(len(audit["missing_fields"]), 9)

    def test_missing_or_invalid_timestamp_sidecar_is_not_filled(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            packet, embedded, source_root = self._fixture(Path(tmp))
            sidecar = source_root / "source" / "media-manifest.json"
            raw = json.loads(sidecar.read_text())
            del raw[0]["absolute_timestamps_us"]
            sidecar.write_text(json.dumps(raw))
            audit = audit_calibration_scene_source(packet, embedded, source_root)

        self.assertEqual(audit["field_status"]["timestamps"]["status"], "REVIEW_REQUIRED")
        self.assertIn("MISSING_VALID_TIMESTAMP_SIDECAR", audit["reason_codes"])
        self.assertNotIn("values_us", audit["field_status"]["timestamps"])

    def test_manifest_filename_mismatch_is_not_hash_inferred_to_another_scene(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            packet, embedded, source_root = self._fixture(Path(tmp))
            wrong = deepcopy(embedded)
            wrong["images"][0]["filename"] = "another-scene.jpg"
            audit = audit_calibration_scene_source(packet, wrong, source_root)

        self.assertIn("MISSING_EMBEDDED_IMAGE_PROVENANCE", audit["reason_codes"])
        self.assertEqual(len(audit["missing_fields"]), 9)


if __name__ == "__main__":
    unittest.main()
