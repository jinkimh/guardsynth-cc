"""CoC/CNL supervision boundary; machine checks are not independent gold.

This module does not infer action labels, source geometry, or human approval.
Its bounded compiler check is explicitly narrower than paper-cohort eligibility.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any

from guard_synth_eblc.bundle_elaborator import elaborate_bundle
from guard_synth_eblc.cnl_renderer import render_bundle
from guard_synth_eblc.composition import EBLCBundle
from guard_synth_eblc.indexed_collection import expand_indexed_collection
from guard_synth_eblc.smt_compiler import check_queries, compile_core_model, solve_assignment

from .source_aware_generator import SourceAwareGenerationResult


PROTOCOL_VERSION = "v2.3-cnl-supervision"
ARMS = ("L0", "L1", "L2", "L3")


def digest_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def digest_json(value: Any) -> str:
    return digest_text(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")))


def digest_file(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


@dataclass(frozen=True)
class ConstraintSupervision:
    arm: str
    text: str
    provenance: dict[str, Any]


def direct_nl(text: str, *, source_refs: tuple[str, ...], provider: str) -> ConstraintSupervision:
    """Accept a real provider's result, not an automatically invented baseline."""
    if not text.strip() or not source_refs or not provider.strip():
        raise ValueError("direct NL requires content, sources and provider")
    return ConstraintSupervision("L1", text, {
        "provider": provider, "source_refs": list(source_refs),
        "text_sha256": digest_text(text), "semantic_verification": "BYPASSED",
        "independent_semantic_audit": "PENDING",
    })


def candidate_cnl(bundle: EBLCBundle) -> ConstraintSupervision:
    """L2 uses the same renderer but never calls the semantic compiler/solver.

    Structural parsing occurs upstream. Parse failures remain upstream abstentions;
    a parseable candidate is not silently repaired or filtered by this function.
    """
    document = render_bundle(bundle)
    return ConstraintSupervision("L2", document.text, {
        **document.mapping_record(), "text_sha256": document.output_sha256,
        "semantic_verification": "BYPASSED", "independent_semantic_audit": "PENDING",
    })


def checked_cnl(generated: SourceAwareGenerationResult) -> ConstraintSupervision:
    """L3 machine path: source gate → expansion → Core/SMT → identical CNL.

    Satisfiability and supported queries do not certify real-scene safety, input
    truth, or CNL human fidelity. Those gates remain independently PENDING.
    """
    if generated.verdict != "VALIDATED" or generated.collection is None:
        raise ValueError("source generation did not validate; retain as abstention")
    expansion = expand_indexed_collection(generated.collection)
    if expansion.verdict != "VALIDATED" or expansion.bundle is None:
        raise ValueError("candidate collection did not expand")
    compiled = compile_core_model(elaborate_bundle(expansion.bundle).core_model)
    satisfiable = solve_assignment(compiled, {})["status"]
    checks = check_queries(compiled)
    if satisfiable != "SAT" or not checks["query_count"] or checks["matches_expected"] != checks["query_count"]:
        raise ValueError("bounded consistency/query check failed; retain as abstention")
    document = render_bundle(expansion.bundle)
    return ConstraintSupervision("L3", document.text, {
        **document.mapping_record(), "text_sha256": document.output_sha256,
        "request_id": generated.request_id,
        "generation_map_sha256": digest_json(generated.generation_map),
        "collection_sha256": digest_json(generated.collection.raw),
        "semantic_verification": "SOURCE_GATE_AND_BOUNDED_COMPILER_QUERIES",
        "base_satisfiability": satisfiable,
        "queries": [{k: item[k] for k in ("query_id", "expected", "status")}
                    for item in checks["results"]],
        "compiler_version": checks["compiler_version"], "z3_version": checks["z3_version"],
        "independent_semantic_audit": "PENDING", "paper_cohort_eligibility": "NOT_EVALUATED",
    })


def build_example(
    *, scene_id: str, group_id: str, split: str, image: Path, image_sha256: str,
    coc: str, coc_source_ref: str, choices: dict[str, str], action: str,
    action_source_ref: str, arm: str, constraint: ConstraintSupervision | None = None,
) -> dict[str, Any]:
    """Build teacher-forced supervision, never a gold-conditioned user prompt."""
    if split not in {"train", "dev", "software_smoke"}:
        raise ValueError("test examples must not be constructed as training supervision")
    if arm not in ARMS or (arm == "L0") != (constraint is None):
        raise ValueError("arm/constraint mismatch")
    if constraint is not None and constraint.arm != arm:
        raise ValueError("constraint belongs to a different arm")
    if not all((scene_id, group_id, coc.strip(), coc_source_ref, action_source_ref)):
        raise ValueError("missing example identity or supervision provenance")
    if len(choices) < 2 or action not in choices or any(not k.strip() or not v.strip() for k, v in choices.items()):
        raise ValueError("action must belong to at least two nonempty choices")
    if digest_file(image) != image_sha256:
        raise ValueError("visual input hash mismatch")
    if constraint and digest_text(constraint.text) != constraint.provenance["text_sha256"]:
        raise ValueError("constraint content hash mismatch")
    prompt = (
        "Inspect the image. Explain the driving situation and relevant constraints, "
        "then select one action. End with ACTION: followed by its key.\n"
        + "\n".join(f"{key}: {value}" for key, value in choices.items())
    )
    target = f"COC:\n{coc}\n"
    if constraint is not None:
        target += f"CONSTRAINTS:\n{constraint.text.rstrip()}\n"
    target += f"ACTION: {action}"
    common = {
        "scene_id": scene_id, "group_id": group_id, "split": split,
        "image": str(image), "image_sha256": image_sha256,
        "coc_sha256": digest_text(coc), "coc_source_ref": coc_source_ref,
        "choices": choices, "action": action, "action_source_ref": action_source_ref,
    }
    return {
        **common, "protocol_version": PROTOCOL_VERSION, "arm": arm,
        "common_example_sha256": digest_json(common),
        "input": {"image": str(image), "text": prompt}, "target": target,
        "target_sha256": digest_text(target),
        "constraint_provenance": None if constraint is None else constraint.provenance,
        "loss_policy": "ASSISTANT_ONLY_ALL_TARGET_TOKENS_EQUAL_WEIGHT",
        "effect_evaluation": "NOT_EVALUATED",
    }


def audit_matched_examples(examples: list[dict[str, Any]]) -> dict[str, int]:
    """No clip leakage, duplicate arms or silent unmatched-coverage comparison."""
    groups: dict[str, str] = {}
    scenes: dict[str, dict[str, str]] = {}
    images: dict[str, str] = {}
    for example in examples:
        group, split = example["group_id"], example["split"]
        if groups.setdefault(group, split) != split:
            raise ValueError("group crosses splits")
        if images.setdefault(example["image_sha256"], split) != split:
            raise ValueError("identical visual input crosses splits")
        arms = scenes.setdefault(example["scene_id"], {})
        if example["arm"] in arms:
            raise ValueError("duplicate scene/arm")
        arms[example["arm"]] = example["common_example_sha256"]
    for arms in scenes.values():
        if set(arms) != set(ARMS) or len(set(arms.values())) != 1:
            raise ValueError("unmatched base scene/CoC/action or missing arm")
    return {"base_scene_count": len(scenes), "example_count": len(examples), "group_count": len(groups)}
