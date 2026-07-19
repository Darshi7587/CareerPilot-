from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables and .env files."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = Field(default="CareerPilot AI", alias="APP_NAME")
    default_llm_provider: str = Field(default="gemini", alias="DEFAULT_LLM_PROVIDER")
    gemini_api_key: str = Field(default="", alias="GEMINI_API_KEY")
    groq_api_key: str = Field(default="", alias="GROQ_API_KEY")
    sqlite_path: Path = Field(
        default=Path("careerpilot/backend/database/careerpilot.sqlite3"),
        alias="CAREERPILOT_SQLITE_PATH",
    )
    chroma_path: Path = Field(
        default=Path("careerpilot/backend/database/chroma"),
        alias="CAREERPILOT_CHROMA_PATH",
    )
    checkpoint_path: Path = Field(
        default=Path("careerpilot/backend/memory/checkpoints.sqlite3"),
        alias="CAREERPILOT_CHECKPOINT_PATH",
    )
    duckduckgo_max_results: int = Field(default=5, alias="DUCKDUCKGO_MAX_RESULTS")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached settings object so the app reads the environment once."""

    return Settings()
