"""Phase 12 filtered QoS report bundle + PDF smoke test."""

from __future__ import annotations

from datetime import datetime, timezone

from app.models.speedtest import SpeedTestResult
from app.services.admin_report import build_qos_report_pdf
from app.services.report_service import build_report_bundle


def test_report_bundle_and_pdf(db_session):
    db_session.add(
        SpeedTestResult(
            timestamp=datetime(2026, 8, 20, 12, tzinfo=timezone.utc),
            download_mbps=90,
            upload_mbps=30,
            ping_ms=15,
            jitter_ms=3,
            packet_loss_pct=0.1,
            overall_score=88,
            isp_name="Emtel Ltd",
            internet_package="Fibre 100",
            advertised_download_mbps=100,
            advertised_upload_mbps=40,
            download_fulfilment_pct=90,
            upload_fulfilment_pct=75,
            server_label="Emtel · Ebene",
            server_operator="Emtel",
            server_location="Ebene",
            detected_region="Ebene",
            hour_utc=12,
            ipv4_ok=True,
            ipv6_ok=False,
        )
    )
    db_session.commit()

    bundle = build_report_bundle(db_session, days=30, metric="download", comparison="isp_vs_isp")
    assert bundle["total_tests"] == 1
    assert bundle["period"]["from"] is not None
    assert bundle["servers"]
    assert "download" in bundle["metric_stats"]
    assert bundle["measurement_config"].get("version")
    assert bundle["limitations"]

    pdf = build_qos_report_pdf(bundle)
    assert pdf[:4] == b"%PDF"
    assert len(pdf) > 2000
