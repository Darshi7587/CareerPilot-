from __future__ import annotations

import sqlite3
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path


@dataclass(frozen=True)
class DocumentRecord:
    document_id: str
    session_id: str
    filename: str
    storage_path: str
    checksum: str
    status: str
    chunk_count: int
    created_at: str
    updated_at: str


class DocumentRegistry:
    """SQLite registry that owns the uploaded-document lifecycle."""

    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path, timeout=5.0)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA busy_timeout = 5000")
        connection.execute("PRAGMA journal_mode = WAL")
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS documents (
                    document_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    filename TEXT NOT NULL,
                    storage_path TEXT NOT NULL,
                    checksum TEXT NOT NULL,
                    status TEXT NOT NULL,
                    chunk_count INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_documents_session_id ON documents(session_id)"
            )

    def create(self, record: DocumentRecord) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO documents (
                    document_id, session_id, filename, storage_path, checksum,
                    status, chunk_count, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                tuple(asdict(record).values()),
            )

    def update_status(self, document_id: str, status: str, chunk_count: int = 0) -> None:
        with self._connect() as connection:
            connection.execute(
                "UPDATE documents SET status = ?, chunk_count = ?, updated_at = ? WHERE document_id = ?",
                (status, chunk_count, datetime.now(tz=UTC).isoformat(), document_id),
            )

    def get(self, document_id: str, session_id: str) -> DocumentRecord | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM documents WHERE document_id = ? AND session_id = ?",
                (document_id, session_id),
            ).fetchone()
        return DocumentRecord(**dict(row)) if row else None

    def list(self, session_id: str) -> list[DocumentRecord]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM documents WHERE session_id = ? ORDER BY created_at DESC", (session_id,)
            ).fetchall()
        return [DocumentRecord(**dict(row)) for row in rows]

    def list_all(self) -> list[DocumentRecord]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM documents ORDER BY created_at DESC"
            ).fetchall()
        return [DocumentRecord(**dict(row)) for row in rows]

    def delete(self, document_id: str, session_id: str) -> DocumentRecord | None:
        record = self.get(document_id, session_id)
        if record is None:
            return None
        with self._connect() as connection:
            connection.execute(
                "DELETE FROM documents WHERE document_id = ? AND session_id = ?",
                (document_id, session_id),
            )
        return record
