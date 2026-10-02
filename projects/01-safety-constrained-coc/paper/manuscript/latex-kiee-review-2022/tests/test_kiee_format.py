"""Regression checks for the independent KIEE review-format manuscript."""

from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STYLE = ROOT / "kiee-review.sty"
MAIN = ROOT / "main.tex"
COMPILED_SECTIONS = [
    ROOT / "sections" / "01-introduction.tex",
    ROOT / "sections" / "02-related-work.tex",
    ROOT / "sections" / "03-problem.tex",
    ROOT / "sections" / "04-method.tex",
    ROOT / "sections" / "05-experiments.tex",
    ROOT / "sections" / "07-discussion.tex",
    ROOT / "sections" / "08-conclusion.tex",
]


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


class KieeFormatTests(unittest.TestCase):
    """Assertions that can run with the Python standard library alone."""

    def test_style_uses_hwp_page_geometry_and_column_gap(self) -> None:
        self.assertTrue(STYLE.exists(), "kiee-review.sty must define the independent format")
        style = read(STYLE)
        for setting in (
            "left=18.01mm",
            "right=18.01mm",
            "top=18.99mm",
            "bottom=18.99mm",
        ):
            self.assertIn(setting, style)
        self.assertIn(r"\setlength{\columnsep}{8mm}", style)


    def test_style_defines_bilingual_caption_interfaces(self) -> None:
        style = read(STYLE)
        self.assertIn(r"\newcommand{\bifigcaption}", style)
        self.assertIn(r"\newcommand{\bitablecaption}", style)


    def test_review_front_matter_is_anonymous_and_uses_local_fonts(self) -> None:
        main = read(MAIN)
        self.assertNotIn(r"\author{", main)
        self.assertIn(r"\makekieefrontmatter", main)
        self.assertGreater((ROOT / "fonts" / "NotoSerifCJKkr-Regular.otf").stat().st_size, 1_000_000)
        self.assertGreater((ROOT / "fonts" / "NotoSerifCJKkr-Bold.otf").stat().st_size, 1_000_000)
        self.assertIn("SIL OPEN FONT LICENSE", read(ROOT / "fonts" / "OFL.txt"))


    def test_english_abstract_has_template_word_count(self) -> None:
        main = read(MAIN)
        match = re.search(
            r"\\begin\{kieeabstract\}(.*?)\\end\{kieeabstract\}",
            main,
            flags=re.DOTALL,
        )
        self.assertIsNotNone(match, "English abstract must use the kieeabstract environment")
        assert match is not None
        normalized = re.sub(r"\s+", " ", match.group(1)).strip()
        self.assertLessEqual(len(normalized), 1_000)
        abstract = re.sub(r"\\[A-Za-z]+(?:\{[^{}]*\})?", " ", match.group(1))
        words = re.findall(r"[A-Za-z0-9]+(?:[-'][A-Za-z0-9]+)*", abstract)
        self.assertGreaterEqual(len(words), 50)
        self.assertLessEqual(len(words), 200)
        self.assertIsNone(re.search(r"\\(?:cite|ref|footnote|begin\{equation)", match.group(1)))


    def test_claim_scope_and_negative_generalization_result_are_explicit(self) -> None:
        main = read(MAIN)
        source = "\n".join(read(path) for path in COMPILED_SECTIONS)
        self.assertNotIn("안전성 향상을 위한 실행 가드", main)
        self.assertIn("synthetic candidate selection", main)
        self.assertIn("미관측 시간값 평가", source)
        self.assertIn("가드 위반률 0.351", source)
        self.assertIn("쌍 정확도 0.306", source)
        self.assertIn("정보 부재 기준선", source)


    def test_experiment_terms_are_consistent_and_explained(self) -> None:
        source = "\n".join(read(path) for path in COMPILED_SECTIONS)
        for term in (
            "별도 자연어 제약",
            "제약--정답 대응 교란",
            "표준 평가",
            "동일 의미 문장 변형 평가",
            "미관측 수치 평가",
            "미관측 시간값 평가",
            "복합 표현 변화 평가",
            "계약 쌍 정확도",
            "Basic CoC (no constraint)",
            "Constraint-integrated CoC (proposed)",
            "Separate natural-language constraint",
            "Shuffled constraint--target mapping",
            "Standard evaluation",
            "Combined expression-shift evaluation",
            "Paired-contract accuracy",
        ):
            self.assertIn(term, source)
        for obsolete in (
            "요구사항 전용형",
            "CoC 통합형",
            "가드 분리형",
            "대응을 섞은 가드",
            "어려운 표현 평가",
            "일반 평가",
            "미관측 시간 값",
            "계약 전환 쌍 정확도",
        ):
            self.assertNotIn(obsolete, source)


    def test_table_bodies_and_figure_labels_are_english_only(self) -> None:
        source = "\n".join(read(path) for path in COMPILED_SECTIONS)
        table_bodies = re.findall(
            r"\\begin\{tabularx?\}.*?\\end\{tabularx?\}",
            source,
            flags=re.DOTALL,
        )
        self.assertEqual(len(table_bodies), 10)
        for body in table_bodies:
            self.assertIsNone(re.search(r"[가-힣]", body), body)

        figure_generator = read(ROOT / "figures" / "generate_figures.py")
        self.assertIsNone(re.search(r"[가-힣]", figure_generator))


    def test_current_results_are_compiled_once(self) -> None:
        main = read(MAIN)
        self.assertIn(r"\input{sections/05-experiments}", main)
        self.assertNotIn(r"\input{sections/06-results}", main)


    def test_korean_acknowledgments_preserve_funders_and_grant_numbers(self) -> None:
        main = read(MAIN)
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


    def test_every_compiled_caption_is_bilingual(self) -> None:
        source = "\n".join(read(path) for path in COMPILED_SECTIONS)
        legacy = len(re.findall(r"\\caption\{", source))
        bilingual_figures = len(re.findall(r"\\bifigcaption\{", source))
        bilingual_tables = len(re.findall(r"\\bitablecaption\{", source))
        self.assertEqual(legacy, 0)
        self.assertEqual(bilingual_figures, 7)
        self.assertEqual(bilingual_tables, 10)


if __name__ == "__main__":
    unittest.main()
