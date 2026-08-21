"""Internet Quality API routes — Ookla-style measurement platform."""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.internet import (
    AggregationResponse,
    AssistantResponse,
    ConnectionIdentity,
    DashboardResponse,
    HistoryResponse,
    IspResponse,
    SpeedTestCompleteRequest,
    SpeedTestFindServerResponse,
    SpeedTestLatencyPhaseOut,
    SpeedTestRequest,
    SpeedTestRunResponse,
    SpeedTestServerPhaseOut,
    SpeedTestServersResponse,
    StatisticsResponse,
)
from app.services import internet_service
from app.services.aggregation_service import AGGREGATION_DIMENSIONS
from measurement.servers import DEFAULT_SERVER_ID

router = APIRouter(tags=["internet-quality"])


def _sse_event(payload: dict) -> str:
    return f"data: {json.dumps(payload)}\n\n"


@router.get("/speedtest/servers", response_model=SpeedTestServersResponse)
def speedtest_servers() -> SpeedTestServersResponse:
    """List Mauritius broadband test servers from local configuration."""
    return SpeedTestServersResponse(
        servers=internet_service.list_speed_servers(),
        default_server_id=DEFAULT_SERVER_ID,
        auto_select=True,
    )


@router.get("/speedtest/config")
def speedtest_config() -> dict:
    """Documented measurement parameters and formulas (Phase 2)."""
    from measurement.config import public_methodology

    return public_methodology()


@router.get("/packages", response_model=None)
def list_public_packages(
    db: Session = Depends(get_db),
):
    """Active ISP packages for optional consumer selection (Phase 4)."""
    from app.schemas.packages import InternetPackageListResponse
    from app.services import package_service

    packages = package_service.list_packages(db, active_only=True)
    return InternetPackageListResponse(count=len(packages), packages=packages)


@router.post("/speedtest/identify", response_model=ConnectionIdentity)
def speedtest_identify() -> ConnectionIdentity:
    """Approximate public IP / ISP / region (network identity, not ground truth)."""
    return internet_service.identify_connection()


@router.post("/speedtest/find-server", response_model=SpeedTestFindServerResponse)
def speedtest_find_server(
    isp_name: str | None = Query(default=None),
) -> SpeedTestFindServerResponse:
    """Probe Mauritius servers and recommend the best candidate (additive scoring)."""
    return SpeedTestFindServerResponse.model_validate(
        internet_service.find_best_server(detected_isp=isp_name)
    )


@router.post("/speedtest", response_model=SpeedTestRunResponse)
def speedtest(
    payload: SpeedTestRequest | None = None,
    db: Session = Depends(get_db),
) -> SpeedTestRunResponse:
    """Run a full network measurement and store the result."""
    quick = payload.quick if payload else False
    server_id = payload.server_id if payload else None
    return internet_service.run_speedtest(db, quick=quick, server_id=server_id)


@router.post("/speedtest/measure/server", response_model=SpeedTestServerPhaseOut)
def speedtest_server_phase(
    server_id: str | None = Query(default=None),
) -> SpeedTestServerPhaseOut:
    """DNS, HTTP, and ISP lookup for the finding-server stage."""
    return internet_service.measure_server_phase(server_id=server_id)


@router.get("/speedtest/stream/download")
def speedtest_stream_download(
    quick: bool = Query(default=False),
    server_id: str | None = Query(default=None),
) -> StreamingResponse:
    """Stream live download Mbps while measuring throughput."""

    def generate():
        for event in internet_service.iter_download_phase(quick=quick, server_id=server_id):
            yield _sse_event(event)

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/speedtest/stream/upload")
def speedtest_stream_upload(
    quick: bool = Query(default=False),
    server_id: str | None = Query(default=None),
) -> StreamingResponse:
    """Stream live upload Mbps while measuring throughput."""

    def generate():
        for event in internet_service.iter_upload_phase(quick=quick, server_id=server_id):
            yield _sse_event(event)

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/speedtest/measure/latency", response_model=SpeedTestLatencyPhaseOut)
def speedtest_latency_phase(
    quick: bool = Query(default=False),
    server_id: str | None = Query(default=None),
) -> SpeedTestLatencyPhaseOut:
    """Measure ping, jitter, and packet loss against the selected server."""
    return internet_service.measure_latency_phase(quick=quick, server_id=server_id)


@router.post("/speedtest/complete", response_model=SpeedTestRunResponse)
def speedtest_complete(
    payload: SpeedTestCompleteRequest,
    db: Session = Depends(get_db),
) -> SpeedTestRunResponse:
    """Persist aggregated phased measurements and return scored results."""
    return internet_service.complete_speedtest(db, payload=payload)


@router.get("/history", response_model=HistoryResponse)
def history(
    limit: int = Query(default=50, ge=1, le=500),
    x_client_hash: str | None = Header(default=None, alias="X-Client-Hash"),
    db: Session = Depends(get_db),
) -> HistoryResponse:
    """Consumer history. Optional ``X-Client-Hash`` scopes to own tests (Phase 15)."""
    return internet_service.list_history(db, limit=limit, client_hash=x_client_hash)


@router.get("/dashboard", response_model=DashboardResponse)
def dashboard(db: Session = Depends(get_db)) -> DashboardResponse:
    return internet_service.get_dashboard(db)


@router.get("/statistics", response_model=StatisticsResponse)
def statistics(db: Session = Depends(get_db)) -> StatisticsResponse:
    return internet_service.get_statistics(db)


@router.get("/aggregations", response_model=AggregationResponse)
def aggregations(
    by: str = Query(
        default="isp",
        description=f"Group by: {', '.join(AGGREGATION_DIMENSIONS)}",
    ),
    days: int | None = Query(default=30, ge=1, le=3650),
    metric: str | None = Query(
        default=None,
        description="Required/useful when by=metric (e.g. download_mbps)",
    ),
    db: Session = Depends(get_db),
) -> AggregationResponse:
    """Traceable speed_tests aggregations (Phase 3). Same dimensions as Supabase views."""
    try:
        return internet_service.get_aggregations(db, by=by, days=days, metric=metric)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/isp", response_model=IspResponse)
def isp(db: Session = Depends(get_db)) -> IspResponse:
    return internet_service.get_isp(db)


@router.get("/recommendation", response_model=AssistantResponse)
def recommendation(db: Session = Depends(get_db)) -> AssistantResponse:
    """AI Network Assistant guidance based on latest + historical tests."""
    return internet_service.get_recommendation(db)
