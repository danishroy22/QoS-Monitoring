"""ORM models mirroring database/schema.sql.

These tables store the broadband network topology, time-series QoS
measurements, ground-truth events, ML anomaly results, and AI recommendations.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class NetworkNode(Base):
    """A simulated broadband access node / service area."""

    __tablename__ = "network_nodes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    node_code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    region: Mapped[str] = mapped_column(String(100), nullable=False)
    access_technology: Mapped[str] = mapped_column(String(50), nullable=False)
    service_tier_mbps: Mapped[float] = mapped_column(Float, nullable=False)
    subscriber_count: Mapped[int] = mapped_column(Integer, nullable=False)
    baseline_latency_ms: Mapped[float] = mapped_column(Float, nullable=False)
    max_bandwidth_mbps: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, server_default=func.now()
    )

    measurements: Mapped[list["QoSMeasurement"]] = relationship(
        back_populates="node", cascade="all, delete-orphan"
    )
    events: Mapped[list["NetworkEvent"]] = relationship(
        back_populates="node", cascade="all, delete-orphan"
    )


class QoSMeasurement(Base):
    """A single timestamped QoS sample for one node."""

    __tablename__ = "qos_measurements"
    __table_args__ = (
        UniqueConstraint("node_id", "timestamp", name="uq_measurement_node_timestamp"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    node_id: Mapped[int] = mapped_column(
        ForeignKey("network_nodes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    latency_ms: Mapped[float] = mapped_column(Float, nullable=False)
    jitter_ms: Mapped[float] = mapped_column(Float, nullable=False)
    packet_loss_pct: Mapped[float] = mapped_column(Float, nullable=False)
    throughput_mbps: Mapped[float] = mapped_column(Float, nullable=False)
    bandwidth_utilisation_pct: Mapped[float] = mapped_column(Float, nullable=False)
    signal_quality: Mapped[float | None] = mapped_column(Float, nullable=True)
    availability_pct: Mapped[float] = mapped_column(Float, nullable=False)
    scenario_label: Mapped[str] = mapped_column(String(50), nullable=False, default="normal")

    node: Mapped["NetworkNode"] = relationship(back_populates="measurements")
    anomaly: Mapped["AnomalyResult | None"] = relationship(
        back_populates="measurement", cascade="all, delete-orphan", uselist=False
    )


class NetworkEvent(Base):
    """A ground-truth incident window from the simulator."""

    __tablename__ = "network_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    node_id: Mapped[int] = mapped_column(
        ForeignKey("network_nodes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    event_type: Mapped[str] = mapped_column(String(80), nullable=False)
    severity: Mapped[str] = mapped_column(String(30), nullable=False)
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)

    node: Mapped["NetworkNode"] = relationship(back_populates="events")


class AnomalyResult(Base):
    """Machine learning anomaly detection output for a measurement."""

    __tablename__ = "anomaly_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    measurement_id: Mapped[int] = mapped_column(
        ForeignKey("qos_measurements.id", ondelete="CASCADE"), nullable=False, index=True
    )
    model_name: Mapped[str] = mapped_column(String(80), nullable=False)
    anomaly_score: Mapped[float] = mapped_column(Float, nullable=False)
    is_anomaly: Mapped[bool] = mapped_column(Boolean, nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(30), nullable=False)
    suspected_issue: Mapped[str | None] = mapped_column(String(120), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, server_default=func.now()
    )

    measurement: Mapped["QoSMeasurement"] = relationship(back_populates="anomaly")
    recommendation: Mapped["AiRecommendation | None"] = relationship(
        back_populates="anomaly", cascade="all, delete-orphan", uselist=False
    )


class AiRecommendation(Base):
    """Generative AI explanation and corrective actions for an anomaly."""

    __tablename__ = "ai_recommendations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    anomaly_id: Mapped[int] = mapped_column(
        ForeignKey("anomaly_results.id", ondelete="CASCADE"), nullable=False, index=True
    )
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    likely_causes: Mapped[str] = mapped_column(Text, nullable=False)
    recommended_actions: Mapped[str] = mapped_column(Text, nullable=False)
    model_provider: Mapped[str] = mapped_column(String(80), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, server_default=func.now()
    )

    anomaly: Mapped["AnomalyResult"] = relationship(back_populates="recommendation")
