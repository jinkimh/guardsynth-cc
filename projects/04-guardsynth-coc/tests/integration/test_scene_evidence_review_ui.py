from __future__ import annotations

import json
from pathlib import Path
import sys
import unittest

ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "PROJECT_REGISTRY.json").is_file())
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from guard_synth_eblc.schema_validation import validate


HTML_PATH = ROOT / "projects/04-guardsynth-coc/pipelines/cli/scene_evidence_review/scene_evidence_review.html"
SCHEMA_PATH = ROOT / "projects/04-guardsynth-coc/src/guard_synth/schemas/scene_evidence_review.schema.json"
EMBEDDER_PATH = ROOT / "projects/04-guardsynth-coc/pipelines/cli/scene_evidence_review/build_embedded.py"
IMAGE_ONLY_PATH = ROOT / "projects/04-guardsynth-coc/pipelines/cli/scene_evidence_review/image_only_scene_review.html"


class SceneEvidenceReviewUiTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.html = HTML_PATH.read_text(encoding="utf-8")
        cls.image_only_html = IMAGE_ONLY_PATH.read_text(encoding="utf-8")

    def test_html_is_self_contained_and_network_closed(self) -> None:
        self.assertIn("default-src 'none'", self.html)
        self.assertIn("connect-src 'none'", self.html)
        self.assertNotIn('src="http', self.html)
        self.assertNotIn('href="http', self.html)

    def test_three_accessible_synthetic_diagrams_exist(self) -> None:
        self.assertEqual(self.html.count('<svg viewBox="0 0 420 240"'), 3)
        self.assertEqual(self.html.count('role="img" aria-label='), 3)
        for title in ("target–zone association", "coordinate transform", "evidence-bound pipeline"):
            self.assertIn(title, self.html)

    def test_method_examples_and_checklist_cover_failure_modes(self) -> None:
        for text in (
            "검토 방법", "검토 예제", "검토 항목과 증거", "적색 신호 · symbolic stop",
            "보행자 한 명 · zone 두 개", "geometry는 있으나 transform 미검증",
            "동적 정지거리 · assurance 없음",
        ):
            self.assertIn(text, self.html)

    def test_all_evidence_groups_are_present(self) -> None:
        for legend in (
            "A. Hazard fact", "B. Target–zone/lane association",
            "C. Geometry·frame·transform", "D. Rule applicability",
            "E. Numeric constraint와 vehicle assurance",
            "F. Lifecycle 관측 가능성", "G. 판정",
        ):
            self.assertIn(legend, self.html)

    def test_fail_closed_triage_precedence_is_explicit(self) -> None:
        conflict = self.html.index('if(conflicts)return {decision:"CONFLICT"')
        unsupported = self.html.index('if(unsupported)return {decision:"UNSUPPORTED"')
        review = self.html.index('return {decision:"REVIEW_REQUIRED"')
        complete = self.html.index('return {decision:"SOURCE_COMPLETE"')
        self.assertLess(conflict, unsupported)
        self.assertLess(unsupported, review)
        self.assertLess(review, complete)
        self.assertIn("INVALID_SOURCE_COMPLETE_OVERRIDE", self.html)
        self.assertIn("MISSING_DECISION_OVERRIDE_REASON", self.html)
        self.assertIn("MISSING_REVIEWER_ID", self.html)

    def test_numeric_assurance_is_conditionally_required(self) -> None:
        self.assertIn("NOT_REQUIRED_SYMBOLIC_ONLY", self.html)
        self.assertIn("REQUIRED_PRESENT", self.html)
        self.assertIn("INCOMPLETE_NUMERIC_ASSURANCE_EVIDENCE", self.html)
        self.assertIn("MISSING_VEHICLE_ASSURANCE_PROFILE", self.html)

    def test_local_image_bytes_are_not_exported(self) -> None:
        self.assertIn("URL.createObjectURL(file)", self.html)
        self.assertIn("image_bytes_included:false", self.html)
        self.assertIn("JSON.stringify(payload", self.html)
        self.assertIn("guardsynth_scene_evidence_review.csv", self.html)

    def test_batch_and_folder_import_create_review_cards(self) -> None:
        self.assertIn('id="batchImages"', self.html)
        self.assertIn('id="folderImages"', self.html)
        self.assertIn("webkitdirectory directory multiple", self.html)
        self.assertIn("function importFiles(fileList)", self.html)
        self.assertIn("for(const file of files)", self.html)
        self.assertIn("function configureImageMode()", self.html)
        self.assertIn("별도 갤러리나 이미지 선택은 필요하지 않습니다", self.html)

    def test_embedded_builder_is_restricted_and_has_one_marker(self) -> None:
        self.assertEqual(
            self.html.count(
                '<div id="embeddedImageStore" hidden aria-hidden="true"></div><!-- restricted packager replaces this exact element -->'
            ),
            1,
        )
        self.assertIn('document.querySelectorAll("#embeddedImageStore img[data-name]")', self.html)
        self.assertIn("guardsynth-scene-evidence-review-v01-embedded-", self.html)
        self.assertNotIn('name="local_image"', self.html)
        builder = EMBEDDER_PATH.read_text(encoding="utf-8")
        self.assertIn('ROOT / "artifacts/results/restricted"', builder)
        self.assertIn("if not output_dir.is_relative_to", builder)
        self.assertIn('"input_class": "LICENSE_RESTRICTED"', builder)
        self.assertIn('"image_bytes_in_json_csv_export": False', builder)
        self.assertIn('class="embedded-scene-image"', builder)

    def test_export_envelope_conforms_to_schema(self) -> None:
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        validate(
            {
                "review_version": "guardsynth-scene-evidence-review-v0.1",
                "exported_at": "2026-08-10T00:00:00Z",
                "image_bytes_included": False,
                "reviewer_id": "reviewer-A",
                "records": [],
            },
            schema,
        )

    def test_image_only_review_does_not_request_unobservable_metadata(self) -> None:
        for field in (
            "hazard_evidence_ref", "timestamp_evidence_ref", "target_id",
            "track_evidence_ref", "zone_id", "geometry_evidence_ref",
            "coordinate_frame", "transform_evidence_ref",
        ):
            self.assertNotIn(f'name="{field}"', self.image_only_html)
        self.assertIn('row.metadata_availability="NOT_AVAILABLE_FROM_IMAGE"', self.image_only_html)
        self.assertIn('row.contract_readiness="REVIEW_REQUIRED"', self.image_only_html)
        self.assertNotIn("SOURCE_COMPLETE</option>", self.image_only_html)

    def test_image_only_review_has_broad_multi_select_scene_options(self) -> None:
        for option in (
            "PEDESTRIAN", "CYCLIST_MICROMOBILITY", "CROSSWALK", "INTERSECTION_TURN",
            "TRAFFIC_SIGNAL", "STOP_YIELD_SIGN", "FOLLOWING", "CUT_IN_MERGE",
            "STATIC_OBSTACLE", "CONSTRUCTION_WORKER", "OCCLUSION", "NOMINAL_CLEAR",
            "OTHER", "CANNOT_TELL",
        ):
            self.assertIn(f'value="{option}"', self.image_only_html)
        self.assertIn('type="checkbox" name="scene_tags"', self.image_only_html)

    def test_image_only_embedded_images_attach_one_per_review_card(self) -> None:
        self.assertIn('document.querySelectorAll("#embeddedImageStore img[data-name]")', self.image_only_html)
        self.assertIn("for(const item of embeddedImages)", self.image_only_html)
        self.assertIn("const card=makeReview(null);attach(card,item.name,item.data_url,false)", self.image_only_html)
        self.assertNotIn('name="local_image"', self.image_only_html)

    def test_image_only_scene_image_uses_full_card_width_without_height_cap(self) -> None:
        self.assertIn("main{width:100%", self.image_only_html)
        self.assertIn(".image-form{display:block}", self.image_only_html)
        self.assertIn(".preview{width:100%", self.image_only_html)
        self.assertIn(".preview img{display:block;width:100%;height:auto", self.image_only_html)
        self.assertNotIn("max-height:560px", self.image_only_html)

    def test_image_only_review_contains_one_non_normative_worked_example(self) -> None:
        for text in (
            "SYNTHETIC_REVIEW_EXAMPLE_001", "실제 장면의 정답이 아닙니다",
            "ROAD_USER_APPROACHING_CONFLICT_AREA", "CROSSWALK_VISIBLE",
            "CANNOT_INFER_FROM_IMAGE", "VISUAL_HAZARD_CANDIDATE",
            "계약 준비도:", "REVIEW_REQUIRED",
        ):
            self.assertIn(text, self.image_only_html)
        self.assertEqual(self.image_only_html.count("SYNTHETIC_REVIEW_EXAMPLE_001"), 1)

    def test_image_only_spatial_questions_define_their_observation_scope(self) -> None:
        for text in (
            "실제 충돌을 예측하거나 확정하는 항목이 아닙니다",
            "관련 이동 영역 후보",
            "공간이 화면에서 식별된다는 뜻일 뿐",
            "대표 공간 하나를 고르고 나머지는 메모에 적습니다",
            "관련 대상과 영역의 관계",
            "관련 대상의 몸체·차체가 장애물에 가려진 정도",
        ):
            self.assertIn(text, self.image_only_html)
        self.assertIn('<option value="UNOBSTRUCTED">가림 없음', self.image_only_html)
        self.assertIn('raw==="NONE_VISIBLE"?"UNOBSTRUCTED"', self.image_only_html)

    def test_image_only_temporal_change_has_an_explicit_subject_and_frame_scope(self) -> None:
        for text in (
            "관련 대상의 프레임 간 변화",
            "동일한 관련 대상을 시간순으로 비교합니다",
            "ego나 화면 전체의 변화가 아닙니다",
            "프레임 순서·대상 대응·변화를 판단할 수 없음",
            "실제 trajectory가 아닙니다",
        ):
            self.assertIn(text, self.image_only_html)


if __name__ == "__main__":
    unittest.main()
