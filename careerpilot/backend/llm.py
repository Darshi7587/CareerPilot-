


from __future__ import annotations

from typing import Any, Literal

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from careerpilot.backend.config import Settings, get_settings

RouteName = Literal["resume", "company", "coding", "interview", "roadmap", "rag", "fallback"]


class RouteDecision(BaseModel):
    """Validated output returned by the semantic planner."""

    route: RouteName
    rationale: str = Field(min_length=1, max_length=240)


class LLMConfigurationError(RuntimeError):
    """Raised when the selected LLM provider has not been configured."""


def build_chat_model(settings: Settings | None = None) -> Any:
    """Create the configured LangChain chat model without making a network call."""

    active_settings = settings or get_settings()
    provider = active_settings.default_llm_provider.lower()
    if provider == "gemini" and active_settings.gemini_api_key:
        from langchain_google_genai import ChatGoogleGenerativeAI

        return ChatGoogleGenerativeAI(
            model="gemini-2.0-flash",
            api_key=active_settings.gemini_api_key,
            temperature=0,
        )

    if provider == "groq" and active_settings.groq_api_key:
        from langchain_groq import ChatGroq

        return ChatGroq(
            model="llama-3.3-70b-versatile",
            api_key=active_settings.groq_api_key,
            temperature=0,
        )

    if active_settings.gemini_api_key:
        from langchain_google_genai import ChatGoogleGenerativeAI

        return ChatGoogleGenerativeAI(model="gemini-2.0-flash", api_key=active_settings.gemini_api_key, temperature=0)

    if active_settings.groq_api_key:
        from langchain_groq import ChatGroq

        return ChatGroq(model="llama-3.3-70b-versatile", api_key=active_settings.groq_api_key, temperature=0)

    raise LLMConfigurationError("No LLM provider has been configured.")


def recent_messages(history: list[dict[str, Any]]) -> list[HumanMessage | AIMessage]:
    """Convert persisted snapshots into bounded LangChain conversation messages."""

    messages: list[HumanMessage | AIMessage] = []
    for item in history:
        query = str(item.get("user_query", "")).strip()
        response = str(item.get("response", "")).strip()
        if query:
            messages.append(HumanMessage(content=query))
        if response:
            messages.append(AIMessage(content=response))
    return messages


def generate_response(system_prompt: str, user_query: str, history: list[dict[str, Any]]) -> str:
    """Invoke the configured LLM for a specialist response."""

    model = build_chat_model()
    result = model.invoke([SystemMessage(content=system_prompt), *recent_messages(history), HumanMessage(content=user_query)])
    content = result.content
    if isinstance(content, str):
        return content.strip()
    return str(content).strip()


def stream_response(system_prompt: str, user_query: str, history: list[dict[str, Any]]):
    """Stream tokens from the configured LLM for a specialist response."""

    model = build_chat_model()
    messages = [SystemMessage(content=system_prompt), *recent_messages(history), HumanMessage(content=user_query)]
    for chunk in model.stream(messages):
        content = chunk.content
        if isinstance(content, str) and content:
            yield content
        elif content:
            yield str(content)


def classify_with_llm(user_query: str, history: list[dict[str, Any]]) -> RouteDecision:
    """Route a placement request with provider-native structured output."""

    planner_prompt = """You are the CareerPilot routing planner. Choose exactly one route:
resume (resume/CV/ATS feedback), company (company hiring research), coding (code, bugs, DSA),
interview (mock, HR, behavioral, technical interview coaching), roadmap (study plan),
rag (questions about the user's stored documents/notes), or fallback (unrelated/ambiguous).
Use the user's intent, not only literal keywords. Return the requested structured decision."""
    model = build_chat_model().with_structured_output(RouteDecision)
    result = model.invoke([SystemMessage(content=planner_prompt), *recent_messages(history), HumanMessage(content=user_query)])
    if not isinstance(result, RouteDecision):
        result = RouteDecision.model_validate(result)
    return result
