"""Tests for the local GuardSynth research tracking and review portal."""

from __future__ import annotations

import json
import hashlib
from pathlib import Path
import re
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from apps.research_portal.run import _portfolio_snapshot, build_portal


ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "PROJECT_REGISTRY.json").is_file())


class ProjectPortalTest(unittest.TestCase):
    def test_build_has_five_independently_managed_research_projects(self) -> None:
        with TemporaryDirectory() as directory:
            output = Path(directory) / "portal"
            manifest = build_portal(output)
            data = json.loads((output / "PORTAL_DATA.json").read_text(encoding="utf-8"))
            projects = data["research_projects"]
            self.assertEqual(len(projects), 5)
            self.assertEqual(manifest["project_count"], 5)
            self.assertEqual(
                [item["id"] for item in projects],
                [
                    "safety-constrained-coc",
                    "specification-alignment",
                    "sequential-coc-verification",
                    "guardsynth-coc",
                    "eblc-language-verification",
                ],
            )
            self.assertEqual(
                manifest["milestone_count"],
                sum(len(item["milestones"]) for item in projects),
            )
            for index, project in enumerate(projects, start=1):
                self.assertTrue(project["overview"])
                self.assertTrue(project["goal"])
                self.assertTrue(project["state"])
                self.assertTrue(project["current_task"])
                self.assertGreater(len(project["milestones"]), 0)
                self.assertEqual(project["page"], f"project_{index:02d}.html")
                self.assertEqual(project["review_page"], f"review_{index:02d}.html")
                self.assertEqual(project["tracking_sync"]["authority"], "CANONICAL_DOCUMENTS")
            self.assertEqual([paper["id"] for paper in data["papers"]], ["paper1", "paper3"])
            self.assertEqual(manifest["paper_count"], 2)
            self.assertEqual(manifest["paper_download_count"], 2)
            guardsynth = next(item for item in projects if item["id"] == "guardsynth-coc")
            self.assertEqual(guardsynth["active_milestone_id"], "M16")
            self.assertEqual(
                guardsynth["state"],
                "M16_M17_SPEED_ACTION_RECEIVED_SOURCE_BINDING_PENDING",
            )
            self.assertIn("M12-R01 / M16", guardsynth["current_task"])
            self.assertIn("source-grounded speed applicability", guardsynth["current_task"])
            self.assertIn("ACTION intake complete", guardsynth["current_task"])
            self.assertIn("original CoC context", guardsynth["current_task"])
            milestones = {item["id"]: item for item in guardsynth["milestones"]}
            self.assertEqual(len(milestones), 22)
            for milestone_id in ("M12", "M14", "M15", "M16"):
                self.assertTrue(milestones[milestone_id]["status"].startswith("PARTIAL"))
            for milestone_id in ("M13", "M19", "M21"):
                self.assertTrue(milestones[milestone_id]["status"].startswith("QUEUED"))
                self.assertEqual(milestones[milestone_id]["phase"], "PHASE2")
            self.assertTrue(any(
                "M17-S01" in task["text"]
                for task in milestones["M17"]["tasks"]
            ))
            self.assertTrue(any(
                "E4-L" in task["text"]
                for task in milestones["M20"]["tasks"]
            ))
            self.assertTrue(any(
                "CNL" in task["text"]
                for task in milestones["M18"]["tasks"]
            ))
            self.assertLess(milestones["M21"]["task_count"], 10)
            self.assertIn("source/target acceptance", guardsynth["blocker"].lower())
            self.assertEqual(len(guardsynth["review_pages"]), 9)
            self.assertEqual(
                guardsynth["review_pages"][0]["id"],
                "paper1-speed-action-jonh",
            )
            self.assertTrue(
                all(not item["review_pages"] for item in projects if item is not guardsynth)
            )

    def test_tracking_snapshot_reloads_authority_documents(self) -> None:
        with TemporaryDirectory() as directory:
            output = Path(directory) / "portal"
            build_portal(output)
            base = json.loads((output / "PORTAL_DATA.json").read_text(encoding="utf-8"))
            source = ROOT / "projects/01-safety-constrained-coc/docs/plans/02_PROJECT_MILESTONES.md"
            changed = Path(directory) / "02_PROJECT_MILESTONES.md"
            changed.write_text(
                source.read_text(encoding="utf-8").replace(
                    "다음 투고 경로와 중복 출판 경계 결정",
                    "다음 투고 경로 자동 연동 검증",
                ),
                encoding="utf-8",
            )
            with patch.dict(
                "apps.research_portal.run.PROJECT_DOCUMENT_OVERRIDES",
                {"safety-constrained-coc": {"milestones": changed}},
            ):
                refreshed = _portfolio_snapshot(base)
            project = next(
                item for item in refreshed["research_projects"]
                if item["id"] == "safety-constrained-coc"
            )
            active = next(item for item in project["milestones"] if item["id"] == "SC-M04")
            self.assertEqual(
                active["title"], "다음 투고 경로 자동 연동 검증"
            )
            self.assertEqual(project["tracking_sync"]["mode"], "LIVE_ON_PAGE_LOAD")

    def test_site_pages_and_selected_restricted_reviews_are_self_contained(self) -> None:
        with TemporaryDirectory() as directory:
            output = Path(directory) / "portal"
            manifest = build_portal(output)
            self.assertEqual(manifest["review_page_count"], 9)
            self.assertEqual(
                set(manifest["review_assets"]),
                {"paper1_action_review.html", "paper1_action_assignment_preview.html", "paper1_source_gap_review.html", "paper1_candidate_readiness.html", "m16_expert_source_review.html", "scene18_source_binding_review.html",
                 "scene18_independent_action_review.html", "scene18_independent_cnl_review.html", "paper1_speed_action_jonh.html"},
            )
            result = json.loads((output / "RESULT.json").read_text(encoding="utf-8"))
            self.assertEqual(result["status"], "BUILT")
            self.assertEqual(result["review_page_count"], 9)
            speed = (output / "reviews/paper1_speed_action_jonh.html").read_text(encoding="utf-8")
            self.assertIn("Jonh · 속도 행동 검토", speed)
            for forbidden in ('original_coc', 'raw_answer', 'zone_polygon', 'cnl_file', 'href="/'):
                self.assertNotIn(forbidden, speed)
            for name in ("paper1_action_review.html", "paper1_action_assignment_preview.html"):
                suspended = (output / "reviews" / name).read_text(encoding="utf-8")
                self.assertIn("이 16장면 검토는 중단했습니다", suspended)
                self.assertIn("임의 경로 배정은 철회", suspended)
                self.assertNotIn("<form", suspended)
                self.assertIn('id="backup"', suspended)
            for name in ("index.html", "papers.html", "milestones.html", "review.html", "guide.html"):
                self.assertTrue((output / name).is_file(), name)
            self.assertFalse((output / "structure.html").exists())
            for index in range(1, 6):
                self.assertTrue((output / f"project_{index:02d}.html").is_file())
                self.assertTrue((output / f"review_{index:02d}.html").is_file())
            papers = (output / "papers.html").read_text(encoding="utf-8")
            self.assertIn("우리의 논문", papers)
            self.assertIn("요약", papers)
            self.assertIn("핵심 기여", papers)
            self.assertIn("핵심 내용", papers)
            self.assertIn("Safety-Constrained Chain-of-Causation", papers)
            self.assertIn("Stateful Consistency Verification", papers)
            self.assertIn("downloads/paper1-safety-constrained-coc.pdf", papers)
            self.assertIn("downloads/paper3-sequential-coc-uppaal-10pages.pdf", papers)
            review_text = (output / "review_04.html").read_text(encoding="utf-8")
            self.assertIn("이 연구영역에 소유권이 등록된 검토 패키지만 표시합니다", review_text)
            expert_review = (
                output / "reviews" / "m16_expert_source_review.html"
            ).read_text(encoding="utf-8")
            self.assertIn("전문가 ID", expert_review)
            self.assertIn("기계 표시는 정답이 아닙니다", expert_review)
            self.assertIn("불일치할 때만 그리기", expert_review)
            self.assertIn('id="zoneButtons"', expert_review)
            self.assertIn('id="disposition"', expert_review)
            self.assertIn("선행 관찰 초안", expert_review)
            source_review = (output / "reviews" / "scene18_source_binding_review.html").read_text(encoding="utf-8")
            self.assertIn("판단 시점의 대상·영역 확인", source_review)
            self.assertIn("정확한 시간 대응이 확인되지 않은", source_review)
            self.assertIn("판단 불가", source_review)
            self.assertIn("source_anchor_display", source_review)
            portal_css = (output / "portal.css").read_text(encoding="utf-8")
            self.assertIn(".review-shell", portal_css)
            self.assertIn(".review-layout { display: block;", portal_css)
            empty_review = (output / "review_01.html").read_text(encoding="utf-8")
            self.assertIn("현재 등록된 검토 패키지가 없습니다", empty_review)
            guide = (output / "guide.html").read_text(encoding="utf-8")
            self.assertIn("충돌 영역", guide)
            self.assertIn("프레임 간 변화", guide)
            overview = (output / "index.html").read_text(encoding="utf-8")
            self.assertIn("연구영역별 독립 관리", overview)
            self.assertNotIn("리팩터링된 프로젝트 구조", overview)
            project_page = (output / "project_02.html").read_text(encoding="utf-8")
            self.assertIn("연구 개요와 목표", project_page)
            self.assertIn("독립 마일스톤", project_page)
            milestones = (output / "milestones.html").read_text(encoding="utf-8")
            self.assertIn("연구영역별 마일스톤", milestones)
            data = json.loads((output / "PORTAL_DATA.json").read_text(encoding="utf-8"))
            for page in next(
                item for item in data["research_projects"] if item["id"] == "guardsynth-coc"
            )["review_pages"]:
                self.assertTrue((output / page["href"]).is_file(), page["href"])
                self.assertRegex(
                    Path(page["href"]).name,
                    r"^[a-z][a-z0-9_]*\.html$",
                )
            for removed_review in (
                "m16_source_review.html",
                "image_review.html",
                "evidence_review.html",
                "expert_training.html",
                "association_01.html",
            ):
                self.assertFalse((output / "reviews" / removed_review).exists())
            portal_js = (output / "portal.js").read_text(encoding="utf-8")
            self.assertIn("menuPanel.hidden = project.review_pages.length <= 1", portal_js)
            downloads = [paper for paper in data["papers"] if paper["download"]]
            self.assertEqual(len(downloads), 2)
            for paper in downloads:
                target = output / paper["download"]["href"]
                source = ROOT / paper["download"]["source"]
                self.assertTrue(target.is_file(), paper["id"])
                self.assertEqual(
                    hashlib.sha256(target.read_bytes()).hexdigest(),
                    hashlib.sha256(source.read_bytes()).hexdigest(),
                )
            paper3 = next(paper for paper in data["papers"] if paper["id"] == "paper3")
            self.assertEqual(
                paper3["download"]["source"],
                "projects/03-sequential-coc-verification/paper/manuscript/latex-kiee-review-2022-coc-audit-10pages/main.pdf",
            )
            all_text = "\n".join(
                path.read_text(encoding="utf-8", errors="ignore")
                for path in output.rglob("*.html")
            )
            self.assertFalse(str(ROOT) in all_text, "portal HTML exposes the absolute repository path")

    def test_all_portal_local_links_resolve(self) -> None:
        with TemporaryDirectory() as directory:
            output = Path(directory) / "portal"
            build_portal(output)
            for source in output.glob("*.html"):
                text = source.read_text(encoding="utf-8")
                for raw in re.findall(r"(?:href|src)=\"([^\"]+)\"", text):
                    if raw.startswith(("#", "http:", "https:", "data:")):
                        continue
                    target = (source.parent / raw.split("#", 1)[0]).resolve()
                    self.assertTrue(target.exists(), f"{source.name}: {raw}")

    def test_builder_refuses_to_overwrite_existing_portal(self) -> None:
        with TemporaryDirectory() as directory:
            output = Path(directory) / "portal"
            build_portal(output)
            with self.assertRaisesRegex(FileExistsError, "refusing to overwrite"):
                build_portal(output)


if __name__ == "__main__":
    unittest.main()
