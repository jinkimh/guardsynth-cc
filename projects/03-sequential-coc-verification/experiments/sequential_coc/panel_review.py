#!/usr/bin/env python3
"""Aggregate completed independent contract reviews without inventing consensus."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import html
import json
from pathlib import Path
import re
from typing import Callable, Iterable, Mapping, Sequence

if __package__ in (None, ""):
    import sys

    sys.path.insert(0, str(next(parent for parent in Path(__file__).resolve().parents if (parent / "PROJECT_REGISTRY.json").is_file())))

from experiments.sequential_coc.build_review_app import (
    CONTRACT_CHOICES,
    CONTRACT_REVIEW_FIELDS,
    REVIEW_DIR,
    ReviewItem,
    select_review_items,
)
from experiments.sequential_coc.contract_review import (
    CATEGORICAL_FIELDS,
    CONSENSUS_FILENAME,
    ContractReviewRow,
    FieldAgreement,
    _as_expected_ids,
    _atomic_write_restricted,
    _review_packet_from_mapping,
    validate_contract_review_csv,
)
from experiments.sequential_coc.extract_windows import read_natural_windows


PANEL_PATTERN = re.compile(r"contract_review_([AB]\([^)]+\))\.csv")
SUMMARY_FILENAME = "panel-review-summary.json"
ADJUDICATION_FILENAME = "PANEL_ADJUDICATION.html"


class PanelAgreement:
    def __init__(
        self,
        reviewer_names: tuple[str, ...],
        rows_by_reviewer: Mapping[str, tuple[ContractReviewRow, ...]],
        disagreement_fields_by_id: Mapping[str, tuple[str, ...]],
        by_field: Mapping[str, FieldAgreement],
        vote_patterns: Mapping[str, Mapping[str, int]],
    ) -> None:
        self.reviewer_names = reviewer_names
        self.rows_by_reviewer = rows_by_reviewer
        self.disagreement_fields_by_id = disagreement_fields_by_id
        self.by_field = by_field
        self.vote_patterns = vote_patterns


def discover_panel_csvs(review_dir: Path) -> dict[str, Path]:
    """Find named independent passes while excluding derived consensus files."""
    found: dict[str, Path] = {}
    if not review_dir.exists():
        return found
    for path in sorted(review_dir.iterdir()):
        match = PANEL_PATTERN.fullmatch(path.name)
        if match and path.is_file():
            reviewer = match.group(1)
            if reviewer in found:
                raise ValueError(f"DUPLICATE_PANEL_REVIEWER: {reviewer}")
            found[reviewer] = path
    return found


def _fleiss(values_by_item: Sequence[Sequence[str]]) -> FieldAgreement:
    if not values_by_item or len(values_by_item[0]) < 2:
        raise ValueError("PANEL_REQUIRES_AT_LEAST_TWO_REVIEWERS")
    rater_count = len(values_by_item[0])
    if any(len(values) != rater_count for values in values_by_item):
        raise ValueError("PANEL_RATER_COUNT_MISMATCH")
    item_agreements = []
    totals: Counter[str] = Counter()
    for values in values_by_item:
        counts = Counter(values)
        totals.update(values)
        item_agreements.append(
            sum(count * (count - 1) for count in counts.values())
            / (rater_count * (rater_count - 1))
        )
    observed = sum(item_agreements) / len(item_agreements)
    rating_total = len(values_by_item) * rater_count
    expected = sum((count / rating_total) ** 2 for count in totals.values())
    kappa = None if expected == 1.0 else (observed - expected) / (1.0 - expected)
    return FieldAgreement("", observed, kappa)


def _vote_pattern(values: Sequence[str]) -> str:
    counts = sorted(Counter(values).values(), reverse=True)
    return "-".join(str(count) for count in counts)


def compare_panel_reviews(
    reviews: Mapping[str, Sequence[ContractReviewRow]],
) -> PanelAgreement:
    reviewer_names = tuple(sorted(reviews))
    if len(reviewer_names) < 2:
        raise ValueError("PANEL_REQUIRES_AT_LEAST_TWO_REVIEWERS")
    first = tuple(reviews[reviewer_names[0]])
    ids = tuple(row.review_id for row in first)
    if len(ids) != len(set(ids)):
        raise ValueError("PANEL_REVIEW_ID_MISMATCH")
    aligned: dict[str, tuple[ContractReviewRow, ...]] = {}
    for reviewer in reviewer_names:
        by_id = {row.review_id: row for row in reviews[reviewer]}
        if len(by_id) != len(reviews[reviewer]) or set(by_id) != set(ids):
            raise ValueError("PANEL_REVIEW_ID_MISMATCH")
        aligned[reviewer] = tuple(by_id[review_id] for review_id in ids)

    disagreements: dict[str, tuple[str, ...]] = {}
    by_field: dict[str, FieldAgreement] = {}
    patterns: dict[str, Counter[str]] = {field: Counter() for field in CATEGORICAL_FIELDS}
    for index, review_id in enumerate(ids):
        disputed = []
        for field in CATEGORICAL_FIELDS:
            values = [aligned[name][index].value(field) for name in reviewer_names]
            patterns[field][_vote_pattern(values)] += 1
            if len(set(values)) > 1:
                disputed.append(field)
        if disputed:
            disagreements[review_id] = tuple(disputed)
    for field in CATEGORICAL_FIELDS:
        values_by_item = [
            [aligned[name][index].value(field) for name in reviewer_names]
            for index in range(len(ids))
        ]
        score = _fleiss(values_by_item)
        by_field[field] = FieldAgreement(field, score.raw_agreement, score.kappa)
    return PanelAgreement(
        reviewer_names,
        aligned,
        disagreements,
        by_field,
        {field: dict(counter) for field, counter in patterns.items()},
    )


def validate_panel_consensus(
    rows: Sequence[ContractReviewRow], report: PanelAgreement, expected_ids: Iterable[str]
) -> tuple[ContractReviewRow, ...]:
    expected = _as_expected_ids(expected_ids)
    by_id = {row.review_id: row for row in rows}
    if len(by_id) != len(rows) or set(by_id) != expected:
        raise ValueError("CONSENSUS_REVIEW_ID_SET_MISMATCH")
    source_by_reviewer = {
        reviewer: {row.review_id: row for row in report.rows_by_reviewer[reviewer]}
        for reviewer in report.reviewer_names
    }
    for review_id in sorted(expected):
        consensus = by_id[review_id]
        for field in CATEGORICAL_FIELDS:
            source_values = {
                source_by_reviewer[reviewer][review_id].value(field)
                for reviewer in report.reviewer_names
            }
            if len(source_values) == 1 and consensus.value(field) != next(iter(source_values)):
                raise ValueError(f"CONSENSUS_ALTERS_UNANIMOUS_VALUE: {review_id}:{field}")
    return tuple(rows)


def _review_values(report: PanelAgreement, review_id: str, field: str) -> list[str]:
    return [
        next(row for row in report.rows_by_reviewer[name] if row.review_id == review_id).value(field)
        for name in report.reviewer_names
    ]


def build_adjudication_page(items: Sequence[ReviewItem], report: PanelAgreement) -> str:
    """Build a restricted page with no selection class or checker output."""
    item_by_id = {item.review_id: item for item in items}
    sections = []
    initial: dict[str, dict[str, str]] = {}
    for index, review_id in enumerate(report.rows_by_reviewer[report.reviewer_names[0]]):
        rid = review_id.review_id
        item = item_by_id[rid]
        disputed = set(report.disagreement_fields_by_id.get(rid, ()))
        events = "".join(
            f"<li><b>+{relative:.3f} s</b><p>{html.escape(text)}</p></li>"
            for text, relative in zip(item.event_texts, item.relative_times_s)
        )
        rows = []
        for reviewer in report.reviewer_names:
            row = next(row for row in report.rows_by_reviewer[reviewer] if row.review_id == rid)
            rows.append(
                "<tr><th>{}</th><td>{}</td><td>{}</td><td>{}</td><td>{}</td></tr>".format(
                    html.escape(reviewer),
                    html.escape(row.temporal_requirement_explicit),
                    html.escape(row.required_action_sequence),
                    html.escape(row.textual_consistency),
                    html.escape(row.notes),
                )
            )
        prefill: dict[str, str] = {}
        controls = []
        for field in CATEGORICAL_FIELDS:
            values = _review_values(report, rid, field)
            value = values[0] if field not in disputed else ""
            prefill[field] = value
            if field == "required_action_sequence":
                controls.append(
                    f'<label>{field}<input name="{field}" value="{html.escape(value, quote=True)}" '
                    f'{"readonly" if field not in disputed else ""}></label>'
                )
            else:
                options = '<option value="">-- 합의 판정 선택 --</option>' + "".join(
                    f'<option value="{html.escape(choice, quote=True)}" '
                    f'{"selected" if choice == value else ""}>{html.escape(choice)}</option>'
                    for choice in CONTRACT_CHOICES[field]
                )
                controls.append(
                    f'<label>{field}<select name="{field}" '
                    f'{"disabled" if field not in disputed else ""}>{options}</select></label>'
                    + (f'<input type="hidden" name="{field}" value="{html.escape(value, quote=True)}">' if field not in disputed else "")
                )
        prefill["notes"] = ""
        initial[rid] = {"review_id": rid, **prefill}
        sections.append(
            f'<section class="item" data-review-id="{rid}"><h2>{index + 1}. {rid}</h2>'
            f'<ol>{events}</ol><table><thead><tr><th>검토자</th><th>시간 요구</th><th>행동열</th><th>텍스트 일관성</th><th>메모</th></tr></thead>'
            f'<tbody>{"".join(rows)}</tbody></table><p class="disputed">합의 필요 필드: {html.escape(", ".join(sorted(disputed)) or "없음(전원 일치)")}</p>'
            f'<form>{"".join(controls)}<label>합의 메모<textarea name="notes"></textarea></label></form></section>'
        )
    columns = json.dumps(CONTRACT_REVIEW_FIELDS, ensure_ascii=False)
    initial_json = json.dumps(initial, ensure_ascii=False).replace("</", "<\\/")
    return f'''<!doctype html><html lang="ko"><meta charset="utf-8"><title>연속 CoC 패널 합의 검토</title>
<style>body{{font-family:sans-serif;max-width:1200px;margin:auto;padding:1rem}}.item{{border:1px solid #bbb;padding:1rem;margin:1rem 0}}table{{border-collapse:collapse;width:100%;font-size:.85rem}}th,td{{border:1px solid #ccc;padding:.4rem;vertical-align:top}}label{{display:block;margin:.7rem 0}}input,select,textarea{{width:100%;padding:.4rem}}textarea{{min-height:3rem}}.disputed{{font-weight:bold;color:#8b2d19}}button{{position:sticky;top:.5rem;padding:.8rem}}</style>
<body><h1>연속 CoC 계약 패널 합의 검토</h1><p>독립 검토가 끝난 뒤의 합의 단계입니다. 네 판정과 문장만 보고 결정하십시오. 전원 일치 필드는 잠겨 있으며, 불일치 필드는 사람이 선택해야 합니다. 영상 상태나 실제 차량 안전을 추정하지 마십시오.</p>
<button id="export">완료 CSV 저장</button>{''.join(sections)}
<script>const columns={columns},rows={initial_json};
function cell(v){{v=String(v??"");return /[",\\r\\n]/.test(v)?'"'+v.replaceAll('"','""')+'"':v}}
document.getElementById("export").onclick=()=>{{for(const section of document.querySelectorAll(".item")){{const id=section.dataset.reviewId,form=new FormData(section.querySelector("form"));for(const field of columns.slice(1))rows[id][field]=form.get(field)||""}}const incomplete=Object.values(rows).filter(row=>columns.slice(1,-1).some(field=>!row[field]));if(incomplete.length){{alert(`미완료 항목 ${{incomplete.length}}개가 있습니다.`);return}}const lines=[columns.join(","),...Object.values(rows).map(row=>columns.map(c=>cell(row[c])).join(","))];const blob=new Blob(["\\ufeff"+lines.join("\\r\\n")+"\\r\\n"],{{type:"text/csv;charset=utf-8"}}),a=document.createElement("a");a.href=URL.createObjectURL(blob);a.download="contract_review_consensus.csv";a.click()}};</script></body></html>'''


def _summary(report: PanelAgreement, paths: Mapping[str, Path], clusters: int) -> dict[str, object]:
    label_counts = {
        field: {
            reviewer: dict(Counter(row.value(field) for row in report.rows_by_reviewer[reviewer]))
            for reviewer in report.reviewer_names
        }
        for field in CATEGORICAL_FIELDS
    }
    return {
        "schema_version": "sequential-coc-panel-review-v1",
        "status": "WAITING_FOR_PANEL_ADJUDICATION",
        "reviewer_count": len(report.reviewer_names),
        "reviewer_rows": {name: len(report.rows_by_reviewer[name]) for name in report.reviewer_names},
        "independent_clusters": clusters,
        "disputed_item_count": len(report.disagreement_fields_by_id),
        "disputed_field_counts": {
            field: sum(field in fields for fields in report.disagreement_fields_by_id.values())
            for field in CATEGORICAL_FIELDS
        },
        "field_agreement": {
            field: {"raw_agreement": score.raw_agreement, "kappa": score.kappa}
            for field, score in report.by_field.items()
        },
        "vote_patterns": report.vote_patterns,
        "label_counts": label_counts,
        "source_csv_sha256": {
            name: hashlib.sha256(path.read_bytes()).hexdigest() for name, path in paths.items()
        },
        "sample_unit": "SCENE_CLUSTER",
        "consensus_policy": "HUMAN_ADJUDICATION_NO_AUTOMATIC_MAJORITY",
    }


def main(
    argv: Sequence[str] | None = None,
    printer: Callable[[str], None] = print,
    review_items: Sequence[ReviewItem] | None = None,
) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--review-dir", type=Path, default=REVIEW_DIR)
    args = parser.parse_args(argv)
    review_dir = args.review_dir
    try:
        packet = _review_packet_from_mapping(review_dir)
        paths = discover_panel_csvs(review_dir)
        if len(paths) < 2:
            printer(json.dumps({"status": "WAITING_FOR_PANEL_REVIEWS", "reviewer_count": len(paths)}, sort_keys=True))
            return 0
        reviews = {
            name: validate_contract_review_csv(path, set(packet.expected_ids))
            for name, path in paths.items()
        }
        report = compare_panel_reviews(reviews)
        if review_items is None:
            selected, _, _ = select_review_items(read_natural_windows())
            review_items = selected
        if {item.review_id for item in review_items} != set(packet.expected_ids):
            raise ValueError("ADJUDICATION_ITEM_ID_MISMATCH")
        summary = _summary(report, paths, packet.independent_clusters)
        consensus_path = review_dir / CONSENSUS_FILENAME
        if consensus_path.exists():
            consensus = validate_contract_review_csv(consensus_path, set(packet.expected_ids))
            validate_panel_consensus(consensus, report, set(packet.expected_ids))
            summary["status"] = "PANEL_REVIEW_COMPLETE"
        _atomic_write_restricted(
            review_dir / SUMMARY_FILENAME,
            json.dumps(summary, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        )
        _atomic_write_restricted(
            review_dir / ADJUDICATION_FILENAME,
            build_adjudication_page(review_items, report),
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        printer(json.dumps({"status": "PANEL_REVIEW_INVALID", "error": str(exc)}, sort_keys=True))
        return 2
    printer(json.dumps(summary, sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
