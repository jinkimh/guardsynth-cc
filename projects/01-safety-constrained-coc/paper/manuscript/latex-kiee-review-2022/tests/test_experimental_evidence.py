"""Independent recomputation checks for every quantitative manuscript claim."""

from __future__ import annotations

import csv
import json
import statistics
import unittest
from collections import defaultdict
from pathlib import Path
from typing import Any


PAPER = Path(__file__).resolve().parents[1]
REPO = next(parent for parent in Path(__file__).resolve().parents if (parent / "PROJECT_REGISTRY.json").is_file())
VLM = REPO / "artifacts/results/public/small-vlm-guard-v0"


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def rate(rows: list[dict[str, Any]], key: str) -> float:
    return sum(bool(row[key]) for row in rows) / len(rows)


def pair_accuracy(rows: list[dict[str, Any]], key_fields: tuple[str, ...]) -> float:
    pairs: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        pairs[tuple(row[key] for key in key_fields)].append(row)
    if not pairs or any(len(pair) != 2 for pair in pairs.values()):
        raise AssertionError("every paired-contract group must contain exactly two rows")
    return sum(all(row["correct"] for row in pair) for pair in pairs.values()) / len(pairs)


class ExperimentalEvidenceTests(unittest.TestCase):
    """Recompute metrics from prediction rows instead of trusting summaries."""

    def assert_close(self, actual: float, expected: float) -> None:
        self.assertAlmostEqual(actual, expected, places=12)

    def test_temporal_rows_and_multiseed_summary(self) -> None:
        run_names = {
            "COC_ONLY": "temporal-coc-only-seed{seed}-v0",
            "INLINE_NL_CONSTRAINT": "temporal-rich-coc-seed{seed}-v0",
            "SEPARATE_NL_GUARD": "temporal-natural-guard-seed{seed}-v0",
            "SHUFFLED_GUARD": "temporal-shuffled-guard-seed{seed}-v0",
            "LOGIC_GUARD": "temporal-logic-guard-seed{seed}-v0",
        }
        summary = load(VLM / "temporal-guard-multiseed-v0/summary.json")
        for condition, pattern in run_names.items():
            by_split: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
            for seed in (42, 17, 123):
                result = load(VLM / pattern.format(seed=seed) / "result.json")
                self.assertEqual(result["seed"], seed)
                self.assertEqual(result["train_scenes"], 192)
                self.assertEqual(result["train_examples"], 384)
                scene_sets = []
                for split in ("post_test", "post_paraphrase", "post_unseen"):
                    stored = result[split]
                    rows = stored["rows"]
                    self.assertEqual(len(rows), 96)
                    self.assertEqual(
                        {row["contract_level"] for row in rows}, {"short", "long"}
                    )
                    scene_sets.append({int(row["scene_id"]) for row in rows})
                    recomputed = {
                        "accuracy": rate(rows, "correct"),
                        "guard_violation_rate": rate(rows, "guard_violation"),
                        "deadlock_rate": rate(rows, "deadlock"),
                        "safe_goal_completion_rate": rate(rows, "safe_goal_complete"),
                        "contract_swap_pair_accuracy": pair_accuracy(rows, ("scene_id",)),
                    }
                    for metric, value in recomputed.items():
                        self.assert_close(value, float(stored[metric]))
                        by_split[split][metric].append(value)
                self.assertTrue(scene_sets[0].isdisjoint(scene_sets[1]))
                self.assertTrue(scene_sets[0].isdisjoint(scene_sets[2]))
                self.assertTrue(scene_sets[1].isdisjoint(scene_sets[2]))
            for split, metrics in by_split.items():
                for metric, values in metrics.items():
                    aggregate = summary["aggregate"][condition][split][metric]
                    self.assertEqual(values, aggregate["values"])
                    self.assert_close(statistics.mean(values), aggregate["mean"])
                    self.assert_close(statistics.pstdev(values), aggregate["pstdev"])

    def test_maneuver_rows_and_multiseed_summary(self) -> None:
        run_names = {
            "Requirement CoC": "maneuver-coc-only-seed{seed}-v0",
            "Safety-Constrained CoC": "maneuver-inline-constraint-seed{seed}-v0",
            "Shuffled constraint": "maneuver-shuffled-constraint-seed{seed}-v0",
        }
        summary = load(VLM / "maneuver-guard-multiseed-v0/summary.json")
        wrong_inline_hard: list[dict[str, Any]] = []
        for condition, pattern in run_names.items():
            values: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
            for seed in (42, 17, 123):
                run_dir = VLM / pattern.format(seed=seed)
                regular = load(run_dir / "result.json")
                hard = load(run_dir / "hard_eval.json")["post_hard"]
                self.assertEqual(regular["train_scenes"], 192)
                self.assertEqual(regular["train_examples"], 384)
                split_values = {
                    "test": regular["post_test"],
                    "paraphrase": regular["post_paraphrase"],
                    "unseen": regular["post_unseen"],
                    "hard": hard,
                }
                scene_sets = []
                for split, stored in split_values.items():
                    rows = stored["rows"]
                    self.assertEqual(len(rows), 96)
                    scene_sets.append({int(row["scene_id"]) for row in rows})
                    self.assertEqual(
                        {row["contract_level"] for row in rows},
                        {"permissive", "restrictive"},
                    )
                    recomputed = {
                        "accuracy": rate(rows, "correct"),
                        "guard_violation_rate": rate(rows, "guard_violation"),
                        "deadlock_rate": rate(rows, "deadlock"),
                        "safe_goal_completion_rate": rate(rows, "safe_goal_complete"),
                        "contract_swap_pair_accuracy": pair_accuracy(rows, ("scene_id",)),
                    }
                    for metric, value in recomputed.items():
                        self.assert_close(value, float(stored[metric]))
                        values[split][metric].append(value)
                    if condition == "Safety-Constrained CoC" and split == "hard":
                        wrong_inline_hard.extend(row for row in rows if not row["correct"])
                for left in range(len(scene_sets)):
                    for right in range(left + 1, len(scene_sets)):
                        self.assertTrue(scene_sets[left].isdisjoint(scene_sets[right]))
            for split, metrics in values.items():
                for metric, seed_values in metrics.items():
                    aggregate = summary["aggregate"][condition][split][metric]
                    self.assertEqual(seed_values, aggregate["values"])
                    self.assert_close(statistics.mean(seed_values), aggregate["mean"])
                    self.assert_close(statistics.stdev(seed_values), aggregate["sample_std"])
        self.assertEqual(len(wrong_inline_hard), 15)
        self.assertTrue(
            all("cm/" in row["constraint_text"] or " cm." in row["constraint_text"]
                for row in wrong_inline_hard)
        )

    def test_saved_adapter_reproduction_and_image_ablation(self) -> None:
        recheck = VLM / "recheck-20260810"
        aggregate: dict[tuple[str, str, str, str], list[float]] = defaultdict(list)
        task_splits = {
            "temporal": ("test", "unseen"),
            "maneuver": ("test", "unseen", "hard"),
        }
        for task, splits in task_splits.items():
            for seed in (42, 17, 123):
                name = f"temporal-rich-seed{seed}.json" if task == "temporal" else f"maneuver-inline-seed{seed}.json"
                result = load(recheck / name)
                self.assertEqual(result["task"], task)
                self.assertEqual(result["seed"], seed)
                for reproduced in result["reproduction"].values():
                    for delta in reproduced["delta"].values():
                        self.assert_close(float(delta), 0.0)
                for image_mode in ("original", "blank", "conflict"):
                    for split in splits:
                        stored = result["evaluations"][image_mode][split]
                        rows = stored["rows"]
                        self.assertEqual(len(rows), 96)
                        recomputed = {
                            "accuracy": rate(rows, "correct"),
                            "guard_violation_rate": rate(rows, "guard_violation"),
                            "safe_goal_completion_rate": rate(rows, "safe_goal_complete"),
                            "contract_swap_pair_accuracy": pair_accuracy(rows, ("scene_id",)),
                        }
                        for metric, value in recomputed.items():
                            self.assert_close(value, float(stored[metric]))
                            aggregate[(task, split, image_mode, metric)].append(value)

        expected = {
            ("temporal", "test", "original"): (1.000000, 1.000000),
            ("temporal", "test", "blank"): (0.670139, 0.402778),
            ("temporal", "test", "conflict"): (0.607639, 0.340278),
            ("temporal", "unseen", "original"): (0.635417, 0.305556),
            ("temporal", "unseen", "blank"): (0.690972, 0.381944),
            ("temporal", "unseen", "conflict"): (0.704861, 0.409722),
            ("maneuver", "test", "original"): (1.000000, 1.000000),
            ("maneuver", "test", "blank"): (1.000000, 1.000000),
            ("maneuver", "test", "conflict"): (1.000000, 1.000000),
            ("maneuver", "hard", "original"): (0.947917, 0.895833),
            ("maneuver", "hard", "blank"): (0.906250, 0.812500),
            ("maneuver", "hard", "conflict"): (0.947917, 0.895833),
        }
        for key, (accuracy, paired) in expected.items():
            self.assertAlmostEqual(
                statistics.mean(aggregate[key + ("accuracy",)]), accuracy, places=6
            )
            self.assertAlmostEqual(
                statistics.mean(aggregate[key + ("contract_swap_pair_accuracy",)]), paired, places=6
            )

    def test_static_rows_and_all_example_denominators(self) -> None:
        run_names = {
            "COC_ONLY": "candidate-coc-only-seed42-v0",
            "RICH_COC": "candidate-rich-coc-seed42-v0",
            "NATURAL_GUARD": "candidate-natural-guard-seed42-v0",
            "SHUFFLED_GUARD": "candidate-shuffled-guard-seed42-v0",
            "LOGIC_GUARD": "candidate-logic-guard-seed42-v0",
        }
        expected_overall = {
            "COC_ONLY": (0.250, 0.250),
            "RICH_COC": (0.000, 0.000),
            "NATURAL_GUARD": (1 / 144, 0.000),
            "SHUFFLED_GUARD": (27 / 144, 50 / 144),
            "LOGIC_GUARD": (0.000, 0.000),
        }
        summary = load(VLM / "candidate-guard-summary-seed42-v0/summary.json")
        for condition, run_name in run_names.items():
            result = load(VLM / run_name / "result.json")
            self.assertEqual(result["train_scenes"], 96)
            self.assertEqual(result["train_examples"], 576)
            split_rows: dict[str, list[dict[str, Any]]] = {}
            for split in ("post_test", "post_paraphrase", "post_unseen"):
                rows = result[split]["rows"]
                split_rows[split] = rows
                self.assertEqual(len(rows), 144)
                self.assert_close(rate(rows, "correct"), result[split]["accuracy"])
                self.assert_close(
                    pair_accuracy(rows, ("scene_id", "constraint_kind")),
                    result[split]["contract_swap_pair_accuracy"],
                )
                restrictive = [row for row in rows if row["contract_level"] == "restrictive"]
                permissive = [row for row in rows if row["contract_level"] == "permissive"]
                self.assert_close(
                    rate(restrictive, "violation_selected"),
                    summary["metrics"][condition][split]["guard_violation_selection_rate"],
                )
                self.assert_close(
                    sum(not row["correct"] for row in permissive) / len(permissive),
                    summary["metrics"][condition][split]["false_conservative_rate"],
                )
            rows = split_rows["post_test"]
            overall_violation = rate(rows, "violation_selected")
            overall_conservative = sum(
                row["contract_level"] == "permissive" and not row["correct"] for row in rows
            ) / len(rows)
            self.assert_close(overall_violation, expected_overall[condition][0])
            self.assert_close(overall_conservative, expected_overall[condition][1])

    def test_auxiliary_closed_loop_numbers_from_episode_rows(self) -> None:
        root = REPO / "artifacts/results/public"
        cases = (
            (
                root / "contract-microworld-v1/pilot-phase-complete-isolated-2026-08-04-v2",
                {"split": "OOD"},
                "variant",
            ),
            (
                root / "contract-microworld-v2/pilot-release-reversal-2026-08-04-v1",
                {},
                "variant",
            ),
        )
        for directory, filters, group_key in cases:
            with (directory / "episode_metrics.csv").open(encoding="utf-8", newline="") as handle:
                rows = [
                    row for row in csv.DictReader(handle)
                    if all(row[key] == value for key, value in filters.items())
                ]
            grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
            for row in rows:
                grouped[row[group_key]].append(row)
            summary = load(directory / "result.json")["summary"]
            summary_rows = {
                row["variant"]: row for row in summary
                if (not filters or row.get("split") == "OOD")
                and ("kind" not in row or row.get("kind") == "ALL")
                and ("stress_type" not in row or row.get("stress_type") == "ALL")
            }
            for variant, variant_rows in grouped.items():
                expected = summary_rows[variant]
                for csv_key, summary_key in (
                    ("unsafe", "unsafe_rate_mean"),
                    ("collision", "collision_rate_mean"),
                    ("completed", "completion_rate_mean"),
                ):
                    actual = sum(row[csv_key] == "True" for row in variant_rows) / len(variant_rows)
                    self.assert_close(actual, float(expected[summary_key]))

    def test_r1_scope_and_reported_deltas(self) -> None:
        result = load(
            REPO / "artifacts/results/restricted/alp-exp-006/guard-semantic-summary-v2/summary.json"
        )
        self.assertEqual(result["scene_count"], 1)
        self.assertEqual(result["paired_run_count"], 3)
        self.assert_close(result["mean_delta_hold_minus_baseline_at_2s_m"], 0.26318955421447754)
        self.assert_close(abs(result["mean_delta_hold_minus_opposite_at_2s_m"]), 0.007872343063354492)
        self.assertFalse(result["pilot_interpretation"]["semantically_specific_beyond_irrelevant_control"])


if __name__ == "__main__":
    unittest.main()
