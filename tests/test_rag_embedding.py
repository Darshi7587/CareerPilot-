from __future__ import annotations

from unittest.mock import patch

from careerpilot.backend.rag.embedding import SentenceTransformerEmbeddingFunction


def test_sentence_transformers_embedding_function_exposes_chroma_compatible_name() -> None:
    with patch("careerpilot.backend.rag.embedding.SentenceTransformer") as mock_transformer:
        mock_transformer.return_value.encode.return_value = [[0.1, 0.2]]

        embedding_function = SentenceTransformerEmbeddingFunction(model_name="dummy")

        assert embedding_function.name() == "default"
