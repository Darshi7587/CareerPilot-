from __future__ import annotations

from careerpilot.backend.agents.common import AgentState
from careerpilot.backend.rag.service import get_rag_service


def handle_rag(state: AgentState) -> AgentState:
    """Answer from indexed documents with safe error handling and fallback."""

    service = get_rag_service()
    session_id = state.get("session_id", "default-session")
    query = state.get("user_query", "")

    try:
        indexed = [record for record in service.registry.list(session_id) if record.status == "indexed"]
        if not indexed and hasattr(service.registry, "list_all"):
            indexed = [record for record in service.registry.list_all() if record.status == "indexed"]

        if not indexed:
            return {
                "response": (
                    "Document retrieval: I could not find indexed documents for this session. "
                    "Upload PDFs on the RAG Knowledge Base page and wait for indexing to finish."
                ),
                "metadata": {"sources": [], "document_count": 0},
            }

        response = service.answer(session_id=session_id, query=query, history=state.get("history", []))
        try:
            matches = service.retrieve(session_id, query)
            sources = [
                f"{item['metadata']['filename']} (p. {item['metadata']['page']})"
                for item in matches
            ]
        except Exception:
            sources = [rec.filename for rec in indexed]

        return {"response": response, "metadata": {"sources": sources, "document_count": len(indexed)}}
    except Exception as exc:
        return {
            "response": f"I processed your document request, but encountered an error: {exc}",
            "metadata": {"sources": [], "document_count": 0},
        }
