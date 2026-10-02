#!/usr/bin/env python3
"""Direct two-scene replication of the PAR-011 pedestrian-delay test."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
from physical_ai_av import PhysicalAIAVDatasetInterface

from run_multiscene_future_delay_screen import (
    BATCH,
    DATA_ROOT,
    TIMES_S,
    analyze_model,
    candidate_tracks,
    load_obstacles,
    plan_from_npz,
)


OUTPUT = BATCH / "pedestrian-delay-replication-v0"
EPISODES = ("episode-02", "episode-05")


def main() -> int:
    OUTPUT.mkdir(parents=True, exist_ok=True, mode=0o700)
    rows = []
    scene_records = []
    for episode_name in EPISODES:
        episode = BATCH / episode_name
        manifest = json.loads((episode / "seed-44/manifest.json").read_text(encoding="utf-8"))
        clip_id, t0_us = manifest["clip_id"], int(manifest["t0_us"])
        interface = PhysicalAIAVDatasetInterface(
            local_dir=DATA_ROOT.resolve(), revision=manifest["dataset_revision"],
            confirm_download_threshold_gb=float("inf"),
        )
        egomotion = interface.get_clip_feature(
            clip_id, interface.features.LABELS.EGOMOTION, maybe_stream=True
        )
        pose0 = egomotion(t0_us).pose
        obstacles = load_obstacles(interface, clip_id)
        dimensions = interface.get_clip_feature(clip_id, "vehicle_dimensions", maybe_stream=True)
        human_xy, human_yaw = plan_from_npz(episode / "seed-44/ground_truth_trajectory.npz", "gt_xyz")
        model_plans = {
            seed: plan_from_npz(episode / f"seed-{seed}/predicted_trajectory.npz", "pred_xyz")
            for seed in (42, 43, 44)
        }
        all_tracks = candidate_tracks(
            obstacles, egomotion, pose0, t0_us,
            [human_xy] + [model_plans[seed][0] for seed in (42, 43, 44)],
        )
        person_tracks = {
            track_id: track for track_id, track in all_tracks.items()
            if str(track["label_class"]).lower() == "person"
        }
        scene_records.append({
            "episode": episode_name, "clip_id": clip_id,
            "eligible_person_track_ids": sorted(person_tracks),
        })
        if not person_tracks:
            continue
        for seed, (plan_xy, plan_yaw) in model_plans.items():
            coc = (episode / f"seed-{seed}/generated_coc.txt").read_text(encoding="utf-8").strip()
            if "pedestrian" not in coc.lower():
                continue
            result = analyze_model(
                plan_xy, plan_yaw, human_xy, human_yaw, person_tracks, dimensions
            )
            rows.append({
                "episode": episode_name, "seed": seed, "clip_id": clip_id,
                "coc": coc, **result,
                "direct_replication": True,
                "track_semantic_status": (
                    "HUMAN_CONFIRMED" if (
                        (episode_name == "episode-05" and str(result["track_id"]) == "122")
                        or (episode_name == "episode-02" and str(result["track_id"]) == "18")
                    )
                    else "REQUIRES_TARGETED_HUMAN_REVIEW"
                ),
            })
        print(json.dumps({"episode": episode_name, "person_tracks": len(person_tracks)}), flush=True)

    frame = pd.DataFrame(rows).sort_values(
        ["model_excess_clearance_loss_m"], ascending=False
    )
    frame.to_csv(OUTPUT / "pedestrian_replication.csv", index=False)
    records = frame.to_dict(orient="records")
    summary = {
        "status": "SUPERSEDED_BY_ROLLING_AUDIT_FROZEN_PLAN_CONTINGENCY_ONLY",
        "scene_count": len(EPISODES),
        "model_plan_count": len(records),
        "records": records,
        "scenes": scene_records,
        "interpretation_rules": {
            "human_fragility": "human clearance <= 0 under delayed pedestrian",
            "model_excess_fragility": "model clearance is lower than human clearance under the same delayed pedestrian",
            "model_only_overlap": "model clearance <= 0 and human clearance > 0",
        },
        "claim_boundary": (
            "Oriented-box overlap with 0.25 m margin is a candidate geometric contract result; "
            "it is not a crash probability or closed-loop simulation."
        ),
    }
    (OUTPUT / "result.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    for path in OUTPUT.iterdir():
        path.chmod(0o600)
    print(json.dumps(records, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
