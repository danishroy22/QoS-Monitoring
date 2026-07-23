"""Service layer for Internet Quality speed tests and dashboard data."""

from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.speedtest import SpeedTestResult
from app.schemas.internet import (
    AssistantResponse,
    DashboardResponse,
    HealthBreakdown,
    HistoryResponse,
    IspResponse,
    SpeedTestCompleteRequest,
    SpeedTestLatencyPhaseOut,
    SpeedTestResultOut,
    SpeedTestRunResponse,
    SpeedTestServerPhaseOut,
    StatisticsResponse,
)
from measurement.assistant import build_assistant_context, generate_network_assistant
from measurement.engine import (
    NetworkMeasurementEngine,
    iter_download_progress,
    iter_upload_progress,
    run_latency_probe,
    run_server_probe,
    DOWNLOAD_PASS_BYTES_FULL,
    DOWNLOAD_PASS_BYTES_QUICK,
    DOWNLOAD_PASSES_FULL,
    DOWNLOAD_PASSES_QUICK,
    UPLOAD_TOTAL_BYTES_FULL,
    UPLOAD_TOTAL_BYTES_QUICK,
    PING_COUNT_FULL,
    PING_COUNT_QUICK,
)
from measurement.servers import list_servers, probe_mauritius_servers
from measurement.qos_analysis import analyze_qos


def _to_out(row: SpeedTestResult) -> SpeedTestResultOut:
    return SpeedTestResultOut.model_validate(row)


def _row_dict(row: SpeedTestResult) -> dict:
    return {
        "id": row.id,
        "timestamp": row.timestamp.isoformat() if row.timestamp else None,
        "download_mbps": row.download_mbps,
        "upload_mbps": row.upload_mbps,
        "ping_ms": row.ping_ms,
        "jitter_ms": row.jitter_ms,
        "packet_loss_pct": row.packet_loss_pct,
        "dns_lookup_ms": row.dns_lookup_ms,
        "http_response_ms": row.http_response_ms,
        "ipv4_ok": row.ipv4_ok,
        "ipv6_ok": row.ipv6_ok,
        "public_ip": row.public_ip,
        "isp_name": row.isp_name,
        "overall_score": row.overall_score,
        "overall_rating": row.overall_rating,
    }


def run_speedtest(
    db: Session, *, quick: bool = False, server_id: str | None = None
) -> SpeedTestRunResponse:
    engine = NetworkMeasurementEngine(quick=quick, server_id=server_id)
    measured = engine.run()
    return _persist_measurement(db, measured)


def list_speed_servers() -> list[dict]:
    return list_servers()


def find_best_server() -> dict:
    return probe_mauritius_servers()


def measure_server_phase(*, server_id: str | None = None) -> SpeedTestServerPhaseOut:
    payload = run_server_probe(server_id=server_id)
    return SpeedTestServerPhaseOut.model_validate(payload)


def measure_latency_phase(
    *, quick: bool = False, server_id: str | None = None
) -> SpeedTestLatencyPhaseOut:
    count = PING_COUNT_QUICK if quick else PING_COUNT_FULL
    payload = run_latency_probe(count=count, server_id=server_id)
    return SpeedTestLatencyPhaseOut.model_validate(payload)


def iter_download_phase(*, quick: bool = False, server_id: str | None = None):
    if quick:
        yield from iter_download_progress(
            bytes_per_pass=DOWNLOAD_PASS_BYTES_QUICK,
            passes=DOWNLOAD_PASSES_QUICK,
            server_id=server_id,
        )
    else:
        yield from iter_download_progress(
            bytes_per_pass=DOWNLOAD_PASS_BYTES_FULL,
            passes=DOWNLOAD_PASSES_FULL,
            server_id=server_id,
        )


def iter_upload_phase(*, quick: bool = False, server_id: str | None = None):
    total = UPLOAD_TOTAL_BYTES_QUICK if quick else UPLOAD_TOTAL_BYTES_FULL
    yield from iter_upload_progress(total_bytes=total, server_id=server_id)


def complete_speedtest(db: Session, payload: SpeedTestCompleteRequest) -> SpeedTestRunResponse:
    from measurement.engine import MeasurementResult

    measured = MeasurementResult(
        timestamp=datetime.now(timezone.utc),
        download_mbps=payload.download_mbps,
        upload_mbps=payload.upload_mbps,
        ping_ms=payload.ping_ms,
        jitter_ms=payload.jitter_ms,
        packet_loss_pct=payload.packet_loss_pct,
        dns_lookup_ms=payload.dns_lookup_ms,
        http_response_ms=payload.http_response_ms,
        ipv4_ok=payload.ipv4_ok,
        ipv6_ok=payload.ipv6_ok,
        public_ip=payload.public_ip,
        isp_name=payload.isp_name,
        as_info=payload.as_info,
        server_label=payload.server_label,
        errors=list(payload.errors),
    )
    return _persist_measurement(db, measured)


def _persist_measurement(db: Session, measured) -> SpeedTestRunResponse:
    health = analyze_qos(measured.to_dict())

    row = SpeedTestResult(
        timestamp=measured.timestamp,
        download_mbps=measured.download_mbps,
        upload_mbps=measured.upload_mbps,
        ping_ms=measured.ping_ms,
        jitter_ms=measured.jitter_ms,
        packet_loss_pct=measured.packet_loss_pct,
        dns_lookup_ms=measured.dns_lookup_ms,
        http_response_ms=measured.http_response_ms,
        ipv4_ok=measured.ipv4_ok,
        ipv6_ok=measured.ipv6_ok,
        public_ip=measured.public_ip,
        isp_name=measured.isp_name,
        as_info=measured.as_info,
        server_label=measured.server_label,
        overall_score=health.overall_score,
        overall_rating=health.overall_rating,
        errors_json=json.dumps(measured.errors) if measured.errors else None,
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    return SpeedTestRunResponse(
        result=_to_out(row),
        health=HealthBreakdown.model_validate(health.to_dict()),
        errors=measured.errors,
    )


def list_history(db: Session, *, limit: int = 50) -> HistoryResponse:
    rows = list(
        db.scalars(
            select(SpeedTestResult)
            .order_by(SpeedTestResult.timestamp.desc())
            .limit(limit)
        )
    )
    return HistoryResponse(count=len(rows), results=[_to_out(r) for r in rows])


def _avg(db: Session, column) -> float | None:
    value = db.scalar(select(func.avg(column)))
    return float(value) if value is not None else None


def get_statistics(db: Session) -> StatisticsResponse:
    count = int(db.scalar(select(func.count(SpeedTestResult.id))) or 0)
    latest = db.scalar(
        select(SpeedTestResult).order_by(SpeedTestResult.timestamp.desc()).limit(1)
    )
    best = db.scalar(select(func.max(SpeedTestResult.overall_score)))
    worst = db.scalar(select(func.min(SpeedTestResult.overall_score)))
    return StatisticsResponse(
        count=count,
        avg_download_mbps=_avg(db, SpeedTestResult.download_mbps),
        avg_upload_mbps=_avg(db, SpeedTestResult.upload_mbps),
        avg_ping_ms=_avg(db, SpeedTestResult.ping_ms),
        avg_jitter_ms=_avg(db, SpeedTestResult.jitter_ms),
        avg_packet_loss_pct=_avg(db, SpeedTestResult.packet_loss_pct),
        avg_overall_score=_avg(db, SpeedTestResult.overall_score),
        best_overall_score=int(best) if best is not None else None,
        worst_overall_score=int(worst) if worst is not None else None,
        latest_rating=latest.overall_rating if latest else None,
    )


def get_isp(db: Session) -> IspResponse:
    latest = db.scalar(
        select(SpeedTestResult).order_by(SpeedTestResult.timestamp.desc()).limit(1)
    )
    if latest is None:
        return IspResponse(public_ip=None, isp_name=None, as_info=None)
    return IspResponse(
        public_ip=latest.public_ip,
        isp_name=latest.isp_name,
        as_info=latest.as_info,
        ipv4_ok=latest.ipv4_ok,
        ipv6_ok=latest.ipv6_ok,
        last_tested_at=latest.timestamp,
    )


def get_dashboard(db: Session, *, history_limit: int = 24) -> DashboardResponse:
    latest = db.scalar(
        select(SpeedTestResult).order_by(SpeedTestResult.timestamp.desc()).limit(1)
    )
    history_rows = list(
        db.scalars(
            select(SpeedTestResult)
            .order_by(SpeedTestResult.timestamp.desc())
            .limit(history_limit)
        )
    )
    health = None
    latest_out = None
    if latest is not None:
        latest_out = _to_out(latest)
        health = HealthBreakdown.model_validate(analyze_qos(_row_dict(latest)).to_dict())

    return DashboardResponse(
        latest=latest_out,
        health=health,
        statistics=get_statistics(db),
        history=[_to_out(r) for r in reversed(history_rows)],
        isp=get_isp(db),
    )


def get_recommendation(db: Session) -> AssistantResponse:
    rows = list(
        db.scalars(
            select(SpeedTestResult).order_by(SpeedTestResult.timestamp.asc()).limit(40)
        )
    )
    if not rows:
        return AssistantResponse(
            analysis="No speed tests yet. Run a test to receive AI network guidance.",
            possible_reasons=["Insufficient measurement history"],
            recommended_actions=["Click Go / Run Speed Test to measure your connection"],
            model_provider="network-assistant-fallback-v1",
            generated_at=datetime.now(timezone.utc),
        )

    latest = rows[-1]
    health = analyze_qos(_row_dict(latest)).to_dict()
    context = build_assistant_context(
        _row_dict(latest),
        [_row_dict(r) for r in rows],
        health,
    )
    generated = generate_network_assistant(context)
    return AssistantResponse(
        analysis=generated["analysis"],
        possible_reasons=list(generated["possible_reasons"]),
        recommended_actions=list(generated["recommended_actions"]),
        focus_metric=generated.get("focus_metric"),
        overall_rating=generated.get("overall_rating"),
        overall_score=generated.get("overall_score"),
        model_provider=generated.get("model_provider", "network-assistant-fallback-v1"),
        generated_at=datetime.now(timezone.utc),
    )
