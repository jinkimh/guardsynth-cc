"""Compatibility namespace for the Safety-Constrained CoC micro-world.

New code belongs in
``projects/01-safety-constrained-coc/experiments/contract_micro_world``.
"""

from pathlib import Path


__path__ = [
    str(
        Path(__file__).resolve().parents[2]
        / "projects/01-safety-constrained-coc/experiments/contract_micro_world"
    )
]
