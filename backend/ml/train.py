"""Train the Isolation Forest anomaly detector.

Purpose
-------
Fit a model on labelled synthetic QoS data (mostly normal behaviour) and save
it under ``backend/ml/artifacts/`` for the FastAPI detection service.

Usage (from repository root)::

    python -m backend.ml.train
    python -m backend.ml.train --samples 400 --contamination 0.08
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.ml.detector import AnomalyDetector
from backend.ml.features import MODEL_NAME
from backend.simulator.generator import QoSSimulator
from backend.simulator.models import ScenarioType


def build_training_set(samples_per_node: int, seed: int) -> list:
    """Generate a mostly-normal training set for unsupervised Isolation Forest.

    Classic IF practice: fit on normal behaviour and let ``contamination``
    reserve a small tail for outliers. A light mix of degradations is still
    included so the contamination quantile is not calibrated on an unrealistically
    clean distribution.
    """
    normal = QoSSimulator(
        seed=seed,
        force_scenario=ScenarioType.NORMAL,
        anomaly_rate=0.0,
        interval_seconds=5,
    ).generate_batch(samples_per_node)

    degraded_budget = max(4, samples_per_node // 20)
    degraded: list = []
    for scenario in (
        ScenarioType.CONGESTION,
        ScenarioType.HIGH_LATENCY,
        ScenarioType.PACKET_LOSS,
        ScenarioType.BANDWIDTH_LIMIT,
        ScenarioType.OUTAGE,
    ):
        sim = QoSSimulator(
            seed=seed + hash(scenario.value) % 1000,
            force_scenario=scenario,
            anomaly_rate=0.0,
            interval_seconds=5,
        )
        degraded.extend(sim.generate_batch(degraded_budget))

    return list(normal) + degraded


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Train Isolation Forest QoS detector")
    parser.add_argument("--samples", type=int, default=200, help="Normal samples per node")
    parser.add_argument("--contamination", type=float, default=0.12)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--estimators", type=int, default=200)
    args = parser.parse_args(argv)

    rows = build_training_set(args.samples, args.seed)
    print(f"Training {MODEL_NAME} on {len(rows)} samples…")
    detector = AnomalyDetector.train(
        rows,
        contamination=args.contamination,
        n_estimators=args.estimators,
        random_state=args.seed,
    )
    path = detector.save()
    print(f"Saved model to {path}")
    print(f"Metadata: {detector.meta}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
