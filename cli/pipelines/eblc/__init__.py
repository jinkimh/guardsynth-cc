"""Compatibility namespace for platform-owned EBLC CLI pipelines."""

from pathlib import Path


__path__ = [str(Path(__file__).resolve().parents[3] / "platforms/eblc-bcv/pipelines/cli")]
