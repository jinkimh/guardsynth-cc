"""Reproduce curated patent examples and build the supplementary delivery package.

Owner: safety-constrained-coc. No model training or inference is performed.
Requires NumPy, Pillow, python-docx, and XeLaTeX; reuse disclosure font setup.
"""

from dataclasses import asdict
import hashlib
import importlib.util
import json
from pathlib import Path
import platform
import sys
import zipfile

import numpy as np
import PIL

from build_coc_disclosure import blocks, docx_document, pdf_document


ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parents[1]
REPO = PROJECT.parents[1]
WORLD = PROJECT / "experiments/vlm_guard_learning"
STEM = "coc_generation_usage_supplement_v01"
SOURCE = ROOT / "COC_GENERATION_USAGE_SUPPLEMENT_V01.md"


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_world(name):
    spec = importlib.util.spec_from_file_location(name, WORLD / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def reproduce_examples():
    temporal = load_world("temporal_guard_world")
    maneuver = load_world("maneuver_guard_world")
    time_pair = [e for e in temporal.generate_temporal_examples(4, 42, "train")
                 if e.scene.scene_id == 2]
    lane_pair = [e for e in maneuver.generate_maneuver_examples(4, 42, "train")
                 if e.scene.scene_id == 1]
    assert [e.target for e in time_pair] == ["B", "C"]
    assert [e.target for e in lane_pair] == ["A", "B"]
    assert time_pair[0].scene.clear_time == 3.0
    assert [e.required_clear_duration for e in time_pair] == [0.5, 1.5]
    assert [e.min_gap for e in lane_pair] == [5.2, 9.0]
    assert [(c.label, c.entry_time, c.progress) for c in time_pair[0].scene.candidates] == [
        ("A", 2.5, 110.0), ("B", 3.5, 100.0), ("C", 4.5, 85.0), ("D", None, 0.0)]
    assert [(c.label, c.min_gap_m, c.progress) for c in lane_pair[0].scene.candidates] == [
        ("D", 2.0, 110.0), ("A", 5.7, 100.0), ("B", 12.3, 85.0), ("C", None, 0.0)]
    records = []
    for task, pair, module, mode in [
        ("temporal", time_pair, temporal, "RICH_COC"),
        ("lane_change", lane_pair, maneuver, "INLINE_CONSTRAINT"),
    ]:
        assert pair[0].scene == pair[1].scene
        render = module.render_storyboard if task == "temporal" else module.render_scene
        images = [render(e.scene) for e in pair]
        assert images[0].tobytes() == images[1].tobytes()
        for example in pair:
            verdicts = []
            for candidate in sorted(example.scene.candidates, key=lambda c: c.label):
                if task == "temporal":
                    valid = module.candidate_admissible(candidate, example)
                    complete = candidate.entry_time is not None
                else:
                    valid = module.admissible(candidate, example)
                    complete = candidate.goal_complete
                verdicts.append({"label": candidate.label, "guard_nonviolating": valid,
                                 "goal_complete": complete, "jointly_satisfying": valid and complete,
                                 "progress_m": candidate.progress})
            joint_target = max((v for v in verdicts if v["jointly_satisfying"]),
                               key=lambda v: v["progress_m"])["label"]
            assert joint_target == example.target
            records.append({
                "task": task, "generation": {"num_scenes": 4, "seed": 42, "split": "train"},
                "mode": mode, "example": asdict(example),
                "prompt": module.prompt_for(example, mode),
                "assistant_target": example.target, "candidate_verdicts": verdicts,
                "image_size": list(images[0].size),
                "image_rgb_sha256": hashlib.sha256(images[0].convert("RGB").tobytes()).hexdigest(),
                "joint_goal_guard_target": joint_target,
            })
    source_paths = [WORLD / f for f in ["temporal_guard_world.py", "maneuver_guard_world.py",
                                      "train_qwen_temporal_guard_lora.py"]]
    source_paths += [Path(__file__).resolve(), SOURCE]
    payload = {
        "project_id": "safety-constrained-coc", "version": "V01",
        "execution_scope": "Synthetic scene, prompt and oracle-label generation only; no model inference or training.",
        "environment": {"python": platform.python_version(), "numpy": np.__version__, "pillow": PIL.__version__},
        "source_sha256": {str(p.relative_to(REPO)): sha256(p) for p in source_paths},
        "records": records,
    }
    path = ROOT / "coc_generation_usage_examples_v01.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Verified fixed-scene pairs: temporal B/C; lane-change A/B; four joint targets agree.")
    return path


def build_package(examples_path):
    paper = PROJECT / "paper/manuscript/latex-kiee-review-2022/main.pdf"
    attachments = {
        "coc_invention_disclosure_v02.pdf": ROOT / "coc_invention_disclosure_v02.pdf",
        "coc_invention_disclosure_v02.docx": ROOT / "coc_invention_disclosure_v02.docx",
        STEM + ".pdf": ROOT / (STEM + ".pdf"),
        STEM + ".docx": ROOT / (STEM + ".docx"),
        examples_path.name: examples_path,
        "safety_constrained_coc_paper.pdf": paper,
        "COC_SUPPLEMENT_REPLY_DRAFT_V01.md": ROOT / "COC_SUPPLEMENT_REPLY_DRAFT_V01.md",
    }
    index = "# CoC 명세서 작성 보완자료 V01\n\nproject_id: safety-constrained-coc\n\n"
    index += "발명내용설명서 V02 PDF/DOCX, 보완자료 PDF/DOCX, 수치 확인용 JSON, 기반 논문 PDF, 회신 초안입니다.\n"
    index += "발명내용설명서는 전체 발명 구성·도면·예비 청구항을, 보완자료는 생성·활용 실시예를 설명합니다.\n"
    index += "JSON의 정답은 규칙 기반 산출값이며 새 모델 추론 결과가 아닙니다.\n"
    index += "공개 참고 문헌의 공식 링크는 보완자료 9절에 있습니다.\n\n"
    index += "## 첨부 파일 SHA-256\n\n"
    for name, path in attachments.items():
        index += f"- {name}: `{sha256(path)}`\n"
    package = ROOT / "coc_patent_supplement_v01.zip"
    with zipfile.ZipFile(package, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("README.md", index)
        for name, path in attachments.items():
            archive.write(path, name)
    with zipfile.ZipFile(package) as archive:
        assert archive.testzip() is None
        for name, path in attachments.items():
            assert archive.read(name) == path.read_bytes()
    print("Created and checked", package.name)


if __name__ == "__main__":
    examples = reproduce_examples()
    content = list(blocks(SOURCE))
    docx_document(content, STEM, "CoC 생성·활용 보완자료", "V01")
    pdf_document(content, STEM, "CoC 생성·활용 보완자료", "V01")
    build_package(examples)
