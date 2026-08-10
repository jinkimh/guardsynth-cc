from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import unittest

from guard_synth.source_catalog import (
    EXPECTED_FAMILIES,
    KR_FIXTURE_PATH,
    SourceCatalogValidationError,
    audit_source_catalog,
    load_source_catalog,
    parse_source_catalog,
)
from guard_synth_eblc.schema_validation import load_json, validate


ROOT = Path(__file__).resolve().parents[2]


class SourceCatalogTest(unittest.TestCase):
    def setUp(self) -> None:
        self.raw = load_json(KR_FIXTURE_PATH)

    def test_fixture_is_schema_valid_and_loads(self) -> None:
        validate(self.raw, load_json(ROOT / "src/guard_synth/schemas/source_catalog.schema.json"))
        catalog = load_source_catalog()
        self.assertEqual(catalog.raw["catalog_version"], "guardsynth-source-catalog-v0.1")

    def test_locked_template_slice_and_family_gate(self) -> None:
        audit = audit_source_catalog(load_source_catalog())
        self.assertEqual(audit["rule_template_count"], 15)
        self.assertEqual(audit["slice_counts"], {
            "FOLLOWING_CUT_IN": 4,
            "PEDESTRIAN_CYCLIST_YIELD": 5,
            "STOP_SIGNALS": 6,
        })
        self.assertEqual(set(audit["family_coverage"]), EXPECTED_FAMILIES)

    def test_all_legal_sources_are_official_and_versioned(self) -> None:
        for source in self.raw["source_records"]:
            with self.subTest(source=source["evidence_id"]):
                self.assertIn("law.go.kr", source["uri"])
                self.assertEqual(len(source["effective_date"]), 10)
                self.assertTrue(source["version"])
                self.assertEqual(source["hash_basis"], "CANONICAL_SOURCE_RECORD_NOT_DOCUMENT_BYTES")

    def test_predicates_fail_to_unknown_and_exclude_claimed(self) -> None:
        for predicate in self.raw["predicate_specs"]:
            with self.subTest(predicate=predicate["predicate_id"]):
                self.assertEqual(predicate["failure_value"], "UNKNOWN")
                self.assertEqual(predicate["freshness"]["failure_value"], "UNKNOWN")
                self.assertNotIn("CLAIMED", predicate["allowed_epistemic"])

    def test_every_rule_has_source_binding_lifecycle_and_priority(self) -> None:
        for rule in self.raw["rule_templates"]:
            with self.subTest(rule=rule["rule_id"]):
                self.assertTrue(rule["source_claim_refs"])
                self.assertTrue(rule["required_predicate_refs"])
                self.assertTrue(rule["binder_ref"])
                self.assertTrue(rule["lifecycle_profile_ref"])
                self.assertIn(rule["priority_tier"], {"HARD_LEGAL", "HARD_SYSTEM", "SERVICE", "PREFERENCE"})

    def test_no_executable_numeric_literal_and_missing_bound_is_explicit(self) -> None:
        audit = audit_source_catalog(load_source_catalog())
        self.assertEqual(audit["unsourced_normative_or_numeric_value_count"], 0)
        output = next(
            output
            for binder in self.raw["binder_specs"]
            if binder["binder_id"] == "safe_distance_unsupported"
            for output in binder["outputs"]
        )
        self.assertEqual(output["kind"], "UNSUPPORTED")
        self.assertEqual(output["reason_code"], "UNSUPPORTED_LEGAL_TEXT_HAS_NO_NUMERIC_BOUND")

    def test_open_rule_reference_is_rejected(self) -> None:
        mutated = deepcopy(self.raw)
        mutated["rule_templates"][0]["source_claim_refs"] = ["NOT-A-CLAIM"]
        with self.assertRaisesRegex(SourceCatalogValidationError, "open rule references"):
            parse_source_catalog(mutated)

    def test_claimed_predicate_is_rejected(self) -> None:
        mutated = deepcopy(self.raw)
        mutated["predicate_specs"][0]["allowed_epistemic"].append("CLAIMED")
        with self.assertRaises(ValueError):
            parse_source_catalog(mutated)

    def test_source_record_tampering_is_rejected(self) -> None:
        mutated = deepcopy(self.raw)
        mutated["source_records"][0]["section"] = "changed after audit"
        with self.assertRaisesRegex(SourceCatalogValidationError, "hash mismatch"):
            parse_source_catalog(mutated)

    def test_bicycle_marking_exception_is_not_a_normative_rule(self) -> None:
        interpretation = next(
            item for item in self.raw["source_records"]
            if item["evidence_id"] == "KR-MOLEG-INTERPRETATION-23-0574"
        )
        self.assertFalse(interpretation["claims"][0]["normative"])
        used = {
            ref for rule in self.raw["rule_templates"] for ref in rule["source_claim_refs"]
        }
        self.assertNotIn("KR-INT-23-0574-NONNORMATIVE", used)


if __name__ == "__main__":
    unittest.main()

