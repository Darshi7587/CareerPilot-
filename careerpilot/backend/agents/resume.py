from __future__ import annotations

from typing import TypedDict


class ResumeState(TypedDict, total=False):
    user_query: str
    response: str


def handle_resume(state: ResumeState) -> ResumeState:
    """Temporary resume agent stub used while the planner is being built."""

    return {
        "response": "Resume agent stub: upload handling, ATS analysis, and skill gaps will be added in the next module.",
    }
