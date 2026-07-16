"""Anomaly endpoints.

GET endpoints are fully functional and read persisted anomaly results. The
detection trigger (POST /anomalies/run) is implemented in Phase 4 when the ML
model is added; until then it returns HTTP 501 with a clear message.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.network import AnomalyResult, NetworkNode, QoSMeasurement
from app.schemas.qos import AnomalyResponse

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


@router.post("/run")
def run_detection() -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        content={
            "detail": "Anomaly detection is implemented in Phase 4.",
            "model_name": "pending_phase_4",
        },
    )
