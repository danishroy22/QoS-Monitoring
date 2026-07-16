"""Feature engineering for QoS anomaly detection.

Purpose
-------
Convert raw QoS measurements into a fixed numeric feature vector suitable for
Isolation Forest. Features are chosen to reflect telecom NOC signals:
delay, variability, loss, capacity use, and availability.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

import numpy as np

FEATURE_NAMES: list[str] = [
    "latency_ms",
    "jitter_ms",
    "packet_loss_pct",
    "throughput_mbps",
    "bandwidth_utilisation_pct",
    "signal_quality",
    "availability_pct",
    # Derived features improve separation of degradation patterns.
    "latency_x_util",
    "loss_x_jitter",
    "unavailable_pct",
]

MODEL_NAME = "isolation_forest_v1"


def _get(row: Mapping[str, Any] | Any, key: str, default: float = 0.0) -> float:
    if isinstance(row, Mapping):
        value = row.get(key, default)
    else:
        value = getattr(row, key, default)
    if value is None:
        return float(default)
    return float(value)


def extract_features(row: Mapping[str, Any] | Any) -> np.ndarray:
    """Extract a 1-D feature vector from one measurement-like object."""
    latency = _get(row, "latency_ms")
    jitter = _get(row, "jitter_ms")
    loss = _get(row, "packet_loss_pct")
    throughput = _get(row, "throughput_mbps")
    util = _get(row, "bandwidth_utilisation_pct")
    signal = _get(row, "signal_quality", 90.0)
    availability = _get(row, "availability_pct", 100.0)

    vector = np.array(
        [
            latency,
            jitter,
            loss,
            throughput,
            util,
            signal,
            availability,
            latency * (util / 100.0),
            loss * jitter,
            100.0 - availability,
        ],
        dtype=np.float64,
    )
    return vector


def extract_feature_matrix(rows: Sequence[Mapping[str, Any] | Any]) -> np.ndarray:
    """Stack feature vectors for a batch of measurements."""
    if not rows:
        return np.empty((0, len(FEATURE_NAMES)), dtype=np.float64)
    return np.vstack([extract_features(row) for row in rows])


def labels_from_scenario(rows: Sequence[Mapping[str, Any] | Any]) -> np.ndarray:
    """Binary ground-truth labels: 1 = degraded scenario, 0 = normal."""
    labels = []
    for row in rows:
        if isinstance(row, Mapping):
            scenario = str(row.get("scenario_label", "normal"))
        else:
            scenario = str(getattr(row, "scenario_label", "normal"))
        labels.append(0 if scenario == "normal" else 1)
    return np.array(labels, dtype=np.int32)
