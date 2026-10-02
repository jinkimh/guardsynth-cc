"""Contracts for the image-embedded M16 source-review workbench."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest


ROOT = next(
    parent
    for parent in Path(__file__).resolve().parents
    if (parent / "PROJECT_REGISTRY.json").is_file()
)
RUN = ROOT / (
    "projects/04-guardsynth-coc/pipelines/cli/"
    "m16_source_review_portal/run.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location("m16_source_review_portal", RUN)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class M16SourceReviewPortalTest(unittest.TestCase):
    def test_rendered_workbench_is_restricted_self_contained_and_exportable(self) -> None:
        module = load_module()
        record = {
            "review_index": 1,
            "candidate_digest": "candidate-sha256:" + "a" * 64,
            "slice": "FOLLOWING_CUT_IN",
            "country": "Example Country",
            "association_precheck_status": (
                "REVIEWABLE_ACTOR_ASSOCIATION_LANE_MISSING"
            ),
            "geometry_source_required": True,
            "source_observation_counts": {
                "relevant_agent_keypoint_count": 1,
                "zone_keypoint_count": 0,
                "control_keypoint_count": 0,
                "obstacle_track_count_within_500ms": 3,
            },
            "event_timestamp_us": 1_000_000,
            "image_data_url": "data:image/jpeg;base64,YWJj",
            "image_sha256": "b" * 64,
            "frame_offsets_s": [-1.0, -0.5, 0.0, 0.5, 1.0],
        }
        rendered = module.render_workbench([record], "packet-sha256")
        self.assertIn("connect-src 'none'", rendered)
        self.assertIn("data:image/jpeg;base64,YWJj", rendered)
        self.assertIn("JSON 내보내기", rendered)
        self.assertIn("CSV 내보내기", rendered)
        self.assertIn("FOLLOWING_CUT_IN", rendered)
        self.assertIn("visual_association_observation", rendered)
        self.assertIn("visual_temporal_observation", rendered)
        self.assertIn("NOT_OBSERVABLE", rendered)
        self.assertIn(".sheet.zoomed", rendered)
        self.assertIn("이미지를 클릭하면 크게", rendered)
        self.assertIn('id="closeZoom"', rendered)
        self.assertIn("검토 화면으로 돌아가기", rendered)
        self.assertIn('document.addEventListener("change"', rendered)
        self.assertIn('window.addEventListener("pagehide",save)', rendered)
        self.assertIn("답변 요령", rendered)
        self.assertIn("검토 전 필독", rendered)
        self.assertIn("특정 대상을 자동으로 지정하지 않습니다", rendered)
        self.assertIn("보행자·자전거·휠체어·스쿠터", rendered)
        self.assertIn("전방 차량의 제동등은 STOP_SIGNALS 대상이 아닙니다", rendered)
        self.assertIn("위험 발생·해제·재활성화", rendered)
        self.assertIn("추측하지 마십시오", rendered)
        self.assertNotIn("답하지 않는 항목", rendered)
        self.assertNotIn("iframe 저장 제한", rendered)
        self.assertNotIn("별도 curator 단계", rendered)
        self.assertNotIn("Example Country", rendered)
        self.assertNotIn("countryFilter", rendered)
        self.assertNotIn("geometry_evidence_ref", rendered)
        self.assertNotIn("transform_evidence_ref", rendered)
        self.assertNotIn("authority_evidence_ref", rendered)
        self.assertNotIn("rule_precondition_decision", rendered)
        self.assertNotIn("rule_exception_decision", rendered)
        self.assertNotIn("rule_applicability_evidence_ref", rendered)
        self.assertNotIn("review_artifact_ref", rendered)
        self.assertNotIn("SOURCE_COMPLETE_CANDIDATE", rendered)
        self.assertNotIn("/home/", rendered)
        self.assertNotIn("file://", rendered)

    def test_output_must_be_new_restricted_owner_scoped_artifact(self) -> None:
        module = load_module()
        with TemporaryDirectory() as directory:
            outside = Path(directory) / "outside"
            with self.assertRaisesRegex(ValueError, "RESTRICTED_OWNER_SCOPED"):
                module.validate_output_dir(outside)

    def test_review_record_resolution_rejects_unmapped_candidate(self) -> None:
        module = load_module()
        packet = {
            "records": [{
                "candidate_digest": "candidate-sha256:" + "a" * 64,
                "slice": "STOP_SIGNALS",
                "country": "Example Country",
                "association_precheck_status": (
                    "REVIEWABLE_CONTROL_ASSOCIATION_LANE_MISSING"
                ),
                "geometry_source_required": True,
                "source_observation_counts": {},
            }]
        }
        with self.assertRaisesRegex(ValueError, "REVIEW_CANDIDATE_SOURCE_MISSING"):
            module.resolve_review_records(packet, {"records": []}, {"records": []})

    def test_resolved_reviewer_record_excludes_curator_only_context(self) -> None:
        module = load_module()
        digest = "candidate-sha256:" + "a" * 64
        packet = {
            "record_count": 60,
            "records": [
                {
                    "candidate_digest": digest if index == 0 else f"candidate-{index}",
                    "slice": "STOP_SIGNALS",
                    "country": "Example Country",
                    "association_precheck_status": "REVIEWABLE_CONTROL_ASSOCIATION_LANE_MISSING",
                    "geometry_source_required": True,
                    "source_observation_counts": {},
                }
                for index in range(60)
            ],
        }
        primary = {
            "records": [
                {
                    "candidate_digest": item["candidate_digest"],
                    "event_timestamp_us": index,
                }
                for index, item in enumerate(packet["records"])
            ]
        }
        records = module.resolve_review_records(packet, primary, {"records": []})
        self.assertNotIn("country", records[0])
        self.assertNotIn("association_precheck_status", records[0])
        self.assertNotIn("geometry_source_required", records[0])
        self.assertNotIn("source_observation_counts", records[0])


if __name__ == "__main__":
    unittest.main()
