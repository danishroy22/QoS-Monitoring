"""Administrator Analytics Portal API (Phase 18).

All routes live under ``/admin`` and read existing ``speed_tests`` data.
They do not replace consumer speed-test or dashboard endpoints.
"""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.admin import (
    AdminAiResponse,
    AdminDashboardResponse,
    BenchmarkProfile,
    BenchmarkProfileDetail,
    BenchmarkProfilesResponse,
    BenchmarkResponse,
    HeatmapResponse,
    HistoryAnalyticsResponse,
    IspAnalyticsResponse,
    IspAiAskResponse,
    IspAiFactsResponse,
    IspComparisonResponse,
    PackagePerformanceResponse,
    PeakHourResponse,
    QosMapResponse,
    RootCauseResponse,
)
from app.schemas.packages import (
    InternetPackageCreate,
    InternetPackageListResponse,
    InternetPackageOut,
    InternetPackageUpdate,
)
from app.services import (
    admin_ai,
    admin_report,
    admin_service,
    benchmark_service,
    comparison_service,
    isp_ai_qa,
    package_service,
    peak_hour_service,
    root_cause_service,
)
from app.services import map_service

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


@router.get("/comparison", response_model=IspComparisonResponse)
def admin_isp_comparison(
    mode: str = Query(
        default="isp_vs_isp",
        description="isp_vs_isp | isp_vs_benchmark | isp_vs_ideal",
    ),
    isp_a: str | None = Query(default=None),
    isp_b: str | None = Query(default=None),
    package: str | None = Query(default=None),
    region: str | None = Query(default=None),
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
    days: int | None = Query(default=90, ge=1, le=3650),
    hour_from: int | None = Query(default=None, ge=0, le=23),
    hour_to: int | None = Query(default=None, ge=0, le=23),
    db: Session = Depends(get_db),
) -> IspComparisonResponse:
    """Fair ISP comparison with avg/median/min/max/stdev and filters (Phase 6)."""
    try:
        payload = comparison_service.compare_isps(
            db,
            mode=mode,  # type: ignore[arg-type]
            isp_a=isp_a,
            isp_b=isp_b,
            package=package,
            region=region,
            date_from=date_from,
            date_to=date_to,
            days=None if (date_from or date_to) else days,
            hour_from=hour_from,
            hour_to=hour_to,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return IspComparisonResponse.model_validate(payload)


@router.get("/peak-hours", response_model=PeakHourResponse)
def admin_peak_hours(
    isp: str | None = Query(default=None),
    package: str | None = Query(default=None),
    region: str | None = Query(default=None),
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
    days: int | None = Query(default=90, ge=1, le=3650),
    db: Session = Depends(get_db),
) -> PeakHourResponse:
    """Peak-hour / congestion-pattern analysis vs off-peak baseline (Phase 8)."""
    payload = peak_hour_service.analyze_peak_hours(
        db,
        isp=isp,
        package=package,
        region=region,
        date_from=date_from,
        date_to=date_to,
        days=None if (date_from or date_to) else days,
    )
    return PeakHourResponse.model_validate(payload)


@router.get("/packages", response_model=InternetPackageListResponse)
def admin_list_packages(
    active_only: bool = Query(default=False),
    db: Session = Depends(get_db),
) -> InternetPackageListResponse:
    """List administrator-configured ISP packages (Phase 4)."""
    packages = package_service.list_packages(db, active_only=active_only)
    return InternetPackageListResponse(count=len(packages), packages=packages)


@router.post("/packages", response_model=InternetPackageOut, status_code=201)
def admin_create_package(
    payload: InternetPackageCreate,
    db: Session = Depends(get_db),
) -> InternetPackageOut:
    """Add a configurable ISP package (advertised download / upload)."""
    try:
        return package_service.create_package(db, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.put("/packages/{package_id}", response_model=InternetPackageOut)
def admin_update_package(
    package_id: int,
    payload: InternetPackageUpdate,
    db: Session = Depends(get_db),
) -> InternetPackageOut:
    """Update an existing ISP package."""
    updated = package_service.update_package(db, package_id, payload)
    if updated is None:
        raise HTTPException(status_code=404, detail="Package not found")
    return updated


@router.delete("/packages/{package_id}", response_model=InternetPackageOut)
def admin_deactivate_package(
    package_id: int,
    db: Session = Depends(get_db),
) -> InternetPackageOut:
    """Soft-delete a package (sets active=false)."""
    updated = package_service.deactivate_package(db, package_id)
    if updated is None:
        raise HTTPException(status_code=404, detail="Package not found")
    return updated


@router.get("/benchmarks", response_model=BenchmarkResponse)
def admin_benchmarks(
    days: int | None = Query(default=90, ge=1, le=3650),
    profile_id: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> BenchmarkResponse:
    """Compare every ISP against a configurable benchmark profile."""
    return admin_service.get_benchmarks(db, days=days, profile_id=profile_id)


@router.put("/benchmarks", response_model=BenchmarkResponse)
def admin_update_benchmarks(
    profile: BenchmarkProfile,
    days: int | None = Query(default=90, ge=1, le=3650),
    db: Session = Depends(get_db),
) -> BenchmarkResponse:
    """Persist flat thresholds onto the active profile, then recompute rankings."""
    admin_service.save_profile(profile)
    return admin_service.get_benchmarks(db, days=days)


@router.get("/benchmark-profiles", response_model=BenchmarkProfilesResponse)
def admin_list_benchmark_profiles() -> BenchmarkProfilesResponse:
    """List all configurable Ideal/use-case benchmark profiles (Phase 7)."""
    return benchmark_service.list_profiles()


@router.put("/benchmark-profiles/active", response_model=BenchmarkProfilesResponse)
def admin_set_active_benchmark_profile(
    profile_id: str = Query(..., description="Profile id to activate"),
) -> BenchmarkProfilesResponse:
    """Select which benchmark profile is active for rankings and comparisons."""
    try:
        return benchmark_service.set_active_profile(profile_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.put("/benchmark-profiles/{profile_id}", response_model=BenchmarkProfilesResponse)
def admin_update_benchmark_profile(
    profile_id: str,
    payload: BenchmarkProfileDetail,
) -> BenchmarkProfilesResponse:
    """Update a profile including per-metric source, rationale, unit, and threshold."""
    if payload.id and payload.id != profile_id:
        raise HTTPException(status_code=400, detail="Body id must match path profile_id")
    try:
        return benchmark_service.update_profile(profile_id, payload.model_copy(update={"id": profile_id}))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/history", response_model=HistoryAnalyticsResponse)
def admin_history(
    granularity: Literal["hourly", "daily", "weekly", "monthly"] = Query(default="daily"),
    days: int | None = Query(default=90, ge=1, le=3650),
    db: Session = Depends(get_db),
) -> HistoryAnalyticsResponse:
    """Hourly (UTC hour-of-day), daily, weekly, or monthly trend aggregates."""
    return admin_service.get_history(db, granularity=granularity, days=days)


@router.get("/package-performance", response_model=PackagePerformanceResponse)
def admin_package_performance(
    days: int | None = Query(default=90, ge=1, le=3650),
    db: Session = Depends(get_db),
) -> PackagePerformanceResponse:
    """Advertised vs measured package performance (Phase 9)."""
    return admin_service.get_package_performance(db, days=days)


@router.get("/heatmap", response_model=HeatmapResponse)
def admin_heatmap(
    days: int | None = Query(default=90, ge=1, le=3650),
    db: Session = Depends(get_db),
) -> HeatmapResponse:
    """Legacy card heatmap by server locality (kept for reports)."""
    return admin_service.get_heatmap(db, days=days)


@router.get("/map", response_model=QosMapResponse)
def admin_qos_map(
    metric: str = Query(default="qos", description="download|upload|latency|jitter|packet_loss|qos|fulfilment"),
    isp: str | None = Query(default=None),
    package: str | None = Query(default=None),
    region: str | None = Query(default=None),
    date_from: str | None = Query(default=None, description="ISO date or datetime"),
    date_to: str | None = Query(default=None, description="ISO date or datetime"),
    days: int | None = Query(default=30, ge=1, le=3650),
    day_of_week: int | None = Query(default=None, ge=0, le=6, description="Monday=0 … Sunday=6"),
    hour_from: int | None = Query(default=None, ge=0, le=23),
    hour_to: int | None = Query(default=None, ge=0, le=23),
    db: Session = Depends(get_db),
) -> QosMapResponse:
    """Mauritius district GeoJSON QoS map with filters (Phase 5)."""
    try:
        payload = map_service.build_qos_map(
            db,
            metric=metric,
            isp=isp,
            package=package,
            region=region,
            date_from=date_from,
            date_to=date_to,
            days=None if (date_from or date_to) else days,
            day_of_week=day_of_week,
            hour_from=hour_from,
            hour_to=hour_to,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return QosMapResponse.model_validate(payload)


@router.get("/ai/isp-analysis", response_model=AdminAiResponse)
def admin_ai_analysis(
    days: int | None = Query(default=90, ge=1, le=3650),
    db: Session = Depends(get_db),
) -> AdminAiResponse:
    """Natural-language summaries of each ISP's historical performance."""
    return admin_ai.generate_isp_analysis(db, days=days)


@router.get("/ai/facts", response_model=IspAiFactsResponse)
def admin_ai_facts(
    days: int | None = Query(default=90, ge=1, le=3650),
    db: Session = Depends(get_db),
) -> IspAiFactsResponse:
    """Structured ISP aggregates used to ground Phase 10 answers."""
    return isp_ai_qa.list_isp_facts(db, days=days)


@router.get("/ai/ask", response_model=IspAiAskResponse)
def admin_ai_ask(
    q: str = Query(..., min_length=3, description="ISP analytics question"),
    days: int | None = Query(default=90, ge=1, le=3650),
    db: Session = Depends(get_db),
) -> IspAiAskResponse:
    """Answer an ISP analytics question using retrieved database facts only."""
    return isp_ai_qa.answer_isp_question(db, question=q, days=days)


@router.post("/ai/ask", response_model=IspAiAskResponse)
def admin_ai_ask_post(
    payload: dict,
    days: int | None = Query(default=90, ge=1, le=3650),
    db: Session = Depends(get_db),
) -> IspAiAskResponse:
    """POST variant: body ``{\"question\": \"...\"}``."""
    question = str((payload or {}).get("question") or "").strip()
    if len(question) < 3:
        raise HTTPException(status_code=400, detail="question must be at least 3 characters")
    return isp_ai_qa.answer_isp_question(db, question=question, days=days)


@router.get("/ai/root-cause", response_model=RootCauseResponse)
def admin_ai_root_cause(
    isp: str | None = Query(default=None),
    package: str | None = Query(default=None),
    region: str | None = Query(default=None),
    days: int | None = Query(default=90, ge=1, le=3650),
    db: Session = Depends(get_db),
) -> RootCauseResponse:
    """Cautious root-cause *style* pattern explanations (Phase 11)."""
    return root_cause_service.analyze_root_cause(
        db, isp=isp, package=package, region=region, days=days
    )


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
