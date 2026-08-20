"""Phase 7 multi-profile benchmark catalog."""

from __future__ import annotations

import json

import pytest

from app.schemas.admin import BenchmarkMetricThreshold, BenchmarkProfileDetail
from app.services import benchmark_service


@pytest.fixture
def catalog_dir(tmp_path, monkeypatch):
    profiles = tmp_path / "qos_benchmark_profiles.json"
    legacy = tmp_path / "qos_benchmarks.json"
    monkeypatch.setattr(benchmark_service, "PROFILES_PATH", profiles)
    monkeypatch.setattr(benchmark_service, "LEGACY_PATH", legacy)
    return profiles, legacy


def _sample_catalog():
    metric = {
        "threshold": 100.0,
        "unit": "Mbps",
        "source": "test",
        "rationale": "unit test",
        "description": "download",
    }
    return {
        "active_profile_id": "gaming",
        "disclaimer": "Not a universal standard.",
        "profiles": [
            {
                "id": "general-broadband",
                "name": "General Broadband",
                "description": "General",
                "metrics": {
                    "download_mbps": {**metric, "threshold": 100},
                    "upload_mbps": {**metric, "threshold": 20, "unit": "Mbps"},
                    "ping_ms": {**metric, "threshold": 20, "unit": "ms"},
                    "jitter_ms": {**metric, "threshold": 5, "unit": "ms"},
                    "packet_loss_pct": {**metric, "threshold": 0.5, "unit": "%"},
                    "overall_score": {**metric, "threshold": 85, "unit": "/100"},
                },
            },
            {
                "id": "gaming",
                "name": "Gaming",
                "description": "Latency first",
                "metrics": {
                    "download_mbps": {**metric, "threshold": 25},
                    "upload_mbps": {**metric, "threshold": 5, "unit": "Mbps"},
                    "ping_ms": {**metric, "threshold": 30, "unit": "ms"},
                    "jitter_ms": {**metric, "threshold": 10, "unit": "ms"},
                    "packet_loss_pct": {**metric, "threshold": 1.0, "unit": "%"},
                    "overall_score": {**metric, "threshold": 80, "unit": "/100"},
                },
            },
        ],
    }


def test_load_and_active_flat(catalog_dir):
    profiles, legacy = catalog_dir
    profiles.write_text(json.dumps(_sample_catalog()), encoding="utf-8")
    flat = benchmark_service.active_flat_profile()
    assert flat.name == "Gaming"
    assert flat.download_mbps == 25
    assert flat.ping_ms == 30


def test_set_active_and_legacy_sync(catalog_dir):
    profiles, legacy = catalog_dir
    profiles.write_text(json.dumps(_sample_catalog()), encoding="utf-8")
    listed = benchmark_service.set_active_profile("general-broadband")
    assert listed.active_profile_id == "general-broadband"
    assert listed.active is not None
    assert listed.active.metrics["download_mbps"].threshold == 100
    synced = json.loads(legacy.read_text(encoding="utf-8"))
    assert synced["download_mbps"] == 100
    assert synced["name"] == "General Broadband"


def test_update_profile_preserves_metadata(catalog_dir):
    profiles, _legacy = catalog_dir
    profiles.write_text(json.dumps(_sample_catalog()), encoding="utf-8")
    detail = BenchmarkProfileDetail(
        id="gaming",
        name="Gaming (edited)",
        description="Updated",
        metrics={
            "download_mbps": BenchmarkMetricThreshold(
                threshold=40,
                unit="Mbps",
                source="admin",
                rationale="raised for test",
                description="download",
            ),
            "ping_ms": BenchmarkMetricThreshold(
                threshold=25,
                unit="ms",
                source="admin",
                rationale="tighter latency",
                description="ping",
            ),
        },
    )
    listed = benchmark_service.update_profile("gaming", detail)
    gaming = next(p for p in listed.profiles if p.id == "gaming")
    assert gaming.name == "Gaming (edited)"
    assert gaming.metrics["download_mbps"].threshold == 40
    assert gaming.metrics["download_mbps"].source == "admin"
    assert gaming.metrics["ping_ms"].rationale == "tighter latency"


def test_migrate_legacy_flat(catalog_dir):
    profiles, legacy = catalog_dir
    legacy.write_text(
        json.dumps(
            {
                "name": "Ideal Broadband Profile",
                "description": "Legacy",
                "download_mbps": 120,
                "upload_mbps": 25,
                "ping_ms": 18,
                "jitter_ms": 4,
                "packet_loss_pct": 0.4,
                "overall_score": 90,
            }
        ),
        encoding="utf-8",
    )
    catalog = benchmark_service.load_catalog()
    assert catalog["active_profile_id"] == "legacy-ideal"
    assert profiles.exists()
    flat = benchmark_service.active_flat_profile()
    assert flat.download_mbps == 120
    assert flat.overall_score == 90


def test_unknown_profile_raises(catalog_dir):
    profiles, _legacy = catalog_dir
    profiles.write_text(json.dumps(_sample_catalog()), encoding="utf-8")
    with pytest.raises(ValueError, match="Unknown profile"):
        benchmark_service.set_active_profile("missing")
