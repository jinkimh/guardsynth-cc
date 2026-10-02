"""Contract tests for the M16 UN-treaty normative baseline."""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import sys
import unittest


ROOT = next(
    parent
    for parent in Path(__file__).resolve().parents
    if (parent / "PROJECT_REGISTRY.json").is_file()
)
SRC = ROOT / "projects/04-guardsynth-coc/src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from guard_synth.m16_treaty_authority import (
    CATALOG_PATH,
    bind_treaty_authority,
    load_treaty_authority_catalog,
)


class M16TreatyAuthorityTest(unittest.TestCase):
    def setUp(self) -> None:
        self.catalog = load_treaty_authority_catalog(CATALOG_PATH)

    def test_catalog_uses_only_official_un_sources(self) -> None:
        self.assertEqual(
            self.catalog["authority_class"],
            "INTERNATIONAL_TREATY_NORMATIVE_BASELINE",
        )
        self.assertEqual(
            {record["official_host"] for record in self.catalog["source_records"]},
            {"treaties.un.org", "unece.org"},
        )
        self.assertTrue(
            all(record["uri"].startswith("https://") for record in self.catalog["source_records"])
        )

    def test_all_current_cohort_countries_and_slices_are_bound(self) -> None:
        countries = {
            "Austria",
            "Belgium",
            "Czechia",
            "Estonia",
            "France",
            "Germany",
            "Italy",
            "Latvia",
            "Lithuania",
            "Slovenia",
            "Sweden",
            "United States",
        }
        slices = {
            "PEDESTRIAN_CYCLIST_YIELD",
            "STOP_SIGNALS",
            "FOLLOWING_CUT_IN",
        }
        records = [
            {"candidate_digest": f"candidate-{i}", "country": country, "slice": slice_name}
            for i, (country, slice_name) in enumerate(
                (country, slice_name) for country in sorted(countries) for slice_name in sorted(slices)
            )
        ]
        audit = bind_treaty_authority(records, self.catalog)
        self.assertEqual(audit["record_count"], 36)
        self.assertEqual(audit["authority_bound_count"], 36)
        self.assertEqual(audit["unbound_count"], 0)

    def test_us_rules_are_general_fallback_not_local_law(self) -> None:
        audit = bind_treaty_authority(
            [{
                "candidate_digest": "candidate-us",
                "country": "United States",
                "slice": "STOP_SIGNALS",
                "next_source_tasks": ["BIND_JURISDICTION_MATCHED_AUTHORITY"],
            }],
            self.catalog,
        )
        record = audit["records"][0]
        self.assertEqual(record["rule_strength"], "GENERAL_DUE_CARE_FALLBACK")
        self.assertEqual(
            record["scope_compatibility"],
            "TREATY_NORMATIVE_BASELINE_COMPATIBLE",
        )
        self.assertTrue(record["domestic_detail_required"])
        self.assertEqual(record["legal_compliance_claim"], "NOT_PERMITTED")
        self.assertNotIn(
            "BIND_JURISDICTION_MATCHED_AUTHORITY", record["next_source_tasks"]
        )

    def test_european_following_rule_is_direct_treaty_rule(self) -> None:
        audit = bind_treaty_authority(
            [{
                "candidate_digest": "candidate-de",
                "country": "Germany",
                "slice": "FOLLOWING_CUT_IN",
            }],
            self.catalog,
        )
        record = audit["records"][0]
        self.assertEqual(record["country_code"], "DE")
        self.assertEqual(record["rule_strength"], "DIRECT_TREATY_RULE")
        self.assertEqual(record["article_refs"], ["1968-ROAD-TRAFFIC:13(5)"])
        self.assertFalse(record["domestic_detail_required"])

    def test_unknown_country_or_slice_fails_closed(self) -> None:
        records = [
            {"candidate_digest": "candidate-country", "country": "UNKNOWN", "slice": "STOP_SIGNALS"},
            {"candidate_digest": "candidate-slice", "country": "Germany", "slice": "UNKNOWN"},
        ]
        audit = bind_treaty_authority(records, self.catalog)
        self.assertEqual(audit["authority_bound_count"], 0)
        self.assertEqual(audit["unbound_count"], 2)
        self.assertEqual(
            {record["authority_status"] for record in audit["records"]},
            {"REVIEW_REQUIRED_NO_TREATY_BINDING"},
        )

    def test_catalog_rejects_non_official_source_and_missing_mapping(self) -> None:
        bad_host = deepcopy(self.catalog)
        bad_host["source_records"][0]["uri"] = "https://example.com/treaty"
        missing_mapping = deepcopy(self.catalog)
        missing_mapping["slice_mappings"] = missing_mapping["slice_mappings"][:-1]
        for raw in (bad_host, missing_mapping):
            with self.subTest(raw=json.dumps(raw, sort_keys=True)[:80]):
                with self.assertRaises(ValueError):
                    load_treaty_authority_catalog(raw)


if __name__ == "__main__":
    unittest.main()
