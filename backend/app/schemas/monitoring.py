"""Pydantic schemas for Continuous QoS Monitoring (Phase 7)."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

IntervalPreset = Literal["1m", "5m", "10m", "30m", "custom"]

PRESET_SECONDS = {
    "1m": 60,
    "5m": 300,
    "10m": 600,
    "30m": 1800,
}


class MonitoringStartRequest(BaseModel):
    interval: IntervalPreset = Field(
        default="5m",
        description="Preset interval or 'custom'",
    )
    custom_seconds: int | None = Field(
        default=None,
        ge=60,
        le=86400,
        description="Required when interval='custom' (minimum 60 seconds)",
    )
    quick: bool = Field(
        default=True,
        description="Use quicker payloads for background runs (recommended)",
    )
    server_id: str | None = Field(
        default=None,
        description="Optional Mauritius server id; null = engine default",
    )


class MonitoringLastMeasurement(BaseModel):
    id: int | None = None
    timestamp: datetime | None = None
    download_mbps: float | None = None
    upload_mbps: float | None = None
    ping_ms: float | None = None
    jitter_ms: float | None = None
    packet_loss_pct: float | None = None
    overall_score: int | None = None
    overall_rating: str | None = None
    isp_name: str | None = None
    server_label: str | None = None


class MonitoringStatusResponse(BaseModel):
    enabled: bool
    running: bool
    interval: str
    interval_seconds: int
    quick: bool
    server_id: str | None = None
    started_at: datetime | None = None
    last_run_at: datetime | None = None
    next_run_at: datetime | None = None
    monitoring_duration_seconds: int = 0
    measurement_count: int = 0
    last_error: str | None = None
    last_measurement: MonitoringLastMeasurement | None = None
