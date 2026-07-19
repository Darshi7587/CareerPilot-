from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


class SQLiteCheckpointStore:
    """Tiny SQLite-backed checkpoint store for conversation state."""

    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS checkpoints (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    step_name TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_checkpoints_session_id ON checkpoints(session_id)"
            )
            connection.commit()

    def save(self, session_id: str, step_name: str, payload: dict[str, Any]) -> None:
        """Store a snapshot of the current graph state."""

        created_at = datetime.now(tz=UTC).isoformat()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO checkpoints (session_id, step_name, payload_json, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (session_id, step_name, json.dumps(payload), created_at),
            )
            connection.commit()

    def latest(self, session_id: str) -> dict[str, Any] | None:
        """Load the newest checkpoint for a session."""

        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT payload_json
                FROM checkpoints
                WHERE session_id = ?
                ORDER BY id DESC
                LIMIT 1
                """,
                (session_id,),
            ).fetchone()
        if row is None:
            return None
        return json.loads(row["payload_json"])
