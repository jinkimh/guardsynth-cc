from __future__ import annotations

from pathlib import Path
import sys
import unittest

import numpy as np
from scipy.spatial.transform import RigidTransform, Rotation


ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "PROJECT_REGISTRY.json").is_file())
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from guard_synth.nvidia_source_bundle import (
    build_coordinate_transform,
    build_vehicle_binding,
)


class NvidiaSourceBundleTest(unittest.TestCase):
    def test_event_pose_is_expressed_in_t0_ego_frame(self) -> None:
        t0 = RigidTransform.from_components(
            rotation=Rotation.identity(), translation=np.array([10.0, 0.0, 0.0])
        )
        event = RigidTransform.from_components(
            rotation=Rotation.identity(), translation=np.array([13.0, 2.0, 0.0])
        )
        record = build_coordinate_transform(
            transform=t0.inv() * event,
            source_frame="dataset_rig_at_event",
            target_frame="ego_at_model_t0",
            event_timestamp_us=3_000_000,
            t0_us=1_000_000,
            evidence_refs=("dataset:egomotion", "devkit:local-frame"),
        )

        self.assertEqual(record["status"], "AVAILABLE_SOURCE_LINKED")
        self.assertEqual(record["matrix_4x4"][0][3], 3.0)
        self.assertEqual(record["matrix_4x4"][1][3], 2.0)
        self.assertLessEqual(record["inverse_closure_max_abs_error"], 1e-9)

    def test_binding_is_exact_to_recorded_configuration_not_vin(self) -> None:
        first = build_vehicle_binding(
            clip_id_sha256="a" * 64,
            dataset_revision="revision",
            platform_class="platform",
            radar_config="radar",
            vehicle_dimensions={"length_m": 5.0, "width_m": 2.0},
            calibration_digest="b" * 64,
            evidence_refs=("dataset:metadata", "dataset:calibration"),
        )
        second = build_vehicle_binding(
            clip_id_sha256="a" * 64,
            dataset_revision="revision",
            platform_class="platform",
            radar_config="different-radar",
            vehicle_dimensions={"length_m": 5.0, "width_m": 2.0},
            calibration_digest="b" * 64,
            evidence_refs=("dataset:metadata", "dataset:calibration"),
        )

        self.assertEqual(
            first["binding_scope"], "DATASET_CLIP_RIG_CONFIGURATION_NOT_VIN"
        )
        self.assertNotEqual(first["vehicle_binding_key"], second["vehicle_binding_key"])


if __name__ == "__main__":
    unittest.main()
