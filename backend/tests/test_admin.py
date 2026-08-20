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
    from app.services import admin_service, benchmark_service

    profiles = tmp_path / "qos_benchmark_profiles.json"
    legacy = tmp_path / "qos_benchmarks.json"
    monkeypatch.setattr(benchmark_service, "PROFILES_PATH", profiles)
    monkeypatch.setattr(benchmark_service, "LEGACY_PATH", legacy)
    monkeypatch.setattr(admin_service, "BENCHMARK_PATH", legacy)
    # Seed a catalog so save_profile updates the active profile.
    seed = {
        "active_profile_id": "general-broadband",
        "disclaimer": "test",
        "profiles": [
            {
                "id": "general-broadband",
                "name": "General Broadband",
                "description": "test",
                "metrics": {
                    "download_mbps": {
                        "threshold": 100,
                        "unit": "Mbps",
                        "source": "t",
                        "rationale": "t",
                        "description": "t",
                    },
                    "upload_mbps": {
                        "threshold": 20,
                        "unit": "Mbps",
                        "source": "t",
                        "rationale": "t",
                        "description": "t",
                    },
                    "ping_ms": {
                        "threshold": 20,
                        "unit": "ms",
                        "source": "t",
                        "rationale": "t",
                        "description": "t",
                    },
                    "jitter_ms": {
                        "threshold": 5,
                        "unit": "ms",
                        "source": "t",
                        "rationale": "t",
                        "description": "t",
                    },
                    "packet_loss_pct": {
                        "threshold": 0.5,
                        "unit": "%",
                        "source": "t",
                        "rationale": "t",
                        "description": "t",
                    },
                    "overall_score": {
                        "threshold": 85,
                        "unit": "/100",
                        "source": "t",
                        "rationale": "t",
                        "description": "t",
                    },
                },
            }
        ],
    }
    profiles.write_text(__import__("json").dumps(seed), encoding="utf-8")
    saved = save_profile(BenchmarkProfile(download_mbps=150, ping_ms=15))
    assert saved.download_mbps == 150
    loaded = default_profile()
    assert loaded.download_mbps == 150
    assert loaded.ping_ms == 15
