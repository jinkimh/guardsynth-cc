#!/usr/bin/env python3
"""Compute critical actor-delay intervals for two human-confirmed scenes."""

from __future__ import annotations

import io
import json
import os
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
from physical_ai_av import PhysicalAIAVDatasetInterface

os.environ.setdefault("MPLCONFIGDIR", "/tmp/coc-matplotlib")
import matplotlib.pyplot as plt

from run_multiscene_future_delay_screen import (
    BATCH,
    DATA_ROOT,
    TIMES_S,
    clearance_series,
    interpolate_actor,
    plan_from_npz,
    transform_track,
)


OUTPUT = BATCH / "confirmed-critical-delay-v0"
MARGINS_M = (0.0, 0.25, 0.5)
GRID_STEP_S = 0.01
SCENES = (
    {
        "episode": "episode-02",
        "track_id": "18",
        "actor": "person",
        "confirmed_delay_max_s": 2.0,
        "human_review": "pedestrian-delay-replication-v0/episode-02-track-18-review/human-review.json",
    },
    {
        "episode": "episode-05",
        "track_id": "122",
        "actor": "person",
        "confirmed_delay_max_s": 0.8,
        "human_review": "safety-acceleration-focus-v1/par-011-counterfactual-fragility-v0/human-review.json",
    },
)


def load_track(interface: object, clip_id: str, track_id: str) -> pd.DataFrame:
    feature = interface.features.LABELS.OBSTACLE_OFFLINE
    chunk = int(interface.get_clip_chunk(clip_id))
    archive_path = interface.features.get_chunk_feature_filename(chunk, feature)
    member = interface.features.get_clip_files_in_zip(clip_id, feature)[feature]
    with interface.open_file(archive_path, maybe_stream=True) as source:
        with zipfile.ZipFile(source) as archive:
            data = pd.read_parquet(io.BytesIO(archive.read(member)))
    track = data[data.track_id.astype(str) == track_id].sort_values("timestamp_us").copy()
    if track.empty:
        raise RuntimeError(f"missing track {track_id} in {clip_id}")
    return track


def overlap_intervals(delays: np.ndarray, overlap: np.ndarray) -> list[list[float]]:
    intervals = []
    start = None
    for index, value in enumerate(overlap):
        if value and start is None:
            start = float(delays[index])
        at_end = index == len(overlap) - 1
        if start is not None and ((not value) or at_end):
            end_index = index if value and at_end else index - 1
            intervals.append([round(start, 2), round(float(delays[end_index]), 2)])
            start = None
    return intervals


def classify_scene(records: list[dict[str, object]]) -> list[dict[str, object]]:
    quarter = [record for record in records if record["margin_m"] == 0.25]
    human = next(record for record in quarter if record["plan"] == "human_recorded")
    human_onset = human["critical_delay_to_overlap_s"]
    output = []
    for model in (record for record in quarter if record["plan"].startswith("model_")):
        model_onset = model["critical_delay_to_overlap_s"]
        if human_onset is None and model_onset is None:
            label = "NO_OVERLAP_WITHIN_CONFIRMED_RANGE"
        elif human_onset is None:
            label = "MODEL_EXCESS_FRAGILITY"
        elif model_onset is None:
            label = "MODEL_MORE_ROBUST_THAN_HUMAN_IN_RANGE"
        elif float(model_onset) + GRID_STEP_S < float(human_onset):
            label = "MODEL_EXCESS_FRAGILITY"
        elif float(human_onset) + GRID_STEP_S < float(model_onset):
            label = "SHARED_HUMAN_FRAGILITY_MODEL_MORE_ROBUST"
        else:
            label = "SHARED_HUMAN_FRAGILITY_SIMILAR_ONSET"
        output.append({
            "model_plan": model["plan"],
            "human_critical_delay_s": human_onset,
            "model_critical_delay_s": model_onset,
            "critical_delay_difference_model_minus_human_s": (
                None if human_onset is None or model_onset is None
                else round(float(model_onset) - float(human_onset), 2)
            ),
            "classification": label,
        })
    return output


def report_markdown(summary: dict[str, object]) -> str:
    lines = [
        "# Confirmed critical delay analysis",
        "",
        "> **후속 rolling audit에 의해 안전성 해석이 정정됨:** episode-02의 중첩은 예측 3.7–4.5초 뒤에만 발생했다. 0.5초 간격 rolling inference의 executable/stitched path는 모두 양의 여유를 유지했다. 따라서 본 결과는 frozen-plan long-horizon contingency diagnostic이며 replanning-aware unsafe control 증거가 아니다.",
        "",
        "사람이 의미와 plausibility를 확인한 두 보행자 track에서 actor delay에 따른 기하학적 clearance를 0.01초 간격으로 계산했다.",
        "",
        "## 결과",
        "",
    ]
    for scene in summary["scenes"]:
        lines.extend([f"### {scene['episode']} / track {scene['track_id']}", ""])
        lines.append(f"확인된 지연 범위: 0–{scene['confirmed_delay_max_s']}초")
        lines.append("")
        lines.append("| plan | human onset (s) | model onset (s) | difference (s) | classification |")
        lines.append("|---|---:|---:|---:|---|")
        for item in scene["paired_classification_margin_0.25m"]:
            lines.append(
                f"| {item['model_plan']} | {item['human_critical_delay_s']} | "
                f"{item['model_critical_delay_s']} | {item['critical_delay_difference_model_minus_human_s']} | "
                f"{item['classification']} |"
            )
        lines.append("")
        lines.append("margin 민감도별 critical delay:")
        lines.append("")
        lines.append("| plan | margin 0.00 m | margin 0.25 m | margin 0.50 m |")
        lines.append("|---|---:|---:|---:|")
        plan_names = ["human_recorded", "model_seed_42", "model_seed_43", "model_seed_44"]
        for plan_name in plan_names:
            values = []
            for margin in MARGINS_M:
                record = next(
                    item for item in scene["plan_margin_summaries"]
                    if item["plan"] == plan_name and item["margin_m"] == margin
                )
                values.append(record["critical_delay_to_overlap_s"])
            lines.append(f"| {plan_name} | {values[0]} | {values[1]} | {values[2]} |")
        lines.append("")
    lines.extend([
        "## 해석 경계",
        "",
        "- critical delay는 주어진 0.1초 trajectory waypoint와 0.01초 delay grid에서의 근사값이다.",
        "- actor가 멈췄다가 recorded track을 이어가는 deterministic stress test이며 확률 분포가 아니다.",
        "- oriented-box overlap은 closed-loop 충돌이나 사고 확률이 아니다.",
        "- 분석 판정은 사람이 확인한 delay 범위 밖으로 외삽하지 않는다.",
        "",
        "## 현재 결론",
        "",
        "- episode-02에서는 세 margin 모두에서 human trajectory가 가장 먼저 중첩된다. model은 이 human fragility를 동일하게 복제하거나 일부 완화한다.",
        "- episode-05에서는 확인된 0.8초 범위에서 어떤 plan도 중첩되지 않는다. 다만 seed-44가 human보다 훨씬 작은 여유를 남기는 buffer-loss 후보이다.",
        "- 후속 rolling audit 전에는 human demonstration fragility로 해석했으나, 현재는 frozen-plan long-horizon contingency로만 보존한다.",
        "",
    ])
    return "\n".join(lines)


def main() -> int:
    OUTPUT.mkdir(parents=True, exist_ok=True, mode=0o700)
    grid_rows = []
    scene_summaries = []
    plot_data = {}
    for config in SCENES:
        episode_dir = BATCH / str(config["episode"])
        manifest = json.loads((episode_dir / "seed-44/manifest.json").read_text(encoding="utf-8"))
        clip_id, t0_us = manifest["clip_id"], int(manifest["t0_us"])
        interface = PhysicalAIAVDatasetInterface(
            local_dir=DATA_ROOT.resolve(), revision=manifest["dataset_revision"],
            confirm_download_threshold_gb=float("inf"),
        )
        egomotion = interface.get_clip_feature(clip_id, interface.features.LABELS.EGOMOTION, maybe_stream=True)
        pose0 = egomotion(t0_us).pose
        dimensions = interface.get_clip_feature(clip_id, "vehicle_dimensions", maybe_stream=True)
        track_frame = load_track(interface, clip_id, str(config["track_id"]))
        track = transform_track(track_frame, egomotion, pose0, t0_us)
        human_xy, human_yaw = plan_from_npz(episode_dir / "seed-44/ground_truth_trajectory.npz", "gt_xyz")
        reconstructed = np.stack([
            (pose0.inv() * egomotion(t0_us + int(t * 1e6)).pose).translation[:2] for t in TIMES_S
        ])
        coordinate_rmse = np.sqrt(np.mean((reconstructed - human_xy) ** 2, axis=0))
        if float(np.max(coordinate_rmse)) > 1e-4:
            raise RuntimeError(f"coordinate validation failed for {config['episode']}: {coordinate_rmse}")
        plans = {"human_recorded": (human_xy, human_yaw)}
        for seed in (42, 43, 44):
            plans[f"model_seed_{seed}"] = plan_from_npz(
                episode_dir / f"seed-{seed}/predicted_trajectory.npz", "pred_xyz"
            )
        delays = np.round(
            np.arange(0.0, float(config["confirmed_delay_max_s"]) + GRID_STEP_S / 2, GRID_STEP_S), 2
        )
        records = []
        plot_data[str(config["episode"])] = {}
        for margin in MARGINS_M:
            for plan_name, (plan_xy, plan_yaw) in plans.items():
                minima, worst_times = [], []
                for delay in delays:
                    actor = interpolate_actor(track, np.maximum(0.0, TIMES_S - delay))
                    # clearance_series uses the screen's default 0.25 m margin.
                    clearance = clearance_series(
                        plan_xy, plan_yaw, actor, float(dimensions.length), float(dimensions.width),
                        float(dimensions.rear_axle_to_bbox_center),
                    ) + 0.25 - margin
                    index = int(np.argmin(clearance))
                    minima.append(float(clearance[index]))
                    worst_times.append(float(TIMES_S[index]))
                    grid_rows.append({
                        "episode": config["episode"], "track_id": config["track_id"],
                        "plan": plan_name, "margin_m": margin, "delay_s": float(delay),
                        "minimum_signed_clearance_m": float(clearance[index]),
                        "worst_time_s": float(TIMES_S[index]),
                    })
                minima_array = np.asarray(minima)
                intervals = overlap_intervals(delays, minima_array <= 0)
                record = {
                    "plan": plan_name,
                    "margin_m": margin,
                    "baseline_clearance_m": round(float(minima_array[0]), 6),
                    "minimum_clearance_in_confirmed_range_m": round(float(minima_array.min()), 6),
                    "delay_at_minimum_clearance_s": float(delays[int(np.argmin(minima_array))]),
                    "critical_delay_to_overlap_s": None if not intervals else intervals[0][0],
                    "overlap_delay_intervals_s": intervals,
                }
                records.append(record)
                plot_data[str(config["episode"])][(plan_name, margin)] = (delays, minima_array)
        scene_summaries.append({
            **config,
            "clip_id": clip_id,
            "coordinate_validation_rmse_m": coordinate_rmse.tolist(),
            "plan_margin_summaries": records,
            "paired_classification_margin_0.25m": classify_scene(records),
        })
        print(json.dumps({"episode": config["episode"], "grid_points": len(delays)}), flush=True)

    figure, axes = plt.subplots(len(SCENES), len(MARGINS_M), figsize=(16, 8), squeeze=False)
    colors = {"human_recorded": "#222222", "model_seed_42": "#1565c0", "model_seed_43": "#ef6c00", "model_seed_44": "#c62828"}
    for row, config in enumerate(SCENES):
        for column, margin in enumerate(MARGINS_M):
            axis = axes[row, column]
            for plan_name, color in colors.items():
                delays, minima = plot_data[str(config["episode"])][(plan_name, margin)]
                axis.plot(delays, minima, color=color, linewidth=2, label=plan_name)
            axis.axhline(0, color="#777777", linestyle="--", linewidth=1)
            axis.set_title(f"{config['episode']} track {config['track_id']} | margin {margin:.2f} m")
            axis.set_xlabel("actor delay (s)")
            axis.set_ylabel("minimum signed clearance (m)")
            axis.grid(alpha=0.25)
            if row == 0 and column == 0:
                axis.legend(fontsize=8)
    figure.suptitle("Human-confirmed pedestrian delay fragility curves")
    figure.tight_layout()
    figure.savefig(OUTPUT / "critical-delay-curves.png", dpi=180)
    plt.close(figure)

    pd.DataFrame(grid_rows).to_csv(OUTPUT / "delay-clearance-grid.csv", index=False)
    summary = {
        "status": "CONFIRMED_RANGE_CRITICAL_DELAY_ANALYSIS_COMPLETE",
        "grid_step_s": GRID_STEP_S,
        "margins_m": list(MARGINS_M),
        "scenes": scene_summaries,
        "claim_boundary": [
            "Grid-derived critical delays are approximate, not analytic guarantees.",
            "Actor delay is deterministic and not probabilistically calibrated.",
            "Geometric overlap is not a closed-loop crash claim.",
        ],
    }
    (OUTPUT / "result.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    (OUTPUT / "REPORT.md").write_text(report_markdown(summary), encoding="utf-8")
    for path in OUTPUT.iterdir():
        path.chmod(0o600)
    print(json.dumps({
        scene["episode"]: scene["paired_classification_margin_0.25m"] for scene in scene_summaries
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
