from pathlib import Path
import unittest

from cli.solver_runtime import configure_project_z3


ROOT = next(
    parent
    for parent in Path(__file__).resolve().parents
    if (parent / "PROJECT_REGISTRY.json").is_file()
)
configure_project_z3(ROOT)

from experiments.eblc_p0b.adapters.pilot_adapter import PILOT_PROFILE, frame, initial_frame, locked_translation_traces
from experiments.eblc_p0b.binders import bind_pedestrian_contract
from experiments.eblc_p0b.catalog import load_pilot_rule, load_predicate_spec
from experiments.eblc_p0b.mutations import MUTATION_METADATA, mutate, run_mutation_suite
from experiments.eblc_p0b.translation_validator import validate_translation
from experiments.eblc_p0b.types import Truth
from experiments.eblc_p0b.z3_bounded_checker import (
    ACTUAL_SOLVER_ENCODING,
    ENGINE,
    ENGINE_VERSION,
    bounded_queries,
    run_bounded_target,
    solver_construction_count,
)


class TranslationAndMutationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = bind_pedestrian_contract(
            load_pilot_rule(), load_predicate_spec(), initial_frame(), PILOT_PROFILE
        ).contract

    def test_locked_trace_translation_agreement_is_complete(self):
        result = validate_translation(self.contract, locked_translation_traces())
        self.assertEqual(result["canonical_runtime_agreement"], 1.0)
        self.assertEqual(result["canonical_bounded_target_agreement"], 1.0)

    def test_bounded_target_required_queries(self):
        queries = bounded_queries(self.contract, frame)
        self.assertEqual(ENGINE, "Z3_BOUNDED_SMT")
        self.assertEqual(ENGINE_VERSION, "5.0.0")
        self.assertTrue(ACTUAL_SOLVER_ENCODING)
        self.assertEqual(queries["solver_constructions"], 4)
        self.assertTrue(queries["lifecycle_transition_consistency"]["consistent"])
        self.assertEqual(queries["lifecycle_transition_consistency"]["counterexample_status"], "UNSAT")
        self.assertTrue(queries["active_stop_position_invariant_violation_witness_exists"])
        self.assertEqual(queries["active_stop_position_invariant_query_status"], "SAT")
        self.assertFalse(queries["release_hazard_reappearance_missing_reactivation_witness_exists"])
        self.assertEqual(queries["release_hazard_reappearance_query_status"], "UNSAT")
        self.assertFalse(queries["safe_progress_false_deadlock_witness_exists"])
        self.assertEqual(queries["safe_progress_false_deadlock_query_status"], "UNSAT")

    def test_fixed_trace_replay_constructs_and_queries_z3(self):
        before = solver_construction_count()
        result = run_bounded_target(self.contract, locked_translation_traces()["safe_release_reactivation"])
        self.assertTrue(result.accepted)
        self.assertGreater(solver_construction_count(), before)

    def test_symbolic_queries_flip_for_reactivation_and_deadlock_mutations(self):
        missing_reactivation = bounded_queries(mutate(self.contract, "MISSING_REACTIVATION"), frame)
        self.assertTrue(missing_reactivation["release_hazard_reappearance_missing_reactivation_witness_exists"])
        self.assertEqual(missing_reactivation["release_hazard_reappearance_query_status"], "SAT")

        false_deadlock = bounded_queries(mutate(self.contract, "FALSE_DEADLOCK"), frame)
        self.assertTrue(false_deadlock["safe_progress_false_deadlock_witness_exists"])
        self.assertEqual(false_deadlock["safe_progress_false_deadlock_query_status"], "SAT")

    def test_all_controlled_mutations_have_expected_witness(self):
        result = run_mutation_suite(self.contract)
        self.assertEqual(len(MUTATION_METADATA), 10)
        self.assertEqual(result["underconstraint"]["detected"], 5)
        self.assertEqual(result["overconstraint"]["detected"], 5)
        self.assertEqual(result["underconstraint"]["recall"], 1.0)
        self.assertEqual(result["overconstraint"]["recall"], 1.0)
        self.assertTrue(all(row["detected"] for row in result["records"]))
        self.assertTrue(all("NOT_INDEPENDENT_SAFETY_ORACLE" in row["oracle_scope"] for row in result["records"]))

    def test_normal_fixtures_have_zero_false_alarm(self):
        result = validate_translation(self.contract, {
            "inactive_nominal": (frame(0.0, Truth.FALSE, x=1.0, speed=1.0, safe_progress=True),),
            "boundary": (frame(0.0, Truth.TRUE, x=-1.5, speed=0.0),),
        })
        for row in result["records"]:
            self.assertTrue(row["canonical"]["accepted"])
            self.assertEqual(row["canonical"]["violations"], [])


if __name__ == "__main__":
    unittest.main()
