from __future__ import annotations

from types import SimpleNamespace

from careerpilot.backend.agents.resume import handle_resume


def test_resume_analysis_uses_indexed_documents(monkeypatch) -> None:
    class FakeRecord:
        status = "indexed"

    class FakeService:
        def __init__(self) -> None:
            self.registry = SimpleNamespace(list=lambda session_id: [FakeRecord()])

        def retrieve(self, session_id: str, query: str) -> list[dict[str, object]]:
            return [
                {
                    "content": "Python, SQL, AWS, REST APIs",
                    "metadata": {"filename": "resume.pdf", "page": 1},
                }
            ]

    captured: dict[str, object] = {}

    def fake_generate_response(system_prompt: str, user_query: str, history: list[dict[str, object]]) -> str:
        captured["prompt"] = system_prompt
        captured["user_query"] = user_query
        captured["history"] = history
        return "Resume analysis generated."

    import careerpilot.backend.agents.resume as resume_module

    monkeypatch.setattr(resume_module, "get_rag_service", lambda: FakeService())
    monkeypatch.setattr(resume_module, "_generate_resume_response", fake_generate_response)

    result = handle_resume({"user_query": "Analyze my resume", "session_id": "demo-session", "history": []})

    assert result["response"] == "Resume analysis generated."
    assert "Python, SQL, AWS, REST APIs" in str(captured["prompt"])
    assert "resume.pdf" in str(captured["prompt"])
