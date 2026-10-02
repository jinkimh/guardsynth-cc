"""Execute the locked 24-case M14 front-end software matrix."""

from __future__ import annotations

import argparse
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

from cli.solver_runtime import configure_project_z3

Z3_RUNTIME = configure_project_z3(ROOT)

from guard_synth.frontend_matrix import evaluate_locked_frontend_matrix
from guard_synth.source_catalog import load_source_catalog
from guard_synth_eblc.schema_validation import load_json


EXPERIMENT_ID = "GUARDSYNTH-COC-FRONTEND-MATRIX-001"
DEFAULT_MODEL = ROOT / "projects/04-guardsynth-coc/src/guard_synth/fixtures/simulated_assurance_profile_v0_1.json"
DEFAULT_BASE = ROOT / "projects/04-guardsynth-coc/src/guard_synth/fixtures/source_aware_generation_request_p0b_v0_1.json"


def _write(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def execute(
    *,
    catalog_path: Path,
    model_path: Path,
    base_request_path: Path,
    output_dir: Path,
) -> dict[str, Any]:
    inputs = (catalog_path, model_path, base_request_path)
    if any(not path.is_file() for path in inputs):
        raise FileNotFoundError("matrix input is missing")
    if output_dir.exists():
        raise FileExistsError(f"refusing to overwrite existing output: {output_dir}")
    matrix = evaluate_locked_frontend_matrix(
        catalog=load_source_catalog(catalog_path),
        model_source=model_path,
        base_request=load_json(base_request_path),
    )
    output_dir.mkdir(parents=True)
    _write(output_dir / "MATRIX_RESULTS.json", matrix)
    rates = {
        "schema_parse": matrix["schema_parse_count"] / matrix["case_count"],
        "expected_verdict": matrix["expected_verdict_matches"] / matrix["case_count"],
        "compiler_on_supported_proposals": (
            matrix["compiler_success_count"] / matrix["compiler_attempt_count"]
            if matrix["compiler_attempt_count"] else 0.0
        ),
    }
    result = {
        "status": "EXECUTED",
        "case_count": matrix["case_count"],
        "slice_count": 3,
        "rates": rates,
        "claim_promotions": matrix["claim_promotions"],
        "coc_text_outputs": matrix["coc_text_outputs"],
        "operational_policy_coverage": {
            "supported_primary_rules": matrix["supported_operational_policy_rule_count"],
            "primary_rules": matrix["primary_rule_count"],
            "complete": (
                matrix["supported_operational_policy_rule_count"]
                == matrix["primary_rule_count"]
            ),
        },
        "software_gate_passed": (
            rates["schema_parse"] == 1.0
            and rates["expected_verdict"] == 1.0
            and rates["compiler_on_supported_proposals"] == 1.0
            and matrix["claim_promotions"] == 0
            and matrix["coc_text_outputs"] == 0
        ),
        "empirical_scene_accuracy_evaluated": False,
        "actual_vehicle_validated": False,
        "claim_scope": (
            "LOCKED_SYNTHETIC_FRONTEND_PROTOCOL_AND_SUPPORTED_COMPILER_PATH_"
            "NOT_NLP_ACCURACY_LEGAL_DECISION_OR_VEHICLE_SAFETY"
        ),
    }
    _write(output_dir / "RESULT.json", result)
    _write(output_dir / "RUN_MANIFEST.json", {
        "experiment_id": EXPERIMENT_ID,
        "run_id": output_dir.name,
        "run_date": date.today().isoformat(),
        "input_class": "PUBLIC_SYNTHETIC",
        "deterministic": True,
        "z3_runtime": Z3_RUNTIME.manifest(),
        "input_hashes": {path.name: _sha256(path) for path in inputs},
        "code_hash": _sha256(ROOT / "projects/04-guardsynth-coc/src/guard_synth/frontend_matrix.py"),
        "claim_scope": result["claim_scope"],
    })
    (output_dir / "REPORT_KO.md").write_text(
        f"""# M14 CoC-conditioned front-end locked matrix

- 상태: **{result['status']}**
- software gate: **{'PASS' if result['software_gate_passed'] else 'FAIL'}**
- locked synthetic cases: **{result['case_count']}개 / 3 slices**
- schema parse: **{rates['schema_parse']:.1%}**
- expected primary verdict: **{rates['expected_verdict']:.1%}**
- 지원된 proposal의 EBLC/Core/Z3 compile: **{rates['compiler_on_supported_proposals']:.1%}**
- CoC authority 승격: **{result['claim_promotions']}건**
- 공개 출력의 CoC 원문: **{result['coc_text_outputs']}건**
- 실행 policy가 연결된 primary rule: **{matrix['supported_operational_policy_rule_count']}/{matrix['primary_rule_count']}**

이 matrix는 세 slice의 정상·동의표현/순서변경·누락·UNKNOWN·CONFLICT·FALSE·CLAIMED·
모호 binding 경계를 검사한다. 실제 24장면 표본, 일반 NLP 정확도 또는 법률 판단을 평가한
것은 아니다. 현재 실행 policy materialization은 횡단보도 규칙 1개만 지원하며, 다른
proposal은 임의 수치 없이 `NO_OPERATIONAL_POLICY_BINDING_FOR_PROPOSAL`로 남는다.
""",
        encoding="utf-8",
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, required=True)
    parser.add_argument("--model", type=Path, default=DEFAULT_MODEL)
    parser.add_argument("--base-request", type=Path, default=DEFAULT_BASE)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    result = execute(
        catalog_path=args.catalog,
        model_path=args.model,
        base_request_path=args.base_request,
        output_dir=args.output_dir,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result["software_gate_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
