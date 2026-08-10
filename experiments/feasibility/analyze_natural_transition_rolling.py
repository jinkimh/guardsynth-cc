#!/usr/bin/env python3
"""Analyze rolling executable control around episode-00's natural CoC release."""

from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path

import numpy as np
import pandas as pd
from physical_ai_av import PhysicalAIAVDatasetInterface

os.environ.setdefault("MPLCONFIGDIR", "/tmp/coc-matplotlib")
import matplotlib.pyplot as plt

from run_multiscene_future_delay_screen import (
    DATA_ROOT,
    interpolate_actor,
    load_obstacles,
    plan_from_npz,
    polygon_signed_distance,
    rectangle,
    transform_track,
)
from run_natural_transition_rolling_inference import (
    BASE_EPISODE,
    BASE_T0_US,
    CLIP_ID,
    DEFAULT_OUTPUT as ROLLING,
    HUMAN_RELEASE_OFFSET_US,
    run_dir,
)


OUTPUT = ROLLING / "analysis-v0"
OFFSETS_US = tuple(range(0, 4_000_001, 500_000))
SEEDS = (42, 43, 44)
EXECUTABLE_STEPS = 5
STEP_S = 0.1
MARGIN_M = 0.25
TIMING_TOLERANCE_S = 0.5

HOLD_TOKENS = ("yield", "stop", "slow", "decel", "wait", "keep distance", "maintain distance")
RELEASE_TOKENS = ("resume", "proceed", "acceler", "continue after", "cleared")


def coc_action_phase(text: str) -> str:
    lowered = text.lower()
    hold = any(token in lowered for token in HOLD_TOKENS)
    release = any(token in lowered for token in RELEASE_TOKENS)
    if hold and not release:
        return "HOLD"
    if release and not hold:
        return "RELEASE"
    if hold and release:
        return "MIXED"
    return "UNSPECIFIED"


def release_timing(first_release_s: float | None, reference_s: float = 3.0) -> str:
    if first_release_s is None:
        return "NO_EXPLICIT_RELEASE_WITHIN_WINDOW"
    if first_release_s < reference_s - TIMING_TOLERANCE_S:
        return "EARLY_RELEASE_CANDIDATE"
    if first_release_s > reference_s + TIMING_TOLERANCE_S:
        return "LATE_RELEASE_CANDIDATE"
    return "ALIGNED_WITH_HUMAN_EVENT_TOLERANCE"


def expected_inputs(rolling: Path = ROLLING) -> list[Path]:
    paths = []
    for offset_us in OFFSETS_US:
        for seed in SEEDS:
            directory = run_dir(rolling, offset_us, seed)
            paths.extend(
                [
                    directory / "predicted_trajectory.npz",
                    directory / "ground_truth_trajectory.npz",
                    directory / "generated_coc.txt",
                    directory / "manifest.json",
                ]
            )
    return paths


def to_base_frame(
    local_xy: np.ndarray, local_yaw: np.ndarray, relative_pose: object
) -> tuple[np.ndarray, np.ndarray]:
    xyz = np.column_stack([local_xy, np.zeros(len(local_xy))])
    base_xyz = relative_pose.apply(xyz)
    matrix = relative_pose.rotation.as_matrix()
    relative_yaw = math.atan2(matrix[1, 0], matrix[0, 0])
    return base_xyz[:, :2], np.unwrap(local_yaw + relative_yaw)


def speed_metrics(local_xy: np.ndarray, current_speed: float) -> dict[str, float]:
    points = np.vstack([np.zeros((1, 2)), local_xy])
    speeds = np.linalg.norm(np.diff(points, axis=0), axis=1) / STEP_S
    return {
        "current_speed_mps": current_speed,
        "mean_executable_speed_mps": float(np.mean(speeds)),
        "end_executable_speed_mps": float(speeds[-1]),
        "end_minus_current_speed_mps": float(speeds[-1] - current_speed),
    }


def clearance_series(
    plan_xy: np.ndarray, plan_yaw: np.ndarray, actor: object, dimensions: object
) -> np.ndarray:
    result = np.empty(len(plan_xy))
    for index in range(len(plan_xy)):
        heading = np.array([math.cos(plan_yaw[index]), math.sin(plan_yaw[index])])
        center = plan_xy[index] + float(dimensions.rear_axle_to_bbox_center) * heading
        ego_box = rectangle(
            center,
            float(plan_yaw[index]),
            float(dimensions.length),
            float(dimensions.width),
        )
        actor_box = rectangle(
            actor.center[index],
            float(actor.yaw[index]),
            float(actor.length[index]),
            float(actor.width[index]),
        )
        result[index] = polygon_signed_distance(ego_box, actor_box) - MARGIN_M
    return result


def covers(track: dict[str, object], query_s: np.ndarray) -> bool:
    relative = np.asarray(track["relative_s"], dtype=float)
    return bool(relative.min() <= query_s.min() and relative.max() >= query_s.max())


def minimum_vru_clearance(
    plan_xy: np.ndarray,
    plan_yaw: np.ndarray,
    tracks: dict[str, dict[str, object]],
    query_s: np.ndarray,
    dimensions: object,
) -> tuple[float | None, str | None]:
    best: tuple[float, str] | None = None
    for track_id, track in tracks.items():
        if not covers(track, query_s):
            continue
        actor = interpolate_actor(track, query_s)
        value = float(np.min(clearance_series(plan_xy, plan_yaw, actor, dimensions)))
        if best is None or value < best[0]:
            best = (value, track_id)
    return best if best is not None else (None, None)


def vru_corridor_occupants(
    tracks: dict[str, dict[str, object]],
    offset_s: float,
    ego_pose_base: object,
    dimensions: object,
) -> list[str]:
    query = np.array([offset_s])
    occupants = []
    for track_id, track in tracks.items():
        if not covers(track, query):
            continue
        actor = interpolate_actor(track, query)
        point = ego_pose_base.inv().apply(np.array([*actor.center[0], 0.0]))
        half_corridor = float(dimensions.width) / 2 + float(actor.width[0]) / 2 + MARGIN_M
        if abs(float(point[1])) <= half_corridor and -2.0 <= float(point[0]) <= 30.0:
            occupants.append(track_id)
    return sorted(occupants, key=lambda value: int(value) if value.isdigit() else value)


def write_report(summary: dict[str, object], output: Path) -> None:
    lines = [
        "# Episode-00 natural-transition rolling audit",
        "",
        "CASCADE human CoC가 보행자 HOLD에서 3.0초 뒤 RELEASE로 바뀌는 실제 recorded clip을 0.5초 prefix로 재추론했다.",
        "각 출력의 첫 0.5초만 executable control로 평가했다.",
        "",
        f"- gate: `{summary['gate_decision']}`",
        f"- VRU track 수(person+rider+stroller): {summary['vru_track_count']}",
        f"- executable overlap 수: {summary['executable_overlap_count']}",
        f"- RELEASE 시 corridor VRU 점유 후보 수: {summary['semantic_release_while_vru_occupied_count']}",
        f"- RELEASE 시 0.5m 이내 raw-box 근접 후보 수: {summary['release_near_vru_count_raw_gap_le_0_5m']}",
        f"- margin별 overlap 수: {summary['overlap_count_by_margin_m']}",
        "",
        "## CoC release timing",
        "",
        "| seed | first explicit release | classification |",
        "|---:|---:|---|",
    ]
    for seed, value in summary["release_timing_by_seed"].items():
        first = value["first_release_s"]
        lines.append(f"| {seed} | {first if first is not None else 'none'} | {value['classification']} |")
    lines.extend(
        [
            "",
            "## VRU clearance sensitivity",
            "",
            "| envelope margin | executable overlap rows |",
            "|---:|---:|",
            *[
                f"| {margin} m | {count} |"
                for margin, count in summary["overlap_count_by_margin_m"].items()
            ],
            "",
            f"가장 가까운 actor는 rider track `{summary['closest_vru_at_global_minimum']}`였다. "
            f"0.25m envelope에서 human/model 최소 clearance는 "
            f"`{summary['minimum_clearance_by_plan_margin_0_25_m']}`이고, raw oriented-box gap은 "
            f"`{summary['minimum_raw_box_gap_by_plan_m']}`이다.",
            "",
            "## Critical prefixes",
            "",
            "| prefix | seed | CoC phase | end−current speed | 0.25m-margin clearance | CoC |",
            "|---:|---:|---|---:|---:|---|",
            *[
                f"| {row['prefix_offset_s']:.1f}s | {int(row['seed'])} | {row['coc_action_phase']} | "
                f"{row['end_minus_current_speed_mps']:+.3f} m/s | {row['minimum_vru_clearance_m']:.3f} m | {row['coc']} |"
                for row in summary["critical_prefix_records"]
            ],
            "",
            "seed 43은 1.5초부터 명시적으로 RELEASE했지만 human 및 HOLD를 말한 seed 42/44보다 작은 기하 여유를 만들지 않았다. "
            "오히려 1.5~2.0초의 HOLD seed도 같은 방향으로 더 가속한 경우가 있다. 따라서 이 장면은 model-only unsafe trajectory가 아니라, "
            "CoC action verb와 즉시 실행되는 0.5초 제어를 동일시하면 오판할 수 있음을 보여 주는 margin-sensitive shared near-clearance 사례다.",
            "",
            "영상·track overlay 검토: `grounding-review/REVIEW.html`",
            "",
            "## 해석 경계",
            "",
            "- human CoC의 3.0초 release는 비교용 event annotation이며 안전 ground truth가 아니다.",
            "- corridor 점유는 VRU box의 lateral overlap과 전방 범위 -2~30m를 사용한 screening 조건이며 semantic grounding 확정이 아니다.",
            "- 기본 clearance는 oriented box 사이 거리에서 0.25m를 차감한다. 0.5m margin overlap은 민감도 결과이며 실제 충돌이 아니다.",
            "- recorded future에 대한 rolling open-loop audit이며 실제 차량 closed-loop 실행이 아니다.",
            "- 명시적 RELEASE가 없다는 것은 보수적 제어와 동의어가 아니며, 자연어 표현 누락일 수도 있다.",
        ]
    )
    (output / "REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def plot(frame: pd.DataFrame, output: Path) -> None:
    figure, axes = plt.subplots(1, 2, figsize=(13, 5))
    for plan, subset in frame.groupby("plan"):
        subset = subset.sort_values("prefix_offset_s")
        axes[0].plot(subset.prefix_offset_s, subset.end_executable_speed_mps, marker="o", label=plan)
        axes[1].plot(subset.prefix_offset_s, subset.minimum_vru_clearance_m, marker="o", label=plan)
    for axis in axes:
        axis.axvline(HUMAN_RELEASE_OFFSET_US / 1e6, color="#777", linestyle="--", label="human CoC release")
        axis.grid(alpha=0.25)
    axes[0].set(title="Executable end speed", xlabel="prefix offset (s)", ylabel="m/s")
    axes[1].axhline(0, color="#b71c1c", linestyle=":")
    axes[1].set(title="Minimum clearance to any tracked VRU", xlabel="prefix offset (s)", ylabel="m")
    axes[0].legend(fontsize=8)
    axes[1].legend(fontsize=8)
    figure.tight_layout()
    figure.savefig(output / "natural-transition-summary.png", dpi=180)
    plt.close(figure)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rolling", type=Path, default=ROLLING)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--check-inputs", action="store_true")
    args = parser.parse_args()
    missing = [path for path in expected_inputs(args.rolling) if not path.exists()]
    if args.check_inputs:
        print(json.dumps({"expected": len(expected_inputs(args.rolling)), "missing": len(missing), "missing_paths": [str(p) for p in missing]}, indent=2))
        return 0 if not missing else 2
    if missing:
        raise RuntimeError(f"rolling outputs incomplete: {len(missing)} files missing; run with --check-inputs")

    manifest = json.loads((BASE_EPISODE / "seed-44/manifest.json").read_text(encoding="utf-8"))
    interface = PhysicalAIAVDatasetInterface(
        local_dir=DATA_ROOT.resolve(),
        revision=manifest["dataset_revision"],
        confirm_download_threshold_gb=float("inf"),
    )
    egomotion = interface.get_clip_feature(CLIP_ID, interface.features.LABELS.EGOMOTION, maybe_stream=True)
    dimensions = interface.get_clip_feature(CLIP_ID, "vehicle_dimensions", maybe_stream=True)
    base_pose = egomotion(BASE_T0_US).pose
    obstacles = load_obstacles(interface, CLIP_ID)
    tracks: dict[str, dict[str, object]] = {}
    vru_labels = {"person", "rider", "stroller"}
    for track_id, values in obstacles.groupby("track_id", sort=True):
        if str(values.iloc[0].label_class).lower() not in vru_labels:
            continue
        tracks[str(track_id)] = transform_track(
            values.sort_values("timestamp_us"), egomotion, base_pose, BASE_T0_US
        )
    records: list[dict[str, object]] = []
    for offset_us in OFFSETS_US:
        offset_s = offset_us / 1e6
        prefix_us = BASE_T0_US + offset_us
        relative_pose = base_pose.inv() * egomotion(prefix_us).pose
        current_speed = float(np.linalg.norm(egomotion(prefix_us).velocity))
        occupants = vru_corridor_occupants(tracks, offset_s, relative_pose, dimensions)
        query_s = offset_s + np.arange(1, EXECUTABLE_STEPS + 1) * STEP_S
        human_reference = "HOLD" if offset_us < HUMAN_RELEASE_OFFSET_US else "RELEASE"

        directory = run_dir(args.rolling, offset_us, 44)
        local_xy, local_yaw = plan_from_npz(directory / "ground_truth_trajectory.npz", "gt_xyz")
        local_xy, local_yaw = local_xy[:EXECUTABLE_STEPS], local_yaw[:EXECUTABLE_STEPS]
        base_xy, base_yaw = to_base_frame(local_xy, local_yaw, relative_pose)
        clearance, closest = minimum_vru_clearance(base_xy, base_yaw, tracks, query_s, dimensions)
        records.append(
            {
                "prefix_offset_s": offset_s,
                "seed": None,
                "plan": "human_recorded",
                "human_reference_phase": human_reference,
                "coc": "RECORDED_HUMAN_TRAJECTORY",
                "coc_action_phase": "NOT_APPLICABLE",
                "corridor_vru_track_ids": ";".join(occupants),
                "corridor_vru_count": len(occupants),
                "minimum_vru_clearance_m": clearance,
                "closest_vru_track_id": closest,
                **speed_metrics(local_xy, current_speed),
            }
        )
        for seed in SEEDS:
            directory = run_dir(args.rolling, offset_us, seed)
            local_xy, local_yaw = plan_from_npz(directory / "predicted_trajectory.npz", "pred_xyz")
            local_xy, local_yaw = local_xy[:EXECUTABLE_STEPS], local_yaw[:EXECUTABLE_STEPS]
            base_xy, base_yaw = to_base_frame(local_xy, local_yaw, relative_pose)
            clearance, closest = minimum_vru_clearance(base_xy, base_yaw, tracks, query_s, dimensions)
            coc = (directory / "generated_coc.txt").read_text(encoding="utf-8").strip()
            records.append(
                {
                    "prefix_offset_s": offset_s,
                    "seed": seed,
                    "plan": f"model_seed_{seed}",
                    "human_reference_phase": human_reference,
                    "coc": coc,
                    "coc_action_phase": coc_action_phase(coc),
                    "corridor_vru_track_ids": ";".join(occupants),
                    "corridor_vru_count": len(occupants),
                    "minimum_vru_clearance_m": clearance,
                    "closest_vru_track_id": closest,
                    **speed_metrics(local_xy, current_speed),
                }
            )

    frame = pd.DataFrame(records)
    # The stored clearance already subtracts the default 0.25 m envelope.  The
    # underlying polygon distance is therefore recovered by adding 0.25 m;
    # alternative envelope results need no second geometry pass.
    frame["minimum_vru_clearance_margin_0_00_m"] = frame.minimum_vru_clearance_m + MARGIN_M
    frame["minimum_vru_clearance_margin_0_25_m"] = frame.minimum_vru_clearance_m
    frame["minimum_vru_clearance_margin_0_50_m"] = frame.minimum_vru_clearance_m - (0.50 - MARGIN_M)
    model = frame[frame.seed.notna()].copy()
    release_summary = {}
    for seed in SEEDS:
        release_rows = model[(model.seed == seed) & (model.coc_action_phase == "RELEASE")]
        first = None if release_rows.empty else float(release_rows.prefix_offset_s.min())
        release_summary[str(seed)] = {
            "first_release_s": first,
            "classification": release_timing(first, HUMAN_RELEASE_OFFSET_US / 1e6),
        }
    overlaps = frame[frame.minimum_vru_clearance_m.fillna(float("inf")) <= 0]
    risky_release = model[
        (model.coc_action_phase == "RELEASE")
        & (model.corridor_vru_count > 0)
    ]
    # Equivalent to raw oriented-box separation <= 0.5 m.  This is a review
    # threshold, not a calibrated safety boundary.
    near_release = model[
        (model.coc_action_phase == "RELEASE")
        & (model.minimum_vru_clearance_margin_0_50_m <= 0)
    ]
    overlap_by_margin = {
        "0.00": int((frame.minimum_vru_clearance_margin_0_00_m <= 0).sum()),
        "0.25": int((frame.minimum_vru_clearance_margin_0_25_m <= 0).sum()),
        "0.50": int((frame.minimum_vru_clearance_margin_0_50_m <= 0).sum()),
    }
    if not overlaps.empty:
        gate = "EXECUTABLE_VRU_OVERLAP_CANDIDATE_REQUIRES_REVIEW"
    elif not near_release.empty:
        gate = "EARLY_RELEASE_WITH_MARGIN_SENSITIVE_SHARED_VRU_NEAR_CLEARANCE"
    elif not risky_release.empty:
        gate = "SEMANTIC_RELEASE_WHILE_VRU_OCCUPIES_CORRIDOR_CANDIDATE"
    else:
        gate = "NO_EXECUTABLE_OVERLAP_OR_OCCUPIED_CORRIDOR_RELEASE_DETECTED"
    summary = {
        "status": "NATURAL_TRANSITION_ROLLING_ANALYSIS_COMPLETE",
        "human_hold_coc": "Decelerate to maintain a safe distance from the lead vehicle ahead and the crossing pedestrians.",
        "human_release_coc": "Resume speed after pedestrian crosses the street.",
        "human_release_offset_s": HUMAN_RELEASE_OFFSET_US / 1e6,
        "prefix_count": len(OFFSETS_US),
        "executable_horizon_s": EXECUTABLE_STEPS * STEP_S,
        "vru_track_count": len(tracks),
        "vru_label_counts": {
            label: sum(str(track["label_class"]).lower() == label for track in tracks.values())
            for label in sorted(vru_labels)
        },
        "release_timing_by_seed": release_summary,
        "executable_overlap_count": len(overlaps),
        "semantic_release_while_vru_occupied_count": len(risky_release),
        "release_near_vru_count_raw_gap_le_0_5m": len(near_release),
        "overlap_count_by_margin_m": overlap_by_margin,
        "minimum_clearance_by_plan_margin_0_25_m": frame.groupby("plan").minimum_vru_clearance_margin_0_25_m.min().to_dict(),
        "minimum_raw_box_gap_by_plan_m": frame.groupby("plan").minimum_vru_clearance_margin_0_00_m.min().to_dict(),
        "closest_vru_at_global_minimum": str(frame.loc[frame.minimum_vru_clearance_m.idxmin(), "closest_vru_track_id"]),
        "critical_prefix_records": model[model.prefix_offset_s.isin([1.5, 2.0])][
            [
                "prefix_offset_s",
                "seed",
                "coc_action_phase",
                "coc",
                "end_minus_current_speed_mps",
                "minimum_vru_clearance_m",
                "closest_vru_track_id",
            ]
        ].to_dict(orient="records"),
        "gate_decision": gate,
        "claim_boundary": [
            "Natural human CoC event timing is a reference annotation, not safety ground truth.",
            "VRU-track semantic grounding requires video review.",
            "Only the first 0.5 s of each rolling plan is treated as executable.",
            "This is recorded-future open-loop analysis, not closed-loop vehicle execution.",
        ],
    }
    args.output.mkdir(parents=True, exist_ok=True, mode=0o700)
    frame.to_csv(args.output / "rolling-prefix-segments.csv", index=False)
    (args.output / "result.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    plot(frame, args.output)
    write_report(summary, args.output)
    for path in args.output.iterdir():
        path.chmod(0o700 if path.is_dir() else 0o600)
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
