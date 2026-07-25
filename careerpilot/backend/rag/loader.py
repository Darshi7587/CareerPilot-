from __future__ import annotations

from pathlib import Path

from pypdf import PdfReader


def load_text_file(file_path: str | Path) -> str:
    """Load a plain text file as the simplest possible document loader."""

    return Path(file_path).read_text(encoding="utf-8")


def load_pdf(file_path: str | Path) -> list[dict[str, str | int]]:
    """Extract each page of a PDF into a lightweight document-like structure."""

    reader = PdfReader(str(file_path))
    pages: list[dict[str, str | int]] = []
    for index, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        pages.append({"page_content": text, "metadata": {"page": index}})
    return pages
