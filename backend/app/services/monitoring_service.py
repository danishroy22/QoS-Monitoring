"""Continuous QoS Monitoring service and background scheduler (Phase 7).

Reuses ``internet_service.run_speedtest`` so monitoring stores the same
``speed_tests`` rows as manual GO runs. Does not replace existing APIs.
"""

from __future__ import annotations

import logging
import threading
import time
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.monitoring import MonitoringState
from app.models.speedtest import SpeedTestResult
from app.schemas.monitoring import (
    PRESET_SECONDS,
    MonitoringLastMeasurement,
    MonitoringStartRequest,
    MonitoringStatusResponse,
)
from app.services.internet_service import run_speedtest

logger = logging.getLogger(__name__)

STATE_ID = 1
TICK_SECONDS = 5
_scheduler_thread: threading.Thread | None = None
_scheduler_stop = threading.Event()
_run_lock = threading.Lock()


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _ensure_state(db: Session) -> MonitoringState:
    row = db.get(MonitoringState, STATE_ID)
    if row is None:
        row = MonitoringState(id=STATE_ID)
        db.add(row)
        db.commit()
        db.refresh(row)
    return row


def _resolve_interval(payload: MonitoringStartRequest) -> tuple[str, int]:
    if payload.interval == "custom":
        if payload.custom_seconds is None:
            raise ValueError("custom_seconds is required when interval='custom'")
        seconds = int(payload.custom_seconds)
        if seconds < 60:
            raise ValueError("custom interval must be at least 60 seconds")
        return "custom", seconds
    seconds = PRESET_SECONDS[payload.interval]
    return payload.interval, seconds


def _duration_seconds(started_at: datetime | None, enabled: bool) -> int:
    if not enabled or started_at is None:
        return 0
    start = started_at if started_at.tzinfo else started_at.replace(tzinfo=timezone.utc)
    return max(0, int((_utcnow() - start).total_seconds()))


def _last_measurement(db: Session, result_id: int | None) -> MonitoringLastMeasurement | None:
    if not result_id:
        return None
    row = db.get(SpeedTestResult, result_id)
    if row is None:
        return None
    return MonitoringLastMeasurement(
        id=row.id,
        timestamp=row.timestamp,
        download_mbps=row.download_mbps,
        upload_mbps=row.upload_mbps,
        ping_ms=row.ping_ms,
        jitter_ms=row.jitter_ms,
        packet_loss_pct=row.packet_loss_pct,
        overall_score=row.overall_score,
        overall_rating=row.overall_rating,
        isp_name=row.isp_name,
        server_label=row.server_label,
    )


def get_status(db: Session) -> MonitoringStatusResponse:
    state = _ensure_state(db)
    return MonitoringStatusResponse(
        enabled=state.enabled,
        running=state.running,
        interval=state.interval_label,
        interval_seconds=state.interval_seconds,
        quick=state.quick,
        server_id=state.server_id,
        started_at=state.started_at,
        last_run_at=state.last_run_at,
        next_run_at=state.next_run_at,
        monitoring_duration_seconds=_duration_seconds(state.started_at, state.enabled),
        measurement_count=state.measurement_count,
        last_error=state.last_error,
        last_measurement=_last_measurement(db, state.last_result_id),
    )


def start_monitoring(db: Session, payload: MonitoringStartRequest) -> MonitoringStatusResponse:
    label, seconds = _resolve_interval(payload)
    state = _ensure_state(db)
    now = _utcnow()
    state.enabled = True
    state.interval_label = label
    state.interval_seconds = seconds
    state.quick = payload.quick
    state.server_id = payload.server_id
    state.started_at = now
    state.next_run_at = now  # run first sample promptly
    state.measurement_count = 0
    state.last_error = None
    state.updated_at = now
    db.commit()
    logger.info(
        "Monitoring started: interval=%ss (%s) quick=%s server=%s",
        seconds,
        label,
        payload.quick,
        payload.server_id,
    )
    return get_status(db)


def stop_monitoring(db: Session) -> MonitoringStatusResponse:
    state = _ensure_state(db)
    state.enabled = False
    state.running = False
    state.next_run_at = None
    state.updated_at = _utcnow()
    db.commit()
    logger.info("Monitoring stopped after %s measurements", state.measurement_count)
    return get_status(db)


def _execute_due_run() -> None:
    """Run one background speed test if monitoring is enabled and due."""
    if not _run_lock.acquire(blocking=False):
        return
    try:
        with SessionLocal() as db:
            state = _ensure_state(db)
            if not state.enabled:
                return
            now = _utcnow()
            next_at = state.next_run_at
            if next_at is not None:
                if next_at.tzinfo is None:
                    next_at = next_at.replace(tzinfo=timezone.utc)
                if now < next_at:
                    return

            state.running = True
            state.updated_at = now
            db.commit()

            quick = state.quick
            server_id = state.server_id
            interval = state.interval_seconds

        try:
            with SessionLocal() as db:
                result = run_speedtest(db, quick=quick, server_id=server_id)
                result_id = result.result.id if result.result else None
            with SessionLocal() as db:
                state = _ensure_state(db)
                if not state.enabled:
                    state.running = False
                    state.updated_at = _utcnow()
                    db.commit()
                    return
                finished = _utcnow()
                state.running = False
                state.last_run_at = finished
                state.next_run_at = finished + timedelta(seconds=state.interval_seconds or interval)
                state.measurement_count = int(state.measurement_count or 0) + 1
                state.last_result_id = result_id
                state.last_error = None
                state.updated_at = finished
                db.commit()
                logger.info(
                    "Monitoring sample #%s stored (result_id=%s)",
                    state.measurement_count,
                    result_id,
                )
        except Exception as exc:  # noqa: BLE001 — persist and continue schedule
            logger.exception("Monitoring measurement failed")
            with SessionLocal() as db:
                state = _ensure_state(db)
                finished = _utcnow()
                state.running = False
                state.last_error = str(exc)[:500]
                state.last_run_at = finished
                if state.enabled:
                    state.next_run_at = finished + timedelta(
                        seconds=max(60, state.interval_seconds or 300)
                    )
                state.updated_at = finished
                db.commit()
    finally:
        _run_lock.release()


def _scheduler_loop() -> None:
    logger.info("Monitoring scheduler started")
    while not _scheduler_stop.is_set():
        try:
            _execute_due_run()
        except Exception:  # noqa: BLE001
            logger.exception("Monitoring scheduler tick failed")
        _scheduler_stop.wait(TICK_SECONDS)
    logger.info("Monitoring scheduler stopped")


def start_scheduler() -> None:
    """Start the background monitoring thread (idempotent)."""
    global _scheduler_thread
    if _scheduler_thread and _scheduler_thread.is_alive():
        return
    _scheduler_stop.clear()
    _scheduler_thread = threading.Thread(
        target=_scheduler_loop,
        name="qos-monitoring-scheduler",
        daemon=True,
    )
    _scheduler_thread.start()


def stop_scheduler() -> None:
    """Signal the background thread to exit."""
    _scheduler_stop.set()
    thread = _scheduler_thread
    if thread and thread.is_alive():
        thread.join(timeout=TICK_SECONDS + 2)
