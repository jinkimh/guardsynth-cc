"""Integration contract for the M16 post-review source-closure audit."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest


ROOT = next(
    parent
    for parent in Path(__file__).resolve().parents
    if (parent / "PROJECT_REGISTRY.json").is_file()
)
PIPELINE = ROOT / "projects/04-guardsynth-coc/pipelines/cli/m16_scene_acquisition"
if str(PIPELINE) not in sys.path:
    sys.path.insert(0, str(PIPELINE))


NCORE_SOURCE = '''
# The non-offline (raw) variants of these features are currently not supported
REQUIRED_OFFLINE_FEATURES: list[str] = [
    "egomotion",
    "sensor_extrinsics",
    "camera_intrinsics",
    "lidar_intrinsics",
]
def _prefer_offline_feature(self, base_name: str) -> str:
    offline = f"{base_name}.offline"
    if offline in self._feature_names:
        return offline
    return base_name
'''


class M16PostReviewSourceClosurePipelineTest(unittest.TestCase):
    def test_real_98_event_inputs_are_reaudited_without_source_promotion(self) -> None:
        from finalize_post_review_source_closure import execute

        with TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "data_provider.py"
            source.write_text(NCORE_SOURCE, encoding="utf-8")
            restricted = root / "restricted"
            public = root / "public"
            commit = "a" * 40
            result = execute(
                restricted_output_dir=restricted,
                public_output_dir=public,
                run_id="m16-post-review-source-closure-test-v1",
                ncore_source_path=source,
                ncore_commit_sha=commit,
                ncore_source_url=(
                    f"https://github.com/NVIDIA/ncore/blob/{commit}/"
                    "tools/data_converter/pai/data_provider.py"
                ),
            )
            self.assertEqual(result["classified_event_count"], 98)
            self.assertEqual(result["human_observation_completed_count"], 60)
            self.assertEqual(result["materialized_unique_clip_count"], 81)
            self.assertEqual(result["calibration_variant_selection_closed_count"], 98)
            self.assertEqual(result["verified_coordinate_transform_count"], 0)
            self.assertEqual(result["new_source_complete_8_of_8_count"], 0)
            self.assertEqual(result["eligible_scene_count"], 1)
            self.assertEqual(result["total_scene_shortfall"], 59)
            self.assertFalse(result["annotation_start_allowed"])
            self.assertEqual(
                json.loads((restricted / "POST_REVIEW_SOURCE_CLOSURE_AUDIT.json").read_text())["records"][0]["source_complete"],
                False,
            )
            public_text = "\n".join(
                path.read_text(encoding="utf-8")
                for path in public.iterdir()
                if path.suffix in {".json", ".md"}
            )
            self.assertNotIn("candidate-sha256", public_text)
            self.assertNotIn("reviewer_id", public_text)
            self.assertNotIn("/home/", public_text)
            manifest = json.loads((restricted / "RUN_MANIFEST.json").read_text())
            self.assertEqual(
                manifest["source_hashes"]["nvidia_ncore_data_provider"],
                hashlib.sha256(source.read_bytes()).hexdigest(),
            )


if __name__ == "__main__":
    unittest.main()
