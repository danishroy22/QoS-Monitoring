"""ORM model for Internet Quality speed-test results."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class SpeedTestResult(Base):
    """One stored run from the Network Measurement Engine.

    Phase 3 adds traceable context (client hash, package, server metadata, and
    UTC time buckets) so rows can be aggregated without unnecessary PII.
    """

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
    client_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    isp_name: Mapped[str | None] = mapped_column(String(200), nullable=True, index=True)
    as_info: Mapped[str | None] = mapped_column(String(200), nullable=True)
    internet_package: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    package_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    advertised_download_mbps: Mapped[float | None] = mapped_column(Float, nullable=True)
    advertised_upload_mbps: Mapped[float | None] = mapped_column(Float, nullable=True)
    download_fulfilment_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    upload_fulfilment_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    detected_region: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    detected_city: Mapped[str | None] = mapped_column(String(120), nullable=True)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    server_id: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    server_label: Mapped[str] = mapped_column(String(80), nullable=False, default="cloudflare")
    server_operator: Mapped[str | None] = mapped_column(String(120), nullable=True)
    server_location: Mapped[str | None] = mapped_column(String(120), nullable=True)
    server_type: Mapped[str | None] = mapped_column(String(120), nullable=True)
    selection_mode: Mapped[str | None] = mapped_column(String(20), nullable=True)
    selection_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    test_date: Mapped[str | None] = mapped_column(String(10), nullable=True, index=True)
    day_of_week: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    hour_utc: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    ping_min_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    ping_max_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    ping_median_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    packets_sent: Mapped[int | None] = mapped_column(Integer, nullable=True)
    packets_received: Mapped[int | None] = mapped_column(Integer, nullable=True)
    packets_lost: Mapped[int | None] = mapped_column(Integer, nullable=True)
    latency_samples_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    download_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    download_duration_s: Mapped[float | None] = mapped_column(Float, nullable=True)
    download_connections: Mapped[int | None] = mapped_column(Integer, nullable=True)
    download_peak_mbps: Mapped[float | None] = mapped_column(Float, nullable=True)
    upload_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    upload_duration_s: Mapped[float | None] = mapped_column(Float, nullable=True)
    upload_connections: Mapped[int | None] = mapped_column(Integer, nullable=True)
    upload_peak_mbps: Mapped[float | None] = mapped_column(Float, nullable=True)
    dns_ok: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    dns_resolver: Mapped[str | None] = mapped_column(String(80), nullable=True)
    tcp_connect_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    tls_handshake_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    http_ok: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    measurement_config_version: Mapped[str | None] = mapped_column(String(20), nullable=True)
    overall_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    overall_rating: Mapped[str | None] = mapped_column(String(40), nullable=True)
    errors_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Phase 16 — data quality (rows are marked, never silently deleted)
    quality_status: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    quality_flags_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    analytics_eligible: Mapped[bool | None] = mapped_column(Boolean, nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, server_default=func.now()
    )
