"""Application settings loaded from environment variables / .env file.

Purpose
-------
Centralise configuration so the same code runs against SQLite (default, zero
setup) during development and PostgreSQL (dissertation target) in evaluation by
changing a single environment variable.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]
PROJECT_ROOT = BACKEND_DIR.parent


class Settings(BaseSettings):
    """Runtime configuration for the backend service."""

    model_config = SettingsConfigDict(
        env_file=str(BACKEND_DIR / ".env"),
        env_prefix="QOS_",
        extra="ignore",
    )

    app_name: str = "ai-broadband-qos-backend"
    api_prefix: str = "/api"
    database_url: str = Field(
        default=f"sqlite:///{(BACKEND_DIR / 'qos_monitoring.db').as_posix()}"
    )
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    seed_nodes: bool = True

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()
