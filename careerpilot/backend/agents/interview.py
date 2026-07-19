from __future__ import annotations

from typing import TypedDict


class InterviewState(TypedDict, total=False):
    user_query: str
    response: str


def handle_interview(state: InterviewState) -> InterviewState:
    """Temporary interview agent stub."""

    return {
        "response": "Interview agent stub: HR and technical interview flows will be added later.",
    }
