"""Continuous QoS Monitoring API routes (Phase 7).

Additive endpoints — does not replace existing speed-test or dashboard APIs.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.monitoring import MonitoringStartRequest, MonitoringStatusResponse
from app.services import monitoring_service

router = APIRouter(tags=["monitoring"])


@router.get("/monitoring/status", response_model=MonitoringStatusResponse)
def monitoring_status(db: Session = Depends(get_db)) -> MonitoringStatusResponse:
    """Current monitoring enablement, schedule, and session stats."""
    return monitoring_service.get_status(db)


@router.post("/monitoring/start", response_model=MonitoringStatusResponse)
def monitoring_start(
    payload: MonitoringStartRequest,
    db: Session = Depends(get_db),
) -> MonitoringStatusResponse:
    """Enable continuous monitoring until manually stopped."""
    try:
        return monitoring_service.start_monitoring(db, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/monitoring/stop", response_model=MonitoringStatusResponse)
def monitoring_stop(db: Session = Depends(get_db)) -> MonitoringStatusResponse:
    """Disable continuous monitoring."""
    return monitoring_service.stop_monitoring(db)
