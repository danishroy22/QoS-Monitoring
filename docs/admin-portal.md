# Phase 18 — Administrator Analytics Portal

Separate operator portal over existing `speed_tests` rows. Consumer speed-test
APIs and the GO / speedometer experience are unchanged.

## API (`/admin`)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/admin/dashboard` | KPIs, ISP leaderboard, live stats, QoS overview |
| GET | `/admin/isp-analytics` | Per-ISP metric comparison |
| GET | `/admin/benchmarks` | Compare ISPs vs active Ideal / use-case profile |
| PUT | `/admin/benchmarks` | Update active profile numeric thresholds |
| GET | `/admin/benchmark-profiles` | List Ideal QoS profiles (Phase 7) |
| PUT | `/admin/benchmark-profiles/active` | Select active profile |
| PUT | `/admin/benchmark-profiles/{id}` | Update profile + metric documentation |
| GET | `/admin/peak-hours` | Peak-hour vs off-peak degradation (Phase 8) |
| GET | `/admin/history` | `granularity=daily\|weekly\|monthly` |
| GET | `/admin/heatmap` | Aggregate by Mauritius region |
| GET | `/admin/ai/isp-analysis` | Natural-language ISP summaries |
| GET | `/admin/report` | Professional QoS PDF |

Query: `days` (default 90) on GET endpoints.

## Benchmarks

Multi-profile catalog: `backend/app/qos_benchmark_profiles.json` (Phase 7).
Active flat thresholds are synced to `backend/app/qos_benchmarks.json`.
See `docs/phase7-benchmark-profiles.md`. Default General Broadband anchors:

- Download ≥ 100 Mbps
- Upload ≥ 20 Mbps
- Ping ≤ 20 ms
- Jitter ≤ 5 ms
- Packet loss ≤ 0.5%
- QoS score ≥ 85

Thresholds are configurable dissertation anchors — **not** universal standards.

## Modules

- `backend/app/schemas/admin.py`
- `backend/app/services/admin_service.py`
- `backend/app/services/admin_ai.py`
- `backend/app/services/admin_report.py`
- `backend/app/api/routes/admin.py`
- `frontend/src/admin/AdminPortal.jsx`

## UI

Open the consumer app and choose **Admin** in the header. The Administrator
Portal is a dedicated NOC-style view; returning to Dashboard restores the
existing speed-test experience.
