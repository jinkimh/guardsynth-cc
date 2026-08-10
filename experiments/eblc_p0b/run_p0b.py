"""Compatibility entry point for the reorganized P0b CLI pipeline."""

from cli.pipelines.eblc.p0b_schema_bcv.run import *  # noqa: F401,F403
from cli.pipelines.eblc.p0b_schema_bcv.run import main


if __name__ == "__main__":
    raise SystemExit(main())
