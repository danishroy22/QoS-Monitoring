"""Phase 9 administrator dashboard extras (hourly history + package performance)."""

from __future__ import annotations

from datetime import datetime, timezone

from app.models.speedtest import SpeedTestResult
from app.services.admin_service import get_history, get_package_performance


def test_history_hourly_buckets(db_session):
    db_session.add_all(
        [
            SpeedTestResult(
                timestamp=datetime(2026, 8, 20, 10, tzinfo=timezone.utc),
                hour_utc=10,
                download_mbps=100,
                upload_mbps=20,
                ping_ms=15,
                jitter_ms=3,
                packet_loss_pct=0.1,
                overall_score=90,
                isp_name="Emtel",
                server_label="Emtel · Ebene",
                ipv4_ok=True,
                ipv6_ok=False,
            ),
            SpeedTestResult(
                timestamp=datetime(2026, 8, 21, 10, tzinfo=timezone.utc),
                hour_utc=10,
                download_mbps=80,
                upload_mbps=18,
                ping_ms=20,
                jitter_ms=4,
                packet_loss_pct=0.2,
                overall_score=85,
                isp_name="Emtel",
                server_label="Emtel · Ebene",
                ipv4_ok=True,
                ipv6_ok=False,
            ),
            SpeedTestResult(
                timestamp=datetime(2026, 8, 20, 19, tzinfo=timezone.utc),
                hour_utc=19,
                download_mbps=60,
                upload_mbps=12,
                ping_ms=35,
                jitter_ms=8,
                packet_loss_pct=1.0,
                overall_score=70,
                isp_name="Emtel",
                server_label="Emtel · Ebene",
                ipv4_ok=True,
                ipv6_ok=False,
            ),
        ]
    )
    db_session.commit()

    history = get_history(db_session, granularity="hourly", days=30)
    assert history.granularity == "hourly"
    periods = [p.period for p in history.points]
    assert periods == ["10:00", "19:00"]
    morning = history.points[0]
    assert morning.tests == 2
    assert morning.avg_download_mbps == 90.0


def test_package_performance(db_session):
    db_session.add(
        SpeedTestResult(
            timestamp=datetime(2026, 8, 20, 12, tzinfo=timezone.utc),
            download_mbps=90,
            upload_mbps=36,
            ping_ms=12,
            jitter_ms=2,
            packet_loss_pct=0,
            overall_score=92,
            isp_name="Emtel Ltd",
            internet_package="Fibre 100",
            advertised_download_mbps=100,
            advertised_upload_mbps=40,
            download_fulfilment_pct=90,
            upload_fulfilment_pct=90,
            server_label="Emtel · Ebene",
            ipv4_ok=True,
            ipv6_ok=False,
        )
    )
    db_session.commit()

    payload = get_package_performance(db_session, days=30)
    assert payload.total_tests_with_package == 1
    assert len(payload.packages) == 1
    row = payload.packages[0]
    assert row.isp == "Emtel"
    assert row.package == "Fibre 100"
    assert row.avg_download_fulfilment_pct == 90.0
    assert row.advertised_download_mbps == 100.0
