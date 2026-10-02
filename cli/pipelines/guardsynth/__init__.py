"""Compatibility namespace for project-owned GuardSynth CLI pipelines."""

from pathlib import Path


__path__ = [str(Path(__file__).resolve().parents[3] / "projects/04-guardsynth-coc/pipelines/cli")]
