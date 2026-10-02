"""Unit contract for selective M16 calibration materialization."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest


ROOT = next(
    parent
    for parent in Path(__file__).resolve().parents
    if (parent / "PROJECT_REGISTRY.json").is_file()
)
MODULE_PATH = ROOT / (
    "projects/04-guardsynth-coc/pipelines/cli/m16_scene_acquisition/"
    "materialize_calibration_shortlist.py"
)
SPEC = importlib.util.spec_from_file_location("m16_calibration_materialization", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class M16CalibrationMaterializationTest(unittest.TestCase):
    def test_target_path_does_not_embed_clip_identifier(self) -> None:
        digest = "candidate-sha256:" + "a" * 64
        path = MODULE.target_relative_path(digest, "sensor_extrinsics.offline")
        self.assertNotIn("private-clip", path.as_posix())
        self.assertTrue(path.as_posix().startswith("event-" + "a" * 64))

    def test_locked_shortlist_builds_285_calibration_packages(self) -> None:
        records = [
            {
                "clip_id": f"private-{index}",
                "chunk": index if index < 57 else 0,
                "candidate_digest": f"candidate-sha256:{index + 1:064x}",
            }
            for index in range(59)
        ]
        work = MODULE.build_work_items({"records": records})
        self.assertEqual(len(work), 285)
        self.assertEqual({item["feature"] for item in work}, set(MODULE.FEATURES))

    def test_reserve_shortlist_accepts_variable_candidate_count(self) -> None:
        records = [
            {
                "clip_id": f"reserve-{index}",
                "chunk": index,
                "candidate_digest": f"candidate-sha256:{index + 1:064x}",
            }
            for index in range(2)
        ]
        work = MODULE.build_work_items({
            "selected_unique_clip_count": 2,
            "records": records,
        })
        self.assertEqual(len(work), 10)


if __name__ == "__main__":
    unittest.main()
