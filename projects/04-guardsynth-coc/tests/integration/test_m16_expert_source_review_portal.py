"""Contracts for the M16 machine-assisted expert source review workbench."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest


ROOT = next(
    parent
    for parent in Path(__file__).resolve().parents
    if (parent / "PROJECT_REGISTRY.json").is_file()
)
RUN = ROOT / (
    "projects/04-guardsynth-coc/pipelines/cli/"
    "m16_source_review_portal/build_expert_source_review.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location("m16_expert_source_review", RUN)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class M16ExpertSourceReviewPortalTest(unittest.TestCase):
    def test_machine_proposal_is_explicitly_non_ground_truth(self) -> None:
        module = load_module()
        proposal = module.machine_visual_proposal(
            scene_slice="PEDESTRIAN_CYCLIST_YIELD",
            anchors=[{
                "x": 0.45,
                "y": 0.55,
                "source_category": "ACTOR",
                "temporal_fit": "NEAR_EVENT",
            }],
        )
        self.assertEqual(proposal["proposal_authority"], "EXPERT_CONFIRMATION_REQUIRED")
        self.assertEqual(proposal["confidence"], "LOW")
        self.assertIn("EGO_LANE_ZONE", proposal["polygons"])
        self.assertIn("CROSSING_CONFLICT_ZONE", proposal["polygons"])

    def test_stop_signal_does_not_infer_stopping_zone_from_signal_anchor(self) -> None:
        module = load_module()
        proposal = module.machine_visual_proposal(
            scene_slice="STOP_SIGNALS",
            anchors=[{
                "x": 0.45,
                "y": 0.30,
                "source_category": "CONTROL",
                "temporal_fit": "AT_EVENT",
            }],
        )
        self.assertIn("EGO_LANE_ZONE", proposal["polygons"])
        self.assertNotIn("STOP_LINE_STOPPING_ZONE", proposal["polygons"])

    def test_rendered_workbench_requires_expert_confirmation_and_exports(self) -> None:
        module = load_module()
        record = {
            "review_index": 1,
            "candidate_digest": "candidate-sha256:" + "a" * 64,
            "slice": "FOLLOWING_CUT_IN",
            "event_timestamp_us": 1_000_000,
            "contact_sheet_data_url": "data:image/jpeg;base64,YWJj",
            "contact_sheet_sha256": "b" * 64,
            "t0_overlay_data_url": "data:image/jpeg;base64,ZGVm",
            "t0_overlay_sha256": "c" * 64,
            "source_target_anchors": [],
            "unanchored_source_target_count": 1,
            "machine_visual_proposal": module.machine_visual_proposal(
                scene_slice="FOLLOWING_CUT_IN", anchors=[]
            ),
            "prior_observation_proposal": {
                "association": "CLEAR_VISIBLE",
                "temporal_observation": "NO_HAZARD_VISIBLE",
                "outcome": "NOMINAL",
                "provenance": "PRIOR_HUMAN_VIDEO_OBSERVATION",
            },
        }
        rendered = module.render_workbench([record], "input-set-sha256")
        self.assertIn("connect-src 'none'", rendered)
        self.assertIn("기계 표시는 정답이 아닙니다", rendered)
        self.assertIn("선행 관찰 초안", rendered)
        self.assertIn("전문가 확인", rendered)
        self.assertIn("CONFIRM_PROPOSALS", rendered)
        self.assertIn("GEOMETRY_CORRECTION", rendered)
        self.assertIn("semantic_pixel_polygons", rendered)
        self.assertIn("JSON 내보내기", rendered)
        self.assertIn("CSV 내보내기", rendered)
        self.assertIn("localStorage", rendered)
        self.assertIn("검토 화면으로 돌아가기", rendered)
        self.assertNotIn('id="country"', rendered)
        self.assertNotIn('id="jurisdiction"', rendered)
        self.assertNotIn('id="authority"', rendered)
        self.assertNotIn('id="calibration"', rendered)
        self.assertNotIn("clip_id", rendered)
        self.assertNotIn("/home/", rendered)


if __name__ == "__main__":
    unittest.main()
