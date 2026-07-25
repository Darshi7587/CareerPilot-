from __future__ import annotations

import re
from collections import Counter
from datetime import UTC, datetime
from typing import Any

from careerpilot.backend.memory.checkpoint import SQLiteCheckpointStore
from careerpilot.backend.rag.service import get_rag_service

SCORE_PATTERN = re.compile(r"(?:score|rating)[:\s]*(\d{1,2})(?:\s*/\s*10)?", re.IGNORECASE)
ATS_PATTERN = re.compile(r"ats[^0-9]*(\d{1,3})", re.IGNORECASE)


def _extract_scores(text: str) -> list[int]:
    return [int(match) for match in SCORE_PATTERN.findall(text) if 1 <= int(match) <= 10]


def _extract_ats(text: str) -> int | None:
    match = ATS_PATTERN.search(text)
    if not match:
        return None
    value = int(match.group(1))
    return value if 0 <= value <= 100 else None


def build_analytics(session_id: str, checkpoint_store: SQLiteCheckpointStore, limit: int = 100) -> dict[str, Any]:
    """Derive dashboard analytics from persisted conversation checkpoints."""

    history = checkpoint_store.history(session_id, limit=limit)
    route_counts: Counter[str] = Counter()
    daily_activity: Counter[str] = Counter()
    interview_scores: list[int] = []
    resume_scores: list[int] = []
    coding_sessions = 0
    company_research = 0
    recent: list[dict[str, Any]] = []

    for item in history:
        route = str(item.get("route", "unknown"))
        route_counts[route] += 1
        response = str(item.get("response", ""))
        query = str(item.get("user_query", ""))
        metadata = item.get("metadata") or {}

        if route == "interview":
            interview_scores.extend(_extract_scores(response))
        elif route == "resume":
            ats = _extract_ats(response)
            if ats is not None:
                resume_scores.append(ats)
        elif route == "coding":
            coding_sessions += 1
        elif route == "company":
            company_research += 1

        created = metadata.get("created_at") or metadata.get("timestamp")
        if isinstance(created, str) and created[:10]:
            daily_activity[created[:10]] += 1

        recent.append(
            {
                "route": route,
                "query": query[:160],
                "response_preview": response[:160],
                "planner_source": metadata.get("classification_source", ""),
            }
        )

    streak = _compute_streak(daily_activity)
    rag_status = get_rag_service().status(session_id)

    return {
        "session_id": session_id,
        "total_interactions": len(history),
        "route_counts": dict(route_counts),
        "agents_used": len(route_counts),
        "interview_score_avg": round(sum(interview_scores) / len(interview_scores), 1) if interview_scores else 0,
        "interview_scores": interview_scores[-20:],
        "resume_score_latest": resume_scores[-1] if resume_scores else 0,
        "resume_scores": resume_scores[-20:],
        "coding_sessions": coding_sessions,
        "company_research_count": company_research,
        "problems_solved": coding_sessions,
        "learning_streak_days": streak,
        "daily_activity": dict(sorted(daily_activity.items())),
        "rag": rag_status,
        "recent_activity": list(reversed(recent[-12:])),
        "skill_radar": _skill_radar_from_routes(route_counts),
    }


def _compute_streak(daily_activity: Counter[str]) -> int:
    if not daily_activity:
        return 0
    days = sorted(daily_activity.keys(), reverse=True)
    streak = 0
    cursor = datetime.now(tz=UTC).date()
    for day_str in days:
        day = datetime.fromisoformat(day_str).date()
        if day == cursor or day == cursor.fromordinal(cursor.toordinal() - streak):
            streak += 1
            cursor = day.fromordinal(day.toordinal() - 1)
        elif streak == 0 and day == datetime.now(tz=UTC).date().fromordinal(datetime.now(tz=UTC).date().toordinal() - 1):
            streak = 1
            cursor = day.fromordinal(day.toordinal() - 1)
        else:
            break
    return streak


def _skill_radar_from_routes(route_counts: Counter[str]) -> dict[str, int]:
    mapping = {
        "Resume": route_counts.get("resume", 0),
        "Company Prep": route_counts.get("company", 0),
        "Coding": route_counts.get("coding", 0),
        "Interview": route_counts.get("interview", 0),
        "Roadmap": route_counts.get("roadmap", 0),
        "RAG / Notes": route_counts.get("rag", 0),
    }
    return mapping
