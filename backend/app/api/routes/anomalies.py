"""Anomaly detection endpoints (Phase 4)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.network import AnomalyResult, NetworkNode, QoSMeasurement
from app.schemas.qos import AnomalyResponse, DetectionRunResponse
from app.services import anomaly_service

router = APIRouter(prefix="/anomalies", tags=["anomalies"])


@router.get("", response_model=list[AnomalyResponse])
def list_anomalies(
    active_only: bool = Query(default=False),
    severity: str | None = Query(default=None),
    node_code: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=1000),
    db: Session = Depends(get_db),
) -> list[AnomalyResponse]:
    stmt = (
        select(AnomalyResult, NetworkNode.node_code)
        .join(QoSMeasurement, AnomalyResult.measurement_id == QoSMeasurement.id)
        .join(NetworkNode, QoSMeasurement.node_id == NetworkNode.id)
    )
    if active_only:
        stmt = stmt.where(AnomalyResult.is_anomaly.is_(True))
    if severity:
        stmt = stmt.where(AnomalyResult.severity == severity)
    if node_code:
        stmt = stmt.where(NetworkNode.node_code == node_code)
    stmt = stmt.order_by(AnomalyResult.created_at.desc()).limit(limit)

    results: list[AnomalyResponse] = []
    for anomaly, code in db.execute(stmt).all():
        results.append(
            AnomalyResponse(
                id=anomaly.id,
                measurement_id=anomaly.measurement_id,
                node_code=code,
                model_name=anomaly.model_name,
                anomaly_score=anomaly.anomaly_score,
                is_anomaly=anomaly.is_anomaly,
                severity=anomaly.severity,
                suspected_issue=anomaly.suspected_issue,
                created_at=anomaly.created_at,
            )
        )
    return results


@router.post("/run", response_model=DetectionRunResponse)
def run_detection(
    limit: int = Query(default=500, ge=1, le=5000),
    only_unscored: bool = Query(default=True),
    db: Session = Depends(get_db),
) -> DetectionRunResponse:
    """Score recent measurements with Isolation Forest and store results."""
    try:
        summary = anomaly_service.run_detection(
            db, limit=limit, only_unscored=only_unscored
        )
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Detection failed: {exc}",
        ) from exc

    return DetectionRunResponse(
        processed_measurements=summary.processed_measurements,
        anomalies_detected=summary.anomalies_detected,
        model_name=summary.model_name,
        skipped_existing=summary.skipped_existing,
    )
