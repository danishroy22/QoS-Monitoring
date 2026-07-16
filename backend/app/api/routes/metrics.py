"""Live and historical metric endpoints for the dashboard."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.qos import HistoryPoint, HistoryResponse, LatestMetric, NodeResponse
from app.services import measurement_service
from app.services.health_rules import classify_health
from app.services.measurement_service import VALID_METRICS, NodeNotFoundError

router = APIRouter(tags=["metrics"])


@router.get("/nodes", response_model=list[NodeResponse])
def list_nodes(db: Session = Depends(get_db)) -> list[NodeResponse]:
    return [NodeResponse.model_validate(node) for node in measurement_service.list_nodes(db)]


@router.get("/metrics/latest", response_model=list[LatestMetric])
def latest_metrics(
    limit: int | None = Query(default=None, ge=1, le=1000),
    db: Session = Depends(get_db),
) -> list[LatestMetric]:
    """Return the newest measurement per node with a health label."""
    rows = measurement_service.get_latest_per_node(db, limit=limit)
    response: list[LatestMetric] = []
    for measurement, node in rows:
        health_status = classify_health(
            latency_ms=measurement.latency_ms,
            jitter_ms=measurement.jitter_ms,
            packet_loss_pct=measurement.packet_loss_pct,
            bandwidth_utilisation_pct=measurement.bandwidth_utilisation_pct,
            availability_pct=measurement.availability_pct,
        )
        response.append(
            LatestMetric(
                id=measurement.id,
                node_code=node.node_code,
                timestamp=measurement.timestamp,
                latency_ms=measurement.latency_ms,
                jitter_ms=measurement.jitter_ms,
                packet_loss_pct=measurement.packet_loss_pct,
                throughput_mbps=measurement.throughput_mbps,
                bandwidth_utilisation_pct=measurement.bandwidth_utilisation_pct,
                signal_quality=measurement.signal_quality,
                availability_pct=measurement.availability_pct,
                scenario_label=measurement.scenario_label,
                region=node.region,
                access_technology=node.access_technology,
                service_tier_mbps=node.service_tier_mbps,
                health_status=health_status,
            )
        )
    return response


@router.get("/metrics/history", response_model=HistoryResponse)
def metric_history(
    node_code: str = Query(...),
    metric: str = Query(default="latency_ms"),
    start_time: datetime | None = Query(default=None),
    end_time: datetime | None = Query(default=None),
    limit: int = Query(default=500, ge=1, le=5000),
    db: Session = Depends(get_db),
) -> HistoryResponse:
    """Return a time-series for one node and one metric."""
    if metric not in VALID_METRICS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid metric '{metric}'. Valid options: {sorted(VALID_METRICS)}",
        )
    try:
        measurements = measurement_service.get_history(
            db,
            node_code=node_code,
            metric=metric,
            start_time=start_time,
            end_time=end_time,
            limit=limit,
        )
    except NodeNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    points = [
        HistoryPoint(timestamp=m.timestamp, value=getattr(m, metric))
        for m in measurements
        if getattr(m, metric) is not None
    ]
    return HistoryResponse(node_code=node_code, metric=metric, points=points)
