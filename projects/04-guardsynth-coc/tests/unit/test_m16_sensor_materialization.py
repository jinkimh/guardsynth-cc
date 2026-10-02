"""Unit contract for selective M16 sensor materialization."""

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
    "materialize_sensor_shortlist.py"
)
SPEC = importlib.util.spec_from_file_location("m16_sensor_materialization", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class M16SensorMaterializationTest(unittest.TestCase):
    def test_target_path_is_deidentified(self) -> None:
        digest = "candidate-sha256:" + "a" * 64
        path = MODULE.target_relative_path(
            digest,
            "camera_front_wide_120fov",
            "video",
            "private-clip.camera_front_wide_120fov.mp4",
        )
        self.assertNotIn("private-clip", path.as_posix())
        self.assertEqual(path.suffix, ".mp4")
        self.assertTrue(path.as_posix().startswith("event-" + "a" * 64))

    def test_locked_shortlist_builds_228_packages_without_raw_output_paths(self) -> None:
        records = []
        for index in range(59):
            records.append({
                "clip_id": f"private-{index}",
                "chunk": index if index < 57 else 0,
                "candidate_digest": f"candidate-sha256:{index + 1:064x}",
                "event_timestamp_us": 1_000_000,
                "shortlist_slice": "STOP_SIGNALS",
            })
        shortlist = {
            "required_sensor_features": [
                "camera_front_wide_120fov",
                "egomotion",
                "egomotion.offline",
                "obstacle.offline",
            ],
            "records": records,
        }
        work = MODULE.build_work_items(shortlist)
        self.assertEqual(len(work), 228)
        self.assertEqual({item["feature"] for item in work}, set(MODULE.FEATURE_ORDER))

    def test_reserve_shortlist_accepts_variable_candidate_count(self) -> None:
        records = [
            {
                "clip_id": f"reserve-{index}",
                "chunk": index,
                "candidate_digest": f"candidate-sha256:{index + 1:064x}",
                "event_timestamp_us": 1_000_000,
                "shortlist_slice": "FOLLOWING_CUT_IN",
            }
            for index in range(2)
        ]
        work = MODULE.build_work_items({
            "selected_unique_clip_count": 2,
            "estimated_sensor_package_count": 8,
            "required_sensor_features": [
                "camera_front_wide_120fov",
                "egomotion",
                "egomotion.offline",
                "obstacle.offline",
            ],
            "records": records,
        })
        self.assertEqual(len(work), 8)


if __name__ == "__main__":
    unittest.main()
