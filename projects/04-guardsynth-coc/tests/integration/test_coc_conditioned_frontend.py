"""TDD contract for the M14 fail-closed CoC-conditioned front-end."""

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

from guard_synth.coc_conditioned_frontend import (
    COC_FRONTEND_VERSION,
    build_constraint_proposals,
    parse_frontend_request,
)
from guard_synth.catalog_retrieval import (
    BM25CatalogRetriever,
    DenseCatalogRetriever,
)
from guard_synth.frontend_materialization import materialize_simulated_proposal
from guard_synth.frontend_matrix import (
    build_locked_frontend_cases,
    evaluate_locked_frontend_matrix,
)
from guard_synth.source_catalog import KR_FIXTURE_PATH, load_source_catalog
from guard_synth_eblc.bundle_elaborator import elaborate_bundle
from guard_synth_eblc.indexed_collection import expand_indexed_collection
from guard_synth_eblc.schema_validation import load_json
from guard_synth_eblc.smt_compiler import compile_core_model


MODEL = ROOT / "projects/04-guardsynth-coc/src/guard_synth/fixtures/simulated_assurance_profile_v0_1.json"
BASE_REQUEST = ROOT / "projects/04-guardsynth-coc/src/guard_synth/fixtures/source_aware_generation_request_p0b_v0_1.json"


def fact(predicate: str, *, truth: str = "TRUE", target: str = "ped-1",
         zone: str = "crosswalk-1", epistemic: str = "OBSERVED") -> dict:
    return {
        "predicate_id": predicate,
        "truth": truth,
        "epistemic_kind": epistemic,
        "source_ref": f"scene-source:{predicate}",
        "freshness_status": "FRESH",
        "target_ids": [target],
        "zone_ids": [zone],
    }


def request() -> dict:
    return {
        "frontend_version": COC_FRONTEND_VERSION,
        "request_id": "frontend_case_01",
        "jurisdiction": "KR",
        "catalog_id": "guardsynth-kr-structured-road-v0.1",
        "catalog_version": "guardsynth-source-catalog-v0.1",
        "catalog_as_of_date": "2026-08-10",
        "odd_tags": ["urban_or_suburban_structured_public_road"],
        "slice_hint": "PEDESTRIAN_CYCLIST_YIELD",
        "scene_tags": ["MARKED_CROSSWALK", "PEDESTRIAN_ACTOR", "PEDESTRIAN_CROSSING"],
        "coc": {
            "text": "횡단보도의 보행자 때문에 정지하려고 한다.",
            "language": "ko",
            "epistemic_kind": "CLAIMED",
            "evidence_ref": "coc-sha256:" + "a" * 64,
        },
        "scene_facts": [
            fact("pedestrian_crossing_state"),
            fact("stop_boundary_geometry"),
            fact("ego_boundary_relation"),
        ],
        "policy_evidence_ref": "GS-COC-FRONTEND-POLICY-v0.1",
    }


class CoCConditionedFrontendTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog = load_source_catalog(KR_FIXTURE_PATH)

    def test_schema_valid_request_proposes_source_bearing_crosswalk_rule(self) -> None:
        result = build_constraint_proposals(parse_frontend_request(request()), self.catalog)
        self.assertEqual(result["status"], "PROPOSED")
        self.assertFalse(result["coc_parse"]["text_included"])
        self.assertEqual(result["coc_parse"]["epistemic_kind"], "CLAIMED")
        proposal = next(
            item for item in result["proposals"]
            if item["rule_id"] == "KR-RTA-27-1-CROSSWALK-STOP"
        )
        self.assertEqual(proposal["applicability"], "TRUE")
        self.assertEqual(proposal["binding_status"], "BOUND")
        self.assertEqual(proposal["verdict"], "PROPOSED")
        self.assertEqual(proposal["source_claim_refs"], ["KR-RTA-27-1"])
        self.assertFalse(result["claim_promoted_to_scene_or_legal_authority"])

    def test_claimed_coc_never_fills_missing_scene_predicate(self) -> None:
        raw = request()
        raw["scene_facts"] = [fact("stop_boundary_geometry"), fact("ego_boundary_relation")]
        result = build_constraint_proposals(parse_frontend_request(raw), self.catalog)
        proposal = next(
            item for item in result["proposals"]
            if item["rule_id"] == "KR-RTA-27-1-CROSSWALK-STOP"
        )
        self.assertEqual(proposal["applicability"], "UNKNOWN")
        self.assertEqual(proposal["verdict"], "REVIEW_REQUIRED")
        self.assertIn("MISSING_REQUIRED_PREDICATE", proposal["reason_codes"])

    def test_conflict_and_ambiguous_binding_are_preserved(self) -> None:
        raw = request()
        raw["scene_facts"][0]["truth"] = "CONFLICT"
        conflict = build_constraint_proposals(parse_frontend_request(raw), self.catalog)
        proposal = next(item for item in conflict["proposals"] if item["rule_id"].endswith("CROSSWALK-STOP"))
        self.assertEqual(proposal["verdict"], "CONFLICT")

        raw = request()
        raw["scene_facts"][0]["target_ids"] = ["ped-1", "ped-2"]
        ambiguous = build_constraint_proposals(parse_frontend_request(raw), self.catalog)
        proposal = next(item for item in ambiguous["proposals"] if item["rule_id"].endswith("CROSSWALK-STOP"))
        self.assertEqual(proposal["binding_status"], "AMBIGUOUS")
        self.assertEqual(proposal["verdict"], "REVIEW_REQUIRED")

    def test_catalog_unsupported_numeric_binder_is_not_given_a_default(self) -> None:
        raw = request()
        raw["scene_facts"] = [
            fact("pedestrian_crossing_state"),
            fact("ego_boundary_relation"),
        ]
        raw["scene_tags"] = ["NO_CROSSWALK", "PEDESTRIAN_ACTOR", "PEDESTRIAN_CROSSING"]
        result = build_constraint_proposals(parse_frontend_request(raw), self.catalog)
        proposal = next(
            item for item in result["proposals"]
            if item["rule_id"] == "KR-RTA-27-5-NONCROSSWALK-STOP"
        )
        self.assertEqual(proposal["applicability"], "TRUE")
        self.assertEqual(proposal["verdict"], "UNSUPPORTED")
        self.assertIn(
            "UNSUPPORTED_LEGAL_TEXT_HAS_NO_NUMERIC_BOUND",
            proposal["reason_codes"],
        )
        self.assertIsNone(proposal["executable_parameters"])

    def test_fact_order_and_coc_paraphrase_preserve_candidate_semantics(self) -> None:
        first = build_constraint_proposals(parse_frontend_request(request()), self.catalog)
        raw = request()
        raw["coc"]["text"] = "보행자가 횡단 중이라 차를 멈출 계획이다."
        raw["scene_facts"].reverse()
        second = build_constraint_proposals(parse_frontend_request(raw), self.catalog)
        self.assertEqual(first["coc_parse"]["concepts"], second["coc_parse"]["concepts"])
        self.assertEqual(
            [(item["rule_id"], item["verdict"]) for item in first["proposals"]],
            [(item["rule_id"], item["verdict"]) for item in second["proposals"]],
        )

    def test_hazard_removal_cannot_leave_a_proposed_crosswalk_rule(self) -> None:
        raw = request()
        raw["scene_facts"][0]["truth"] = "FALSE"
        result = build_constraint_proposals(parse_frontend_request(raw), self.catalog)
        proposal = next(
            item for item in result["proposals"]
            if item["rule_id"] == "KR-RTA-27-1-CROSSWALK-STOP"
        )
        self.assertEqual(proposal["verdict"], "NOT_APPLICABLE")

    def test_wrong_jurisdiction_fails_closed(self) -> None:
        raw = request()
        raw["jurisdiction"] = "US-CA"
        result = build_constraint_proposals(parse_frontend_request(raw), self.catalog)
        self.assertEqual(result["status"], "UNSUPPORTED")
        self.assertEqual(result["reason_codes"], ["UNSUPPORTED_JURISDICTION"])
        self.assertEqual(result["proposals"], [])

    def test_catalog_version_and_odd_scope_fail_closed(self) -> None:
        raw = request()
        raw["catalog_version"] = "wrong-version"
        result = build_constraint_proposals(parse_frontend_request(raw), self.catalog)
        self.assertEqual(result["status"], "UNSUPPORTED")
        self.assertEqual(result["reason_codes"], ["CATALOG_VERSION_OR_ID_MISMATCH"])

        raw = request()
        raw["odd_tags"] = ["unstructured_offroad"]
        result = build_constraint_proposals(parse_frontend_request(raw), self.catalog)
        self.assertEqual(result["status"], "UNSUPPORTED")
        self.assertEqual(result["reason_codes"], ["UNSUPPORTED_OUTSIDE_ODD"])

    def test_non_claimed_coc_is_rejected(self) -> None:
        raw = deepcopy(request())
        raw["coc"]["epistemic_kind"] = "OBSERVED"
        with self.assertRaisesRegex(ValueError, "COC_MUST_REMAIN_CLAIMED"):
            parse_frontend_request(raw)

    def test_red_signal_tags_select_red_not_yellow_rule(self) -> None:
        raw = request()
        raw.update({
            "slice_hint": "STOP_SIGNALS",
            "scene_tags": ["APPLICABLE_TRAFFIC_CONTROL", "RED_SIGNAL"],
        })
        raw["coc"]["text"] = "적색 신호 때문에 정지하려고 한다."
        raw["scene_facts"] = [
            fact("traffic_control_state", target="signal-1", zone="lane-1"),
            fact("stop_boundary_geometry", target="signal-1", zone="lane-1"),
            fact("ego_boundary_relation", target="signal-1", zone="lane-1"),
        ]
        result = build_constraint_proposals(parse_frontend_request(raw), self.catalog)
        by_id = {item["rule_id"]: item for item in result["proposals"]}
        self.assertEqual(by_id["KR-RULES-A2-RED-STOP"]["verdict"], "PROPOSED")
        self.assertEqual(
            by_id["KR-RULES-A2-YELLOW-TRANSITION"]["verdict"],
            "NOT_APPLICABLE",
        )

    def test_following_rule_preserves_nonnumeric_legal_distance(self) -> None:
        raw = request()
        raw.update({
            "slice_hint": "FOLLOWING_CUT_IN",
            "scene_tags": ["FOLLOWING_LEAD_VEHICLE"],
        })
        raw["coc"]["text"] = "앞차가 있어서 감속할 계획이다."
        raw["scene_facts"] = [
            fact("lead_vehicle_state", target="lead-1", zone="lane-1"),
            fact("ego_longitudinal_action", target="lead-1", zone="lane-1"),
        ]
        result = build_constraint_proposals(parse_frontend_request(raw), self.catalog)
        proposal = next(
            item for item in result["proposals"]
            if item["rule_id"] == "KR-RTA-19-1-FOLLOWING-DISTANCE"
        )
        self.assertEqual(proposal["applicability"], "TRUE")
        self.assertEqual(proposal["verdict"], "UNSUPPORTED")
        self.assertIsNone(proposal["executable_parameters"])

    def test_bm25_and_dense_retrieval_adapters_are_deterministic_and_slice_filtered(self) -> None:
        parsed = parse_frontend_request(request())
        first = build_constraint_proposals(
            parsed,
            self.catalog,
            retriever=BM25CatalogRetriever(),
        )
        second = build_constraint_proposals(
            parsed,
            self.catalog,
            retriever=BM25CatalogRetriever(),
        )
        self.assertEqual(first["proposals"], second["proposals"])
        self.assertTrue(
            all(item["slice"] == "PEDESTRIAN_CYCLIST_YIELD" for item in first["proposals"])
        )

        def fake_embed(text: str) -> tuple[float, ...]:
            lowered = text.casefold()
            return (
                float("pedestrian" in lowered or "pedestrian_crossing_state" in lowered),
                float("signal" in lowered),
            )

        dense = build_constraint_proposals(
            parsed,
            self.catalog,
            retriever=DenseCatalogRetriever(fake_embed),
        )
        self.assertEqual(dense["retrieval_query"]["retrieval_backend"], "DENSE_ADAPTER_V0.1")
        self.assertEqual(len(dense["proposals"]), 5)

    def test_exception_tags_fail_closed_or_make_rule_not_applicable(self) -> None:
        raw = request()
        raw.update({
            "slice_hint": "FOLLOWING_CUT_IN",
            "scene_tags": ["EGO_SUDDEN_BRAKE", "DANGER_PREVENTION"],
        })
        raw["scene_facts"] = [
            fact("ego_longitudinal_action", target="ego", zone="road-scene"),
            fact("danger_or_unavoidable_reason", target="ego", zone="road-scene"),
        ]
        result = build_constraint_proposals(parse_frontend_request(raw), self.catalog)
        proposal = next(
            item for item in result["proposals"]
            if item["rule_id"] == "KR-RTA-19-4-NO-UNNECESSARY-HARD-BRAKE"
        )
        self.assertEqual(proposal["verdict"], "NOT_APPLICABLE")
        self.assertIn("DANGER_OR_UNAVOIDABLE_EXCEPTION_TRUE", proposal["reason_codes"])

        raw = request()
        raw.update({
            "slice_hint": "STOP_SIGNALS",
            "scene_tags": [
                "APPLICABLE_TRAFFIC_CONTROL", "RED_SIGNAL", "RIGHT_TURN"
            ],
        })
        raw["scene_facts"] = [
            fact("traffic_control_state", target="signal-1", zone="lane-1"),
            fact("stop_boundary_geometry", target="signal-1", zone="lane-1"),
            fact("ego_boundary_relation", target="signal-1", zone="lane-1"),
        ]
        result = build_constraint_proposals(parse_frontend_request(raw), self.catalog)
        proposal = next(
            item for item in result["proposals"]
            if item["rule_id"] == "KR-RULES-A2-RED-STOP"
        )
        self.assertEqual(proposal["verdict"], "REVIEW_REQUIRED")
        self.assertIn("RIGHT_TURN_NONOBSTRUCTION_NOT_VERIFIED", proposal["reason_codes"])

    def test_proposed_rule_materializes_with_separate_numeric_evidence_to_core_smt(self) -> None:
        proposal_bundle = build_constraint_proposals(
            parse_frontend_request(request()), self.catalog
        )
        materialized = materialize_simulated_proposal(
            proposal_bundle=proposal_bundle,
            proposal_rule_id="KR-RTA-27-1-CROSSWALK-STOP",
            scene_context={
                "scene_ref": "synthetic-m14-scene",
                "timestamp_s": 1.0,
                "hazard_evidence_ref": "synthetic-scene:pedestrian-crossing-state",
                "target_entity_id": "ped-1",
                "zone_id": "crosswalk-1",
                "zone_entry_x_m": 15.0,
                "coordinate_frame": "dataset_rig",
                "distance_unit": "m",
                "geometry_evidence_ref": "synthetic-scene:geometry",
                "association_evidence_refs": ["synthetic-scene:association"],
                "transform_verified": True,
                "transform_evidence_ref": "synthetic-scene:transform",
                "recorded_vehicle_binding_key": "recorded-rig:synthetic-scene",
            },
            model_source=MODEL,
            base_request=load_json(BASE_REQUEST),
            request_id="m14_materialized_crosswalk_01",
        )
        self.assertEqual(materialized.generated.verdict, "VALIDATED")
        self.assertEqual(len(materialized.generated.collection.instances), 1)
        self.assertNotEqual(
            materialized.recorded_vehicle_binding_key,
            materialized.simulation_vehicle_binding_key,
        )
        self.assertFalse(
            set(materialized.legal_proposal_refs).intersection(
                materialized.numeric_evidence_refs
            )
        )
        self.assertIn(
            proposal_bundle["coc_parse"]["evidence_ref"],
            materialized.request.raw["source_refs"],
        )
        self.assertTrue(
            set(materialized.legal_proposal_refs).issubset(
                materialized.request.raw["source_refs"]
            )
        )

        symbols = {
            item["symbol_id"]: item
            for item in materialized.generated.program_template.raw["typed_derivation"]["symbols"]
        }
        self.assertEqual(
            symbols["stop_margin"]["evidence_refs"],
            ["GUARDSYNTH-SIM-CORRIDOR-SYSTEM-REQUIREMENT-v0.1"],
        )
        self.assertTrue(
            symbols["response_time"]["evidence_refs"][0].startswith(
                "simulated-model-sha256:"
            )
        )
        self.assertEqual(
            symbols["response_time"]["evidence_refs"],
            symbols["deceleration"]["evidence_refs"],
        )

        expansion = expand_indexed_collection(materialized.generated.collection)
        self.assertEqual(expansion.verdict, "VALIDATED")
        elaborated = elaborate_bundle(expansion.bundle)
        compiled = compile_core_model(elaborated.core_model)
        self.assertGreater(len(compiled.assertions), 0)
        self.assertGreater(len(compiled.symbol_table["symbols"]), 0)

    def test_materialization_rejects_rule_without_operational_policy_binding(self) -> None:
        raw = request()
        raw["scene_tags"] = ["NO_CROSSWALK", "PEDESTRIAN_ACTOR", "PEDESTRIAN_CROSSING"]
        raw["scene_facts"] = [
            fact("pedestrian_crossing_state"),
            fact("ego_boundary_relation"),
        ]
        proposal_bundle = build_constraint_proposals(
            parse_frontend_request(raw), self.catalog
        )
        with self.assertRaisesRegex(
            ValueError, "FRONTEND_PROPOSAL_NOT_MATERIALIZABLE"
        ):
            materialize_simulated_proposal(
                proposal_bundle=proposal_bundle,
                proposal_rule_id="KR-RTA-27-5-NONCROSSWALK-STOP",
                scene_context={},
                model_source=MODEL,
                base_request=load_json(BASE_REQUEST),
                request_id="m14_rejected_rule",
            )

    def test_locked_24_case_matrix_preserves_verdicts_and_source_boundaries(self) -> None:
        cases = build_locked_frontend_cases()
        self.assertEqual(len(cases), 24)
        self.assertEqual(
            {item["slice"] for item in cases},
            {"PEDESTRIAN_CYCLIST_YIELD", "STOP_SIGNALS", "FOLLOWING_CUT_IN"},
        )
        result = evaluate_locked_frontend_matrix(
            catalog=self.catalog,
            model_source=MODEL,
            base_request=load_json(BASE_REQUEST),
        )
        self.assertEqual(result["schema_parse_count"], 24)
        self.assertEqual(result["expected_verdict_matches"], 24)
        self.assertEqual(result["claim_promotions"], 0)
        self.assertEqual(result["coc_text_outputs"], 0)
        self.assertEqual(result["compiler_attempt_count"], 2)
        self.assertEqual(result["compiler_success_count"], 2)
        self.assertTrue(all(
            item["compiler"]["source_separation"] is not False
            for item in result["records"]
        ))


if __name__ == "__main__":
    unittest.main()
