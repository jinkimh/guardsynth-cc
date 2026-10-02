#!/usr/bin/env python3
"""Regression checks for readable result figures."""

from __future__ import annotations

import csv
import struct
import subprocess
import sys
import unittest
from pathlib import Path


HERE = Path(__file__).resolve().parent


def png_size(path: Path) -> tuple[int, int]:
    with path.open("rb") as handle:
        signature = handle.read(24)
    if signature[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError(f"not a PNG file: {path}")
    return struct.unpack(">II", signature[16:24])


class ResultFigureLayoutTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        subprocess.run([sys.executable, str(HERE / "generate_figures.py")], check=True)

    def test_result_figures_are_split_and_wide(self) -> None:
        expected = {
            "fig04_r1_diagnostic.png": 1.25,
            "fig05_temporal_pair.png": 1.80,
            "fig06_release_reversal.png": 1.80,
        }
        for name, minimum_ratio in expected.items():
            path = HERE / name
            self.assertTrue(path.exists(), name)
            width, height = png_size(path)
            self.assertGreater(width / height, minimum_ratio, name)

    def test_pipeline_figure_does_not_keep_excess_vertical_canvas(self) -> None:
        width, height = png_size(HERE / "fig02_pipeline.png")
        self.assertGreater(width / height, 2.45)

    def test_release_reversal_uses_descriptive_condition_names(self) -> None:
        with (HERE / "data" / "release_reversal.csv").open(encoding="utf-8") as handle:
            labels = [row["condition"] for row in csv.DictReader(handle)]
        self.assertEqual(
            labels,
            [
                "State only",
                "State + CoC",
                "Dynamic contract",
                "Monotone-stage contract",
                "Contract + shield",
                "Future-information upper bound",
                "Delayed dynamic contract",
                "Delayed shield",
            ],
        )

    def test_paired_contract_keeps_candidates_fixed_and_changes_verdict(self) -> None:
        width, height = png_size(HERE / "fig03_paired_contract.png")
        self.assertGreater(width / height, 1.8)

        with (HERE / "data" / "paired_contract_example.csv").open(encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual(
            rows,
            [
                {
                    "contract": "Permissive contract",
                    "min_gap_m": "5.5",
                    "candidate_a_verdict": "admissible",
                    "selected_candidate": "Candidate A",
                    "reason": "current gap 7.2 m ≥ minimum gap",
                },
                {
                    "contract": "Restrictive contract",
                    "min_gap_m": "9.0",
                    "candidate_a_verdict": "violation",
                    "selected_candidate": "Candidate B",
                    "reason": "current gap 7.2 m < minimum gap",
                },
            ],
        )

    def test_typed_contract_figure_uses_english_stage_terms(self) -> None:
        width, height = png_size(HERE / "fig05_typed_contract.png")
        self.assertGreater(height / width, 1.1)

        with (HERE / "data" / "typed_contract_stages.csv").open(encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual(
            rows,
            [
                {"stage": "1", "description": "Natural-language Safety-Constrained CoC"},
                {"stage": "2", "description": "Guard parsing: condition type, comparator, value, unit, fallback"},
                {"stage": "3", "description": "Unit normalization: 600 cm → 6.0 m"},
                {"stage": "4", "description": "Model-external verifier or shield: check distance, speed, and time"},
            ],
        )


if __name__ == "__main__":
    unittest.main()
