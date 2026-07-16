"""Default virtual broadband nodes used by the simulator."""

from __future__ import annotations

from .models import NetworkNode

DEFAULT_NODES: list[NetworkNode] = [
    NetworkNode(
        node_code="BNG-DXB-001",
        region="Dubai North",
        access_technology="FTTH",
        service_tier_mbps=100.0,
        subscriber_count=250,
        baseline_latency_ms=22.0,
        max_bandwidth_mbps=1000.0,
        baseline_jitter_ms=2.0,
        baseline_packet_loss_pct=0.03,
        baseline_signal_quality=95.0,
    ),
    NetworkNode(
        node_code="BNG-DXB-002",
        region="Dubai South",
        access_technology="FTTH",
        service_tier_mbps=250.0,
        subscriber_count=180,
        baseline_latency_ms=18.0,
        max_bandwidth_mbps=1500.0,
        baseline_jitter_ms=1.8,
        baseline_packet_loss_pct=0.02,
        baseline_signal_quality=96.0,
    ),
    NetworkNode(
        node_code="DSL-SHJ-001",
        region="Sharjah Central",
        access_technology="DSL",
        service_tier_mbps=50.0,
        subscriber_count=320,
        baseline_latency_ms=35.0,
        max_bandwidth_mbps=500.0,
        baseline_jitter_ms=4.0,
        baseline_packet_loss_pct=0.08,
        baseline_signal_quality=88.0,
    ),
    NetworkNode(
        node_code="FWA-AUH-001",
        region="Abu Dhabi Suburban",
        access_technology="Fixed Wireless",
        service_tier_mbps=100.0,
        subscriber_count=140,
        baseline_latency_ms=28.0,
        max_bandwidth_mbps=700.0,
        baseline_jitter_ms=5.5,
        baseline_packet_loss_pct=0.12,
        baseline_signal_quality=84.0,
    ),
]


def get_default_nodes() -> list[NetworkNode]:
    """Return a copy of the default node catalogue."""
    return list(DEFAULT_NODES)


def get_node_by_code(node_code: str) -> NetworkNode | None:
    """Look up a default node by code."""
    for node in DEFAULT_NODES:
        if node.node_code == node_code:
            return node
    return None
