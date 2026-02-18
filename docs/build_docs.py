"""Minimal docs builder for M0 demo mode.

This keeps the docs pipeline credential-free and offline-safe until full Sphinx
integration lands in a later milestone.
"""

from __future__ import annotations

from html import escape
from pathlib import Path

DOCS_DIR = Path(__file__).parent
BUILD_DIR = DOCS_DIR / "_build" / "html"

PAGES = [
    "index.md",
    "gallery.md",
    "forecasts.md",
    "installation.md",
]


def render_page(markdown_name: str) -> None:
    source = DOCS_DIR / markdown_name
    target_name = markdown_name.replace(".md", ".html")
    target = BUILD_DIR / target_name

    text = source.read_text(encoding="utf-8")
    title = text.splitlines()[0].lstrip("# ") if text.strip() else markdown_name

    html = (
        "<!doctype html>\n"
        "<html lang=\"en\">\n"
        "<head><meta charset=\"utf-8\"><title>{title}</title></head>\n"
        "<body>\n"
        "<main>\n"
        "<h1>{title}</h1>\n"
        "<pre>{content}</pre>\n"
        "</main>\n"
        "</body></html>\n"
    ).format(title=escape(title), content=escape(text))

    target.write_text(html, encoding="utf-8")


def main() -> int:
    BUILD_DIR.mkdir(parents=True, exist_ok=True)
    for page in PAGES:
        render_page(page)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
