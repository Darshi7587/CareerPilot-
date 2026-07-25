from __future__ import annotations

import logging

from careerpilot.backend.agents.common import AgentState, run_specialist
from careerpilot.backend.config import get_settings
from careerpilot.backend.tools.search import duckduckgo_search

logger = logging.getLogger(__name__)

_COMPANY_PROMPT = """You are CareerPilot's expert company research analyst.

When the user asks about a company, provide comprehensive hiring intelligence using the web search results provided.

## Your Analysis Must Cover:

### 1. Company Overview
- Brief description of the company and its tech stack
- Company culture and work environment

### 2. Hiring Process
- Detailed breakdown of interview rounds (Online Assessment → Technical → HR → Managerial)
- What to expect at each stage
- Timeline from application to offer

### 3. Online Assessment (OA) Pattern
- Types of questions (MCQ, coding, aptitude)
- Difficulty level
- Time limits
- Platforms used (HackerRank, CodeSignal, etc.)

### 4. Technical Interview Details
- Common DSA topics asked
- System design questions (if applicable)
- CS fundamental topics emphasized
- Language-specific questions

### 5. HR/Behavioral Round
- Common HR questions asked
- Company values they look for
- Salary negotiation tips

### 6. Required Skills
- Must-have technical skills
- Preferred programming languages
- Tools and frameworks

### 7. Recent Interview Experiences
- Summarize any recent interview experiences from the web results
- Note trends and changes in the hiring process

### 8. Preparation Tips
- Specific resources to study
- Key topics to focus on
- Common mistakes to avoid
- Timeline recommendation for preparation

**Important Rules:**
- Only state facts supported by the web search snippets
- Clearly label uncertain or time-sensitive claims
- Cite the supplied URLs as sources
- If information is unavailable, say so honestly rather than guessing

Format output in clean markdown with headers and bullet points."""


def handle_company(state: AgentState) -> AgentState:
    """Research a company with live web search and synthesize hiring intelligence."""
    query = state.get("user_query", "")
    try:
        results = duckduckgo_search(query, max_results=get_settings().duckduckgo_max_results)
        evidence = "\n".join(
            f"- {item['title']}: {item['body']} ({item['href']})" for item in results
        )
    except Exception:
        logger.warning("Web search failed for company query", exc_info=True)
        evidence = "No live web results were available. State uncertainty instead of inventing current facts."

    enriched_state = {
        **state,
        "user_query": f"{query}\n\nWeb research snippets:\n{evidence}",
    }
    result = run_specialist(enriched_state, _COMPANY_PROMPT)

    # Store research results in RAG for future retrieval
    try:
        from careerpilot.backend.rag.service import get_rag_service
        service = get_rag_service()
        session_id = state.get("session_id", "default-session")
        response_text = result.get("response", "")
        if response_text and len(response_text) > 50:
            # Store as a text chunk in ChromaDB for future retrieval
            chunk_id = f"company-research-{hash(query) % 100000}"
            service.collection.upsert(
                ids=[chunk_id],
                documents=[response_text[:4000]],
                metadatas=[{
                    "document_id": "company-research",
                    "session_id": session_id,
                    "filename": f"research-{query[:50]}.md",
                    "page": 1,
                    "chunk_index": 0,
                }],
            )
    except Exception:
        logger.debug("Could not store company research in RAG", exc_info=True)

    return result
