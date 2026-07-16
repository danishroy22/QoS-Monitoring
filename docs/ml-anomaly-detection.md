# Phase 4 — Anomaly Detection

## Approach

1. **Feature engineering** — latency, jitter, packet loss, throughput, utilisation,
   signal quality, availability, plus derived features (`latency_x_util`,
   `loss_x_jitter`, `unavailable_pct`).
2. **Isolation Forest** (`isolation_forest_v1`) — unsupervised detector trained
   mainly on normal synthetic broadband traffic.
3. **Hybrid operational flag** — a sample is marked anomalous if Isolation Forest
   flags it **or** QoS health rules classify it as degraded/critical. This improves
   recall on mild high-latency and bandwidth-limit cases while retaining the ML
   anomaly score for evidence.
4. **Issue classification** — rule-based mapping to `congestion`, `high_latency`,
   `packet_loss`, `bandwidth_limit`, `outage`, or `performance_degradation`.
5. **Severity** — derived from anomaly score and metric magnitudes.

## Commands

```bash
python -m backend.ml.train --samples 200 --contamination 0.12
python -m backend.ml.evaluate --samples 120
python -m pytest backend/tests/test_ml.py backend/tests/test_api.py -v
```

## API

```http
POST /api/anomalies/run?limit=500
GET  /api/anomalies?active_only=true
```

Evaluation metrics are written to `docs/ml-evaluation.json`.
