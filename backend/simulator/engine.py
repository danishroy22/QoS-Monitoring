"""Scenario scheduling engine for each virtual broadband node."""

from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone

from .models import ActiveScenario, NetworkEvent, NetworkNode, ScenarioType, Severity
from .scenarios import SCENARIO_PROFILES, peak_hour_weight


# Relative chance of starting a degradation while currently normal.
# Values are intentionally low so most traffic remains healthy.
DEGRADATION_WEIGHTS: dict[ScenarioType, float] = {
    ScenarioType.CONGESTION: 0.35,
    ScenarioType.HIGH_LATENCY: 0.20,
    ScenarioType.PACKET_LOSS: 0.18,
    ScenarioType.BANDWIDTH_LIMIT: 0.17,
    ScenarioType.OUTAGE: 0.10,
}

DURATION_MINUTES: dict[ScenarioType, tuple[int, int]] = {
    ScenarioType.CONGESTION: (15, 45),
    ScenarioType.HIGH_LATENCY: (10, 30),
    ScenarioType.PACKET_LOSS: (8, 25),
    ScenarioType.BANDWIDTH_LIMIT: (20, 60),
    ScenarioType.OUTAGE: (5, 20),
}


class ScenarioEngine:
    """Tracks active scenarios and emits ground-truth network events."""

    def __init__(
        self,
        nodes: list[NetworkNode],
        *,
        seed: int | None = None,
        force_scenario: ScenarioType | None = None,
        anomaly_rate: float = 0.08,
    ) -> None:
        self.nodes = {node.node_code: node for node in nodes}
        self.rng = random.Random(seed)
        self.force_scenario = force_scenario
        self.anomaly_rate = max(0.0, min(1.0, anomaly_rate))
        self._active: dict[str, ActiveScenario] = {}
        self.events: list[NetworkEvent] = []
        self._event_counter = 0

    def current_scenario(self, node_code: str, now: datetime) -> ScenarioType:
        """Return the scenario label active for a node at ``now``."""
        if self.force_scenario is not None:
            return self.force_scenario

        active = self._active.get(node_code)
        if active is not None and active.started_at <= now < active.ends_at:
            return active.scenario

        if active is not None and now >= active.ends_at:
            self._close_event(node_code, now)
            del self._active[node_code]

        if self._should_start_degradation(node_code, now):
            scenario = self._pick_degradation(now)
            self._start_scenario(node_code, scenario, now)
            return scenario

        return ScenarioType.NORMAL

    def active_event(self, node_code: str) -> ActiveScenario | None:
        return self._active.get(node_code)

    def _should_start_degradation(self, node_code: str, now: datetime) -> bool:
        if node_code in self._active:
            return False
        hour = now.astimezone(timezone.utc).hour if now.tzinfo else now.hour
        busy = peak_hour_weight(hour)
        # Base anomaly rate is boosted during busy hours.
        probability = self.anomaly_rate * (0.4 + 0.9 * busy)
        return self.rng.random() < probability

    def _pick_degradation(self, now: datetime) -> ScenarioType:
        hour = now.astimezone(timezone.utc).hour if now.tzinfo else now.hour
        busy = peak_hour_weight(hour)
        weights = dict(DEGRADATION_WEIGHTS)
        # Congestion is more likely in busy hours.
        weights[ScenarioType.CONGESTION] *= 1.0 + 1.5 * busy
        scenarios = list(weights.keys())
        chosen = self.rng.choices(scenarios, weights=[weights[s] for s in scenarios], k=1)[0]
        return chosen

    def _start_scenario(self, node_code: str, scenario: ScenarioType, now: datetime) -> None:
        low, high = DURATION_MINUTES[scenario]
        duration = timedelta(minutes=self.rng.randint(low, high))
        profile = SCENARIO_PROFILES[scenario]
        active = ActiveScenario(
            scenario=scenario,
            severity=profile.severity,
            started_at=now,
            ends_at=now + duration,
            description=profile.description,
        )
        self._active[node_code] = active
        self._event_counter += 1
        event = NetworkEvent(
            event_id=f"EVT-{self._event_counter:05d}",
            node_code=node_code,
            event_type=scenario.value,
            severity=profile.severity.value,
            start_time=now,
            end_time=None,
            description=profile.description,
        )
        self.events.append(event)

    def _close_event(self, node_code: str, now: datetime) -> None:
        for event in reversed(self.events):
            if event.node_code == node_code and event.end_time is None:
                event.end_time = now
                break

    def close_all(self, now: datetime) -> None:
        """Close any open events at the end of a simulation run."""
        for node_code in list(self._active.keys()):
            self._close_event(node_code, now)
        self._active.clear()
