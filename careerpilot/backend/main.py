from __future__ import annotations

from fastapi import FastAPI
from pydantic import BaseModel, Field

from careerpilot.backend.agents.planner import PlannerState, build_planner_graph
from careerpilot.backend.config import get_settings
from careerpilot.backend.memory.checkpoint import SQLiteCheckpointStore

settings = get_settings()
app = FastAPI(title=settings.app_name)
planner_graph = build_planner_graph()
checkpoint_store = SQLiteCheckpointStore(settings.checkpoint_path)


class ChatRequest(BaseModel):
    """Request body for the first planner endpoint."""

    message: str = Field(min_length=1)
    session_id: str = Field(default="default-session")


class ChatResponse(BaseModel):
    """Response body returned by the planner endpoint."""

    route: str
    response: str


@app.get("/health")
def health() -> dict[str, str]:
    """Simple readiness endpoint."""

    return {"status": "ok", "app": settings.app_name}


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    """Route the user message through the planner graph and persist the result."""

    state: PlannerState = {"user_query": request.message}
    result = planner_graph.invoke(state)
    checkpoint_store.save(
        session_id=request.session_id,
        step_name=result.get("route", "fallback"),
        payload=result,
    )
    return ChatResponse(
        route=result.get("route", "fallback"),
        response=result.get("response", ""),
    )
