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

## Supervisor Phase 1 — Automatic server and ISP selection

Consumer GO identifies the connection, then probes catalogue hosts with TCP RTT
and a documented score. Manual selection is under Advanced Settings.
See `docs/server-selection-methodology.md`.

- `POST /speedtest/identify`
- `POST /speedtest/find-server` (real probes; optional `isp_name`)

## Supervisor Phase 2 — Documented measurement methodology

Throughput is duration-windowed (not a fixed byte pass). Parameters live in
`backend/measurement/measurement_config.json`. Defaults are experimental,
not claimed optima. See `docs/measurement-methodology.md`.

- `GET /speedtest/config`

## Supervisor Phase 3 — Traceable DB (Supabase)

Every `speed_tests` row stores measurement context (ISP, ASN, region, server
operator/location/type, optional package, anonymised `client_hash`, UTC time
buckets). Aggregations: `GET /aggregations?by=isp|package|region|date|day_of_week|hour|server|metric`.

SQL schema + views: `database/supabase/speed_tests.sql`. Setup: `docs/phase3-supabase.md`.

## Supervisor Phase 4 — Internet packages + fulfilment

Administrator-configured ISP packages (no hard-coded commercial plans). Optional
selection under Advanced Settings. When present:

`fulfilment% = measured / advertised × 100` for download and upload.

- Admin: `GET/POST/PUT/DELETE /admin/packages`
- Consumer list: `GET /packages`
- Docs: `docs/phase4-packages.md`

## Supervisor Phase 5 — Mauritius geographic QoS map

Interactive district GeoJSON map in Admin → **QoS Map** with metric modes,
ISP/package/region/date/time filters, and Excellent→Critical colour legend.

- `GET /admin/map`
- Docs: `docs/phase5-qos-map.md`

## Supervisor Phase 6 — Fair ISP comparison

Compare ISPs with avg/median/min/max/stdev and n=, filtered by package/region/
time. Ordered by QoS score — not raw download speed.

- `GET /admin/comparison`
- Docs: `docs/phase6-isp-comparison.md`

## Supervisor Phase 7 — Ideal QoS / Benchmark profiles

Multiple configurable use-case profiles (General Broadband, Gaming, Video
Conferencing, Streaming, VoIP, Enterprise). Each metric has source, rationale,
unit, threshold, and description. Thresholds are **not** universal standards.

- `GET/PUT /admin/benchmarks`
- `GET /admin/benchmark-profiles`
- `PUT /admin/benchmark-profiles/active`
- `PUT /admin/benchmark-profiles/{id}`
- Docs: `docs/phase7-benchmark-profiles.md`

## Phase 18 — Administrator Analytics Portal

Separate NOC-style portal over `speed_tests`. See `docs/admin-portal.md`.

- `GET /admin/dashboard`
- `GET /admin/isp-analytics`
- `GET /admin/benchmarks`
- `PUT /admin/benchmarks`
- `GET /admin/history`
- `GET /admin/heatmap`
- `GET /admin/ai/isp-analysis`
- `GET /admin/report`
