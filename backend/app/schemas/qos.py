"""Pydantic schemas for the QoS monitoring API.

These mirror the contract in docs/api-design.md and the payloads produced by
the Phase 2 simulator (backend/simulator).
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class HealthResponse(BaseModel):
    status: str = "ok"
    service: str
    database: str


class NodeBase(BaseModel):
    node_code: str = Field(..., max_length=50)
    region: str
    access_technology: str
    service_tier_mbps: float = Field(..., gt=0)
    subscriber_count: int = Field(..., ge=0)
    baseline_latency_ms: float = Field(..., ge=0)
    max_bandwidth_mbps: float = Field(..., gt=0)


class NodeResponse(NodeBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime


class MeasurementCreate(BaseModel):
    """Incoming QoS measurement from the simulator or a live probe."""

    model_config = ConfigDict(extra="forbid")

    node_code: str = Field(..., max_length=50)
    timestamp: datetime
    latency_ms: float = Field(..., ge=0, le=10000)
    jitter_ms: float = Field(..., ge=0, le=5000)
    packet_loss_pct: float = Field(..., ge=0, le=100)
    throughput_mbps: float = Field(..., ge=0)
    bandwidth_utilisation_pct: float = Field(..., ge=0, le=100)
    signal_quality: float | None = Field(default=None, ge=0, le=100)
    availability_pct: float = Field(..., ge=0, le=100)
    scenario_label: str = Field(default="normal", max_length=50)


class MeasurementCreateResponse(BaseModel):
    measurement_id: int
    stored: bool = True


class MeasurementResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    node_code: str
    timestamp: datetime
    latency_ms: float
    jitter_ms: float
    packet_loss_pct: float
    throughput_mbps: float
    bandwidth_utilisation_pct: float
    signal_quality: float | None
    availability_pct: float
    scenario_label: str


class LatestMetric(MeasurementResponse):
    """Latest sample per node, enriched with node context and health status."""

    region: str
    access_technology: str
    service_tier_mbps: float
    health_status: str


class HistoryPoint(BaseModel):
    timestamp: datetime
    value: float


class HistoryResponse(BaseModel):
    node_code: str
    metric: str
    points: list[HistoryPoint]


class AnomalyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    measurement_id: int
    node_code: str
    model_name: str
    anomaly_score: float
    is_anomaly: bool
    severity: str
    suspected_issue: str | None
    created_at: datetime


class RecommendationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    anomaly_id: int
    summary: str
    likely_causes: str
    recommended_actions: str
    model_provider: str
    created_at: datetime


class DetectionRunResponse(BaseModel):
    processed_measurements: int
    anomalies_detected: int
    model_name: str
    skipped_existing: int = 0
