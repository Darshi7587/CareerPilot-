from __future__ import annotations

import json
import logging
import time
from typing import Any, Literal

from fastapi import FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from careerpilot.backend.agents.planner import PlannerState, build_planner_graph
from careerpilot.backend.analytics import build_analytics
from careerpilot.backend.config import get_settings
from careerpilot.backend.llm import LLMConfigurationError, build_chat_model
from careerpilot.backend.memory.checkpoint import SQLiteCheckpointStore
from careerpilot.backend.rag.service import (
    DocumentNotFoundError,
    DocumentValidationError,
    get_rag_service,
)

settings = get_settings()
app = FastAPI(title=settings.app_name)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
planner_graph = build_planner_graph()
checkpoint_store = SQLiteCheckpointStore(settings.checkpoint_path)
logger = logging.getLogger(__name__)


class ChatRequest(BaseModel):
    """Request body for the planner endpoint."""

    message: str = Field(min_length=1)
    session_id: str = Field(default="default-session", min_length=1, max_length=128)
    focus: Literal["all", "resume", "company", "coding", "interview", "roadmap", "rag"] = "all"


class ChatResponse(BaseModel):
    """Response body returned by the planner endpoint."""

    route: str
    response: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    execution_time_ms: float = 0
    sources: list[str] = Field(default_factory=list)
    agent: str = ""
    planner_source: str = ""


class DocumentResponse(BaseModel):
    document_id: str
    session_id: str
    filename: str
    storage_path: str = ""
    checksum: str = ""
    status: str
    chunk_count: int
    created_at: str
    updated_at: str


class RAGStatusResponse(BaseModel):
    status: str
    document_count: int
    indexed_document_count: int
    chunk_count: int


class SystemStatusResponse(BaseModel):
    status: str
    app: str
    llm_provider: str
    llm_configured: bool
    llm_model: str
    memory_status: str
    rag_status: str
    database_status: str
    checkpoint_count: int


def _build_chat_query(message: str, focus: str) -> str:
    if focus == "all":
        return message
    return f"[{focus} request] {message}"


def _enrich_chat_response(result: dict[str, Any], elapsed_ms: float) -> ChatResponse:
    metadata = dict(result.get("metadata") or {})
    sources = metadata.get("sources", [])
    if isinstance(sources, str):
        sources = [sources]
    return ChatResponse(
        route=str(result.get("route", "fallback")),
        response=str(result.get("response", "")),
        metadata=metadata,
        execution_time_ms=round(elapsed_ms, 1),
        sources=list(sources),
        agent=str(result.get("route", "fallback")),
        planner_source=str(metadata.get("classification_source", "")),
    )


@app.get("/health")
def health() -> dict[str, str]:
    """Simple readiness endpoint."""

    return {"status": "ok", "app": settings.app_name}


@app.get("/status", response_model=SystemStatusResponse)
def system_status(session_id: str = Query("default-session")) -> SystemStatusResponse:
    """Report subsystem health for the settings dashboard."""

    llm_configured = True
    try:
        build_chat_model()
    except LLMConfigurationError:
        llm_configured = False

    rag = get_rag_service().status(session_id)
    memory_rows = len(checkpoint_store.history(session_id, limit=1000))

    db_ok = settings.sqlite_path.parent.exists()
    return SystemStatusResponse(
        status="ok" if llm_configured else "degraded",
        app=settings.app_name,
        llm_provider=settings.default_llm_provider,
        llm_configured=llm_configured,
        llm_model=settings.gemini_model if settings.default_llm_provider == "gemini" else settings.groq_model,
        memory_status="ready",
        rag_status=str(rag.get("status", "unknown")),
        database_status="ready" if db_ok else "missing",
        checkpoint_count=memory_rows,
    )


@app.get("/analytics")
def analytics(session_id: str = Query("default-session")) -> dict[str, Any]:
    """Return session analytics derived from conversation memory."""

    return build_analytics(session_id, checkpoint_store)


@app.get("/memory/history")
def memory_history(session_id: str = Query("default-session"), limit: int = Query(20, ge=1, le=100)) -> list[dict[str, Any]]:
    """Return recent conversation snapshots for a session."""

    return checkpoint_store.history(session_id, limit=limit)


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    """Route the user message through the planner graph and persist the result."""

    history_limit = getattr(settings, "history_limit", 8)
    history = checkpoint_store.history(request.session_id, history_limit)
    query = _build_chat_query(request.message, request.focus)
    started = time.perf_counter()
    try:
        result = planner_graph.invoke(
            {"user_query": query, "history": history, "session_id": request.session_id}
        )
        elapsed_ms = (time.perf_counter() - started) * 1000
        metadata = dict(result.get("metadata") or {})
        metadata["execution_time_ms"] = round(elapsed_ms, 1)
        metadata["created_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        checkpoint_store.save(
            session_id=request.session_id,
            step_name=result.get("route", "fallback"),
            payload={
                "user_query": query,
                "route": result.get("route", "fallback"),
                "response": result.get("response", ""),
                "metadata": metadata,
            },
        )
    except Exception as exc:
        logger.exception("Chat request failed for session %s", request.session_id)
        raise HTTPException(status_code=503, detail="CareerPilot is temporarily unavailable. Please try again.") from exc
    return _enrich_chat_response(result, elapsed_ms)


@app.post("/chat/stream")
def chat_stream(request: ChatRequest) -> StreamingResponse:
    """Stream planner response tokens as server-sent events."""

    history_limit = getattr(settings, "history_limit", 8)
    history = checkpoint_store.history(request.session_id, history_limit)
    query = _build_chat_query(request.message, request.focus)
    started = time.perf_counter()

    def event_generator():
        try:
            result = planner_graph.invoke(
                {"user_query": query, "history": history, "session_id": request.session_id}
            )
            response_text = str(result.get("response", ""))
            route = str(result.get("route", "fallback"))
            metadata = dict(result.get("metadata") or {})
            elapsed_ms = (time.perf_counter() - started) * 1000
            metadata["execution_time_ms"] = round(elapsed_ms, 1)
            metadata["created_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

            meta_payload = {
                "route": route,
                "agent": route,
                "planner_source": metadata.get("classification_source", ""),
                "execution_time_ms": metadata["execution_time_ms"],
                "sources": metadata.get("sources", []),
            }
            yield f"event: meta\ndata: {json.dumps(meta_payload)}\n\n"

            chunk_size = 48
            for index in range(0, len(response_text), chunk_size):
                yield f"event: token\ndata: {json.dumps(response_text[index : index + chunk_size])}\n\n"

            checkpoint_store.save(
                session_id=request.session_id,
                step_name=route,
                payload={
                    "user_query": query,
                    "route": route,
                    "response": response_text,
                    "metadata": metadata,
                },
            )
            yield f"event: done\ndata: {json.dumps({'status': 'ok'})}\n\n"
        except Exception as exc:
            logger.exception("Streaming chat failed for session %s", request.session_id)
            yield f"event: error\ndata: {json.dumps({'detail': str(exc)})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.get("/documents", response_model=list[DocumentResponse])
def list_documents(session_id: str = Query("default-session")) -> list[dict[str, Any]]:
    """Return uploaded documents for the current session."""

    return get_rag_service().documents(session_id)


@app.post("/documents", response_model=list[DocumentResponse])
async def upload_documents(
    files: list[UploadFile] = File(...),
    session_id: str = Form(default="default-session"),
) -> list[DocumentResponse]:
    """Save and index uploaded PDFs for the session."""

    if not files:
        raise HTTPException(status_code=400, detail="At least one file is required")

    results: list[DocumentResponse] = []
    for upload in files:
        if upload.filename is None:
            continue
        try:
            content = await upload.read()
            record = get_rag_service().save_upload(session_id, upload.filename, content)
            results.append(
                DocumentResponse(
                    document_id=record.document_id,
                    session_id=session_id,
                    filename=record.filename,
                    storage_path=str(record.storage_path),
                    checksum=record.checksum,
                    status=record.status,
                    chunk_count=record.chunk_count,
                    created_at=record.created_at,
                    updated_at=record.updated_at,
                )
            )
        except Exception as exc:  # pragma: no cover - defensive guard
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    return results


@app.post("/documents/{document_id}/reindex")
def reindex_document(document_id: str, session_id: str = Query("default-session")) -> dict[str, Any]:
    """Re-index a single uploaded document."""

    record = get_rag_service().index(document_id, session_id)
    return {"document_id": record.document_id, "status": record.status, "chunk_count": record.chunk_count}


@app.delete("/documents/{document_id}")
def delete_document(document_id: str, session_id: str = Query("default-session")) -> dict[str, str]:
    """Delete a document from the session-owned store."""

    get_rag_service().delete(document_id, session_id)
    return {"status": "deleted", "document_id": document_id}


@app.get("/rag/status")
def rag_status(session_id: str = Query("default-session")) -> dict[str, Any]:
    """Report document counts and indexing health."""

    return get_rag_service().status(session_id)
