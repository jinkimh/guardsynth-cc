"""Compatibility import for the canonical GuardSynth project package.

New code belongs in ``projects/04-guardsynth-coc/src/guard_synth``.
"""

from pathlib import Path


_CANONICAL = (
    Path(__file__).resolve().parents[2]
    / "projects/04-guardsynth-coc/src/guard_synth"
)
__path__ = [str(_CANONICAL)]
exec(compile((_CANONICAL / "__init__.py").read_text(encoding="utf-8"), str(_CANONICAL / "__init__.py"), "exec"))
