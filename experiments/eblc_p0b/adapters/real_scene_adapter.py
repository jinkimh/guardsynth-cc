"""Compatibility entry point for the restricted derived-scene adapter."""

from src.guard_synth_eblc.adapters.nvidia_derived_scene import *  # noqa: F401,F403
from cli.pipelines.eblc.restricted_scene_grounding.run import main


if __name__ == "__main__":
    raise SystemExit(main())
