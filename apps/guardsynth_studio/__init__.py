"""GuardSynth Studio, owned by guardsynth-coc. No model calls on import."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
for relative in ("projects/04-guardsynth-coc/src", "platforms/eblc-bcv/src"):
    path = str(ROOT / relative)
    if path not in sys.path:
        sys.path.insert(0, path)

VERSION = "studio-v0.1"
