from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import unittest

from cli.solver_runtime import configure_project_z3


ROOT = Path(__file__).resolve().parents[2]
configure_project_z3(ROOT)

from src.guard_synth_eblc.adapters.synthetic_pedestrian import (
    PILOT_PROFILE,
    frame,
    initial_frame,
    locked_translation_traces,
)
from src.guard_synth_eblc.binders import bind_pedestrian_contract
from src.guard_synth_eblc.catalog import load_pilot_rule, load_predicate_spec
from src.guard_synth_eblc.conformance import compare_trace
from src.guard_synth_eblc.derivation import (
    DerivationValidationError,
    elaborate_derivation,
    parse_derivation_spec,
)
from src.guard_synth_eblc.elaborator import elaborate_program
from src.guard_synth_eblc.program import load_program
from src.guard_synth_eblc.smt_compiler import compile_core_model, solve_assignment
from src.guard_synth_eblc.types import Truth


PROGRAM_FIXTURE = ROOT / "src/guard_synth_eblc/fixtures/eblc_program_p0b.json"
RULE_REF = "P0B-SYNTHETIC-SYSTEM-REQUIREMENT-PED-YIELD-v0"


def stop_position_spec() -> dict:
    return {
        "derivation_version": "eblc-derivation-v0.1",
        "derivation_id": "p0b_stop_position_derivation",
        "horizon": 2,
        "claim_scope": "SYNTHETIC_TYPED_DERIVATION_NOT_VEHICLE_SAFETY",
        "source_refs": [RULE_REF],
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
        ],
        "nodes": [
            {
                "node_id": "stop_position",
                "operation": "SUB",
                "inputs": ["symbol:zone_entry_x", "symbol:stop_margin"],
                "source_refs": [RULE_REF],
            }
        ],
        "outputs": [
            {
                "output_id": "stop_position",
                "node_ref": "node:stop_position",
                "target_declaration": "derived_stop_position",
                "sort": "REAL",
                "time_varying": False,
                "unit": "m",
                "frame": "ego_path_s",
                "replace_clause_ids": [],
                "evidence_refs": [RULE_REF],
            }
        ],
    }


class DerivationValidationTests(unittest.TestCase):
    def test_valid_typed_derivation_parses(self) -> None:
        parsed = parse_derivation_spec(stop_position_spec())
        self.assertEqual(parsed.derivation_id, "p0b_stop_position_derivation")
        self.assertEqual(parsed.nodes[0].operation, "SUB")

    def test_unknown_reference_fails_closed(self) -> None:
        raw = stop_position_spec()
        raw["nodes"][0]["inputs"][1] = "symbol:missing"
        with self.assertRaisesRegex(DerivationValidationError, "unknown derivation reference"):
            parse_derivation_spec(raw)

    def test_cycle_fails_closed(self) -> None:
        raw = stop_position_spec()
        raw["nodes"] = [
            {"node_id": "left", "operation": "NEG", "inputs": ["node:right"], "source_refs": [RULE_REF]},
            {"node_id": "right", "operation": "NEG", "inputs": ["node:left"], "source_refs": [RULE_REF]},
        ]
        raw["outputs"][0]["node_ref"] = "node:left"
        with self.assertRaisesRegex(DerivationValidationError, "cycle"):
            parse_derivation_spec(raw)

    def test_operation_arity_fails_closed(self) -> None:
        raw = stop_position_spec()
        raw["nodes"][0]["inputs"] = ["symbol:zone_entry_x"]
        with self.assertRaisesRegex(DerivationValidationError, "arity"):
            parse_derivation_spec(raw)

    def test_unknown_evidence_reference_fails_closed(self) -> None:
        raw = stop_position_spec()
        raw["nodes"][0]["source_refs"] = ["MISSING-SOURCE"]
        with self.assertRaisesRegex(DerivationValidationError, "unknown evidence"):
            parse_derivation_spec(raw)


class DerivationCompilerTests(unittest.TestCase):
    def test_standalone_derivation_replays_numeric_value_in_z3(self) -> None:
        result = elaborate_derivation(parse_derivation_spec(stop_position_spec()))
        compiled = compile_core_model(result.core_model)
        solved = solve_assignment(compiled, {})
        self.assertEqual(solved["status"], "SAT")
        symbol = next(
            item["smt_symbol"]
            for item in compiled.symbol_table["symbols"]
            if item["declaration"] == "derived_stop_position"
        )
        self.assertEqual(solved["witness"][symbol], "-3/2")

    def test_unit_mismatch_is_rejected_by_core_type_checker(self) -> None:
        raw = stop_position_spec()
        raw["symbols"][1]["unit"] = "s"
        with self.assertRaisesRegex(ValueError, "unit mismatch"):
            elaborate_derivation(parse_derivation_spec(raw))

    def test_frame_mismatch_is_rejected_by_core_type_checker(self) -> None:
        raw = stop_position_spec()
        raw["symbols"][1]["frame"] = "map_xy"
        with self.assertRaisesRegex(ValueError, "frame mismatch"):
            elaborate_derivation(parse_derivation_spec(raw))

    def test_zero_divisor_makes_generated_core_unsatisfiable(self) -> None:
        raw = stop_position_spec()
        raw["symbols"].append({
            "symbol_id": "zero_scale",
            "kind": "SOURCED_VALUE",
            "sort": "REAL",
            "time_varying": False,
            "value": 0.0,
            "core_name": None,
            "unit": "1",
            "frame": None,
            "evidence_refs": [RULE_REF],
        })
        raw["nodes"][0] = {
            "node_id": "stop_position",
            "operation": "DIV",
            "inputs": ["symbol:zone_entry_x", "symbol:zero_scale"],
            "source_refs": [RULE_REF],
        }
        result = elaborate_derivation(parse_derivation_spec(raw))
        solved = solve_assignment(compile_core_model(result.core_model), {})
        self.assertEqual(solved["status"], "UNSAT")

    def test_program_augmentation_replaces_static_binding_and_preserves_trace(self) -> None:
        program = load_program(PROGRAM_FIXTURE)
        base = elaborate_program(program)
        raw = stop_position_spec()
        raw["horizon"] = base.core_model.horizon
        raw["outputs"][0]["target_declaration"] = "stop_position"
        raw["outputs"][0]["replace_clause_ids"] = ["bind_stop_position"]
        derived = elaborate_derivation(
            parse_derivation_spec(raw), base_core_document=base.core_document
        )
        clause_ids = {item.clause_id for item in derived.core_model.clauses}
        self.assertNotIn("bind_stop_position", clause_ids)
        self.assertIn("derive__output__stop_position", clause_ids)

        binding = bind_pedestrian_contract(
            load_pilot_rule(), load_predicate_spec(), initial_frame(), PILOT_PROFILE
        )
        if binding.contract is None:
            raise AssertionError(binding.reason_codes)
        compared = compare_trace(
            binding.contract,
            program,
            compile_core_model(derived.core_model),
            "typed_stop_position",
            (frame(0.0, Truth.TRUE),),
        )
        self.assertTrue(compared["matches"], compared["mismatches"])

    def test_typed_stop_position_preserves_all_locked_trace_results(self) -> None:
        program = load_program(PROGRAM_FIXTURE)
        base = elaborate_program(program)
        raw = stop_position_spec()
        raw["horizon"] = base.core_model.horizon
        raw["outputs"][0]["target_declaration"] = "stop_position"
        raw["outputs"][0]["replace_clause_ids"] = ["bind_stop_position"]
        derived = elaborate_derivation(
            parse_derivation_spec(raw), base_core_document=base.core_document
        )
        compiled = compile_core_model(derived.core_model)
        binding = bind_pedestrian_contract(
            load_pilot_rule(), load_predicate_spec(), initial_frame(), PILOT_PROFILE
        )
        if binding.contract is None:
            raise AssertionError(binding.reason_codes)
        records = [
            compare_trace(binding.contract, program, compiled, trace_id, samples)
            for trace_id, samples in locked_translation_traces().items()
        ]
        self.assertEqual(len(records), 8)
        self.assertTrue(all(item["matches"] for item in records), records)


if __name__ == "__main__":
    unittest.main()
