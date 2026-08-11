"""Embed a local image set into one restricted GuardSynth review HTML file."""

from __future__ import annotations

import argparse
import base64
from datetime import date
import hashlib
import html
import json
import mimetypes
from pathlib import Path
import sys
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from cli.project_paths import project_root


ROOT = project_root(__file__)
HERE = Path(__file__).resolve().parent
SOURCE_HTML_BY_MODE = {
    "evidence": HERE / "SCENE_EVIDENCE_REVIEW.html",
    "image-only": HERE / "IMAGE_ONLY_SCENE_REVIEW.html",
}
RESTRICTED_ROOT = ROOT / "artifacts/results/restricted"
MARKER = '<div id="embeddedImageStore" hidden aria-hidden="true"></div><!-- restricted packager replaces this exact element -->'
SUPPORTED_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".gif"}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def build(
    image_dir: Path, output_dir: Path, source_ref: str, review_mode: str = "evidence"
) -> tuple[Path, dict[str, Any]]:
    image_dir = image_dir.resolve()
    output_dir = output_dir.resolve()
    if not image_dir.is_dir():
        raise FileNotFoundError(f"image directory not found: {image_dir}")
    if not output_dir.is_relative_to(RESTRICTED_ROOT.resolve()):
        raise ValueError("embedded scene images may only be written under artifacts/results/restricted")
    if output_dir.exists():
        raise FileExistsError(f"refusing to overwrite existing output: {output_dir}")

    images = sorted(
        path for path in image_dir.iterdir()
        if path.is_file() and path.suffix.lower() in SUPPORTED_SUFFIXES
    )
    if not images:
        raise ValueError("no supported images found")

    figures = []
    image_manifest = []
    for path in images:
        mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        data = base64.b64encode(path.read_bytes()).decode("ascii")
        safe_name = html.escape(path.name, quote=True)
        figures.append(
            f'<img class="embedded-scene-image" data-name="{safe_name}" '
            f'src="data:{mime};base64,{data}" alt="내장 검토 장면 {safe_name}">'
        )
        image_manifest.append({
            "filename": path.name,
            "mime_type": mime,
            "byte_count": path.stat().st_size,
            "sha256": _sha256(path),
        })

    source_html = SOURCE_HTML_BY_MODE[review_mode]
    source = source_html.read_text(encoding="utf-8")
    if source.count(MARKER) != 1:
        raise RuntimeError("embedded-image marker is missing or ambiguous")
    gallery = '<div id="embeddedImageStore" hidden aria-hidden="true">' + "".join(figures) + "</div>"
    rendered = source.replace(MARKER, gallery)

    output_dir.mkdir(parents=True)
    html_name = (
        "IMAGE_ONLY_SCENE_REVIEW_WITH_IMAGES.html"
        if review_mode == "image-only"
        else "SCENE_EVIDENCE_REVIEW_WITH_IMAGES.html"
    )
    html_path = output_dir / html_name
    html_path.write_text(rendered, encoding="utf-8")
    manifest = {
        "package_version": "guardsynth-scene-evidence-review-embedded-v0.1",
        "run_date": date.today().isoformat(),
        "input_class": "LICENSE_RESTRICTED",
        "source_ref": source_ref,
        "review_mode": review_mode,
        "embedded_image_count": len(images),
        "image_bytes_in_html": True,
        "image_bytes_in_json_csv_export": False,
        "raw_source_paths_included": False,
        "html_sha256": _sha256(html_path),
        "images": image_manifest,
        "claim_scope": "REVIEW_PRESENTATION_NOT_SCENE_GROUNDING_OR_VEHICLE_SAFETY",
    }
    _write_json(output_dir / "EMBEDDED_REVIEW_MANIFEST.json", manifest)
    (output_dir / "REPORT_KO.md").write_text(
        f"""# 이미지 내장 GuardSynth 검토 패키지

- 상태: **EXECUTED**
- 입력 등급: `LICENSE_RESTRICTED`
- 내장 이미지: {len(images)}개
- 검토 모드: `{review_mode}`
- 단일 HTML: `{html_name}`
- JSON/CSV export의 이미지 bytes: 없음

HTML을 열면 이미지별 검토 카드가 자동 생성된다. 이미지가 HTML 안에 들어 있으므로 이
파일은 공개 결과로 이동하거나 외부에 업로드하면 안 된다. 이미지 자체는 association,
geometry, transform, 규칙 또는 차량 assurance source를 대신하지 않는다.
""",
        encoding="utf-8",
    )
    return html_path, manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--source-ref", required=True)
    parser.add_argument("--review-mode", choices=tuple(SOURCE_HTML_BY_MODE), default="evidence")
    args = parser.parse_args()
    html_path, manifest = build(
        args.image_dir, args.output_dir, args.source_ref, review_mode=args.review_mode
    )
    print(json.dumps({
        "html": str(html_path),
        "embedded_image_count": manifest["embedded_image_count"],
        "input_class": manifest["input_class"],
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
