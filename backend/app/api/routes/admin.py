"""Administrator Analytics Portal API.

All routes live under ``/admin`` and read existing ``speed_tests`` data.
They do not replace consumer speed-test or dashboard endpoints.

Phase 15 — role gating (Consumer blocked; ISP Admin scoped to own ISP).
Phase 16 — data-quality summary + reassess endpoints.
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
from app.services.auth_service import (
    AuthStatusResponse,
    Principal,
    apply_isp_scope,
    auth_status,
    require_admin_portal,
    require_full_admin,
)
from app.services import data_quality_service
from app.models.speedtest import SpeedTestResult
from sqlalchemy import select

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(require_admin_portal)],
)


@router.get("/auth/status", response_model=AuthStatusResponse)
def admin_auth_status(
    principal: Principal = Depends(require_admin_portal),
) -> AuthStatusResponse:
    """Current role, ISP scope, and permissions (Phase 15)."""
    return auth_status(principal)


@router.get("/dashboard", response_model=AdminDashboardResponse)
def admin_dashboard(
    days: int | None = Query(default=90, ge=1, le=3650),
    isp: str | None = Query(default=None),
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_admin_portal),
) -> AdminDashboardResponse:
    """KPI cards, ISP leaderboard, live stats, and QoS overview."""
    scoped = apply_isp_scope(principal, requested_isp=isp)
    return admin_service.get_dashboard(db, days=days, isp=scoped)


@router.get("/isp-analytics", response_model=IspAnalyticsResponse)
def admin_isp_analytics(
    days: int | None = Query(default=90, ge=1, le=3650),
    isp: str | None = Query(default=None),
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_admin_portal),
) -> IspAnalyticsResponse:
    """Per-ISP download, upload, ping, jitter, loss, and QoS averages."""
    scoped = apply_isp_scope(principal, requested_isp=isp)
    return admin_service.get_isp_analytics(db, days=days, isp=scoped)


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
    principal: Principal = Depends(require_admin_portal),
) -> IspComparisonResponse:
    """Fair ISP comparison with avg/median/min/max/stdev and filters (Phase 6)."""
    if principal.role == "isp_administrator":
        # Force both sides to own ISP — no cross-ISP private comparison.
        scoped = apply_isp_scope(principal, requested_isp=isp_a or isp_b)
        isp_a, isp_b = scoped, None
        mode = "isp_vs_benchmark"
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
    principal: Principal = Depends(require_admin_portal),
) -> PeakHourResponse:
    """Peak-hour / congestion-pattern analysis vs off-peak baseline (Phase 8)."""
    scoped = apply_isp_scope(principal, requested_isp=isp)
    payload = peak_hour_service.analyze_peak_hours(
        db,
        isp=scoped,
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
    principal: Principal = Depends(require_admin_portal),
) -> InternetPackageListResponse:
    """List administrator-configured ISP packages (Phase 4)."""
    scoped = apply_isp_scope(principal)
    packages = package_service.list_packages(db, active_only=active_only, isp=scoped)
    return InternetPackageListResponse(count=len(packages), packages=packages)


@router.post("/packages", response_model=InternetPackageOut, status_code=201)
def admin_create_package(
    payload: InternetPackageCreate,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_admin_portal),
) -> InternetPackageOut:
    """Add a configurable ISP package (advertised download / upload)."""
    if principal.role == "isp_administrator":
        apply_isp_scope(principal, requested_isp=payload.isp_name)
    elif principal.role != "administrator":
        raise HTTPException(status_code=403, detail="Insufficient role to create packages")
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
    principal: Principal = Depends(require_admin_portal),
) -> InternetPackageOut:
    """Update an existing ISP package."""
    if principal.role == "isp_administrator":
        from app.models.package import InternetPackage

        row = db.get(InternetPackage, package_id)
        if row is None:
            raise HTTPException(status_code=404, detail="Package not found")
        apply_isp_scope(principal, requested_isp=row.isp_name)
        if payload.isp_name:
            apply_isp_scope(principal, requested_isp=payload.isp_name)
    updated = package_service.update_package(db, package_id, payload)
    if updated is None:
        raise HTTPException(status_code=404, detail="Package not found")
    return updated


@router.delete("/packages/{package_id}", response_model=InternetPackageOut)
def admin_deactivate_package(
    package_id: int,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_admin_portal),
) -> InternetPackageOut:
    """Soft-delete a package (sets active=false)."""
    if principal.role == "isp_administrator":
        from app.models.package import InternetPackage

        row = db.get(InternetPackage, package_id)
        if row is None:
            raise HTTPException(status_code=404, detail="Package not found")
        apply_isp_scope(principal, requested_isp=row.isp_name)
    updated = package_service.deactivate_package(db, package_id)
    if updated is None:
        raise HTTPException(status_code=404, detail="Package not found")
    return updated


@router.get("/benchmarks", response_model=BenchmarkResponse)
def admin_benchmarks(
    days: int | None = Query(default=90, ge=1, le=3650),
    profile_id: str | None = Query(default=None),
    isp: str | None = Query(default=None),
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_admin_portal),
) -> BenchmarkResponse:
    """Compare every ISP against a configurable benchmark profile."""
    scoped = apply_isp_scope(principal, requested_isp=isp)
    return admin_service.get_benchmarks(db, days=days, profile_id=profile_id, isp=scoped)


@router.put("/benchmarks", response_model=BenchmarkResponse)
def admin_update_benchmarks(
    profile: BenchmarkProfile,
    days: int | None = Query(default=90, ge=1, le=3650),
    db: Session = Depends(get_db),
    _: Principal = Depends(require_full_admin),
) -> BenchmarkResponse:
    """Persist flat thresholds onto the active profile, then recompute rankings."""
    admin_service.save_profile(profile)
    return admin_service.get_benchmarks(db, days=days)


@router.get("/benchmark-profiles", response_model=BenchmarkProfilesResponse)
def admin_list_benchmark_profiles(
    _: Principal = Depends(require_admin_portal),
) -> BenchmarkProfilesResponse:
    """List all configurable Ideal/use-case benchmark profiles (Phase 7)."""
    return benchmark_service.list_profiles()


@router.put("/benchmark-profiles/active", response_model=BenchmarkProfilesResponse)
def admin_set_active_benchmark_profile(
    profile_id: str = Query(..., description="Profile id to activate"),
    _: Principal = Depends(require_full_admin),
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
    _: Principal = Depends(require_full_admin),
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
    isp: str | None = Query(default=None),
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_admin_portal),
) -> HistoryAnalyticsResponse:
    """Hourly (UTC hour-of-day), daily, weekly, or monthly trend aggregates."""
    scoped = apply_isp_scope(principal, requested_isp=isp)
    return admin_service.get_history(db, granularity=granularity, days=days, isp=scoped)


@router.get("/package-performance", response_model=PackagePerformanceResponse)
def admin_package_performance(
    days: int | None = Query(default=90, ge=1, le=3650),
    isp: str | None = Query(default=None),
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_admin_portal),
) -> PackagePerformanceResponse:
    """Advertised vs measured package performance (Phase 9)."""
    scoped = apply_isp_scope(principal, requested_isp=isp)
    return admin_service.get_package_performance(db, days=days, isp=scoped)


@router.get("/heatmap", response_model=HeatmapResponse)
def admin_heatmap(
    days: int | None = Query(default=90, ge=1, le=3650),
    isp: str | None = Query(default=None),
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_admin_portal),
) -> HeatmapResponse:
    """Legacy card heatmap by server locality (kept for reports)."""
    scoped = apply_isp_scope(principal, requested_isp=isp)
    return admin_service.get_heatmap(db, days=days, isp=scoped)


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
    principal: Principal = Depends(require_admin_portal),
) -> QosMapResponse:
    """Mauritius district GeoJSON QoS map with filters (Phase 5)."""
    scoped = apply_isp_scope(principal, requested_isp=isp)
    try:
        payload = map_service.build_qos_map(
            db,
            metric=metric,
            isp=scoped,
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
    isp: str | None = Query(default=None),
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_admin_portal),
) -> AdminAiResponse:
    """Natural-language summaries of each ISP's historical performance."""
    scoped = apply_isp_scope(principal, requested_isp=isp)
    return admin_ai.generate_isp_analysis(db, days=days, isp=scoped)


@router.get("/ai/facts", response_model=IspAiFactsResponse)
def admin_ai_facts(
    days: int | None = Query(default=90, ge=1, le=3650),
    isp: str | None = Query(default=None),
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_admin_portal),
) -> IspAiFactsResponse:
    """Structured ISP aggregates used to ground Phase 10 answers."""
    scoped = apply_isp_scope(principal, requested_isp=isp)
    return isp_ai_qa.list_isp_facts(db, days=days, isp=scoped)


@router.get("/ai/ask", response_model=IspAiAskResponse)
def admin_ai_ask(
    q: str = Query(..., min_length=3, description="ISP analytics question"),
    days: int | None = Query(default=90, ge=1, le=3650),
    isp: str | None = Query(default=None),
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_admin_portal),
) -> IspAiAskResponse:
    """Answer an ISP analytics question using retrieved database facts only."""
    scoped = apply_isp_scope(principal, requested_isp=isp)
    return isp_ai_qa.answer_isp_question(db, question=q, days=days, isp=scoped)


@router.post("/ai/ask", response_model=IspAiAskResponse)
def admin_ai_ask_post(
    payload: dict,
    days: int | None = Query(default=90, ge=1, le=3650),
    isp: str | None = Query(default=None),
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_admin_portal),
) -> IspAiAskResponse:
    """POST variant: body ``{\"question\": \"...\"}``."""
    question = str((payload or {}).get("question") or "").strip()
    if len(question) < 3:
        raise HTTPException(status_code=400, detail="question must be at least 3 characters")
    scoped = apply_isp_scope(principal, requested_isp=isp)
    return isp_ai_qa.answer_isp_question(db, question=question, days=days, isp=scoped)


@router.get("/ai/root-cause", response_model=RootCauseResponse)
def admin_ai_root_cause(
    isp: str | None = Query(default=None),
    package: str | None = Query(default=None),
    region: str | None = Query(default=None),
    days: int | None = Query(default=90, ge=1, le=3650),
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_admin_portal),
) -> RootCauseResponse:
    """Cautious root-cause *style* pattern explanations (Phase 11)."""
    scoped = apply_isp_scope(principal, requested_isp=isp)
    return root_cause_service.analyze_root_cause(
        db, isp=scoped, package=package, region=region, days=days
    )


@router.get("/data-quality")
def admin_data_quality(
    days: int | None = Query(default=90, ge=1, le=3650),
    isp: str | None = Query(default=None),
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_admin_portal),
) -> dict:
    """Phase 16 — quality flag counts and sample-size example (never deletes rows)."""
    scoped = apply_isp_scope(principal, requested_isp=isp)
    return data_quality_service.quality_summary(db, days=days, isp=scoped)


@router.post("/data-quality/reassess")
def admin_data_quality_reassess(
    limit: int = Query(default=5000, ge=1, le=50000),
    db: Session = Depends(get_db),
    _: Principal = Depends(require_full_admin),
) -> dict:
    """Re-mark existing rows with quality flags (does not delete)."""
    rows = list(
        db.scalars(select(SpeedTestResult).order_by(SpeedTestResult.id.desc()).limit(limit))
    )
    updated = 0
    for row in rows:
        data_quality_service.apply_quality_to_row(db, row)
        updated += 1
    db.commit()
    return {"reassessed": updated, "note": "Rows marked in place; none deleted."}


@router.get("/report")
def admin_report_pdf(
    days: int | None = Query(default=90, ge=1, le=3650),
    isp: str | None = Query(default=None),
    package: str | None = Query(default=None),
    region: str | None = Query(default=None),
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
    metric: str = Query(default="qos", description="download|upload|latency|jitter|packet_loss|qos"),
    comparison: str = Query(default="isp_vs_isp", description="isp_vs_isp|isp_vs_benchmark|isp_vs_ideal"),
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_admin_portal),
) -> Response:
    """Generate a professional multi-section QoS PDF (Phase 12)."""
    from app.services import report_service

    scoped = apply_isp_scope(principal, requested_isp=isp)
    if principal.role == "isp_administrator":
        comparison = "isp_vs_benchmark"
    bundle = report_service.build_report_bundle(
        db,
        days=None if (date_from or date_to) else days,
        isp=scoped,
        package=package,
        region=region,
        date_from=date_from,
        date_to=date_to,
        metric=metric,
        comparison=comparison,
    )
    bundle["ai"] = bundle.get("ai") or admin_ai.generate_isp_analysis(
        db, days=None if (date_from or date_to) else days, isp=scoped
    )
    pdf = admin_report.build_qos_report_pdf(bundle)
    filename = "SmartQoS-Administrator-QoS-Report.pdf"
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
