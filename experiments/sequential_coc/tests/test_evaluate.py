"""Separated-domain evaluation and conservative claim-gate tests."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
import tempfile
import unittest

from experiments.sequential_coc.evaluate import (
    EvaluationInputs,
    collect_uppaal_evidence,
    cohens_kappa,
    evaluate_all,
    wilson_interval,
)


MUTATION_TYPES = (
    "HOLD_GO_CONFLICT",
    "PREMATURE_RELEASE",
    "ORDER_VIOLATION",
    "STALE_OBLIGATION",
)


def _result(verdict: str) -> dict[str, object]:
    return {
        "verdict": verdict,
        "contradiction_types": [],
        "first_event_id": None,
        "state_trace": [],
        "unknown_reasons": [],
    }


def _mutation_pairs() -> tuple[dict[str, object], ...]:
    rows = []
    for type_index, mutation_type in enumerate(MUTATION_TYPES):
        for number in range(10):
            local_detected = type_index in {0, 1}
            rows.append(
                {
                    "pair_id": f"pair-{type_index}-{number}",
                    "cluster_id": f"cluster-{type_index}-{number}",
                    "oracle": mutation_type,
                    "checker_results": {
                        "original": {
                            "event_local": _result("CONSISTENT"),
                            "stateful": _result("CONSISTENT"),
                        },
                        "mutated": {
                            "event_local": _result(
                                "CONTRADICTION" if local_detected else "CONSISTENT"
                            ),
                            "stateful": _result("CONTRADICTION"),
                        },
                    },
                }
            )
    return tuple(rows)


def _review_rows(*, one_disagreement: bool = False) -> tuple[dict[str, str], ...]:
    rows = []
    for number in range(27):
        rows.append(
            {
                "review_id": f"REV-{number:016x}",
                "temporal_requirement_explicit": "YES",
                "required_action_sequence": "STOP_OR_HOLD>ACCELERATE_OR_PROCEED",
                "textual_consistency": (
                    "TEXTUAL_CONTRADICTION"
                    if one_disagreement and number == 0
                    else "TEXTUALLY_CONSISTENT"
                ),
            }
        )
    return tuple(rows)


def fixture_inputs(*, actual_verifyta_ran: bool = True) -> EvaluationInputs:
    return EvaluationInputs(
        mutation_pairs=_mutation_pairs(),
        natural_cluster_ids=tuple(f"cluster-{number}" for number in range(27)),
        review_labels_a=_review_rows(),
        review_labels_b=_review_rows(one_disagreement=True),
        consensus_labels=_review_rows(),
        trajectory_summary={
            "sample_units": {"event": 403, "scene_cluster": 94},
            "linked_event_count": 403,
            "verdict_counts": {
                "event": {
                    "baseline": {"ALIGNED": 107, "NOT_ALIGNED": 47, "UNKNOWN": 249},
                    "strict": {"ALIGNED": 71, "NOT_ALIGNED": 21, "UNKNOWN": 311},
                    "lenient": {"ALIGNED": 107, "NOT_ALIGNED": 48, "UNKNOWN": 248},
                },
                "scene_cluster": {
                    "baseline": {"ALIGNED": 6, "NOT_ALIGNED": 28, "UNKNOWN": 60},
                    "strict": {"ALIGNED": 2, "NOT_ALIGNED": 10, "UNKNOWN": 82},
                    "lenient": {"ALIGNED": 7, "NOT_ALIGNED": 29, "UNKNOWN": 58},
                },
            },
            "verdict_change_counts": {"event": 78, "scene_cluster": 25},
        },
        uppaal_mismatch_count=0,
        actual_verifyta_ran=actual_verifyta_ran,
        uppaal_evaluated_count=7 if actual_verifyta_ran else 0,
    )


class EvaluateTests(unittest.TestCase):
    def test_natural_mutation_and_trajectory_results_never_share_denominators(self):
        result = evaluate_all(fixture_inputs())

        self.assertEqual(result["controlled_mutation"]["pair_count"], 40)
        self.assertEqual(result["natural_contract_review"]["cluster_count"], 27)
        self.assertEqual(result["trajectory_exploratory"]["scene_cluster_count"], 94)
        self.assertIn("UNKNOWN", result["trajectory_exploratory"]["verdict_counts"])
        self.assertEqual(
            result["sample_unit_boundaries"],
            {
                "controlled_mutation": "PAIR",
                "natural_contract_review": "SCENE_CLUSTER",
                "trajectory_exploratory": "SCENE_CLUSTER_PRIMARY_EVENT_SECONDARY",
            },
        )

    def test_claim_gate_never_promotes_text_review_to_actual_state_ground_truth(self):
        gate = evaluate_all(fixture_inputs())["claim_gate"]

        self.assertFalse(gate["NATURAL_ACTUAL_STATE_READY"])
        self.assertTrue(gate["MUTATION_EVALUABLE"])
        self.assertTrue(gate["NATURAL_QUANTITATIVE_READY"])
        self.assertFalse(gate["GLOBAL_COC_MODEL_CLAIM"])
        self.assertFalse(gate["PHYSICAL_SAFETY_CLAIM"])
        self.assertFalse(gate["LEARNING_PERFORMANCE_CLAIM"])

    def test_uppaal_gate_requires_actual_runtime_evidence(self):
        gate = evaluate_all(fixture_inputs(actual_verifyta_ran=False))["claim_gate"]

        self.assertFalse(gate["UPPAAL_EQUIVALENT"])

    def test_verifyta_execution_evidence_requires_successful_subprocesses(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            successful = root / "successful-verifyta"
            successful.write_text(
                "#!/bin/sh\n"
                "if [ \"$1\" = \"--version\" ]; then echo 'UPPAAL test 1.0'; exit 0; fi\n"
                "i=0\n"
                "while [ $i -lt 6 ]; do echo 'Formula is satisfied.'; i=$((i+1)); done\n",
                encoding="utf-8",
            )
            successful.chmod(0o700)
            ran = collect_uppaal_evidence(successful)
            self.assertTrue(ran.actual_verifyta_ran)
            self.assertEqual(ran.evaluated_count, 7)
            self.assertGreater(ran.mismatch_count, 0)

            failed = root / "failed-verifyta"
            failed.write_text("#!/bin/sh\necho 'license failure' >&2\nexit 7\n", encoding="utf-8")
            failed.chmod(0o700)
            not_run = collect_uppaal_evidence(failed)
            self.assertFalse(not_run.actual_verifyta_ran)
            self.assertEqual(not_run.evaluated_count, 0)
            self.assertIsNone(not_run.mismatch_count)

    def test_missing_human_consensus_keeps_natural_metrics_not_run(self):
        fixture = fixture_inputs()
        waiting = EvaluationInputs(
            mutation_pairs=fixture.mutation_pairs,
            natural_cluster_ids=fixture.natural_cluster_ids,
            review_labels_a=None,
            review_labels_b=None,
            consensus_labels=None,
            trajectory_summary=fixture.trajectory_summary,
        )

        result = evaluate_all(waiting)
        self.assertEqual(result["status"], "WAITING_FOR_CONTRACT_REVIEW")
        self.assertEqual(result["natural_contract_review"]["status"], "NOT_RUN")
        self.assertEqual(result["natural_contract_review"]["agreement_by_field"], "NOT_RUN")
        self.assertEqual(result["natural_contract_review"]["kiee_update"], "NOT_RUN")
        self.assertEqual(result["natural_contract_review"]["paper_update_gate"], "CLOSED")
        self.assertFalse(result["claim_gate"]["NATURAL_CONTRACT_DESCRIPTIVE"])

    def test_paper_update_gate_requires_all_core_prerequisites(self):
        fixture = fixture_inputs()
        skewed = [dict(row) for row in fixture.mutation_pairs]
        skewed[0] = {**skewed[0], "oracle": "PREMATURE_RELEASE"}
        no_trajectory = {
            **fixture.trajectory_summary,
            "linked_event_count": 0,
        }
        cases = (
            (
                "uppaal_false",
                EvaluationInputs(
                    mutation_pairs=fixture.mutation_pairs,
                    natural_cluster_ids=fixture.natural_cluster_ids,
                    review_labels_a=fixture.review_labels_a,
                    review_labels_b=fixture.review_labels_b,
                    consensus_labels=fixture.consensus_labels,
                    trajectory_summary=fixture.trajectory_summary,
                    uppaal_mismatch_count=0,
                    actual_verifyta_ran=False,
                ),
            ),
            (
                "mutation_false",
                EvaluationInputs(
                    mutation_pairs=skewed,
                    natural_cluster_ids=fixture.natural_cluster_ids,
                    review_labels_a=fixture.review_labels_a,
                    review_labels_b=fixture.review_labels_b,
                    consensus_labels=fixture.consensus_labels,
                    trajectory_summary=fixture.trajectory_summary,
                    uppaal_mismatch_count=0,
                    actual_verifyta_ran=True,
                    uppaal_evaluated_count=7,
                ),
            ),
            (
                "trajectory_false",
                EvaluationInputs(
                    mutation_pairs=fixture.mutation_pairs,
                    natural_cluster_ids=fixture.natural_cluster_ids,
                    review_labels_a=fixture.review_labels_a,
                    review_labels_b=fixture.review_labels_b,
                    consensus_labels=fixture.consensus_labels,
                    trajectory_summary=no_trajectory,
                    uppaal_mismatch_count=0,
                    actual_verifyta_ran=True,
                    uppaal_evaluated_count=7,
                ),
            ),
        )
        for name, inputs in cases:
            with self.subTest(name=name):
                result = evaluate_all(inputs)
                self.assertTrue(result["claim_gate"]["NATURAL_CONTRACT_DESCRIPTIVE"])
                self.assertEqual(
                    result["natural_contract_review"]["paper_update_gate"], "CLOSED"
                )
                self.assertEqual(
                    result["natural_contract_review"]["kiee_update"], "NOT_RUN"
                )

    def test_paper_update_gate_distinguishes_descriptive_and_quantitative_scope(self):
        fixture = fixture_inputs()
        low_quant_consensus = tuple(
            {
                **row,
                "textual_consistency": (
                    "UNKNOWN_EXTERNAL_EVIDENCE_REQUIRED"
                    if index >= 19
                    else "TEXTUALLY_CONSISTENT"
                ),
            }
            for index, row in enumerate(fixture.consensus_labels or ())
        )
        descriptive_only_inputs = EvaluationInputs(
            mutation_pairs=fixture.mutation_pairs,
            natural_cluster_ids=fixture.natural_cluster_ids,
            review_labels_a=fixture.review_labels_a,
            review_labels_b=fixture.review_labels_b,
            consensus_labels=low_quant_consensus,
            trajectory_summary=fixture.trajectory_summary,
            uppaal_mismatch_count=0,
            actual_verifyta_ran=True,
            uppaal_evaluated_count=7,
        )

        descriptive = evaluate_all(descriptive_only_inputs)
        quantitative = evaluate_all(fixture)
        self.assertFalse(descriptive["claim_gate"]["NATURAL_QUANTITATIVE_READY"])
        self.assertEqual(
            descriptive["natural_contract_review"]["paper_update_gate"],
            "OPEN_DESCRIPTIVE_ONLY",
        )
        self.assertEqual(
            descriptive["natural_contract_review"]["paper_update_scope"],
            "DESCRIPTIVE_NATURAL_RESULTS_ONLY_NO_NATURAL_QUANTITATIVE_RESULTS",
        )
        self.assertTrue(quantitative["claim_gate"]["NATURAL_QUANTITATIVE_READY"])
        self.assertEqual(
            quantitative["natural_contract_review"]["paper_update_gate"], "OPEN"
        )
        self.assertFalse(quantitative["claim_gate"]["NATURAL_ACTUAL_STATE_READY"])
        self.assertFalse(quantitative["claim_gate"]["PHYSICAL_SAFETY_CLAIM"])

    def test_controlled_metrics_use_pairs_and_report_stateful_increment(self):
        controlled = evaluate_all(fixture_inputs())["controlled_mutation"]

        self.assertEqual(
            Counter(row["total"] for row in controlled["detection_by_type"].values()),
            Counter({10: 4}),
        )
        self.assertEqual(controlled["stateful_detection"]["detected"], 40)
        self.assertEqual(controlled["event_local_detection"]["detected"], 20)
        self.assertEqual(controlled["stateful_additional_detection"]["detected"], 20)
        self.assertEqual(controlled["original_false_positive"]["stateful"]["count"], 0)

    def test_mutation_gate_requires_exact_four_by_ten_stratification(self):
        fixture = fixture_inputs()
        valid = evaluate_all(fixture)
        self.assertTrue(valid["claim_gate"]["MUTATION_EVALUABLE"])
        self.assertEqual(valid["controlled_mutation"]["stratification_status"], "READY")

        cases = {}
        skewed = [dict(row) for row in fixture.mutation_pairs]
        skewed[0] = {**skewed[0], "oracle": "PREMATURE_RELEASE"}
        cases["skewed"] = skewed
        missing = [dict(row) for row in fixture.mutation_pairs]
        missing[:10] = [{**row, "oracle": "PREMATURE_RELEASE"} for row in missing[:10]]
        cases["missing"] = missing
        extra = [dict(row) for row in fixture.mutation_pairs]
        extra[0] = {**extra[0], "oracle": "UNDECLARED_MUTATION"}
        cases["extra"] = extra

        for name, pairs in cases.items():
            with self.subTest(name=name):
                inputs = EvaluationInputs(
                    mutation_pairs=pairs,
                    natural_cluster_ids=fixture.natural_cluster_ids,
                    review_labels_a=fixture.review_labels_a,
                    review_labels_b=fixture.review_labels_b,
                    consensus_labels=fixture.consensus_labels,
                    trajectory_summary=fixture.trajectory_summary,
                )
                result = evaluate_all(inputs)
                self.assertFalse(result["claim_gate"]["MUTATION_EVALUABLE"])
                self.assertEqual(
                    result["controlled_mutation"]["stratification_status"],
                    "NOT_READY_INVALID_STRATIFICATION",
                )

    def test_wilson_and_kappa_have_hand_checked_boundary_behavior(self):
        lower, upper = wilson_interval(10, 10)
        self.assertAlmostEqual(lower, 0.7224672001)
        self.assertEqual(upper, 1.0)
        self.assertEqual(wilson_interval(0, 40)[0], 0.0)
        self.assertEqual(wilson_interval(40, 40)[1], 1.0)
        self.assertAlmostEqual(cohens_kappa(("A", "A", "B", "B"), ("A", "B", "B", "B")), 0.5)
        self.assertIsNone(cohens_kappa(("A", "A"), ("A", "A")))


if __name__ == "__main__":
    unittest.main()
