"""Tests for documented measurement parameters."""

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
    "download_pass_bytes",
    "download_passes",
    "upload_total_bytes",
    "download_chunk_bytes",
    "upload_chunk_bytes",
)


def test_config_profiles_include_required_keys():
    cfg = load_measurement_config()
    assert cfg["version"]
    assert cfg["throughput_mode"] == "bytes"
    for name in ("full", "quick"):
        block = cfg[name]
        for key in REQUIRED_KEYS:
            assert key in block, key
        assert block["download_passes"] >= 1
        assert block["download_pass_bytes"] > 0
        assert block["upload_total_bytes"] > 0


def test_restored_pre_methodology_byte_budgets():
    full = profile(False)
    quick = profile(True)
    assert full["download_pass_bytes"] == 25_000_000
    assert full["download_passes"] == 2
    assert full["upload_total_bytes"] == 20_000_000
    assert full["latency_packet_count"] == 12
    assert quick["download_pass_bytes"] == 3_000_000
    assert quick["download_passes"] == 1
    assert quick["upload_total_bytes"] == 2_000_000
    assert quick["latency_packet_count"] == 4


def test_public_methodology_is_safe_snapshot():
    snap = public_methodology()
    assert snap["version"] == load_measurement_config()["version"]
    assert "throughput_mbps" in snap["formulas"]
    assert snap["full"]["download_pass_bytes"] == profile(False)["download_pass_bytes"]
    assert snap["quick"]["download_pass_bytes"] == profile(True)["download_pass_bytes"]


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
