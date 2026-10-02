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
                "상태 전용",
                "상태+CoC",
                "동적 계약",
                "단조 단계 계약",
                "계약+차단장치",
                "미래정보 상한",
                "지연된 동적 계약",
                "지연된 차단장치",
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
                    "contract": "완화 계약",
                    "min_gap_m": "5.5",
                    "candidate_a_verdict": "허용",
                    "selected_candidate": "후보 A",
                    "reason": "현재 간격 7.2 m가 최소 간격 이상",
                },
                {
                    "contract": "엄격 계약",
                    "min_gap_m": "9.0",
                    "candidate_a_verdict": "위반",
                    "selected_candidate": "후보 B",
                    "reason": "현재 간격 7.2 m가 최소 간격 미만",
                },
            ],
        )

    def test_typed_contract_figure_uses_chapter_terms_in_korean(self) -> None:
        width, height = png_size(HERE / "fig05_typed_contract.png")
        self.assertGreater(height / width, 1.1)

        with (HERE / "data" / "typed_contract_stages.csv").open(encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual(
            rows,
            [
                {"stage": "1", "description": "자연어 Safety-Constrained CoC"},
                {"stage": "2", "description": "실행 가드 변환: 조건 종류, 비교 방향, 값, 단위, 대체 행동"},
                {"stage": "3", "description": "단위 통일: 600 cm → 6.0 m"},
                {"stage": "4", "description": "독립 검증기 또는 차단장치: 거리, 속도, 시간 조건 확인"},
            ],
        )


if __name__ == "__main__":
    unittest.main()
