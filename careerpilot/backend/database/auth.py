from __future__ import annotations

import hashlib
import os
import sqlite3
from dataclasses import dataclass
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Generator

from careerpilot.backend.config import get_settings


@dataclass
class UserRecord:
    user_id: int
    username: str
    email: str
    full_name: str
    password_hash: str
    salt: str
    created_at: str


class AuthDatabase:
    """SQLite-backed authentication and user management repository."""

    def __init__(self, db_path: Path | None = None) -> None:
        settings = get_settings()
        self.db_path = db_path or settings.sqlite_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    @contextmanager
    def _get_connection(self) -> Generator[sqlite3.Connection, None, None]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def _init_db(self) -> None:
        with self._get_connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    full_name TEXT NOT NULL DEFAULT '',
                    password_hash TEXT NOT NULL,
                    salt TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.commit()

    @staticmethod
    def _hash_password(password: str, salt: str) -> str:
        return hashlib.sha256((password + salt).encode("utf-8")).hexdigest()

    def signup(self, username: str, email: str, password: str, full_name: str = "") -> UserRecord:
        """Create a new user account."""

        username = username.strip().lower()
        email = email.strip().lower()
        full_name = full_name.strip() or username.capitalize()

        if len(username) < 3:
            raise ValueError("Username must be at least 3 characters long")
        if "@" not in email:
            raise ValueError("Invalid email address")
        if len(password) < 4:
            raise ValueError("Password must be at least 4 characters long")

        salt = os.urandom(16).hex()
        password_hash = self._hash_password(password, salt)
        created_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    """
                    INSERT INTO users (username, email, full_name, password_hash, salt, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (username, email, full_name, password_hash, salt, created_at),
                )
                conn.commit()
                user_id = cursor.lastrowid
                return UserRecord(
                    user_id=user_id,
                    username=username,
                    email=email,
                    full_name=full_name,
                    password_hash=password_hash,
                    salt=salt,
                    created_at=created_at,
                )
        except sqlite3.IntegrityError as exc:
            if "username" in str(exc):
                raise ValueError("Username is already taken") from exc
            if "email" in str(exc):
                raise ValueError("Email address is already registered") from exc
            raise ValueError("User registration failed") from exc

    def login(self, username_or_email: str, password: str) -> UserRecord:
        """Authenticate an existing user."""

        target = username_or_email.strip().lower()
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM users WHERE username = ? OR email = ?",
                (target, target),
            ).fetchone()

            if not row:
                raise ValueError("Invalid username/email or password")

            user = UserRecord(
                user_id=row["user_id"],
                username=row["username"],
                email=row["email"],
                full_name=row["full_name"],
                password_hash=row["password_hash"],
                salt=row["salt"],
                created_at=row["created_at"],
            )

            expected_hash = self._hash_password(password, user.salt)
            if expected_hash != user.password_hash:
                raise ValueError("Invalid username/email or password")

            return user

    def get_by_username(self, username: str) -> UserRecord | None:
        """Fetch user by username."""

        with self._get_connection() as conn:
            row = conn.execute("SELECT * FROM users WHERE username = ?", (username.strip().lower(),)).fetchone()
            if not row:
                return None
            return UserRecord(
                user_id=row["user_id"],
                username=row["username"],
                email=row["email"],
                full_name=row["full_name"],
                password_hash=row["password_hash"],
                salt=row["salt"],
                created_at=row["created_at"],
            )


_auth_db: AuthDatabase | None = None


def get_auth_db() -> AuthDatabase:
    global _auth_db
    if _auth_db is None:
        _auth_db = AuthDatabase()
    return _auth_db
