"""Deterministic robustness and metamorphic tests for public EBLC v0."""

from __future__ import annotations

import ast
from copy import deepcopy
from dataclasses import replace
from itertools import product
import json
import math
from pathlib import Path
import unittest

from src.guard_synth_eblc.adapters.synthetic_pedestrian import (
    PILOT_PROFILE,
    frame,
    initial_frame,
)
from src.guard_synth_eblc.binders import bind_pedestrian_contract
from src.guard_synth_eblc.catalog import (
    SCHEMA_ROOT,
    load_pilot_rule,
    load_predicate_spec,
)
from src.guard_synth_eblc.mutations import run_mutation_suite
from src.guard_synth_eblc.runtime_monitor import run_runtime
from src.guard_synth_eblc.schema_validation import (
    SchemaValidationError,
    load_json,
    validate,
)
from src.guard_synth_eblc.semantics import run_canonical
from src.guard_synth_eblc.translation_validator import normalized
from src.guard_synth_eblc.types import (
    EpistemicKind,
    Lifecycle,
    Truth,
    Verdict,
)
from src.guard_synth_eblc.z3_bounded_checker import run_bounded_target


ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "PROJECT_REGISTRY.json").is_file())


class RobustnessTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.rule = load_pilot_rule()
        cls.predicate = load_predicate_spec()
        outcome = bind_pedestrian_contract(
            cls.rule, cls.predicate, initial_frame(), PILOT_PROFILE
        )
        assert outcome.contract is not None
        cls.contract = outcome.contract

    def assert_targets_agree(self, frames) -> None:
        canonical = normalized(run_canonical(self.contract, frames))
        self.assertEqual(canonical, normalized(run_runtime(self.contract, frames)))
        self.assertEqual(canonical, normalized(run_bounded_target(self.contract, frames)))

    def test_schema_rejects_structural_type_enum_and_range_mutations(self) -> None:
        schema = load_json(SCHEMA_ROOT / "context_graph.schema.json")
        base = {
            "timestamp_s": 0.0,
            "hazard_fact": {
                "truth": "TRUE",
                "epistemic_kind": "OBSERVED",
                "source": "SYNTHETIC",
                "timestamp_s": 0.0,
                "maximum_age_s": 0.2,
            },
            "ego_front_x_m": -12.0,
            "ego_speed_mps": 6.0,
            "zone_entry_x_m": 0.0,
            "target_entity_id": "pedestrian:P17",
            "zone_id": "zone:CZ4",
            "coordinate_frame": "ego_path_s",
            "distance_unit": "m",
        }
        invalid = []
        extra = deepcopy(base); extra["silent_default"] = 1; invalid.append(extra)
        missing = deepcopy(base); del missing["zone_id"]; invalid.append(missing)
        enum = deepcopy(base); enum["hazard_fact"]["truth"] = "MAYBE"; invalid.append(enum)
        negative = deepcopy(base); negative["ego_speed_mps"] = -0.01; invalid.append(negative)
        boolean = deepcopy(base); boolean["ego_speed_mps"] = True; invalid.append(boolean)
        empty_source = deepcopy(base); empty_source["hazard_fact"]["source"] = ""; invalid.append(empty_source)
        for nonfinite in (math.nan, math.inf, -math.inf):
            case = deepcopy(base); case["ego_speed_mps"] = nonfinite; invalid.append(case)
        for case in invalid:
            with self.subTest(case=case):
                with self.assertRaises(SchemaValidationError):
                    validate(case, schema)
        with self.assertRaises(SchemaValidationError):
            validate({}, {"type": "object", "patternProperties": {}})

    def test_binder_abstention_and_conflict_matrix(self) -> None:
        cases = (
            (initial_frame(), None, None, Verdict.UNSUPPORTED),
            (frame(0.0, Truth.UNKNOWN), PILOT_PROFILE, None, Verdict.REVIEW_REQUIRED),
            (frame(0.0, Truth.FALSE), PILOT_PROFILE, None, Verdict.REVIEW_REQUIRED),
            (frame(0.0, Truth.CONFLICT), PILOT_PROFILE, None, Verdict.CONFLICT),
            (frame(0.0, Truth.TRUE, epistemic=EpistemicKind.CLAIMED), PILOT_PROFILE, None, Verdict.REVIEW_REQUIRED),
            (replace(initial_frame(), distance_unit="cm"), PILOT_PROFILE, None, Verdict.UNSUPPORTED),
            (replace(initial_frame(), coordinate_frame="map"), PILOT_PROFILE, None, Verdict.UNSUPPORTED),
            (replace(initial_frame(), target_entity_id=""), PILOT_PROFILE, None, Verdict.UNSUPPORTED),
            (initial_frame(), PILOT_PROFILE, "MULTIPLE_CANDIDATES", Verdict.REVIEW_REQUIRED),
        )
        for sample, profile, ambiguity, expected in cases:
            with self.subTest(expected=expected, ambiguity=ambiguity):
                outcome = bind_pedestrian_contract(
                    self.rule,
                    self.predicate,
                    sample,
                    profile,
                    target_ambiguity_reason=ambiguity,
                )
                self.assertIs(outcome.verdict, expected)

        invalid_profiles = (
            replace(PILOT_PROFILE, maximum_service_deceleration_mps2=0.0),
            replace(PILOT_PROFILE, response_time_s=-0.01),
            replace(PILOT_PROFILE, position_uncertainty_m=-0.01),
            replace(PILOT_PROFILE, evidence_ref=""),
            replace(PILOT_PROFILE, maximum_service_deceleration_mps2=math.nan),
            replace(PILOT_PROFILE, response_time_s=math.inf),
            replace(PILOT_PROFILE, position_uncertainty_m=-math.inf),
        )
        for profile in invalid_profiles:
            with self.subTest(profile=profile):
                outcome = bind_pedestrian_contract(
                    self.rule, self.predicate, initial_frame(), profile
                )
                self.assertIs(outcome.verdict, Verdict.UNSUPPORTED)

    def test_contract_schema_covers_all_runtime_numeric_inputs(self) -> None:
        schema = load_json(SCHEMA_ROOT / "eblc_contract.schema.json")
        required = set(schema["required"])
        self.assertTrue({
            "derivation_dag",
            "predicate_maximum_age_s",
            "maximum_service_deceleration_mps2",
            "response_time_s",
            "position_uncertainty_m",
        }.issubset(required))

    def test_all_targets_fail_closed_on_invalid_trace_inputs(self) -> None:
        invalid_cases = (
            ((), "EMPTY_TRACE"),
            ((frame(0.0, Truth.TRUE, speed=math.nan),), "NONFINITE_SCENE_VALUE"),
            ((frame(0.1, Truth.TRUE), frame(0.0, Truth.FALSE)), "NONMONOTONIC_TIMESTAMPS"),
            ((frame(0.0, Truth.TRUE, speed=-0.1),), "INVALID_SCENE_NUMERIC_RANGE"),
        )
        runners = (run_canonical, run_runtime, run_bounded_target)
        for frames, reason in invalid_cases:
            normalized_results = []
            for runner in runners:
                with self.subTest(runner=runner.__name__, reason=reason):
                    result = runner(self.contract, frames)
                    self.assertFalse(result.accepted)
                    self.assertIs(result.verdict, Verdict.UNSUPPORTED)
                    self.assertIn(reason, result.diagnostics)
                    normalized_results.append(normalized(result))
            self.assertEqual(normalized_results[0], normalized_results[1])
            self.assertEqual(normalized_results[0], normalized_results[2])

        invalid_contract = replace(
            self.contract,
            maximum_service_deceleration_mps2=math.nan,
        )
        for runner in runners:
            with self.subTest(runner=runner.__name__, reason="NONFINITE_BOUND_CONTRACT"):
                result = runner(invalid_contract, (frame(0.0, Truth.TRUE),))
                self.assertFalse(result.accepted)
                self.assertIs(result.verdict, Verdict.UNSUPPORTED)
                self.assertIn("NONFINITE_BOUND_CONTRACT", result.diagnostics)

    def test_all_four_valued_sequences_length_five_agree(self) -> None:
        checked = 0
        for sequence in product(tuple(Truth), repeat=5):
            frames = tuple(
                frame(index * 0.1, truth, x=-12.0, speed=0.0)
                for index, truth in enumerate(sequence)
            )
            self.assert_targets_agree(frames)
            checked += 1
        self.assertEqual(checked, 4 ** 5)

    def test_freshness_and_epistemic_matrix_agrees(self) -> None:
        ages = (-0.01, 0.0, 0.2, 0.20000001)
        for truth, epistemic, age in product(tuple(Truth), tuple(EpistemicKind), ages):
            sample = frame(
                1.0,
                truth,
                x=-12.0,
                speed=0.0,
                fact_timestamp_s=1.0 - age,
                epistemic=epistemic,
            )
            with self.subTest(truth=truth, epistemic=epistemic, age=age):
                self.assert_targets_agree((sample,))

    def test_numeric_boundary_grid_agrees_and_bound_is_monotone(self) -> None:
        bounds = []
        for position in (-20.0, -12.0, -5.0, -2.1, -2.0):
            baseline = run_canonical(
                self.contract,
                (frame(0.0, Truth.TRUE, x=position, speed=0.0),),
            )
            bound = baseline.steps[0].maximum_safe_speed_mps
            assert bound is not None
            bounds.append(bound)
            for speed in (0.0, max(0.0, bound - 1e-8), bound, bound + 5e-10, bound + 2e-9):
                with self.subTest(position=position, speed=speed):
                    self.assert_targets_agree(
                        (frame(0.0, Truth.TRUE, x=position, speed=speed),)
                    )
        self.assertEqual(bounds, sorted(bounds, reverse=True))

    def test_release_threshold_variants(self) -> None:
        for threshold in (1, 2, 3, 4):
            contract = replace(self.contract, release_clear_frames=threshold)
            frames = (frame(0.0, Truth.TRUE),) + tuple(
                frame((index + 1) * 0.1, Truth.FALSE)
                for index in range(threshold)
            )
            canonical = normalized(run_canonical(contract, frames))
            self.assertEqual(canonical, normalized(run_runtime(contract, frames)))
            self.assertEqual(canonical, normalized(run_bounded_target(contract, frames)))
            self.assertEqual(canonical["lifecycle"][-1], Lifecycle.RELEASED.value)
            if threshold > 1:
                self.assertEqual(canonical["lifecycle"][-2], Lifecycle.MAINTAINED.value)

    def test_mutation_suite_is_deterministic(self) -> None:
        first = json.dumps(run_mutation_suite(self.contract), sort_keys=True)
        second = json.dumps(run_mutation_suite(self.contract), sort_keys=True)
        self.assertEqual(first, second)

    def test_compiler_targets_do_not_import_canonical_semantics(self) -> None:
        for relative in (
            "platforms/eblc-bcv/src/guard_synth_eblc/runtime_monitor.py",
            "platforms/eblc-bcv/src/guard_synth_eblc/z3_bounded_checker.py",
        ):
            tree = ast.parse((ROOT / relative).read_text(encoding="utf-8"))
            imported = {
                node.module
                for node in ast.walk(tree)
                if isinstance(node, ast.ImportFrom)
            }
            self.assertNotIn("semantics", imported)
            self.assertNotIn("guard_synth_eblc.semantics", imported)


if __name__ == "__main__":
    unittest.main()
