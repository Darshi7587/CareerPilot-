from __future__ import annotations

from careerpilot.backend.agents.common import AgentState
from careerpilot.backend.rag.service import get_rag_service


def handle_rag(state: AgentState) -> AgentState:
    """Answer only from the requesting session's indexed PDFs."""

    service = get_rag_service()
    session_id = state.get("session_id", "default-session")
    query = state.get("user_query", "")

    indexed = [record for record in service.registry.list(session_id) if record.status == "indexed"]
    if not indexed:
        return {
            "response": (
                "Document retrieval: I could not find indexed documents for this session. "
                "Upload PDFs on the RAG Knowledge Base page and wait for indexing to finish."
            ),
            "metadata": {"sources": [], "document_count": 0},
        }

    response = service.answer(session_id=session_id, query=query, history=state.get("history", []))
    sources = [
        f"{item['metadata']['filename']} (p. {item['metadata']['page']})"
        for item in service.retrieve(session_id, query)
    ]
    return {"response": response, "metadata": {"sources": sources, "document_count": len(indexed)}}
