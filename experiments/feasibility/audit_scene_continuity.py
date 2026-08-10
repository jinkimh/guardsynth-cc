#!/usr/bin/env python3
"""Audit whether local PAD/nuScenes-style data can support inter-scene continuity."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

import pandas as pd


CONTINUITY_FIELDS = {
    "global_timestamp",
    "timestamp_start",
    "timestamp_end",
    "start_time",
    "end_time",
    "log_id",
    "log_token",
    "scene_token",
    "prev",
    "next",
    "prev_scene",
    "next_scene",
    "global_pose",
    "ego_pose",
    "map",
    "route",
    "track_id",
}


def read_table(path: Path) -> pd.DataFrame | None:
    if not path.exists():
        return None
    if path.suffix == ".csv":
        return pd.read_csv(path)
    return pd.read_parquet(path)


def table_summary(path: Path) -> dict[str, Any]:
    frame = read_table(path)
    if frame is None:
        return {"path": str(path), "exists": False}
    columns = [str(column) for column in frame.columns]
    index_name = str(frame.index.name) if frame.index.name else None
    matched = sorted(
        field
        for field in CONTINUITY_FIELDS
        if field in {column.lower() for column in columns + ([index_name] if index_name else [])}
    )
    fuzzy = sorted(
        column
        for column in columns + ([index_name] if index_name else [])
        if column and any(field in column.lower() for field in CONTINUITY_FIELDS)
    )
    return {
        "path": str(path),
        "exists": True,
        "shape": list(frame.shape),
        "index": index_name,
        "columns": columns,
        "continuity_field_matches": matched,
        "continuity_field_fuzzy_matches": fuzzy,
    }


def egomotion_reset_summary(root: Path) -> dict[str, Any]:
    egomotion_dir = root / "labels/egomotion"
    paths = sorted(egomotion_dir.glob("scene-*.egomotion.parquet"))
    rows = []
    for path in paths:
        frame = pd.read_parquet(path)
        rows.append(
            {
                "clip_id": path.name.split(".")[0],
                "t_min": int(frame["timestamp"].min()),
                "t_max": int(frame["timestamp"].max()),
                "start_x": float(frame["x"].iloc[0]),
                "start_y": float(frame["y"].iloc[0]),
                "end_x": float(frame["x"].iloc[-1]),
                "end_y": float(frame["y"].iloc[-1]),
            }
        )
    numeric_pairs = []
    by_clip = {row["clip_id"]: row for row in rows}
    for row in rows:
        number = int(row["clip_id"].split("-")[1])
        next_clip = f"scene-{number + 1:04d}"
        if next_clip not in by_clip:
            continue
        other = by_clip[next_clip]
        gap = math.hypot(other["start_x"] - row["end_x"], other["start_y"] - row["end_y"])
        numeric_pairs.append(
            {
                "from": row["clip_id"],
                "to": next_clip,
                "naive_local_pose_gap_m": round(gap, 4),
            }
        )
    return {
        "egomotion_file_count": len(paths),
        "all_timestamps_start_at_zero": bool(rows) and all(row["t_min"] == 0 for row in rows),
        "all_start_poses_near_zero": bool(rows)
        and all(abs(row["start_x"]) < 1e-6 and abs(row["start_y"]) < 1e-6 for row in rows),
        "numeric_consecutive_pairs": len(numeric_pairs),
        "smallest_naive_local_pose_gaps": sorted(
            numeric_pairs, key=lambda item: item["naive_local_pose_gap_m"]
        )[:10],
    }


def hf_tree_summary(tree_dir: Path) -> dict[str, Any]:
    files = []
    for path in sorted(tree_dir.glob("*.json")):
        payload = json.loads(path.read_text())
        files.extend(payload.get("files", {}).keys())
    metadata_files = sorted(path for path in files if path.startswith("metadata/"))
    continuity_named_files = sorted(
        path
        for path in files
        if any(token in path.lower() for token in ("scene", "sample", "log", "pose", "route", "map"))
    )
    return {
        "tree_file_count": len(list(tree_dir.glob("*.json"))),
        "repo_file_count": len(files),
        "metadata_files": metadata_files,
        "continuity_named_file_count": len(continuity_named_files),
        "continuity_named_file_examples": continuity_named_files[:30],
    }


def audit(coc_root: Path, nvidia_root: Path) -> dict[str, Any]:
    coc_tables = [
        coc_root / "clip_index.parquet",
        coc_root / "metadata/feature_presence.parquet",
        coc_root / "reasoning/ood_reasoning.parquet",
    ]
    nvidia_tables = [
        nvidia_root / "clip_index.parquet",
        nvidia_root / "metadata/feature_presence.parquet",
        nvidia_root / "metadata/data_collection.parquet",
        nvidia_root / "reasoning/ood_reasoning.parquet",
        nvidia_root / "features.csv",
    ]
    result = {
        "audit": "scene-continuity-metadata",
        "required_evidence_for_inter_scene_connection": sorted(CONTINUITY_FIELDS),
        "coc_nusc": {
            "tables": [table_summary(path) for path in coc_tables],
            "egomotion_reset_summary": egomotion_reset_summary(coc_root),
        },
        "nvidia_physicalai": {
            "tables": [table_summary(path) for path in nvidia_tables],
            "hf_tree_summary": hf_tree_summary(nvidia_root / ".cache/huggingface/trees"),
        },
    }
    result["conclusion"] = {
        "inter_scene_connection_supported_by_local_metadata": False,
        "reason": (
            "Available local metadata lacks log/session id, prev/next scene relation, "
            "global timestamps, global ego poses, and object-track continuity. "
            "Existing egomotion in CoC-Nusc is scene-local: timestamps and start poses reset."
        ),
        "safe_policy": (
            "Treat scenes as independent episodes unless additional continuity metadata is provided. "
            "Use scene-boundary checks as a negative-control data gate."
        ),
        "download_priority": (
            "Do not download more camera/egomotion clips first. First obtain metadata that encodes "
            "global scene continuity, such as nuScenes scene/sample/log/ego_pose tables or an "
            "equivalent PAD prev-next/log/global-pose index."
        ),
    }
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--coc-root", type=Path, default=Path("data/baseline/coc_nusc"))
    parser.add_argument(
        "--nvidia-root", type=Path, default=Path("data/restricted/nvidia_physicalai")
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("artifacts/results/public/scene-continuity-audit.json"),
    )
    args = parser.parse_args()
    result = audit(args.coc_root, args.nvidia_root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps(result["conclusion"], indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
