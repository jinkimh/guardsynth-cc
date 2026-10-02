from __future__ import annotations

import unittest
from pathlib import Path

from cli.solver_runtime import configure_project_z3


ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "PROJECT_REGISTRY.json").is_file())
configure_project_z3(ROOT)

from src.guard_synth_eblc.adapters.synthetic_pedestrian import (
    PILOT_PROFILE,
    frame,
    initial_frame,
)
from src.guard_synth_eblc.binders import bind_pedestrian_contract
from src.guard_synth_eblc.bundle_conformance import compare_bundle_trace
from src.guard_synth_eblc.bundle_elaborator import elaborate_bundle
from src.guard_synth_eblc.catalog import load_pilot_rule, load_predicate_spec
from src.guard_synth_eblc import examples
from src.guard_synth_eblc.smt_compiler import compile_core_model, solve_assignment
from src.guard_synth_eblc.types import Truth


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


def bound_contracts(bundle):
    outcome = bind_pedestrian_contract(
        load_pilot_rule(), load_predicate_spec(), initial_frame(), PILOT_PROFILE
    )
    if outcome.contract is None:
        raise AssertionError(outcome.reason_codes)
    from dataclasses import replace

    return {
        item.contract_id: replace(outcome.contract, contract_id=item.contract_id)
        for item in bundle.contracts
    }


class BundleV02DerivationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.bundle = examples.synthetic_bundle_v02()
        cls.elaborated = elaborate_bundle(cls.bundle)
        cls.compiled = compile_core_model(cls.elaborated.core_model)

    def test_bundle_v01_container_accepts_v02_components(self) -> None:
        self.assertEqual(self.bundle.raw["bundle_version"], "eblc-bundle-v0.1")
        self.assertTrue(all(
            item.program.raw["program_version"] == "eblc-program-v0.2"
            and item.program.typed_derivation is not None
            for item in self.bundle.contracts
        ))

    def test_derived_declarations_and_clauses_are_namespaced(self) -> None:
        declarations = {item.name for item in self.elaborated.core_model.declarations}
        clauses = {item.clause_id for item in self.elaborated.core_model.clauses}
        for prefix in ("c0__", "c1__"):
            self.assertIn(f"{prefix}stop_position", declarations)
            self.assertIn(f"{prefix}stopping_distance", declarations)
            self.assertIn(f"{prefix}derive__output__stop_position", clauses)
            self.assertIn(f"{prefix}derive__output__stopping_distance", clauses)
        self.assertNotIn("stopping_distance", declarations)

    def test_speed_violation_consumes_namespaced_derived_output(self) -> None:
        clauses = {
            item["id"]: item for item in self.elaborated.core_document["clauses"]
        }
        for prefix in ("c0__", "c1__"):
            names = variable_names(clauses[f"{prefix}generated_speed_violation"]["formula"])
            self.assertIn(f"{prefix}stopping_distance", names)
            self.assertNotIn("stopping_distance", names)

    def test_smt_preserves_division_definedness_for_each_component_and_frame(self) -> None:
        records = [item for item in self.compiled.assertions if item.role == "DEFINEDNESS"]
        self.assertEqual(len(records), 18)
        self.assertEqual(
            {item.clause_id for item in records},
            {
                "c0__derive__output__stopping_distance",
                "c1__derive__output__stopping_distance",
            },
        )

    def test_z3_replays_independent_exact_derivation_witnesses(self) -> None:
        solved = solve_assignment(
            self.compiled,
            {
                ("c0__ego_speed", 0): 6.000000001,
                ("c1__ego_speed", 0): 3.000000001,
            },
        )
        self.assertEqual(solved["status"], "SAT")
        symbols = {
            (item["declaration"], item["time"]): item["smt_symbol"]
            for item in self.compiled.symbol_table["symbols"]
        }
        witness = solved["witness"]
        self.assertEqual(witness[symbols[("c0__stopping_distance", 0)]], "9")
        self.assertEqual(witness[symbols[("c1__stopping_distance", 0)]], "3")

    def test_elaboration_map_exposes_component_versions_and_derived_outputs(self) -> None:
        mapping = self.elaborated.elaboration_map
        self.assertEqual(
            mapping["component_program_versions"],
            {"C0": "eblc-program-v0.2", "C1": "eblc-program-v0.2"},
        )
        self.assertEqual(
            mapping["component_derived_outputs"],
            {"C0": ["stop_position", "stopping_distance"], "C1": ["stop_position", "stopping_distance"]},
        )
        self.assertNotIn(
            "DERIVATION_PROVENANCE_PRESERVED_NOT_SYMBOLICALLY_REPLAYED",
            mapping["limitations"],
        )

    def test_v02_hard_service_canonical_core_smt_agreement(self) -> None:
        contracts = bound_contracts(self.bundle)
        trace = (frame(0.0, Truth.TRUE),)
        result = compare_bundle_trace(
            self.bundle, contracts, {contract_id: trace for contract_id in contracts}
        )
        self.assertTrue(result["matches"], result["mismatches"])
        self.assertEqual(result["core_smt"][0]["selected_contracts"], ["C0"])
        self.assertEqual(result["core_smt"][0]["admissible_actions"], ["STOP"])

    def test_v02_hard_conflict_canonical_core_smt_agreement(self) -> None:
        bundle = examples.synthetic_bundle_v02(
            ("HARD", "HARD"),
            (("STOP",), ("PROCEED",)),
            bundle_id="p0b_v02_hard_conflict_bundle",
        )
        contracts = bound_contracts(bundle)
        trace = (frame(0.0, Truth.TRUE),)
        result = compare_bundle_trace(
            bundle,
            contracts,
            {contract_id: trace for contract_id in contracts},
            safe_progress_action_exists=(True,),
        )
        self.assertTrue(result["matches"], result["mismatches"])
        self.assertEqual(result["core_smt"][0]["verdict"], "CONFLICT")
        self.assertTrue(result["core_smt"][0]["false_deadlock"])


if __name__ == "__main__":
    unittest.main()
