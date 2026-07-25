from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[2]
ENV_FILE = REPO_ROOT / ".env"
load_dotenv(dotenv_path=ENV_FILE, override=False)


class Settings(BaseSettings):
    """Application settings loaded from environment variables and .env files."""

    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE),
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
    upload_path: Path = Field(
        default=Path("careerpilot/backend/database/uploads"),
        alias="CAREERPILOT_UPLOAD_PATH",
    )
    max_upload_bytes: int = Field(default=10 * 1024 * 1024, alias="CAREERPILOT_MAX_UPLOAD_BYTES")
    rag_chunk_size: int = Field(default=1000, alias="CAREERPILOT_RAG_CHUNK_SIZE")
    rag_chunk_overlap: int = Field(default=150, alias="CAREERPILOT_RAG_CHUNK_OVERLAP")
    rag_top_k: int = Field(default=4, alias="CAREERPILOT_RAG_TOP_K")
    history_limit: int = Field(default=8, alias="CAREERPILOT_HISTORY_LIMIT")
    duckduckgo_max_results: int = Field(default=5, alias="DUCKDUCKGO_MAX_RESULTS")

    def resolve_paths(self) -> "Settings":
        """Resolve relative paths against the repository root for stable local storage."""

        for field_name in ("sqlite_path", "chroma_path", "checkpoint_path", "upload_path"):
            value = getattr(self, field_name)
            if not isinstance(value, Path):
                continue
            if not value.is_absolute():
                setattr(self, field_name, REPO_ROOT / value)
            else:
                setattr(self, field_name, value)
        return self


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached settings object so the app reads the environment once."""

    return Settings().resolve_paths()
