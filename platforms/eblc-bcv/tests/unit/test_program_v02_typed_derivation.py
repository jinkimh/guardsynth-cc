from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import unittest

from cli.solver_runtime import configure_project_z3


ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "PROJECT_REGISTRY.json").is_file())
configure_project_z3(ROOT)

from src.guard_synth_eblc.adapters.synthetic_pedestrian import (
    PILOT_PROFILE,
    initial_frame,
    locked_translation_traces,
)
from src.guard_synth_eblc.binders import bind_pedestrian_contract
from src.guard_synth_eblc.catalog import load_pilot_rule, load_predicate_spec
from src.guard_synth_eblc.conformance import (
    compare_trace,
    generated_p0b_conformance_suite,
    validate_conformance,
)
from src.guard_synth_eblc.elaborator import elaborate_program
from src.guard_synth_eblc.program import EBLCProgramValidationError, load_program, parse_program
from src.guard_synth_eblc.smt_compiler import compile_core_model, solve_assignment


PROGRAM_V01 = ROOT / "platforms/eblc-bcv/src/guard_synth_eblc/fixtures/eblc_program_p0b.json"
PROGRAM_V02 = ROOT / "platforms/eblc-bcv/src/guard_synth_eblc/fixtures/eblc_program_p0b_v0_2.json"
RULE_REF = "P0B-SYNTHETIC-SYSTEM-REQUIREMENT-PED-YIELD-v0"
PROFILE_REF = "P0B-SYNTHETIC-VEHICLE-PROFILE-v0"
ORACLE_REF = "P0B-CONTROLLED-CONFORMANCE-ORACLE-v0"


def full_stopping_derivation(*, horizon: int = 9) -> dict:
    return {
        "derivation_version": "eblc-derivation-v0.1",
        "derivation_id": "p0b_full_stopping_derivation",
        "horizon": horizon,
        "claim_scope": "P0B_HIGH_LEVEL_ELABORATION_AND_BOUNDED_CONFORMANCE_NOT_VEHICLE_SAFETY",
        "source_refs": [RULE_REF, PROFILE_REF, ORACLE_REF],
        "symbols": [
            {
                "symbol_id": "zone_entry_x",
                "kind": "SOURCED_VALUE",
                "sort": "REAL",
                "time_varying": False,
                "value": 0.0,
                "core_name": None,
                "unit": "m",
                "frame": "ego_path_s",
                "evidence_refs": [RULE_REF],
            },
            {
                "symbol_id": "stop_margin",
                "kind": "SOURCED_VALUE",
                "sort": "REAL",
                "time_varying": False,
                "value": 1.5,
                "core_name": None,
                "unit": "m",
                "frame": "ego_path_s",
                "evidence_refs": [RULE_REF],
            },
            {
                "symbol_id": "factor_two",
                "kind": "SOURCED_VALUE",
                "sort": "REAL",
                "time_varying": False,
                "value": 2.0,
                "core_name": None,
                "unit": "1",
                "frame": None,
                "evidence_refs": [PROFILE_REF],
            },
            {
                "symbol_id": "zero_speed",
                "kind": "SOURCED_VALUE",
                "sort": "REAL",
                "time_varying": False,
                "value": 0.0,
                "core_name": None,
                "unit": "m/s",
                "frame": "ego_path_s",
                "evidence_refs": [ORACLE_REF],
            },
            {
                "symbol_id": "ego_speed",
                "kind": "CORE_VARIABLE",
                "sort": "REAL",
                "time_varying": True,
                "value": None,
                "core_name": "ego_speed",
                "unit": "m/s",
                "frame": "ego_path_s",
                "evidence_refs": [ORACLE_REF],
            },
            {
                "symbol_id": "speed_epsilon",
                "kind": "CORE_VARIABLE",
                "sort": "REAL",
                "time_varying": False,
                "value": None,
                "core_name": "speed_epsilon",
                "unit": "m/s",
                "frame": "ego_path_s",
                "evidence_refs": [ORACLE_REF],
            },
            {
                "symbol_id": "response_time",
                "kind": "CORE_VARIABLE",
                "sort": "REAL",
                "time_varying": False,
                "value": None,
                "core_name": "response_time",
                "unit": "s",
                "frame": None,
                "evidence_refs": [PROFILE_REF],
            },
            {
                "symbol_id": "deceleration",
                "kind": "CORE_VARIABLE",
                "sort": "REAL",
                "time_varying": False,
                "value": None,
                "core_name": "deceleration",
                "unit": "m/s^2",
                "frame": "ego_path_s",
                "evidence_refs": [PROFILE_REF],
            },
        ],
        "nodes": [
            {"node_id": "stop_position", "operation": "SUB", "inputs": ["symbol:zone_entry_x", "symbol:stop_margin"], "source_refs": [RULE_REF]},
            {"node_id": "adjusted_speed", "operation": "SUB", "inputs": ["symbol:ego_speed", "symbol:speed_epsilon"], "source_refs": [ORACLE_REF]},
            {"node_id": "effective_speed", "operation": "MAX", "inputs": ["node:adjusted_speed", "symbol:zero_speed"], "source_refs": [ORACLE_REF]},
            {"node_id": "response_distance", "operation": "MUL", "inputs": ["node:effective_speed", "symbol:response_time"], "source_refs": [PROFILE_REF, ORACLE_REF]},
            {"node_id": "speed_squared", "operation": "MUL", "inputs": ["node:effective_speed", "node:effective_speed"], "source_refs": [ORACLE_REF]},
            {"node_id": "twice_deceleration", "operation": "MUL", "inputs": ["symbol:factor_two", "symbol:deceleration"], "source_refs": [PROFILE_REF]},
            {"node_id": "braking_distance", "operation": "DIV", "inputs": ["node:speed_squared", "node:twice_deceleration"], "source_refs": [PROFILE_REF, ORACLE_REF]},
            {"node_id": "stopping_distance", "operation": "ADD", "inputs": ["node:response_distance", "node:braking_distance"], "source_refs": [PROFILE_REF, ORACLE_REF]},
        ],
        "outputs": [
            {
                "output_id": "stop_position",
                "node_ref": "node:stop_position",
                "target_declaration": "stop_position",
                "sort": "REAL",
                "time_varying": False,
                "unit": "m",
                "frame": "ego_path_s",
                "replace_clause_ids": [],
                "evidence_refs": [RULE_REF],
            },
            {
                "output_id": "stopping_distance",
                "node_ref": "node:stopping_distance",
                "target_declaration": "stopping_distance",
                "sort": "REAL",
                "time_varying": True,
                "unit": "m",
                "frame": "ego_path_s",
                "replace_clause_ids": [],
                "evidence_refs": [PROFILE_REF, ORACLE_REF],
            },
        ],
    }


def raw_program_v02() -> dict:
    return json.loads(PROGRAM_V02.read_text(encoding="utf-8"))


def variable_names(expression: dict) -> set[str]:
    names: set[str] = set()
    if expression.get("op") == "var":
        names.add(expression["name"])
    for value in expression.values():
        if isinstance(value, dict):
            names.update(variable_names(value))
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    names.update(variable_names(item))
    return names


class ProgramV02ValidationTests(unittest.TestCase):
    def test_v02_embeds_typed_derivation(self) -> None:
        raw = raw_program_v02()
        self.assertEqual(raw["typed_derivation"], full_stopping_derivation())
        program = parse_program(raw)
        self.assertEqual(program.raw["program_version"], "eblc-program-v0.2")
        self.assertIsNotNone(program.typed_derivation)
        self.assertEqual(len(program.typed_derivation.nodes), 8)

    def test_v01_remains_supported_without_typed_derivation(self) -> None:
        program = load_program(PROGRAM_V01)
        self.assertEqual(program.raw["program_version"], "eblc-program-v0.1")
        self.assertIsNone(program.typed_derivation)

    def test_v02_requires_typed_derivation_and_rejects_free_form_dag(self) -> None:
        missing = raw_program_v02()
        missing.pop("typed_derivation")
        with self.assertRaises(ValueError):
            parse_program(missing)
        legacy = raw_program_v02()
        legacy["derivation_dag"] = [{"unsafe": "free-form"}]
        with self.assertRaises(ValueError):
            parse_program(legacy)

    def test_embedded_derivation_horizon_and_sources_match_program(self) -> None:
        horizon = raw_program_v02()
        horizon["typed_derivation"]["horizon"] = 8
        with self.assertRaisesRegex(EBLCProgramValidationError, "horizon"):
            parse_program(horizon)
        source = raw_program_v02()
        source["typed_derivation"]["source_refs"].append("UNDECLARED-SOURCE")
        with self.assertRaisesRegex(EBLCProgramValidationError, "source"):
            parse_program(source)

    def test_embedded_derivation_interface_is_fail_closed(self) -> None:
        output = raw_program_v02()
        output["typed_derivation"]["outputs"][1]["target_declaration"] = "other_distance"
        with self.assertRaisesRegex(EBLCProgramValidationError, "output interface"):
            parse_program(output)
        replacement = raw_program_v02()
        replacement["typed_derivation"]["outputs"][0]["replace_clause_ids"] = ["generated_verdict"]
        with self.assertRaisesRegex(EBLCProgramValidationError, "replace"):
            parse_program(replacement)
        variable = raw_program_v02()
        variable["typed_derivation"]["symbols"][4]["core_name"] = "undeclared_speed"
        with self.assertRaisesRegex(EBLCProgramValidationError, "CORE_VARIABLE"):
            parse_program(variable)


class ProgramV02ElaborationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.program = parse_program(raw_program_v02())
        cls.elaborated = elaborate_program(cls.program)
        cls.compiled = compile_core_model(cls.elaborated.core_model)

    def test_full_dag_outputs_are_bound_in_core(self) -> None:
        clause_ids = {item.clause_id for item in self.elaborated.core_model.clauses}
        self.assertIn("derive__output__stop_position", clause_ids)
        self.assertIn("derive__output__stopping_distance", clause_ids)
        self.assertNotIn("bind_stop_position", clause_ids)

    def test_speed_violation_consumes_derived_stopping_distance(self) -> None:
        clause = next(
            item for item in self.elaborated.core_document["clauses"]
            if item["id"] == "generated_speed_violation"
        )
        self.assertIn("stopping_distance", variable_names(clause["formula"]))

    def test_z3_replays_exact_stop_position_and_stopping_distance(self) -> None:
        solved = solve_assignment(self.compiled, {("ego_speed", 0): 6.000000001})
        self.assertEqual(solved["status"], "SAT")
        symbols = {
            (item["declaration"], item["time"]): item["smt_symbol"]
            for item in self.compiled.symbol_table["symbols"]
        }
        witness = solved["witness"]
        self.assertEqual(witness[symbols[("stop_position", None)]], "-3/2")
        self.assertEqual(witness[symbols[("stopping_distance", 0)]], "9")

    def test_locked_trace_translation_agreement_is_preserved(self) -> None:
        binding = bind_pedestrian_contract(
            load_pilot_rule(), load_predicate_spec(), initial_frame(), PILOT_PROFILE
        )
        if binding.contract is None:
            raise AssertionError(binding.reason_codes)
        records = [
            compare_trace(binding.contract, self.program, self.compiled, trace_id, samples)
            for trace_id, samples in locked_translation_traces().items()
        ]
        self.assertEqual(len(records), 8)
        self.assertTrue(all(item["matches"] for item in records), records)

    def test_generated_conformance_matrix_remains_at_full_agreement(self) -> None:
        binding = bind_pedestrian_contract(
            load_pilot_rule(), load_predicate_spec(), initial_frame(), PILOT_PROFILE
        )
        if binding.contract is None:
            raise AssertionError(binding.reason_codes)
        result = validate_conformance(
            binding.contract,
            self.program,
            generated_p0b_conformance_suite(),
        )
        self.assertEqual(result["trace_count"], 129)
        self.assertEqual(result["trace_agreement"], 1.0)
        self.assertEqual(result["frame_agreement"], 1.0)

    def test_v01_elaboration_keeps_legacy_static_path(self) -> None:
        legacy = elaborate_program(load_program(PROGRAM_V01))
        clause_ids = {item.clause_id for item in legacy.core_model.clauses}
        declaration_names = {item.name for item in legacy.core_model.declarations}
        self.assertIn("bind_stop_position", clause_ids)
        self.assertNotIn("stopping_distance", declaration_names)


if __name__ == "__main__":
    unittest.main()
