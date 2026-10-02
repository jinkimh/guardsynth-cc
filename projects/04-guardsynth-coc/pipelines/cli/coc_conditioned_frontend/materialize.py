"""Materialize one supported CoC proposal through EBLC Core and bounded SMT."""

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

from guard_synth.coc_conditioned_frontend import (
    build_constraint_proposals,
    parse_frontend_request,
)
from guard_synth.frontend_materialization import materialize_simulated_proposal
from guard_synth.source_catalog import load_source_catalog
from guard_synth_eblc.bundle_elaborator import elaborate_bundle
from guard_synth_eblc.indexed_collection import expand_indexed_collection
from guard_synth_eblc.schema_validation import load_json
from guard_synth_eblc.smt_compiler import compile_core_model, export_compilation


EXPERIMENT_ID = "GUARDSYNTH-COC-FRONTEND-MATERIALIZATION-001"
DEFAULT_FRONTEND = ROOT / "projects/04-guardsynth-coc/src/guard_synth/fixtures/coc_frontend_request_crosswalk_v0_1.json"
DEFAULT_MATERIALIZATION = ROOT / (
    "projects/04-guardsynth-coc/src/guard_synth/fixtures/coc_frontend_materialization_crosswalk_v0_1.json"
)
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
    frontend_path: Path,
    materialization_path: Path,
    catalog_path: Path,
    model_path: Path,
    base_request_path: Path,
    output_dir: Path,
) -> dict[str, Any]:
    inputs = (
        frontend_path, materialization_path, catalog_path, model_path,
        base_request_path,
    )
    if any(not path.is_file() for path in inputs):
        raise FileNotFoundError("materialization input is missing")
    if output_dir.exists():
        raise FileExistsError(f"refusing to overwrite existing output: {output_dir}")

    frontend = build_constraint_proposals(
        parse_frontend_request(load_json(frontend_path)),
        load_source_catalog(catalog_path),
    )
    materialization = load_json(materialization_path)
    result = materialize_simulated_proposal(
        proposal_bundle=frontend,
        proposal_rule_id=materialization["proposal_rule_id"],
        scene_context=materialization["scene_context"],
        model_source=model_path,
        base_request=load_json(base_request_path),
        request_id=f"{frontend['request_id']}__materialized",
    )
    expansion = expand_indexed_collection(result.generated.collection)
    if expansion.bundle is None:
        raise RuntimeError(f"indexed expansion failed: {expansion.reason_codes}")
    elaborated = elaborate_bundle(expansion.bundle)
    compiled = compile_core_model(elaborated.core_model)

    output_dir.mkdir(parents=True)
    _write(output_dir / "CONSTRAINT_PROPOSAL_BUNDLE.json", frontend)
    _write(output_dir / "GUARDSYNTH_GENERATION_REQUEST.json", result.request.raw)
    _write(output_dir / "GENERATED_EBLC_PROGRAM.json", result.generated.program_template.raw)
    _write(output_dir / "GENERATED_INDEXED_COLLECTION.json", result.generated.collection.raw)
    _write(output_dir / "GENERATED_EBLC_BUNDLE.json", expansion.bundle.raw)
    _write(output_dir / "ELABORATED_CORE.json", elaborated.core_document)
    _write(output_dir / "ELABORATION_MAP.json", elaborated.elaboration_map)
    query_results = export_compilation(compiled, output_dir)

    mapping = {
        "proposal_rule_id": result.proposal_rule_id,
        "executable_system_requirement_rule_id": result.executable_system_requirement_rule_id,
        "legal_proposal_refs": list(result.legal_proposal_refs),
        "numeric_evidence_refs": list(result.numeric_evidence_refs),
        "legal_numeric_source_overlap": sorted(
            set(result.legal_proposal_refs).intersection(result.numeric_evidence_refs)
        ),
        "recorded_vehicle_binding_key": result.recorded_vehicle_binding_key,
        "simulation_vehicle_binding_key": result.simulation_vehicle_binding_key,
        "claim_scope": result.claim_scope,
    }
    _write(output_dir / "MATERIALIZATION_MAP.json", mapping)
    summary = {
        "status": "EXECUTED",
        "frontend_status": frontend["status"],
        "generation_verdict": result.generated.verdict,
        "indexed_expansion_verdict": expansion.verdict,
        "contract_count": len(result.generated.collection.instances),
        "core_model_id": elaborated.core_model.model_id,
        "bounded_smt_query_count": len(query_results["results"]),
        "bounded_smt_statuses": {
            item["query_id"]: item["status"] for item in query_results["results"]
        },
        "source_separation_gate": not mapping["legal_numeric_source_overlap"],
        "coc_text_in_output": False,
        "actual_vehicle_validated": False,
        "claim_scope": result.claim_scope,
    }
    _write(output_dir / "RESULT.json", summary)
    _write(output_dir / "RUN_MANIFEST.json", {
        "experiment_id": EXPERIMENT_ID,
        "run_id": output_dir.name,
        "run_date": date.today().isoformat(),
        "input_class": "PUBLIC_SYNTHETIC",
        "deterministic": True,
        "z3_runtime": {
            "version": Z3_RUNTIME.version,
            "prefix": str(Z3_RUNTIME.prefix),
        },
        "input_hashes": {path.name: _sha256(path) for path in inputs},
        "code_hashes": {
            "frontend": _sha256(ROOT / "projects/04-guardsynth-coc/src/guard_synth/coc_conditioned_frontend.py"),
            "materialization": _sha256(ROOT / "projects/04-guardsynth-coc/src/guard_synth/frontend_materialization.py"),
        },
        "claim_scope": result.claim_scope,
    })
    (output_dir / "REPORT_KO.md").write_text(
        f"""# GuardSynth CoC proposal → EBLC → Core/SMT pilot

- 상태: **{summary['status']}**
- front-end: **{summary['frontend_status']}**
- GuardSynth generation: **{summary['generation_verdict']}**
- 생성 계약: **{summary['contract_count']}개**
- bounded SMT query: **{summary['bounded_smt_query_count']}개**
- 법규 제안 근거와 수치 근거 중복: **{len(mapping['legal_numeric_source_overlap'])}개**
- 실제 차량 검증: **아니오**

CoC는 `CLAIMED` 단서이고 법규 source는 규칙 제안의 provenance다. 실행 수치는 별도의
simulation system requirement와 simulated assurance model에서 왔다. 이 공개 synthetic
pilot은 변환 경로와 source separation을 검사하며 법률 판단, 자연어 parser 정확도,
실제 장면 정확도 또는 실제 차량 안전성을 입증하지 않는다.
""",
        encoding="utf-8",
    )
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--frontend", type=Path, default=DEFAULT_FRONTEND)
    parser.add_argument("--materialization", type=Path, default=DEFAULT_MATERIALIZATION)
    parser.add_argument("--catalog", type=Path, required=True)
    parser.add_argument("--model", type=Path, default=DEFAULT_MODEL)
    parser.add_argument("--base-request", type=Path, default=DEFAULT_BASE)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    result = execute(
        frontend_path=args.frontend,
        materialization_path=args.materialization,
        catalog_path=args.catalog,
        model_path=args.model,
        base_request_path=args.base_request,
        output_dir=args.output_dir,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
