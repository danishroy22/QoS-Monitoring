"""Evaluate the anomaly detector against simulator ground-truth labels.

Usage::

    python -m backend.ml.evaluate
    python -m backend.ml.evaluate --samples 150
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.ml.detector import AnomalyDetector
from backend.ml.features import labels_from_scenario
from backend.simulator.generator import QoSSimulator
from backend.simulator.models import ScenarioType


def build_eval_set(samples_per_node: int, seed: int) -> list:
    rows: list = []
    # Half normal, half mixed degradations.
    normal_n = samples_per_node // 2
    degraded_n = max(4, samples_per_node // 10)

    rows.extend(
        QoSSimulator(
            seed=seed,
            force_scenario=ScenarioType.NORMAL,
            anomaly_rate=0.0,
        ).generate_batch(normal_n)
    )
    for scenario in (
        ScenarioType.CONGESTION,
        ScenarioType.HIGH_LATENCY,
        ScenarioType.PACKET_LOSS,
        ScenarioType.BANDWIDTH_LIMIT,
        ScenarioType.OUTAGE,
    ):
        rows.extend(
            QoSSimulator(
                seed=seed + 17 + hash(scenario.value) % 500,
                force_scenario=scenario,
                anomaly_rate=0.0,
            ).generate_batch(degraded_n)
        )
    return rows


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Evaluate QoS anomaly detector")
    parser.add_argument("--samples", type=int, default=120)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument(
        "--output",
        type=str,
        default="docs/ml-evaluation.json",
        help="Where to write evaluation metrics JSON",
    )
    args = parser.parse_args(argv)

    detector = AnomalyDetector.load()
    rows = build_eval_set(args.samples, args.seed)
    y_true = labels_from_scenario(rows)
    preds = detector.predict_many(rows)
    y_pred = np.array([1 if p.is_anomaly else 0 for p in preds], dtype=np.int32)

    precision = float(precision_score(y_true, y_pred, zero_division=0))
    recall = float(recall_score(y_true, y_pred, zero_division=0))
    f1 = float(f1_score(y_true, y_pred, zero_division=0))
    cm = confusion_matrix(y_true, y_pred).tolist()
    report = classification_report(y_true, y_pred, target_names=["normal", "anomaly"], zero_division=0)

    # Per-scenario recall for dissertation tables.
    per_scenario: dict[str, dict[str, float]] = {}
    for scenario in ScenarioType:
        idx = [
            i
            for i, row in enumerate(rows)
            if row.scenario_label == scenario.value
        ]
        if not idx:
            continue
        yt = y_true[idx]
        yp = y_pred[idx]
        per_scenario[scenario.value] = {
            "n": int(len(idx)),
            "precision": float(precision_score(yt, yp, zero_division=0)),
            "recall": float(recall_score(yt, yp, zero_division=0)),
            "f1": float(f1_score(yt, yp, zero_division=0)),
        }

    results = {
        "model_name": detector.meta.get("model_name", "isolation_forest_v1"),
        "n_samples": int(len(rows)),
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "confusion_matrix": cm,
        "per_scenario": per_scenario,
    }

    out = Path(args.output)
    if not out.is_absolute():
        out = ROOT / out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(results, indent=2), encoding="utf-8")

    print(report)
    print(json.dumps(results, indent=2))
    print(f"Wrote evaluation to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
