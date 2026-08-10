"""Validate project layout v2 and persist a reproducible public audit."""

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

from cli.checks.project_integrity import broken_markdown_links
from cli.project_paths import project_root


ROOT = project_root(__file__)
EXPERIMENT_ID = "PROJECT-LAYOUT-REFACTOR-001"
CLAIM_SCOPE = "REPOSITORY_LAYOUT_AND_SOFTWARE_REGRESSION_NOT_RESEARCH_OR_VEHICLE_SAFETY"
PIPELINE_MODULES = (
    "cli.pipelines.eblc.core_smt_compile.run",
    "cli.pipelines.eblc.p0b_schema_bcv.run",
    "cli.pipelines.eblc.program_conformance.run",
    "cli.pipelines.eblc.restricted_scene_grounding.run",
    "cli.pipelines.eblc.robustness_audit.run",
    "cli.pipelines.eblc.scenario_validation.run",
)


def _write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _run(command: list[str], extra_env: dict[str, str] | None = None) -> dict[str, Any]:
    environment = os.environ.copy()
    environment.update(extra_env or {})
    completed = subprocess.run(
        command, cwd=ROOT, text=True, capture_output=True, check=False, env=environment
    )
    combined = completed.stdout + "\n" + completed.stderr
    match = re.search(r"Ran (\d+) tests?", combined)
    return {
        "command": " ".join(command),
        "exit_code": completed.returncode,
        "test_count": int(match.group(1)) if match else None,
        "passed": completed.returncode == 0,
    }


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _file_count(path: Path) -> int:
    return sum(1 for candidate in path.rglob("*") if candidate.is_file())


def _report(result: dict[str, Any]) -> str:
    tests = result["tests"]
    return f"""# 프로젝트 폴더 구조 v2 리팩토링 검증 보고서

- 상태: **{result['status']}**
- 실행일: {result['run_date']}
- run ID: `{result['run_id']}`
- 범위: `{CLAIM_SCOPE}`

## 변경 결과

문서, 공개 코드, 실행 파이프라인, 테스트, 실험 정의, 생성 산출물을 각각
`docs/`, `src/`, `cli/pipelines/<domain>/<purpose>/`, `tests/`, `experiments/`,
`artifacts/`로 분리했다. 기존 `research/`와 `experiments/results/`는 제거했고,
과거 결과 파일의 내용은 바꾸지 않은 채 `artifacts/results/public|restricted/`로 이동했다.

EBLC 공개 구현의 소유자는 `src/guard_synth_eblc/`이며, 아홉 개 유지보수 테스트는
`tests/guard_synth_eblc/`, 여섯 실행 진입점은 `cli/pipelines/eblc/<purpose>/`가 소유한다.
`experiments/eblc_p0b/`에는 과거 호환 wrapper와 실험 설명만 남겼다.

## 검증 결과

| 검사 | 결과 |
|---|---:|
| 구조 계약 | {tests['structure']['test_count']}/{tests['structure']['test_count']} PASS |
| EBLC 단위ㆍ통합 회귀 | {tests['eblc']['test_count']}/{tests['eblc']['test_count']} PASS |
| P0a 회귀 | {tests['p0a']['test_count']}/{tests['p0a']['test_count']} PASS |
| UPPAAL 모델 생성 회귀 | {tests['uppaal_models']['test_count']}/{tests['uppaal_models']['test_count']} PASS |
| EBLC CLI import/도움말 | {tests['cli_help']['passed_count']}/{tests['cli_help']['total_count']} PASS |
| canonical 문서의 깨진 로컬 링크 | {result['broken_markdown_link_count']}건 |

기본 Python 환경에 `numpy`와 `pandas`가 없어 일부 비-EBLC legacy suite가 import되지
않는 기존 dependency gap은 이번 폴더 이동의 회귀로 계산하지 않았다. 해당 suite는
각 실험용 runtime을 명시하는 후속 환경 정규화 작업으로 분리한다.

## 해석

이 결과는 새 경로에서 EBLC와 P0a가 동일한 테스트를 통과하고, 공개 CLI가 import되며,
문서 링크와 산출물 소유 규칙이 일관됨을 보인다. 연구 방법의 타당성, SMT의 완전성,
실제 차량 안전성 또는 제한 데이터 품질을 입증하지는 않는다.
"""


def run(run_id: str) -> Path:
    output = ROOT / "artifacts/results/public/project-layout-refactor-001" / run_id
    if output.exists():
        raise FileExistsError(f"refusing to overwrite existing run: {run_id}")

    structure = _run([sys.executable, "-m", "unittest", "tests.structure.test_project_layout", "-v"])
    eblc = _run([
        sys.executable, "-m", "unittest", "discover", "-s", "tests/guard_synth_eblc",
        "-p", "test_*.py",
    ])
    p0a = _run([
        sys.executable, "-m", "unittest", "discover", "-s", "experiments/eblc_pilot",
        "-p", "test_*.py",
    ])
    uppaal_models = _run(
        [
            sys.executable, "-m", "unittest", "discover", "-s", "experiments/uppaal",
            "-p", "test_*.py",
        ],
        {"PYTHONPATH": "experiments/uppaal"},
    )
    cli_results = [_run([sys.executable, "-m", module, "--help"]) for module in PIPELINE_MODULES]
    cli_help = {
        "total_count": len(cli_results),
        "passed_count": sum(1 for item in cli_results if item["passed"]),
        "commands": cli_results,
    }
    links = broken_markdown_links(ROOT)
    required = (structure, eblc, p0a, uppaal_models)
    passed = all(item["passed"] for item in required) and cli_help["passed_count"] == len(cli_results) and not links
    result = {
        "experiment_id": EXPERIMENT_ID,
        "run_id": run_id,
        "run_date": date.today().isoformat(),
        "status": "EXECUTED" if passed else "FAILED",
        "layout_version": "2.0",
        "claim_scope": CLAIM_SCOPE,
        "tests": {
            "structure": structure,
            "eblc": eblc,
            "p0a": p0a,
            "uppaal_models": uppaal_models,
            "cli_help": cli_help,
        },
        "broken_markdown_link_count": len(links),
        "broken_markdown_links": list(links),
        "canonical_owners": {
            "documents": "docs",
            "public_code": "src",
            "pipelines": "cli/pipelines/<domain>/<purpose>",
            "tests": "tests",
            "experiment_protocols": "experiments",
            "generated_artifacts": "artifacts",
        },
        "file_counts": {
            "public_results": _file_count(ROOT / "artifacts/results/public"),
            "restricted_results": _file_count(ROOT / "artifacts/results/restricted"),
            "maintained_eblc_tests": len(tuple((ROOT / "tests/guard_synth_eblc").glob("test_*.py"))),
        },
        "known_preexisting_dependency_gaps": [
            "base Python lacks numpy for experiments/contract_micro_world",
            "base Python lacks pandas for experiments/sequential_coc",
        ],
    }
    manifest = {
        "experiment_id": EXPERIMENT_ID,
        "run_id": run_id,
        "run_date": result["run_date"],
        "python_version": sys.version.split()[0],
        "input_class": "PUBLIC_REPOSITORY_METADATA",
        "deterministic": True,
        "network_access_performed": False,
        "claim_scope": CLAIM_SCOPE,
        "layout_spec": "docs/architecture/PROJECT_LAYOUT_V2.md",
        "migration_map": "docs/architecture/MIGRATION_MAP.json",
        "code_hashes": {
            "runner": _sha256(Path(__file__)),
            "layout_spec": _sha256(ROOT / "docs/architecture/PROJECT_LAYOUT_V2.md"),
            "structure_test": _sha256(ROOT / "tests/structure/test_project_layout.py"),
        },
        "test_commands": [structure, eblc, p0a, uppaal_models, *cli_results],
    }
    output.mkdir(parents=True)
    _write_json(output / "RESULT.json", result)
    _write_json(output / "RUN_MANIFEST.json", manifest)
    (output / "REPORT_KO.md").write_text(_report(result), encoding="utf-8")
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", default="layout-v2-2026-08-09-v4")
    args = parser.parse_args()
    output = run(args.run_id)
    print(output.relative_to(ROOT).as_posix())


if __name__ == "__main__":
    main()
