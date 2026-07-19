from __future__ import annotations

from typing import TypedDict


class RoadmapState(TypedDict, total=False):
    user_query: str
    response: str


def handle_roadmap(state: RoadmapState) -> RoadmapState:
    """Temporary roadmap agent stub."""

    return {
        "response": "Roadmap agent stub: personalized DSA planning will be added later.",
    }
