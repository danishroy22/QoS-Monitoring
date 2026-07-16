"""Services for storing and querying QoS measurements and nodes."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.network import NetworkNode, QoSMeasurement
from app.schemas.qos import MeasurementCreate

VALID_METRICS = {
    "latency_ms",
    "jitter_ms",
    "packet_loss_pct",
    "throughput_mbps",
    "bandwidth_utilisation_pct",
    "signal_quality",
    "availability_pct",
}


class NodeNotFoundError(Exception):
    """Raised when a measurement references an unknown node_code."""

    def __init__(self, node_code: str) -> None:
        super().__init__(f"Unknown node_code: {node_code}")
        self.node_code = node_code


def get_node_by_code(db: Session, node_code: str) -> NetworkNode | None:
    return db.scalar(select(NetworkNode).where(NetworkNode.node_code == node_code))


def list_nodes(db: Session) -> list[NetworkNode]:
    return list(db.scalars(select(NetworkNode).order_by(NetworkNode.node_code)))


def create_measurement(db: Session, payload: MeasurementCreate) -> QoSMeasurement:
    """Persist one measurement, resolving node_code to a node id."""
    node = get_node_by_code(db, payload.node_code)
    if node is None:
        raise NodeNotFoundError(payload.node_code)

    measurement = QoSMeasurement(
        node_id=node.id,
        timestamp=payload.timestamp,
        latency_ms=payload.latency_ms,
        jitter_ms=payload.jitter_ms,
        packet_loss_pct=payload.packet_loss_pct,
        throughput_mbps=payload.throughput_mbps,
        bandwidth_utilisation_pct=payload.bandwidth_utilisation_pct,
        signal_quality=payload.signal_quality,
        availability_pct=payload.availability_pct,
        scenario_label=payload.scenario_label,
    )
    db.add(measurement)
    db.commit()
    db.refresh(measurement)
    return measurement


def get_latest_per_node(db: Session, limit: int | None = None) -> list[tuple[QoSMeasurement, NetworkNode]]:
    """Return the most recent measurement for each node."""
    nodes = list_nodes(db)
    results: list[tuple[QoSMeasurement, NetworkNode]] = []
    for node in nodes:
        latest = db.scalar(
            select(QoSMeasurement)
            .where(QoSMeasurement.node_id == node.id)
            .order_by(QoSMeasurement.timestamp.desc())
            .limit(1)
        )
        if latest is not None:
            results.append((latest, node))
    if limit is not None:
        results = results[:limit]
    return results


def get_history(
    db: Session,
    *,
    node_code: str,
    metric: str,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    limit: int = 500,
) -> list[QoSMeasurement]:
    """Return ordered measurements for one node for charting."""
    node = get_node_by_code(db, node_code)
    if node is None:
        raise NodeNotFoundError(node_code)

    stmt = select(QoSMeasurement).where(QoSMeasurement.node_id == node.id)
    if start_time is not None:
        stmt = stmt.where(QoSMeasurement.timestamp >= start_time)
    if end_time is not None:
        stmt = stmt.where(QoSMeasurement.timestamp <= end_time)
    stmt = stmt.order_by(QoSMeasurement.timestamp.asc()).limit(limit)
    return list(db.scalars(stmt))
