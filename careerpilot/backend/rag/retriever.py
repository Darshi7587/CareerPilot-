from __future__ import annotations

from careerpilot.backend.rag.service import RAGService, get_rag_service


def build_retriever() -> RAGService:
    """Return the persistent Chroma-backed retriever service."""

    return get_rag_service()
