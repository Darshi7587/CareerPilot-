from __future__ import annotations

from careerpilot.backend.agents.planner import build_planner_graph, classify_query


def test_company_prompt_routes_to_company() -> None:
    result = classify_query("Research Amazon interview rounds and hiring process")

    assert result == "company"


def test_coding_prompt_routes_to_coding() -> None:
    result = classify_query("Review this SQL code for bugs and improvements")

    assert result == "coding"


def test_rag_route_has_a_real_graph_node() -> None:
    graph = build_planner_graph(classifier=classify_query)
    result = graph.invoke({"user_query": "Use RAG to retrieve notes from my knowledge base", "history": []})

    assert result["route"] == "rag"
    assert "Document retrieval" in str(result["response"])


def test_focus_marker_routes_deterministically_without_an_llm() -> None:
    result = classify_query("[roadmap request] Help me prepare")

    assert result == "roadmap"
