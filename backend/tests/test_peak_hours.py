"""Peak-hour / congestion-pattern analysis (Phase 8)."""

from __future__ import annotations

from datetime import datetime, timezone

from app.models.speedtest import SpeedTestResult
from app.services.peak_hour_service import (
    INTERPRETATION,
    _degradation_index,
    _delta_block,
    analyze_peak_hours,
)


def test_delta_block_download_degraded():
    block = _delta_block(
        key="download_mbps",
        label="Download",
        unit="Mbps",
        higher_is_better=True,
        peak_avg=77,
        baseline_avg=100,
    )
    assert block["delta_pct"] == -23.0
    assert block["degraded"] is True


def test_delta_block_latency_degraded():
    block = _delta_block(
        key="ping_ms",
        label="Latency",
        unit="ms",
        higher_is_better=False,
        peak_avg=28.2,
        baseline_avg=20,
    )
    assert block["delta_pct"] == 41.0
    assert block["degraded"] is True


def test_degradation_index_positive_when_worse():
    peak = {
        "download_mbps": 70,
        "upload_mbps": 15,
        "ping_ms": 40,
        "jitter_ms": 10,
        "packet_loss_pct": 1.5,
        "overall_score": 60,
    }
    baseline = {
        "download_mbps": 100,
        "upload_mbps": 20,
        "ping_ms": 20,
        "jitter_ms": 5,
        "packet_loss_pct": 0.2,
        "overall_score": 90,
    }
    assert _degradation_index(peak, baseline) > 0.2


def _row(**kwargs):
    defaults = dict(
        timestamp=datetime(2026, 8, 20, 12, tzinfo=timezone.utc),
        download_mbps=100,
        upload_mbps=20,
        ping_ms=15,
        jitter_ms=3,
        packet_loss_pct=0.1,
        overall_score=90,
        isp_name="Emtel Ltd",
        internet_package="Fibre 100",
        server_label="Emtel · Ebene",
        detected_region="Ebene",
        ipv4_ok=True,
        ipv6_ok=False,
    )
    defaults.update(kwargs)
    return SpeedTestResult(**defaults)


def test_analyze_finds_evening_peak(db_session):
    # Off-peak morning samples
    for hour in (10, 11, 12):
        for _ in range(3):
            db_session.add(
                _row(
                    timestamp=datetime(2026, 8, 20, hour, tzinfo=timezone.utc),
                    hour_utc=hour,
                    day_of_week=3,
                    download_mbps=100,
                    ping_ms=15,
                    packet_loss_pct=0.1,
                    overall_score=90,
                )
            )
    # Peak evening samples — worse QoS
    for hour in (18, 19, 20):
        for _ in range(3):
            db_session.add(
                _row(
                    timestamp=datetime(2026, 8, 20, hour, tzinfo=timezone.utc),
                    hour_utc=hour,
                    day_of_week=3,
                    download_mbps=70,
                    ping_ms=30,
                    packet_loss_pct=1.5,
                    overall_score=65,
                    isp_name="Emtel Ltd",
                )
            )
    db_session.commit()

    payload = analyze_peak_hours(db_session, days=30)
    assert payload["peak_window"] is not None
    assert payload["peak_window"]["hour_from"] == 18
    assert payload["peak_window"]["hour_to"] == 21
    assert INTERPRETATION in payload["interpretation"]
    assert "cannot independently confirm" in payload["disclaimer"].lower()

    metrics = {m["key"]: m for m in payload["peak_window"]["metrics"]}
    assert metrics["download_mbps"]["degraded"] is True
    assert metrics["download_mbps"]["delta_pct"] is not None
    assert metrics["download_mbps"]["delta_pct"] < 0
    assert metrics["ping_ms"]["degraded"] is True
    assert metrics["ping_ms"]["delta_pct"] > 0

    assert any(h["in_peak_window"] for h in payload["hourly"])
    assert payload["breakdowns"]["isp"]
    assert payload["total_tests"] == 18


def test_analyze_empty(db_session):
    payload = analyze_peak_hours(db_session, days=7)
    assert payload["peak_window"] is None
    assert payload["total_tests"] == 0
