"""Integration tests for the Phase 3 FastAPI backend.

Uses an isolated in-memory SQLite database so tests never touch the dev DB.
"""

from __future__ import annotations

import importlib

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


@pytest.fixture()
def client(monkeypatch):
    # Point the app at an in-memory database before importing app modules.
    monkeypatch.setenv("QOS_DATABASE_URL", "sqlite://")
    monkeypatch.setenv("QOS_SEED_NODES", "true")

    # Reload config + session so the in-memory URL takes effect.
    from app.core import config as config_module

    config_module.get_settings.cache_clear()

    from app.db import session as session_module

    importlib.reload(session_module)

    # Rebuild an in-memory engine that persists across connections.
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    session_module.engine = engine
    session_module.SessionLocal = sessionmaker(
        bind=engine, autoflush=False, autocommit=False, future=True
    )

    # Reload modules that captured the old engine/session at import time.
    from app.db import init_db as init_db_module

    importlib.reload(init_db_module)

    from app.api.routes import health as health_module
    from app.api.routes import measurements as measurements_module
    from app.api.routes import metrics as metrics_module
    from app.api.routes import anomalies as anomalies_module
    from app.api.routes import analyze as analyze_module

    for module in (
        health_module,
        measurements_module,
        metrics_module,
        anomalies_module,
        analyze_module,
    ):
        importlib.reload(module)

    from app import main as main_module

    importlib.reload(main_module)

    with TestClient(main_module.app) as test_client:
        yield test_client


def _sample_payload(node_code: str = "BNG-DXB-001", **overrides):
    payload = {
        "node_code": node_code,
        "timestamp": "2026-07-16T19:00:00Z",
        "latency_ms": 32.5,
        "jitter_ms": 4.2,
        "packet_loss_pct": 0.1,
        "throughput_mbps": 84.6,
        "bandwidth_utilisation_pct": 61.3,
        "signal_quality": 91.0,
        "availability_pct": 100.0,
        "scenario_label": "normal",
    }
    payload.update(overrides)
    return payload


def test_health_ok(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["database"] == "connected"


def test_default_nodes_seeded(client):
    resp = client.get("/api/nodes")
    assert resp.status_code == 200
    codes = {n["node_code"] for n in resp.json()}
    assert {"BNG-DXB-001", "BNG-DXB-002", "DSL-SHJ-001", "FWA-AUH-001"} <= codes


def test_post_measurement_and_latest(client):
    resp = client.post("/api/measurements", json=_sample_payload())
    assert resp.status_code == 201
    assert resp.json()["stored"] is True

    latest = client.get("/api/metrics/latest")
    assert latest.status_code == 200
    rows = latest.json()
    match = [r for r in rows if r["node_code"] == "BNG-DXB-001"]
    assert match and match[0]["health_status"] == "healthy"


def test_post_measurement_unknown_node(client):
    resp = client.post("/api/measurements", json=_sample_payload(node_code="NOPE"))
    assert resp.status_code == 404


def test_invalid_measurement_rejected(client):
    resp = client.post("/api/measurements", json=_sample_payload(packet_loss_pct=250))
    assert resp.status_code == 422


def test_history_endpoint(client):
    for i in range(3):
        client.post(
            "/api/measurements",
            json=_sample_payload(timestamp=f"2026-07-16T19:0{i}:00Z", latency_ms=30 + i),
        )
    resp = client.get("/api/metrics/history", params={"node_code": "BNG-DXB-001", "metric": "latency_ms"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["metric"] == "latency_ms"
    assert len(body["points"]) == 3


def test_history_invalid_metric(client):
    resp = client.get("/api/metrics/history", params={"node_code": "BNG-DXB-001", "metric": "bogus"})
    assert resp.status_code == 400


def test_critical_health_classification(client):
    client.post(
        "/api/measurements",
        json=_sample_payload(
            node_code="DSL-SHJ-001",
            latency_ms=180.0,
            packet_loss_pct=5.0,
            availability_pct=90.0,
        ),
    )
    rows = client.get("/api/metrics/latest").json()
    match = [r for r in rows if r["node_code"] == "DSL-SHJ-001"]
    assert match and match[0]["health_status"] == "critical"


def test_anomalies_empty(client):
    resp = client.get("/api/anomalies")
    assert resp.status_code == 200
    assert resp.json() == []


def test_run_detection_not_implemented(client):
    resp = client.post("/api/anomalies/run")
    assert resp.status_code == 501


def test_analyze_not_implemented(client):
    resp = client.post("/api/analyze")
    assert resp.status_code == 501
