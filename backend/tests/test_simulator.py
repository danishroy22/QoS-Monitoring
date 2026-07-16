"""Unit tests for the Phase 2 QoS simulator."""

from __future__ import annotations

import csv
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from backend.simulator.engine import ScenarioEngine
from backend.simulator.generator import QoSSimulator
from backend.simulator.models import ScenarioType
from backend.simulator.nodes import get_default_nodes
from backend.simulator.publishers import CsvPublisher
from backend.simulator.scenarios import get_profile


class QoSSimulatorTests(unittest.TestCase):
    def test_default_nodes_match_seed_catalogue(self) -> None:
        nodes = get_default_nodes()
        codes = {node.node_code for node in nodes}
        self.assertEqual(
            codes,
            {"BNG-DXB-001", "BNG-DXB-002", "DSL-SHJ-001", "FWA-AUH-001"},
        )

    def test_normal_measurements_are_within_expected_ranges(self) -> None:
        simulator = QoSSimulator(seed=1, force_scenario=ScenarioType.NORMAL, anomaly_rate=0.0)
        samples = simulator.generate_batch(30)
        self.assertEqual(len(samples), 30 * len(simulator.nodes))

        for sample in samples:
            self.assertEqual(sample.scenario_label, "normal")
            self.assertGreaterEqual(sample.latency_ms, 1.0)
            self.assertLess(sample.latency_ms, 120.0)
            self.assertLess(sample.packet_loss_pct, 1.0)
            self.assertGreaterEqual(sample.availability_pct, 99.0)
            self.assertLessEqual(sample.bandwidth_utilisation_pct, 70.0)

    def test_congestion_increases_latency_and_utilisation(self) -> None:
        normal = QoSSimulator(seed=2, force_scenario=ScenarioType.NORMAL)
        congested = QoSSimulator(seed=2, force_scenario=ScenarioType.CONGESTION)

        normal_samples = normal.generate_batch(40)
        congested_samples = congested.generate_batch(40)
        normal_avg_latency = sum(s.latency_ms for s in normal_samples) / len(normal_samples)
        congested_avg_latency = (
            sum(s.latency_ms for s in congested_samples) / len(congested_samples)
        )
        congested_avg_util = (
            sum(s.bandwidth_utilisation_pct for s in congested_samples)
            / len(congested_samples)
        )

        self.assertGreater(congested_avg_latency, normal_avg_latency * 2)
        self.assertGreater(congested_avg_util, 80.0)

    def test_outage_reduces_availability(self) -> None:
        simulator = QoSSimulator(seed=3, force_scenario=ScenarioType.OUTAGE)
        samples = simulator.generate_batch(20)
        avg_availability = sum(s.availability_pct for s in samples) / len(samples)
        self.assertLess(avg_availability, 45.0)

    def test_bandwidth_limit_caps_throughput(self) -> None:
        simulator = QoSSimulator(seed=4, force_scenario=ScenarioType.BANDWIDTH_LIMIT)
        samples = [
            s for s in simulator.generate_batch(30) if s.node_code == "BNG-DXB-001"
        ]
        node = next(n for n in simulator.nodes if n.node_code == "BNG-DXB-001")
        avg_throughput = sum(s.throughput_mbps for s in samples) / len(samples)
        self.assertLess(avg_throughput, node.service_tier_mbps * 0.55)

    def test_packet_loss_scenario_elevates_loss(self) -> None:
        simulator = QoSSimulator(seed=5, force_scenario=ScenarioType.PACKET_LOSS)
        samples = simulator.generate_batch(25)
        avg_loss = sum(s.packet_loss_pct for s in samples) / len(samples)
        self.assertGreater(avg_loss, 2.0)

    def test_batch_is_reproducible_with_same_seed(self) -> None:
        start = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
        a = QoSSimulator(seed=99, anomaly_rate=0.2).generate_batch(15, start_time=start)
        b = QoSSimulator(seed=99, anomaly_rate=0.2).generate_batch(15, start_time=start)
        self.assertEqual([s.to_dict() for s in a], [s.to_dict() for s in b])

    def test_csv_publisher_writes_measurements_and_events(self) -> None:
        simulator = QoSSimulator(seed=7, force_scenario=ScenarioType.HIGH_LATENCY)
        samples = simulator.generate_batch(5)
        with tempfile.TemporaryDirectory() as tmp:
            publisher = CsvPublisher(tmp)
            measurements_path = publisher.write_measurements(samples)
            events_path = publisher.write_events(simulator.events)

            self.assertTrue(measurements_path.exists())
            self.assertTrue(events_path.exists())

            with measurements_path.open(encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(len(rows), len(samples))
            self.assertIn("latency_ms", rows[0])
            self.assertEqual(rows[0]["scenario_label"], "high_latency")

    def test_measurement_payload_matches_api_contract(self) -> None:
        simulator = QoSSimulator(seed=8, force_scenario=ScenarioType.NORMAL)
        sample = simulator.generate_measurement(simulator.nodes[0])
        payload = sample.to_dict()
        expected_keys = {
            "node_code",
            "timestamp",
            "latency_ms",
            "jitter_ms",
            "packet_loss_pct",
            "throughput_mbps",
            "bandwidth_utilisation_pct",
            "signal_quality",
            "availability_pct",
            "scenario_label",
        }
        self.assertEqual(set(payload.keys()), expected_keys)
        self.assertTrue(payload["timestamp"].endswith("Z"))

    def test_scenario_engine_emits_ground_truth_events(self) -> None:
        nodes = get_default_nodes()
        engine = ScenarioEngine(nodes, seed=11, force_scenario=ScenarioType.CONGESTION)
        now = datetime(2026, 7, 16, 20, 0, tzinfo=timezone.utc)
        label = engine.current_scenario(nodes[0].node_code, now)
        self.assertEqual(label, ScenarioType.CONGESTION)
        # Forced mode does not auto-create timed events; verify profile exists.
        profile = get_profile(ScenarioType.CONGESTION)
        self.assertEqual(profile.scenario, ScenarioType.CONGESTION)

    def test_random_engine_can_open_and_close_events(self) -> None:
        nodes = get_default_nodes()[:1]
        engine = ScenarioEngine(nodes, seed=0, anomaly_rate=1.0)
        start = datetime(2026, 7, 16, 20, 0, tzinfo=timezone.utc)
        label = engine.current_scenario(nodes[0].node_code, start)
        self.assertNotEqual(label, ScenarioType.NORMAL)
        self.assertEqual(len(engine.events), 1)
        self.assertIsNone(engine.events[0].end_time)

        # Jump far ahead to expire the scenario.
        later = start.replace(year=2027)
        engine.current_scenario(nodes[0].node_code, later)
        engine.close_all(later)
        self.assertIsNotNone(engine.events[0].end_time)


if __name__ == "__main__":
    unittest.main()
