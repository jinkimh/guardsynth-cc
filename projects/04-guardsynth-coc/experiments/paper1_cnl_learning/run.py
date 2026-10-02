"""Pinned local source audit and four-arm VLM software smoke, NOT E4-L efficacy."""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
import random
import re
import sys
import time

ROOT = next(p for p in Path(__file__).resolve().parents if (p / "PROJECT_REGISTRY.json").is_file())
sys.path[:0] = [str(ROOT), str(ROOT / "projects/04-guardsynth-coc/src"),
               str(ROOT / "platforms/eblc-bcv/src")]
from cli.solver_runtime import configure_project_z3
configure_project_z3(ROOT)
from guard_synth.cnl_training import (
    ARMS, PROTOCOL_VERSION, audit_matched_examples, build_example, candidate_cnl,
    checked_cnl, digest_file, digest_text, direct_nl,
)
from guard_synth.source_aware_generator import generate_from_request, load_generation_request
from guard_synth_eblc.indexed_collection import expand_indexed_collection

MODEL_ID = "Qwen/Qwen3-VL-2B-Instruct"
REVISION = "89644892e4d85e24eaac8bacfd4f463576704203"
MODEL_PATH = Path.home() / ".cache/huggingface/hub/models--Qwen--Qwen3-VL-2B-Instruct/snapshots" / REVISION
FIXTURE = ROOT / "projects/04-guardsynth-coc/src/guard_synth/fixtures/source_aware_generation_request_p0b_v0_1.json"
ACQUISITION = ROOT / "artifacts/projects/guardsynth-coc/restricted/guardsynth-m16-scene-acquisition-001"


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def source_audit(output):
    import pyarrow.parquet as pq
    reasoning = ROOT / "data/restricted/nvidia_physicalai/reasoning/ood_reasoning.parquet"
    shortlist = ACQUISITION / "m16-source-acquisition-2026-08-14-v18/SENSOR_MATERIALIZATION_SHORTLIST.json"
    reserve = shortlist.with_name("ATTRITION_RESERVE_COHORT.json")
    audit_path = ACQUISITION / "m16-cascade-structured-link-audit-2026-09-05-v1/CASCADE_STRUCTURED_LINK_AUDIT.json"
    table = pq.read_table(reasoning)
    event_index = {}
    missing_event_rows = 0
    for row in table.to_pylist():
        if row["events"] is None:
            missing_event_rows += 1
            continue
        for event in json.loads(row["events"]):
            key = (row["clip_id"], int(event["event_start_timestamp"]))
            event_index.setdefault(key, []).append((event.get("coc"), row["split"], row["feature"]))
    candidates = []
    for path, field in ((shortlist, "shortlist_slice"), (reserve, "reserve_slice")):
        for row in json.loads(path.read_text())["records"]:
            candidates.append({**row, "slice": row[field]})
    audit = {r["candidate_digest"]: r for r in json.loads(audit_path.read_text())["records"]}
    if len(candidates) != len({r["candidate_digest"] for r in candidates}):
        raise ValueError("duplicate candidate identity")
    records = []
    for row in candidates:
        matches = event_index.get((row["clip_id"], int(row["event_timestamp_us"])), [])
        linked = len(matches) == 1 and isinstance(matches[0][0], str) and bool(matches[0][0].strip())
        previous = audit[row["candidate_digest"]]
        records.append({
            "candidate_digest": row["candidate_digest"], "group_id": row["clip_id"],
            "event_timestamp_us": row["event_timestamp_us"], "slice": row["slice"],
            "selected_development_family": row["slice"] == "PEDESTRIAN_CYCLIST_YIELD",
            "exact_coc_link": linked, "coc_match_count": len(matches),
            "coc_sha256": digest_text(matches[0][0]) if linked else None,
            "upstream_split": matches[0][1] if linked else None,
            "human_observation_status": previous["human_observation_status"],
            "prior_source_field_status": previous["field_status"],
            "independent_test_admission": "NOT_ADMITTED_PRIOR_DEVELOPMENT_POOL",
            "paper_cohort_eligibility": "NOT_EVALUATED",
        })
    write_json(output / "source_audit.json", records)
    return {
        "status": "SOURCE_INVENTORY_COMPLETE_COHORT_NOT_FROZEN",
        "reasoning_clip_rows": table.num_rows, "reasoning_rows_without_events": missing_event_rows,
        "reasoning_event_count": sum(map(len, event_index.values())),
        "candidate_count": len(records), "slice_counts": dict(Counter(r["slice"] for r in records)),
        "exact_coc_link_count": sum(r["exact_coc_link"] for r in records),
        "selected_development_candidate_count": sum(r["selected_development_family"] for r in records),
        "selected_development_coc_link_count": sum(r["selected_development_family"] and r["exact_coc_link"] for r in records),
        "input_hashes": {str(p.relative_to(ROOT)): digest_file(p) for p in (reasoning, shortlist, reserve, audit_path)},
        "paper_cohort_eligibility": "NOT_EVALUATED", "learning_effect": "NOT_EVALUATED",
        "blockers": ["TASK_SOURCE_CLAUSE_AND_ACTION_GOLD_CONTRACT", "INDEPENDENT_REVIEW_AND_CNL_AUDIT",
                     "FRESH_GROUP_SPLITS_AND_ENDPOINT_POWER", "REAL_DATA_L1_L2_L3_PROVIDERS"],
    }


def software_examples(output):
    from PIL import Image, ImageDraw
    # Deliberately artificial diagram, not a substitute for missing scene evidence.
    image_path = output / "software_fixture.png"
    im = Image.new("RGB", (224, 224), "white")
    draw = ImageDraw.Draw(im)
    draw.rectangle((65, 0, 155, 224), fill="gray")
    draw.rectangle((94, 154, 126, 205), fill="blue")
    draw.ellipse((100, 70, 119, 89), fill="red")
    draw.text((8, 8), "SOFTWARE FIXTURE", fill="black")
    im.save(image_path)
    request = load_generation_request(FIXTURE)
    generated = generate_from_request(request)
    bundle = expand_indexed_collection(generated.collection).bundle
    # Source-policy projection for this synthetic fixture only, not a real-data L1 provider.
    nl = "For the declared pedestrian-conflict fixture, the supplied action policy permits " + ", ".join(request.raw["policy"]["allowed_actions"]) + "."
    constraints = {
        "L0": None, "L1": direct_nl(nl, source_refs=tuple(request.raw["source_refs"]), provider="synthetic-policy-projection-v0.1"),
        "L2": candidate_cnl(bundle), "L3": checked_cnl(generated),
    }
    write_json(output / "source_request.json", request.raw)
    write_json(output / "eblc_bundle.json", bundle.raw)
    examples = [build_example(
        scene_id="software-fixture-001", group_id="software-fixture-001", split="software_smoke",
        image=image_path, image_sha256=digest_file(image_path),
        coc="Synthetic harness only: yield to the declared pedestrian conflict.",
        coc_source_ref="SOFTWARE_FIXTURE_NOT_DATASET_COC",
        choices={"STOP": "Stop before the conflict zone", "CREEP": "Move slowly", "PROCEED": "Continue forward"},
        action="STOP", action_source_ref="SOFTWARE_FIXTURE_NOT_HUMAN_ACTION_GOLD",
        arm=arm, constraint=constraints[arm],
    ) for arm in ARMS]
    audit_matched_examples(examples)
    write_json(output / "training_examples.json", examples)
    return examples


def encode(processor, example):
    from PIL import Image
    image = Image.open(example["input"]["image"]).convert("RGB")
    user = {"role": "user", "content": [{"type": "image", "image": image},
                                            {"type": "text", "text": example["input"]["text"]}]}
    prompt = processor.apply_chat_template([user], tokenize=True, add_generation_prompt=True,
                                           return_dict=True, return_tensors="pt")
    full = processor.apply_chat_template([user, {"role": "assistant", "content": [{"type": "text", "text": example["target"]}]}],
                                         tokenize=True, add_generation_prompt=False, return_dict=True, return_tensors="pt")
    n = prompt["input_ids"].shape[1]
    if not full["input_ids"][0, :n].equal(prompt["input_ids"][0]):
        raise ValueError("chat template prompt/target prefix mismatch")
    if full["input_ids"].shape[1] > 8192:
        raise ValueError("refusing silent CNL truncation")
    labels = full["input_ids"].clone(); labels[:, :n] = -100
    full["labels"] = labels
    if not (labels != -100).any() or full["pixel_values"].numel() == 0:
        raise ValueError("missing visual input or supervised tokens")
    return full, prompt


def train_smoke(args, output):
    import hashlib
    import numpy as np
    import torch
    import transformers
    import peft
    from peft import LoraConfig, TaskType, get_peft_model
    from transformers import AutoProcessor, Qwen3VLForConditionalGeneration
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA unavailable; run in the authorized GPU environment")
    device = torch.device(args.device)
    if device.type != "cuda" or device.index is None:
        raise ValueError("select an explicit cuda:N device")
    torch.cuda.set_device(device)
    free, _ = torch.cuda.mem_get_info(device)
    if free < 30 * 1024**3:
        raise RuntimeError("less than 30 GiB free; do not disturb other GPU jobs")
    examples = software_examples(output)
    processor = AutoProcessor.from_pretrained(args.model_path, local_files_only=True)
    model = Qwen3VLForConditionalGeneration.from_pretrained(
        args.model_path, local_files_only=True, dtype=torch.bfloat16, attn_implementation="sdpa",
    ).to(device)
    model.config.use_cache = False
    targets = [name for name, module in model.named_modules() if isinstance(module, torch.nn.Linear)
               and "language_model" in name and name.rsplit(".", 1)[-1] in {"q_proj", "k_proj", "v_proj", "o_proj"}]
    if not targets:
        raise RuntimeError("no internal VLM language attention modules")
    config = LoraConfig(r=8, lora_alpha=16, lora_dropout=0.0, bias="none",
                        task_type=TaskType.CAUSAL_LM, target_modules=targets)
    results = []
    for index, example in enumerate(examples):
        random.seed(args.seed); np.random.seed(args.seed); torch.manual_seed(args.seed); torch.cuda.manual_seed_all(args.seed)
        arm = example["arm"]
        adapter_name = arm.lower()
        if index == 0:
            model = get_peft_model(model, config, adapter_name=adapter_name)
            model.enable_input_require_grads()
        else:
            model.add_adapter(adapter_name, config)
        model.set_adapter(adapter_name)
        trainable = {name: parameter for name, parameter in model.named_parameters() if parameter.requires_grad}
        if not trainable or any("lora_" not in name or "language_model" not in name for name in trainable):
            raise RuntimeError("trainable modules escaped internal VLM LoRA scope")
        before = {name: p.detach().cpu().clone() for name, p in trainable.items()}
        # Ignore arm names in this digest to verify paired initialization exactly.
        initial_digest = hashlib.sha256(b"".join(p.float().numpy().tobytes() for p in before.values())).hexdigest()
        full, prompt = encode(processor, example)
        batch = {k: v.to(device) for k, v in full.items()}
        image_token_count = int((batch["input_ids"] == model.config.image_token_id).sum())
        if image_token_count == 0:
            raise RuntimeError("processor did not emit image tokens")
        optimizer = torch.optim.AdamW(trainable.values(), lr=2e-4, weight_decay=0.01)
        model.train(); optimizer.zero_grad(set_to_none=True)
        torch.cuda.reset_peak_memory_stats(device)
        started = time.monotonic()
        with torch.autocast("cuda", dtype=torch.bfloat16):
            loss = model(**batch, use_cache=False).loss
        if not torch.isfinite(loss):
            raise RuntimeError("nonfinite loss")
        loss.backward()
        gradient_norm = float(torch.nn.utils.clip_grad_norm_(list(trainable.values()), 1.0))
        if not np.isfinite(gradient_norm) or gradient_norm <= 0:
            raise RuntimeError("missing finite VLM gradient")
        optimizer.step(); torch.cuda.synchronize(device)
        seconds = time.monotonic() - started
        changes = {name: float((p.detach().cpu() - before[name]).abs().max()) for name, p in trainable.items()}
        if not any(v > 0 for v in changes.values()):
            raise RuntimeError("no VLM LoRA parameter changed")
        model.save_pretrained(output / "adapters", selected_adapters=[adapter_name])
        model.eval()
        visual_input = {k: v.to(device) for k, v in prompt.items()}
        with torch.no_grad(), torch.autocast("cuda", dtype=torch.bfloat16):
            logits = model(**visual_input, use_cache=False).logits[:, -1].float()
            changed_visual = dict(visual_input)
            changed_visual["pixel_values"] = torch.zeros_like(visual_input["pixel_values"])
            alternate = model(**changed_visual, use_cache=False).logits[:, -1].float()
            visual_delta = float((logits - alternate).abs().max())
        result = {
            "arm": arm, "seed": args.seed, "optimizer_steps": 1,
            "initial_adapter_sha256": initial_digest, "trainable_parameters": sum(p.numel() for p in trainable.values()),
            "changed_tensor_count": sum(v > 0 for v in changes.values()), "max_parameter_change": max(changes.values()),
            "gradient_norm_before_clip": gradient_norm, "training_loss": float(loss.detach()),
            "sequence_tokens": int(batch["input_ids"].numel()), "supervised_tokens": int((batch["labels"] != -100).sum()),
            "image_tokens": image_token_count, "pixel_values_shape": list(batch["pixel_values"].shape),
            "optimizer_step_seconds": seconds, "peak_allocated_bytes": torch.cuda.max_memory_allocated(device),
            "zero_pixel_diagnostic_max_logit_delta": visual_delta,
            "diagnostic_scope": "VISUAL_TENSOR_PATH_ONLY_NOT_SEMANTIC_GROUNDING",
            "held_out_action_evaluation": "NOT_EVALUATED",
        }
        results.append(result)
        write_json(output / f"{arm.lower()}_training.json", result)
        print(json.dumps(result), flush=True)
        del optimizer, before, batch, loss, logits, alternate, visual_input, changed_visual
        torch.cuda.empty_cache()
    if len({r["initial_adapter_sha256"] for r in results}) != 1:
        raise RuntimeError("arm initialization was not paired")
    processor.save_pretrained(output / "processor")
    return {
        "status": "FOUR_ARM_VLM_WEIGHT_UPDATE_SOFTWARE_SMOKE_COMPLETE", "arms": results,
        "torch": torch.__version__, "transformers": transformers.__version__, "peft": peft.__version__,
        "device_name": torch.cuda.get_device_name(device), "trainable_module_names": targets,
        "paired_initialization_verified": True, "matched_compute_claim": False,
        "learning_effect": "NOT_EVALUATED", "independent_gold": "NOT_PROVIDED",
        "source_request_sha256": digest_file(FIXTURE),
        "claim_scope": "SYNTHETIC_SOFTWARE_FIXTURE_NOT_REAL_SCENE_TRAINING_OR_PAPER_EFFECT",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("audit", "software-smoke"))
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--model-path", type=Path, default=MODEL_PATH)
    parser.add_argument("--device", default="cuda:1")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*-[0-9]+", args.run_id):
        parser.error("run-id must be kebab-case with a numeric suffix")
    output = ROOT / "artifacts/projects/guardsynth-coc/restricted/guardsynth-eblc-learning-001" / args.run_id
    output.mkdir(parents=True, exist_ok=False, mode=0o700)
    manifest = {
        "project_id": "guardsynth-coc", "experiment_id": "guardsynth-eblc-learning-001",
        "run_id": args.run_id, "mode": args.mode, "protocol_version": PROTOCOL_VERSION,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "model_id": MODEL_ID, "expected_model_revision": REVISION,
        "model_snapshot_path": str(args.model_path), "seed": args.seed, "device": args.device,
        "code_hashes": {str(p.relative_to(ROOT)): digest_file(p) for p in (
            Path(__file__).resolve(), ROOT / "projects/04-guardsynth-coc/src/guard_synth/cnl_training.py",
            ROOT / "platforms/eblc-bcv/src/guard_synth_eblc/cnl_renderer.py")},
        "model_file_hashes": {name: digest_file(args.model_path / name) for name in
                              ("config.json", "model.safetensors", "preprocessor_config.json", "chat_template.json")},
        "paper_effect_evaluation": "NOT_EVALUATED", "status": "RUNNING",
    }
    write_json(output / "RUN_MANIFEST.json", manifest)
    try:
        result = source_audit(output) if args.mode == "audit" else train_smoke(args, output)
    except Exception as exc:
        write_json(output / "RESULT.json", {"status": "FAILED", "error": f"{type(exc).__name__}: {exc}",
                                           "learning_effect": "NOT_EVALUATED"})
        manifest["status"] = "FAILED"; write_json(output / "RUN_MANIFEST.json", manifest)
        raise
    write_json(output / "RESULT.json", result)
    manifest["status"] = result["status"]
    manifest["output_hashes"] = {str(p.relative_to(output)): digest_file(p)
                                 for p in sorted(output.rglob("*")) if p.is_file() and p.name != "RUN_MANIFEST.json"}
    write_json(output / "RUN_MANIFEST.json", manifest)
    print(str(output), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
