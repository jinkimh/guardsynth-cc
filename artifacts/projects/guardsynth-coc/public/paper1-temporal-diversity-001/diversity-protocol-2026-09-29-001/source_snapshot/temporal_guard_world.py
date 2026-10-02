"""Temporal STOP-HOLD-RELEASE-GO micro-world."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Literal

import numpy as np
from PIL import Image, ImageDraw


Split = Literal["train", "validation", "test", "test_paraphrase", "test_unseen"]
Label = Literal["A", "B", "C", "D"]
LABELS: tuple[Label, ...] = ("A", "B", "C", "D")
COC_TEXT = "Yield to the crossing pedestrian, then proceed through the intersection."


@dataclass(frozen=True)
class TemporalCandidate:
    label: Label
    entry_time: float | None
    progress: float
    role: Literal["premature", "short_wait", "long_wait", "deadlock"]


@dataclass(frozen=True)
class TemporalScene:
    scene_id: int
    clear_time: float
    visual_seed: int
    candidates: tuple[TemporalCandidate, ...]


@dataclass(frozen=True)
class TemporalExample:
    scene: TemporalScene
    required_clear_duration: float
    contract_level: Literal["short", "long"]
    guard_text: str
    rich_coc_text: str
    logic_guard_text: str
    target: Label
    split: Split


def _fmt(value: float) -> str:
    return f"{value:.1f}"


def make_scene(scene_id: int, seed: int, split: Split) -> TemporalScene:
    rng = np.random.default_rng(seed * 1_000_003 + scene_id * 113)
    if split == "test_unseen":
        clear_time = float(rng.choice([2.5, 3.5, 4.5]))
        short_delay, long_delay = 0.8, 1.8
    else:
        clear_time = float(rng.choice([2.0, 3.0, 4.0]))
        short_delay, long_delay = 0.5, 1.5
    physical = [
        (clear_time - 0.5, 110.0, "premature"),
        (clear_time + short_delay, 100.0, "short_wait"),
        (clear_time + long_delay, 85.0, "long_wait"),
        (None, 0.0, "deadlock"),
    ]
    # Rotate labels so no semantic role has a fixed output token.
    shift = (scene_id + seed) % len(LABELS)
    labels = LABELS[shift:] + LABELS[:shift]
    candidates = tuple(
        TemporalCandidate(label, entry, progress, role)  # type: ignore[arg-type]
        for label, (entry, progress, role) in zip(labels, physical, strict=True)
    )
    return TemporalScene(scene_id, clear_time, seed * 100_003 + scene_id * 97, candidates)


def required_entry_time(example: TemporalExample) -> float:
    return example.scene.clear_time + example.required_clear_duration


def candidate_admissible(candidate: TemporalCandidate, example: TemporalExample) -> bool:
    return candidate.entry_time is None or candidate.entry_time + 1e-9 >= required_entry_time(example)


def target_for(scene: TemporalScene, required_duration: float) -> Label:
    admissible = [
        candidate
        for candidate in scene.candidates
        if candidate.entry_time is None
        or candidate.entry_time + 1e-9 >= scene.clear_time + required_duration
    ]
    return max(admissible, key=lambda candidate: candidate.progress).label


def _guard(duration: float, paraphrase: bool) -> str:
    if paraphrase:
        return (
            "Keep holding before the stop line until the pedestrian conflict zone has remained "
            f"unoccupied continuously for no less than {_fmt(duration)} s; only then may ego enter."
        )
    return (
        "Do not enter while the pedestrian conflict zone is occupied. After it becomes clear, "
        f"remain stopped for at least {_fmt(duration)} s before entering."
    )


def generate_temporal_examples(num_scenes: int, seed: int, split: Split) -> list[TemporalExample]:
    if num_scenes < 1:
        raise ValueError("num_scenes must be positive")
    offset = {
        "train": 0,
        "validation": 10_000,
        "test": 20_000,
        "test_paraphrase": 30_000,
        "test_unseen": 40_000,
    }[split]
    durations = (0.8, 1.8) if split == "test_unseen" else (0.5, 1.5)
    examples: list[TemporalExample] = []
    for local_id in range(num_scenes):
        scene = make_scene(offset + local_id, seed, split)
        for level, duration in zip(("short", "long"), durations, strict=True):
            guard = _guard(duration, split == "test_paraphrase")
            examples.append(
                TemporalExample(
                    scene=scene,
                    required_clear_duration=duration,
                    contract_level=level,  # type: ignore[arg-type]
                    guard_text=guard,
                    rich_coc_text=COC_TEXT + " " + guard,
                    logic_guard_text=(
                        "INVARIANT occupied(conflict_zone) -> ego_before_stop_line; "
                        f"RELEASE clear_duration_s >= {_fmt(duration)}; "
                        "FALLBACK uncertain(occupancy) -> HOLD"
                    ),
                    target=target_for(scene, duration),
                    split=split,
                )
            )
    return examples


def shuffled_guard_control(examples: list[TemporalExample], seed: int) -> list[TemporalExample]:
    rng = np.random.default_rng(seed)
    texts = [(e.guard_text, e.logic_guard_text, e.rich_coc_text) for e in examples]
    permutation = np.roll(rng.permutation(len(examples)), 1)
    return [
        replace(e, guard_text=texts[int(i)][0], logic_guard_text=texts[int(i)][1], rich_coc_text=texts[int(i)][2])
        for e, i in zip(examples, permutation, strict=True)
    ]


def candidate_description(candidate: TemporalCandidate) -> str:
    if candidate.entry_time is None:
        return f"Candidate {candidate.label}: remains stopped through the horizon; route progress 0 m."
    return (
        f"Candidate {candidate.label}: enters the intersection at t={_fmt(candidate.entry_time)} s "
        f"and completes the route; route progress {_fmt(candidate.progress)} m."
    )


def prompt_for(example: TemporalExample, mode: str) -> str:
    if mode not in {"COC_ONLY", "RICH_COC", "NATURAL_GUARD", "LOGIC_GUARD"}:
        raise ValueError(f"unknown mode {mode}")
    coc = example.rich_coc_text if mode == "RICH_COC" else COC_TEXT
    lines = [f"Requirement CoC: {coc}"]
    if mode == "NATURAL_GUARD":
        lines.append(f"Temporal safety guard: {example.guard_text}")
    elif mode == "LOGIC_GUARD":
        lines.append(f"Temporal safety guard: {example.logic_guard_text}")
    lines.extend(candidate_description(candidate) for candidate in sorted(example.scene.candidates, key=lambda c: c.label))
    lines.append(
        "The storyboard is ordered by time and shows when the conflict zone becomes clear. "
        "Select the admissible candidate with greatest route progress. Answer exactly A, B, C, or D."
    )
    return "\n".join(lines)


def render_storyboard(scene: TemporalScene, size: int = 224) -> Image.Image:
    image = Image.new("RGB", (size, size), (242, 242, 238))
    draw = ImageDraw.Draw(image)
    frames = [0.0, max(0.0, scene.clear_time - 1.0), scene.clear_time, scene.clear_time + 1.0]
    margin, gap = 5, 4
    width = (size - margin * 2 - gap * 3) // 4
    top, bottom = 25, size - 10
    for index, time_value in enumerate(frames):
        left = margin + index * (width + gap)
        right = left + width
        draw.rectangle((left, top, right, bottom), fill=(80, 83, 85), outline=(20, 20, 20))
        stop_y = bottom - 32
        draw.line((left + 3, stop_y, right - 3, stop_y), fill=(250, 250, 250), width=3)
        draw.rectangle((left + width // 2 - 5, bottom - 25, left + width // 2 + 5, bottom - 7), fill=(40, 125, 220))
        occupied = time_value < scene.clear_time - 1e-9
        if occupied:
            ped_x = left + width // 2
            ped_y = top + 65
            draw.ellipse((ped_x - 4, ped_y - 12, ped_x + 4, ped_y - 4), fill=(245, 205, 165))
            draw.line((ped_x, ped_y - 3, ped_x, ped_y + 12), fill=(145, 35, 150), width=4)
            state = "OCCUPIED"
            state_color = (255, 105, 105)
        else:
            state = "CLEAR"
            state_color = (105, 245, 130)
        draw.text((left + 2, 5), f"t={_fmt(time_value)}s", fill=(15, 15, 15))
        draw.text((left + 2, top + 5), state, fill=state_color)
    return image
