from __future__ import annotations

from typing import TypedDict


class CodingState(TypedDict, total=False):
    user_query: str
    response: str


def handle_coding(state: CodingState) -> CodingState:
    """Temporary coding feedback agent stub."""

    return {
        "response": "Coding agent stub: bug review, complexity analysis, and improvements will be added later.",
    }
