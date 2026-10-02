import json
import re
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from apps.research_portal.run import _review_cards, build_portal


class SiteIntegrityTest(unittest.TestCase):
    def test_review_cards_escape_metadata_and_handle_empty_registry(self):
        self.assertIn("등록된 검토 화면이 없습니다", _review_cards([]))
        cards = _review_cards([{
            "title": "Project <A>",
            "review_pages": [{
                "title": "Review <B>", "description": "A & B",
                "href": 'reviews/example.html?label="test"',
            }],
        }])
        self.assertIn("Project &lt;A&gt;", cards)
        self.assertIn("Review &lt;B&gt;", cards)
        self.assertIn("A &amp; B", cards)
        self.assertIn('href="reviews/example.html?label=&quot;test&quot;"', cards)

    def test_native_templates_have_no_inline_script_or_style(self):
        site = Path(__file__).resolve().parents[1] / "site"
        for source in site.glob("*.html"):
            text = source.read_text(encoding="utf-8")
            self.assertNotIn("style=", text, source.name)
            self.assertNotRegex(text, r"<script(?![^>]+src=)", source.name)

    def test_every_native_page_has_a_home_link(self):
        site = Path(__file__).resolve().parents[1] / "site"
        for source in site.glob("*.html"):
            self.assertIn('href="index.html"', source.read_text(encoding="utf-8"), source.name)

    def test_next_generation_routes_and_owner_data_are_built(self):
        with TemporaryDirectory() as directory:
            output = Path(directory) / "portal"
            build_portal(output)
            data = json.loads((output / "PORTAL_DATA.json").read_text(encoding="utf-8"))

            for route in (
                "projects.html",
                "platform.html",
                "evidence.html",
                "artifact.html",
                "reviews.html",
                "review_round.html",
                "review_sample.html",
                "review_adjudication.html",
                "meetings.html",
                "login.html",
            ):
                self.assertTrue((output / route).is_file(), route)
            self.assertEqual([item["platform_id"] for item in data["platforms"]], ["eblc-bcv"])
            self.assertEqual(data["projection"]["projects"][3]["gate_state"], "PARTIAL")
            self.assertEqual(len(data["paper_registry"]["projects"]), 5)
            self.assertTrue(data["artifact_registry"])
            self.assertTrue(all("canonical_path" not in item for item in data["artifact_registry"]))
            # The actual questionnaire links must exist before JavaScript runs.
            reviews = (output / "reviews.html").read_text(encoding="utf-8")
            links = re.findall(r'href="(reviews/[^"]+)"', reviews)
            expected = [page["href"] for project in data["research_projects"]
                        for page in project["review_pages"]]
            self.assertEqual(links, expected)
            self.assertEqual(links[0], "reviews/paper1_action_review.html")
            self.assertNotIn("{{REVIEW_CARDS}}", reviews)
            self.assertIn('data-rendered="true"', reviews)

    def test_every_static_route_has_resolving_local_links(self):
        with TemporaryDirectory() as directory:
            output = Path(directory) / "portal"
            build_portal(output)

            for source in output.glob("*.html"):
                for raw in re.findall(r'(?:href|src)="([^"]+)"', source.read_text(encoding="utf-8")):
                    if raw.startswith(("#", "http:", "https:", "data:")):
                        continue
                    self.assertTrue((source.parent / raw.split("#", 1)[0]).exists(), f"{source.name}: {raw}")


if __name__ == "__main__":
    unittest.main()
