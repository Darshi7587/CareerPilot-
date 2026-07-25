from __future__ import annotations

from fastapi.testclient import TestClient

from careerpilot.backend.main import app


def test_chat_route_returns_response() -> None:
    client = TestClient(app)
    response = client.post(
        "/chat",
        json={"message": "Analyze my resume and suggest ATS improvements", "session_id": "test-session", "focus": "resume"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["route"] in {"resume", "fallback"}
    assert payload["response"]
    assert payload["session_id"] == "test-session"
