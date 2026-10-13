"""Validate an anonymous categorical panel and replay its agreement statistics."""
from collections import Counter
import csv
from pathlib import Path
import re

FIELDS = ("temporal_requirement_explicit", "required_action_sequence", "textual_consistency")
HEADERS = ("subject_id", "rater_id") + FIELDS
TIME_LABELS = {"YES", "NO", "AMBIGUOUS"}
TEXT_LABELS = {"TEXTUAL_CONTRADICTION", "TEXTUALLY_CONSISTENT", "UNKNOWN_EXTERNAL_EVIDENCE_REQUIRED",
               "AMBIGUOUS_TEXT", "NOT_APPLICABLE_NO_TEMPORAL_REQUIREMENT"}
ACTION_LABELS = {"STOP_OR_HOLD", "YIELD_OR_DECELERATE", "ACCELERATE_OR_PROCEED", "MAINTAIN_SPEED", "OTHER"}


def calculate(path, coefficients, exact_check):
    with Path(path).open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        if tuple(reader.fieldnames or ()) != HEADERS:
            raise ValueError("Only anonymous subject/rater IDs and three categorical fields are allowed")
        rows = list(reader)
    panel = {}
    for row in rows:
        if set(row) != set(HEADERS) or not re.fullmatch(r"G(?:0[1-9]|1[0-9]|2[0-7])", row["subject_id"]):
            raise ValueError("Unexpected subject ID or extra cell")
        if row["rater_id"] not in "ABCD" or len(row["rater_id"]) != 1:
            raise ValueError("Unexpected rater ID")
        if row[FIELDS[0]] not in TIME_LABELS or row[FIELDS[2]] not in TEXT_LABELS:
            raise ValueError("Unexpected categorical label")
        action = row[FIELDS[1]]
        if action not in {"AMBIGUOUS", "NO_EXPLICIT_ACTION"} and not all(p in ACTION_LABELS for p in action.split(">")):
            raise ValueError("Action sequences must contain only categorical tokens")
        key = (row["subject_id"], row["rater_id"])
        if key in panel:
            raise ValueError("Duplicate subject/rater rating")
        panel[key] = row
    subjects = [f"G{i:02d}" for i in range(1, 28)]
    if set(panel) != {(s, r) for s in subjects for r in "ABCD"}:
        raise ValueError("Expected a complete four-rater, 27-subject panel")
    fields, distributions = {}, {}
    for field in FIELDS:
        votes = [[panel[s, r][field] for r in "ABCD"] for s in subjects]
        categories = sorted({v for row in votes for v in row})
        stats = coefficients(votes, categories)
        for key, value in exact_check(votes, categories).items():
            if abs(stats[key] - value) >= 1e-12:
                raise ValueError("Agreement calculation and exact pair enumeration disagree")
        fields[field] = stats
        distributions[field] = {r: dict(sorted(Counter(panel[s, r][field] for s in subjects).items())) for r in "ABCD"}
    return {"subjects": 27, "raters": 4, "ratings": 108, "fields": fields,
            "rater_distributions": distributions, "new_human_evaluation": False,
            "labels_recoded": False, "exact_arithmetic_crosscheck": "PASS"}
