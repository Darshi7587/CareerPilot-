from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from careerpilot.backend.database.auth import AuthDatabase


def test_auth_signup_and_login_success() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_path = Path(tmp_dir) / "test_auth.sqlite3"
        auth_db = AuthDatabase(db_path)

        user = auth_db.signup(
            username="darshi_test",
            email="darshi@example.com",
            password="securepassword123",
            full_name="Darshitha S R",
        )

        assert user.user_id == 1
        assert user.username == "darshi_test"
        assert user.email == "darshi@example.com"
        assert user.full_name == "Darshitha S R"

        logged_in = auth_db.login("darshi_test", "securepassword123")
        assert logged_in.user_id == user.user_id

        logged_in_by_email = auth_db.login("darshi@example.com", "securepassword123")
        assert logged_in_by_email.user_id == user.user_id


def test_auth_duplicate_user_raises_value_error() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_path = Path(tmp_dir) / "test_auth.sqlite3"
        auth_db = AuthDatabase(db_path)

        auth_db.signup("unique_user", "unique@example.com", "pass1234")

        with pytest.raises(ValueError, match="Username is already taken"):
            auth_db.signup("unique_user", "other@example.com", "pass1234")

        with pytest.raises(ValueError, match="Email address is already registered"):
            auth_db.signup("other_user", "unique@example.com", "pass1234")
