from __future__ import annotations

from typing import Any, TypedDict

from careerpilot.backend.llm import LLMConfigurationError, generate_response


class AgentState(TypedDict, total=False):
    user_query: str
    session_id: str
    history: list[dict[str, Any]]
    response: str
    metadata: dict[str, Any]


def run_specialist(state: AgentState, system_prompt: str) -> AgentState:
    """Run an LLM specialist and fall back gracefully when the provider is unavailable."""

    try:
        response = generate_response(
            system_prompt=system_prompt,
            user_query=state.get("user_query", ""),
            history=state.get("history", []),
        )
    except LLMConfigurationError as exc:
        response = f"The selected LLM provider is not configured: {exc}"
    except Exception:
        response = "I could not complete that request because the AI provider is temporarily unavailable. Please try again."
    return {"response": response}
