"""Core QoS measurement generator for simulated broadband nodes."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Iterator

from .engine import ScenarioEngine
from .models import NetworkEvent, NetworkNode, QoSMeasurement, ScenarioType
from .nodes import get_default_nodes
from .scenarios import get_profile, technology_noise_scale


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _round(value: float, digits: int = 2) -> float:
    return round(value, digits)


class QoSSimulator:
    """Generate ISP-like QoS samples for one or more broadband nodes.

    Purpose
    -------
    Produce realistic, labelled time-series data that the FastAPI backend,
    anomaly detector, and dashboard can consume without physical telecom
    equipment. Each sample includes a ``scenario_label`` ground truth so ML
    evaluation can compare predictions against known degradations.
    """

    def __init__(
        self,
        nodes: list[NetworkNode] | None = None,
        *,
        seed: int | None = 42,
        force_scenario: ScenarioType | None = None,
        anomaly_rate: float = 0.08,
        interval_seconds: int = 5,
    ) -> None:
        self.nodes = nodes or get_default_nodes()
        self.interval_seconds = interval_seconds
        self.engine = ScenarioEngine(
            self.nodes,
            seed=seed,
            force_scenario=force_scenario,
            anomaly_rate=anomaly_rate,
        )
        # Dedicated RNG for metric noise so scenario selection stays independent.
        import random

        self.rng = random.Random(None if seed is None else seed + 7)

    def generate_measurement(
        self,
        node: NetworkNode,
        timestamp: datetime | None = None,
    ) -> QoSMeasurement:
        """Generate a single QoS measurement for one node."""
        now = timestamp or datetime.now(timezone.utc)
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)

        scenario = self.engine.current_scenario(node.node_code, now)
        profile = get_profile(scenario)
        noise = technology_noise_scale(node)

        utilisation = self.rng.uniform(profile.utilisation_min, profile.utilisation_max)
        utilisation = _clamp(utilisation + self.rng.gauss(0, 1.5 * noise), 0.0, 100.0)

        latency = node.baseline_latency_ms * profile.latency_factor
        latency += self.rng.gauss(0, 1.8 * noise)
        latency = _clamp(latency, 1.0, 2000.0)

        jitter = node.baseline_jitter_ms * profile.jitter_factor
        jitter += abs(self.rng.gauss(0, 0.6 * noise))
        jitter = _clamp(jitter, 0.1, 500.0)

        packet_loss = node.baseline_packet_loss_pct + profile.packet_loss_add
        packet_loss += abs(self.rng.gauss(0, 0.08 * noise))
        packet_loss = _clamp(packet_loss, 0.0, 100.0)

        # Achieved throughput depends on service tier, utilisation demand,
        # and scenario impairment (congestion / caps / outages).
        demand_fraction = utilisation / 100.0
        raw_throughput = node.service_tier_mbps * demand_fraction * profile.throughput_factor
        # Mild capacity headroom: FTTH nodes can sometimes approach tier closely.
        raw_throughput += self.rng.gauss(0, 1.2 * noise)
        throughput = _clamp(raw_throughput, 0.0, node.service_tier_mbps)

        signal = node.baseline_signal_quality + profile.signal_delta
        signal += self.rng.gauss(0, 1.2 * noise)
        signal = _clamp(signal, 0.0, 100.0)

        availability = self.rng.uniform(profile.availability_min, profile.availability_max)
        availability = _clamp(availability, 0.0, 100.0)

        # Outages suppress meaningful throughput and inflate loss.
        if scenario == ScenarioType.OUTAGE and availability < 20:
            throughput = _clamp(throughput * 0.2, 0.0, node.service_tier_mbps)
            packet_loss = _clamp(packet_loss + 5.0, 0.0, 100.0)

        return QoSMeasurement(
            node_code=node.node_code,
            timestamp=now,
            latency_ms=_round(latency),
            jitter_ms=_round(jitter),
            packet_loss_pct=_round(packet_loss, 3),
            throughput_mbps=_round(throughput),
            bandwidth_utilisation_pct=_round(utilisation),
            signal_quality=_round(signal),
            availability_pct=_round(availability),
            scenario_label=scenario.value,
        )

    def generate_tick(self, timestamp: datetime | None = None) -> list[QoSMeasurement]:
        """Generate one measurement for every configured node."""
        now = timestamp or datetime.now(timezone.utc)
        return [self.generate_measurement(node, now) for node in self.nodes]

    def generate_batch(
        self,
        samples_per_node: int,
        *,
        start_time: datetime | None = None,
        interval_seconds: int | None = None,
    ) -> list[QoSMeasurement]:
        """Generate a historical batch of measurements for offline ML training."""
        interval = interval_seconds or self.interval_seconds
        start = start_time or datetime.now(timezone.utc) - timedelta(
            seconds=interval * samples_per_node
        )
        if start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)

        measurements: list[QoSMeasurement] = []
        for index in range(samples_per_node):
            ts = start + timedelta(seconds=interval * index)
            measurements.extend(self.generate_tick(ts))

        self.engine.close_all(start + timedelta(seconds=interval * samples_per_node))
        return measurements

    def stream(
        self,
        *,
        max_ticks: int | None = None,
        start_time: datetime | None = None,
    ) -> Iterator[list[QoSMeasurement]]:
        """Yield successive ticks. Useful for live simulation loops."""
        tick = 0
        current = start_time or datetime.now(timezone.utc)
        if current.tzinfo is None:
            current = current.replace(tzinfo=timezone.utc)

        while max_ticks is None or tick < max_ticks:
            yield self.generate_tick(current)
            tick += 1
            current += timedelta(seconds=self.interval_seconds)

    @property
    def events(self) -> list[NetworkEvent]:
        """Ground-truth incident windows created during the run."""
        return self.engine.events
