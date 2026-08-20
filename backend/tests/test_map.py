"""Tests for Mauritius QoS map aggregations (Phase 5)."""

from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace

from app.models.speedtest import SpeedTestResult
from app.services.map_service import (
    MAP_METRICS,
    _score_0_100,
    build_qos_map,
    colour_for_score,
    load_district_geojson,
    resolve_district,
)


def test_district_geojson_loads():
    geo = load_district_geojson()
    assert geo["type"] == "FeatureCollection"
    assert len(geo["features"]) >= 9


def test_resolve_district_aliases():
    row = SimpleNamespace(
        detected_region=None,
        detected_city=None,
        server_location="Ebene",
        server_label="Emtel · Ebene",
    )
    assert resolve_district(row) == "Plaines Wilhems"
    arsenal = SimpleNamespace(
        detected_region="Arsenal",
        detected_city=None,
        server_location=None,
        server_label="Emtel · Arsenal",
    )
    assert resolve_district(arsenal) == "Pamplemousses"


def test_colour_scale_excellent_to_critical():
    assert colour_for_score(95) == "#059669"
    assert colour_for_score(80) == "#10b981"
    assert colour_for_score(65) == "#f59e0b"
    assert colour_for_score(45) == "#f97316"
    assert colour_for_score(10) == "#e11d48"
    assert _score_0_100(15, "latency") == 100.0
    assert _score_0_100(200, "latency") == 20.0


def test_build_qos_map_features(db_session):
    db_session.add(
        SpeedTestResult(
            timestamp=datetime(2026, 8, 20, 19, tzinfo=timezone.utc),
            download_mbps=120,
            upload_mbps=30,
            ping_ms=14,
            jitter_ms=3,
            packet_loss_pct=0.1,
            overall_score=92,
            isp_name="Emtel Ltd",
            internet_package="100 Mbps",
            download_fulfilment_pct=120,
            upload_fulfilment_pct=75,
            server_label="Emtel · Ebene",
            server_location="Ebene",
            detected_region="Ebene",
            day_of_week=3,
            hour_utc=19,
            ipv4_ok=True,
            ipv6_ok=False,
        )
    )
    db_session.commit()

    assert set(MAP_METRICS) == {
        "download",
        "upload",
        "latency",
        "jitter",
        "packet_loss",
        "qos",
        "fulfilment",
    }
    payload = build_qos_map(db_session, metric="download", days=30, hour_from=18, hour_to=21)
    assert payload["type"] == "FeatureCollection"
    assert payload["legend"]["metric"] == "download"
    plains = next(
        f for f in payload["features"] if f["properties"]["name"] == "Plaines Wilhems"
    )
    assert plains["properties"]["tests"] == 1
    assert plains["properties"]["avg_download_mbps"] == 120
    assert plains["properties"]["colour"] is not None
    assert "Emtel" in payload["meta"]["available_isps"]
