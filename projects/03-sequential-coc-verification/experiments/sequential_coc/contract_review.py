#!/usr/bin/env python3
"""Validate blinded contract-review CSVs and gate human consensus.

This module deliberately never infers labels.  It only accepts completed human
CSV exports, reports agreement, and creates a restricted discrepancy worksheet
once both independent first passes are available.
"""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
import io
import json
import os
from pathlib import Path
import re
import sys
import tempfile
from typing import Callable, Iterable, Mapping, Sequence

if __package__ in (None, ""):
    sys.path.insert(0, str(next(parent for parent in Path(__file__).resolve().parents if (parent / "PROJECT_REGISTRY.json").is_file())))

from experiments.sequential_coc.build_review_app import (
    CONTRACT_CHOICES,
    CONTRACT_REVIEW_FIELDS,
    REVIEW_DIR,
)


NOTES_MAX_LENGTH = 1000
EXPECTED_REVIEW_ID_COUNT = 27
REVIEW_ID_PATTERN = re.compile(r"REV-[0-9a-f]{16}")
FIRST_PASS_FILENAMES = ("contract_review_A.csv", "contract_review_B.csv")
CONSENSUS_FILENAME = "contract_review_consensus.csv"
DISAGREEMENTS_FILENAME = "contract-review-disagreements.csv"
CATEGORICAL_FIELDS = tuple(
    field for field in CONTRACT_REVIEW_FIELDS if field not in {"review_id", "notes"}
)
ACTION_SEQUENCE_SPECIALS = frozenset({"AMBIGUOUS", "NO_EXPLICIT_ACTION"})
ACTION_SEQUENCE_TOKENS = frozenset(CONTRACT_CHOICES["required_action_sequence"]) - ACTION_SEQUENCE_SPECIALS
COUNTED_LABELS = CONTRACT_CHOICES["textual_consistency"]


@dataclass(frozen=True, slots=True)
class ContractReviewRow:
    review_id: str
    temporal_requirement_explicit: str
    required_action_sequence: str
    textual_consistency: str
    notes: str

    def value(self, field: str) -> str:
        return getattr(self, field)


@dataclass(frozen=True, slots=True)
class FieldAgreement:
    field: str
    raw_agreement: float
    kappa: float | None


@dataclass(frozen=True, slots=True)
class ReviewAgreement:
    rows_a: tuple[ContractReviewRow, ...]
    rows_b: tuple[ContractReviewRow, ...]
    disagreement_ids: tuple[str, ...]
    by_field: Mapping[str, FieldAgreement]


@dataclass(frozen=True, slots=True)
class ReviewPacket:
    expected_ids: frozenset[str]
    independent_clusters: int


def _error(code: str, detail: str = "") -> ValueError:
    return ValueError(f"{code}{': ' + detail if detail else ''}")


def _as_expected_ids(expected_ids: Iterable[str]) -> set[str]:
    supplied = tuple(expected_ids)
    values = set(supplied)
    if len(supplied) != EXPECTED_REVIEW_ID_COUNT or len(values) != EXPECTED_REVIEW_ID_COUNT:
        raise _error("EXPECTED_REVIEW_ID_COUNT")
    if any(not isinstance(value, str) or REVIEW_ID_PATTERN.fullmatch(value) is None for value in values):
        raise _error("EXPECTED_REVIEW_ID_FORMAT")
    return values


def _validate_action_sequence(value: str, line_number: int) -> None:
    if value in ACTION_SEQUENCE_SPECIALS:
        return
    phases = value.split(">")
    if (
        not value
        or any(not phase or phase not in ACTION_SEQUENCE_TOKENS for phase in phases)
        or any(left == right for left, right in zip(phases, phases[1:]))
    ):
        raise _error("INVALID_ACTION_SEQUENCE", f"row {line_number}")


def validate_contract_review_csv(
    path: Path, expected_ids: set[str]
) -> tuple[ContractReviewRow, ...]:
    """Read one complete first-pass or consensus CSV without normalizing it.

    The BOM exported by the reviewer page is accepted.  All other structure is
    exact: the header's names and order, one row per expected opaque ID, valid
    categorical labels, and at most 1,000 note characters.
    """
    expected = _as_expected_ids(expected_ids)
    try:
        handle = path.open("r", encoding="utf-8-sig", newline="")
    except FileNotFoundError as exc:
        raise _error("CSV_NOT_FOUND", str(path)) from exc
    with handle:
        reader = csv.DictReader(handle)
        if tuple(reader.fieldnames or ()) != CONTRACT_REVIEW_FIELDS:
            raise _error("CSV_HEADER_MISMATCH")
        parsed: list[ContractReviewRow] = []
        seen: set[str] = set()
        for line_number, raw in enumerate(reader, start=2):
            if None in raw or any(value is None for value in raw.values()):
                raise _error("CSV_ROW_SHAPE_MISMATCH", str(line_number))
            review_id = raw["review_id"]
            if review_id in seen:
                raise _error("DUPLICATE_REVIEW_ID", review_id)
            seen.add(review_id)
            for field in CATEGORICAL_FIELDS:
                value = raw[field]
                if field == "required_action_sequence":
                    _validate_action_sequence(value, line_number)
                elif not value or value not in CONTRACT_CHOICES[field]:
                    raise _error("INVALID_CATEGORICAL_VALUE", f"{field} at row {line_number}")
            notes = raw["notes"]
            if len(notes) > NOTES_MAX_LENGTH:
                raise _error("NOTES_TOO_LONG", f"row {line_number}")
            parsed.append(ContractReviewRow(**{field: raw[field] for field in CONTRACT_REVIEW_FIELDS}))
    if seen != expected:
        raise _error("REVIEW_ID_SET_MISMATCH")
    return tuple(parsed)


def _cohen_kappa(a_values: Sequence[str], b_values: Sequence[str]) -> float | None:
    total = len(a_values)
    if total != len(b_values) or total == 0:
        raise _error("AGREEMENT_INPUT_MISMATCH")
    observed = sum(a == b for a, b in zip(a_values, b_values)) / total
    labels = set(a_values) | set(b_values)
    expected = sum(
        (a_values.count(label) / total) * (b_values.count(label) / total)
        for label in labels
    )
    if expected == 1.0:
        return None
    return (observed - expected) / (1.0 - expected)


def compare_contract_reviews(
    a: Sequence[ContractReviewRow], b: Sequence[ContractReviewRow]
) -> ReviewAgreement:
    """Compare aligned independent first passes without changing either one."""
    ids_a = [row.review_id for row in a]
    by_id_b = {row.review_id: row for row in b}
    if len(ids_a) != len(set(ids_a)) or len(by_id_b) != len(b) or set(ids_a) != set(by_id_b):
        raise _error("AGREEMENT_REVIEW_ID_MISMATCH")
    aligned_b = tuple(by_id_b[review_id] for review_id in ids_a)
    rows_a = tuple(a)
    disagreements = tuple(
        row_a.review_id
        for row_a, row_b in zip(rows_a, aligned_b)
        if any(row_a.value(field) != row_b.value(field) for field in CATEGORICAL_FIELDS)
    )
    by_field = {
        field: FieldAgreement(
            field=field,
            raw_agreement=sum(
                row_a.value(field) == row_b.value(field)
                for row_a, row_b in zip(rows_a, aligned_b)
            ) / len(rows_a),
            kappa=_cohen_kappa(
                [row.value(field) for row in rows_a],
                [row.value(field) for row in aligned_b],
            ),
        )
        for field in CATEGORICAL_FIELDS
    }
    return ReviewAgreement(rows_a, aligned_b, disagreements, by_field)


def validate_consensus(
    rows: Sequence[ContractReviewRow],
    disagreements: ReviewAgreement,
    expected_ids: set[str],
) -> tuple[ContractReviewRow, ...]:
    """Ensure consensus covers every ID and only resolves disputed values."""
    expected = _as_expected_ids(expected_ids)
    by_id = {row.review_id: row for row in rows}
    if len(by_id) != len(rows) or set(by_id) != expected:
        raise _error("CONSENSUS_REVIEW_ID_SET_MISMATCH")
    first_a = {row.review_id: row for row in disagreements.rows_a}
    first_b = {row.review_id: row for row in disagreements.rows_b}
    if set(first_a) != expected or set(first_b) != expected:
        raise _error("CONSENSUS_FIRST_PASS_ID_MISMATCH")
    for review_id in sorted(expected):
        consensus = by_id[review_id]
        row_a, row_b = first_a[review_id], first_b[review_id]
        for field in CATEGORICAL_FIELDS:
            if row_a.value(field) == row_b.value(field) and consensus.value(field) != row_a.value(field):
                raise _error("CONSENSUS_ALTERS_AGREED_VALUE", f"{review_id}:{field}")
    return tuple(rows)


def _atomic_write_restricted(path: Path, content: str) -> None:
    encoded = content.encode("utf-8")
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        if temporary.read_bytes() != encoded or temporary.stat().st_mode & 0o777 != 0o600:
            raise RuntimeError("restricted discrepancy write verification failed")
        os.replace(temporary, path)
        directory_descriptor = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory_descriptor)
        finally:
            os.close(directory_descriptor)
    finally:
        if temporary.exists():
            temporary.unlink()


def _disagreement_csv(report: ReviewAgreement) -> str:
    fields = ("review_id",) + tuple(f"A_{field}" for field in CONTRACT_REVIEW_FIELDS[1:]) + tuple(
        f"B_{field}" for field in CONTRACT_REVIEW_FIELDS[1:]
    )
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    disagreement_ids = set(report.disagreement_ids)
    for row_a, row_b in zip(report.rows_a, report.rows_b):
        if row_a.review_id not in disagreement_ids:
            continue
        row = {"review_id": row_a.review_id}
        row.update({f"A_{field}": row_a.value(field) for field in CONTRACT_REVIEW_FIELDS[1:]})
        row.update({f"B_{field}": row_b.value(field) for field in CONTRACT_REVIEW_FIELDS[1:]})
        writer.writerow(row)
    return stream.getvalue()


def _review_packet_from_mapping(review_dir: Path) -> ReviewPacket:
    path = review_dir / "adjudication-mapping.json"
    try:
        mapping = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise _error("REVIEW_PACKET_MAPPING_NOT_FOUND") from exc
    if not isinstance(mapping, list) or len(mapping) != EXPECTED_REVIEW_ID_COUNT:
        raise _error("REVIEW_PACKET_ID_MISMATCH")
    ids = [row.get("review_id") for row in mapping if isinstance(row, dict)]
    clusters = [row.get("cluster_id") for row in mapping if isinstance(row, dict)]
    if len(ids) != len(mapping) or len(clusters) != len(mapping):
        raise _error("REVIEW_PACKET_ID_MISMATCH")
    try:
        expected = _as_expected_ids(ids)
    except ValueError as exc:
        raise _error("REVIEW_PACKET_ID_MISMATCH") from exc
    if any(not isinstance(cluster, str) or not cluster for cluster in clusters):
        raise _error("REVIEW_PACKET_CLUSTER_MISMATCH")
    independent_clusters = len(set(clusters))
    if independent_clusters != EXPECTED_REVIEW_ID_COUNT:
        raise _error("REVIEW_PACKET_CLUSTER_MISMATCH")
    return ReviewPacket(frozenset(expected), independent_clusters)


def _expected_ids_from_packet(review_dir: Path) -> set[str]:
    """Return the public expected-ID set after validating packet membership."""
    return set(_review_packet_from_mapping(review_dir).expected_ids)


def _invalidate_disagreements(review_dir: Path) -> None:
    """Remove only the derived worksheet, never either human first pass."""
    path = review_dir / DISAGREEMENTS_FILENAME
    if not (path.is_file() or path.is_symlink()):
        return
    path.unlink()
    directory_descriptor = os.open(review_dir, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(directory_descriptor)
    finally:
        os.close(directory_descriptor)


def _not_run_summary() -> dict[str, object]:
    return {
        "reviewer_rows": {"A": "NOT_RUN", "B": "NOT_RUN"},
        "independent_clusters": "NOT_RUN",
        "field_agreement": {
            field: {"raw_agreement": "NOT_RUN", "kappa": "NOT_RUN"}
            for field in CATEGORICAL_FIELDS
        },
        "label_counts": {label: "NOT_RUN" for label in COUNTED_LABELS},
    }


def _agreement_summary(report: ReviewAgreement, independent_clusters: int) -> dict[str, object]:
    counts = {
        label: {
            "A": sum(row.textual_consistency == label for row in report.rows_a),
            "B": sum(row.textual_consistency == label for row in report.rows_b),
        }
        for label in COUNTED_LABELS
    }
    for value in counts.values():
        value["combined"] = value["A"] + value["B"]
    return {
        "reviewer_rows": {"A": len(report.rows_a), "B": len(report.rows_b)},
        "independent_clusters": independent_clusters,
        "field_agreement": {
            field: {"raw_agreement": agreement.raw_agreement, "kappa": agreement.kappa}
            for field, agreement in report.by_field.items()
        },
        "label_counts": counts,
    }


def _status(status: str, **extra: object) -> str:
    return json.dumps({"status": status, **extra}, sort_keys=True)


def main(argv: Sequence[str] | None = None, printer: Callable[[str], None] = print) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--review-dir", type=Path, default=REVIEW_DIR)
    args = parser.parse_args(argv)
    review_dir: Path = args.review_dir
    a_path, b_path = (review_dir / filename for filename in FIRST_PASS_FILENAMES)
    if not a_path.exists() or not b_path.exists():
        _invalidate_disagreements(review_dir)
        printer(
            _status(
                "WAITING_FOR_CONTRACT_REVIEW",
                agreement="NOT_RUN",
                adjudication="NOT_RUN",
                **_not_run_summary(),
            )
        )
        return 0
    try:
        packet = _review_packet_from_mapping(review_dir)
        expected_ids = set(packet.expected_ids)
        rows_a = validate_contract_review_csv(a_path, expected_ids)
        rows_b = validate_contract_review_csv(b_path, expected_ids)
        agreement = compare_contract_reviews(rows_a, rows_b)
        _atomic_write_restricted(review_dir / DISAGREEMENTS_FILENAME, _disagreement_csv(agreement))
        summary = _agreement_summary(agreement, packet.independent_clusters)
        consensus_path = review_dir / CONSENSUS_FILENAME
        if not consensus_path.exists():
            printer(
                _status(
                    "WAITING_FOR_CONSENSUS",
                    disagreement_count=len(agreement.disagreement_ids),
                    **summary,
                )
            )
            return 0
        consensus_rows = validate_contract_review_csv(consensus_path, expected_ids)
        validate_consensus(consensus_rows, agreement, expected_ids)
    except ValueError as exc:
        _invalidate_disagreements(review_dir)
        printer(_status("CONTRACT_REVIEW_INVALID", error=str(exc), **_not_run_summary()))
        return 2
    printer(
        _status(
            "CONTRACT_REVIEW_COMPLETE",
            disagreement_count=len(agreement.disagreement_ids),
            **summary,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
