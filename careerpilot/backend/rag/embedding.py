from __future__ import annotations

from sentence_transformers import SentenceTransformer


_MODEL_NAME = "all-MiniLM-L6-v2"


def build_embedding_model(model_name: str = _MODEL_NAME) -> SentenceTransformer:
    """Create the sentence transformer used for document embeddings."""

    return SentenceTransformer(model_name)
