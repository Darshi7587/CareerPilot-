from __future__ import annotations

import re
from typing import Any, Callable, Literal, TypedDict

from langgraph.graph import END, START, StateGraph

from careerpilot.backend.agents.coding import handle_coding
from careerpilot.backend.agents.company import handle_company
from careerpilot.backend.agents.interview import handle_interview
from careerpilot.backend.agents.resume import handle_resume
from careerpilot.backend.agents.roadmap import handle_roadmap
from careerpilot.backend.agents.rag import handle_rag
from careerpilot.backend.llm import LLMConfigurationError, RouteDecision, classify_with_llm

RouteName = Literal["resume", "company", "coding", "interview", "roadmap", "rag", "fallback"]

FOCUS_PATTERN = re.compile(r"^\[(\w+)\s+request\]\s*", re.IGNORECASE)
FOCUS_ROUTES = frozenset({"resume", "company", "coding", "interview", "roadmap", "rag"})


class PlannerState(TypedDict, total=False):
    """Shared graph state for the controller and the specialized agents."""

    user_query: str
    route: RouteName
    response: str
    metadata: dict[str, Any]
    history: list[dict[str, Any]]
    session_id: str


RouteClassifier = Callable[[str], RouteName]


def parse_focus_marker(user_query: str) -> tuple[str, RouteName | None]:
    """Strip UI focus prefixes such as ``[roadmap request]`` and return a forced route."""

    match = FOCUS_PATTERN.match(user_query.strip())
    if not match:
        return user_query, None
    focus = match.group(1).lower()
    if focus not in FOCUS_ROUTES:
        return user_query, None
    cleaned = user_query[match.end() :].strip()
    return cleaned or user_query, focus  # type: ignore[return-value]


def classify_query(user_query: str) -> RouteName:
    """Classify the query with simple rules so the first module is testable without an API key."""

    _, forced_route = parse_focus_marker(user_query)
    if forced_route:
        return forced_route

    normalized = user_query.lower().strip()

    resume_terms = ("resume", "cv", "ats", "upload pdf", "pdf resume", "skill gap")
    company_terms = (
        "company",
        "research",
        "interview rounds",
        "hiring process",
        "oa pattern",
        "interview experiences",
        "recent interview",
        "required skills",
        "hr round",
        "google",
        "amazon",
        "microsoft",
        "meta",
        "apple",
        "netflix",
        "nvidia",
        "adobe",
        "tcs",
        "infosys",
        "wipro",
        "accenture",
        "uber",
        "flipkart",
        "oracle",
        "salesforce",
    )
    coding_terms = (
        "code review",
        "review this code",
        "analyze code",
        "sql code",
        "leetcode",
        "debug",
        "bug",
        "time complexity",
        "space complexity",
        "better solution",
        "complexity",
        "def ",
        "class ",
        "function ",
        "```",
    )
    interview_terms = (
        "hr interview",
        "technical interview",
        "mock interview",
        "start interview",
        "interview me",
        "behavioral",
        "star format",
        "evaluate my answer",
        "submit answer",
    )
    roadmap_terms = ("roadmap", "study plan", "prep plan", "weekly plan", "schedule", "routine")
    rag_terms = (
        "rag",
        "notes",
        "document",
        "pdfs",
        "retrieve",
        "knowledge base",
        "my uploaded",
        "indexed documents",
    )

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


def _plan_route(state: PlannerState, classifier: RouteClassifier | None) -> tuple[RouteName, dict[str, Any]]:
    """Use an injected test classifier, then semantic routing with a safe local fallback."""

    query = state["user_query"]
    cleaned_query, forced_route = parse_focus_marker(query)
    if forced_route:
        return forced_route, {
            "classification_source": "focus_marker",
            "classification_reason": f"Forced route from UI focus: {forced_route}",
            "cleaned_query": cleaned_query,
        }

    if classifier is not None:
        return classifier(query), {"classification_source": "injected_classifier"}
    try:
        decision: RouteDecision = classify_with_llm(query, state.get("history", []))
        return decision.route, {"classification_source": "llm", "classification_reason": decision.rationale}
    except LLMConfigurationError as exc:
        return classify_query(query), {"classification_source": "keyword_fallback", "llm_error": str(exc)}
    except Exception:
        return classify_query(query), {"classification_source": "keyword_fallback", "llm_error": "Planner provider unavailable."}


def _fallback_handler(state: PlannerState) -> PlannerState:
    """Provide a helpful fallback response when the query is too vague for a specialist."""

    user_query = str(state.get("user_query", "")).strip()
    if not user_query:
        response = "I'm here to help with placements. You can ask about resumes, companies, interviews, coding, or study plans."
    else:
        response = (
            "I can help with placements, but I need a bit more context. "
            "Try asking about resumes, company research, interview prep, coding review, or a roadmap."
        )
    return {
        "route": "fallback",
        "response": response,
    }


def build_planner_graph(classifier: RouteClassifier | None = None) -> Any:
    """Build the LangGraph planner with conditional edges to specialist agents."""

    def route_node(state: PlannerState) -> PlannerState:
        route, metadata = _plan_route(state, classifier)
        cleaned_query, _ = parse_focus_marker(state["user_query"])
        updates: PlannerState = {"route": route, "metadata": metadata}
        if cleaned_query != state["user_query"]:
            updates["user_query"] = cleaned_query
        return updates

    graph = StateGraph(PlannerState)
    graph.add_node("route", route_node)
    graph.add_node("resume", handle_resume)
    graph.add_node("company", handle_company)
    graph.add_node("coding", handle_coding)
    graph.add_node("interview", handle_interview)
    graph.add_node("roadmap", handle_roadmap)
    graph.add_node("rag", handle_rag)
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
            "rag": "rag",
            "fallback": "fallback",
        },
    )
    graph.add_edge("resume", END)
    graph.add_edge("company", END)
    graph.add_edge("coding", END)
    graph.add_edge("interview", END)
    graph.add_edge("roadmap", END)
    graph.add_edge("rag", END)
    graph.add_edge("fallback", END)
    return graph.compile()
