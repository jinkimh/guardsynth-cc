"""Compatibility namespace for historical EBLC P0b experiments."""

from pathlib import Path


__path__ = [str(Path(__file__).resolve().parents[2] / "platforms/eblc-bcv/experiments/eblc_p0b")]
