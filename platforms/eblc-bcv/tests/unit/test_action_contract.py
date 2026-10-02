"""Qualitative contract parsing, Core semantics, CNL and mutation regression."""

from copy import deepcopy
from itertools import product
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = next(p for p in Path(__file__).resolve().parents if (p / "PROJECT_REGISTRY.json").is_file())
sys.path.insert(0, str(ROOT / "platforms/eblc-bcv/src"))
from guard_synth_eblc.action_contract import parse_action_contract, lower_action_contract
from guard_synth_eblc.core_ir import parse_core_model
from guard_synth_eblc.smt_compiler import compile_core_model, solve_assignment
from guard_synth_eblc.cnl_renderer import render_action_contract


def fixture():
    return {"contract_version": "eblc-action-contract-v0.1", "contract_id": "entry_fixture", "horizon": 3,
        "claim_scope": "CONDITIONAL_ACTION_SELECTION_NOT_VEHICLE_SAFETY", "subject_id": "synthetic_ego",
        "zone_id": "synthetic_zone", "policy": "CLEAR_REQUIRED_FOR_ENTRY", "source_refs": ["synthetic:policy"],
        "obligations": [{"obligation_id": x, "predicate_id": x + "_hazard", "target_entity_id": "synthetic_" + x,
                         "rule_ref": "synthetic:policy", "source_refs": ["synthetic:policy"]} for x in ("ped", "road")]}


class ActionContractTest(unittest.TestCase):
    def setUp(self):
        self.raw = fixture()
        self.contract = parse_action_contract(self.raw)
        self.core = lower_action_contract(self.contract)
        self.compiled = compile_core_model(parse_core_model(self.core))

    def status(self, assignments, compiled=None):
        return solve_assignment(compiled or self.compiled, assignments)["status"]

    def test_invalid_schema_policy_and_sources_fail_closed(self):
        variants = []
        for key, value in (("horizon", True), ("horizon", 33), ("policy", "ALLOW_UNKNOWN"),
                           ("contract_version", "eblc-program-v0.1"), ("unexpected", True)):
            raw = deepcopy(self.raw); raw[key] = value; variants.append(raw)
        raw = deepcopy(self.raw); raw["obligations"][0]["rule_ref"] = "missing"; variants.append(raw)
        raw = deepcopy(self.raw); raw["obligations"].append(raw["obligations"][0]); variants.append(raw)
        for raw in variants:
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                parse_action_contract(raw)

    def test_parse_isolated_from_original_and_rechecks_mutation(self):
        self.raw["policy"] = "ALLOW_UNKNOWN"
        self.assertEqual(self.contract.raw["policy"], "CLEAR_REQUIRED_FOR_ENTRY")
        self.contract.raw["policy"] = "ALLOW_UNKNOWN"
        with self.assertRaises(ValueError):
            lower_action_contract(self.contract)

    def test_conditional_unbound_identity_allowed_but_visible(self):
        raw = fixture(); raw["zone_id"] = None; raw["obligations"][0]["target_entity_id"] = None
        contract = parse_action_contract(raw)
        self.assertIn("UNBOUND", render_action_contract(contract).text)
        lower_action_contract(contract)

    def test_both_unknown_gaps_are_closed(self):
        for which in ("ped", "road"):
            inputs = {(x + "_truth", 0): "FALSE" for x in ("ped", "road")}
            inputs.update({(x + "_evidence_valid", 0): True for x in ("ped", "road")})
            inputs[(which + "_truth", 0)] = "UNKNOWN"
            inputs[(which + "_prior_active", None)] = False
            self.assertEqual(self.status(inputs), "SAT")
            self.assertEqual(self.status({**inputs, ("action", 0): "ENTER_ZONE"}), "UNSAT")
            self.assertEqual(self.status({**inputs, ("action", 0): "DEFER_ENTRY"}), "SAT")

    def test_single_step_exhaustive_truth_validity_prior_and_actions(self):
        # Independent truth-table oracle over 4*2*2 combinations for each obligation.
        # Entry is checked in all 256 combinations; every input also admits defer.
        states = list(product(("TRUE", "FALSE", "UNKNOWN", "CONFLICT"), (False, True), (False, True)))
        for ped, road in product(states, repeat=2):
            inputs, expected_clear = {}, True
            for oid, (truth, valid, prior) in (("ped", ped), ("road", road)):
                inputs.update({(oid + "_truth", 0): truth, (oid + "_evidence_valid", 0): valid,
                               (oid + "_prior_active", None): prior})
                expected_clear &= valid and truth == "FALSE"
            self.assertEqual(self.status({**inputs, ("action", 0): "DEFER_ENTRY"}), "SAT")
            self.assertEqual(self.status({**inputs, ("action", 0): "ENTER_ZONE"}), "SAT" if expected_clear else "UNSAT")

    def test_retention_release_and_reactivation(self):
        cases = [("TRUE", "UNKNOWN", "FALSE", (True, True, False)),
                 ("TRUE", "FALSE", "TRUE", (True, False, True))]
        for t0, t1, t2, states in cases:
            inputs = {("ped_prior_active", None): False}
            for i, truth in enumerate((t0, t1, t2)):
                inputs[("ped_truth", i)] = truth; inputs[("ped_evidence_valid", i)] = True
            self.assertEqual(self.status(inputs), "SAT")
            for i, state in enumerate(states):
                self.assertEqual(self.status({**inputs, ("ped_active", i): not state}), "UNSAT")

    def test_stale_clear_cannot_release(self):
        inputs = {("ped_prior_active", None): True, ("ped_truth", 0): "FALSE", ("ped_evidence_valid", 0): False}
        self.assertEqual(self.status(inputs), "SAT")
        self.assertEqual(self.status({**inputs, ("ped_active", 0): False}), "UNSAT")

    def test_gate_removal_reproduces_old_gap(self):
        core = deepcopy(self.core)
        core["clauses"] = [c for c in core["clauses"] if c["id"] != "action_gate"]
        compiled = compile_core_model(parse_core_model(core))
        inputs = {("ped_prior_active", None): False, ("ped_truth", 0): "UNKNOWN", ("ped_evidence_valid", 0): True,
                  ("road_truth", 0): "FALSE", ("road_evidence_valid", 0): True, ("action", 0): "ENTER_ZONE"}
        self.assertEqual(self.status(inputs, compiled), "SAT")

    def test_renderer_is_deterministic_covered_and_solver_free(self):
        with patch("guard_synth_eblc.smt_compiler.compile_core_model", side_effect=AssertionError):
            doc = render_action_contract(self.contract)
        self.assertEqual(doc, render_action_contract(self.contract))
        self.assertTrue({"$." + k for k in self.raw}.issubset(set(doc.covered_paths)))
        self.assertEqual(doc.omitted_paths, ())
        self.assertIn("Review is required if and only if", doc.text)
        for phrase in ("if and only if", "UNKNOWN", "CONFLICT", "DEFER_ENTRY", "not forced", "synthetic_road"):
            self.assertIn(phrase, doc.text)
        self.assertTrue(all(set(c.source_refs).issubset(self.raw["source_refs"]) for c in doc.clauses))


if __name__ == "__main__":
    unittest.main()
