"""Scenario profiles that reshape baseline QoS into degraded conditions."""

from __future__ import annotations

from dataclasses import dataclass

from .models import NetworkNode, ScenarioType, Severity


@dataclass(frozen=True)
class ScenarioProfile:
    """Multiplicative / additive modifiers applied to baseline QoS."""

    scenario: ScenarioType
    severity: Severity
    description: str
    utilisation_min: float
    utilisation_max: float
    latency_factor: float
    jitter_factor: float
    packet_loss_add: float
    throughput_factor: float
    signal_delta: float
    availability_min: float
    availability_max: float


# Profiles are calibrated to look like ISP NOC telemetry, not random noise.
SCENARIO_PROFILES: dict[ScenarioType, ScenarioProfile] = {
    ScenarioType.NORMAL: ScenarioProfile(
        scenario=ScenarioType.NORMAL,
        severity=Severity.LOW,
        description="Normal broadband service within expected operating range",
        utilisation_min=25.0,
        utilisation_max=55.0,
        latency_factor=1.0,
        jitter_factor=1.0,
        packet_loss_add=0.0,
        throughput_factor=0.85,
        signal_delta=0.0,
        availability_min=99.5,
        availability_max=100.0,
    ),
    ScenarioType.CONGESTION: ScenarioProfile(
        scenario=ScenarioType.CONGESTION,
        severity=Severity.HIGH,
        description="Peak-hour access network congestion with elevated delay and loss",
        utilisation_min=85.0,
        utilisation_max=98.0,
        latency_factor=3.8,
        jitter_factor=4.5,
        packet_loss_add=1.8,
        throughput_factor=0.45,
        signal_delta=-4.0,
        availability_min=98.0,
        availability_max=100.0,
    ),
    ScenarioType.HIGH_LATENCY: ScenarioProfile(
        scenario=ScenarioType.HIGH_LATENCY,
        severity=Severity.MEDIUM,
        description="High latency event consistent with backhaul or routing delay",
        utilisation_min=35.0,
        utilisation_max=65.0,
        latency_factor=5.5,
        jitter_factor=2.2,
        packet_loss_add=0.15,
        throughput_factor=0.75,
        signal_delta=-1.5,
        availability_min=99.0,
        availability_max=100.0,
    ),
    ScenarioType.PACKET_LOSS: ScenarioProfile(
        scenario=ScenarioType.PACKET_LOSS,
        severity=Severity.HIGH,
        description="Elevated packet loss suggesting noisy link or queue overflow",
        utilisation_min=50.0,
        utilisation_max=80.0,
        latency_factor=1.8,
        jitter_factor=5.0,
        packet_loss_add=4.5,
        throughput_factor=0.55,
        signal_delta=-8.0,
        availability_min=96.0,
        availability_max=99.5,
    ),
    ScenarioType.BANDWIDTH_LIMIT: ScenarioProfile(
        scenario=ScenarioType.BANDWIDTH_LIMIT,
        severity=Severity.MEDIUM,
        description="Throughput capped below service tier due to capacity or throttling",
        utilisation_min=70.0,
        utilisation_max=95.0,
        latency_factor=1.6,
        jitter_factor=1.8,
        packet_loss_add=0.4,
        throughput_factor=0.35,
        signal_delta=-2.0,
        availability_min=99.0,
        availability_max=100.0,
    ),
    ScenarioType.OUTAGE: ScenarioProfile(
        scenario=ScenarioType.OUTAGE,
        severity=Severity.CRITICAL,
        description="Service availability degradation or partial node outage",
        utilisation_min=5.0,
        utilisation_max=20.0,
        latency_factor=8.0,
        jitter_factor=6.0,
        packet_loss_add=12.0,
        throughput_factor=0.05,
        signal_delta=-35.0,
        availability_min=0.0,
        availability_max=40.0,
    ),
}


def get_profile(scenario: ScenarioType) -> ScenarioProfile:
    """Return the metric profile for a scenario type."""
    return SCENARIO_PROFILES[scenario]


def peak_hour_weight(hour: int) -> float:
    """Return a 0-1 weight that peaks in evening busy hours."""
    # Typical residential broadband busy hour: 19:00-23:00 local time.
    if 19 <= hour <= 22:
        return 1.0
    if hour in (18, 23):
        return 0.7
    if 12 <= hour <= 14:
        return 0.35
    return 0.1


def technology_noise_scale(node: NetworkNode) -> float:
    """DSL and fixed wireless are noisier than FTTH."""
    tech = node.access_technology.lower()
    if "dsl" in tech:
        return 1.35
    if "wireless" in tech or "fwa" in tech:
        return 1.5
    if "cable" in tech:
        return 1.15
    return 1.0
