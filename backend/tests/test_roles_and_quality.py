"""Phase 15–16: roles + data quality."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.db.init_db import ensure_speed_test_columns, init_db
from app.main import create_app
from app.services.data_quality_service import assess_measurement


def _fresh_client() -> TestClient:
    get_settings.cache_clear()
    init_db(seed=False)
    ensure_speed_test_columns()
    return TestClient(create_app())


def test_assess_marks_incomplete_and_outlier():
    incomplete = assess_measurement(
        download_mbps=None,
        upload_mbps=10,
        ping_ms=20,
        jitter_ms=1,
        packet_loss_pct=0,
        isp_name="Emtel",
        detected_region="Port Louis",
        server_label="x",
        internet_package="Fibre 100",
        errors=None,
        http_ok=True,
        dns_ok=True,
    )
    assert incomplete["quality_status"] == "incomplete"
    assert incomplete["analytics_eligible"] is False

    outlier = assess_measurement(
        download_mbps=9000,
        upload_mbps=10,
        ping_ms=20,
        jitter_ms=1,
        packet_loss_pct=0,
        isp_name="Emtel",
        detected_region="Port Louis",
        server_label="x",
        internet_package="Fibre 100",
        errors=None,
        http_ok=True,
        dns_ok=True,
    )
    assert outlier["quality_status"] == "outlier"
    assert "outlier_download" in outlier["quality_flags"]


def test_admin_auth_status_and_isp_scope(monkeypatch):
    monkeypatch.setenv("QOS_AUTH_REQUIRED", "true")
    monkeypatch.setenv("QOS_ADMIN_TOKEN", "admin-demo-token")
    monkeypatch.setenv("QOS_ISP_TOKENS", "Emtel:emtel-demo-token,Rogers:rogers-demo-token")
    client = _fresh_client()

    denied = client.get("/admin/dashboard")
    assert denied.status_code == 401

    admin = client.get(
        "/admin/auth/status",
        headers={
            "X-SmartQoS-Role": "administrator",
            "X-SmartQoS-Token": "admin-demo-token",
        },
    )
    assert admin.status_code == 200
    assert admin.json()["role"] == "administrator"

    isp = client.get(
        "/admin/dashboard",
        headers={
            "X-SmartQoS-Role": "isp_administrator",
            "X-SmartQoS-Token": "emtel-demo-token",
        },
    )
    assert isp.status_code == 200

    cross = client.get(
        "/admin/dashboard?isp=Rogers",
        headers={
            "X-SmartQoS-Role": "isp_administrator",
            "X-SmartQoS-Token": "emtel-demo-token",
        },
    )
    assert cross.status_code == 403

    consumer = client.get(
        "/admin/dashboard",
        headers={
            "X-SmartQoS-Role": "consumer",
            "X-SmartQoS-Token": "x",
        },
    )
    assert consumer.status_code == 403

    monkeypatch.delenv("QOS_AUTH_REQUIRED", raising=False)
    get_settings.cache_clear()


def test_data_quality_endpoint_demo_mode(monkeypatch):
    monkeypatch.setenv("QOS_AUTH_REQUIRED", "false")
    client = _fresh_client()
    res = client.get("/admin/data-quality?days=90")
    assert res.status_code == 200
    body = res.json()
    assert "counts" in body
    assert "analytics_example" in body
    assert "n=" in body["analytics_example"]
    get_settings.cache_clear()
