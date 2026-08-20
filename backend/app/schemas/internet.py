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
    operator: str | None = None
    ookla_server_id: int | None = None
    distance_km: float | int | None = None
    latitude: float | None = None
    longitude: float | None = None
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
    operator: str | None = None
    distance_km: float | int | None = None
    latency_ms: float | None = None
    packet_loss_pct: float | None = None
    score: float | None = None
    isp_affinity: bool = False
    reachable: bool | None = None
    probe_method: str | None = None


class SpeedTestFindServerResponse(BaseModel):
    probes: list[SpeedTestServerProbe]
    best_server_id: str
    best_server: SpeedTestServerProbe | None = None
    weights: dict[str, float] | None = None
    detected_isp: str | None = None


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
    detected_region: str | None = None
    detected_city: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    server_label: str = "emtel"
    server_id: str | None = None
    tcp_connect_ms: float | None = None
    tls_handshake_ms: float | None = None
    dns_ok: bool | None = None
    http_ok: bool | None = None
    dns_resolver: str | None = None
    errors: list[str] = []


class SpeedTestLatencyPhaseOut(BaseModel):
    ping_ms: float | None = None
    ping_min_ms: float | None = None
    ping_max_ms: float | None = None
    ping_median_ms: float | None = None
    jitter_ms: float | None = None
    packet_loss_pct: float | None = None
    packets_sent: int | None = None
    packets_received: int | None = None
    packets_lost: int | None = None
    latency_samples: list[float] | None = None
    probe_method: str | None = None
    latency_packet_size: int | None = None
    errors: list[str] = []
    server_id: str | None = None


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
    internet_package: str | None = None
    package_id: int | None = None
    detected_region: str | None = None
    detected_city: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    server_label: str = "cloudflare"
    server_id: str | None = None
    server_operator: str | None = None
    server_location: str | None = None
    server_type: str | None = None
    selection_mode: str | None = None
    selection_score: float | None = None
    ping_min_ms: float | None = None
    ping_max_ms: float | None = None
    ping_median_ms: float | None = None
    packets_sent: int | None = None
    packets_received: int | None = None
    packets_lost: int | None = None
    latency_samples: list[float] | None = None
    download_bytes: int | None = None
    download_duration_s: float | None = None
    download_connections: int | None = None
    download_peak_mbps: float | None = None
    upload_bytes: int | None = None
    upload_duration_s: float | None = None
    upload_connections: int | None = None
    upload_peak_mbps: float | None = None
    dns_ok: bool | None = None
    dns_resolver: str | None = None
    tcp_connect_ms: float | None = None
    tls_handshake_ms: float | None = None
    http_ok: bool | None = None
    measurement_config_version: str | None = None
    errors: list[str] = []


class AggregationBucket(BaseModel):
    key: str
    label: str
    count: int
    avg_download_mbps: float | None = None
    avg_upload_mbps: float | None = None
    avg_ping_ms: float | None = None
    avg_jitter_ms: float | None = None
    avg_packet_loss_pct: float | None = None
    avg_dns_lookup_ms: float | None = None
    avg_http_response_ms: float | None = None
    avg_overall_score: float | None = None
    server_operator: str | None = None
    server_location: str | None = None
    avg: float | None = None
    min: float | None = None
    max: float | None = None


class AggregationResponse(BaseModel):
    dimension: str
    days: int | None = None
    metric: str | None = None
    total_rows: int
    bucket_count: int | None = None
    buckets: list[AggregationBucket]
    backend: str | None = None
    note: str | None = None


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
    client_hash: str | None = None
    isp_name: str | None
    as_info: str | None
    internet_package: str | None = None
    package_id: int | None = None
    advertised_download_mbps: float | None = None
    advertised_upload_mbps: float | None = None
    download_fulfilment_pct: float | None = None
    upload_fulfilment_pct: float | None = None
    detected_region: str | None = None
    detected_city: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    server_id: str | None = None
    server_label: str
    server_operator: str | None = None
    server_location: str | None = None
    server_type: str | None = None
    selection_mode: str | None = None
    selection_score: float | None = None
    test_date: str | None = None
    day_of_week: int | None = None
    hour_utc: int | None = None
    ping_min_ms: float | None = None
    ping_max_ms: float | None = None
    ping_median_ms: float | None = None
    packets_sent: int | None = None
    packets_received: int | None = None
    packets_lost: int | None = None
    latency_samples_json: str | None = None
    download_bytes: int | None = None
    download_duration_s: float | None = None
    download_connections: int | None = None
    download_peak_mbps: float | None = None
    upload_bytes: int | None = None
    upload_duration_s: float | None = None
    upload_connections: int | None = None
    upload_peak_mbps: float | None = None
    dns_ok: bool | None = None
    dns_resolver: str | None = None
    tcp_connect_ms: float | None = None
    tls_handshake_ms: float | None = None
    http_ok: bool | None = None
    measurement_config_version: str | None = None
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


class ConnectionIdentity(BaseModel):
    public_ip: str | None = None
    isp_name: str | None = None
    as_info: str | None = None
    detected_region: str | None = None
    detected_city: str | None = None
    country: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    approximate: bool = True
    note: str = (
        "IP-based ISP and location are approximate network identity, not a guaranteed operator record."
    )


class IspResponse(BaseModel):
    public_ip: str | None
    isp_name: str | None
    as_info: str | None
    ipv4_ok: bool | None = None
    ipv6_ok: bool | None = None
    last_tested_at: datetime | None = None
    detected_region: str | None = None
    detected_city: str | None = None


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
