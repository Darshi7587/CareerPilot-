from __future__ import annotations

from careerpilot.backend.memory.checkpoint import SQLiteCheckpointStore


def test_history_returns_oldest_to_newest_and_applies_limit(tmp_path) -> None:
    store = SQLiteCheckpointStore(tmp_path / "history.sqlite3")
    store.save("session", "resume", {"user_query": "first", "response": "one"})
    store.save("session", "coding", {"user_query": "second", "response": "two"})

    assert [item["user_query"] for item in store.history("session", limit=1)] == ["second"]
    assert [item["user_query"] for item in store.history("session", limit=2)] == ["first", "second"]
