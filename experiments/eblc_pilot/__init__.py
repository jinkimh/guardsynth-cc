"""Compatibility namespace for the historical EBLC P0a pilot."""

from pathlib import Path


__path__ = [str(Path(__file__).resolve().parents[2] / "platforms/eblc-bcv/experiments/eblc_pilot")]
