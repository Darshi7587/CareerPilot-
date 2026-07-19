from __future__ import annotations

from typing import Any

from duckduckgo_search import DDGS


def duckduckgo_search(query: str, max_results: int = 5) -> list[dict[str, Any]]:
    """Run a small DuckDuckGo search and return a structured result list."""

    results: list[dict[str, Any]] = []
    with DDGS() as ddgs:
        for result in ddgs.text(query, max_results=max_results):
            results.append(
                {
                    "title": result.get("title", ""),
                    "body": result.get("body", ""),
                    "href": result.get("href", ""),
                }
            )
    return results
