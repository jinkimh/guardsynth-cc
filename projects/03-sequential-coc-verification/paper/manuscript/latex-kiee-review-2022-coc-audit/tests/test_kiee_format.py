"""Acceptance checks for the independent KIEE CoC-audit manuscript."""

from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MAIN = ROOT / "main.tex"
STYLE = ROOT / "kiee-review.sty"
TARGET_SECTIONS = [
    "01-introduction.tex",
    "02-related-work.tex",
    "03-data.tex",
    "04-problem.tex",
    "05-method.tex",
    "06-experiments.tex",
    "07-results.tex",
    "08-discussion.tex",
    "09-threats.tex",
    "10-conclusion.tex",
]
REQUIRED_VALUES = ["309", "90", "27", "40", "20", "0/7"]
REQUIRED_SCOPE = [
    "지속 의무",
    "해제 조건",
    "사건별",
    "상태형",
    "물리적 차량 안전",
]
APPROVED_ENGLISH_TITLE = (
    "Stateful Consistency Verification of Sequential CoC Annotations for E2E "
    "Autonomous Driving: A CoC-Nusc and UPPAAL Study"
)
APPROVED_ABSTRACT = """
Chain-of-Causation (CoC) annotations can make driving data more interpretable
by pairing an action with its stated reason. Event-local checks, however,
cannot retain an obligation introduced by an earlier annotation. We compile
sequential CoCs into ordered behavior contracts with persistent obligations,
release conditions, action order, and three-valued evidence, and execute the
semantics with a stateful Python monitor. From 90 trajectory-linked multi-CoC
scenes, we extracted 309 adjacent windows and conducted blinded review of 27
selected scene clusters. Pre-adjudication agreement on textual consistency was
low (Fleiss' kappa 0.027), and consensus found no textual contradiction in this
sample; natural-error effectiveness therefore remains unestablished. In a
deterministic suite of 40 synthetic baseline--mutation pairs, stateful rules
classified all 40 mutations as contradictions and all 40 baselines as
consistent, whereas event-local rules classified 20 mutations as
contradictions. Because generation enforces the stateful postcondition, these
counts measure rule-fixture coverage, not out-of-sample detection accuracy.
Seven canonical UPPAAL fixtures matched the Python verdicts (0/7 mismatches)
and supplied a transition-level witness. The results support executable,
traceable contract semantics, not a natural error rate, vehicle safety, or
learning benefit.
"""
APPROVED_KEYWORDS = [
    "Autonomous driving",
    "End-to-end learning",
    "Chain-of-Causation",
    "Stateful verification",
    "Model checking",
    "Data provenance",
]
INPUT_PATTERN = re.compile(r"\\input\s*\{\s*([^}]+?)\s*\}")
RAW_CAPTION_PATTERN = re.compile(r"\\caption\s*\{")


class KieeFormatTests(unittest.TestCase):
    """Checks that are executable with only the Python standard library."""

    def require_text(self, path: Path) -> str:
        self.assertTrue(path.is_file(), f"required file is missing: {path.relative_to(ROOT)}")
        return path.read_text(encoding="utf-8")

    def section_paths(self) -> list[Path]:
        return [ROOT / "sections" / name for name in TARGET_SECTIONS]

    @staticmethod
    def normalized_whitespace(text: str) -> str:
        return " ".join(text.split())

    def abstract_text(self, main: str) -> str:
        match = re.search(
            r"\\begin\{kieeabstract\}(.*?)\\end\{kieeabstract\}",
            main,
            flags=re.DOTALL,
        )
        self.assertIsNotNone(match, "English abstract must use the kieeabstract environment")
        assert match is not None
        return match.group(1)

    def resolve_local_input(self, including_file: Path, input_name: str) -> Path | None:
        requested = Path(input_name)
        if requested.suffix != ".tex":
            requested = requested.with_suffix(".tex")
        root_resolved = ROOT.resolve()
        for candidate in (ROOT / requested, including_file.parent / requested):
            try:
                candidate.resolve().relative_to(root_resolved)
            except ValueError:
                continue
            if candidate.is_file():
                return candidate
        return None

    def compiled_tex_paths(self) -> list[Path]:
        """Follow local ``\\input`` edges from main through sections and figures."""
        pending = [MAIN]
        compiled: list[Path] = []
        seen: set[Path] = set()
        while pending:
            path = pending.pop()
            if path in seen:
                continue
            seen.add(path)
            text = self.require_text(path)
            compiled.append(path)
            for input_name in INPUT_PATTERN.findall(text):
                target = self.resolve_local_input(path, input_name)
                self.assertIsNotNone(
                    target,
                    f"compiled local input is missing or escapes target: "
                    f"{path.relative_to(ROOT)} -> {input_name}",
                )
                assert target is not None
                pending.append(target)
        return compiled

    def test_style_uses_required_geometry_and_column_gap(self) -> None:
        style = self.require_text(STYLE)
        for setting in (
            "left=18.01mm",
            "right=18.01mm",
            "top=18.99mm",
            "bottom=18.99mm",
        ):
            self.assertIn(setting, style)
        self.assertIn(r"\setlength{\columnsep}{8mm}", style)

    def test_target_source_is_anonymous(self) -> None:
        author_commands = []
        for path in ROOT.rglob("*"):
            if not path.is_file() or "tests" in path.parts or path.suffix not in {".tex", ".sty"}:
                continue
            if re.search(r"\\author\b", path.read_text(encoding="utf-8")):
                author_commands.append(path.relative_to(ROOT).as_posix())
        self.assertEqual([], author_commands, "review-copy sources must not declare authors")

    def test_local_fonts_and_ofl_license_are_present(self) -> None:
        for name in ("NotoSerifCJKkr-Regular.otf", "NotoSerifCJKkr-Bold.otf"):
            font = ROOT / "fonts" / name
            self.assertTrue(font.is_file(), f"local review font is missing: fonts/{name}")
        license_text = self.require_text(ROOT / "fonts" / "OFL.txt")
        self.assertIn("SIL OPEN FONT LICENSE", license_text.upper())

    def test_english_abstract_has_50_to_200_words(self) -> None:
        main = self.require_text(MAIN)
        abstract = self.abstract_text(main)
        self.assertEqual(
            self.normalized_whitespace(APPROVED_ABSTRACT),
            self.normalized_whitespace(abstract),
            "English abstract must preserve the approved evidence and scope statement",
        )
        abstract = re.sub(r"\\[A-Za-z]+(?:\{[^{}]*\})?", " ", abstract)
        words = re.findall(r"[A-Za-z0-9]+(?:[-'][A-Za-z0-9]+)*", abstract)
        self.assertGreaterEqual(len(words), 50)
        self.assertLessEqual(len(words), 200)

    def test_english_abstract_has_no_citations_references_footnotes_or_equations(self) -> None:
        abstract = self.abstract_text(self.require_text(MAIN))
        forbidden = {
            "citation": r"\\(?:cite[a-zA-Z*]*|autocite)\b",
            "reference": r"\\(?:ref|pageref|eqref)\b",
            "footnote": r"\\(?:footnote|thanks)\b",
            "equation": r"\\(?:begin\s*\{(?:equation|align|gather|math)\*?\}|\[|\]|\(|\)|\$\$)",
        }
        for kind, pattern in forbidden.items():
            self.assertNotRegex(abstract, pattern, f"English abstract must not contain a {kind}")

    def test_english_title_matches_the_approved_review_copy(self) -> None:
        main = self.require_text(MAIN)
        match = re.search(r"\\kieeenglishtitle\s*\{(.*?)\}", main, flags=re.DOTALL)
        self.assertIsNotNone(match, "main.tex must declare the approved English title")
        assert match is not None
        self.assertEqual(
            self.normalized_whitespace(APPROVED_ENGLISH_TITLE),
            self.normalized_whitespace(match.group(1)),
        )

    def test_english_keywords_are_exactly_six(self) -> None:
        main = self.require_text(MAIN)
        match = re.search(r"\\kieekeywords\{([^{}]*)\}", main, flags=re.DOTALL)
        self.assertIsNotNone(match, "main.tex must declare English keywords")
        assert match is not None
        keywords = [keyword.strip() for keyword in match.group(1).split(",") if keyword.strip()]
        self.assertEqual(APPROVED_KEYWORDS, keywords, "KIEE review copy requires the approved six keywords")

    def test_main_compiles_all_ten_sections_in_order(self) -> None:
        main = self.require_text(MAIN)
        inputs = re.findall(r"\\input\s*\{sections/([^}]+)\}", main)
        self.assertEqual([Path(name).stem for name in TARGET_SECTIONS], inputs)

    def test_korean_acknowledgments_preserve_funders_and_grant_numbers(self) -> None:
        main = self.require_text(MAIN)
        heading = r"\section*{감사의 글}"
        self.assertEqual(1, main.count(heading))
        self.assertLess(main.index(heading), main.index(r"\bibliographystyle{unsrt}"))
        for required in (
            "대한민국 정부(교육과학기술부)",
            "한국연구재단(NRF)",
            "NRF-2023R1A2C1006639",
            "대한민국 정부(과학기술정보통신부)",
            "정보통신기획평가원(IITP)",
            "지역지능화혁신인재양성사업",
            "IITP-2026-RS-2024-00436773",
        ):
            self.assertIn(required, main)

    def test_sections_preserve_core_question_values_and_scope(self) -> None:
        paths = self.section_paths()
        for path in paths:
            self.assertTrue(path.is_file(), f"compiled section is missing: {path.relative_to(ROOT)}")
        text = "\n".join(path.read_text(encoding="utf-8") for path in paths)
        self.assertIn("연구 질문", text)
        for removed_question in ("RQ1", "RQ2", "RQ3", "RQ4", "RQ5"):
            self.assertNotIn(removed_question, text)
        for value in REQUIRED_VALUES:
            self.assertIn(value, text)
        for scope_term in REQUIRED_SCOPE:
            self.assertIn(scope_term, text)

    def test_no_source_relative_inputs(self) -> None:
        for path in ROOT.rglob("*.tex"):
            source = path.read_text(encoding="utf-8")
            self.assertNotRegex(
                source,
                r"\\(?:input|include|subfile)\s*\{\s*\.\./",
                f"source-relative input found in {path.relative_to(ROOT)}",
            )

    def test_target_contains_no_symlinks(self) -> None:
        symlinks = [path.relative_to(ROOT) for path in ROOT.rglob("*") if path.is_symlink()]
        self.assertEqual([], symlinks, "independent copy must not contain symbolic links")

    def test_compiled_figure_and_table_environments_use_bilingual_captions(self) -> None:
        raw_captions = []
        missing_bilingual_captions = []
        environments = (("figure", "bifigcaption"), ("table", "bitablecaption"))
        for path in self.compiled_tex_paths():
            text = path.read_text(encoding="utf-8")
            for environment, macro in environments:
                pattern = re.compile(
                    rf"\\begin\s*\{{({environment}\\*?)\}}(.*?)\\end\s*\{{\\1\}}",
                    flags=re.DOTALL,
                )
                for match in pattern.finditer(text):
                    label = f"{path.relative_to(ROOT).as_posix()}:{match.group(1)}"
                    body = match.group(2)
                    if RAW_CAPTION_PATTERN.search(body):
                        raw_captions.append(label)
                    if not re.search(rf"\\{macro}\s*\{{", body):
                        missing_bilingual_captions.append(label)
        self.assertEqual([], raw_captions, "compiled floats must not use raw \\caption")
        self.assertEqual(
            [],
            missing_bilingual_captions,
            "every compiled figure/table environment must use its bilingual caption macro",
        )

    def test_table_bodies_and_figure_labels_are_english_only(self) -> None:
        table_bodies: list[tuple[Path, str]] = []
        compiled_figures: list[Path] = []
        for path in self.compiled_tex_paths():
            source = path.read_text(encoding="utf-8")
            for body in re.findall(
                r"\\begin\{tabularx?\}.*?\\end\{tabularx?\}",
                source,
                flags=re.DOTALL,
            ):
                table_bodies.append((path, body))
            if path.parent == ROOT / "figures":
                compiled_figures.append(path)

        self.assertEqual(19, len(table_bodies), "unexpected number of compiled tables")
        for path, body in table_bodies:
            self.assertIsNone(
                re.search(r"[가-힣]", body),
                f"Korean text remains in a table body in {path.relative_to(ROOT)}:\n{body}",
            )

        self.assertEqual(5, len(compiled_figures), "unexpected number of compiled figures")
        for path in compiled_figures:
            self.assertIsNone(
                re.search(r"[가-힣]", path.read_text(encoding="utf-8")),
                f"Korean text remains inside {path.relative_to(ROOT)}",
            )


if __name__ == "__main__":
    unittest.main()
