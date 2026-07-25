from __future__ import annotations

from typing import Any


class DocumentChunk(dict):
    """Lightweight chunk container compatible with the RAG pipeline."""

    def __getattr__(self, item: str) -> Any:
        return self[item]


def split_text(text: str, chunk_size: int = 1000, chunk_overlap: int = 150) -> list[str]:
    """Split text into overlapping chunks using a simple beginner-friendly approach."""

    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    if chunk_overlap < 0:
        raise ValueError("chunk_overlap cannot be negative")
    if chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap must be smaller than chunk_size")

    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        if end >= len(text):
            break
        start = end - chunk_overlap
    return chunks


def split_documents(pages: list[dict[str, Any]], chunk_size: int = 1000, chunk_overlap: int = 150) -> list[DocumentChunk]:
    """Split PDF pages into chunks with metadata attached."""

    chunks: list[DocumentChunk] = []
    for page in pages:
        text = str(page.get("page_content", ""))
        if not text.strip():
            continue
        for chunk_text in split_text(text, chunk_size=chunk_size, chunk_overlap=chunk_overlap):
            if not chunk_text.strip():
                continue
            chunk = DocumentChunk(page_content=chunk_text, metadata={**page.get("metadata", {}), "source": "pdf"})
            chunks.append(chunk)
    return chunks
