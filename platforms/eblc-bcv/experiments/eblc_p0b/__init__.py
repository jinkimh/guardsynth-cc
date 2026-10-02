"""Compatibility namespace for the preserved EBLC-P0B experiment."""

from pathlib import Path

from cli.solver_runtime import configure_project_z3


ROOT = Path(__file__).resolve().parents[2]
Z3_RUNTIME = configure_project_z3(ROOT)

from src.guard_synth_eblc import COMPILER_VERSION, SCHEMA_VERSION, SEMANTICS_VERSION

__all__ = ["COMPILER_VERSION", "SCHEMA_VERSION", "SEMANTICS_VERSION", "Z3_RUNTIME"]
