"""TDD contract for label-light GuardSynth grounding."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import json
import sys
import unittest


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from guard_synth.label_light_grounding import (
    LabelLightValidationError,
    ReviewDecision,
    aggregate_label_light_metrics,
    apply_review_decision,
    assess_legacy_adapter_label_light,
    parse_label_light_packet,
    triage_label_light_packet,
)
from guard_synth.assurance_registry import parse_assurance_registry
from guard_synth.source_authoring import author_generation_request
from guard_synth.source_aware_generator import generate_from_request, parse_generation_request
from guard_synth_eblc.schema_validation import load_json


FIXTURE = ROOT / "src/guard_synth/fixtures/label_light_grounding_packet_v0_1.json"
REQUEST = ROOT / "src/guard_synth/fixtures/source_aware_generation_request_p0b_v0_1.json"


def packet_raw() -> dict:
    return load_json(FIXTURE)


def registry_raw() -> dict:
    return {
        "registry_version": "guardsynth-vehicle-assurance-registry-v0.1",
        "registry_id": "label_light_test_registry",
        "profiles": [{
            "profile_id": "label_light_test_profile",
            "vehicle_binding_key": "vehicle:test-platform",
            "maximum_service_deceleration_mps2": 3.0,
            "response_time_s": 0.5,
            "position_uncertainty_m": 0.5,
            "evidence": {
                "evidence_ref": "TEST-VEHICLE-ASSURANCE-v1",
                "source_class": "CONTROLLED_TEST_REPORT",
                "uri": "urn:test:vehicle-assurance:v1",
                "version": "1",
                "sha256": "d" * 64,
                "scope": "SYNTHETIC_TEST_ONLY_NOT_REAL_VEHICLE_ASSURANCE",
            },
        }],
    }


def second_packet() -> dict:
    raw = packet_raw()
    raw["packet_id"] = "label_light_scene_002"
    raw["scene_ref"] = "synthetic-scene:002"
    raw["hazard"]["evidence_ref"] = "OBS-002"
    raw["targets"][0].update({"target_entity_id": "pedestrian:P18", "track_evidence_ref": "TRACK-002"})
    raw["zones"][0].update({
        "zone_id": "zone:Z5", "geometry_evidence_ref": "GEOMETRY-002",
        "transform_evidence_ref": "TRANSFORM-002", "entry_x_m": 12.0,
    })
    raw["pair_candidates"][0].update({
        "target_entity_id": "pedestrian:P18", "zone_id": "zone:Z5",
        "association_evidence_ref": "ASSOC-002",
    })
    raw["source_refs"].extend(["OBS-002", "TRACK-002", "GEOMETRY-002", "TRANSFORM-002", "ASSOC-002"])
    return raw


class LabelLightTriageTest(unittest.TestCase):
    def test_unique_calibrated_candidate_is_auto_confirmed(self) -> None:
        result = triage_label_light_packet(parse_label_light_packet(packet_raw()))
        self.assertEqual(result.association_status, "AUTO_CONFIRMED")
        self.assertEqual(result.contract_readiness, "SOURCE_AUTHORED_PENDING_ASSURANCE_LOOKUP")
        self.assertIsNotNone(result.grounded_scene)
        self.assertIsNone(result.review_task)

    def test_auto_confirmation_can_be_disabled_by_policy(self) -> None:
        raw = packet_raw()
        raw["policy"]["auto_confirm_enabled"] = False
        result = triage_label_light_packet(parse_label_light_packet(raw))
        self.assertEqual(result.association_status, "REVIEW_REQUIRED")
        self.assertEqual(result.review_task["estimated_interactions"], 1)

    def test_low_confidence_and_multiple_candidates_require_review(self) -> None:
        low = packet_raw()
        low["pair_candidates"][0]["confidence_lower_bound"] = 0.7
        low_result = triage_label_light_packet(parse_label_light_packet(low))
        self.assertEqual(low_result.association_status, "REVIEW_REQUIRED")
        multi = packet_raw()
        multi["targets"].append({
            "target_entity_id": "pedestrian:P19", "classification": "PEDESTRIAN",
            "track_evidence_ref": "TRACK-019",
        })
        multi["pair_candidates"].append({
            "target_entity_id": "pedestrian:P19", "zone_id": "zone:Z4",
            "path_intersection": "TRUE", "association_evidence_ref": "ASSOC-019",
            "confidence_lower_bound": 0.96, "confidence_upper_bound": 0.99,
            "calibration_evidence_ref": "CALIBRATION-001",
        })
        multi["source_refs"].extend(["TRACK-019", "ASSOC-019"])
        multi_result = triage_label_light_packet(parse_label_light_packet(multi))
        self.assertEqual(multi_result.association_status, "REVIEW_REQUIRED")
        self.assertEqual(len(multi_result.review_task["candidate_pairs"]), 2)

    def test_missing_geometry_transform_or_calibration_is_unsupported(self) -> None:
        mutations = (
            lambda raw: raw["zones"][0].update(geometry_evidence_ref=""),
            lambda raw: raw["zones"][0].update(transform_verified=False),
            lambda raw: raw["pair_candidates"][0].update(calibration_evidence_ref=""),
        )
        for mutate in mutations:
            raw = packet_raw()
            mutate(raw)
            with self.subTest(mutation=mutate):
                result = triage_label_light_packet(parse_label_light_packet(raw))
                self.assertEqual(result.association_status, "UNSUPPORTED")
                self.assertIsNone(result.grounded_scene)

    def test_claimed_hazard_cannot_auto_confirm_and_conflict_is_preserved(self) -> None:
        claimed = packet_raw()
        claimed["hazard"]["epistemic_kind"] = "CLAIMED"
        result = triage_label_light_packet(parse_label_light_packet(claimed))
        self.assertEqual(result.association_status, "REVIEW_REQUIRED")
        conflict = packet_raw()
        conflict["hazard"]["truth"] = "CONFLICT"
        conflict_result = triage_label_light_packet(parse_label_light_packet(conflict))
        self.assertEqual(conflict_result.association_status, "CONFLICT")

    def test_stale_or_future_hazard_requires_review_with_explicit_reason(self) -> None:
        stale = packet_raw()
        stale["timestamp_s"] = 1.0
        stale_result = triage_label_light_packet(parse_label_light_packet(stale))
        self.assertEqual(stale_result.association_status, "REVIEW_REQUIRED")
        self.assertIn("STALE_HAZARD_EVIDENCE", stale_result.reason_codes)
        future = packet_raw()
        future["hazard"]["timestamp_s"] = 1.0
        future_result = triage_label_light_packet(parse_label_light_packet(future))
        self.assertIn("FUTURE_HAZARD_EVIDENCE", future_result.reason_codes)

    def test_unknown_evidence_reference_is_rejected(self) -> None:
        raw = packet_raw()
        raw["pair_candidates"][0]["association_evidence_ref"] = "UNKNOWN-EVIDENCE"
        with self.assertRaisesRegex(LabelLightValidationError, "unknown evidence"):
            parse_label_light_packet(raw)


class MinimalReviewTest(unittest.TestCase):
    def review_result(self):
        raw = packet_raw()
        raw["policy"]["auto_confirm_enabled"] = False
        packet = parse_label_light_packet(raw)
        return packet, triage_label_light_packet(packet)

    def test_one_click_confirmation_produces_grounded_scene_with_review_evidence(self) -> None:
        packet, triage = self.review_result()
        result = apply_review_decision(packet, triage, ReviewDecision(
            decision="CONFIRM_PROPOSAL", selected_target_entity_id=None,
            selected_zone_id=None, reviewer_evidence_ref="REVIEW-001",
        ))
        self.assertEqual(result.association_status, "HUMAN_CONFIRMED")
        self.assertIn("REVIEW-001", result.grounded_scene["association"]["evidence_refs"])

    def test_selecting_an_alternative_is_counted_as_correction(self) -> None:
        raw = packet_raw()
        raw["policy"]["auto_confirm_enabled"] = False
        raw["targets"].append({
            "target_entity_id": "pedestrian:P19", "classification": "PEDESTRIAN",
            "track_evidence_ref": "TRACK-019",
        })
        raw["pair_candidates"].append({
            "target_entity_id": "pedestrian:P19", "zone_id": "zone:Z4",
            "path_intersection": "TRUE", "association_evidence_ref": "ASSOC-019",
            "confidence_lower_bound": 0.7, "confidence_upper_bound": 0.8,
            "calibration_evidence_ref": "CALIBRATION-001",
        })
        raw["source_refs"].extend(["TRACK-019", "ASSOC-019"])
        packet = parse_label_light_packet(raw)
        triage = triage_label_light_packet(packet)
        result = apply_review_decision(packet, triage, ReviewDecision(
            decision="SELECT_PAIR", selected_target_entity_id="pedestrian:P19",
            selected_zone_id="zone:Z4", reviewer_evidence_ref="REVIEW-002",
        ))
        self.assertTrue(result.human_correction)
        self.assertEqual(result.grounded_scene["association"]["target_entity_id"], "pedestrian:P19")

    def test_invalid_selection_fails_and_ambiguous_decision_generates_no_scene(self) -> None:
        packet, triage = self.review_result()
        with self.assertRaisesRegex(LabelLightValidationError, "candidate"):
            apply_review_decision(packet, triage, ReviewDecision(
                decision="SELECT_PAIR", selected_target_entity_id="not-a-candidate",
                selected_zone_id="zone:Z4", reviewer_evidence_ref="REVIEW-003",
            ))
        ambiguous = apply_review_decision(packet, triage, ReviewDecision(
            decision="MARK_AMBIGUOUS", selected_target_entity_id=None,
            selected_zone_id=None, reviewer_evidence_ref="REVIEW-004",
        ))
        self.assertEqual(ambiguous.association_status, "REVIEW_REQUIRED")
        self.assertIsNone(ambiguous.grounded_scene)

    def test_association_confirmation_does_not_upgrade_claimed_hazard(self) -> None:
        raw = packet_raw()
        raw["hazard"]["epistemic_kind"] = "CLAIMED"
        packet = parse_label_light_packet(raw)
        triage = triage_label_light_packet(packet)
        result = apply_review_decision(packet, triage, ReviewDecision(
            decision="CONFIRM_PROPOSAL", selected_target_entity_id=None,
            selected_zone_id=None, reviewer_evidence_ref="REVIEW-CLAIM-001",
        ))
        self.assertEqual(result.association_status, "HUMAN_CONFIRMED")
        self.assertEqual(result.contract_readiness, "HAZARD_REVIEW_REQUIRED")
        self.assertIsNone(result.grounded_scene)
        self.assertIn("COC_CLAIM_NOT_OBSERVED_FACT", result.reason_codes)


class LabelLightIntegrationAndMetricsTest(unittest.TestCase):
    def test_two_auto_confirmed_scenes_reach_existing_generator(self) -> None:
        scenes = []
        for raw in (packet_raw(), second_packet()):
            triage = triage_label_light_packet(parse_label_light_packet(raw))
            scenes.append(triage.grounded_scene)
        request = author_generation_request(
            base_request=load_json(REQUEST), grounded_scenes=scenes,
            registry=parse_assurance_registry(registry_raw()),
            request_id="label_light_two_scene_request",
        )
        result = generate_from_request(parse_generation_request(request))
        self.assertEqual(result.verdict, "VALIDATED")
        self.assertEqual(len(result.collection.instances), 2)

    def test_human_review_evidence_reaches_generated_request(self) -> None:
        review_raw = packet_raw()
        review_raw["policy"]["auto_confirm_enabled"] = False
        packet = parse_label_light_packet(review_raw)
        reviewed = apply_review_decision(
            packet,
            triage_label_light_packet(packet),
            ReviewDecision(
                decision="CONFIRM_PROPOSAL",
                selected_target_entity_id=None,
                selected_zone_id=None,
                reviewer_evidence_ref="REVIEW-006",
            ),
        )
        automatic = triage_label_light_packet(parse_label_light_packet(second_packet()))
        request = author_generation_request(
            base_request=load_json(REQUEST),
            grounded_scenes=[reviewed.grounded_scene, automatic.grounded_scene],
            registry=parse_assurance_registry(registry_raw()),
            request_id="label_light_review_provenance_request",
        )
        self.assertIn("REVIEW-006", request["source_refs"])
        self.assertIn(
            "REVIEW-006",
            request["context_graph"]["instances"][0]["association"]["evidence_refs"],
        )

    def test_metrics_separate_automation_review_unsupported_and_correction(self) -> None:
        auto = triage_label_light_packet(parse_label_light_packet(packet_raw()))
        review_raw = packet_raw()
        review_raw["policy"]["auto_confirm_enabled"] = False
        packet = parse_label_light_packet(review_raw)
        review = triage_label_light_packet(packet)
        corrected = apply_review_decision(packet, review, ReviewDecision(
            decision="CONFIRM_PROPOSAL", selected_target_entity_id=None,
            selected_zone_id=None, reviewer_evidence_ref="REVIEW-005",
        ))
        unsupported_raw = packet_raw()
        unsupported_raw["zones"][0]["transform_verified"] = False
        unsupported = triage_label_light_packet(parse_label_light_packet(unsupported_raw))
        metrics = aggregate_label_light_metrics([auto, review, corrected, unsupported])
        self.assertEqual(metrics["total"], 4)
        self.assertEqual(metrics["auto_confirmed"], 1)
        self.assertEqual(metrics["review_required"], 1)
        self.assertEqual(metrics["human_confirmed"], 1)
        self.assertEqual(metrics["unsupported"], 1)
        self.assertEqual(metrics["human_corrections"], 0)

    def test_current_restricted_adapter_is_aggregated_without_identifiers(self) -> None:
        path = ROOT / "artifacts/results/restricted/eblc-p0b-001/p0b-restricted-grounding-multiview-2026-08-08-v1/ADAPTER_RESULT.json"
        if not path.is_file():
            self.skipTest("restricted adapter result is absent")
        result = assess_legacy_adapter_label_light(load_json(path), target_slots=24)
        self.assertEqual(result["candidate_event_count"], 5)
        self.assertEqual(result["association_review_required_count"], 4)
        self.assertEqual(result["auto_confirmed_count"], 0)
        self.assertEqual(result["contract_blocked_count"], 4)
        self.assertNotIn("clip_id", json.dumps(result))
        self.assertNotIn("candidate_id", json.dumps(result))


if __name__ == "__main__":
    unittest.main()
