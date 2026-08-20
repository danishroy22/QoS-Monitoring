"""Pydantic schemas for the Administrator Analytics Portal (Phase 18)."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class AdminKpis(BaseModel):
    total_tests: int = 0
    isp_count: int = 0
    region_count: int = 0
    tests_24h: int = 0
    avg_qos_score: float | None = None
    avg_download_mbps: float | None = None
    avg_upload_mbps: float | None = None
    avg_ping_ms: float | None = None
    avg_jitter_ms: float | None = None
    avg_packet_loss_pct: float | None = None
    excellent_pct: float | None = None
    last_test_at: datetime | None = None


class AdminLiveStats(BaseModel):
    monitoring_enabled: bool = False
    monitoring_running: bool = False
    last_isp: str | None = None
    last_region: str | None = None
    last_score: int | None = None
    last_rating: str | None = None
    database: str = "connected"


class IspMetricRow(BaseModel):
    isp: str
    tests: int
    avg_download_mbps: float | None = None
    avg_upload_mbps: float | None = None
    avg_ping_ms: float | None = None
    avg_jitter_ms: float | None = None
    avg_packet_loss_pct: float | None = None
    avg_qos_score: float | None = None
    avg_dns_lookup_ms: float | None = None
    avg_http_response_ms: float | None = None
    best_score: int | None = None
    worst_score: int | None = None
    latest_rating: str | None = None
    rank: int | None = None


class QosBucket(BaseModel):
    rating: str
    count: int
    pct: float


class AdminDashboardResponse(BaseModel):
    kpis: AdminKpis
    live: AdminLiveStats
    leaderboard: list[IspMetricRow]
    qos_overview: list[QosBucket]
    generated_at: datetime


class IspAnalyticsResponse(BaseModel):
    isps: list[IspMetricRow]
    generated_at: datetime


class BenchmarkProfile(BaseModel):
    """Flat threshold view used by ranking / comparison engines."""

    name: str = "Ideal Broadband Profile"
    description: str | None = None
    download_mbps: float = Field(default=100, ge=1)
    upload_mbps: float = Field(default=20, ge=0.5)
    ping_ms: float = Field(default=20, ge=1)
    jitter_ms: float = Field(default=5, ge=0.1)
    packet_loss_pct: float = Field(default=0.5, ge=0)
    overall_score: int = Field(default=85, ge=1, le=100)


class BenchmarkMetricThreshold(BaseModel):
    threshold: float
    unit: str
    source: str
    rationale: str
    description: str


class BenchmarkProfileDetail(BaseModel):
    id: str
    name: str
    description: str | None = None
    metrics: dict[str, BenchmarkMetricThreshold]


class BenchmarkProfilesResponse(BaseModel):
    active_profile_id: str
    disclaimer: str
    profiles: list[BenchmarkProfileDetail]
    active: BenchmarkProfileDetail | None = None


class MetricCompliance(BaseModel):
    metric: str
    unit: str
    target: float
    actual: float | None = None
    higher_is_better: bool
    meets_target: bool | None = None
    gap: float | None = None
    compliance_pct: float | None = None


class IspBenchmarkRow(BaseModel):
    isp: str
    tests: int
    composite_score: float | None = None
    metrics: list[MetricCompliance]


class BenchmarkResponse(BaseModel):
    profile: BenchmarkProfile
    profile_detail: BenchmarkProfileDetail | None = None
    active_profile_id: str | None = None
    disclaimer: str | None = None
    profiles: list[BenchmarkProfileDetail] = []
    rankings: list[IspBenchmarkRow]
    generated_at: datetime


class HistoryPoint(BaseModel):
    period: str
    tests: int
    avg_download_mbps: float | None = None
    avg_upload_mbps: float | None = None
    avg_ping_ms: float | None = None
    avg_jitter_ms: float | None = None
    avg_packet_loss_pct: float | None = None
    avg_qos_score: float | None = None


class HistoryAnalyticsResponse(BaseModel):
    granularity: Literal["daily", "weekly", "monthly"]
    points: list[HistoryPoint]
    generated_at: datetime


class HeatmapCell(BaseModel):
    region: str
    tests: int
    avg_qos_score: float | None = None
    avg_download_mbps: float | None = None
    avg_ping_ms: float | None = None
    rating: str | None = None


class HeatmapResponse(BaseModel):
    cells: list[HeatmapCell]
    generated_at: datetime


class MapLegendBand(BaseModel):
    rating: str
    colour: str
    min_score: float
    meaning: str


class MapLegend(BaseModel):
    metric: str
    higher_is_better: bool
    bands: list[MapLegendBand]
    note: str | None = None


class MapMeta(BaseModel):
    metric: str
    total_tests: int
    districts_with_data: int
    filters: dict
    available_isps: list[str] = []
    available_packages: list[str] = []
    available_regions: list[str] = []
    generated_at: datetime | str


class QosMapResponse(BaseModel):
    type: str = "FeatureCollection"
    features: list[dict]
    meta: MapMeta
    legend: MapLegend
    metrics: list[str]


class MetricStats(BaseModel):
    key: str
    label: str
    unit: str
    higher_is_better: bool
    count: int = 0
    avg: float | None = None
    median: float | None = None
    min: float | None = None
    max: float | None = None
    stdev: float | None = None
    target: float | None = None
    gap: float | None = None
    meets_target: bool | None = None
    delta_pct: float | None = None


class IspComparisonRow(BaseModel):
    isp: str
    tests: int
    qos_score: float | None = None
    qos_rating: str | None = None
    fulfilment_pct: float | None = None
    metrics: list[MetricStats]


class PairwiseDelta(BaseModel):
    key: str
    label: str
    unit: str
    isp_a_avg: float | None = None
    isp_b_avg: float | None = None
    delta: float | None = None
    better: str | None = None


class PairwiseComparison(BaseModel):
    isp_a: str
    isp_b: str
    deltas: list[PairwiseDelta]
    note: str | None = None


class IspComparisonResponse(BaseModel):
    mode: Literal["isp_vs_isp", "isp_vs_benchmark", "isp_vs_ideal"]
    profile: BenchmarkProfile | None = None
    isps: list[IspComparisonRow]
    pairwise: PairwiseComparison | None = None
    filters: dict
    available_isps: list[str] = []
    available_packages: list[str] = []
    available_regions: list[str] = []
    total_tests: int = 0
    ranking_note: str
    generated_at: datetime | str


class IspAiCard(BaseModel):
    isp: str
    tests: int
    summary: str
    strengths: list[str]
    weaknesses: list[str]
    recommendations: list[str]
    rating: str | None = None


class AdminAiResponse(BaseModel):
    market_summary: str
    isps: list[IspAiCard]
    recommendations: list[str]
    model_provider: str
    generated_at: datetime
