from __future__ import annotations

from pathlib import Path


def load_text_file(file_path: str | Path) -> str:
    """Load a plain text file as the simplest possible document loader."""

    return Path(file_path).read_text(encoding="utf-8")
