"""Behavior tests for strict independent contract-review CSV handling."""

from __future__ import annotations

import csv
import io
import json
import os
from pathlib import Path
import tempfile
import unittest

from experiments.sequential_coc.build_review_app import (
    CONTRACT_CHOICES,
    CONTRACT_REVIEW_FIELDS,
)
from experiments.sequential_coc.contract_review import (
    _expected_ids_from_packet,
    compare_contract_reviews,
    main,
    validate_consensus,
    validate_contract_review_csv,
)


EXPECTED_IDS = {f"REV-{index:016x}" for index in range(1, 28)}


def _row(review_id: str, **changes: str) -> dict[str, str]:
    row = {
        "review_id": review_id,
        "temporal_requirement_explicit": "YES",
        "required_action_sequence": "STOP_OR_HOLD>ACCELERATE_OR_PROCEED",
        "textual_consistency": "TEXTUALLY_CONSISTENT",
        "notes": "synthetic rationale",
    }
    row.update(changes)
    return row


def _csv_bytes(rows: list[dict[str, str]], headers=CONTRACT_REVIEW_FIELDS, *, bom=False) -> bytes:
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=headers, lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    return (("\ufeff" if bom else "") + stream.getvalue()).encode("utf-8")


def _write_csv(path: Path, rows: list[dict[str, str]], headers=CONTRACT_REVIEW_FIELDS, *, bom=False) -> None:
    path.write_bytes(_csv_bytes(rows, headers, bom=bom))


def _rows() -> list[dict[str, str]]:
    return [_row(review_id) for review_id in sorted(EXPECTED_IDS)]


def _write_mapping(review_dir: Path, review_ids: list[str] | None = None) -> None:
    ids = sorted(EXPECTED_IDS) if review_ids is None else review_ids
    (review_dir / "adjudication-mapping.json").write_text(
        json.dumps(
            [
                {"review_id": review_id, "cluster_id": f"SYNTHETIC-CLUSTER-{index:02d}"}
                for index, review_id in enumerate(ids, start=1)
            ]
        ),
        encoding="utf-8",
    )


class ContractReviewTests(unittest.TestCase):
    def test_review_csv_rejects_wrong_header_duplicate_id_and_invalid_choice(self):
        # Removing a header, accepting duplicate IDs, or accepting a made-up label
        # would make this test fail; each is a corrupted human-review export.
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            wrong_header = root / "wrong.csv"
            duplicate = root / "duplicate.csv"
            invalid = root / "invalid.csv"
            _write_csv(wrong_header, _rows(), tuple(reversed(CONTRACT_REVIEW_FIELDS)))
            duplicate_rows = _rows()
            duplicate_rows[-1]["review_id"] = duplicate_rows[0]["review_id"]
            _write_csv(duplicate, duplicate_rows)
            invalid_rows = _rows()
            invalid_rows[0]["textual_consistency"] = "UNSUPPORTED_LABEL"
            _write_csv(invalid, invalid_rows)

            with self.assertRaisesRegex(ValueError, "CSV_HEADER_MISMATCH"):
                validate_contract_review_csv(wrong_header, EXPECTED_IDS)
            with self.assertRaisesRegex(ValueError, "DUPLICATE_REVIEW_ID"):
                validate_contract_review_csv(duplicate, EXPECTED_IDS)
            with self.assertRaisesRegex(ValueError, "INVALID_CATEGORICAL_VALUE"):
                validate_contract_review_csv(invalid, EXPECTED_IDS)

    def test_review_csv_accepts_bom_and_rejects_id_set_blank_category_and_long_notes(self):
        # Losing UTF-8 BOM compatibility or accepting incomplete categorical rows
        # would make this test fail.
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            valid = root / "valid.csv"
            bad_ids = root / "bad_ids.csv"
            blank = root / "blank.csv"
            long_notes = root / "long_notes.csv"
            _write_csv(valid, _rows(), bom=True)
            bad_id_rows = _rows()
            bad_id_rows[-1]["review_id"] = "REV-ffffffffffffffff"
            _write_csv(bad_ids, bad_id_rows)
            blank_rows = _rows()
            blank_rows[0]["required_action_sequence"] = ""
            _write_csv(blank, blank_rows)
            long_rows = _rows()
            long_rows[0]["notes"] = "x" * 1001
            _write_csv(long_notes, long_rows)

            self.assertEqual(len(validate_contract_review_csv(valid, EXPECTED_IDS)), 27)
            with self.assertRaisesRegex(ValueError, "REVIEW_ID_SET_MISMATCH"):
                validate_contract_review_csv(bad_ids, EXPECTED_IDS)
            with self.assertRaisesRegex(ValueError, "INVALID_ACTION_SEQUENCE"):
                validate_contract_review_csv(blank, EXPECTED_IDS)
            with self.assertRaisesRegex(ValueError, "NOTES_TOO_LONG"):
                validate_contract_review_csv(long_notes, EXPECTED_IDS)

    def test_review_csv_accepts_ordered_action_sequences_and_rejects_malformed_sequences(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            valid = root / "valid.csv"
            bad_token = root / "bad-token.csv"
            empty_phase = root / "empty-phase.csv"
            mixed_special = root / "mixed-special.csv"
            _write_csv(valid, _rows())
            bad_token_rows = _rows()
            bad_token_rows[0]["required_action_sequence"] = "STOP_OR_HOLD>FLY"
            _write_csv(bad_token, bad_token_rows)
            empty_phase_rows = _rows()
            empty_phase_rows[0]["required_action_sequence"] = "STOP_OR_HOLD>>ACCELERATE_OR_PROCEED"
            _write_csv(empty_phase, empty_phase_rows)
            mixed_special_rows = _rows()
            mixed_special_rows[0]["required_action_sequence"] = "AMBIGUOUS>STOP_OR_HOLD"
            _write_csv(mixed_special, mixed_special_rows)

            parsed = validate_contract_review_csv(valid, EXPECTED_IDS)
            self.assertEqual(
                parsed[0].required_action_sequence,
                "STOP_OR_HOLD>ACCELERATE_OR_PROCEED",
            )
            for path in (bad_token, empty_phase, mixed_special):
                with self.subTest(path=path.name), self.assertRaisesRegex(
                    ValueError, "INVALID_ACTION_SEQUENCE"
                ):
                    validate_contract_review_csv(path, EXPECTED_IDS)

    def test_expected_review_id_invariant_rejects_wrong_count_and_nonopaque_ids(self):
        # Allowing a packet or public loader to use another population than the
        # 27 opaque review IDs would invalidate independent-review alignment.
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "valid.csv"
            _write_csv(path, _rows())

            with self.assertRaisesRegex(ValueError, "EXPECTED_REVIEW_ID_COUNT"):
                validate_contract_review_csv(path, set(sorted(EXPECTED_IDS)[:-1]))
            malformed = {f"NOT-REVIEW-{index:016x}" for index in range(27)}
            with self.assertRaisesRegex(ValueError, "EXPECTED_REVIEW_ID_FORMAT"):
                validate_contract_review_csv(path, malformed)

    def test_packet_mapping_rejects_nonopaque_duplicate_and_extra_rows(self):
        # Mapping rows are the population authority; accepting malformed,
        # duplicate, or extra entries would misalign all reviewer CSVs.
        with tempfile.TemporaryDirectory() as temporary_directory:
            review_dir = Path(temporary_directory)
            malformed = sorted(EXPECTED_IDS)
            malformed[0] = "NOT-AN-OPAQUE-ID"
            duplicate = sorted(EXPECTED_IDS)
            duplicate[-1] = duplicate[0]
            extra = sorted(EXPECTED_IDS) + ["REV-000000000000001c"]

            for name, review_ids in (("malformed", malformed), ("duplicate", duplicate), ("extra", extra)):
                with self.subTest(name=name):
                    _write_mapping(review_dir, review_ids)
                    with self.assertRaisesRegex(ValueError, "REVIEW_PACKET_ID_MISMATCH"):
                        _expected_ids_from_packet(review_dir)

    def test_disagreements_preserve_both_first_passes_and_constant_kappa_is_none(self):
        # Comparing only IDs, discarding one first pass, or reporting a spurious
        # kappa for a constant label would make this test fail.
        with tempfile.TemporaryDirectory() as temporary_directory:
            path_a = Path(temporary_directory) / "a.csv"
            path_b = Path(temporary_directory) / "b.csv"
            rows_a = _rows()
            rows_b = _rows()
            changed_id = "REV-0000000000000002"
            for row in rows_b:
                if row["review_id"] == changed_id:
                    row["textual_consistency"] = "AMBIGUOUS_TEXT"
            _write_csv(path_a, rows_a)
            _write_csv(path_b, rows_b)

            report = compare_contract_reviews(
                validate_contract_review_csv(path_a, EXPECTED_IDS),
                validate_contract_review_csv(path_b, EXPECTED_IDS),
            )

            self.assertEqual(report.disagreement_ids, (changed_id,))
            self.assertEqual(report.rows_a[1].textual_consistency, "TEXTUALLY_CONSISTENT")
            self.assertEqual(report.rows_b[1].textual_consistency, "AMBIGUOUS_TEXT")
            self.assertEqual(report.by_field["temporal_requirement_explicit"].kappa, None)
            self.assertEqual(report.by_field["textual_consistency"].raw_agreement, 26 / 27)

    def test_consensus_requires_all_ids_and_keeps_uncontested_labels(self):
        # A consensus export that drops an item or revises an already-agreed label
        # is not an adjudication of disagreement and must be rejected.
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            a_path = root / "a.csv"
            b_path = root / "b.csv"
            consensus_path = root / "consensus.csv"
            rows_a = _rows()
            rows_b = _rows()
            rows_b[1]["textual_consistency"] = "AMBIGUOUS_TEXT"
            _write_csv(a_path, rows_a)
            _write_csv(b_path, rows_b)
            report = compare_contract_reviews(
                validate_contract_review_csv(a_path, EXPECTED_IDS),
                validate_contract_review_csv(b_path, EXPECTED_IDS),
            )
            consensus = _rows()
            consensus[0]["required_action_sequence"] = "STOP_OR_HOLD"
            _write_csv(consensus_path, consensus)
            parsed = validate_contract_review_csv(consensus_path, EXPECTED_IDS)
            with self.assertRaisesRegex(ValueError, "CONSENSUS_ALTERS_AGREED_VALUE"):
                validate_consensus(parsed, report, EXPECTED_IDS)
            consensus[0]["required_action_sequence"] = "STOP_OR_HOLD>ACCELERATE_OR_PROCEED"
            consensus[1]["textual_consistency"] = "UNKNOWN_EXTERNAL_EVIDENCE_REQUIRED"
            _write_csv(consensus_path, consensus)
            self.assertEqual(len(validate_consensus(
                validate_contract_review_csv(consensus_path, EXPECTED_IDS), report, EXPECTED_IDS
            )), 27)

    def test_cli_waits_without_human_csv_and_creates_no_adjudication_outputs(self):
        # Treating absent human input as agreement would make this test fail.
        with tempfile.TemporaryDirectory() as temporary_directory:
            review_dir = Path(temporary_directory)
            _write_mapping(review_dir)
            output: list[str] = []
            exit_code = main(["--review-dir", str(review_dir)], printer=output.append)

            self.assertEqual(exit_code, 0)
            status = json.loads(output[0])
            self.assertEqual(status["status"], "WAITING_FOR_CONTRACT_REVIEW")
            self.assertEqual(status["reviewer_rows"], {"A": "NOT_RUN", "B": "NOT_RUN"})
            self.assertEqual(status["independent_clusters"], "NOT_RUN")
            self.assertEqual(
                status["field_agreement"]["required_action_sequence"]["kappa"], "NOT_RUN"
            )
            self.assertEqual(
                status["label_counts"]["UNKNOWN_EXTERNAL_EVIDENCE_REQUIRED"], "NOT_RUN"
            )
            self.assertFalse((review_dir / "contract-review-disagreements.csv").exists())
            self.assertFalse((review_dir / "contract_review_consensus.csv").exists())

    def test_cli_writes_mode_0600_disagreements_only_after_two_first_passes(self):
        # Writing before both independent passes or mutating either source CSV
        # would make this test fail.
        with tempfile.TemporaryDirectory() as temporary_directory:
            review_dir = Path(temporary_directory)
            _write_mapping(review_dir)
            a_path = review_dir / "contract_review_A.csv"
            b_path = review_dir / "contract_review_B.csv"
            a_rows = _rows()
            b_rows = _rows()
            b_rows[1]["textual_consistency"] = "AMBIGUOUS_TEXT"
            _write_csv(a_path, a_rows)
            original_a = a_path.read_bytes()
            _write_csv(b_path, b_rows)
            output: list[str] = []

            self.assertEqual(main(["--review-dir", str(review_dir)], printer=output.append), 0)
            disagreement = review_dir / "contract-review-disagreements.csv"
            status = json.loads(output[0])
            self.assertEqual(status["status"], "WAITING_FOR_CONSENSUS")
            self.assertEqual(status["reviewer_rows"], {"A": 27, "B": 27})
            self.assertEqual(status["independent_clusters"], 27)
            self.assertEqual(status["field_agreement"]["textual_consistency"]["raw_agreement"], 26 / 27)
            self.assertEqual(status["label_counts"]["AMBIGUOUS_TEXT"], {"A": 0, "B": 1, "combined": 1})
            self.assertEqual(disagreement.stat().st_mode & 0o777, 0o600)
            self.assertEqual(a_path.read_bytes(), original_a)
            content = disagreement.read_text(encoding="utf-8")
            self.assertIn("A_textual_consistency", content)
            self.assertIn("B_textual_consistency", content)

    def test_cli_removes_stale_disagreement_for_missing_or_invalid_input(self):
        # A stale derivative after a source pass vanishes or becomes malformed
        # could be mistaken for current human disagreement.
        with tempfile.TemporaryDirectory() as temporary_directory:
            review_dir = Path(temporary_directory)
            _write_mapping(review_dir)
            a_path = review_dir / "contract_review_A.csv"
            b_path = review_dir / "contract_review_B.csv"
            a_rows = _rows()
            b_rows = _rows()
            b_rows[1]["textual_consistency"] = "AMBIGUOUS_TEXT"
            _write_csv(a_path, a_rows)
            _write_csv(b_path, b_rows)
            original_a = a_path.read_bytes()
            original_b = b_path.read_bytes()
            disagreement = review_dir / "contract-review-disagreements.csv"
            initial_output: list[str] = []
            self.assertEqual(main(["--review-dir", str(review_dir)], printer=initial_output.append), 0)
            self.assertTrue(disagreement.exists())

            b_path.unlink()
            missing_output: list[str] = []
            self.assertEqual(main(["--review-dir", str(review_dir)], printer=missing_output.append), 0)
            self.assertEqual(json.loads(missing_output[0])["status"], "WAITING_FOR_CONTRACT_REVIEW")
            self.assertFalse(disagreement.exists())
            self.assertEqual(a_path.read_bytes(), original_a)

            _write_csv(b_path, b_rows)
            regenerated_output: list[str] = []
            self.assertEqual(main(["--review-dir", str(review_dir)], printer=regenerated_output.append), 0)
            self.assertTrue(disagreement.exists())
            invalid_rows = _rows()
            invalid_rows[0]["textual_consistency"] = "INVALID"
            _write_csv(b_path, invalid_rows)
            invalid_output: list[str] = []
            self.assertEqual(main(["--review-dir", str(review_dir)], printer=invalid_output.append), 2)
            self.assertEqual(json.loads(invalid_output[0])["status"], "CONTRACT_REVIEW_INVALID")
            self.assertFalse(disagreement.exists())
            self.assertEqual(a_path.read_bytes(), original_a)


if __name__ == "__main__":
    unittest.main()
