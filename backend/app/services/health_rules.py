"""Rule-based QoS health classification.

Purpose
-------
Provide a fast, explainable health label for each node before ML anomaly
detection (Phase 4). These thresholds also serve as the baseline comparison
in the dissertation evaluation.
"""

from __future__ import annotations

# Threshold tiers roughly aligned with broadband QoS expectations.
LATENCY_WARN_MS = 60.0
LATENCY_CRIT_MS = 120.0
JITTER_WARN_MS = 15.0
JITTER_CRIT_MS = 30.0
PACKET_LOSS_WARN_PCT = 1.0
PACKET_LOSS_CRIT_PCT = 3.0
UTILISATION_WARN_PCT = 80.0
UTILISATION_CRIT_PCT = 92.0
AVAILABILITY_WARN_PCT = 99.0
AVAILABILITY_CRIT_PCT = 95.0

HEALTHY = "healthy"
DEGRADED = "degraded"
CRITICAL = "critical"


def classify_health(
    *,
    latency_ms: float,
    jitter_ms: float,
    packet_loss_pct: float,
    bandwidth_utilisation_pct: float,
    availability_pct: float,
) -> str:
    """Return an overall health label from QoS metrics.

    The worst individual metric determines the status.
    """
    critical_hits = (
        latency_ms >= LATENCY_CRIT_MS
        or jitter_ms >= JITTER_CRIT_MS
        or packet_loss_pct >= PACKET_LOSS_CRIT_PCT
        or bandwidth_utilisation_pct >= UTILISATION_CRIT_PCT
        or availability_pct <= AVAILABILITY_CRIT_PCT
    )
    if critical_hits:
        return CRITICAL

    degraded_hits = (
        latency_ms >= LATENCY_WARN_MS
        or jitter_ms >= JITTER_WARN_MS
        or packet_loss_pct >= PACKET_LOSS_WARN_PCT
        or bandwidth_utilisation_pct >= UTILISATION_WARN_PCT
        or availability_pct <= AVAILABILITY_WARN_PCT
    )
    if degraded_hits:
        return DEGRADED

    return HEALTHY
