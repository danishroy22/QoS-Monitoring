"""Pydantic schemas for the Internet Quality API."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class SpeedTestRequest(BaseModel):
    quick: bool = Field(
        default=False,
        description="Faster test with smaller download/upload payloads",
    )
    server_id: str | None = Field(
        default=None,
        description="Speed-test server id from GET /speedtest/servers",
    )


class SpeedTestServerOption(BaseModel):
    id: str
    name: str
    location: str
    country: str | None = "Mauritius"
    type: str | None = "ISP Test Server"
    status: str = "Online"
    host: str | None = None
    ookla_server_id: int | None = None
    distance_km: float | int | None = None
    supports_upload: bool = True
    upload_note: str | None = None


class SpeedTestServersResponse(BaseModel):
    servers: list[SpeedTestServerOption]
    default_server_id: str = "emtel-ebene-18276"
    auto_select: bool = True


class SpeedTestServerProbe(BaseModel):
    id: str
    name: str
    location: str
    type: str | None = None
    status: str = "Online"
    host: str | None = None
    distance_km: float | int | None = None
    latency_ms: float


class SpeedTestFindServerResponse(BaseModel):
    probes: list[SpeedTestServerProbe]
    best_server_id: str
    best_server: SpeedTestServerProbe | None = None


class SpeedTestPhaseQuery(BaseModel):
    quick: bool = Field(default=False, description="Use smaller payloads for this phase")


class SpeedTestServerPhaseOut(BaseModel):
    dns_lookup_ms: float | None = None
    http_response_ms: float | None = None
    ipv4_ok: bool = False
    ipv6_ok: bool = False
    public_ip: str | None = None
    isp_name: str | None = None
    as_info: str | None = None
    server_label: str = "emtel"
    server_id: str | None = None
    errors: list[str] = []


class SpeedTestLatencyPhaseOut(BaseModel):
    ping_ms: float | None = None
    jitter_ms: float | None = None
    packet_loss_pct: float | None = None
    errors: list[str] = []


class SpeedTestCompleteRequest(BaseModel):
    download_mbps: float | None = None
    upload_mbps: float | None = None
    ping_ms: float | None = None
    jitter_ms: float | None = None
    packet_loss_pct: float | None = None
    dns_lookup_ms: float | None = None
    http_response_ms: float | None = None
    ipv4_ok: bool = False
    ipv6_ok: bool = False
    public_ip: str | None = None
    isp_name: str | None = None
    as_info: str | None = None
    server_label: str = "cloudflare"
    errors: list[str] = []


class MetricScoreOut(BaseModel):
    name: str
    value: float | None = None
    unit: str
    score: int
    rating: str


class HealthBreakdown(BaseModel):
    overall_score: int
    overall_rating: str
    metrics: list[MetricScoreOut]


class SpeedTestResultOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    timestamp: datetime
    download_mbps: float | None
    upload_mbps: float | None
    ping_ms: float | None
    jitter_ms: float | None
    packet_loss_pct: float | None
    dns_lookup_ms: float | None
    http_response_ms: float | None
    ipv4_ok: bool
    ipv6_ok: bool
    public_ip: str | None
    isp_name: str | None
    as_info: str | None
    server_label: str
    overall_score: int | None
    overall_rating: str | None


class SpeedTestRunResponse(BaseModel):
    result: SpeedTestResultOut
    health: HealthBreakdown
    errors: list[str] = []


class HistoryResponse(BaseModel):
    count: int
    results: list[SpeedTestResultOut]


class StatisticsResponse(BaseModel):
    count: int
    avg_download_mbps: float | None
    avg_upload_mbps: float | None
    avg_ping_ms: float | None
    avg_jitter_ms: float | None
    avg_packet_loss_pct: float | None
    avg_overall_score: float | None
    best_overall_score: int | None
    worst_overall_score: int | None
    latest_rating: str | None


class IspResponse(BaseModel):
    public_ip: str | None
    isp_name: str | None
    as_info: str | None
    ipv4_ok: bool | None = None
    ipv6_ok: bool | None = None
    last_tested_at: datetime | None = None


class DashboardResponse(BaseModel):
    latest: SpeedTestResultOut | None
    health: HealthBreakdown | None
    statistics: StatisticsResponse
    history: list[SpeedTestResultOut]
    isp: IspResponse


class AssistantResponse(BaseModel):
    analysis: str
    possible_reasons: list[str]
    recommended_actions: list[str]
    focus_metric: str | None = None
    overall_rating: str | None = None
    overall_score: int | None = None
    model_provider: str
    generated_at: datetime
