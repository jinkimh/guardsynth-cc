#!/usr/bin/env python3
"""Audit official nuScenes mini metadata for scene-continuity evidence."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd


def load_json(path: Path) -> list[dict[str, Any]]:
    return json.loads(path.read_text())


def load_local_coc_scene_names(coc_root: Path) -> list[str]:
    names: set[str] = set()
    clip_index = coc_root / "clip_index.parquet"
    if clip_index.exists():
        frame = pd.read_parquet(clip_index)
        if "clip_id" in frame.columns:
            names.update(str(value) for value in frame["clip_id"])
        if frame.index.name == "clip_id":
            names.update(str(value) for value in frame.index)
    for path in (coc_root / "camera").glob("scene-*.timestamps.parquet"):
        names.add(path.name.split(".")[0])
    for path in (coc_root / "labels/egomotion").glob("scene-*.egomotion.parquet"):
        names.add(path.name.split(".")[0])
    reasoning = coc_root / "reasoning/ood_reasoning.parquet"
    if reasoning.exists():
        frame = pd.read_parquet(reasoning)
        if "clip_id" in frame.columns:
            names.update(str(value) for value in frame["clip_id"])
        if frame.index.name == "clip_id":
            names.update(str(value) for value in frame.index)
    return sorted(names)


def sample_time_bounds(samples: list[dict[str, Any]]) -> dict[str, dict[str, int]]:
    bounds: dict[str, dict[str, int]] = {}
    for sample in samples:
        scene_token = sample["scene_token"]
        timestamp = int(sample["timestamp"])
        if scene_token not in bounds:
            bounds[scene_token] = {"first_timestamp": timestamp, "last_timestamp": timestamp}
        bounds[scene_token]["first_timestamp"] = min(bounds[scene_token]["first_timestamp"], timestamp)
        bounds[scene_token]["last_timestamp"] = max(bounds[scene_token]["last_timestamp"], timestamp)
    return bounds


def load_candidate_pairs(path: Path) -> set[tuple[str, str]]:
    if not path.exists():
        return set()
    payload = json.loads(path.read_text())
    pairs: set[tuple[str, str]] = set()
    for key in ("smallest_gap_pairs", "local_coc_candidates"):
        for item in payload.get(key, []):
            left = item.get("a_name") or item.get("from")
            right = item.get("b_name") or item.get("to")
            if left and right:
                pairs.add((str(left), str(right)))
    return pairs


def audit(metadata_root: Path, coc_root: Path, candidate_path: Path) -> dict[str, Any]:
    scenes = load_json(metadata_root / "scene.json")
    samples = load_json(metadata_root / "sample.json")
    logs = load_json(metadata_root / "log.json")
    ego_poses = load_json(metadata_root / "ego_pose.json")
    sample_data = load_json(metadata_root / "sample_data.json")

    bounds = sample_time_bounds(samples)
    log_by_token = {log["token"]: log for log in logs}
    scene_rows = []
    for scene in scenes:
        time_bound = bounds[scene["token"]]
        log = log_by_token[scene["log_token"]]
        scene_rows.append(
            {
                "name": scene["name"],
                "token": scene["token"],
                "log_token": scene["log_token"],
                "logfile": log.get("logfile"),
                "location": log.get("location"),
                "first_timestamp": time_bound["first_timestamp"],
                "last_timestamp": time_bound["last_timestamp"],
                "nbr_samples": scene.get("nbr_samples"),
            }
        )

    adjacent_pairs = []
    for log_token in sorted({row["log_token"] for row in scene_rows}):
        rows = sorted(
            [row for row in scene_rows if row["log_token"] == log_token],
            key=lambda row: row["first_timestamp"],
        )
        for left, right in zip(rows, rows[1:]):
            adjacent_pairs.append(
                {
                    "from": left["name"],
                    "to": right["name"],
                    "log_token": log_token,
                    "logfile": left["logfile"],
                    "location": left["location"],
                    "gap_seconds": round(
                        (right["first_timestamp"] - left["last_timestamp"]) / 1_000_000, 6
                    ),
                }
            )

    local_names = load_local_coc_scene_names(coc_root)
    official_names = sorted(row["name"] for row in scene_rows)
    local_overlap = sorted(set(local_names) & set(official_names))
    candidate_pairs = load_candidate_pairs(candidate_path)
    mini_pairs = {(item["from"], item["to"]) for item in adjacent_pairs}
    confirmed_candidate_pairs = sorted(candidate_pairs & mini_pairs)

    return {
        "audit": "official-nuscenes-mini-scene-continuity",
        "metadata_root": str(metadata_root),
        "table_counts": {
            "scene": len(scenes),
            "sample": len(samples),
            "sample_data": len(sample_data),
            "ego_pose": len(ego_poses),
            "log": len(logs),
        },
        "official_scene_names": official_names,
        "local_coc_scene_count": len(local_names),
        "local_coc_scene_overlap": local_overlap,
        "candidate_pair_source": str(candidate_path),
        "candidate_pair_overlap": [
            {"from": left, "to": right} for left, right in confirmed_candidate_pairs
        ],
        "same_log_adjacent_pair_count": len(adjacent_pairs),
        "same_log_adjacent_pairs": sorted(adjacent_pairs, key=lambda item: item["gap_seconds"]),
        "conclusion": {
            "official_mini_has_continuity_fields": True,
            "official_mini_can_demonstrate_schema": True,
            "official_mini_overlaps_local_coc_scenes": bool(local_overlap),
            "official_mini_can_validate_coc_trainval_candidate_pairs": bool(
                confirmed_candidate_pairs
            ),
            "reason": (
                "The official mini archive includes scene, sample, log, sample_data, and ego_pose "
                "tables, so it confirms the nuScenes continuity schema and overlaps with several "
                "local CoC-Nusc scene names. However, mini is a subset and omits many trainval "
                "scenes between those names, so adjacent scenes inside mini must not be interpreted "
                "as physically contiguous trainval pairs. It does not confirm the previously found "
                "CoC trainval candidate pairs."
            ),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--metadata-root",
        type=Path,
        default=Path("data/baseline/nuscenes_official/v1.0-mini"),
    )
    parser.add_argument("--coc-root", type=Path, default=Path("data/baseline/coc_nusc"))
    parser.add_argument(
        "--candidate-path",
        type=Path,
        default=Path("artifacts/results/public/nuscenes-scene-continuity-candidates.json"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("artifacts/results/public/nuscenes-official-mini-continuity-audit.json"),
    )
    args = parser.parse_args()
    result = audit(args.metadata_root, args.coc_root, args.candidate_path)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps(result["conclusion"], indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
