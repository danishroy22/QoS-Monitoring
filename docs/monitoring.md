# Phase 7 — Continuous QoS Monitoring

## Purpose

Background monitoring that periodically runs the **same** Network Measurement
Engine path used by manual GO tests (`run_speedtest`) and stores each sample in
`speed_tests`. Monitoring continues until the user stops it.

## API (additive)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/monitoring/status` | Status, schedule, duration, count, last sample |
| POST | `/monitoring/start` | Enable monitoring with interval |
| POST | `/monitoring/stop` | Disable monitoring |

### Start body

```json
{
  "interval": "5m",
  "custom_seconds": null,
  "quick": true,
  "server_id": null
}
```

- `interval`: `1m` | `5m` | `10m` | `30m` | `custom`
- `custom_seconds`: required when `interval` is `custom` (min 60)
- `quick`: recommended `true` so background samples do not overlap long full tests

## Persistence

- Table `monitoring_state` — singleton config + session counters
- Measurements — existing `speed_tests` via `internet_service.run_speedtest`

## Scheduler

Daemon thread started in FastAPI lifespan (`monitoring_service.start_scheduler`).
Ticks every 5 seconds; if enabled and `next_run_at` is due, runs one sample.

## Modules

- `backend/app/models/monitoring.py`
- `backend/app/schemas/monitoring.py`
- `backend/app/services/monitoring_service.py`
- `backend/app/api/routes/monitoring.py`
- `frontend/src/components/MonitoringView.jsx`
