from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

from cli.solver_runtime import configure_project_z3


ROOT = Path(__file__).resolve().parents[2]
configure_project_z3(ROOT)

from src.guard_synth_eblc.core_ir import CoreIRValidationError, load_core_model, parse_core_model
from src.guard_synth_eblc.smt_compiler import compile_core_model, export_compilation, check_queries


FIXTURE = ROOT / "src/guard_synth_eblc/fixtures/eblc_core_p0b.json"


def raw_fixture() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


class CoreSMTCompilerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.model = load_core_model(FIXTURE)
        cls.compiled = compile_core_model(cls.model)
        cls.checked = check_queries(cls.compiled)

    def test_schema_parser_and_type_checker_accept_locked_fixture(self) -> None:
        self.assertEqual(self.model.grammar_version, "eblc-core-v0.1")
        self.assertEqual(len(self.model.declarations), 14)
        self.assertEqual(len(self.model.clauses), 16)
        self.assertEqual(len(self.model.queries), 7)

    def test_all_locked_query_results_match(self) -> None:
        expected = {
            "lifecycle_transition_inconsistency": "UNSAT",
            "active_stop_position_violation": "SAT",
            "missing_reactivation": "UNSAT",
            "safe_progress_false_deadlock": "UNSAT",
            "dynamic_stopping_bound_violation": "SAT",
            "clear_counter_always_nonnegative": "SAT",
            "inactive_until_activation": "SAT",
        }
        actual = {item["query_id"]: item["status"] for item in self.checked["results"]}
        self.assertEqual(actual, expected)
        self.assertEqual(self.checked["agreement"], 1.0)

    def test_declarative_properties_are_queries_not_assumptions(self) -> None:
        source = self.compiled.source_map["clauses"]
        self.assertFalse(source["stop_position_invariant"]["compiled"])
        self.assertFalse(source["dynamic_stopping_bound"]["compiled"])
        statuses = {item["query_id"]: item["status"] for item in self.checked["results"]}
        self.assertEqual(statuses["active_stop_position_violation"], "SAT")
        self.assertEqual(statuses["dynamic_stopping_bound_violation"], "SAT")

    def test_division_emits_definedness_constraint(self) -> None:
        result = next(
            item for item in self.checked["results"]
            if item["query_id"] == "dynamic_stopping_bound_violation"
        )
        self.assertGreaterEqual(result["definedness_constraint_count"], 1)

    def test_time_indexed_symbol_table_and_enum_codes(self) -> None:
        state_symbols = [
            item for item in self.compiled.symbol_table["symbols"]
            if item["declaration"] == "state"
        ]
        stop_symbols = [
            item for item in self.compiled.symbol_table["symbols"]
            if item["declaration"] == "stop_position"
        ]
        self.assertEqual(len(state_symbols), self.model.horizon)
        self.assertEqual(len(stop_symbols), 1)
        self.assertEqual(
            self.compiled.symbol_table["enum_codes"]["Lifecycle"]["REACTIVATED"],
            5,
        )
        mapped = self.compiled.source_map["clauses"]["lifecycle_transition"]
        self.assertEqual(len(mapped["assertion_indices"]), self.model.horizon - 1)
        self.assertTrue(all(isinstance(index, int) for index in mapped["assertion_indices"]))

    def test_export_contains_replayable_smt_and_maps(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            checked = export_compilation(self.compiled, output)
            self.assertEqual(checked["agreement"], 1.0)
            self.assertIn("check-sat", (output / "MODEL.smt2").read_text(encoding="utf-8"))
            self.assertTrue((output / "SYMBOL_TABLE.json").is_file())
            self.assertTrue((output / "SOURCE_MAP.json").is_file())
            self.assertTrue((output / "QUERY_MANIFEST.json").is_file())
            self.assertEqual(len(list(output.glob("QUERY_*.smt2"))), 7)

    def test_unit_mismatch_fails_closed(self) -> None:
        raw = raw_fixture()
        raw["clauses"][2]["formula"]["right"]["unit"] = "s"
        with self.assertRaisesRegex(CoreIRValidationError, "unit mismatch"):
            parse_core_model(raw)

    def test_coordinate_frame_mismatch_fails_closed(self) -> None:
        raw = raw_fixture()
        raw["clauses"][2]["formula"]["right"]["frame"] = "map_xy"
        with self.assertRaisesRegex(CoreIRValidationError, "frame mismatch"):
            parse_core_model(raw)

    def test_unknown_enum_literal_fails_closed(self) -> None:
        raw = raw_fixture()
        raw["clauses"][0]["formula"]["right"]["value"] = "UNKNOWN_STATE"
        with self.assertRaisesRegex(CoreIRValidationError, "outside Lifecycle"):
            parse_core_model(raw)

    def test_temporal_window_beyond_horizon_fails_closed(self) -> None:
        raw = raw_fixture()
        raw["queries"][0]["formula"]["end"] = raw["horizon"]
        with self.assertRaisesRegex(CoreIRValidationError, "window exceeds horizon"):
            parse_core_model(raw)

    def test_constant_cannot_be_time_shifted(self) -> None:
        raw = raw_fixture()
        raw["clauses"][2]["formula"]["left"]["offset"] = 1
        with self.assertRaisesRegex(CoreIRValidationError, "constant variable cannot use offset"):
            parse_core_model(raw)

    def test_query_witness_is_deterministic_typed_mapping(self) -> None:
        result = next(
            item for item in self.checked["results"]
            if item["query_id"] == "active_stop_position_violation"
        )
        self.assertIsInstance(result["witness"], dict)
        self.assertEqual(
            result["witness"]["p0b_pedestrian_conflict_zone_core__state__t0"],
            "INACTIVE",
        )


if __name__ == "__main__":
    unittest.main()
