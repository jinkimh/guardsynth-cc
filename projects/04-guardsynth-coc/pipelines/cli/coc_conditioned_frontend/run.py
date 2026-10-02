"""Generate a reviewable constraint proposal bundle from CoC and scene facts."""

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

from guard_synth.coc_conditioned_frontend import (
    build_constraint_proposals,
    parse_frontend_request,
)
from guard_synth.source_catalog import load_source_catalog
from guard_synth_eblc.schema_validation import load_json


EXPERIMENT_ID = "GUARDSYNTH-COC-FRONTEND-001"
DEFAULT_INPUT = ROOT / "projects/04-guardsynth-coc/src/guard_synth/fixtures/coc_frontend_request_crosswalk_v0_1.json"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def execute(input_path: Path, catalog_path: Path, output_dir: Path) -> dict[str, Any]:
    if output_dir.exists():
        raise FileExistsError(f"refusing to overwrite existing output: {output_dir}")
    request = parse_frontend_request(load_json(input_path))
    catalog = load_source_catalog(catalog_path)
    result = build_constraint_proposals(request, catalog)
    output_dir.mkdir(parents=True)
    _write(output_dir / "CONSTRAINT_PROPOSAL_BUNDLE.json", result)
    _write(output_dir / "RUN_MANIFEST.json", {
        "experiment_id": EXPERIMENT_ID,
        "run_id": output_dir.name,
        "run_date": date.today().isoformat(),
        "input_class": "PUBLIC_SYNTHETIC",
        "deterministic": True,
        "input_hashes": {
            "frontend_request": _sha256(input_path),
            "source_catalog": _sha256(catalog_path),
        },
        "code_hash": _sha256(ROOT / "projects/04-guardsynth-coc/src/guard_synth/coc_conditioned_frontend.py"),
        "coc_text_in_output": False,
        "claim_promoted_to_scene_or_legal_authority": False,
        "claim_scope": result["claim_scope"],
    })
    proposed = sum(item["verdict"] == "PROPOSED" for item in result["proposals"])
    unsupported = sum(item["verdict"] == "UNSUPPORTED" for item in result["proposals"])
    (output_dir / "REPORT_KO.md").write_text(
        f"""# GuardSynth CoC-conditioned front-end v0.1 pilot

- 상태: **{result['status']}**
- catalog 후보: **{len(result['proposals'])}개**
- 검토 제안: **{proposed}개**
- unsupported: **{unsupported}개**
- CoC 원문 출력: **아니오**
- CoC authority 승격: **아니오**

이 결과는 제한된 lexical parser와 구조화 장면 predicate를 사용한 공개 synthetic software
pilot이다. `PROPOSED`는 source-linked 검토 후보이며 최종 법률 적용, 실제 장면 정확도,
차량 assurance 또는 안전성을 뜻하지 않는다.
""",
        encoding="utf-8",
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--catalog", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    result = execute(args.input, args.catalog, args.output_dir)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result["status"] in {"PROPOSED", "REVIEW_REQUIRED"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
