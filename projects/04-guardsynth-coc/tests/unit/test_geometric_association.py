from __future__ import annotations

from copy import deepcopy
import sys
from pathlib import Path
import unittest


ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "PROJECT_REGISTRY.json").is_file())
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from guard_synth.geometric_association import build_geometric_set_association


def candidate(track_hash: str, y_values: list[float]) -> dict:
    return {
        "track_id_sha256": track_hash,
        "label_class": "person",
        "track_samples": [
            {
                "timestamp_us": 1_000_000 + index * 100_000,
                "center_x_m": 10.0 + index * 0.1,
                "center_y_m": y,
                "half_extent_x_m": 0.3,
                "half_extent_y_m": 0.3,
            }
            for index, y in enumerate(y_values)
        ],
    }


class GeometricSetAssociationTest(unittest.TestCase):
    def test_all_and_only_corridor_overlapping_tracks_form_target_set(self) -> None:
        evidence = build_geometric_set_association(
            scene_ref="scene-001",
            event_timestamp_us=1_100_000,
            candidates=[
                candidate("a" * 64, [1.2, 0.9, 0.4]),
                candidate("b" * 64, [1.4, 1.1, 0.8]),
                candidate("c" * 64, [3.0, 2.9, 2.8]),
            ],
            ego_half_width_m=1.0,
            ego_front_extent_m=4.0,
            evidence_refs=["restricted-sha256:" + "d" * 64 + "#/event"],
        )

        self.assertEqual(evidence["status"], "AVAILABLE_SOURCE_LINKED")
        self.assertEqual(evidence["association_cardinality"], 2)
        self.assertEqual(
            evidence["associated_track_id_sha256"], ["a" * 64, "b" * 64]
        )
        self.assertEqual(evidence["excluded_track_id_sha256"], ["c" * 64])
        self.assertEqual(evidence["target_kind"], "SET")
        self.assertEqual(evidence["zone"]["coordinate_frame"], "dataset_rig")
        self.assertFalse(evidence["crosswalk_or_legal_zone_claimed"])
        self.assertFalse(evidence["collision_prediction_claimed"])

    def test_no_overlap_fails_closed(self) -> None:
        evidence = build_geometric_set_association(
            scene_ref="scene-001",
            event_timestamp_us=1_100_000,
            candidates=[candidate("a" * 64, [3.0, 2.8, 2.6])],
            ego_half_width_m=1.0,
            ego_front_extent_m=4.0,
            evidence_refs=["source:event"],
        )
        self.assertEqual(evidence["status"], "REVIEW_REQUIRED")
        self.assertEqual(evidence["reason_code"], "NO_GEOMETRIC_CORRIDOR_ASSOCIATION")

    def test_invalid_track_hash_is_rejected(self) -> None:
        bad = candidate("raw-track-id", [0.5])
        with self.assertRaisesRegex(ValueError, "INVALID_TRACK_ID_SHA256"):
            build_geometric_set_association(
                scene_ref="scene-001",
                event_timestamp_us=1_000_000,
                candidates=[bad],
                ego_half_width_m=1.0,
                ego_front_extent_m=4.0,
                evidence_refs=["source:event"],
            )

    def test_missing_extent_is_not_invented(self) -> None:
        bad = candidate("a" * 64, [0.5])
        del bad["track_samples"][0]["half_extent_y_m"]
        with self.assertRaisesRegex(ValueError, "MISSING_TRACK_EXTENT"):
            build_geometric_set_association(
                scene_ref="scene-001",
                event_timestamp_us=1_000_000,
                candidates=[bad],
                ego_half_width_m=1.0,
                ego_front_extent_m=4.0,
                evidence_refs=["source:event"],
            )

    def test_input_is_not_mutated(self) -> None:
        candidates = [candidate("a" * 64, [0.5, 0.2])]
        before = deepcopy(candidates)
        build_geometric_set_association(
            scene_ref="scene-001",
            event_timestamp_us=1_000_000,
            candidates=candidates,
            ego_half_width_m=1.0,
            ego_front_extent_m=4.0,
            evidence_refs=["source:event"],
        )
        self.assertEqual(candidates, before)


if __name__ == "__main__":
    unittest.main()
