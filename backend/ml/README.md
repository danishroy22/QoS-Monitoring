# Machine Learning Module (Phase 4)

Isolation Forest anomaly detection for broadband QoS measurements.

## Components

| Path | Role |
|------|------|
| `features.py` | Feature engineering (raw + derived QoS features) |
| `classifier.py` | Suspected-issue and severity labelling |
| `detector.py` | Train / load / predict wrapper |
| `train.py` | Training CLI using simulator data |
| `evaluate.py` | Precision / recall / F1 vs ground-truth scenarios |
| `artifacts/` | Saved model (`isolation_forest_v1.joblib`) |

## Train

```bash
python -m backend.ml.train --samples 200 --contamination 0.08
```

## Evaluate

```bash
python -m backend.ml.evaluate --samples 120
```

Writes `docs/ml-evaluation.json`.

## Run via API

With the backend running and a trained model present:

```bash
curl -X POST "http://127.0.0.1:8000/api/anomalies/run?limit=500"
curl "http://127.0.0.1:8000/api/anomalies?active_only=true"
```

The React dashboard Issues panel automatically prefers ML anomaly rows when present.
