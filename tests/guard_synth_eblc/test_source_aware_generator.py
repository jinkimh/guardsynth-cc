"""TDD contract for RuleTemplate + ContextGraph + profile generation."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import unittest

from cli.solver_runtime import configure_project_z3


ROOT = Path(__file__).resolve().parents[2]
configure_project_z3(ROOT)
import sys
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from src.guard_synth_eblc.bundle_elaborator import elaborate_bundle
from src.guard_synth_eblc.indexed_collection import expand_indexed_collection
from src.guard_synth_eblc.schema_validation import load_json
from src.guard_synth_eblc.smt_compiler import compile_core_model, solve_assignment
from guard_synth.source_aware_generator import (
    SourceAwareGenerationValidationError,
    generate_from_request,
    load_generation_request,
    parse_generation_request,
)


FIXTURE = ROOT / "src/guard_synth/fixtures/source_aware_generation_request_p0b_v0_1.json"


def raw_request() -> dict:
    return load_json(FIXTURE)


class SourceAwareGeneratorTest(unittest.TestCase):
    def test_valid_request_generates_schema_valid_indexed_collection(self) -> None:
        request = load_generation_request(FIXTURE)
        result = generate_from_request(request)
        self.assertEqual(result.verdict, "VALIDATED")
        self.assertEqual(result.reason_codes, ("SOURCE_AWARE_INDEXED_COLLECTION_GENERATED",))
        self.assertIsNotNone(result.program_template)
        self.assertIsNotNone(result.collection)
        self.assertEqual(len(result.collection.instances), 2)

    def test_program_values_come_from_rule_predicate_profile_and_policy(self) -> None:
        result = generate_from_request(load_generation_request(FIXTURE))
        raw = result.program_template.raw
        self.assertEqual(raw["binding"]["rule_id"], "P0B-SYS-PED-CZ-001")
        self.assertEqual(raw["predicate"]["maximum_age_s"], 0.2)
        self.assertEqual(raw["constraints"]["deceleration"]["value"], 3.0)
        self.assertEqual(raw["constraints"]["response_time"]["value"], 0.5)
        self.assertEqual(raw["typed_derivation"]["symbols"][1]["value"], 1.5)
        self.assertNotIn("P0B-SYNTHETIC-COC-CLAIM-v0", raw["predicate"]["evidence_refs"])
        self.assertIn("P0B-SYNTHETIC-COC-CLAIM-v0", result.claimed_evidence_refs)

    def test_generated_collection_expands_to_distinct_contracts(self) -> None:
        result = generate_from_request(load_generation_request(FIXTURE))
        expansion = expand_indexed_collection(result.collection)
        self.assertEqual(expansion.verdict, "VALIDATED")
        self.assertEqual(
            [(item.contract_id, item.program.raw["binding"]["target_entity_id"], item.program.raw["binding"]["zone_id"])
             for item in expansion.bundle.contracts],
            [
                ("C0", "synthetic-pedestrian:P17", "synthetic-zone:CZ4"),
                ("C1", "synthetic-pedestrian:P18", "synthetic-zone:CZ5"),
            ],
        )

    def test_generated_collection_reaches_core_smt_with_exact_witness(self) -> None:
        result = generate_from_request(load_generation_request(FIXTURE))
        bundle = expand_indexed_collection(result.collection).bundle
        compiled = compile_core_model(elaborate_bundle(bundle).core_model)
        solved = solve_assignment(compiled, {
            ("c0__ego_speed", 0): 6.000000001,
            ("c1__ego_speed", 0): 3.000000001,
        })
        self.assertEqual(solved["status"], "SAT")
        symbols = {
            (item["declaration"], item["time"]): item["smt_symbol"]
            for item in compiled.symbol_table["symbols"]
        }
        witness = solved["witness"]
        self.assertEqual(witness[symbols[("c0__stop_position", None)]], "-3/2")
        self.assertEqual(witness[symbols[("c1__stop_position", None)]], "21/2")
        self.assertEqual(witness[symbols[("c0__stopping_distance", 0)]], "9")
        self.assertEqual(witness[symbols[("c1__stopping_distance", 0)]], "3")

    def test_claimed_only_hazard_requires_review_and_generates_nothing(self) -> None:
        raw = raw_request()
        raw["context_graph"]["instances"][0]["hazard_fact"]["epistemic_kind"] = "CLAIMED"
        result = generate_from_request(parse_generation_request(raw))
        self.assertEqual(result.verdict, "REVIEW_REQUIRED")
        self.assertIn("COC_CLAIM_NOT_OBSERVED_FACT", result.reason_codes)
        self.assertIsNone(result.collection)

    def test_missing_vehicle_profile_is_unsupported_without_default(self) -> None:
        raw = raw_request()
        raw["vehicle_profile"] = None
        result = generate_from_request(parse_generation_request(raw))
        self.assertEqual(result.verdict, "UNSUPPORTED")
        self.assertIn("MISSING_VEHICLE_ASSURANCE_PROFILE", result.reason_codes)
        self.assertIsNone(result.program_template)

    def test_missing_geometry_or_transform_is_unsupported(self) -> None:
        raw = raw_request()
        raw["context_graph"]["instances"][1]["association"]["zone_geometry_ref"] = None
        result = generate_from_request(parse_generation_request(raw))
        self.assertEqual(result.verdict, "UNSUPPORTED")
        self.assertIn("MISSING_ZONE_GEOMETRY", result.reason_codes)
        self.assertIsNone(result.collection)

    def test_ambiguous_target_requires_review(self) -> None:
        raw = raw_request()
        association = raw["context_graph"]["instances"][0]["association"]
        association["selected_target_entity_id"] = None
        association["candidate_target_entity_ids"] = [
            "synthetic-pedestrian:P17", "synthetic-pedestrian:P19"
        ]
        result = generate_from_request(parse_generation_request(raw))
        self.assertEqual(result.verdict, "REVIEW_REQUIRED")
        self.assertIn("AMBIGUOUS_TARGET_ASSOCIATION", result.reason_codes)
        self.assertIsNone(result.collection)

    def test_duplicate_target_zone_binding_is_conflict(self) -> None:
        raw = raw_request()
        first = raw["context_graph"]["instances"][0]["association"]
        second = raw["context_graph"]["instances"][1]["association"]
        second["selected_target_entity_id"] = first["selected_target_entity_id"]
        second["selected_zone_id"] = first["selected_zone_id"]
        second["candidate_target_entity_ids"] = [first["selected_target_entity_id"]]
        second["candidate_zone_ids"] = [first["selected_zone_id"]]
        result = generate_from_request(parse_generation_request(raw))
        self.assertEqual(result.verdict, "CONFLICT")
        self.assertIn("DUPLICATE_TARGET_ZONE_BINDING", result.reason_codes)

    def test_zone_entry_unit_or_frame_mismatch_is_unsupported(self) -> None:
        raw = raw_request()
        raw["context_graph"]["instances"][0]["zone_entry"]["unit"] = "cm"
        result = generate_from_request(parse_generation_request(raw))
        self.assertEqual(result.verdict, "UNSUPPORTED")
        self.assertIn("ZONE_ENTRY_UNIT_OR_FRAME_MISMATCH", result.reason_codes)

    def test_unknown_evidence_reference_fails_request_validation(self) -> None:
        raw = raw_request()
        raw["context_graph"]["instances"][0]["association"]["evidence_refs"].append("UNKNOWN-REF")
        with self.assertRaisesRegex(SourceAwareGenerationValidationError, "unknown evidence"):
            parse_generation_request(raw)

    def test_generation_is_deterministic(self) -> None:
        request = load_generation_request(FIXTURE)
        left = generate_from_request(request)
        right = generate_from_request(request)
        self.assertEqual(left.program_template.raw, right.program_template.raw)
        self.assertEqual(left.collection.raw, right.collection.raw)


if __name__ == "__main__":
    unittest.main()
