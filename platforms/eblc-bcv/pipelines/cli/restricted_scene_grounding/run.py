"""CLI for restricted derived-scene grounding without raw data copying."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


from cli.project_paths import project_root

ROOT = project_root(__file__)
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from guard_synth_eblc.adapters.nvidia_derived_scene import DEFAULT_RUN_ID, write_restricted_run


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Adapt existing restricted derived scenes into partial EBLC context records."
    )
    parser.add_argument("--project-root", type=Path, default=ROOT)
    parser.add_argument("--run-id", default=DEFAULT_RUN_ID)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    project_root = args.project_root.resolve()
    output = write_restricted_run(project_root, args.run_id)
    print(json.dumps({
        "status": "PARTIAL_REAL_SCENE_CONTEXT_ADAPTER_EXECUTED",
        "output": str(output.relative_to(project_root)),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
