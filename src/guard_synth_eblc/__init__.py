"""Compatibility import for the canonical EBLC/BCV platform package.

New code belongs in ``platforms/eblc-bcv/src/guard_synth_eblc``.
"""

from pathlib import Path


_CANONICAL = (
    Path(__file__).resolve().parents[2]
    / "platforms/eblc-bcv/src/guard_synth_eblc"
)
__path__ = [str(_CANONICAL)]
exec(compile((_CANONICAL / "__init__.py").read_text(encoding="utf-8"), str(_CANONICAL / "__init__.py"), "exec"))
