"""ORM model for Continuous QoS Monitoring state (Phase 7).

Singleton row (id=1) tracks enable/disable, interval, and session stats.
Actual measurement rows continue to live in ``speed_tests``.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class MonitoringState(Base):
    """Persisted monitoring configuration and live session counters."""

    __tablename__ = "monitoring_state"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    interval_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=300)
    interval_label: Mapped[str] = mapped_column(String(40), nullable=False, default="5m")
    quick: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    server_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    next_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    measurement_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_result_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    running: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
