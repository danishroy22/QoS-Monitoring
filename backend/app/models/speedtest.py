"""ORM model for Internet Quality speed-test results."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class SpeedTestResult(Base):
    """One stored run from the Network Measurement Engine."""

    __tablename__ = "speed_tests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True, default=_utcnow
    )
    download_mbps: Mapped[float | None] = mapped_column(Float, nullable=True)
    upload_mbps: Mapped[float | None] = mapped_column(Float, nullable=True)
    ping_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    jitter_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    packet_loss_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    dns_lookup_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    http_response_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    ipv4_ok: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    ipv6_ok: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    public_ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    isp_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    as_info: Mapped[str | None] = mapped_column(String(200), nullable=True)
    server_label: Mapped[str] = mapped_column(String(80), nullable=False, default="cloudflare")
    overall_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    overall_rating: Mapped[str | None] = mapped_column(String(40), nullable=True)
    errors_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, server_default=func.now()
    )
