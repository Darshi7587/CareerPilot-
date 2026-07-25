from __future__ import annotations

import re
from collections import Counter
from datetime import UTC, datetime
from typing import Any

from careerpilot.backend.memory.checkpoint import SQLiteCheckpointStore
from careerpilot.backend.rag.service import get_rag_service

SCORE_PATTERN = re.compile(r"(?:score|rating|mark)[:\s]*(\d{1,2})(?:\s*/\s*10)?", re.IGNORECASE)
ATS_PATTERN = re.compile(r"(?:ats|compatibility)[^0-9]*(\d{1,3})", re.IGNORECASE)
FRACTION_ATS_PATTERN = re.compile(r"(\d{1,3})\s*/\s*100")


def _extract_scores(text: str) -> list[int]:
    matches = SCORE_PATTERN.findall(text)
    scores = []
    for match in matches:
        val = int(match)
        if 1 <= val <= 10:
            scores.append(val)
    return scores


def _extract_ats(text: str) -> int | None:
    match = ATS_PATTERN.search(text)
    if match:
        value = int(match.group(1))
        if 0 <= value <= 100:
            return value
    match2 = FRACTION_ATS_PATTERN.search(text)
    if match2:
        value = int(match2.group(1))
        if 0 <= value <= 100:
            return value
    return None


def build_analytics(session_id: str, checkpoint_store: SQLiteCheckpointStore, limit: int = 100) -> dict[str, Any]:
    """Derive dashboard analytics from persisted conversation checkpoints."""

    history = checkpoint_store.history(session_id, limit=limit)
    if not history:
        # Fallback to recent checkpoints across all sessions if current session is brand new
        with checkpoint_store._connect() as connection:
            rows = connection.execute(
                "SELECT payload_json FROM checkpoints ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
        import json
        history = [json.loads(row["payload_json"]) for row in rows if row["payload_json"]]

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
        "learning_streak_days": streak or 1,
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
        try:
            day = datetime.fromisoformat(day_str).date()
        except Exception:
            continue
        if day == cursor or day == cursor.fromordinal(cursor.toordinal() - streak):
            streak += 1
            cursor = day.fromordinal(day.toordinal() - 1)
        elif streak == 0 and day == datetime.now(tz=UTC).date().fromordinal(datetime.now(tz=UTC).date().toordinal() - 1):
            streak = 1
            cursor = day.fromordinal(day.toordinal() - 1)
        else:
            break
    return max(streak, 1) if daily_activity else 0


def _skill_radar_from_routes(route_counts: Counter[str]) -> dict[str, int]:
    mapping = {
        "Resume ATS": max(route_counts.get("resume", 0) * 20, 15),
        "Company Intel": max(route_counts.get("company", 0) * 20, 15),
        "Coding DSA": max(route_counts.get("coding", 0) * 20, 15),
        "Mock Interview": max(route_counts.get("interview", 0) * 20, 15),
        "Roadmaps": max(route_counts.get("roadmap", 0) * 20, 15),
        "RAG Notes": max(route_counts.get("rag", 0) * 20, 15),
    }
    return mapping
