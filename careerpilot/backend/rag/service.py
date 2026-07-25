from __future__ import annotations

import hashlib
import uuid
from dataclasses import asdict
from datetime import UTC, datetime
from functools import lru_cache
from pathlib import Path
from typing import Any, Callable

import chromadb

from careerpilot.backend.config import Settings, get_settings
from careerpilot.backend.llm import LLMConfigurationError, generate_response
from careerpilot.backend.rag.embedding import SentenceTransformerEmbeddingFunction
from careerpilot.backend.rag.loader import load_pdf
from careerpilot.backend.rag.repository import DocumentRecord, DocumentRegistry
from careerpilot.backend.rag.splitter import split_documents


class DocumentNotFoundError(LookupError):
    """Raised when a document is absent or belongs to another session."""


class DocumentValidationError(ValueError):
    """Raised when uploaded content is not a permitted document."""


class RAGService:
    """Own PDF storage, Chroma indexing, and document-grounded answering."""

    def __init__(
        self,
        settings: Settings | None = None,
        embedding_function: Callable[[list[str]], list[list[float]]] | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.upload_path = self.settings.upload_path.resolve()
        self.upload_path.mkdir(parents=True, exist_ok=True)
        self.registry = DocumentRegistry(self.settings.sqlite_path)
        self.client = chromadb.PersistentClient(path=str(self.settings.chroma_path))
        self.collection = self.client.get_or_create_collection(
            name="careerpilot_documents",
            embedding_function=embedding_function or SentenceTransformerEmbeddingFunction(),
            metadata={"hnsw:space": "cosine"},
        )

    def _stored_path(self, document_id: str, filename: str) -> Path:
        safe_name = Path(filename).name
        return self.upload_path / f"{document_id}-{safe_name}"

    def _assert_inside_upload_path(self, path: Path) -> Path:
        resolved = path.resolve()
        if self.upload_path not in resolved.parents:
            raise DocumentValidationError("Document storage path is invalid.")
        return resolved

    def save_upload(self, session_id: str, filename: str, content: bytes) -> DocumentRecord:
        """Validate, persist, and index a single PDF upload."""

        if Path(filename).suffix.lower() != ".pdf":
            raise DocumentValidationError("Only PDF uploads are supported.")
        if not content:
            raise DocumentValidationError("The uploaded PDF is empty.")
        if len(content) > self.settings.max_upload_bytes:
            raise DocumentValidationError(
                f"The uploaded PDF exceeds the {self.settings.max_upload_bytes} byte limit."
            )

        document_id = str(uuid.uuid4())
        destination = self._stored_path(document_id, filename)
        destination.write_bytes(content)
        now = datetime.now(tz=UTC).isoformat()
        record = DocumentRecord(
            document_id=document_id,
            session_id=session_id,
            filename=Path(filename).name,
            storage_path=str(destination),
            checksum=hashlib.sha256(content).hexdigest(),
            status="pending",
            chunk_count=0,
            created_at=now,
            updated_at=now,
        )
        self.registry.create(record)
        try:
            return self.index(document_id, session_id)
        except Exception:
            self.registry.update_status(document_id, "failed")
            raise

    def _add_chunks(self, document_id: str, session_id: str, record: DocumentRecord, chunks: list[Any]) -> None:
        ids: list[str] = []
        texts: list[str] = []
        metadatas: list[dict[str, str | int]] = []
        for index, chunk in enumerate(chunks):
            text = str(chunk.page_content).strip()
            if not text:
                continue
            ids.append(f"{document_id}:{index}")
            texts.append(text)
            metadatas.append(
                {
                    "document_id": document_id,
                    "session_id": session_id,
                    "filename": record.filename,
                    "page": int(chunk.metadata.get("page", 0)) + 1,
                    "chunk_index": index,
                }
            )
        if not texts:
            raise DocumentValidationError("No readable text was found in the uploaded document.")
        self.collection.add(ids=ids, documents=texts, metadatas=metadatas)

    def index(self, document_id: str, session_id: str) -> DocumentRecord:
        """Rebuild one document's chunks from the stored source PDF."""

        record = self.registry.get(document_id, session_id)
        if record is None:
            raise DocumentNotFoundError("Document not found.")
        source_path = self._assert_inside_upload_path(Path(record.storage_path))
        if not source_path.is_file():
            raise DocumentNotFoundError("The stored source PDF is missing.")

        self.collection.delete(where={"document_id": document_id})
        if source_path.suffix.lower() == ".pdf":
            pages = load_pdf(source_path)
            chunks = split_documents(
                pages,
                chunk_size=self.settings.rag_chunk_size,
                chunk_overlap=self.settings.rag_chunk_overlap,
            )
        else:
            text = source_path.read_text(encoding="utf-8")
            pages = [{"page_content": text, "metadata": {"page": 0}}]
            chunks = split_documents(
                pages,
                chunk_size=self.settings.rag_chunk_size,
                chunk_overlap=self.settings.rag_chunk_overlap,
            )
        if not chunks:
            raise DocumentValidationError("No readable text was found in the uploaded document.")

        self._add_chunks(document_id, session_id, record, chunks)
        self.registry.update_status(document_id, "indexed", len(chunks))
        updated = self.registry.get(document_id, session_id)
        if updated is None:  # pragma: no cover - defensive guard
            raise DocumentNotFoundError("Document disappeared during indexing.")
        return updated

    def save_text_upload(self, session_id: str, filename: str, content: bytes) -> DocumentRecord:
        """Persist a text-based document and add it to the RAG index."""

        if not content:
            raise DocumentValidationError("The uploaded document is empty.")
        if len(content) > self.settings.max_upload_bytes:
            raise DocumentValidationError(
                f"The uploaded document exceeds the {self.settings.max_upload_bytes} byte limit."
            )

        document_id = str(uuid.uuid4())
        destination = self._stored_path(document_id, filename)
        destination.write_bytes(content)
        now = datetime.now(tz=UTC).isoformat()
        record = DocumentRecord(
            document_id=document_id,
            session_id=session_id,
            filename=Path(filename).name,
            storage_path=str(destination),
            checksum=hashlib.sha256(content).hexdigest(),
            status="pending",
            chunk_count=0,
            created_at=now,
            updated_at=now,
        )
        self.registry.create(record)
        try:
            return self.index(document_id, session_id)
        except Exception:
            self.registry.update_status(document_id, "failed")
            raise

    def delete(self, document_id: str, session_id: str) -> None:
        """Delete a session-owned document from Chroma, registry, and local storage."""

        record = self.registry.get(document_id, session_id)
        if record is None:
            raise DocumentNotFoundError("Document not found.")
        self.collection.delete(where={"document_id": document_id})
        path = self._assert_inside_upload_path(Path(record.storage_path))
        if path.exists():
            path.unlink()
        self.registry.delete(document_id, session_id)

    def documents(self, session_id: str) -> list[dict[str, Any]]:
        """Return session-owned document metadata safe for API/UI display."""

        return [asdict(record) for record in self.registry.list(session_id)]

    def status(self, session_id: str) -> dict[str, int | str]:
        records = self.registry.list(session_id)
        return {
            "status": "ready",
            "document_count": len(records),
            "indexed_document_count": sum(record.status == "indexed" for record in records),
            "chunk_count": sum(record.chunk_count for record in records),
        }

    def retrieve(self, session_id: str, query: str) -> list[dict[str, Any]]:
        """Retrieve only chunks belonging to the requesting session."""

        if not any(record.status == "indexed" for record in self.registry.list(session_id)):
            return []
        result = self.collection.query(
            query_texts=[query],
            n_results=self.settings.rag_top_k,
            where={"session_id": session_id},
            include=["documents", "metadatas", "distances"],
        )
        documents = result.get("documents", [[]])[0] or []
        metadatas = result.get("metadatas", [[]])[0] or []
        distances = result.get("distances", [[]])[0] or []
        return [
            {"content": text, "metadata": metadata, "distance": distance}
            for text, metadata, distance in zip(documents, metadatas, distances)
        ]

    def answer(self, session_id: str, query: str, history: list[dict[str, Any]]) -> str:
        """Generate an answer grounded exclusively in retrieved chunks and cite every source."""

        matches = self.retrieve(session_id, query)
        if not matches:
            return "I could not find indexed documents for this session that answer that question. Upload PDFs or ask about their content after indexing finishes."
        context = "\n\n".join(
            f"Source: {item['metadata']['filename']} page {item['metadata']['page']}\n{item['content']}"
            for item in matches
        )
        prompt = (
            "You are CareerPilot's document-grounded assistant. Answer only using the supplied context. "
            "If the context does not answer the question, say that clearly. Do not use outside knowledge.\n\n"
            f"CONTEXT:\n{context}"
        )
        try:
            response = generate_response(prompt, query, history)
        except LLMConfigurationError as exc:
            return f"The documents were retrieved, but the selected LLM provider is not configured: {exc}"
        citations = "\n".join(
            f"- [{item['metadata']['filename']}, p. {item['metadata']['page']}]"
            for item in matches
        )
        return f"{response}\n\nSources:\n{citations}"


@lru_cache(maxsize=1)
def get_rag_service() -> RAGService:
    """Return the process-wide RAG service and persistent vector-store client."""

    return RAGService()
