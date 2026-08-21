"""Database engine and session management.

If ``QOS_SUPABASE_DB_URL`` is set but unreachable (paused project, bad DNS,
wrong host), the engine falls back to ``QOS_DATABASE_URL`` (local SQLite) so
the backend can still start for development.
"""

from __future__ import annotations

import logging
from collections.abc import Generator
from urllib.parse import urlsplit, urlunsplit

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def _redact_url(url: str) -> str:
    """Hide password when logging connection strings."""
    try:
        parts = urlsplit(url)
        if not parts.username and not parts.password:
            return url
        host = parts.hostname or ""
        port = f":{parts.port}" if parts.port else ""
        user = parts.username or ""
        netloc = f"{user}:***@{host}{port}" if user else f"***@{host}{port}"
        return urlunsplit((parts.scheme, netloc, parts.path, parts.query, parts.fragment))
    except Exception:  # noqa: BLE001
        return "<unparseable-url>"


def _make_engine(url: str) -> Engine:
    connect_args: dict = {}
    if url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
    else:
        # Fail fast when DNS/network is broken instead of hanging startup.
        connect_args["connect_timeout"] = 8
    return create_engine(
        url,
        connect_args=connect_args,
        pool_pre_ping=True,
        future=True,
    )


def _can_connect(eng: Engine) -> bool:
    try:
        with eng.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as exc:  # noqa: BLE001
        logger.warning("Database probe failed: %s", exc)
        return False


def _resolve_engine() -> tuple[Engine, str]:
    primary = settings.resolved_database_url
    engine = _make_engine(primary)
    if _can_connect(engine):
        logger.info("Database connected: %s", _redact_url(primary))
        return engine, primary

    fallback = (settings.database_url or "").strip()
    if settings.uses_supabase and fallback and fallback != primary:
        logger.error(
            "Supabase unreachable (%s). Falling back to local SQLite (%s). "
            "In Supabase → Project Settings → Database, copy the "
            "Session pooler URI (not the direct db.* host if DNS fails), "
            "ensure the project is not paused, then update QOS_SUPABASE_DB_URL.",
            _redact_url(primary),
            _redact_url(fallback),
        )
        try:
            engine.dispose()
        except Exception:  # noqa: BLE001
            pass
        engine = _make_engine(fallback)
        if not _can_connect(engine):
            raise RuntimeError(
                f"Local SQLite fallback also failed: {_redact_url(fallback)}"
            )
        logger.info("Using SQLite fallback: %s", _redact_url(fallback))
        return engine, fallback

    raise RuntimeError(f"Cannot connect to database: {_redact_url(primary)}")


engine, active_database_url = _resolve_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
