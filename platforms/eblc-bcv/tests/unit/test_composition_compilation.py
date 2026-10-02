from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path
import unittest

from cli.solver_runtime import configure_project_z3


ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "PROJECT_REGISTRY.json").is_file())
configure_project_z3(ROOT)

from src.guard_synth_eblc.adapters.synthetic_pedestrian import PILOT_PROFILE, frame, initial_frame
from src.guard_synth_eblc.binders import bind_pedestrian_contract
from src.guard_synth_eblc.bundle_conformance import compare_bundle_trace
from src.guard_synth_eblc.bundle_elaborator import elaborate_bundle
from src.guard_synth_eblc.catalog import load_pilot_rule, load_predicate_spec
from src.guard_synth_eblc.composition import (
    ContractEvaluation,
    EBLCBundleValidationError,
    parse_bundle,
    resolve_composition,
)
from src.guard_synth_eblc.smt_compiler import check_queries, compile_core_model
from src.guard_synth_eblc.types import Truth


PROGRAM_FIXTURE = ROOT / "platforms/eblc-bcv/src/guard_synth_eblc/fixtures/eblc_program_p0b.json"
COMPOSITION_REF = "P0B-SYNTHETIC-COMPOSITION-POLICY-v0"


def make_bundle(
    tiers: tuple[str, ...],
    allowed: tuple[tuple[str, ...], ...],
    *,
    overrides: tuple[tuple[str, ...], ...] | None = None,
):
    base = json.loads(PROGRAM_FIXTURE.read_text(encoding="utf-8"))
    ids = tuple(f"C{index}" for index in range(len(tiers)))
    entries = []
    for index, (contract_id, tier, actions) in enumerate(zip(ids, tiers, allowed)):
        program = deepcopy(base)
        program["program_id"] = f"composition_program_{index}"
        program["binding"]["contract_id"] = contract_id
        entries.append({
            "contract_id": contract_id,
            "program": program,
            "priority_tier": tier,
            "allowed_actions": list(actions),
            "overrides_contracts": list((overrides or tuple(() for _ in tiers))[index]),
            "evidence_refs": [COMPOSITION_REF],
        })
    source_refs = list(dict.fromkeys(base["source_refs"] + [COMPOSITION_REF]))
    return parse_bundle({
        "bundle_version": "eblc-bundle-v0.1",
        "bundle_id": "composition_test_bundle",
        "frames": base["frames"],
        "claim_scope": "SYNTHETIC_COMPOSITION_AND_BOUNDED_TRANSLATION_NOT_VEHICLE_SAFETY",
        "source_refs": source_refs,
        "action_domain": ["STOP", "CREEP", "PROCEED"],
        "contracts": entries,
        "composition_evidence_refs": [COMPOSITION_REF],
    })


def bound_contracts(bundle):
    outcome = bind_pedestrian_contract(
        load_pilot_rule(), load_predicate_spec(), initial_frame(), PILOT_PROFILE
    )
    if outcome.contract is None:
        raise AssertionError(outcome.reason_codes)
    return {
        item.contract_id: replace(outcome.contract, contract_id=item.contract_id)
        for item in bundle.contracts
    }


def active_evaluations(bundle):
    return tuple(
        ContractEvaluation(item.contract_id, "ACTIVE", "VALIDATED")
        for item in bundle.contracts
    )


class CompositionSemanticsTests(unittest.TestCase):
    def test_hard_dominates_service_without_scalar_weight(self) -> None:
        bundle = make_bundle(("HARD", "SERVICE"), (("STOP",), ("PROCEED",)))
        result = resolve_composition(bundle, active_evaluations(bundle))
        self.assertEqual(result.selected_contracts, ("C0",))
        self.assertEqual(result.suppressed_contracts, ("C1",))
        self.assertEqual(result.admissible_actions, ("STOP",))
        self.assertEqual(result.verdict, "VALIDATED")

    def test_incomparable_hard_conflict_is_not_silently_resolved(self) -> None:
        bundle = make_bundle(("HARD", "HARD"), (("STOP",), ("PROCEED",)))
        result = resolve_composition(
            bundle, active_evaluations(bundle), safe_progress_action_exists=True
        )
        self.assertEqual(result.selected_contracts, ("C0", "C1"))
        self.assertEqual(result.admissible_actions, ())
        self.assertEqual(result.verdict, "CONFLICT")
        self.assertTrue(result.false_deadlock)
        self.assertIn("INCOMPARABLE_HARD_CONTRACT_ACTION_CONFLICT", result.reason_codes)

    def test_incomparable_service_conflict_requires_review(self) -> None:
        bundle = make_bundle(("SERVICE", "SERVICE"), (("STOP",), ("PROCEED",)))
        result = resolve_composition(bundle, active_evaluations(bundle))
        self.assertEqual(result.verdict, "REVIEW_REQUIRED")
        self.assertIn(
            "INCOMPARABLE_NONHARD_CONTRACT_ACTION_CONFLICT", result.reason_codes
        )

    def test_explicit_same_tier_override_resolves_conflict(self) -> None:
        bundle = make_bundle(
            ("SERVICE", "SERVICE"), (("STOP",), ("PROCEED",)),
            overrides=(("C1",), ()),
        )
        result = resolve_composition(bundle, active_evaluations(bundle))
        self.assertEqual(result.selected_contracts, ("C0",))
        self.assertEqual(result.admissible_actions, ("STOP",))
        self.assertEqual(result.verdict, "VALIDATED")

    def test_no_live_contract_restores_full_action_domain(self) -> None:
        bundle = make_bundle(("HARD", "SERVICE"), (("STOP",), ("PROCEED",)))
        evaluations = tuple(
            ContractEvaluation(item.contract_id, "INACTIVE", "VALIDATED")
            for item in bundle.contracts
        )
        result = resolve_composition(bundle, evaluations)
        self.assertEqual(result.selected_contracts, ())
        self.assertEqual(result.admissible_actions, bundle.action_domain)

    def test_child_verdict_precedence_is_conflict_unsupported_review_validated(self) -> None:
        bundle = make_bundle(("HARD", "SERVICE"), (("STOP",), ("STOP",)))
        for child, expected in (
            ("CONFLICT", "CONFLICT"),
            ("UNSUPPORTED", "UNSUPPORTED"),
            ("REVIEW_REQUIRED", "REVIEW_REQUIRED"),
            ("VALIDATED", "VALIDATED"),
        ):
            evaluations = (
                ContractEvaluation("C0", "ACTIVE", "VALIDATED"),
                ContractEvaluation("C1", "ACTIVE", child),
            )
            with self.subTest(child=child):
                self.assertEqual(resolve_composition(bundle, evaluations).verdict, expected)

    def test_lower_priority_override_of_hard_fails_closed(self) -> None:
        with self.assertRaisesRegex(EBLCBundleValidationError, "lower priority"):
            make_bundle(
                ("HARD", "SERVICE"), (("STOP",), ("PROCEED",)),
                overrides=((), ("C0",)),
            )

    def test_priority_override_cycle_fails_closed(self) -> None:
        with self.assertRaisesRegex(EBLCBundleValidationError, "override cycle"):
            make_bundle(
                ("SERVICE", "SERVICE"), (("STOP",), ("PROCEED",)),
                overrides=(("C1",), ("C0",)),
            )


class BundleCompilationTests(unittest.TestCase):
    def test_high_level_bundle_elaborates_to_namespaced_core_and_z3(self) -> None:
        bundle = make_bundle(("HARD", "SERVICE"), (("STOP",), ("PROCEED",)))
        elaborated = elaborate_bundle(bundle)
        declarations = {item.name for item in elaborated.core_model.declarations}
        clauses = {item.clause_id for item in elaborated.core_model.clauses}
        self.assertIn("c0__state", declarations)
        self.assertIn("c1__state", declarations)
        self.assertIn("selected__C0", declarations)
        self.assertIn("admissible__STOP", declarations)
        self.assertIn("composition_verdict", declarations)
        self.assertIn("compose_verdict", clauses)
        self.assertFalse(
            elaborated.elaboration_map["priority"]["compiled_as_scalar_weight"]
        )
        checked = check_queries(compile_core_model(elaborated.core_model))
        self.assertEqual(checked["agreement"], 1.0)

    def test_hard_service_canonical_to_core_smt_agreement(self) -> None:
        bundle = make_bundle(("HARD", "SERVICE"), (("STOP",), ("PROCEED",)))
        contracts = bound_contracts(bundle)
        trace = (frame(0.0, Truth.TRUE),)
        result = compare_bundle_trace(
            bundle, contracts, {contract_id: trace for contract_id in contracts}
        )
        self.assertTrue(result["matches"], result["mismatches"])
        self.assertEqual(result["core_smt"][0]["selected_contracts"], ["C0"])
        self.assertEqual(result["core_smt"][0]["admissible_actions"], ["STOP"])

    def test_hard_conflict_and_false_deadlock_agree_with_core_smt(self) -> None:
        bundle = make_bundle(("HARD", "HARD"), (("STOP",), ("PROCEED",)))
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

    def test_no_live_contract_agrees_with_core_smt(self) -> None:
        bundle = make_bundle(("HARD", "SERVICE"), (("STOP",), ("PROCEED",)))
        contracts = bound_contracts(bundle)
        trace = (frame(0.0, Truth.FALSE),)
        result = compare_bundle_trace(
            bundle, contracts, {contract_id: trace for contract_id in contracts}
        )
        self.assertTrue(result["matches"], result["mismatches"])
        self.assertEqual(
            result["core_smt"][0]["admissible_actions"],
            list(bundle.action_domain),
        )


if __name__ == "__main__":
    unittest.main()
