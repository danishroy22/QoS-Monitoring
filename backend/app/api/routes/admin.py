"""Administrator Analytics Portal API (Phase 18).

All routes live under ``/admin`` and read existing ``speed_tests`` data.
They do not replace consumer speed-test or dashboard endpoints.
"""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.admin import (
    AdminAiResponse,
    AdminDashboardResponse,
    BenchmarkProfile,
    BenchmarkResponse,
    HeatmapResponse,
    HistoryAnalyticsResponse,
    IspAnalyticsResponse,
)
from app.services import admin_ai, admin_report, admin_service

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/dashboard", response_model=AdminDashboardResponse)
def admin_dashboard(
    days: int | None = Query(default=90, ge=1, le=3650),
    db: Session = Depends(get_db),
) -> AdminDashboardResponse:
    """KPI cards, ISP leaderboard, live stats, and QoS overview."""
    return admin_service.get_dashboard(db, days=days)


@router.get("/isp-analytics", response_model=IspAnalyticsResponse)
def admin_isp_analytics(
    days: int | None = Query(default=90, ge=1, le=3650),
    db: Session = Depends(get_db),
) -> IspAnalyticsResponse:
    """Per-ISP download, upload, ping, jitter, loss, and QoS averages."""
    return admin_service.get_isp_analytics(db, days=days)


@router.get("/benchmarks", response_model=BenchmarkResponse)
def admin_benchmarks(
    days: int | None = Query(default=90, ge=1, le=3650),
    db: Session = Depends(get_db),
) -> BenchmarkResponse:
    """Compare every ISP against the Ideal Broadband Profile."""
    return admin_service.get_benchmarks(db, days=days)


@router.put("/benchmarks", response_model=BenchmarkResponse)
def admin_update_benchmarks(
    profile: BenchmarkProfile,
    days: int | None = Query(default=90, ge=1, le=3650),
    db: Session = Depends(get_db),
) -> BenchmarkResponse:
    """Persist configurable benchmark thresholds, then recompute rankings."""
    admin_service.save_profile(profile)
    return admin_service.get_benchmarks(db, days=days)


@router.get("/history", response_model=HistoryAnalyticsResponse)
def admin_history(
    granularity: Literal["daily", "weekly", "monthly"] = Query(default="daily"),
    days: int | None = Query(default=90, ge=1, le=3650),
    db: Session = Depends(get_db),
) -> HistoryAnalyticsResponse:
    """Daily, weekly, or monthly trend aggregates."""
    return admin_service.get_history(db, granularity=granularity, days=days)


@router.get("/heatmap", response_model=HeatmapResponse)
def admin_heatmap(
    days: int | None = Query(default=90, ge=1, le=3650),
    db: Session = Depends(get_db),
) -> HeatmapResponse:
    """Aggregate tests by Mauritius region from stored server labels."""
    return admin_service.get_heatmap(db, days=days)


@router.get("/ai/isp-analysis", response_model=AdminAiResponse)
def admin_ai_analysis(
    days: int | None = Query(default=90, ge=1, le=3650),
    db: Session = Depends(get_db),
) -> AdminAiResponse:
    """Natural-language summaries of each ISP's historical performance."""
    return admin_ai.generate_isp_analysis(db, days=days)


@router.get("/report")
def admin_report_pdf(
    days: int | None = Query(default=90, ge=1, le=3650),
    db: Session = Depends(get_db),
) -> Response:
    """Download a professional QoS PDF covering rankings, benchmarks, and AI."""
    bundle = admin_service.report_payload(db, days=days)
    bundle["ai"] = admin_ai.generate_isp_analysis(db, days=days)
    pdf = admin_report.build_qos_report_pdf(bundle)
    filename = "SmartQoS-Administrator-QoS-Report.pdf"
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
