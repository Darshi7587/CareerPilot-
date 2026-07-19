from __future__ import annotations

from typing import Any, Callable, Literal, TypedDict

from langgraph.graph import END, START, StateGraph

from careerpilot.backend.agents.coding import handle_coding
from careerpilot.backend.agents.company import handle_company
from careerpilot.backend.agents.interview import handle_interview
from careerpilot.backend.agents.resume import handle_resume
from careerpilot.backend.agents.roadmap import handle_roadmap

RouteName = Literal["resume", "company", "coding", "interview", "roadmap", "rag", "fallback"]


class PlannerState(TypedDict, total=False):
    """Shared graph state for the controller and the specialized agents."""

    user_query: str
    route: RouteName
    response: str
    metadata: dict[str, Any]


RouteClassifier = Callable[[str], RouteName]


def classify_query(user_query: str) -> RouteName:
    """Classify the query with simple rules so the first module is testable without an API key."""

    normalized = user_query.lower().strip()

    resume_terms = ("resume", "cv", "ats", "upload pdf", "pdf resume", "skill gap")
    company_terms = (
        "company",
        "hiring process",
        "oa pattern",
        "interview experiences",
        "recent interview",
        "required skills",
        "hr round",
    )
    coding_terms = (
        "code review",
        "debug",
        "bug",
        "time complexity",
        "space complexity",
        "better solution",
        "complexity",
    )
    interview_terms = (
        "hr interview",
        "technical interview",
        "mock interview",
        "interview me",
        "behavioral",
        "star format",
    )
    roadmap_terms = ("roadmap", "study plan", "prep plan", "weekly plan", "schedule", "routine")
    rag_terms = ("rag", "notes", "document", "pdfs", "retrieve", "knowledge base")

    if any(term in normalized for term in resume_terms):
        return "resume"
    if any(term in normalized for term in company_terms):
        return "company"
    if any(term in normalized for term in coding_terms):
        return "coding"
    if any(term in normalized for term in interview_terms):
        return "interview"
    if any(term in normalized for term in roadmap_terms):
        return "roadmap"
    if any(term in normalized for term in rag_terms):
        return "rag"
    return "fallback"


def _route_planner(state: PlannerState) -> PlannerState:
    """Add the routing decision to the graph state."""

    route = classify_query(state["user_query"])
    return {
        "route": route,
        "metadata": {
            "classification_reason": "keyword_router",
        },
    }


def _fallback_handler(state: PlannerState) -> PlannerState:
    """Provide a safe default response when the query does not match a specialized agent."""

    return {
        "response": "I could not confidently classify this request yet. Please ask about resumes, companies, interviews, coding, roadmaps, or study materials.",
    }


def build_planner_graph(classifier: RouteClassifier | None = None) -> Any:
    """Build the LangGraph planner with conditional edges to the first agent stubs."""

    route_classifier = classifier or classify_query

    def route_node(state: PlannerState) -> PlannerState:
        return {"route": route_classifier(state["user_query"])}

    graph = StateGraph(PlannerState)
    graph.add_node("route", route_node)
    graph.add_node("resume", handle_resume)
    graph.add_node("company", handle_company)
    graph.add_node("coding", handle_coding)
    graph.add_node("interview", handle_interview)
    graph.add_node("roadmap", handle_roadmap)
    graph.add_node("fallback", _fallback_handler)

    graph.add_edge(START, "route")
    graph.add_conditional_edges(
        "route",
        lambda state: state["route"],
        {
            "resume": "resume",
            "company": "company",
            "coding": "coding",
            "interview": "interview",
            "roadmap": "roadmap",
            "rag": "fallback",
            "fallback": "fallback",
        },
    )
    graph.add_edge("resume", END)
    graph.add_edge("company", END)
    graph.add_edge("coding", END)
    graph.add_edge("interview", END)
    graph.add_edge("roadmap", END)
    graph.add_edge("fallback", END)
    return graph.compile()
