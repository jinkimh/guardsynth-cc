"""Tests for four-reviewer aggregation and human-only adjudication."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from experiments.sequential_coc.build_review_app import CONTRACT_REVIEW_FIELDS, ReviewItem
from experiments.sequential_coc.contract_review import validate_contract_review_csv
from experiments.sequential_coc.panel_review import (
    build_adjudication_page,
    compare_panel_reviews,
    main,
    validate_panel_consensus,
)


IDS = tuple(f"REV-{index:016x}" for index in range(27))


def _rows() -> list[dict[str, str]]:
    return [
        {
            "review_id": review_id,
            "temporal_requirement_explicit": "YES",
            "required_action_sequence": "STOP_OR_HOLD>ACCELERATE_OR_PROCEED",
            "textual_consistency": "TEXTUALLY_CONSISTENT",
            "notes": "",
        }
        for review_id in IDS
    ]


def _write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CONTRACT_REVIEW_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def _write_mapping(path: Path) -> None:
    path.write_text(
        json.dumps(
            [
                {"review_id": review_id, "cluster_id": f"scene-{index:04d}"}
                for index, review_id in enumerate(IDS)
            ]
        ),
        encoding="utf-8",
    )


class PanelReviewTests(unittest.TestCase):
    def test_four_rater_agreement_and_disagreement_fields_are_cluster_aligned(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            panels = {}
            for reviewer in ("R1", "R2", "R3", "R4"):
                rows = _rows()
                if reviewer in {"R3", "R4"}:
                    rows[0]["textual_consistency"] = "TEXTUAL_CONTRADICTION"
                path = root / f"{reviewer}.csv"
                _write_csv(path, rows)
                panels[reviewer] = validate_contract_review_csv(path, set(IDS))

            report = compare_panel_reviews(panels)

            self.assertEqual(report.reviewer_names, ("R1", "R2", "R3", "R4"))
            self.assertEqual(
                report.disagreement_fields_by_id[IDS[0]], ("textual_consistency",)
            )
            self.assertAlmostEqual(
                report.by_field["textual_consistency"].raw_agreement,
                26 / 27 + (1 / 3) / 27,
            )
            self.assertEqual(report.vote_patterns["textual_consistency"]["2-2"], 1)

    def test_consensus_cannot_change_a_four_way_unanimous_field(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            panels = {}
            for reviewer in ("R1", "R2", "R3", "R4"):
                rows = _rows()
                if reviewer == "R4":
                    rows[0]["textual_consistency"] = "AMBIGUOUS_TEXT"
                path = root / f"{reviewer}.csv"
                _write_csv(path, rows)
                panels[reviewer] = validate_contract_review_csv(path, set(IDS))
            report = compare_panel_reviews(panels)
            consensus = _rows()
            consensus[0]["temporal_requirement_explicit"] = "NO"
            path = root / "consensus.csv"
            _write_csv(path, consensus)
            parsed = validate_contract_review_csv(path, set(IDS))
            with self.assertRaisesRegex(ValueError, "CONSENSUS_ALTERS_UNANIMOUS_VALUE"):
                validate_panel_consensus(parsed, report, set(IDS))

    def test_adjudication_page_shows_text_and_reviews_but_not_hidden_group(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            panels = {}
            for reviewer in ("R1", "R2", "R3", "R4"):
                path = root / f"{reviewer}.csv"
                _write_csv(path, _rows())
                panels[reviewer] = validate_contract_review_csv(path, set(IDS))
            report = compare_panel_reviews(panels)
            items = [
                ReviewItem(
                    review_id,
                    (("Stop, then proceed." if index == 0 else f"event {index}"), "Proceed carefully."),
                    (0.0, 1.0),
                )
                for index, review_id in enumerate(IDS)
            ]

            page = build_adjudication_page(items, report)

            self.assertIn("Stop, then proceed.", page)
            self.assertIn("TEXTUALLY_CONSISTENT", page)
            self.assertIn("contract_review_consensus.csv", page)
            self.assertNotIn("CANDIDATE", page)
            self.assertNotIn("checker", page.lower())

    def test_cli_preserves_sources_and_writes_restricted_waiting_outputs(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            review_dir = Path(temporary_directory)
            _write_mapping(review_dir / "adjudication-mapping.json")
            sources = []
            for name in ("A(cjh)", "A(ljy)", "B(cjw)", "B(lsj)"):
                path = review_dir / f"contract_review_{name}.csv"
                rows = _rows()
                if name == "B(lsj)":
                    rows[0]["textual_consistency"] = "AMBIGUOUS_TEXT"
                _write_csv(path, rows)
                sources.append(path)
            before = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in sources}
            items = [
                ReviewItem(review_id, (f"event {index}", "next"), (0.0, 1.0))
                for index, review_id in enumerate(IDS)
            ]
            output: list[str] = []

            code = main(
                ["--review-dir", str(review_dir)],
                printer=output.append,
                review_items=items,
            )

            self.assertEqual(code, 0)
            status = json.loads(output[0])
            self.assertEqual(status["status"], "WAITING_FOR_PANEL_ADJUDICATION")
            self.assertEqual(status["reviewer_count"], 4)
            self.assertEqual(status["independent_clusters"], 27)
            for filename in ("panel-review-summary.json", "PANEL_ADJUDICATION.html"):
                path = review_dir / filename
                self.assertTrue(path.exists())
                self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            self.assertEqual(
                before,
                {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in sources},
            )


if __name__ == "__main__":
    unittest.main()
