"""Audit the first source-bearing Republic of Korea GuardSynth catalog."""

from __future__ import annotations

import argparse
from datetime import date
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from cli.project_paths import project_root


ROOT = project_root(__file__)
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from guard_synth.source_catalog import (
    KR_FIXTURE_PATH,
    SCHEMA_PATH,
    audit_source_catalog,
    load_source_catalog,
)


EXPERIMENT_ID = "GUARDSYNTH-SOURCE-CATALOG-001"
DEFAULT_RUN_ID = "kr-source-catalog-2026-08-10-v1"
CLAIM_SCOPE = "P0_SOURCE_CATALOG_TRACEABILITY_NOT_LEGAL_ADVICE_SENSOR_ACCURACY_VEHICLE_ASSURANCE_OR_SAFETY"


def _write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _test(command: list[str]) -> dict[str, Any]:
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(SRC) + os.pathsep + str(ROOT)
    completed = subprocess.run(
        command, cwd=ROOT, env=environment, text=True, capture_output=True, check=False
    )
    combined = completed.stdout + "\n" + completed.stderr
    match = re.search(r"Ran (\d+) tests?", combined)
    count = int(match.group(1)) if match else None
    return {
        "command": " ".join(command),
        "exit_code": completed.returncode,
        "test_count": count,
        "passed_count": count if completed.returncode == 0 else 0,
        "passed": completed.returncode == 0,
    }


def _report(result: dict[str, Any]) -> str:
    audit = result["audit"]
    tests = result["tests"]
    return f"""# GuardSynth 대한민국 source catalog v0.1 감사 보고서

- 상태: **{result['status']}**
- template: {audit['rule_template_count']}개
- slice 배분: pedestrian/cyclist {audit['slice_counts']['PEDESTRIAN_CYCLIST_YIELD']}, stop/signals {audit['slice_counts']['STOP_SIGNALS']}, following/cut-in {audit['slice_counts']['FOLLOWING_CUT_IN']}
- broad family: {audit['family_coverage_count']}/6
- source record/claim: {audit['source_record_count']}/{audit['source_claim_count']}
- predicate failure-to-UNKNOWN: {audit['failure_to_unknown_coverage']['numerator']}/{audit['failure_to_unknown_coverage']['denominator']}
- source 없는 규범·실행 수치: {audit['unsourced_normative_or_numeric_value_count']}건
- 주장 범위: `{CLAIM_SCOPE}`

## 결과

대한민국 도로교통법과 시행규칙의 현행 공식 원문을 기준으로 세 slice 15개 규칙을
source claim에 연결했다. 법이 숫자를 제공하지 않는 안전거리에는 값을 넣지 않고
`UNSUPPORTED_LEGAL_TEXT_HAS_NO_NUMERIC_BOUND`를 유지했다. sensor freshness, release
hysteresis와 fallback은 법률 원문이 아니라 별도 시스템 operationalization으로 구분했다.

## 테스트

- source catalog 집중: {tests['focused']['passed_count']}/{tests['focused']['test_count']}
- 전체 maintained: {tests['full']['passed_count']}/{tests['full']['test_count']}
- P0a 회귀: {tests['p0a']['passed_count']}/{tests['p0a']['test_count']}
- 구조/문서 링크: {tests['structure']['passed_count']}/{tests['structure']['test_count']}

## 제한

이 결과는 공식 source record, schema와 reference closure를 감사한 것이다. 법률 전문가의
적용 판단, 자연어 CoC parsing, 실제 장면 association, sensor 성능, 차량 assurance 및
차량 안전성을 입증하지 않는다. source record hash는 원문 파일 hash가 아니라 공개한
canonical record의 변경 검출용 hash다.
"""


def execute(run_id: str) -> tuple[Path, dict[str, Any]]:
    output = ROOT / "artifacts/results/public/guardsynth-source-catalog-001" / run_id
    if output.exists():
        raise FileExistsError(f"refusing to overwrite existing run: {run_id}")
    output.mkdir(parents=True)
    catalog = load_source_catalog()
    audit = audit_source_catalog(catalog)
    python = "/usr/bin/python3"
    tests = {
        "focused": _test([python, "-m", "unittest", "tests.guard_synth_eblc.test_source_catalog", "-v"]),
        "full": _test([python, "-m", "unittest", "discover", "-s", "tests/guard_synth_eblc", "-p", "test_*.py", "-v"]),
        "p0a": _test([python, "-m", "unittest", "experiments.eblc_pilot.test_pilot", "-v"]),
        "structure": _test([python, "-m", "unittest", "tests.structure.test_project_layout", "-v"]),
    }
    gates = {
        "template_count_12_to_20": 12 <= audit["rule_template_count"] <= 20,
        "each_slice_at_least_four": all(value >= 4 for value in audit["slice_counts"].values()),
        "six_family_coverage": audit["family_coverage_count"] == 6,
        "source_reference_closure": audit["reference_closure"],
        "no_unsourced_normative_or_numeric_value": audit["unsourced_normative_or_numeric_value_count"] == 0,
        "failure_to_unknown_complete": audit["failure_to_unknown_coverage"]["numerator"] == audit["failure_to_unknown_coverage"]["denominator"],
        "all_tests_pass": all(item["passed"] for item in tests.values()),
    }
    result = {
        "experiment_id": EXPERIMENT_ID,
        "run_id": run_id,
        "run_date": str(date.today()),
        "status": "EXECUTED" if all(gates.values()) else "FAILED",
        "decision": "M12_CATALOG_GATE_PASS" if all(gates.values()) else "M12_CATALOG_REWORK",
        "audit": audit,
        "gates": gates,
        "tests": tests,
        "claim_scope": CLAIM_SCOPE,
    }
    _write_json(output / "SOURCE_AUDIT.json", audit)
    _write_json(output / "RESULT.json", result)
    manifest = {
        "experiment_id": EXPERIMENT_ID,
        "run_id": run_id,
        "run_date": str(date.today()),
        "input_class": "PUBLIC_OFFICIAL_SOURCE_RECORDS",
        "jurisdiction": "KR",
        "catalog_version": catalog.raw["catalog_version"],
        "catalog_sha256": _sha256(KR_FIXTURE_PATH),
        "schema_sha256": _sha256(SCHEMA_PATH),
        "source_record_hash_basis": "CANONICAL_SOURCE_RECORD_NOT_DOCUMENT_BYTES",
        "determinism": "DETERMINISTIC_VALIDATION",
        "tests": tests,
        "claim_scope": CLAIM_SCOPE,
    }
    _write_json(output / "RUN_MANIFEST.json", manifest)
    (output / "REPORT_KO.md").write_text(_report(result), encoding="utf-8")
    return output, result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", default=DEFAULT_RUN_ID)
    args = parser.parse_args()
    output, result = execute(args.run_id)
    print(json.dumps({"output": str(output), "status": result["status"], "decision": result["decision"]}, ensure_ascii=False))
    return 0 if result["status"] == "EXECUTED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
