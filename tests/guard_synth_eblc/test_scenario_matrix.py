from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
import json
import math
from pathlib import Path
import unittest

from cli.solver_runtime import configure_project_z3


ROOT = Path(__file__).resolve().parents[2]
configure_project_z3(ROOT)

from src.guard_synth_eblc.adapters.synthetic_pedestrian import PILOT_PROFILE, frame, initial_frame
from src.guard_synth_eblc.binders import bind_pedestrian_contract
from src.guard_synth_eblc.catalog import load_pilot_rule, load_predicate_spec
from src.guard_synth_eblc.conformance import validate_conformance
from src.guard_synth_eblc.elaborator import elaborate_program
from src.guard_synth_eblc.program import EBLCProgramValidationError, parse_program
from src.guard_synth_eblc.schema_validation import SchemaValidationError
from src.guard_synth_eblc.smt_compiler import compile_core_model, solve_assignment
from src.guard_synth_eblc.finite_state_enumerator import run_enumerator_target
from src.guard_synth_eblc.translation_validator import normalized, validate_translation
from src.guard_synth_eblc.semantics import run_canonical
from src.guard_synth_eblc.types import EpistemicKind, Truth


FIXTURE = ROOT / "src/guard_synth_eblc/fixtures/eblc_program_p0b.json"
EPSILON = 1e-9


def raw_program() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


class HighLevelProgramUnitTests(unittest.TestCase):
    def test_duplicate_program_source_is_rejected(self) -> None:
        raw = raw_program()
        raw["source_refs"].append(raw["source_refs"][0])
        with self.assertRaisesRegex(EBLCProgramValidationError, "duplicate source_refs"):
            parse_program(raw)

    def test_duplicate_derivation_node_is_rejected(self) -> None:
        raw = raw_program()
        raw["derivation_dag"].append(deepcopy(raw["derivation_dag"][0]))
        with self.assertRaisesRegex(EBLCProgramValidationError, "duplicate derivation node"):
            parse_program(raw)

    def test_invalid_numeric_ranges_are_rejected(self) -> None:
        mutations = (
            ("deceleration", 0.0, "deceleration must be positive"),
            ("response_time", -0.1, "response time must be nonnegative"),
            ("position_uncertainty", -0.1, "position uncertainty must be nonnegative"),
            ("time_epsilon", -0.1, "epsilon values must be nonnegative"),
        )
        for field, value, message in mutations:
            with self.subTest(field=field):
                raw = raw_program()
                raw["constraints"][field]["value"] = value
                with self.assertRaisesRegex(EBLCProgramValidationError, message):
                    parse_program(raw)

    def test_nonfinite_quantity_is_rejected_by_schema_layer(self) -> None:
        raw = raw_program()
        raw["constraints"]["deceleration"]["value"] = float("inf")
        with self.assertRaises(SchemaValidationError):
            parse_program(raw)

    def test_priority_cannot_be_silently_replaced_by_scalar_weight(self) -> None:
        raw = raw_program()
        raw["priority"]["weight"] = 0.7
        with self.assertRaisesRegex(SchemaValidationError, "unexpected fields"):
            parse_program(raw)

    def test_empty_evidence_on_quantity_is_rejected(self) -> None:
        raw = raw_program()
        raw["constraints"]["stop_position"]["evidence_refs"] = []
        with self.assertRaisesRegex(SchemaValidationError, "array is too short"):
            parse_program(raw)


class PolicyVariantIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        outcome = bind_pedestrian_contract(
            load_pilot_rule(), load_predicate_spec(), initial_frame(), PILOT_PROFILE
        )
        if outcome.contract is None:
            raise AssertionError(outcome.reason_codes)
        cls.contract = outcome.contract

    def _run_variant(
        self,
        trace_id: str,
        samples: tuple,
        *,
        lifecycle: dict | None = None,
        constraints: dict | None = None,
        contract: dict | None = None,
    ) -> dict:
        raw = raw_program()
        raw["frames"] = max(len(samples), 1)
        if lifecycle:
            raw["lifecycle"].update(lifecycle)
        if constraints:
            raw["constraints"].update(constraints)
        program = parse_program(raw)
        bound = replace(self.contract, **(contract or {}))
        result = validate_conformance(bound, program, {trace_id: samples})
        self.assertEqual(result["trace_agreement"], 1.0, result["records"][0]["mismatches"])
        translation = validate_translation(bound, {trace_id: samples})
        self.assertEqual(translation["canonical_runtime_agreement"], 1.0)
        self.assertEqual(translation["canonical_bounded_target_agreement"], 1.0)
        self.assertEqual(
            normalized(run_canonical(bound, samples)),
            normalized(run_enumerator_target(bound, samples)),
        )
        return result["records"][0]

    def test_policy_variant_matrix(self) -> None:
        cases = (
            {
                "name": "release_disabled",
                "samples": (frame(0.0, Truth.TRUE), frame(0.1, Truth.FALSE), frame(0.2, Truth.FALSE)),
                "lifecycle": {"release_enabled": False},
                "contract": {"release_enabled": False},
                "expected": {"state": "MAINTAINED"},
            },
            {
                "name": "reactivation_disabled",
                "samples": (frame(0.0, Truth.TRUE), frame(0.1, Truth.FALSE), frame(0.2, Truth.FALSE), frame(0.3, Truth.TRUE)),
                "lifecycle": {"reactivation_enabled": False},
                "contract": {"reactivation_enabled": False},
                "expected": {"state": "RELEASED"},
            },
            {
                "name": "unknown_as_false",
                "samples": (frame(0.0, Truth.TRUE), frame(0.1, Truth.UNKNOWN)),
                "lifecycle": {"unknown_policy": "AS_FALSE"},
                "contract": {"unknown_policy": "AS_FALSE"},
                "expected": {"state": "MAINTAINED", "verdict": "VALIDATED"},
            },
            {
                "name": "unknown_as_true",
                "samples": (frame(0.0, Truth.UNKNOWN),),
                "lifecycle": {"unknown_policy": "AS_TRUE"},
                "contract": {"unknown_policy": "AS_TRUE"},
                "expected": {"state": "ACTIVE", "verdict": "REVIEW_REQUIRED"},
            },
            {
                "name": "always_active",
                "samples": (frame(0.0, Truth.FALSE),),
                "lifecycle": {"always_active": True},
                "contract": {"always_active": True},
                "expected": {"state": "MAINTAINED", "progress_allowed": False},
            },
            {
                "name": "explicit_expiry",
                "samples": (frame(0.0, Truth.TRUE), frame(0.2, Truth.TRUE)),
                "lifecycle": {"expiry_timestamp_s": 0.15},
                "contract": {"expiry_timestamp_s": 0.15},
                "expected": {"state": "EXPIRED", "progress_allowed": True},
            },
            {
                "name": "invariant_disabled",
                "samples": (frame(0.0, Truth.TRUE, x=-1.0, speed=20.0),),
                "constraints": {"enforce_invariant": False},
                "contract": {"enforce_invariant": False},
                "expected": {"entry_violation": False, "speed_violation": False},
            },
            {
                "name": "forced_deadlock",
                "samples": (frame(0.0, Truth.FALSE, safe_progress=True),),
                "constraints": {"force_deadlock": True},
                "contract": {"force_deadlock": True},
                "expected": {"deadlock_violation": True, "progress_allowed": False},
            },
            {
                "name": "one_clear_releases",
                "samples": (frame(0.0, Truth.TRUE), frame(0.1, Truth.FALSE)),
                "lifecycle": {"release_clear_frames": 1},
                "contract": {"release_clear_frames": 1},
                "expected": {"state": "RELEASED"},
            },
        )
        for case in cases:
            with self.subTest(case=case["name"]):
                record = self._run_variant(
                    case["name"], case["samples"],
                    lifecycle=case.get("lifecycle"), constraints=case.get("constraints"),
                    contract=case.get("contract"),
                )
                final = record["core_smt"][-1]
                for field, expected in case["expected"].items():
                    self.assertEqual(final[field], expected)

    def test_position_freshness_and_speed_boundary_matrix(self) -> None:
        stop = self.contract.stop_position_x_m
        traces: dict[str, tuple] = {}
        for index, offset in enumerate((-2 * EPSILON, -EPSILON, 0.0, EPSILON, 2 * EPSILON)):
            traces[f"position_{index}"] = (frame(0.0, Truth.TRUE, x=stop + offset, speed=0.0),)
        for index, age_offset in enumerate((-2 * EPSILON, -EPSILON, 0.0, EPSILON, 2 * EPSILON)):
            timestamp = 1.0
            age = self.contract.predicate_maximum_age_s + age_offset
            traces[f"stale_boundary_{index}"] = (
                frame(timestamp, Truth.TRUE, fact_timestamp_s=timestamp - age, speed=0.0),
            )
        for index, future_age in enumerate((-2 * EPSILON, -EPSILON, -0.5 * EPSILON, 0.0)):
            traces[f"future_boundary_{index}"] = (
                frame(1.0, Truth.TRUE, fact_timestamp_s=1.0 - future_age, speed=0.0),
            )
        for x in (-12.0, -5.0, -2.1):
            available = self.contract.stop_position_x_m - x - self.contract.position_uncertainty_m
            deceleration = self.contract.maximum_service_deceleration_mps2
            response = self.contract.response_time_s
            maximum = max(0.0, -deceleration * response + math.sqrt((deceleration * response) ** 2 + 2.0 * deceleration * available))
            for offset in (-2 * EPSILON, 0.0, 2 * EPSILON):
                traces[f"speed_{x}_{offset}"] = (
                    frame(0.0, Truth.TRUE, x=x, speed=max(0.0, maximum + offset)),
                )
        program = parse_program(raw_program())
        result = validate_conformance(self.contract, program, traces)
        self.assertEqual(result["trace_count"], len(traces))
        self.assertEqual(result["trace_agreement"], 1.0)
        self.assertEqual(result["frame_agreement"], 1.0)
        translation = validate_translation(self.contract, traces)
        self.assertEqual(translation["canonical_runtime_agreement"], 1.0)
        self.assertEqual(translation["canonical_bounded_target_agreement"], 1.0)
        for trace_id, samples in traces.items():
            with self.subTest(target="enumerator", trace=trace_id):
                self.assertEqual(
                    normalized(run_canonical(self.contract, samples)),
                    normalized(run_enumerator_target(self.contract, samples)),
                )

    def test_combined_scope_and_input_failure_precedence(self) -> None:
        record = self._run_variant(
            "scope_and_unit_failure",
            (frame(0.0, Truth.TRUE, scope_valid=False, distance_unit="cm"),),
        )
        final = record["core_smt"][-1]
        self.assertEqual(final["state"], "EXPIRED")
        self.assertEqual(final["verdict"], "UNSUPPORTED")
        self.assertFalse(final["progress_allowed"])

    def test_narrow_epistemic_policy_fails_disallowed_source_to_unknown(self) -> None:
        raw = raw_program()
        raw["frames"] = 1
        raw["predicate"]["allowed_epistemic"] = ["OBSERVED"]
        elaborated = elaborate_program(parse_program(raw))
        compiled = compile_core_model(elaborated.core_model)
        solved = solve_assignment(compiled, {
            ("raw_truth", 0): "TRUE",
            ("epistemic", 0): "PREDICTED",
            ("timestamp", 0): 0.0,
            ("fact_timestamp", 0): 0.0,
            ("fact_maximum_age", 0): 0.2,
        })
        self.assertEqual(solved["status"], "SAT")
        names = {
            (item["declaration"], item["time"]): item["smt_symbol"]
            for item in compiled.symbol_table["symbols"]
        }
        self.assertEqual(solved["witness"][names[("effective_truth", 0)]], "UNKNOWN")

    def test_one_frame_horizon_executes(self) -> None:
        raw = raw_program()
        raw["frames"] = 1
        result = validate_conformance(
            self.contract, parse_program(raw), {"single": (frame(0.0, Truth.TRUE),)}
        )
        self.assertEqual(result["trace_agreement"], 1.0)
        self.assertEqual(result["frame_count"], 1)


if __name__ == "__main__":
    unittest.main()
