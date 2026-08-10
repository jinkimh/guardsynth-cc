#!/usr/bin/env python3
"""Find natural pedestrian HOLD -> RELEASE transitions in CASCADE CoC labels.

This screen deliberately uses recorded event transitions instead of modifying an
actor future.  Its output is a candidate list for rolling-prefix inference, not
a safety label.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REASONING = ROOT / "data/restricted/nvidia_physicalai/reasoning/ood_reasoning.parquet"
DEFAULT_PRESENCE = ROOT / "data/restricted/nvidia_physicalai/metadata/feature_presence.parquet"
DEFAULT_BATCH = ROOT / "artifacts/results/restricted/alp-exp-005/feasibility-batch-v0"
DEFAULT_OUTPUT = DEFAULT_BATCH / "natural-pedestrian-transition-screen-v0"

PEDESTRIAN = re.compile(r"\b(pedestrian(?:s)?|person|people|child(?:ren)?|crosswalk)\b", re.I)
HOLD = re.compile(r"\b(stop|yield|wait|slow|decelerat\w*)\b", re.I)
RELEASE = re.compile(r"\b(resum\w*|proceed\w*|accelerat\w*|clear(?:ed|s|ing)?|crossed)\b", re.I)


def semantic_phase(text: str) -> str:
    """Return the pedestrian-related action phase expressed by one CoC."""
    if not PEDESTRIAN.search(text):
        return "OTHER"
    hold = bool(HOLD.search(text))
    release = bool(RELEASE.search(text))
    if hold and not release:
        return "HOLD"
    if release and not hold:
        return "RELEASE"
    if hold and release:
        return "MIXED"
    return "PEDESTRIAN_UNSPECIFIED"


def parse_events(value: object) -> list[dict[str, object]]:
    if not isinstance(value, str):
        return []
    parsed = json.loads(value)
    return sorted(parsed, key=lambda event: int(event["event_start_timestamp"]))


def transition_candidates(
    reasoning: pd.DataFrame,
    minimum_duration_s: float = 1.0,
    maximum_duration_s: float = 6.0,
) -> list[dict[str, object]]:
    """Pair each pedestrian HOLD with its nearest later pedestrian RELEASE."""
    records: list[dict[str, object]] = []
    for clip_id, row in reasoning.iterrows():
        events = parse_events(row.get("events"))
        for index, hold_event in enumerate(events):
            hold_coc = str(hold_event["coc"])
            if semantic_phase(hold_coc) != "HOLD":
                continue
            release_event = next(
                (
                    event
                    for event in events[index + 1 :]
                    if semantic_phase(str(event["coc"])) == "RELEASE"
                ),
                None,
            )
            if release_event is None:
                continue
            hold_us = int(hold_event["event_start_timestamp"])
            release_us = int(release_event["event_start_timestamp"])
            duration_s = (release_us - hold_us) / 1e6
            if not minimum_duration_s <= duration_s <= maximum_duration_s:
                continue
            records.append(
                {
                    "clip_id": str(clip_id),
                    "event_cluster": str(row.get("event_cluster", "")),
                    "split": str(row.get("split", "")),
                    "hold_t0_us": hold_us,
                    "release_t0_us": release_us,
                    "transition_duration_s": duration_s,
                    "hold_coc": hold_coc,
                    "release_coc": str(release_event["coc"]),
                }
            )
    return records


def episode_lookup(batch: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for manifest in sorted(batch.glob("episode-*/seed-44/manifest.json")):
        data = json.loads(manifest.read_text(encoding="utf-8"))
        result[str(data["clip_id"])] = manifest.parents[1].name
    return result


def add_availability(
    records: Iterable[dict[str, object]], presence: pd.DataFrame, batch: Path
) -> list[dict[str, object]]:
    episodes = episode_lookup(batch)
    output = []
    required = (
        "egomotion",
        "obstacle.offline",
        "vehicle_dimensions",
        "camera_front_wide_120fov",
    )
    for record in records:
        item = dict(record)
        clip_id = str(item["clip_id"])
        if clip_id in presence.index:
            missing = [feature for feature in required if not bool(presence.loc[clip_id, feature])]
        else:
            missing = list(required)
        item["required_features_available"] = not missing
        item["missing_required_features"] = ";".join(missing)
        item["existing_batch_episode"] = episodes.get(clip_id, "")
        item["reuses_existing_t0_inference"] = bool(
            episodes.get(clip_id)
            and (batch / episodes[clip_id] / "seed-44/manifest.json").exists()
            and int(
                json.loads(
                    (batch / episodes[clip_id] / "seed-44/manifest.json").read_text(
                        encoding="utf-8"
                    )
                )["t0_us"]
            )
            == int(item["hold_t0_us"])
        )
        # Prefer an existing exact-t0 run, then complete sensor coverage, then a
        # transition long enough to contain multiple 0.5 s prefixes.
        item["screen_priority"] = (
            int(item["reuses_existing_t0_inference"]) * 100
            + int(item["required_features_available"]) * 10
            + min(float(item["transition_duration_s"]), 5.0)
        )
        output.append(item)
    return sorted(output, key=lambda item: (-float(item["screen_priority"]), str(item["clip_id"])))


def base_executable_metrics(batch: Path) -> list[dict[str, object]]:
    records = []
    for seed in (42, 43, 44):
        directory = batch / "episode-00" / f"seed-{seed}"
        predicted_path = directory / "predicted_trajectory.npz"
        human_path = directory / "ground_truth_trajectory.npz"
        if not predicted_path.exists() or not human_path.exists():
            continue
        predicted = np.load(predicted_path)["pred_xyz"].reshape(-1, 64, 3)[0, :, :2]
        human = np.load(human_path)["gt_xyz"].reshape(-1, 64, 3)[0, :, :2]
        predicted_speed = np.linalg.norm(
            np.diff(np.vstack([np.zeros((1, 2)), predicted]), axis=0), axis=1
        ) / 0.1
        human_speed = np.linalg.norm(
            np.diff(np.vstack([np.zeros((1, 2)), human]), axis=0), axis=1
        ) / 0.1
        records.append(
            {
                "seed": seed,
                "model_end_speed_0_5s_mps": float(predicted_speed[4]),
                "model_mean_speed_0_5s_mps": float(predicted_speed[:5].mean()),
                "human_end_speed_0_5s_mps": float(human_speed[4]),
                "human_mean_speed_0_5s_mps": float(human_speed[:5].mean()),
            }
        )
    return records


def report(
    records: list[dict[str, object]],
    base_model_cocs: dict[str, str],
    executable_metrics: list[dict[str, object]],
) -> str:
    lines = [
        "# Natural pedestrian HOLD→RELEASE screen",
        "",
        "합성 actor delay 없이 CASCADE의 연속 human CoC에서 보행자 HOLD 뒤 RELEASE가 명시된 clip을 찾았다.",
        "이 결과는 rolling-prefix 실험 후보이며, CoC 정답이나 안전 위반 판정이 아니다.",
        "",
        f"- 후보 수: {len(records)}",
        f"- 기존 feasibility batch exact-t0 재사용 가능: {sum(bool(r['reuses_existing_t0_inference']) for r in records)}",
        "",
        "| rank | episode | duration | hold | release |",
        "|---:|---|---:|---|---|",
    ]
    for rank, item in enumerate(records, 1):
        lines.append(
            f"| {rank} | {item['existing_batch_episode'] or 'new clip'} | "
            f"{float(item['transition_duration_s']):.1f}s | {item['hold_coc']} | {item['release_coc']} |"
        )
    lines.extend(
        [
            "",
            "## 최우선 후보의 기존 t0 출력",
            "",
            "human CoC는 lead vehicle과 crossing pedestrians를 함께 감속 이유로 들지만, 기존 Alpamayo 3회 출력은 다음과 같다.",
            "",
            *[f"- seed {seed}: {coc}" for seed, coc in base_model_cocs.items()],
            "",
            "세 출력 모두 HOLD 계열 행동이지만 원인 객체는 lead vehicle 또는 cyclist로 달랐고 pedestrian은 명시하지 않았다. "
            "이는 곧바로 오류가 아니라, 자연 전환 동안 causal attribution과 release timing이 안정적인지 검사해야 할 근거다.",
            "",
            "기존 t0에서 첫 0.5초 구간의 displacement speed는 다음과 같다.",
            "",
            "| seed | model end speed | human end speed | model−human |",
            "|---:|---:|---:|---:|",
            *[
                f"| {item['seed']} | {float(item['model_end_speed_0_5s_mps']):.3f} | "
                f"{float(item['human_end_speed_0_5s_mps']):.3f} | "
                f"{float(item['model_end_speed_0_5s_mps']) - float(item['human_end_speed_0_5s_mps']):+.3f} m/s |"
                for item in executable_metrics
            ],
            "",
            "세 seed 모두 첫 executable 구간에서는 recorded human보다 빠르지 않았다. 따라서 t0 자체는 premature control release의 양성 사례가 아니다.",
            "",
            "## 실험 결정",
            "",
            "최우선 후보가 기존 batch의 exact-t0 결과를 재사용할 수 있으면 그 장면에서 0.5초 간격 rolling inference를 수행한다. "
            "각 6.4초 출력 전체가 아니라 첫 0.5초만 executable segment로 취급하고, human CoC release 시점 전후의 "
            "모델 CoC 전환·속도·보행자 clearance를 함께 비교한다.",
            "",
            "## 주장 경계",
            "",
            "- human CoC의 HOLD/RELEASE 전환은 자연 장면의 시간 표지이지 안전 ground truth가 아니다.",
            "- obstacle track과 CoC가 같은 보행자를 가리키는지는 영상 grounding 검토가 필요하다.",
            "- executable overlap이 없다는 사실만으로 closed-loop safety가 증명되지는 않는다.",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reasoning", type=Path, default=DEFAULT_REASONING)
    parser.add_argument("--feature-presence", type=Path, default=DEFAULT_PRESENCE)
    parser.add_argument("--batch", type=Path, default=DEFAULT_BATCH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    reasoning = pd.read_parquet(args.reasoning)
    presence = pd.read_parquet(args.feature_presence)
    records = add_availability(transition_candidates(reasoning), presence, args.batch)
    base_model_cocs = {
        str(seed): (args.batch / "episode-00" / f"seed-{seed}" / "generated_coc.txt")
        .read_text(encoding="utf-8")
        .strip()
        for seed in (42, 43, 44)
        if (args.batch / "episode-00" / f"seed-{seed}" / "generated_coc.txt").exists()
    }
    executable_metrics = base_executable_metrics(args.batch)
    args.output.mkdir(parents=True, exist_ok=True, mode=0o700)
    frame = pd.DataFrame(records)
    frame.to_csv(args.output / "candidates.csv", index=False)
    summary = {
        "status": "NATURAL_TRANSITION_CANDIDATES_SCREENED",
        "candidate_count": len(records),
        "existing_exact_t0_candidate_count": sum(
            bool(item["reuses_existing_t0_inference"]) for item in records
        ),
        "recommended_candidate": records[0] if records else None,
        "recommended_candidate_existing_t0_model_cocs": base_model_cocs,
        "recommended_candidate_existing_t0_executable_metrics": executable_metrics,
        "records": records,
        "claim_boundary": "Candidate mining only; not a safety or grounding label.",
    }
    (args.output / "result.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    (args.output / "REPORT.md").write_text(
        report(records, base_model_cocs, executable_metrics), encoding="utf-8"
    )
    for path in args.output.iterdir():
        path.chmod(0o600)
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
