"""Tests for documented measurement parameters (Phase 2)."""

from __future__ import annotations

from measurement.config import (
    load_measurement_config,
    packet_loss_pct,
    profile,
    public_methodology,
    rtt_stats,
    throughput_mbps,
)

REQUIRED_KEYS = (
    "latency_packet_size",
    "latency_packet_count",
    "latency_timeout",
    "download_duration",
    "upload_duration",
    "download_connections",
    "upload_connections",
    "warmup_duration",
    "measurement_interval",
)


def test_config_profiles_include_required_keys():
    cfg = load_measurement_config()
    assert cfg["version"]
    assert cfg["throughput_mode"] == "duration"
    for name in ("full", "quick"):
        block = cfg[name]
        for key in REQUIRED_KEYS:
            assert key in block, key
        assert block["download_connections"] >= 1
        assert block["upload_connections"] >= 1


def test_public_methodology_is_safe_snapshot():
    snap = public_methodology()
    assert snap["version"] == load_measurement_config()["version"]
    assert "throughput_mbps" in snap["formulas"]
    assert snap["full"]["download_duration"] == profile(False)["download_duration"]
    assert snap["quick"]["download_duration"] == profile(True)["download_duration"]


def test_throughput_mbps_duration_formula():
    # 1_000_000 bytes in 1 s → 8 Mbps
    assert abs(throughput_mbps(1_000_000, 1.0) - 8.0) < 1e-9
    assert throughput_mbps(0, 8.0) == 0.0


def test_packet_loss_pct():
    assert packet_loss_pct(10, 10) == 0.0
    assert packet_loss_pct(10, 7) == 30.0
    assert packet_loss_pct(0, 0) == 100.0


def test_rtt_stats_mean_min_max_median_jitter():
    samples = [10.0, 12.0, 14.0, 16.0]
    stats = rtt_stats(samples, sent=5, received=4)
    assert stats["ping_ms"] == 13.0
    assert stats["ping_min_ms"] == 10.0
    assert stats["ping_max_ms"] == 16.0
    assert stats["ping_median_ms"] == 13.0
    assert stats["packets_sent"] == 5
    assert stats["packets_received"] == 4
    assert stats["packets_lost"] == 1
    assert stats["packet_loss_pct"] == 20.0
    # population stdev of [10,12,14,16] = sqrt(5) ≈ 2.24
    assert abs(stats["jitter_ms"] - 2.24) < 0.01


def test_rtt_stats_empty_samples():
    stats = rtt_stats([], sent=4, received=0)
    assert stats["ping_ms"] is None
    assert stats["packet_loss_pct"] == 100.0
    assert stats["packets_lost"] == 4
