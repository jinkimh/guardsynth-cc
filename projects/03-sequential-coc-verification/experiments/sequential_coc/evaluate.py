#!/usr/bin/env python3
"""Separated evaluation domains and conservative claim gates.

Controlled mutations, natural contract review, and trajectory consistency have
different sampling units.  This module keeps their aggregates in separate
top-level objects and never treats recorded behavior as state ground truth.
"""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import asdict, dataclass, is_dataclass, replace
import json
import math
from pathlib import Path
import os
from statistics import NormalDist
import tempfile
from typing import Mapping, Sequence

if __package__ in (None, ""):
    import sys

    sys.path.insert(0, str(next(parent for parent in Path(__file__).resolve().parents if (parent / "PROJECT_REGISTRY.json").is_file())))

from experiments.sequential_coc.contract_review import (
    CONSENSUS_FILENAME,
    FIRST_PASS_FILENAMES,
    _review_packet_from_mapping,
    compare_contract_reviews,
    validate_consensus,
    validate_contract_review_csv,
)
from experiments.sequential_coc.panel_review import (
    compare_panel_reviews,
    discover_panel_csvs,
    validate_panel_consensus,
)
from experiments.sequential_coc.contract_ir import Action, ContractEvent, EvidenceValue
from experiments.sequential_coc.run_uppaal import last_verifyta_run_metadata, run_verifyta
from experiments.sequential_coc.stateful_checker import check_stateful
from experiments.sequential_coc.uppaal_generator import (
    build_uppaal_model,
    write_uppaal_artifacts,
)


OUTPUT_DIR = (
    Path(__file__).resolve().parents[1]
    / "results"
    / "restricted"
    / "sequential-coc-consistency-v1"
)
METRICS_PATH = OUTPUT_DIR / "metrics.json"
MUTATIONS_PATH = OUTPUT_DIR / "mutations.jsonl"
TRAJECTORY_PATH = OUTPUT_DIR / "trajectory-results.jsonl"
REVIEW_DIR = OUTPUT_DIR / "review"

CHECKERS = ("event_local", "stateful")
MUTATION_ORACLES = (
    "HOLD_GO_CONFLICT",
    "PREMATURE_RELEASE",
    "ORDER_VIOLATION",
    "STALE_OBLIGATION",
)
BASELINE_PROFILE = "baseline"
VERDICTS = ("ALIGNED", "NOT_ALIGNED", "UNKNOWN")


@dataclass(frozen=True, slots=True)
class EvaluationInputs:
    mutation_pairs: Sequence[Mapping[str, object]]
    natural_cluster_ids: Sequence[str]
    review_labels_a: Sequence[Mapping[str, object]] | None
    review_labels_b: Sequence[Mapping[str, object]] | None
    consensus_labels: Sequence[Mapping[str, object]] | None
    trajectory_summary: Mapping[str, object]
    uppaal_mismatch_count: int | None = None
    actual_verifyta_ran: bool = False
    uppaal_evaluated_count: int = 0
    panel_review_summary: Mapping[str, object] | None = None
    review_id_to_cluster_id: Mapping[str, str] | None = None


@dataclass(frozen=True, slots=True)
class UppaalEvidence:
    actual_verifyta_ran: bool
    evaluated_count: int
    mismatch_count: int | None


def _hold_event(
    timestamp_us: int,
    event_id: str,
    release: EvidenceValue,
    *,
    parse_status: str = "PARSED",
) -> ContractEvent:
    release_known = release is not EvidenceValue.UNKNOWN
    return ContractEvent(
        scene_id="uppaal-equivalence",
        event_id=event_id,
        timestamp_us=timestamp_us,
        action=Action.STOP_OR_HOLD,
        release_known=release_known,
        release_value=release is EvidenceValue.TRUE,
        release_condition="clearance confirmed",
        permitted_next_action=Action.ACCELERATE_OR_PROCEED,
        provenance="DETERMINISTIC_EQUIVALENCE_FIXTURE",
        parse_status=parse_status,
    )


def _proceed_event(
    timestamp_us: int = 1,
    event_id: str = "proceed",
    *,
    parse_status: str = "PARSED",
) -> ContractEvent:
    return ContractEvent(
        scene_id="uppaal-equivalence",
        event_id=event_id,
        timestamp_us=timestamp_us,
        action=Action.ACCELERATE_OR_PROCEED,
        provenance="DETERMINISTIC_EQUIVALENCE_FIXTURE",
        parse_status=parse_status,
    )


def _equivalence_tables() -> tuple[tuple[ContractEvent, ...], ...]:
    normal_go = replace(
        _proceed_event(),
        release_known=True,
        release_value=True,
        satisfaction_known=True,
        satisfaction_value=True,
    )
    premature = replace(
        _proceed_event(event_id="premature"),
        release_known=True,
        release_value=False,
    )
    order = replace(
        _proceed_event(event_id="out-of-order"),
        satisfaction_known=True,
        satisfaction_value=False,
    )
    stale = _hold_event(1, "stale-hold", EvidenceValue.TRUE)
    return (
        (_hold_event(0, "normal-hold", EvidenceValue.FALSE), normal_go),
        (_hold_event(0, "conflict-hold", EvidenceValue.FALSE), _proceed_event()),
        (premature,),
        (order,),
        (_hold_event(0, "stale-base", EvidenceValue.FALSE), stale),
        (_hold_event(0, "unknown-hold", EvidenceValue.UNKNOWN), _proceed_event()),
        (
            _hold_event(0, "mixed-hold", EvidenceValue.FALSE),
            _proceed_event(parse_status="UNKNOWN_AMBIGUOUS_ORDER"),
        ),
    )


def _result_signature(result: object) -> tuple[object, ...]:
    return (
        result.verdict,
        result.contradiction_types,
        result.first_event_id,
        result.unknown_reasons,
    )


def collect_uppaal_evidence(verifyta: Path) -> UppaalEvidence:
    """Execute all seven canonical tables and return process-backed evidence.

    ``actual_verifyta_ran`` is true only if every model invocation returned zero.
    Semantic/parser mismatches remain counted separately and therefore cannot
    open the equivalence claim gate.
    """
    tables = _equivalence_tables()
    mismatches = 0
    successful_runs = 0
    try:
        with tempfile.TemporaryDirectory(prefix="sequential-coc-uppaal-") as temporary:
            root = Path(temporary)
            for number, events in enumerate(tables):
                tree, queries = build_uppaal_model(list(events))
                model = root / f"model-{number}.xml"
                query = root / f"model-{number}.q"
                write_uppaal_artifacts(tree, queries, model, query)
                actual = run_verifyta(model, query, verifyta)
                metadata = last_verifyta_run_metadata()
                if metadata is None or metadata.returncode != 0 or not metadata.command:
                    return UppaalEvidence(False, 0, None)
                successful_runs += 1
                expected = check_stateful(list(events))
                mismatches += _result_signature(actual) != _result_signature(expected)
    except (OSError, PermissionError, ValueError):
        return UppaalEvidence(False, 0, None)
    return UppaalEvidence(successful_runs == len(tables), successful_runs, mismatches)


def wilson_interval(
    successes: int, total: int, confidence: float = 0.95
) -> tuple[float, float]:
    """Return a two-sided Wilson score interval for a binomial proportion."""
    if isinstance(successes, bool) or not isinstance(successes, int):
        raise TypeError("successes must be an integer")
    if isinstance(total, bool) or not isinstance(total, int):
        raise TypeError("total must be an integer")
    if successes < 0 or total <= 0 or successes > total:
        raise ValueError("require 0 <= successes <= total and total > 0")
    if isinstance(confidence, bool) or not isinstance(confidence, (int, float)):
        raise TypeError("confidence must be numeric")
    if not math.isfinite(float(confidence)) or not 0 < confidence < 1:
        raise ValueError("confidence must be in (0, 1)")

    z = NormalDist().inv_cdf(1.0 - (1.0 - float(confidence)) / 2.0)
    proportion = successes / total
    denominator = 1.0 + z * z / total
    center = (proportion + z * z / (2.0 * total)) / denominator
    margin = (
        z
        * math.sqrt(
            proportion * (1.0 - proportion) / total
            + z * z / (4.0 * total * total)
        )
        / denominator
    )
    lower = 0.0 if successes == 0 else max(0.0, center - margin)
    upper = 1.0 if successes == total else min(1.0, center + margin)
    return lower, upper


def cohens_kappa(labels_a: Sequence[object], labels_b: Sequence[object]) -> float | None:
    """Return unweighted Cohen's kappa, or ``None`` when it is undefined."""
    values_a, values_b = tuple(labels_a), tuple(labels_b)
    if len(values_a) != len(values_b):
        raise ValueError("label sequences must have equal lengths")
    if not values_a:
        return None
    observed = sum(a == b for a, b in zip(values_a, values_b)) / len(values_a)
    counts_a, counts_b = Counter(values_a), Counter(values_b)
    expected = sum(
        counts_a[label] / len(values_a) * counts_b[label] / len(values_b)
        for label in counts_a.keys() | counts_b.keys()
    )
    if math.isclose(expected, 1.0):
        return None
    return (observed - expected) / (1.0 - expected)


def _rate(successes: int, total: int) -> dict[str, object]:
    return {
        "detected": successes,
        "total": total,
        "rate": successes / total,
        "wilson_95": wilson_interval(successes, total),
    }


def _verdict(pair: Mapping[str, object], variant: str, checker: str) -> str:
    try:
        checker_results = pair["checker_results"]
        assert isinstance(checker_results, Mapping)
        variants = checker_results[variant]
        assert isinstance(variants, Mapping)
        result = variants[checker]
        assert isinstance(result, Mapping)
        verdict = result["verdict"]
    except (KeyError, TypeError, AssertionError) as exc:
        raise ValueError(f"invalid mutation checker result: {variant}/{checker}") from exc
    if verdict not in {"CONSISTENT", "CONTRADICTION", "UNKNOWN"}:
        raise ValueError(f"invalid mutation verdict: {verdict!r}")
    return str(verdict)


def _controlled_metrics(pairs: Sequence[Mapping[str, object]]) -> dict[str, object]:
    rows = tuple(pairs)
    pair_ids = [row.get("pair_id") for row in rows]
    if any(not isinstance(value, str) or not value for value in pair_ids):
        raise ValueError("every mutation row requires a non-empty pair_id")
    if len(pair_ids) != len(set(pair_ids)):
        raise ValueError("mutation pair_id values must be unique")

    by_type: dict[str, dict[str, object]] = {}
    observed_strata = Counter(str(row.get("oracle")) for row in rows)
    expected_strata = {oracle: 10 for oracle in MUTATION_ORACLES}
    stratification_ready = dict(observed_strata) == expected_strata
    mutation_types = sorted(observed_strata)
    for mutation_type in mutation_types:
        typed = tuple(row for row in rows if row.get("oracle") == mutation_type)
        stateful = sum(
            _verdict(row, "mutated", "stateful") == "CONTRADICTION" for row in typed
        )
        local = sum(
            _verdict(row, "mutated", "event_local") == "CONTRADICTION"
            for row in typed
        )
        by_type[mutation_type] = {
            "total": len(typed),
            "stateful_detected": stateful,
            "stateful_rate": stateful / len(typed),
            "stateful_wilson_95": wilson_interval(stateful, len(typed)),
            "event_local_detected": local,
            "event_local_rate": local / len(typed),
            "event_local_wilson_95": wilson_interval(local, len(typed)),
        }

    total = len(rows)
    if total == 0:
        raise ValueError("at least one controlled mutation pair is required")
    stateful_detected = sum(
        _verdict(row, "mutated", "stateful") == "CONTRADICTION" for row in rows
    )
    local_detected = sum(
        _verdict(row, "mutated", "event_local") == "CONTRADICTION" for row in rows
    )
    additional = sum(
        _verdict(row, "mutated", "stateful") == "CONTRADICTION"
        and _verdict(row, "mutated", "event_local") != "CONTRADICTION"
        for row in rows
    )
    false_positive = {
        checker: sum(
            _verdict(row, "original", checker) == "CONTRADICTION" for row in rows
        )
        for checker in CHECKERS
    }
    return {
        "sample_unit": "PAIR",
        "pair_count": total,
        "stratification_status": (
            "READY" if stratification_ready else "NOT_READY_INVALID_STRATIFICATION"
        ),
        "stratification": {
            "expected_counts": expected_strata,
            "observed_counts": dict(sorted(observed_strata.items())),
        },
        "detection_by_type": by_type,
        "event_local_detection": _rate(local_detected, total),
        "stateful_detection": _rate(stateful_detected, total),
        "stateful_additional_detection": _rate(additional, total),
        "original_false_positive": {
            checker: {
                "count": count,
                "total": total,
                "rate": count / total,
                "wilson_95": wilson_interval(count, total),
            }
            for checker, count in false_positive.items()
        },
    }


def _mapping_row(row: object) -> dict[str, object]:
    if isinstance(row, Mapping):
        return dict(row)
    if is_dataclass(row):
        return asdict(row)
    raise TypeError("review labels must be mappings or dataclass rows")


def _aligned_review_rows(
    rows: Sequence[Mapping[str, object]], expected_count: int
) -> dict[str, dict[str, object]]:
    mapped = [_mapping_row(row) for row in rows]
    by_id = {row.get("review_id"): row for row in mapped}
    if len(by_id) != len(mapped) or any(
        not isinstance(review_id, str) or not review_id for review_id in by_id
    ):
        raise ValueError("review_id values must be non-empty and unique")
    if len(mapped) != expected_count:
        raise ValueError("review row count must equal natural cluster count")
    return by_id  # type: ignore[return-value]


def _natural_metrics(inputs: EvaluationInputs) -> dict[str, object]:
    cluster_ids = tuple(inputs.natural_cluster_ids)
    if any(not isinstance(value, str) or not value for value in cluster_ids):
        raise ValueError("natural cluster IDs must be non-empty strings")
    if len(cluster_ids) != len(set(cluster_ids)):
        raise ValueError("natural cluster IDs must be unique")
    base: dict[str, object] = {
        "sample_unit": "SCENE_CLUSTER",
        "cluster_count": len(cluster_ids),
    }
    supplied = (
        inputs.review_labels_a,
        inputs.review_labels_b,
        inputs.consensus_labels,
    )
    if any(value is None for value in supplied):
        panel = inputs.panel_review_summary
        return {
            **base,
            "status": (
                "WAITING_FOR_PANEL_ADJUDICATION" if panel is not None else "NOT_RUN"
            ),
            "reviewer_rows": (
                panel.get("reviewer_rows", "NOT_RUN")
                if panel is not None
                else {"A": "NOT_RUN", "B": "NOT_RUN"}
            ),
            "agreement_by_field": (
                panel.get("field_agreement", "NOT_RUN")
                if panel is not None
                else "NOT_RUN"
            ),
            "consensus_count": "NOT_RUN",
            "evaluable_textual_clusters": "NOT_RUN",
            "kiee_update": "NOT_RUN",
        }

    rows_a = _aligned_review_rows(inputs.review_labels_a or (), len(cluster_ids))
    rows_b = _aligned_review_rows(inputs.review_labels_b or (), len(cluster_ids))
    consensus = _aligned_review_rows(inputs.consensus_labels or (), len(cluster_ids))
    if set(rows_a) != set(rows_b) or set(rows_a) != set(consensus):
        raise ValueError("review and consensus ID sets must match")

    excluded = {"review_id", "notes"}
    fields = sorted((set.intersection(*(set(row) for row in rows_a.values()))) - excluded)
    if not fields:
        raise ValueError("review rows require at least one categorical field")
    agreement = {}
    for field in fields:
        values_a = [rows_a[review_id][field] for review_id in sorted(rows_a)]
        values_b = [rows_b[review_id][field] for review_id in sorted(rows_a)]
        agreement[field] = {
            "raw_agreement": sum(a == b for a, b in zip(values_a, values_b))
            / len(values_a),
            "kappa": cohens_kappa(values_a, values_b),
        }

    evaluable = sum(
        row.get("temporal_requirement_explicit") == "YES"
        and row.get("textual_consistency")
        in {"TEXTUAL_CONTRADICTION", "TEXTUALLY_CONSISTENT"}
        for row in consensus.values()
    )
    temporal_counts = dict(
        sorted(Counter(str(row["temporal_requirement_explicit"]) for row in consensus.values()).items())
    )
    textual_counts = dict(
        sorted(Counter(str(row["textual_consistency"]) for row in consensus.values()).items())
    )
    logical_trajectory_cross_tab: object = "NOT_RUN"
    if inputs.review_id_to_cluster_id is not None:
        scene_records = inputs.trajectory_summary.get("scene_records")
        if isinstance(scene_records, Sequence) and not isinstance(scene_records, (str, bytes)):
            trajectory_by_scene = {
                record.get("scene_cluster_id"): record
                for record in scene_records
                if isinstance(record, Mapping)
            }
            cross: dict[str, Counter[str]] = {}
            for review_id, row in consensus.items():
                scene_id = inputs.review_id_to_cluster_id.get(review_id)
                record = trajectory_by_scene.get(scene_id)
                if not isinstance(record, Mapping):
                    verdict = "UNKNOWN"
                else:
                    thresholds = record.get("threshold_results")
                    baseline = thresholds.get("baseline") if isinstance(thresholds, Mapping) else None
                    verdict = (
                        str(baseline.get("verdict"))
                        if isinstance(baseline, Mapping)
                        else "UNKNOWN"
                    )
                    if verdict not in VERDICTS:
                        verdict = "UNKNOWN"
                logical = str(row["textual_consistency"])
                cross.setdefault(logical, Counter())[verdict] += 1
            logical_trajectory_cross_tab = {
                logical: {verdict: counts.get(verdict, 0) for verdict in VERDICTS}
                for logical, counts in sorted(cross.items())
            }
    panel = inputs.panel_review_summary
    return {
        **base,
        "status": "COMPLETE",
        "reviewer_rows": (
            panel.get("reviewer_rows")
            if panel is not None
            else {"A": len(rows_a), "B": len(rows_b)}
        ),
        "agreement_by_field": (
            panel.get("field_agreement") if panel is not None else agreement
        ),
        "consensus_count": len(consensus),
        "evaluable_textual_clusters": evaluable,
        "consensus_temporal_counts": temporal_counts,
        "consensus_textual_counts": textual_counts,
        "consensus_unknown_count": textual_counts.get(
            "UNKNOWN_EXTERNAL_EVIDENCE_REQUIRED", 0
        ),
        "logical_trajectory_cross_tab_baseline": logical_trajectory_cross_tab,
        "kiee_update": "NOT_RUN",
    }


def _count_map(value: object, context: str) -> dict[str, int]:
    if not isinstance(value, Mapping) or set(value) != set(VERDICTS):
        raise ValueError(f"{context} requires exact ALIGNED/NOT_ALIGNED/UNKNOWN counts")
    result: dict[str, int] = {}
    for verdict in VERDICTS:
        count = value[verdict]
        if isinstance(count, bool) or not isinstance(count, int) or count < 0:
            raise ValueError(f"{context} counts must be non-negative integers")
        result[verdict] = count
    return result


def _trajectory_metrics(summary: Mapping[str, object]) -> dict[str, object]:
    sample_units = summary.get("sample_units")
    counts = summary.get("verdict_counts")
    changes = summary.get("verdict_change_counts")
    if not isinstance(sample_units, Mapping) or not isinstance(counts, Mapping):
        raise ValueError("trajectory summary requires sample_units and verdict_counts")
    if not isinstance(changes, Mapping):
        raise ValueError("trajectory summary requires verdict_change_counts")
    cross_tab: dict[str, dict[str, dict[str, int]]] = {}
    for unit in ("event", "scene_cluster"):
        total = sample_units.get(unit)
        profiles = counts.get(unit)
        if isinstance(total, bool) or not isinstance(total, int) or total < 0:
            raise ValueError(f"invalid trajectory {unit} sample count")
        if not isinstance(profiles, Mapping) or set(profiles) != {
            "baseline",
            "strict",
            "lenient",
        }:
            raise ValueError(f"trajectory {unit} requires three threshold profiles")
        cross_tab[unit] = {}
        for profile in ("baseline", "strict", "lenient"):
            verdict_counts = _count_map(profiles[profile], f"{unit}/{profile}")
            if sum(verdict_counts.values()) != total:
                raise ValueError(f"trajectory {unit}/{profile} denominator mismatch")
            cross_tab[unit][profile] = verdict_counts
        changed = changes.get(unit)
        if isinstance(changed, bool) or not isinstance(changed, int) or not 0 <= changed <= total:
            raise ValueError(f"invalid trajectory {unit} sensitivity count")

    linked = summary.get("linked_event_count")
    if isinstance(linked, bool) or not isinstance(linked, int) or not 0 <= linked <= sample_units["event"]:
        raise ValueError("invalid linked trajectory count")
    return {
        "sample_unit": "SCENE_CLUSTER_PRIMARY_EVENT_SECONDARY",
        "scene_cluster_count": sample_units["scene_cluster"],
        "event_count": sample_units["event"],
        "linked_trajectory_count": linked,
        "verdict_counts": cross_tab["scene_cluster"][BASELINE_PROFILE],
        "consistency_cross_tab": cross_tab,
        "threshold_sensitivity": {
            "verdict_change_counts": {
                "event": changes["event"],
                "scene_cluster": changes["scene_cluster"],
            }
        },
        "interpretation": "EXPLORATORY_CONSISTENCY_NOT_GROUND_TRUTH_SAFETY_OR_OPTIMALITY",
    }


def evaluate_all(inputs: EvaluationInputs) -> dict[str, object]:
    """Evaluate all domains without pooling their independent sample units."""
    controlled = _controlled_metrics(inputs.mutation_pairs)
    natural = _natural_metrics(inputs)
    trajectory = _trajectory_metrics(inputs.trajectory_summary)
    consensus_available = natural["status"] == "COMPLETE"
    evaluable = natural["evaluable_textual_clusters"]
    mismatch = inputs.uppaal_mismatch_count
    if mismatch is not None and (
        isinstance(mismatch, bool) or not isinstance(mismatch, int) or mismatch < 0
    ):
        raise ValueError("uppaal_mismatch_count must be a non-negative integer or None")
    if isinstance(inputs.uppaal_evaluated_count, bool) or inputs.uppaal_evaluated_count < 0:
        raise ValueError("uppaal_evaluated_count must be non-negative")

    status = (
        "COMPLETE"
        if consensus_available
        else (
            "WAITING_FOR_PANEL_ADJUDICATION"
            if natural["status"] == "WAITING_FOR_PANEL_ADJUDICATION"
            else "WAITING_FOR_CONTRACT_REVIEW"
        )
    )
    claim_gate = {
        "MUTATION_EVALUABLE": (
            controlled["pair_count"] == 40
            and controlled["stratification_status"] == "READY"
        ),
        "UPPAAL_EQUIVALENT": mismatch == 0 and inputs.actual_verifyta_ran,
        "NATURAL_CONTRACT_DESCRIPTIVE": consensus_available,
        "NATURAL_QUANTITATIVE_READY": (
            isinstance(evaluable, int) and evaluable >= 20
        ),
        "NATURAL_ACTUAL_STATE_READY": False,
        "TRAJECTORY_EXPLORATORY": trajectory["linked_trajectory_count"] > 0,
        "GLOBAL_COC_MODEL_CLAIM": False,
        "PHYSICAL_SAFETY_CLAIM": False,
        "LEARNING_PERFORMANCE_CLAIM": False,
    }
    core_paper_prerequisites = all(
        claim_gate[key]
        for key in (
            "MUTATION_EVALUABLE",
            "UPPAAL_EQUIVALENT",
            "NATURAL_CONTRACT_DESCRIPTIVE",
            "TRAJECTORY_EXPLORATORY",
        )
    )
    if not core_paper_prerequisites:
        natural["paper_update_gate"] = "CLOSED"
        natural["paper_update_scope"] = "NONE"
    elif not claim_gate["NATURAL_QUANTITATIVE_READY"]:
        natural["paper_update_gate"] = "OPEN_DESCRIPTIVE_ONLY"
        natural["paper_update_scope"] = (
            "DESCRIPTIVE_NATURAL_RESULTS_ONLY_NO_NATURAL_QUANTITATIVE_RESULTS"
        )
    else:
        natural["paper_update_gate"] = "OPEN"
        natural["paper_update_scope"] = (
            "DESCRIPTIVE_AND_QUANTITATIVE_NATURAL_RESULTS_WITHIN_CLAIM_GATES"
        )
    return {
        "schema_version": "sequential-coc-separated-metrics-v1",
        "status": status,
        "sample_unit_boundaries": {
            "controlled_mutation": "PAIR",
            "natural_contract_review": "SCENE_CLUSTER",
            "trajectory_exploratory": "SCENE_CLUSTER_PRIMARY_EVENT_SECONDARY",
        },
        "controlled_mutation": controlled,
        "natural_contract_review": natural,
        "trajectory_exploratory": trajectory,
        "uppaal_equivalence": {
            "status": "RUN" if inputs.actual_verifyta_ran else "NOT_RUN",
            "actual_verifyta_ran": inputs.actual_verifyta_ran,
            "evaluated_count": (
                inputs.uppaal_evaluated_count
                if inputs.actual_verifyta_ran
                else "NOT_RUN"
            ),
            "mismatch_count": mismatch if inputs.actual_verifyta_ran else "NOT_RUN",
        },
        "claim_gate": claim_gate,
    }


def _jsonl_rows(path: Path) -> tuple[dict[str, object], ...]:
    with path.open("r", encoding="utf-8") as handle:
        rows = tuple(json.loads(line) for line in handle if line.strip())
    if any(not isinstance(row, dict) for row in rows):
        raise ValueError(f"{path.name} must contain JSON objects")
    return rows


def load_production_inputs(
    output_dir: Path = OUTPUT_DIR, verifyta: Path | None = None
) -> EvaluationInputs:
    mutations = _jsonl_rows(output_dir / MUTATIONS_PATH.name)
    trajectory_rows = _jsonl_rows(output_dir / TRAJECTORY_PATH.name)
    if len(trajectory_rows) != 1:
        raise ValueError("trajectory-results.jsonl must contain one aggregate row")

    review_dir = output_dir / "review"
    packet = _review_packet_from_mapping(review_dir)
    mapping = json.loads((review_dir / "adjudication-mapping.json").read_text(encoding="utf-8"))
    natural_cluster_ids = tuple(row["cluster_id"] for row in mapping)
    review_id_to_cluster_id = {
        row["review_id"]: row["cluster_id"] for row in mapping
    }
    a_path, b_path = (review_dir / name for name in FIRST_PASS_FILENAMES)
    consensus_path = review_dir / CONSENSUS_FILENAME
    labels_a = labels_b = consensus = None
    panel_summary = None
    panel_paths = discover_panel_csvs(review_dir)
    if len(panel_paths) >= 2:
        expected_ids = set(packet.expected_ids)
        panel_rows = {
            name: validate_contract_review_csv(path, expected_ids)
            for name, path in panel_paths.items()
        }
        panel_report = compare_panel_reviews(panel_rows)
        panel_summary = {
            "reviewer_rows": {
                name: len(panel_report.rows_by_reviewer[name])
                for name in panel_report.reviewer_names
            },
            "field_agreement": {
                field: {
                    "raw_agreement": score.raw_agreement,
                    "kappa": score.kappa,
                }
                for field, score in panel_report.by_field.items()
            },
        }
        if consensus_path.exists():
            consensus_rows = validate_contract_review_csv(consensus_path, expected_ids)
            validate_panel_consensus(consensus_rows, panel_report, expected_ids)
            first, second = panel_report.reviewer_names[:2]
            rows_a = panel_report.rows_by_reviewer[first]
            rows_b = panel_report.rows_by_reviewer[second]
            labels_a = tuple(asdict(row) for row in rows_a)
            labels_b = tuple(asdict(row) for row in rows_b)
            consensus = tuple(asdict(row) for row in consensus_rows)
    elif a_path.exists() and b_path.exists() and consensus_path.exists():
        expected_ids = set(packet.expected_ids)
        rows_a = validate_contract_review_csv(a_path, expected_ids)
        rows_b = validate_contract_review_csv(b_path, expected_ids)
        agreement = compare_contract_reviews(rows_a, rows_b)
        consensus_rows = validate_contract_review_csv(consensus_path, expected_ids)
        validate_consensus(consensus_rows, agreement, expected_ids)
        labels_a = tuple(asdict(row) for row in rows_a)
        labels_b = tuple(asdict(row) for row in rows_b)
        consensus = tuple(asdict(row) for row in consensus_rows)

    # Historical prose is never accepted as execution evidence.  The optional
    # executable path runs all seven canonical tables during this CLI process.
    uppaal = (
        collect_uppaal_evidence(verifyta)
        if verifyta is not None
        else UppaalEvidence(False, 0, None)
    )
    return EvaluationInputs(
        mutation_pairs=mutations,
        natural_cluster_ids=natural_cluster_ids,
        review_labels_a=labels_a,
        review_labels_b=labels_b,
        consensus_labels=consensus,
        trajectory_summary=trajectory_rows[0],
        uppaal_mismatch_count=uppaal.mismatch_count,
        actual_verifyta_ran=uppaal.actual_verifyta_ran,
        uppaal_evaluated_count=uppaal.evaluated_count,
        panel_review_summary=panel_summary,
        review_id_to_cluster_id=review_id_to_cluster_id,
    )


def _atomic_write_json(path: Path, value: Mapping[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(path.parent, 0o700)
    payload = (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        directory_descriptor = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory_descriptor)
        finally:
            os.close(directory_descriptor)
    finally:
        if temporary.exists():
            temporary.unlink()


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    parser.add_argument("--metrics-path", type=Path)
    parser.add_argument(
        "--verifyta",
        type=Path,
        help="execute seven canonical equivalence tables with this verifyta binary",
    )
    args = parser.parse_args(argv)
    try:
        result = evaluate_all(load_production_inputs(args.output_dir, args.verifyta))
        metrics_path = args.metrics_path or args.output_dir / METRICS_PATH.name
        _atomic_write_json(metrics_path, result)
    except (OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "INVALID_EVALUATION_INPUT", "reason": str(exc)}, sort_keys=True))
        return 2
    print(json.dumps({"status": result["status"], "metrics_path": str(metrics_path)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
