# QoS Simulator Design (Phase 2)

## Purpose

The simulator replaces physical broadband monitoring equipment with a realistic synthetic telemetry source. It produces labelled QoS samples that the FastAPI backend, anomaly detector, and Generative AI services can consume.

## Components

1. **Virtual nodes** (`nodes.py`) — four access nodes covering FTTH, DSL, and fixed wireless.
2. **Scenario profiles** (`scenarios.py`) — calibrated modifiers for latency, jitter, loss, throughput, utilisation, signal, and availability.
3. **Scenario engine** (`engine.py`) — schedules degradations, boosts congestion in busy hours, and records ground-truth events.
4. **Generator** (`generator.py`) — produces timestamped `QoSMeasurement` objects.
5. **Publishers** (`publishers.py`) — CSV export for offline ML; HTTP POST for live ingestion (Phase 3).
6. **CLI** (`cli.py`) — batch and live operating modes.

## Scenarios

| Label | Typical symptoms |
|-------|------------------|
| `normal` | Stable latency, low loss, moderate utilisation |
| `congestion` | High utilisation, high latency/jitter, reduced throughput |
| `high_latency` | Latency spike with relatively moderate loss |
| `packet_loss` | Elevated loss and jitter |
| `bandwidth_limit` | Throughput capped below service tier |
| `outage` | Low availability, collapsed throughput |

## Outputs

- `data/simulator/qos_measurements.csv`
- `data/simulator/network_events.csv`

Measurement payloads match the Phase 3 API contract for `POST /api/measurements`.
