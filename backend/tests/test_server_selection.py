"""Tests for automatic server selection scoring (Phase 1)."""

from __future__ import annotations

from measurement.server_selection import isp_affinity, parse_host_port, score_candidate


def test_parse_host_port():
    assert parse_host_port("speedtest.emtel.com:8080") == ("speedtest.emtel.com", 8080)
    assert parse_host_port("202.123.3.108:8080") == ("202.123.3.108", 8080)
    assert parse_host_port("example.com")[0] == "example.com"


def test_isp_affinity_is_contextual():
    assert isp_affinity("Emtel Ltd", "Emtel", "Emtel Ltd") is True
    assert isp_affinity("Orange", "Mauritius Telecom / Orange", "Orange") is True
    assert isp_affinity("Emtel Ltd", "Rogers", "Rogers Capital") is False
    assert isp_affinity(None, "Emtel") is False


def test_lower_latency_beats_same_isp_affinity():
    """Same-ISP bonus must not override a clearly better path."""
    other = score_candidate(
        latency_ms=12,
        packet_loss_pct=0,
        distance_km=8,
        online=True,
        affinity=False,
    )
    same_isp_slow = score_candidate(
        latency_ms=70,
        packet_loss_pct=0,
        distance_km=8,
        online=True,
        affinity=True,
    )
    assert other > same_isp_slow


def test_offline_or_unreachable_scores_zero():
    assert score_candidate(
        latency_ms=10, packet_loss_pct=0, distance_km=5, online=False, affinity=True
    ) == 0
    assert score_candidate(
        latency_ms=None, packet_loss_pct=100, distance_km=5, online=True, affinity=True
    ) == 0
