import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from audit_scene_continuity import audit


class SceneContinuityAuditTest(unittest.TestCase):
    def test_local_metadata_does_not_support_inter_scene_connection(self) -> None:
        result = audit(
            Path("data/baseline/coc_nusc"),
            Path("data/restricted/nvidia_physicalai"),
        )
        self.assertFalse(
            result["conclusion"]["inter_scene_connection_supported_by_local_metadata"]
        )
        self.assertTrue(
            result["coc_nusc"]["egomotion_reset_summary"]["all_timestamps_start_at_zero"]
        )
        self.assertTrue(
            result["coc_nusc"]["egomotion_reset_summary"]["all_start_poses_near_zero"]
        )


if __name__ == "__main__":
    unittest.main()
