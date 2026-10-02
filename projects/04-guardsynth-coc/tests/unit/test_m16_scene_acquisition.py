"""Adversarial TDD contract for M16 per-scene source eligibility."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys
import unittest


ROOT = next(
    parent
    for parent in Path(__file__).resolve().parents
    if (parent / "PROJECT_REGISTRY.json").is_file()
)
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from guard_synth.expert_pilot_protocol import build_pilot_slot_manifest
from guard_synth.m16_scene_acquisition import (
    REQUIRED_EVIDENCE_FIELDS,
    assert_public_export_safe,
    bind_eligible_scenes_to_slots,
    build_m16_scene_preflight,
    build_scene_eligibility_manifest,
)


class M16SceneAcquisitionTest(unittest.TestCase):
    @staticmethod
    def evidence_fields() -> dict:
        digest = "a" * 64
        common = {
            "status": "AVAILABLE_SOURCE_LINKED",
            "evidence_ref": f"restricted-sha256:{digest}#/evidence",
            "freshness_status": "CURRENT",
            "reason_code": "SOURCE_LINKED",
        }
        fields = {
            "timestamps": {
                **common,
                "frame": "DATASET_TIME",
                "unit": "us",
                "timestamps_us": [1000, 2000, 3000],
            },
            "ego_pose_and_speed": {
                **common,
                "frame": "EGO_AT_MODEL_T0",
                "unit": "m_and_mps",
            },
            "relevant_actor_or_control_state": {
                **common,
                "frame": "DATASET_RIG",
                "unit": "m_and_us",
                "time_continuous": True,
            },
            "target_zone_or_lane_association": {
                **common,
                "frame": "DATASET_RIG",
                "unit": "set_membership",
                "ambiguity_status": "UNAMBIGUOUS_SOURCE_LINKED",
            },
            "conflict_stop_or_following_geometry": {
                **common,
                "frame": "DATASET_RIG",
                "unit": "m",
            },
            "verified_coordinate_transform": {
                **common,
                "frame": "DATASET_RIG_TO_EGO_AT_MODEL_T0",
                "unit": "rigid_transform",
                "inverse_closure_max_abs_error": 1e-12,
            },
            "applicable_rule_scope": {
                **common,
                "freshness_status": "NOT_TIME_VARYING",
                "frame": "NORMATIVE_SCOPE",
                "unit": "not_applicable",
                "scope_precondition_exception_status": "SATISFIED",
            },
            "recorded_rig_binding": {
                **common,
                "freshness_status": "NOT_TIME_VARYING",
                "frame": "RECORDED_RIG",
                "unit": "not_applicable",
            },
        }
        self_fields = set(fields)
        if self_fields != set(REQUIRED_EVIDENCE_FIELDS):
            raise AssertionError((self_fields, REQUIRED_EVIDENCE_FIELDS))
        return fields

    @classmethod
    def record(
        cls,
        index: int = 1,
        *,
        slice_name: str = "PEDESTRIAN_CYCLIST_YIELD",
        outcome: str = "HAZARD_TRUE_ACTIVE",
    ) -> dict:
        digest = f"{index:064x}"
        evidence_ref = f"restricted-sha256:{digest}#/outcome"
        outcome_evidence = {
            "kind": "ACTIVE_HAZARD_WITNESS",
            "evidence_refs": [evidence_ref],
            "source_packet_complete": True,
            "time_continuous": True,
            "lifecycle_states": ["ACTIVE"],
        }
        if outcome == "NOMINAL":
            outcome_evidence.update({
                "kind": "SAFE_PROGRESS_WITNESS",
                "relevant_scene_confirmed": True,
                "safe_progress_confirmed": True,
            })
        elif outcome == "UNKNOWN":
            outcome_evidence.update({
                "kind": "APPROVED_OBSERVABILITY_RESULT",
                "freshness_result": "STALE_APPROVED_UNKNOWN",
            })
        elif outcome == "CONFLICT":
            outcome_evidence.update({
                "kind": "SOURCE_CONFLICT",
                "evidence_refs": [
                    evidence_ref,
                    f"restricted-sha256:{'f' * 64}#/conflict",
                ],
            })
        elif outcome == "RELEASE":
            outcome_evidence.update({
                "kind": "LIFECYCLE_WITNESS",
                "lifecycle_states": ["ACTIVE", "RELEASED"],
                "lifecycle_timestamps_us": [1000, 2000],
            })
        elif outcome == "REACTIVATION":
            outcome_evidence.update({
                "kind": "LIFECYCLE_WITNESS",
                "lifecycle_states": ["ACTIVE", "RELEASED", "REACTIVATED"],
                "lifecycle_timestamps_us": [1000, 2000, 3000],
            })
        return {
            "scene_hash": f"scene-sha256:{digest}",
            "event_hash": f"event-sha256:{digest}",
            "content_hash": f"content-sha256:{digest}",
            "source_hash": f"source-sha256:{digest}",
            "slice": slice_name,
            "outcome": outcome,
            "fields": cls.evidence_fields(),
            "jurisdiction": {
                "country_code": "KR",
                "source_ref": f"restricted-sha256:{digest}#/jurisdiction",
            },
            "odd": {
                "scope_id": "KR_URBAN_SUBURBAN_STRUCTURED_ROAD",
                "status": "IN_SCOPE",
                "source_ref": f"restricted-sha256:{digest}#/odd",
            },
            "rule_catalog": {
                "catalog_id": "guardsynth-kr-structured-road-v0.1",
                "version": "guardsynth-source-catalog-v0.1",
                "authority_class": "LEGAL",
                "jurisdiction_country_code": "KR",
                "source_status": "OFFICIAL_SOURCE_LINKED",
                "source_ref": f"restricted-sha256:{digest}#/rule-catalog",
            },
            "scope_compatibility": "JURISDICTION_SOURCE_COMPATIBLE",
            "recorded_rig_binding": {
                "binding_key": f"recorded-rig-sha256:{digest}",
                "evidence_ref": f"restricted-sha256:{digest}#/recorded-rig",
            },
            "simulation_vehicle_binding": {
                "binding_key": f"simulation-vehicle-sha256:{digest}",
                "assurance_class": "SIMULATED_ASSURANCE",
                "evidence_ref": f"restricted-sha256:{digest}#/simulation-binding",
            },
            "outcome_evidence": outcome_evidence,
            "synthetic_required_field_fill": False,
            "prior_eligible": False,
        }

    def test_each_missing_or_unsourced_required_field_fails_closed(self) -> None:
        for field in REQUIRED_EVIDENCE_FIELDS:
            with self.subTest(field=field, failure="missing"):
                record = self.record()
                del record["fields"][field]
                audited = build_scene_eligibility_manifest([record])["records"][0]
                self.assertFalse(audited["source_complete"])
                self.assertFalse(audited["eligible"])
            with self.subTest(field=field, failure="unsourced"):
                record = self.record()
                record["fields"][field]["evidence_ref"] = ""
                audited = build_scene_eligibility_manifest([record])["records"][0]
                self.assertFalse(audited["eligible"])

    def test_duplicate_event_content_or_renamed_scene_is_not_counted_twice(self) -> None:
        first = self.record(1)
        renamed = self.record(2)
        renamed["event_hash"] = first["event_hash"]
        renamed["content_hash"] = first["content_hash"]
        manifest = build_scene_eligibility_manifest([renamed, first])
        self.assertEqual(manifest["eligible_scene_count"], 1)
        self.assertEqual(manifest["deduplicated_count"], 1)
        excluded = [record for record in manifest["records"] if not record["eligible"]]
        self.assertIn("DUPLICATE_EVENT_OR_CONTENT", excluded[0]["exclusion_reasons"])

    def test_bad_unit_frame_and_decreasing_timestamps_fail_closed(self) -> None:
        mutations = (
            ("ego_pose_and_speed", "unit", "kmh"),
            ("conflict_stop_or_following_geometry", "frame", "CAMERA_PIXEL"),
            ("timestamps", "timestamps_us", [1000, 900]),
        )
        for field, key, value in mutations:
            with self.subTest(field=field, key=key):
                record = self.record()
                record["fields"][field][key] = value
                audited = build_scene_eligibility_manifest([record])["records"][0]
                self.assertFalse(audited["eligible"])

    def test_target_ambiguity_and_jurisdiction_source_mismatch_are_preserved(self) -> None:
        ambiguous = self.record(1)
        ambiguous["fields"]["target_zone_or_lane_association"].update({
            "status": "REVIEW_REQUIRED",
            "ambiguity_status": "AMBIGUOUS",
            "reason_code": "TARGET_ZONE_AMBIGUOUS",
        })
        mismatched = self.record(2)
        mismatched["jurisdiction"]["country_code"] = "US"
        records = build_scene_eligibility_manifest([ambiguous, mismatched])["records"]
        self.assertFalse(records[0]["eligible"])
        self.assertIn("TARGET_ZONE_AMBIGUOUS", records[0]["exclusion_reasons"])
        self.assertFalse(records[1]["eligible"])
        self.assertIn("JURISDICTION_SOURCE_SCOPE_MISMATCH", records[1]["exclusion_reasons"])

    def test_any_country_is_allowed_when_scene_and_rule_jurisdiction_match(self) -> None:
        california = self.record(2)
        california["jurisdiction"].update({
            "country_code": "US",
            "subdivision_code": "US-CA",
        })
        california["odd"]["scope_id"] = "URBAN_SUBURBAN_STRUCTURED_ROAD"
        california["rule_catalog"].update({
            "catalog_id": "california-vehicle-code-v0.1",
            "version": "2026-snapshot",
            "jurisdiction_country_code": "US",
        })
        audited = build_scene_eligibility_manifest([california])["records"][0]
        self.assertTrue(audited["eligible"])

    def test_un_treaty_baseline_is_valid_without_claiming_domestic_compliance(self) -> None:
        germany = self.record(4, slice_name="FOLLOWING_CUT_IN")
        germany["jurisdiction"].update({"country_code": "DE"})
        germany["odd"]["scope_id"] = "URBAN_SUBURBAN_STRUCTURED_ROAD"
        germany["rule_catalog"] = {
            "catalog_id": "un-road-traffic-common-core-v0.1",
            "version": "guardsynth-m16-treaty-authority-v0.1",
            "authority_class": "INTERNATIONAL_TREATY_NORMATIVE_BASELINE",
            "jurisdiction_country_code": "MULTI",
            "treaty_participant_country_codes": ["DE"],
            "source_status": "OFFICIAL_TREATY_SOURCE_LINKED",
            "rule_strength": "DIRECT_TREATY_RULE",
            "legal_compliance_claim": "NOT_PERMITTED",
            "source_ref": germany["jurisdiction"]["source_ref"],
        }
        germany["scope_compatibility"] = "TREATY_NORMATIVE_BASELINE_COMPATIBLE"
        audited = build_scene_eligibility_manifest([germany])["records"][0]
        self.assertTrue(audited["eligible"])

    def test_unknown_country_fails_closed(self) -> None:
        record = self.record(3)
        record["jurisdiction"]["country_code"] = "UNKNOWN"
        record["rule_catalog"]["jurisdiction_country_code"] = "UNKNOWN"
        audited = build_scene_eligibility_manifest([record])["records"][0]
        self.assertFalse(audited["eligible"])
        self.assertIn("JURISDICTION_SOURCE_SCOPE_MISMATCH", audited["exclusion_reasons"])

    def test_outcome_labels_require_source_bearing_semantic_witnesses(self) -> None:
        cases = []
        unknown = self.record(1, outcome="UNKNOWN")
        unknown["outcome_evidence"]["source_packet_complete"] = False
        cases.append(unknown)
        conflict = self.record(2, outcome="CONFLICT")
        conflict["outcome_evidence"]["evidence_refs"] = conflict["outcome_evidence"]["evidence_refs"][:1]
        cases.append(conflict)
        released = self.record(3, outcome="RELEASE")
        released["outcome_evidence"]["lifecycle_states"] = ["ACTIVE"]
        cases.append(released)
        reactivated = self.record(4, outcome="REACTIVATION")
        reactivated["outcome_evidence"]["lifecycle_states"] = ["ACTIVE", "REACTIVATED"]
        cases.append(reactivated)
        nominal = self.record(5, outcome="NOMINAL")
        nominal["outcome_evidence"]["safe_progress_confirmed"] = False
        cases.append(nominal)
        for record in cases:
            with self.subTest(outcome=record["outcome"]):
                audited = build_scene_eligibility_manifest([record])["records"][0]
                self.assertFalse(audited["eligible"])
                self.assertIn("OUTCOME_WITNESS_INVALID", audited["exclusion_reasons"])

    def test_aggregate_count_cannot_override_individual_records(self) -> None:
        manifest = build_scene_eligibility_manifest([self.record(1)])
        binding = bind_eligible_scenes_to_slots(manifest, build_pilot_slot_manifest())
        with self.assertRaisesRegex(ValueError, "AGGREGATE_INDIVIDUAL_COUNT_MISMATCH"):
            build_m16_scene_preflight(
                manifest,
                binding,
                asserted_aggregate={"eligible_scene_count": 60},
            )

    def test_quota_and_ready_state_are_derived_from_60_individual_bindings(self) -> None:
        slots = build_pilot_slot_manifest()
        records = [
            self.record(
                index,
                slice_name=slot["slice"],
                outcome=slot["outcome"],
            )
            for index, slot in enumerate(slots["slots"], start=1)
        ]
        manifest = build_scene_eligibility_manifest(records)
        binding = bind_eligible_scenes_to_slots(manifest, slots)
        preflight = build_m16_scene_preflight(manifest, binding)
        self.assertEqual(binding["bound_slot_count"], 60)
        self.assertEqual(set(binding["joint_cell_shortfall"].values()), {0})
        self.assertTrue(
            all(record["assigned_slot_id"] for record in manifest["records"])
        )
        self.assertEqual(preflight["status"], "READY_FOR_REVIEWER_CALIBRATION")
        self.assertTrue(preflight["annotation_start_allowed"])
        self.assertFalse(preflight["annotation_started"])

    def test_public_export_rejects_raw_path_identifier_and_coc_text(self) -> None:
        safe = {"eligible_scene_count": 0, "reason_codes": ["DATA_SHORTFALL"]}
        assert_public_export_safe(safe)
        for unsafe in (
            {"path": "/home/user/restricted/source.json"},
            {"clip_id": "raw-identifier"},
            {"coc_text": "full private reasoning"},
        ):
            with self.subTest(unsafe=unsafe):
                with self.assertRaisesRegex(ValueError, "RESTRICTED_IDENTIFIER_LEAK"):
                    assert_public_export_safe(unsafe)


if __name__ == "__main__":
    unittest.main()
