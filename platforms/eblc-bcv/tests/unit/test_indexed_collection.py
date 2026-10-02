from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import unittest

from cli.solver_runtime import configure_project_z3


ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "PROJECT_REGISTRY.json").is_file())
configure_project_z3(ROOT)

from src.guard_synth_eblc.indexed_collection import (
    IndexedCollectionValidationError,
    expand_indexed_collection,
    parse_indexed_collection,
)
from src.guard_synth_eblc.bundle_elaborator import elaborate_bundle
from src.guard_synth_eblc.smt_compiler import (
    check_queries,
    compile_core_model,
    solve_assignment,
)


FIXTURE = ROOT / "platforms/eblc-bcv/src/guard_synth_eblc/fixtures/eblc_indexed_collection_p0b_v0_1.json"


def raw_fixture() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


class IndexedCollectionValidationTests(unittest.TestCase):
    def test_valid_two_actor_two_zone_collection_parses(self) -> None:
        collection = parse_indexed_collection(raw_fixture())
        self.assertEqual(collection.collection_id, "p0b_two_actor_two_zone_collection")
        self.assertEqual(len(collection.instances), 2)
        self.assertEqual(
            {(item.target_entity_id, item.zone_id) for item in collection.instances},
            {
                ("synthetic-pedestrian:P17", "synthetic-zone:CZ4"),
                ("synthetic-pedestrian:P18", "synthetic-zone:CZ5"),
            },
        )

    def test_duplicate_bound_target_zone_pair_fails_closed(self) -> None:
        raw = raw_fixture()
        raw["instances"][1]["association"]["target_entity_id"] = raw["instances"][0]["association"]["target_entity_id"]
        raw["instances"][1]["association"]["zone_id"] = raw["instances"][0]["association"]["zone_id"]
        with self.assertRaisesRegex(IndexedCollectionValidationError, "duplicate bound target-zone"):
            parse_indexed_collection(raw)

    def test_bound_association_requires_geometry_transform_and_evidence(self) -> None:
        for field in ("zone_geometry_ref", "coordinate_transform_ref"):
            raw = raw_fixture()
            raw["instances"][0]["association"][field] = None
            with self.subTest(field=field), self.assertRaisesRegex(
                IndexedCollectionValidationError, "BOUND association"
            ):
                parse_indexed_collection(raw)
        raw = raw_fixture()
        raw["instances"][0]["association"]["evidence_refs"].append("UNKNOWN-EVIDENCE")
        with self.assertRaisesRegex(IndexedCollectionValidationError, "evidence"):
            parse_indexed_collection(raw)


class IndexedCollectionExpansionTests(unittest.TestCase):
    def test_bound_instances_expand_to_distinct_program_bindings(self) -> None:
        result = expand_indexed_collection(parse_indexed_collection(raw_fixture()))
        self.assertEqual(result.verdict, "VALIDATED")
        self.assertIsNotNone(result.bundle)
        bundle = result.bundle
        assert bundle is not None
        bindings = [item.program.raw["binding"] for item in bundle.contracts]
        self.assertEqual(
            [(item["target_entity_id"], item["zone_id"]) for item in bindings],
            [
                ("synthetic-pedestrian:P17", "synthetic-zone:CZ4"),
                ("synthetic-pedestrian:P18", "synthetic-zone:CZ5"),
            ],
        )
        self.assertEqual(len({item.program.program_id for item in bundle.contracts}), 2)

    def test_zone_geometry_values_replace_template_derivation_symbol(self) -> None:
        result = expand_indexed_collection(parse_indexed_collection(raw_fixture()))
        assert result.bundle is not None
        values = []
        for component in result.bundle.contracts:
            symbols = component.program.raw["typed_derivation"]["symbols"]
            zone_entry = next(item for item in symbols if item["symbol_id"] == "zone_entry_x")
            values.append(zone_entry["value"])
        self.assertEqual(values, [0.0, 12.0])

    def test_ambiguous_association_stops_before_contract_generation(self) -> None:
        raw = raw_fixture()
        association = raw["instances"][1]["association"]
        association.update({
            "status": "AMBIGUOUS",
            "target_entity_id": None,
            "zone_id": None,
            "zone_geometry_ref": None,
            "coordinate_transform_ref": None,
            "candidate_target_entity_ids": ["synthetic-pedestrian:P18", "synthetic-pedestrian:P19"],
            "candidate_zone_ids": ["synthetic-zone:CZ5"],
            "reason_codes": ["MULTIPLE_TARGET_CANDIDATES"],
        })
        raw["instances"][1]["zone_entry"] = None
        result = expand_indexed_collection(parse_indexed_collection(raw))
        self.assertEqual(result.verdict, "REVIEW_REQUIRED")
        self.assertIsNone(result.bundle)
        self.assertIn("MULTIPLE_TARGET_CANDIDATES", result.reason_codes)

    def test_unsupported_and_conflict_precedence_are_fail_closed(self) -> None:
        raw = raw_fixture()
        association = raw["instances"][0]["association"]
        association.update({
            "status": "UNSUPPORTED",
            "target_entity_id": None,
            "zone_id": None,
            "zone_geometry_ref": None,
            "coordinate_transform_ref": None,
            "candidate_target_entity_ids": [],
            "candidate_zone_ids": [],
            "reason_codes": ["MISSING_TRACK_GEOMETRY"],
        })
        raw["instances"][0]["zone_entry"] = None
        result = expand_indexed_collection(parse_indexed_collection(raw))
        self.assertEqual(result.verdict, "UNSUPPORTED")
        self.assertIsNone(result.bundle)

        conflict = deepcopy(raw)
        conflict["instances"][1]["association"].update({
            "status": "CONFLICT",
            "target_entity_id": None,
            "zone_id": None,
            "zone_geometry_ref": None,
            "coordinate_transform_ref": None,
            "candidate_target_entity_ids": ["synthetic-pedestrian:P18"],
            "candidate_zone_ids": ["synthetic-zone:CZ5", "synthetic-zone:CZ6"],
            "reason_codes": ["ASSOCIATION_EVIDENCE_CONFLICT"],
        })
        conflict["instances"][1]["zone_entry"] = None
        result = expand_indexed_collection(parse_indexed_collection(conflict))
        self.assertEqual(result.verdict, "CONFLICT")
        self.assertIsNone(result.bundle)

    def test_multi_actor_zone_bundle_compiles_with_namespaced_derivations(self) -> None:
        result = expand_indexed_collection(parse_indexed_collection(raw_fixture()))
        assert result.bundle is not None
        elaborated = elaborate_bundle(result.bundle)
        compiled = compile_core_model(elaborated.core_model)
        self.assertEqual(check_queries(compiled)["agreement"], 1.0)
        declarations = {item.name for item in elaborated.core_model.declarations}
        self.assertIn("c0__stopping_distance", declarations)
        self.assertIn("c1__stopping_distance", declarations)
        definedness = [item for item in compiled.assertions if item.role == "DEFINEDNESS"]
        self.assertEqual(len(definedness), 18)

    def test_z3_replays_distinct_zone_geometry_and_speed_witnesses(self) -> None:
        result = expand_indexed_collection(parse_indexed_collection(raw_fixture()))
        assert result.bundle is not None
        compiled = compile_core_model(elaborate_bundle(result.bundle).core_model)
        solved = solve_assignment(compiled, {
            ("c0__ego_speed", 0): 6.000000001,
            ("c1__ego_speed", 0): 3.000000001,
        })
        self.assertEqual(solved["status"], "SAT")
        symbols = {
            (item["declaration"], item["time"]): item["smt_symbol"]
            for item in compiled.symbol_table["symbols"]
        }
        witness = solved["witness"] or {}
        self.assertEqual(witness[symbols[("c0__stop_position", None)]], "-3/2")
        self.assertEqual(witness[symbols[("c1__stop_position", None)]], "21/2")
        self.assertEqual(witness[symbols[("c0__stopping_distance", 0)]], "9")
        self.assertEqual(witness[symbols[("c1__stopping_distance", 0)]], "3")


if __name__ == "__main__":
    unittest.main()
