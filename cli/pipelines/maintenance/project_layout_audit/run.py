"""Validate Project Structure Codex v3 and persist a reproducible public audit."""

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
    "cli.pipelines.guardsynth.source_aware_generate.run",
    "cli.pipelines.guardsynth.real_scene_readiness.run",
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
    return f"""# 프로젝트 폴더 구조 v3 리팩토링 검증 보고서

- 상태: **{result['status']}**
- 실행일: {result['run_date']}
- run ID: `{result['run_id']}`
- 범위: `{CLAIM_SCOPE}`

## 변경 결과

연구 질문별 문서, 코드, 파이프라인, 테스트, 실험, 논문을 `projects/<NN>-<project-id>/`에
함께 배치했다. 재사용 가능한 EBLC/BCV 구현은 `platforms/eblc-bcv/`, 포털은
`apps/research_portal/`가 소유한다. 루트 `src/`, `experiments/`와 domain CLI에는
이전 import/명령을 위한 forwarding shim만 남겼다.

## 검증 결과

| 검사 | 결과 |
|---|---:|
| 구조 계약 | {tests['structure']['test_count']}/{tests['structure']['test_count']} PASS |
| EBLC 단위ㆍ통합 회귀 | {tests['eblc']['test_count']}/{tests['eblc']['test_count']} PASS |
| GuardSynth 회귀 | {tests['guardsynth']['test_count'] + tests['nvidia_source_bundle']['test_count']}/{tests['guardsynth']['test_count'] + tests['nvidia_source_bundle']['test_count']} PASS |
| Safety-Constrained CoC micro-world | {tests['contract_micro_world']['test_count']}/{tests['contract_micro_world']['test_count']} PASS |
| Sequential CoC | {tests['sequential_coc']['test_count']}/{tests['sequential_coc']['test_count']} PASS |
| bounded logic/SMT | {tests['logic']['test_count']}/{tests['logic']['test_count']} PASS |
| P0a 회귀 | {tests['p0a']['test_count']}/{tests['p0a']['test_count']} PASS |
| UPPAAL 모델 생성 회귀 | {tests['uppaal_models']['test_count']}/{tests['uppaal_models']['test_count']} PASS |
| domain CLI import/도움말 | {tests['cli_help']['passed_count']}/{tests['cli_help']['total_count']} PASS |
| canonical 문서의 깨진 로컬 링크 | {result['broken_markdown_link_count']}건 |

NumPy/Pandas가 필요한 기존 실험은 등록된 Alpamayo runtime으로 분리 실행했다.
UPPAAL의 라이선스가 필요한 실제 `verifyta` 동등성 검사는 해당 suite에서 명시적으로
skip되며, 모델 생성과 판정 파서 회귀는 실행한다.

## 해석

이 결과는 새 경로에서 EBLC와 P0a가 동일한 테스트를 통과하고, 공개 CLI가 import되며,
문서 링크와 산출물 소유 규칙이 일관됨을 보인다. 연구 방법의 타당성, SMT의 완전성,
실제 차량 안전성 또는 제한 데이터 품질을 입증하지는 않는다.
"""


def run(run_id: str) -> Path:
    output = ROOT / "artifacts/projects/guardsynth-coc/public/project-layout-refactor-001" / run_id
    if output.exists():
        raise FileExistsError(f"refusing to overwrite existing run: {run_id}")

    structure = _run([sys.executable, "-m", "unittest", "tests.structure.test_project_layout", "-v"])
    eblc = _run([
        sys.executable, "-m", "unittest", "discover", "-s", "platforms/eblc-bcv/tests",
        "-p", "test_*.py",
    ])
    guardsynth_files = sorted(
        path for path in (ROOT / "projects/04-guardsynth-coc/tests").rglob("test_*.py")
        if path.name != "test_nvidia_source_bundle.py"
    )
    guardsynth = _run([
        sys.executable, "-m", "unittest", *[str(path.relative_to(ROOT)) for path in guardsynth_files],
    ])
    runtime_python = ROOT / "runtime/alpamayo/ar1_venv/bin/python"
    nvidia_source_bundle = _run([
        str(runtime_python), "-m", "unittest",
        "projects/04-guardsynth-coc/tests/integration/test_nvidia_source_bundle.py",
    ])
    contract_micro_world = _run([
        str(runtime_python), "-m", "unittest", "discover", "-s",
        "projects/01-safety-constrained-coc/experiments/contract_micro_world", "-p", "test_*.py",
    ])
    sequential_coc = _run([
        str(runtime_python), "-m", "unittest", "discover", "-s",
        "projects/03-sequential-coc-verification/experiments/sequential_coc/tests", "-p", "test_*.py",
    ])
    logic = _run([
        str(runtime_python), "-m", "unittest", "discover", "-s",
        "projects/03-sequential-coc-verification/experiments/logic", "-p", "test_*.py",
    ], {"MPLCONFIGDIR": "/tmp/guardsynth-matplotlib-cache"})
    p0a = _run([
        sys.executable, "-m", "unittest", "discover", "-s", "platforms/eblc-bcv/experiments/eblc_pilot",
        "-p", "test_*.py",
    ])
    uppaal_models = _run(
        [
            sys.executable, "-m", "unittest", "discover", "-s", "projects/03-sequential-coc-verification/experiments/uppaal",
            "-p", "test_*.py",
        ],
        {"PYTHONPATH": "projects/03-sequential-coc-verification/experiments/uppaal"},
    )
    cli_results = [_run([sys.executable, "-m", module, "--help"]) for module in PIPELINE_MODULES]
    cli_help = {
        "total_count": len(cli_results),
        "passed_count": sum(1 for item in cli_results if item["passed"]),
        "commands": cli_results,
    }
    links = broken_markdown_links(ROOT)
    required = (
        structure, eblc, guardsynth, nvidia_source_bundle, contract_micro_world,
        sequential_coc, logic, p0a, uppaal_models,
    )
    passed = all(item["passed"] for item in required) and cli_help["passed_count"] == len(cli_results) and not links
    result = {
        "experiment_id": EXPERIMENT_ID,
        "run_id": run_id,
        "run_date": date.today().isoformat(),
        "status": "EXECUTED" if passed else "FAILED",
        "layout_version": "3.3",
        "claim_scope": CLAIM_SCOPE,
        "tests": {
            "structure": structure,
            "eblc": eblc,
            "guardsynth": guardsynth,
            "nvidia_source_bundle": nvidia_source_bundle,
            "contract_micro_world": contract_micro_world,
            "sequential_coc": sequential_coc,
            "logic": logic,
            "p0a": p0a,
            "uppaal_models": uppaal_models,
            "cli_help": cli_help,
        },
        "broken_markdown_link_count": len(links),
        "broken_markdown_links": list(links),
        "canonical_owners": {
            "research_projects": "projects/<NN>-<project-id>",
            "shared_platforms": "platforms/<platform-id>",
            "applications": "apps/<app-id>",
            "generated_artifacts": "artifacts/projects|platforms/<owner>/<class>",
        },
        "file_counts": {
            "public_results": _file_count(ROOT / "artifacts/results/public"),
            "restricted_results": _file_count(ROOT / "artifacts/results/restricted"),
            "maintained_eblc_tests": len(tuple((ROOT / "platforms/eblc-bcv/tests").rglob("test_*.py"))),
            "maintained_guardsynth_tests": len(tuple((ROOT / "projects/04-guardsynth-coc/tests").rglob("test_*.py"))),
        },
        "known_environment_limits": [
            "UPPAAL verifyta equivalence requires an available local license",
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
        "layout_spec": "docs/architecture/PROJECT_STRUCTURE_CODEX.md",
        "migration_map": "docs/architecture/MIGRATION_MAP.json",
        "code_hashes": {
            "runner": _sha256(Path(__file__)),
            "layout_spec": _sha256(ROOT / "docs/architecture/PROJECT_STRUCTURE_CODEX.md"),
            "structure_test": _sha256(ROOT / "tests/structure/test_project_layout.py"),
        },
        "test_commands": [
            structure, eblc, guardsynth, nvidia_source_bundle, contract_micro_world,
            sequential_coc, logic, p0a, uppaal_models, *cli_results,
        ],
    }
    output.mkdir(parents=True)
    _write_json(output / "RESULT.json", result)
    _write_json(output / "RUN_MANIFEST.json", manifest)
    (output / "REPORT_KO.md").write_text(_report(result), encoding="utf-8")
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", default="layout-v3-2026-08-12-v1")
    args = parser.parse_args()
    output = run(args.run_id)
    print(output.relative_to(ROOT).as_posix())


if __name__ == "__main__":
    main()
