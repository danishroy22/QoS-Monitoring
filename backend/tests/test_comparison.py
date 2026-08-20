"""Tests for fair ISP comparison (Phase 6)."""

from __future__ import annotations

from datetime import datetime, timezone

from app.models.speedtest import SpeedTestResult
from app.services.comparison_service import _stats, compare_isps


def test_stats_include_median_and_stdev():
    block = _stats([10, 20, 30, 40])
    assert block["count"] == 4
    assert block["avg"] == 25.0
    assert block["median"] == 25.0
    assert block["min"] == 10.0
    assert block["max"] == 40.0
    assert block["stdev"] is not None


def test_compare_orders_by_qos_not_download(db_session):
    db_session.add_all(
        [
            SpeedTestResult(
                timestamp=datetime(2026, 8, 20, 10, tzinfo=timezone.utc),
                download_mbps=300,
                upload_mbps=40,
                ping_ms=40,
                jitter_ms=12,
                packet_loss_pct=1.5,
                dns_lookup_ms=40,
                http_response_ms=250,
                overall_score=55,
                isp_name="FastButUnstable ISP",
                internet_package="Fibre 300",
                download_fulfilment_pct=100,
                upload_fulfilment_pct=100,
                server_label="X · Ebene",
                server_location="Ebene",
                detected_region="Ebene",
                hour_utc=10,
                ipv4_ok=True,
                ipv6_ok=False,
            ),
            SpeedTestResult(
                timestamp=datetime(2026, 8, 20, 11, tzinfo=timezone.utc),
                download_mbps=90,
                upload_mbps=35,
                ping_ms=12,
                jitter_ms=2,
                packet_loss_pct=0,
                dns_lookup_ms=15,
                http_response_ms=120,
                overall_score=92,
                isp_name="Emtel Ltd",
                internet_package="Fibre 100",
                download_fulfilment_pct=90,
                upload_fulfilment_pct=88,
                server_label="Emtel · Ebene",
                server_location="Ebene",
                detected_region="Ebene",
                hour_utc=11,
                ipv4_ok=True,
                ipv6_ok=False,
            ),
        ]
    )
    db_session.commit()

    payload = compare_isps(db_session, mode="isp_vs_isp", days=30)
    assert payload["isps"][0]["isp"] == "Emtel"
    assert "QoS" in payload["ranking_note"]
    keys = {m["key"] for m in payload["isps"][0]["metrics"]}
    assert "fulfilment_pct" in keys
    assert "dns_lookup_ms" in keys
    assert "http_response_ms" in keys


def test_compare_vs_ideal_includes_targets(db_session):
    db_session.add(
        SpeedTestResult(
            timestamp=datetime(2026, 8, 20, 12, tzinfo=timezone.utc),
            download_mbps=110,
            upload_mbps=25,
            ping_ms=18,
            overall_score=88,
            isp_name="Emtel",
            ipv4_ok=True,
            ipv6_ok=False,
            server_label="Emtel · Arsenal",
        )
    )
    db_session.commit()
    payload = compare_isps(db_session, mode="isp_vs_ideal", days=30)
    assert payload["profile"] is not None
    download = next(m for m in payload["isps"][0]["metrics"] if m["key"] == "download_mbps")
    assert download["target"] is not None
    assert download["meets_target"] is not None


def test_package_filter_scopes_comparison(db_session):
    db_session.add_all(
        [
            SpeedTestResult(
                timestamp=datetime(2026, 8, 20, 12, tzinfo=timezone.utc),
                download_mbps=80,
                overall_score=80,
                isp_name="Emtel",
                internet_package="Fibre 100",
                ipv4_ok=True,
                ipv6_ok=False,
                server_label="Emtel · Ebene",
                server_location="Ebene",
            ),
            SpeedTestResult(
                timestamp=datetime(2026, 8, 20, 13, tzinfo=timezone.utc),
                download_mbps=200,
                overall_score=85,
                isp_name="Orange",
                internet_package="Fibre 200",
                ipv4_ok=True,
                ipv6_ok=False,
                server_label="MT · Floreal",
                server_location="Floreal",
            ),
        ]
    )
    db_session.commit()
    payload = compare_isps(db_session, mode="isp_vs_isp", package="Fibre 100", days=30)
    assert payload["total_tests"] == 1
    assert payload["isps"][0]["isp"] == "Emtel"
