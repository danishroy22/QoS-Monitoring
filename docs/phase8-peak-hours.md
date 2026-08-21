# Phase 8 — Peak-hour and congestion analysis

Identify periods where measured QoS degrades relative to an off-peak baseline.

## What it does

- Groups stored tests by **hour (UTC)**, **day of week**, **ISP**, **region**, and **package**
- Finds the contiguous 2–4 hour window with the strongest multi-metric degradation
- Reports peak vs off-peak deltas for download, upload, latency, jitter, packet loss, QoS score
- Filters: ISP, package, region, date range / days

## Scientific caution

Do **not** treat the result as confirmed congestion. The API and UI use wording such as:

> Performance degradation consistent with a possible congestion pattern.

Measurements alone cannot independently confirm the underlying network cause.

## API

```http
GET /admin/peak-hours?days=90
GET /admin/peak-hours?isp=Emtel&region=Ebene&days=30
GET /admin/peak-hours?package=Fibre%20100&date_from=2026-07-01&date_to=2026-08-20
```

## UI

Admin portal → **Peak Hours**.

## Module

`backend/app/services/peak_hour_service.py`
