"""Integration contracts for the M16 geometry candidate workbench."""

from __future__ import annotations

import csv
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


class M16GeometryCandidatePipelineTest(unittest.TestCase):
    def test_workbench_is_curator_only_and_navigation_safe(self) -> None:
        from generate_geometry_candidates import render_workbench

        html = render_workbench(
            [{
                "review_index": 1,
                "candidate_digest": "candidate-sha256:" + "a" * 64,
                "slice": "STOP_SIGNALS",
                "event_timestamp_us": 1_000_000,
                "source_video_sha256": "b" * 64,
                "t0_source_pixel_sha256": "c" * 64,
                "t0_overlay_sha256": "d" * 64,
                "contact_sheet_data_url": "data:image/jpeg;base64,AA==",
                "t0_overlay_data_url": "data:image/jpeg;base64,AA==",
            }],
            manifest_sha256="e" * 64,
        )
        self.assertIn("Curator ID", html)
        self.assertIn("STOP_LINE_STOPPING_ZONE", html)
        self.assertIn('id="zoneButtons"', html)
        self.assertIn('data-zone-label', html)
        self.assertIn('aria-pressed', html)
        self.assertIn('id="correctionPanel"', html)
        self.assertIn('id="derivedDisposition"', html)
        self.assertIn('id="canvasFinishShape"', html)
        self.assertIn("finishCurrentShape", html)
        self.assertIn("effectivePolygons", html)
        self.assertIn("3번째 점부터 polygon으로 자동 완료", html)
        self.assertIn("아직 저장되지 않음", html)
        self.assertIn("incompleteReviewIndices", html)
        self.assertIn("내보낼 수 없습니다", html)
        self.assertIn("검토 완료 ${done}/${records.length}", html)
        self.assertIn("s.assessment)}", html)
        self.assertIn("표시된 보정 polygon ${polygonCount}개 저장", html)
        self.assertIn("drafts", html)
        self.assertIn("두 영역은 같은 영상 위에 함께 표시되고 각각 저장됩니다", html)
        self.assertIn("보정이 필요할 때만", html)
        self.assertNotIn('<select id="activeLabel"', html)
        self.assertNotIn('<select id="disposition"', html)
        self.assertLess(html.index('id="assessment"'), html.index('id="correctionPanel"'))
        self.assertIn("localStorage", html)
        self.assertIn("source_complete_decision_included:false", html)
        self.assertNotIn("법규 적용을 선택", html)
        self.assertNotIn("iframe 저장 제한", html)

    def test_review_only_run_reuses_hash_verified_candidate_images(self) -> None:
        from build_geometry_review_workbench import execute

        with TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source"
            output = root / "output"
            image = b"review-image"
            image_hash = hashlib.sha256(image).hexdigest()
            (source / "geometry/event-001").mkdir(parents=True)
            (source / "geometry/event-001/contact-sheet.jpg").write_bytes(image)
            (source / "geometry/event-001/frame-p0000-overlay.jpg").write_bytes(image)
            records = []
            for index in range(1, 99):
                records.append({
                    "review_index": index,
                    "candidate_digest": f"candidate-sha256:{index:064x}",
                    "slice": "STOP_SIGNALS",
                    "event_timestamp_us": index,
                    "source_video_sha256": f"{index:064x}",
                    "contact_sheet_path": "geometry/event-001/contact-sheet.jpg",
                    "contact_sheet_sha256": image_hash,
                    "frames": [{
                        "offset_s": 0.0,
                        "source_pixel_sha256": f"{index + 1:064x}",
                        "overlay_path": "geometry/event-001/frame-p0000-overlay.jpg",
                        "overlay_sha256": image_hash,
                    }],
                })
            candidate_manifest = source / "GEOMETRY_CANDIDATE_MANIFEST.json"
            candidate_manifest.write_text(json.dumps({
                "classified_event_count": 98,
                "claim_scope": "TEST_SCOPE",
                "records": records,
            }), encoding="utf-8")
            candidate_hash = hashlib.sha256(candidate_manifest.read_bytes()).hexdigest()
            (source / "RUN_MANIFEST.json").write_text(json.dumps({
                "run_id": "source-v1",
                "output_hashes": {"geometry_candidate_manifest": candidate_hash},
            }), encoding="utf-8")

            result = execute(source_run_dir=source, output_dir=output, run_id="review-v2")

            self.assertEqual(result["candidate_count"], 98)
            html = (output / "geometry_candidate_workbench.html").read_text(encoding="utf-8")
            self.assertIn("guardsynth-m16-geometry-curator-workbench-v0.5", html)
            manifest = json.loads((output / "RUN_MANIFEST.json").read_text(encoding="utf-8"))
            self.assertEqual(
                manifest["input_hashes"]["geometry_candidate_manifest"],
                candidate_hash,
            )

    def test_uploaded_assessments_define_review_completion_without_inventing_polygons(self) -> None:
        from finalize_geometry_curator_review import execute

        with TemporaryDirectory() as directory:
            root = Path(directory)
            candidate = root / "candidate"
            output = root / "output"
            candidate.mkdir()
            candidate_records = []
            review_records = []
            for index in range(1, 99):
                digest = f"candidate-sha256:{index:064x}"
                source_hash = f"{index + 100:064x}"
                pixel_hash = f"{index + 200:064x}"
                overlay_hash = f"{index + 300:064x}"
                candidate_records.append({
                    "review_index": index,
                    "candidate_digest": digest,
                    "slice": "STOP_SIGNALS",
                    "event_timestamp_us": index,
                    "source_video_sha256": source_hash,
                    "frames": [{
                        "offset_s": 0.0,
                        "source_pixel_sha256": pixel_hash,
                        "overlay_sha256": overlay_hash,
                    }],
                })
                assessment = (
                    "ACCEPTABLE_VISIBLE_CANDIDATE"
                    if index == 1
                    else "MINOR_CORRECTION_REQUIRED"
                )
                review_records.append({
                    "candidate_digest": digest,
                    "review_index": index,
                    "slice": "STOP_SIGNALS",
                    "event_timestamp_us": index,
                    "source_video_sha256": source_hash,
                    "t0_source_pixel_sha256": pixel_hash,
                    "t0_overlay_sha256": overlay_hash,
                    "curator_id": "",
                    "machine_geometry_assessment": assessment,
                    "geometry_disposition": (
                        "CONFIRM_MACHINE_CANDIDATE"
                        if index == 1
                        else "USE_MANUAL_POLYGONS"
                    ),
                    "normalized_pixel_polygons": {},
                    "notes": "",
                    "source_complete_decision_included": False,
                })
            candidate_manifest_path = candidate / "GEOMETRY_CANDIDATE_MANIFEST.json"
            candidate_manifest_path.write_text(
                json.dumps({"records": candidate_records}), encoding="utf-8"
            )
            candidate_hash = hashlib.sha256(candidate_manifest_path.read_bytes()).hexdigest()
            (candidate / "RUN_MANIFEST.json").write_text(json.dumps({
                "output_hashes": {"geometry_candidate_manifest": candidate_hash}
            }), encoding="utf-8")
            review_json = root / "review.json"
            review_json.write_text(json.dumps({
                "manifest_sha256": candidate_hash,
                "records": review_records,
            }), encoding="utf-8")
            review_csv = root / "review.csv"
            csv_rows = [dict(record) for record in review_records]
            for row in csv_rows:
                row["normalized_pixel_polygons"] = "{}"
                row["source_complete_decision_included"] = "false"
            with review_csv.open("w", encoding="utf-8", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=list(csv_rows[0]))
                writer.writeheader()
                writer.writerows(csv_rows)

            result = execute(
                candidate_run_dir=candidate,
                review_json_path=review_json,
                review_csv_path=review_csv,
                output_dir=output,
                run_id="geometry-review-result-v1",
                curator_id="Jin Hyun Kim",
            )

            self.assertTrue(result["curator_review_complete"])
            self.assertEqual(result["curator_review_completed_count"], 98)
            self.assertEqual(result["accepted_machine_geometry_count"], 1)
            self.assertEqual(result["manual_correction_pending_count"], 97)
            self.assertEqual(result["polygon_record_count"], 0)
            self.assertNotIn("Jin Hyun Kim", (output / "RESULT.json").read_text())

    def test_frontier_binds_accepted_masks_without_closing_semantic_geometry(self) -> None:
        from integrate_geometry_source_frontier import build_frontier

        with TemporaryDirectory() as directory:
            root = Path(directory)
            mask = root / "mask.png"
            mask.write_bytes(b"verified-mask")
            mask_hash = hashlib.sha256(mask.read_bytes()).hexdigest()
            candidates = []
            reviews = []
            prior = []
            for index in range(1, 99):
                digest = f"candidate-sha256:{index:064x}"
                frames = [{
                    "offset_s": offset,
                    "timestamp_us": index * 1_000_000 + round(offset * 1_000_000),
                    "source_pixel_sha256": f"{index + 100:064x}",
                    "overlay_sha256": f"{index + 200:064x}",
                    "drivable_mask_path": "mask.png",
                    "drivable_mask_sha256": mask_hash,
                    "lane_mask_path": "mask.png",
                    "lane_mask_sha256": mask_hash,
                } for offset in (-1.0, -0.5, 0.0, 0.5, 1.0)]
                candidates.append({
                    "review_index": index,
                    "candidate_digest": digest,
                    "slice": "FOLLOWING_CUT_IN",
                    "event_timestamp_us": index * 1_000_000,
                    "source_video_sha256": f"{index + 300:064x}",
                    "model_source_revision": "revision",
                    "model_weight_sha256": "a" * 64,
                    "frames": frames,
                })
                assessment = (
                    "ACCEPTABLE_VISIBLE_CANDIDATE"
                    if index <= 2
                    else "MINOR_CORRECTION_REQUIRED"
                )
                reviews.append({
                    "candidate_digest": digest,
                    "review_index": index,
                    "slice": "FOLLOWING_CUT_IN",
                    "event_timestamp_us": index * 1_000_000,
                    "source_video_sha256": f"{index + 300:064x}",
                    "t0_source_pixel_sha256": f"{index + 100:064x}",
                    "t0_overlay_sha256": f"{index + 200:064x}",
                    "machine_geometry_assessment": assessment,
                    "normalized_pixel_polygons": {},
                })
                prior.append({
                    "candidate_digest": digest,
                    "country": "United States",
                    "field_status": {
                        "relevant_actor_or_control_state": (
                            "AVAILABLE_SOURCE_LINKED" if index <= 70 else "REVIEW_REQUIRED_SOURCE_ASSOCIATION"
                        ),
                        "target_zone_or_lane_association": (
                            "AVAILABLE_SOURCE_LINKED" if index == 1 else "REVIEW_REQUIRED_SOURCE_GEOMETRY"
                        ),
                    },
                })

            audit, queue = build_frontier(
                candidate_run_dir=root,
                candidate_manifest={
                    "coordinate_frame": "camera_front_wide_120fov_pixel",
                    "records": candidates,
                },
                review_document={"records": reviews},
                curator_result={
                    "curator_review_complete": True,
                    "curator_review_completed_count": 98,
                    "accepted_machine_geometry_count": 2,
                    "manual_correction_pending_count": 96,
                },
                structured_audit={
                    "records": prior,
                    "relevant_actor_or_control_state_closed_count": 70,
                    "target_zone_or_lane_association_closed_count": 1,
                },
            )

            self.assertEqual(audit["curator_confirmed_machine_mask_event_count"], 2)
            self.assertEqual(audit["verified_machine_mask_file_count"], 20)
            self.assertEqual(audit["slice_specific_geometry_closed_count"], 0)
            self.assertEqual(audit["source_complete_8_of_8_count"], 0)
            self.assertEqual(queue["task_counts"]["ACQUIRE_MANUAL_NORMALIZED_PIXEL_POLYGONS"], 96)


if __name__ == "__main__":
    unittest.main()
