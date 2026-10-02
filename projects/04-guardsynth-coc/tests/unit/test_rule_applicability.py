from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys
import unittest


ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "PROJECT_REGISTRY.json").is_file())
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from guard_synth.rule_applicability import build_rule_applicability_evidence


def packet() -> dict:
    return {
        "scene_ref": "scene-001",
        "observations": {
            "candidate_region": "CROSSWALK_VISIBLE",
            "primary_situation": "ROAD_USER_IN_EGO_PATH",
            "subject_region_relation": "IN_CONFLICT_REGION",
            "review_confidence": "HIGH",
            "visual_hazard": "TRUE",
        },
        "review_evidence": {
            "evidence_kind": "HUMAN_REVIEWED_IMAGE_CLAIM",
            "evidence_ref": "image-review:test",
        },
    }


def association() -> dict:
    return {
        "scene_ref": "scene-001",
        "status": "AVAILABLE_SOURCE_LINKED",
        "target_kind": "SET",
        "association_cardinality": 2,
        "associated_track_id_sha256": ["a" * 64, "b" * 64],
        "evidence_refs": ["restricted-sha256:" + "c" * 64 + "#/event"],
    }


def localization(status: str = "INFERRED_HIGH_CONFIDENCE_NOT_DATASET_GPS") -> dict:
    return {
        "status": status,
        "country": "United States",
        "administrative_area": "California",
        "locality": "San Francisco",
        "intersection_hypothesis": "Hyde St & Lombard St",
        "method": "IMAGE_CUES_CORROBORATED_BY_OFFICIAL_TRANSPORT_AND_MUNICIPAL_SOURCES",
        "evidence_refs": ["restricted-image-sha256:" + "d" * 64, "https://www.sfmta.com/x"],
        "independent_dataset_gps_confirmation": False,
    }


def sources() -> list[dict]:
    return [
        {
            "source_id": "CA-VEH-21950",
            "authority": "California Legislature",
            "jurisdiction": "California",
            "section": "Vehicle Code 21950",
            "official_url": "https://leginfo.legislature.ca.gov/example-21950",
            "snapshot_sha256": "e" * 64,
            "role": "PRIMARY_CROSSWALK_YIELD_DUE_CARE",
        },
        {
            "source_id": "CA-VEH-21954",
            "authority": "California Legislature",
            "jurisdiction": "California",
            "section": "Vehicle Code 21954",
            "official_url": "https://leginfo.legislature.ca.gov/example-21954",
            "snapshot_sha256": "f" * 64,
            "role": "OUTSIDE_CROSSWALK_EXCEPTION_CONTEXT",
        },
    ]


class RuleApplicabilityEvidenceTest(unittest.TestCase):
    def test_crosswalk_scene_gets_conditionally_applicable_official_rule(self) -> None:
        result = build_rule_applicability_evidence(
            scene_ref="scene-001",
            dataset_country="United States",
            packet=packet(),
            association=association(),
            localization=localization(),
            rule_sources=sources(),
        )
        self.assertEqual(result["status"], "AVAILABLE_SOURCE_LINKED")
        self.assertEqual(result["applicability_verdict"], "CONDITIONALLY_APPLICABLE")
        self.assertEqual(result["primary_rule_source_id"], "CA-VEH-21950")
        self.assertEqual(result["unsourced_normative_or_numeric_value_count"], 0)
        self.assertFalse(result["jurisdiction_binding"]["independent_dataset_gps_confirmation"])
        self.assertFalse(result["vehicle_safety_validated"])

    def test_country_only_location_does_not_close_applicability(self) -> None:
        result = build_rule_applicability_evidence(
            scene_ref="scene-001",
            dataset_country="United States",
            packet=packet(),
            association=association(),
            localization=localization("COUNTRY_ONLY"),
            rule_sources=sources(),
        )
        self.assertEqual(result["status"], "REVIEW_REQUIRED")
        self.assertEqual(result["reason_code"], "INSUFFICIENT_JURISDICTION_LOCALIZATION")

    def test_non_crosswalk_image_claim_does_not_activate_crosswalk_rule(self) -> None:
        review = packet()
        review["observations"]["candidate_region"] = "ROADWAY_VISIBLE"
        result = build_rule_applicability_evidence(
            scene_ref="scene-001",
            dataset_country="United States",
            packet=review,
            association=association(),
            localization=localization(),
            rule_sources=sources(),
        )
        self.assertEqual(result["status"], "REVIEW_REQUIRED")
        self.assertEqual(result["reason_code"], "CROSSWALK_APPLICABILITY_NOT_OBSERVED")

    def test_scene_mismatch_is_rejected(self) -> None:
        bad = association()
        bad["scene_ref"] = "another-scene"
        with self.assertRaisesRegex(ValueError, "SCENE_EVIDENCE_MISMATCH"):
            build_rule_applicability_evidence(
                scene_ref="scene-001",
                dataset_country="United States",
                packet=packet(),
                association=bad,
                localization=localization(),
                rule_sources=sources(),
            )

    def test_input_is_not_mutated(self) -> None:
        review, binding, place, refs = packet(), association(), localization(), sources()
        before = deepcopy((review, binding, place, refs))
        build_rule_applicability_evidence(
            scene_ref="scene-001",
            dataset_country="United States",
            packet=review,
            association=binding,
            localization=place,
            rule_sources=refs,
        )
        self.assertEqual((review, binding, place, refs), before)


if __name__ == "__main__":
    unittest.main()
