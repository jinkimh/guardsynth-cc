"""Locate exact response excerpts and verify the current compiled package."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import unicodedata

from sync_responses import resolve_references

SOURCE = Path(__file__).resolve().parent
NAMES = ("main", "main-clean", "response-to-reviewer-1", "response-to-reviewer-2", "response-to-reviewer-3")


def normalize(text):
    return "".join(character for character in unicodedata.normalize("NFKC", text).casefold()
                   if character.isalnum())


def visible_tex(text):
    text = resolve_references(text)
    text = text.replace(r"\_", "_").replace(r"\%", "%")
    text = re.sub(r"\\[A-Za-z]+\*?", "", text)
    return normalize(text)


def pages(name):
    result = subprocess.run(["mutool", "draw", "-F", "txt", "-o", "-", str(SOURCE / (name + ".pdf"))],
                            check=True, capture_output=True, text=True)
    # The article and response templates put only a page number in the footer.
    return [re.sub(r"\n\s*\d+\s*$", "", page)
            for page in result.stdout.rstrip("\f\n").split("\f")]


def split_with_float(needle, page, cut, gap=1500):
    """True when the excerpt occurs as two parts separated by at most `gap` characters."""
    start = page.find(needle[:cut])
    if start < 0:
        return False
    rest = page.find(needle[cut:], start + cut)
    return 0 <= rest - (start + cut) <= gap


def locate():
    metadata = json.loads((SOURCE / "response_excerpt_sources.json").read_text())
    article = [normalize(page) for page in pages("main")]
    locations = ["% Generated from exact excerpts in the current main.pdf."]
    matches = {}
    for identity, descriptor in metadata.items():
        assert descriptor["quote"] in (SOURCE / descriptor["source"]).read_text(), identity
        needle = visible_tex(descriptor["rendered_quote"])
        found = [number for number, page in enumerate(article, 1) if needle in page]
        if not found:
            for index in range(len(article) - 1):
                if needle in article[index] + article[index + 1]:
                    found = [index + 1, index + 2]
                    break
        if not found:
            # A float placed at a column top can interrupt an excerpt in the extracted text.
            for number, page in enumerate(article, 1):
                if any(split_with_float(needle, page, cut) for cut in range(20, len(needle) - 20)):
                    found = [number]
                    break
        assert found, "Excerpt not found in the article PDF: " + identity
        matches[identity] = found
        label = ", ".join(map(str, found)) + "쪽"
        locations.append(r"\expandafter\def\csname quotepages@" + identity + r"\endcsname{" + label + "}")
    assert len(matches) == 28
    (SOURCE / "quote-locations.tex").write_text("\n".join(locations) + "\n")
    return matches


def verify():
    matches = locate()
    article = normalize("".join(pages("main")))
    clean = normalize("".join(pages("main-clean")))
    assert article == clean, "Marked and clean article text differs"
    metadata = json.loads((SOURCE / "response_excerpt_sources.json").read_text())
    locations = (SOURCE / "manuscript-locations.tex").read_text()
    warnings = {}
    for reviewer, count in [(1, 9), (2, 8), (3, 11)]:
        name = f"response-to-reviewer-{reviewer}"
        source = (SOURCE / (name + ".tex")).read_text()
        assert source.count(r"\begin{reviewitem}") == count
        assert source.count(r"\begin{reviewercomment}") == count
        assert source.count(r"\begin{manuscriptrevision}") == count
        response_text = normalize("".join(pages(name)))
        for identity, descriptor in metadata.items():
            if identity.startswith(f"R{reviewer}-"):
                assert descriptor["rendered_quote"] in source, identity
                assert visible_tex(descriptor["rendered_quote"]) in response_text, identity
                assert "mloc@" + descriptor["label"] in locations, identity
    for name in NAMES:
        log = (SOURCE / (name + ".log")).read_text()
        forbidden = ("Overfull", "Missing character:", "Undefined control sequence", "undefined references",
                     "undefined citations", "Citation `", "Reference `", "Fatal error")
        assert not any(word in log for word in forbidden), "Unresolved compiler diagnostics: " + name
        warnings[name] = sorted(set(re.findall(r"(?:LaTeX|Package [\w-]+) .*Warning:[^\n]*", log)))
    report = {
        "status": "PASS", "excerpts_verified": len(matches), "excerpt_pages": matches,
        "marked_clean_text_identical": True, "review_items": {"R1": 9, "R2": 8, "R3": 11},
        "pdfs": {name: {"pages": len(pages(name)),
                         "sha256": hashlib.sha256((SOURCE / (name + ".pdf")).read_bytes()).hexdigest()}
                 for name in NAMES},
        "remaining_compiler_warnings": warnings,
    }
    (SOURCE / "document_validation.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({key: report[key] for key in ("status", "excerpts_verified", "marked_clean_text_identical", "review_items")}, ensure_ascii=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--locate", action="store_true")
    args = parser.parse_args()
    if args.locate:
        print("Located", len(locate()), "excerpts in the article PDF")
    else:
        verify()
