# Phase 18 — Administrator Analytics Portal

Separate operator portal over existing `speed_tests` rows. Consumer speed-test
APIs and the GO / speedometer experience are unchanged.

## API (`/admin`)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/admin/dashboard` | KPIs, ISP leaderboard, live stats, QoS overview |
| GET | `/admin/isp-analytics` | Per-ISP metric comparison |
| GET | `/admin/benchmarks` | Compare ISPs vs Ideal Broadband Profile |
| PUT | `/admin/benchmarks` | Update configurable thresholds |
| GET | `/admin/history` | `granularity=daily\|weekly\|monthly` |
| GET | `/admin/heatmap` | Aggregate by Mauritius region |
| GET | `/admin/ai/isp-analysis` | Natural-language ISP summaries |
| GET | `/admin/report` | Professional QoS PDF |

Query: `days` (default 90) on GET endpoints.

## Benchmarks

Stored in `backend/app/qos_benchmarks.json`. Defaults:

- Download ≥ 100 Mbps
- Upload ≥ 20 Mbps
- Ping ≤ 20 ms
- Jitter ≤ 5 ms
- Packet loss ≤ 0.5%
- QoS score ≥ 85

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
