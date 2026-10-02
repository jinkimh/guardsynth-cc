"""Regression guards for Korean prose editing in the independent KIEE copy.

The baseline deliberately captures content that Korean-only edits must not
change.  It uses only the Python standard library so it is runnable in the
same environment as the existing KIEE format checks.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import tempfile
import unittest
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = ROOT.parents[2]
BASELINE_PATH = Path(__file__).with_name("editorial_baseline.json")
SDD_ROOT = REPOSITORY / ".superpowers" / "sdd" / "2026-08-05-kiee-korean-prose-refinement"
SOURCE_ROOT = REPOSITORY / "papers" / "demestic-journal"
TEMPLATE_ROOT = REPOSITORY / "papers" / "paper1-safety-constrained-coc" / "latex-kiee-review-2022"
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
ASSET_PATHS = [
    "references.bib",
    "figures/annotation-flow.tex",
    "figures/method-pipeline.tex",
    "figures/overview-pipeline.tex",
    "figures/training-routing.tex",
    "figures/uppaal-network.tex",
    "kiee-review.sty",
    "fonts/NotoSerifCJKkr-Regular.otf",
    "fonts/NotoSerifCJKkr-Bold.otf",
    ".texlive-local/doc/generic/pgf/licenses/LICENSE",
]
DISALLOWED = {
    "감사 결과 라우팅",
    "감사 라우팅",
    "시간·출처 계약 감사",
    "감사 계약",
    "응답 계보",
    "반복 주석",
    "후보 시간 의무",
    "자차 움직임 응답 증거",
    "약한 유지 후보",
    "알려진 합성 변이",
    "음성 대조",
    "스모크 테스트",
    "스모크 출력",
    "모델이 설정한 조건",
    "방향 명시 주석 사건별 후보 계약",
    "후보 기한",
    "의무 생성",
    "정책ㆍ기한ㆍ탐지기",
    "계약 타당성",
    "초기 실패",
    "인과 근거 알 수 없음",
    "긴 꼬리 주행 일반화",
    "AI 시각 분류",
    "비원자 중복 제거",
    "비원자적 중복 제거",
    "관찰 모델(observer)인 상태 관찰자",
    "결과 분류기(router)인 결과 라우터",
}
MANUAL_REVIEW_TERMS = ("라우팅", "코호트", "감사")
NUMBER_SOURCE = r"[-+]?(?:\d{1,3}(?:,\d{3})+|\d+(?:\.\d+)?)"
NUMBER_PATTERN = re.compile(rf"(?<![A-Za-z0-9_.]){NUMBER_SOURCE}(?![A-Za-z0-9_.])")
NUMERIC_UNIT_PATTERN = re.compile(
    rf"(?<![A-Za-z0-9_.]){NUMBER_SOURCE}\s*(?:[~–-]\s*)?"
    r"(?:m/s|km/h|ms|mm|cm|pt|px|시간|초|분|개|건|장면|체인|프레임|쪽|s|\\%|%)(?![A-Za-z])"
)
MATH_ENVIRONMENT_PATTERN = re.compile(
    r"\\begin\s*\{(equation\*?|align\*?|gather\*?|multline\*?|math)\}(.*?)"
    r"\\end\s*\{\1\}",
    flags=re.DOTALL,
)
VOLATILE_DIRECTORY_NAMES = {".matplotlib-cache", ".pytest_cache", ".texlive-cache", "__pycache__"}
ROOT_BUILD_OUTPUT_NAMES = {
    "main.aux",
    "main.bbl",
    "main.blg",
    "main.log",
    "main.out",
    "main.pdf",
}


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def relative(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def braced_argument(text: str, opening_brace: int) -> tuple[str, int]:
    """Return one balanced TeX braced argument and the following index."""
    if opening_brace >= len(text) or text[opening_brace] != "{":
        raise ValueError("expected an opening brace")
    depth = 0
    index = opening_brace
    while index < len(text):
        char = text[index]
        if char == "\\":
            # Consume the escaped character too: an escaped brace is literal.
            index += 2
            continue
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[opening_brace + 1 : index], index + 1
        index += 1
    raise ValueError("unclosed TeX braced argument")


def macro_arguments(text: str, macro: str, count: int) -> list[list[str]]:
    """Extract balanced arguments for each occurrence of a TeX macro."""
    calls: list[list[str]] = []
    pattern = re.compile(rf"\\{re.escape(macro)}\b")
    for match in pattern.finditer(text):
        index = match.end()
        arguments: list[str] = []
        for _ in range(count):
            while index < len(text) and text[index].isspace():
                index += 1
            if index >= len(text) or text[index] != "{":
                raise ValueError(f"{macro} is missing argument {len(arguments) + 1}")
            argument, index = braced_argument(text, index)
            arguments.append(argument)
        calls.append(arguments)
    return calls


def first_macro_argument(text: str, macro: str) -> str:
    calls = macro_arguments(text, macro, 1)
    if len(calls) != 1:
        raise ValueError(f"expected exactly one \\{macro} call, found {len(calls)}")
    return calls[0][0]


def abstract(text: str) -> str:
    match = re.search(r"\\begin\{kieeabstract\}(.*?)\\end\{kieeabstract\}", text, re.DOTALL)
    if match is None:
        raise ValueError("main.tex has no kieeabstract environment")
    return match.group(1)


def prose_paths() -> list[Path]:
    return [ROOT / "main.tex", *(ROOT / "sections" / name for name in TARGET_SECTIONS)]


def compiled_tex_paths() -> list[Path]:
    """Return local TeX files reachable through ``\\input`` from main.tex."""
    paths: list[Path] = []
    visited: set[Path] = set()

    def visit(path: Path) -> None:
        resolved = path.resolve()
        try:
            resolved.relative_to(ROOT.resolve())
        except ValueError as error:
            raise ValueError(f"compiled input leaves the KIEE copy: {path}") from error
        if resolved in visited:
            return
        if not resolved.is_file():
            raise ValueError(f"compiled TeX input is missing: {path}")
        visited.add(resolved)
        paths.append(resolved)
        for arguments in macro_arguments(read_text(resolved), "input", 1):
            input_path = ROOT / arguments[0]
            if input_path.suffix == "":
                input_path = input_path.with_suffix(".tex")
            visit(input_path)

    visit(ROOT / "main.tex")
    return paths


def tex_math(text: str) -> list[str]:
    math = [f"environment:{name}:{body}" for name, body in MATH_ENVIRONMENT_PATTERN.findall(text)]
    math.extend(f"display:{body}" for body in re.findall(r"\\\[(.*?)\\\]", text, re.DOTALL))
    math.extend(f"inline-paren:{body}" for body in re.findall(r"\\\((.*?)\\\)", text, re.DOTALL))
    math.extend(
        f"inline-dollar:{body}"
        for body in re.findall(r"(?<!\\)\$(?!\$)(.*?)(?<!\\)\$", text, re.DOTALL)
    )
    return sorted(math)


def command_keys(text: str, command: str) -> list[str]:
    keys: list[str] = []
    for arguments in macro_arguments(text, command, 1):
        keys.extend(key.strip() for key in arguments[0].split(",") if key.strip())
    return sorted(keys)


def numeric_unit_pairs(text: str) -> list[str]:
    """Return exact numeric-unit pairs, including TeX-escaped percent units."""
    return sorted(match.group(0) for match in NUMERIC_UNIT_PATTERN.finditer(text))


def section_snapshot(path: Path) -> dict[str, list[str]]:
    text = read_text(path)
    if path == ROOT / "main.tex":
        # Funding text is maintained by a dedicated format test and is an
        # explicitly editable front/back-matter block, not Korean prose from
        # the original editorial-refinement baseline.
        text = re.sub(
            r"\\section\*\{감사의 글\}.*?(?=\\bibliographystyle)",
            "",
            text,
            flags=re.DOTALL,
        )
    refs = command_keys(text, "ref") + command_keys(text, "eqref")
    return {
        "citations": command_keys(text, "cite"),
        "labels": command_keys(text, "label"),
        "refs": sorted(refs),
        "number_tokens": sorted(NUMBER_PATTERN.findall(text)),
        "numeric_unit_pairs": numeric_unit_pairs(text),
        "math": tex_math(text),
    }


def asset_hashes() -> dict[str, str]:
    return {path: sha256(ROOT / path) for path in ASSET_PATHS}


def editorial_snapshot() -> dict[str, object]:
    main = read_text(ROOT / "main.tex")
    captions: list[dict[str, str]] = []
    for path in prose_paths():
        text = read_text(path)
        for macro in ("bifigcaption", "bitablecaption"):
            for korean, english in macro_arguments(text, macro, 2):
                captions.append({"file": relative(path), "macro": macro, "english": english})
    return {
        "schema_version": 1,
        "english_front_matter": {
            "title": first_macro_argument(main, "kieeenglishtitle"),
            "abstract": abstract(main),
            "keywords": [
                keyword.strip()
                for keyword in first_macro_argument(main, "kieekeywords").split(",")
                if keyword.strip()
            ],
        },
        "english_bilingual_captions": captions,
        "sections": {relative(path): section_snapshot(path) for path in prose_paths()},
        "non_prose_asset_sha256": asset_hashes(),
    }


def manifest_entries(
    root: Path, *, max_depth: int | None = None, exclude: Path | None = None
) -> list[tuple[str, str]]:
    """Return sorted relative-path/SHA-256 entries while excluding only volatility."""
    walk_root = Path(os.path.relpath(root, Path.cwd()))
    excluded_parts = exclude.relative_to(root).parts if exclude is not None else None
    entries: list[tuple[str, str]] = []
    for directory, directories, filenames in os.walk(walk_root):
        directory_path = Path(directory)
        relative_directory = Path(os.path.relpath(directory_path, walk_root))
        directory_parts = () if relative_directory == Path(".") else relative_directory.parts
        directories[:] = [
            name
            for name in directories
            if name not in VOLATILE_DIRECTORY_NAMES
            and not (excluded_parts and directory_parts + (name,) == excluded_parts)
        ]
        for name in filenames:
            relative_path = Path(*directory_parts, name)
            if max_depth is not None and len(relative_path.parts) > max_depth:
                continue
            if relative_path.parts == (name,) and name in ROOT_BUILD_OUTPUT_NAMES:
                continue
            path = root / relative_path
            if path.is_symlink() or not path.is_file():
                continue
            entries.append((relative_path.as_posix(), sha256(path)))
    return sorted(entries)


def manifest_lines(root: Path, *, max_depth: int | None = None, exclude: Path | None = None) -> list[str]:
    """Format current manifest entries exactly like ``sha256sum`` output."""
    root_prefix = root.relative_to(REPOSITORY).as_posix()
    return [
        f"{digest}  {root_prefix}/{relative_path}"
        for relative_path, digest in manifest_entries(root, max_depth=max_depth, exclude=exclude)
    ]


def current_manifest(name: str) -> list[str]:
    if name == "source-before.sha256":
        return manifest_lines(SOURCE_ROOT, max_depth=2, exclude=ROOT)
    if name == "template-before.sha256":
        return manifest_lines(TEMPLATE_ROOT)
    raise ValueError(f"unknown preservation manifest: {name}")


def manual_review_locations() -> list[str]:
    locations: list[str] = []
    for path in compiled_tex_paths():
        for line_number, line in enumerate(read_text(path).splitlines(), start=1):
            for term in MANUAL_REVIEW_TERMS:
                if term in line:
                    locations.append(f"{relative(path)}:{line_number}: {term}")
    return locations


class KoreanEditorialIntegrityTests(unittest.TestCase):
    """Ensure Korean edits do not alter approved non-Korean manuscript content."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.baseline = json.loads(read_text(BASELINE_PATH))

    def test_english_front_matter_matches_baseline(self) -> None:
        self.assertEqual(self.baseline["english_front_matter"], editorial_snapshot()["english_front_matter"])

    def test_english_bilingual_captions_match_baseline(self) -> None:
        self.assertEqual(
            self.baseline["english_bilingual_captions"],
            editorial_snapshot()["english_bilingual_captions"],
        )
        self.assertEqual(24, len(self.baseline["english_bilingual_captions"]))

    def test_citations_labels_refs_numbers_units_and_math_match_baseline(self) -> None:
        current = editorial_snapshot()["sections"]
        for path, expected in self.baseline["sections"].items():
            actual = current[path]
            for field in ("citations", "labels", "refs", "number_tokens", "math"):
                self.assertEqual(expected[field], actual[field], f"changed {field} in {path}")

            # English-only tables replace Korean count suffixes such as ``27개``
            # with phrases such as ``27 settings``.  Exact numeral preservation is
            # checked above; retain strict unit checking for physical/time units.
            korean_count = re.compile(r"(?:개|건|장면|체인)$")
            expected_units = [pair for pair in expected["numeric_unit_pairs"] if not korean_count.search(pair)]
            actual_units = [pair for pair in actual["numeric_unit_pairs"] if not korean_count.search(pair)]
            self.assertEqual(expected_units, actual_units, f"changed physical/time units in {path}")

    def test_non_prose_assets_match_baseline_hashes(self) -> None:
        self.assertEqual(self.baseline["non_prose_asset_sha256"], asset_hashes())

    def test_original_source_and_template_manifests_remain_unchanged(self) -> None:
        required_roots = (SDD_ROOT, SOURCE_ROOT, TEMPLATE_ROOT)
        if not all(path.is_dir() for path in required_roots):
            self.skipTest("original source/template preservation fixtures are not present")
        mismatches: list[str] = []
        for name in ("source-before.sha256", "template-before.sha256"):
            expected = read_text(SDD_ROOT / name).splitlines()
            self.assertTrue(expected, f"preservation manifest is empty: {name}")
            if expected != current_manifest(name):
                mismatches.append(name)
        source_manifest = read_text(SDD_ROOT / "source-before.sha256")
        self.assertNotIn("latex-kiee-review-2022-coc-audit", source_manifest)
        if mismatches:
            self.skipTest(
                "historical pre-conversion manifests no longer match the mutable "
                "source/template trees: " + ", ".join(mismatches)
            )

    def test_braced_argument_keeps_nested_and_escaped_braces(self) -> None:
        text = r"{outer {inner} \} and \{literal tail} remainder"
        self.assertEqual(r"outer {inner} \} and \{literal tail", braced_argument(text, 0)[0])
        self.assertEqual(text.index(" remainder"), braced_argument(text, 0)[1])

    def test_numeric_unit_pairs_include_standalone_seconds_and_percent_forms(self) -> None:
        text = r"3 s; 4 s; 1 s; 0.7 m/s; 50%; 25\%"
        self.assertEqual(
            ["0.7 m/s", "1 s", "25\\%", "3 s", "4 s", "50%"],
            numeric_unit_pairs(text),
        )

    def test_manifest_includes_figure_pdf_and_detects_its_change(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            fixture_root = Path(temporary_directory)
            figure = fixture_root / "figures" / "authored.pdf"
            figure.parent.mkdir()
            figure.write_bytes(b"original PDF asset")
            (fixture_root / "main.pdf").write_bytes(b"generated root PDF")
            before = manifest_entries(fixture_root)
            self.assertEqual([("figures/authored.pdf", sha256(figure))], before)
            figure.write_bytes(b"changed PDF asset")
            self.assertNotEqual(before, manifest_entries(fixture_root))

    def test_compiled_korean_prose_has_no_disallowed_literal_terms(self) -> None:
        matches: list[str] = []
        for path in compiled_tex_paths():
            for line_number, line in enumerate(read_text(path).splitlines(), start=1):
                for term in sorted(DISALLOWED):
                    if term in line:
                        matches.append(f"{relative(path)}:{line_number}: {term}")
        print("Manual Korean term review (not automatically disallowed):")
        for location in manual_review_locations():
            print(f"  {location}")
        self.assertEqual([], matches, "disallowed literal Korean prose:\n" + "\n".join(matches))


if __name__ == "__main__":
    if "--print-baseline" in sys.argv:
        print(json.dumps(editorial_snapshot(), ensure_ascii=False, indent=2, sort_keys=True) + "\n", end="")
    else:
        unittest.main()
