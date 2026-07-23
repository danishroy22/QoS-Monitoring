# Internet Quality Redesign Notes

## Phase 2 — Network Measurement Engine

Real probes in `backend/measurement/engine.py`:

- Download / upload throughput (Cloudflare speed endpoints)
- Ping, jitter, packet loss (OS ping, TCP fallback)
- DNS lookup time
- HTTP response time
- IPv4 / IPv6 reachability
- Public IP + ISP name (ip-api.com)

Every run is stored in `speed_tests`.

## Phase 3 — Backend API

- `POST /speedtest`
- `GET /history`
- `GET /dashboard`
- `GET /statistics`
- `GET /isp`
- `GET /recommendation`
- `GET /health`

## Phase 4 — QoS Analysis Engine

Weighted health score + ratings: Excellent / Good / Fair / Poor / Critical.

## Phase 5 — Dashboard

Ookla-style React UI with GO button, overall score, metric cards, speed graph, history, AI panel.

## Phase 6 — AI Network Assistant

Trend-aware analysis with possible reasons and recommended actions (`GET /recommendation`).

## Phase 7 — Continuous QoS Monitoring

Background interval-based measurements using the same engine. See `docs/monitoring.md`.

- `GET /monitoring/status`
- `POST /monitoring/start`
- `POST /monitoring/stop`
