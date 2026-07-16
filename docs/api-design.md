# API Design

Base URL during local development:

```text
http://localhost:8000
```

## Health

### `GET /health`

Returns backend status.

Example response:

```json
{
  "status": "ok",
  "service": "ai-broadband-qos-backend"
}
```

## Measurements

### `POST /api/measurements`

Used by the simulator to submit one QoS measurement.

Example request:

```json
{
  "node_code": "BNG-DXB-001",
  "timestamp": "2026-07-16T19:00:00Z",
  "latency_ms": 32.5,
  "jitter_ms": 4.2,
  "packet_loss_pct": 0.1,
  "throughput_mbps": 84.6,
  "bandwidth_utilisation_pct": 61.3,
  "signal_quality": 91.0,
  "availability_pct": 100.0,
  "scenario_label": "normal"
}
```

Example response:

```json
{
  "measurement_id": 1024,
  "stored": true
}
```

### `GET /api/metrics/latest`

Returns the latest QoS measurements for all nodes.

Query parameters:

- `limit`: Maximum number of nodes to return

### `GET /api/metrics/history`

Returns time-series measurements for charts.

Query parameters:

- `node_code`
- `start_time`
- `end_time`
- `metric`

## Anomalies

### `GET /api/anomalies`

Returns detected anomaly events.

Query parameters:

- `active_only`
- `severity`
- `node_code`

### `POST /api/anomalies/run`

Runs anomaly detection on recent measurements. This can be called manually during development or scheduled later.

Example response:

```json
{
  "processed_measurements": 500,
  "anomalies_detected": 14,
  "model_name": "isolation_forest_v1"
}
```

## AI Analysis

### `POST /api/analyze`

Generates an explanation and recommendation for a selected anomaly, node, or time window.

Example request:

```json
{
  "anomaly_id": 42,
  "include_recent_history": true
}
```

Example response:

```json
{
  "summary": "The node is showing congestion symptoms during peak usage.",
  "likely_causes": [
    "High bandwidth utilisation",
    "Increased latency and jitter",
    "Reduced throughput compared with service tier"
  ],
  "recommended_actions": [
    "Check access node capacity",
    "Review backhaul utilisation",
    "Apply traffic engineering or capacity upgrade planning"
  ],
  "severity": "medium"
}
```

### `GET /api/recommendations`

Returns saved AI explanations and recommendations.

## Frontend Integration

The React dashboard should call:

- `/api/metrics/latest` every 3-5 seconds for live health cards.
- `/api/metrics/history` when charts need a selected time range.
- `/api/anomalies` for the incident panel.
- `/api/analyze` when the user requests AI interpretation for an incident.
