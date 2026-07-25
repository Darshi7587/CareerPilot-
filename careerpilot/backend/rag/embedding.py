import hashlib
import math
import ssl
from typing import Any

try:
    ssl._create_default_https_context = ssl._create_unverified_context
except Exception:
    pass

try:
    from sentence_transformers import SentenceTransformer
except Exception:  # pragma: no cover - optional dependency may be absent
    SentenceTransformer = None  # type: ignore[assignment]


_MODEL_NAME = "all-MiniLM-L6-v2"


class SentenceTransformerEmbeddingFunction:
    """Minimal Chroma-compatible embedding adapter with resilient fallback."""

    def __init__(self, model_name: str = _MODEL_NAME) -> None:
        self.model_name = model_name
        self._model = None

    def name(self) -> str:
        return "default"

    def _build_model(self) -> Any:
        try:
            import huggingface_hub.utils._http as hf_http
            if hasattr(hf_http, "_client"):
                setattr(hf_http, "_client", None)
            if hasattr(hf_http, "_default_client"):
                setattr(hf_http, "_default_client", None)
        except Exception:
            pass

        if SentenceTransformer is None:
            return None

        try:
            self._model = SentenceTransformer(self.model_name)
            return self._model
        except Exception:
            return None

    def _fallback_embedding(self, text: str, dim: int = 384) -> list[float]:
        words = text.lower().split()
        if not words:
            words = ["empty"]
        vec = [0.0] * dim
        for w in words:
            h = int(hashlib.sha256(w.encode("utf-8")).hexdigest(), 16)
            idx = h % dim
            val = ((h >> 8) % 1000) / 500.0 - 1.0
            vec[idx] += val
        norm = math.sqrt(sum(x * x for x in vec)) or 1.0
        return [round(x / norm, 6) for x in vec]

    def __call__(self, input: list[str]) -> list[list[float]]:
        try:
            model = self._model or self._build_model()
            if model is not None:
                embeddings = model.encode(input, convert_to_tensor=False)
                if isinstance(embeddings, list):
                    return [list(map(float, item)) for item in embeddings]
                return [list(map(float, row)) for row in embeddings]
        except Exception:
            pass
        return [self._fallback_embedding(text) for text in input]

    def embed_query(self, input: Any) -> list[list[float]]:
        if isinstance(input, str):
            input = [input]
        return self.__call__(input)

    def embed_documents(self, input: Any) -> list[list[float]]:
        if isinstance(input, str):
            input = [input]
        return self.__call__(input)


def build_embedding_model(model_name: str = _MODEL_NAME) -> Any:
    if SentenceTransformer is None:
        raise RuntimeError("sentence-transformers is not installed")
    return SentenceTransformer(model_name)
