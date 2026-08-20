"""Tests for Phase 3 privacy helpers and aggregations."""

from __future__ import annotations

from datetime import datetime, timezone

from app.services.privacy import anonymize_client_id, time_buckets
from app.services.aggregation_service import AGGREGATION_DIMENSIONS, aggregate_measurements
from app.models.speedtest import SpeedTestResult


def test_anonymize_client_id_stable_and_truncated():
    a = anonymize_client_id("1.2.3.4", salt="unit-test-salt")
    b = anonymize_client_id("1.2.3.4", salt="unit-test-salt")
    c = anonymize_client_id("1.2.3.5", salt="unit-test-salt")
    assert a == b
    assert a != c
    assert a is not None and len(a) == 32
    assert anonymize_client_id(None, salt="x") is None


def test_time_buckets_utc():
    ts = datetime(2026, 8, 20, 16, 30, tzinfo=timezone.utc)
    buckets = time_buckets(ts)
    assert buckets["test_date"] == "2026-08-20"
    assert buckets["day_of_week"] == 3  # Thursday
    assert buckets["hour_utc"] == 16


def test_aggregation_dimensions_documented():
    assert set(AGGREGATION_DIMENSIONS) == {
        "isp",
        "package",
        "region",
        "date",
        "day_of_week",
        "hour",
        "server",
        "metric",
    }


def test_aggregate_by_isp(db_session):
    db_session.add_all(
        [
            SpeedTestResult(
                timestamp=datetime(2026, 8, 20, 10, tzinfo=timezone.utc),
                download_mbps=100,
                upload_mbps=20,
                ping_ms=12,
                isp_name="Emtel Ltd",
                server_label="Emtel · Ebene",
                server_id="emtel-ebene-18276",
                internet_package="Fibre 100",
                detected_region="Ebene",
                test_date="2026-08-20",
                day_of_week=3,
                hour_utc=10,
                overall_score=90,
                ipv4_ok=True,
                ipv6_ok=False,
            ),
            SpeedTestResult(
                timestamp=datetime(2026, 8, 20, 11, tzinfo=timezone.utc),
                download_mbps=80,
                upload_mbps=15,
                ping_ms=18,
                isp_name="Emtel",
                server_label="Emtel · Arsenal",
                server_id="emtel-arsenal-7763",
                internet_package="Fibre 100",
                detected_region="Arsenal",
                test_date="2026-08-20",
                day_of_week=3,
                hour_utc=11,
                overall_score=80,
                ipv4_ok=True,
                ipv6_ok=False,
            ),
            SpeedTestResult(
                timestamp=datetime(2026, 8, 19, 22, tzinfo=timezone.utc),
                download_mbps=50,
                upload_mbps=10,
                ping_ms=30,
                isp_name="Orange Mauritius",
                server_label="MT · Floreal",
                server_id="mt-floreal-3827",
                internet_package="ADSL 20",
                detected_region="Floreal",
                test_date="2026-08-19",
                day_of_week=2,
                hour_utc=22,
                overall_score=70,
                ipv4_ok=True,
                ipv6_ok=False,
            ),
        ]
    )
    db_session.commit()

    by_isp = aggregate_measurements(db_session, by="isp", days=30)
    assert by_isp["total_rows"] == 3
    keys = {b["key"] for b in by_isp["buckets"]}
    assert "Emtel" in keys
    assert "Mauritius Telecom / Orange" in keys

    by_pkg = aggregate_measurements(db_session, by="package", days=30)
    assert {b["key"] for b in by_pkg["buckets"]} == {"Fibre 100", "ADSL 20"}

    by_hour = aggregate_measurements(db_session, by="hour", days=30)
    assert any(b["key"] == "10:00" for b in by_hour["buckets"])

    by_metric = aggregate_measurements(
        db_session, by="metric", days=30, metric="download_mbps"
    )
    assert abs(by_metric["buckets"][0]["avg"] - 76.67) < 0.02
