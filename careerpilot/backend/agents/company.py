from __future__ import annotations

from typing import TypedDict


class CompanyState(TypedDict, total=False):
    user_query: str
    response: str


def handle_company(state: CompanyState) -> CompanyState:
    """Temporary company research agent stub."""

    return {
        "response": "Company agent stub: DuckDuckGo-based company research will be implemented later.",
    }
