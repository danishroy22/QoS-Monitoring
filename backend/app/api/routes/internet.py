"""Internet Quality API routes — Ookla-style measurement platform."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.internet import (
    AssistantResponse,
    DashboardResponse,
    HistoryResponse,
    IspResponse,
    SpeedTestRequest,
    SpeedTestRunResponse,
    StatisticsResponse,
)
from app.services import internet_service

router = APIRouter(tags=["internet-quality"])


@router.post("/speedtest", response_model=SpeedTestRunResponse)
def speedtest(
    payload: SpeedTestRequest | None = None,
    db: Session = Depends(get_db),
) -> SpeedTestRunResponse:
    """Run a real network measurement and store the result."""
    quick = payload.quick if payload else False
    return internet_service.run_speedtest(db, quick=quick)


@router.get("/history", response_model=HistoryResponse)
def history(
    limit: int = Query(default=50, ge=1, le=500),
    db: Session = Depends(get_db),
) -> HistoryResponse:
    return internet_service.list_history(db, limit=limit)


@router.get("/dashboard", response_model=DashboardResponse)
def dashboard(db: Session = Depends(get_db)) -> DashboardResponse:
    return internet_service.get_dashboard(db)


@router.get("/statistics", response_model=StatisticsResponse)
def statistics(db: Session = Depends(get_db)) -> StatisticsResponse:
    return internet_service.get_statistics(db)


@router.get("/isp", response_model=IspResponse)
def isp(db: Session = Depends(get_db)) -> IspResponse:
    return internet_service.get_isp(db)


@router.get("/recommendation", response_model=AssistantResponse)
def recommendation(db: Session = Depends(get_db)) -> AssistantResponse:
    """AI Network Assistant guidance based on latest + historical tests."""
    return internet_service.get_recommendation(db)
