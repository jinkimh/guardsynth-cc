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
from src.guard_synth_eblc.catalog import load_pilot_rule, load_predicate_spec
from src.guard_synth_eblc.conformance import generated_p0b_conformance_suite, validate_conformance
from src.guard_synth_eblc.core_ir import CoreIRValidationError
from src.guard_synth_eblc.elaborator import elaborate_program
from src.guard_synth_eblc.program import EBLCProgramValidationError, load_program, parse_program
from src.guard_synth_eblc.smt_compiler import SMTCompilationError, compile_core_model, solve_assignment
from src.guard_synth_eblc.types import Truth


FIXTURE = ROOT / "platforms/eblc-bcv/src/guard_synth_eblc/fixtures/eblc_program_p0b.json"


def raw_program() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


class ElaborationConformanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.program = load_program(FIXTURE)
        binding = bind_pedestrian_contract(
            load_pilot_rule(), load_predicate_spec(), initial_frame(), PILOT_PROFILE
        )
        if binding.contract is None:
            raise AssertionError(binding.reason_codes)
        cls.contract = binding.contract
        cls.elaborated = elaborate_program(cls.program)
        cls.compiled = compile_core_model(cls.elaborated.core_model)
        cls.conformance = validate_conformance(
            cls.contract, cls.program, generated_p0b_conformance_suite()
        )

    def test_high_level_fixture_contains_no_core_formula_ast(self) -> None:
        raw = raw_program()
        self.assertNotIn("formula", json.dumps(raw))
        self.assertEqual(raw["program_version"], "eblc-program-v0.1")

    def test_elaborator_generates_freshness_lifecycle_verdict_and_violations(self) -> None:
        clause_ids = {item.clause_id for item in self.elaborated.core_model.clauses}
        self.assertTrue({
            "effective_truth_from_freshness_and_epistemic",
            "generated_lifecycle_transition",
            "generated_clear_counter_transition",
            "generated_verdict",
            "generated_entry_violation",
            "generated_speed_violation",
            "generated_deadlock_violation",
            "generated_progress_permission",
        }.issubset(clause_ids))
        self.assertEqual(self.elaborated.core_model.horizon, self.program.frames + 1)

    def test_all_generated_traces_match_canonical(self) -> None:
        self.assertEqual(self.conformance["trace_count"], 129)
        self.assertEqual(self.conformance["frame_count"], 266)
        self.assertEqual(self.conformance["trace_agreement"], 1.0)
        self.assertEqual(self.conformance["frame_agreement"], 1.0)

    def test_conformance_includes_open_world_and_boundary_cases(self) -> None:
        records = {item["trace_id"]: item for item in self.conformance["records"]}
        for trace_id in (
            "epistemic_TRUE_CLAIMED_fresh",
            "epistemic_TRUE_OBSERVED_stale",
            "epistemic_TRUE_OBSERVED_future",
            "unit_mismatch",
            "coordinate_mismatch",
            "target_mismatch",
            "entry_boundary_equal",
            "entry_boundary_above",
        ):
            self.assertTrue(records[trace_id]["matches"], trace_id)

    def test_release_threshold_is_elaborated_from_policy(self) -> None:
        raw = raw_program()
        raw["lifecycle"]["release_clear_frames"] = 3
        program = parse_program(raw)
        contract = replace(self.contract, release_clear_frames=3)
        trace = {
            "release_three": (
                frame(0.0, Truth.TRUE), frame(0.1, Truth.FALSE),
                frame(0.2, Truth.FALSE), frame(0.3, Truth.FALSE),
            )
        }
        result = validate_conformance(contract, program, trace)
        self.assertEqual(result["trace_agreement"], 1.0)
        final = result["records"][0]["core_smt"][-1]
        self.assertEqual(final["state"], "RELEASED")

    def test_missing_fallback_approval_is_represented_as_review_not_hold(self) -> None:
        raw = raw_program()
        raw["lifecycle"]["fallback_approved"] = False
        program = parse_program(raw)
        contract = replace(self.contract, fallback_approved=False)
        result = validate_conformance(
            contract,
            program,
            {"unapproved_unknown": (frame(0.0, Truth.TRUE), frame(0.1, Truth.UNKNOWN))},
        )
        self.assertEqual(result["trace_agreement"], 1.0)
        final = result["records"][0]["core_smt"][-1]
        self.assertEqual(final["state"], "ACTIVE")
        self.assertEqual(final["verdict"], "REVIEW_REQUIRED")

    def test_claimed_cannot_be_promoted_to_activation_source(self) -> None:
        raw = raw_program()
        raw["predicate"]["allowed_epistemic"].append("CLAIMED")
        with self.assertRaisesRegex(EBLCProgramValidationError, "CLAIMED cannot"):
            parse_program(raw)

    def test_unknown_evidence_reference_fails_closed(self) -> None:
        raw = raw_program()
        raw["constraints"]["deceleration"]["evidence_refs"] = ["MISSING-SOURCE"]
        with self.assertRaisesRegex(EBLCProgramValidationError, "unknown evidence refs"):
            parse_program(raw)

    def test_high_level_unit_error_is_rejected_during_elaboration(self) -> None:
        raw = raw_program()
        raw["constraints"]["speed_epsilon"]["unit"] = "m"
        with self.assertRaisesRegex(CoreIRValidationError, "unit mismatch"):
            elaborate_program(parse_program(raw))

    def test_assignment_api_rejects_invalid_enum_label(self) -> None:
        with self.assertRaisesRegex(SMTCompilationError, "invalid ENUM assignment"):
            solve_assignment(self.compiled, {("raw_truth", 0): "NOT_A_TRUTH"})

    def test_priority_is_preserved_without_scalarization(self) -> None:
        priority = self.elaborated.elaboration_map["generated_from"]["priority"]
        self.assertEqual(priority["class"], "MANDATORY_SYSTEM")
        self.assertFalse(priority["compiled_as_scalar_weight"])


if __name__ == "__main__":
    unittest.main()
