"""Unit and integration tests for Phase 4 anomaly detection."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from backend.ml.classifier import classify_severity, classify_suspected_issue
from backend.ml.detector import AnomalyDetector
from backend.ml.features import extract_features, labels_from_scenario
from backend.simulator.generator import QoSSimulator
from backend.simulator.models import ScenarioType


class FeatureTests(unittest.TestCase):
    def test_feature_vector_length(self) -> None:
        sim = QoSSimulator(seed=1, force_scenario=ScenarioType.NORMAL)
        sample = sim.generate_measurement(sim.nodes[0])
        vector = extract_features(sample)
        self.assertEqual(vector.shape, (10,))

    def test_labels_from_scenario(self) -> None:
        rows = [
            {"scenario_label": "normal"},
            {"scenario_label": "congestion"},
        ]
        labels = labels_from_scenario(rows)
        self.assertEqual(list(labels), [0, 1])


class ClassifierTests(unittest.TestCase):
    def test_outage_issue(self) -> None:
        issue = classify_suspected_issue(
            {"availability_pct": 10, "packet_loss_pct": 20, "latency_ms": 200}
        )
        self.assertEqual(issue, "outage")

    def test_congestion_issue(self) -> None:
        issue = classify_suspected_issue(
            {
                "availability_pct": 100,
                "packet_loss_pct": 1.5,
                "latency_ms": 90,
                "bandwidth_utilisation_pct": 92,
                "jitter_ms": 8,
            }
        )
        self.assertEqual(issue, "congestion")

    def test_severity_critical(self) -> None:
        severity = classify_severity(
            anomaly_score=-0.3,
            row={"availability_pct": 20, "packet_loss_pct": 10, "latency_ms": 200},
        )
        self.assertEqual(severity, "critical")


class DetectorTests(unittest.TestCase):
    def test_train_predict_and_persist(self) -> None:
        normal = QoSSimulator(
            seed=3, force_scenario=ScenarioType.NORMAL, anomaly_rate=0.0
        ).generate_batch(40)
        congested = QoSSimulator(
            seed=4, force_scenario=ScenarioType.CONGESTION, anomaly_rate=0.0
        ).generate_batch(20)
        rows = normal + congested

        detector = AnomalyDetector.train(rows, contamination=0.15, random_state=3)
        preds = detector.predict_many(congested)
        anomaly_rate = sum(1 for p in preds if p.is_anomaly) / len(preds)
        self.assertGreater(anomaly_rate, 0.3)

        with tempfile.TemporaryDirectory() as tmp:
            model_path = Path(tmp) / "model.joblib"
            meta_path = Path(tmp) / "meta.json"
            detector.save(model_path, meta_path)
            loaded = AnomalyDetector.load(model_path, meta_path)
            again = loaded.predict_many(congested[:5])
            self.assertEqual(len(again), 5)


if __name__ == "__main__":
    unittest.main()
