# Phase 3 — Traceable measurements on Supabase

Supervisor goal: every speed test is **traceable** and the database supports
aggregation by ISP, package, region, date, day of week, hour, server, and metric.

This phase uses **Supabase Postgres** as the dissertation database target.
Local SQLite remains the default for zero-setup development and tests.

## What is stored

Each `speed_tests` row includes measurement values plus context:

| Group | Fields |
|-------|--------|
| Identity | `timestamp`, `public_ip` (optional), `client_hash` (HMAC anonymised id) |
| Network | `isp_name`, `as_info`, `detected_region` / `city`, lat/lon |
| Package | `internet_package` (nullable until packages UI lands) |
| Server | `server_id`, `server_label`, `server_operator`, `server_location`, `server_type` |
| Metrics | download / upload / ping / jitter / loss / DNS / HTTP + Phase 2 detail |
| QoS | `overall_score`, `overall_rating`, `measurement_config_version`, `errors_json` |
| Time buckets | `test_date`, `day_of_week` (Mon=0), `hour_utc` |

`client_hash` is HMAC-SHA256 of the public IP with `QOS_CLIENT_HASH_SALT`.
Set `QOS_STORE_PUBLIC_IP=false` to stop persisting raw IPs.

## Supabase setup

1. Create a Supabase project.
2. Open **SQL Editor** and run [`database/supabase/speed_tests.sql`](../database/supabase/speed_tests.sql).
3. In **Project Settings → Database**, copy the connection string (prefer the
   **Session pooler** URI for long-lived backends).
4. Convert it for SQLAlchemy + psycopg, for example:

```bash
# backend/.env
QOS_SUPABASE_DB_URL=postgresql+psycopg://postgres.PROJECT:PASSWORD@aws-0-REGION.pooler.supabase.com:5432/postgres?sslmode=require
QOS_CLIENT_HASH_SALT=replace-with-a-long-random-string
QOS_STORE_PUBLIC_IP=true
```

5. Install the Postgres driver and restart the backend:

```bash
pip install "psycopg[binary]"
python scripts/run_backend.py
```

When `QOS_SUPABASE_DB_URL` is set it **overrides** `QOS_DATABASE_URL`.
On startup FastAPI still calls `ensure_speed_test_columns()` so additive
columns are applied if the table already exists.

## Aggregations

### API (works on SQLite and Supabase)

```http
GET /aggregations?by=isp&days=30
GET /aggregations?by=package
GET /aggregations?by=region
GET /aggregations?by=date
GET /aggregations?by=day_of_week
GET /aggregations?by=hour
GET /aggregations?by=server
GET /aggregations?by=metric&metric=download_mbps
```

### SQL views (Supabase)

After running the SQL file:

- `agg_by_isp`
- `agg_by_package`
- `agg_by_region`
- `agg_by_date`
- `agg_by_day_of_week`
- `agg_by_hour`
- `agg_by_server`
- `agg_by_metric`

## Privacy notes

- Prefer `client_hash` for correlating repeat tests from the same line.
- Do not put end-user names, emails, or account numbers in `speed_tests`.
- Row Level Security is enabled on the table; the FastAPI backend should use
  the **database password / service connection**, not the anon key, for writes.

## Existing APIs

Consumer GO, SSE streams, `/speedtest/complete`, history, dashboard, and admin
portal keep working. They now persist richer context when available.
