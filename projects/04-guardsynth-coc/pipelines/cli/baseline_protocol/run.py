"""Run B0-B8/B13 on the locked M14 software matrix without scoring quality."""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import date
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

from cli.project_paths import project_root


ROOT = project_root(__file__)
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from guard_synth.baseline_protocol import ALL_BASELINES, baseline_manifest, run_baseline
from guard_synth.frontend_matrix import build_locked_frontend_cases
from guard_synth.source_catalog import load_source_catalog


EXPERIMENT_ID = "GUARDSYNTH-BASELINE-PROTOCOL-001"


def _write(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def execute(*, catalog_path: Path, output_dir: Path) -> dict[str, Any]:
    if not catalog_path.is_file():
        raise FileNotFoundError("source catalog is missing")
    if output_dir.exists():
        raise FileExistsError(f"refusing to overwrite existing output: {output_dir}")
    catalog = load_source_catalog(catalog_path)
    records = []
    for case in build_locked_frontend_cases():
        for baseline_id in ALL_BASELINES:
            result = run_baseline(
                baseline_id,
                request_raw=case["request"],
                catalog=catalog,
                auxiliary=case["baseline_auxiliary"],
            )
            records.append({
                "case_id": case["case_id"],
                "slice": case["slice"],
                "baseline_result": result,
            })
    counts = {
        baseline_id: dict(Counter(
            record["baseline_result"]["status"]
            for record in records
            if record["baseline_result"]["baseline_id"] == baseline_id
        ))
        for baseline_id in ALL_BASELINES
    }
    firewall_violations = sum(
        not set(item["baseline_result"]["used_channels"]).issubset(
            item["baseline_result"]["declared_channels"]
        )
        for item in records
    )
    output_dir.mkdir(parents=True)
    _write(output_dir / "BASELINE_MANIFEST.json", baseline_manifest())
    _write(output_dir / "BASELINE_RESULTS.json", {"records": records})
    _write(output_dir / "METRIC_CONTRACT.json", {
        "protocol_version": "guardsynth-baseline-metric-contract-v0.1",
        "quality_scoring_enabled": False,
        "future_gold_source": "INDEPENDENT_EXPERT_ADJUDICATION_M16",
        "metrics": [
            "applicability_macro_f1", "source_precision", "unsupported_rate",
            "false_deadlock_rate", "expert_correction_time_s",
        ],
        "abstentions_count_as_outputs": True,
        "missing_provider_is_not_success": True,
        "split_or_expected_labels_read_by_adapter": False,
    })
    result = {
        "status": "EXECUTED",
        "case_count": 24,
        "baseline_count": len(ALL_BASELINES),
        "record_count": len(records),
        "schema_valid_result_count": len(records),
        "channel_firewall_violations": firewall_violations,
        "status_counts_by_baseline": counts,
        "hidden_failures": 0,
        "quality_scoring_enabled": False,
        "software_protocol_gate_passed": (
            len(records) == 24 * len(ALL_BASELINES)
            and firewall_violations == 0
        ),
        "claim_scope": (
            "BASELINE_INTERFACE_AND_ABSTENTION_SMOKE_NOT_PERFORMANCE_RANKING_"
            "OR_VEHICLE_SAFETY"
        ),
    }
    _write(output_dir / "RESULT.json", result)
    _write(output_dir / "RUN_MANIFEST.json", {
        "experiment_id": EXPERIMENT_ID,
        "run_id": output_dir.name,
        "run_date": date.today().isoformat(),
        "input_class": "PUBLIC_SYNTHETIC",
        "deterministic": True,
        "random_seed": None,
        "input_hashes": {catalog_path.name: _sha256(catalog_path)},
        "code_hash": _sha256(ROOT / "projects/04-guardsynth-coc/src/guard_synth/baseline_protocol.py"),
        "claim_scope": result["claim_scope"],
    })
    (output_dir / "REPORT_KO.md").write_text(
        f"""# M15 GuardSynth baseline protocol smoke run

- 상태: **{result['status']}**
- software protocol gate: **{'PASS' if result['software_protocol_gate_passed'] else 'FAIL'}**
- baseline: **{result['baseline_count']}개 (B0–B8/B13)**
- locked cases: **{result['case_count']}개**
- 공통 schema 결과: **{result['schema_valid_result_count']}/{result['record_count']}**
- channel firewall 위반: **{result['channel_firewall_violations']}건**
- 숨긴 failure: **{result['hidden_failures']}건**
- 품질 점수 계산: **아니오**

외부 free-form/scene model provider, matrix의 physics/assurance와 reachability 입력은 제공되지
않았으므로 관련 adapter는 명시적으로 abstain했다. B5/B6는 각각 deterministic BM25
source retrieval과 scene-only semantic filter의 `style adapter`이며 원 시스템 재현이 아니다.
이 run은 비교 인터페이스·입력 channel·abstention protocol을 동결할 뿐 성능 우열이나 실제
안전 효과를 보여주지 않는다.
""",
        encoding="utf-8",
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    result = execute(catalog_path=args.catalog, output_dir=args.output_dir)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result["software_protocol_gate_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
