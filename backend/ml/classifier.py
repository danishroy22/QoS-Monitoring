"""Map anomalous QoS samples to telecom-readable issue labels and severity."""

from __future__ import annotations

from typing import Any, Mapping


def classify_suspected_issue(row: Mapping[str, Any] | Any) -> str:
    """Infer the most likely degradation type from metric magnitudes."""

    def get(key: str, default: float = 0.0) -> float:
        if isinstance(row, Mapping):
            value = row.get(key, default)
        else:
            value = getattr(row, key, default)
        return float(default if value is None else value)

    availability = get("availability_pct", 100.0)
    loss = get("packet_loss_pct")
    latency = get("latency_ms")
    util = get("bandwidth_utilisation_pct")
    throughput = get("throughput_mbps")
    service_tier = get("service_tier_mbps", 0.0)
    jitter = get("jitter_ms")

    if availability < 50.0:
        return "outage"
    if loss >= 3.0 and jitter >= 10.0:
        return "packet_loss"
    if util >= 85.0 and latency >= 60.0:
        return "congestion"
    if latency >= 100.0 and loss < 1.5:
        return "high_latency"
    if service_tier > 0 and throughput < service_tier * 0.45 and util >= 70.0:
        return "bandwidth_limit"
    if util >= 80.0:
        return "congestion"
    if loss >= 1.5:
        return "packet_loss"
    if latency >= 60.0:
        return "high_latency"
    return "performance_degradation"


def classify_severity(
    *,
    anomaly_score: float,
    row: Mapping[str, Any] | Any,
) -> str:
    """Assign severity from Isolation Forest score and QoS magnitudes.

    Isolation Forest decision_function: more negative => more anomalous.
    """

    def get(key: str, default: float = 0.0) -> float:
        if isinstance(row, Mapping):
            value = row.get(key, default)
        else:
            value = getattr(row, key, default)
        return float(default if value is None else value)

    availability = get("availability_pct", 100.0)
    loss = get("packet_loss_pct")
    latency = get("latency_ms")

    if availability < 40.0 or loss >= 8.0 or anomaly_score <= -0.25:
        return "critical"
    if loss >= 3.0 or latency >= 120.0 or anomaly_score <= -0.12:
        return "high"
    if loss >= 1.0 or latency >= 60.0 or anomaly_score <= -0.05:
        return "medium"
    return "low"
