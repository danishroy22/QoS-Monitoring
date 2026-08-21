# Phase 16 — Data quality and validation

Measurements are **never silently deleted**. Invalid or incomplete tests are **marked** and excluded from analytics by default.

## Flags & statuses

Assessment runs on every persist (`data_quality_service.apply_quality_to_row`):

| Status | Typical causes |
|--------|----------------|
| `valid` | Core metrics present; no hard failure / outlier |
| `incomplete` | Missing download / upload / ping |
| `failed` | Measurement errors, HTTP failure |
| `outlier` | Extreme download/upload/ping/loss fences |
| `duplicate_suspect` | Near-identical test from same client hash within ~20s |

Additional flags (may exist on otherwise eligible rows):

- `isp_detection_failed`
- `missing_package_information`
- `missing_geographic_information`
- `dns_failure` / `http_failure` / `measurement_errors`

Columns on `speed_tests`: `quality_status`, `quality_flags_json`, `analytics_eligible`.

## Analytics sample size

Admin KPIs expose:

- `total_tests` — all stored rows in window
- `analytics_n` — eligible rows used for averages
- `sample_note` — e.g. `Average Download: 96.2 Mbps (n=1,482)`

Maps, peak hours, comparison, reports, and AI facts filter with `analytics_eligible is not False` (legacy unmarked rows remain eligible).

## API / UI

- `GET /admin/data-quality?days=90` — counts + flag histogram + sample-size example
- `POST /admin/data-quality/reassess` — Administrator only; re-marks existing rows in place
- Admin portal → **Data Quality** tab
