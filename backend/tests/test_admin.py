"""Unit tests for Administrator Portal grouping and benchmarks."""

from __future__ import annotations

from app.schemas.admin import BenchmarkProfile
from app.services.admin_service import normalize_isp, region_from_label, save_profile, default_profile


def test_normalize_isp_aliases():
    assert normalize_isp("Emtel Ltd") == "Emtel"
    assert normalize_isp("Orange") == "Mauritius Telecom / Orange"
    assert normalize_isp("Mauritius Telecom Ltd") == "Mauritius Telecom / Orange"
    assert normalize_isp("Rogers Capital Technology Services") == "Rogers"
    assert normalize_isp("Bharat Telecom Ltd") == "Bharat Telecom"
    assert normalize_isp(None) == "Unknown"


def test_region_from_server_label():
    assert region_from_label("Emtel Ltd · Ebene") == "Ebene"
    assert region_from_label("Mauritius Telecom · Port Louis") == "Port Louis"
    assert region_from_label("Rogers · Rose-Hill") == "Rose Hill"
    assert region_from_label(None) == "Unknown"


def test_benchmark_profile_roundtrip(tmp_path, monkeypatch):
    from app.services import admin_service

    path = tmp_path / "qos_benchmarks.json"
    monkeypatch.setattr(admin_service, "BENCHMARK_PATH", path)
    saved = save_profile(BenchmarkProfile(download_mbps=150, ping_ms=15))
    assert saved.download_mbps == 150
    loaded = default_profile()
    assert loaded.download_mbps == 150
    assert loaded.ping_ms == 15
