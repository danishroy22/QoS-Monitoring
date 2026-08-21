# Phase 9 — Administrator Dashboard

Completes the dedicated Administrator / ISP Analytics dashboard without changing
the consumer speed-test experience.

## Overview modules

| Module | Content |
|--------|---------|
| Overall Mauritius QoS | Tests, ISPs, regions, QoS, download, upload, ping, jitter, loss |
| ISP leaderboard | QoS · download · upload · latency · packet loss · tests |
| Regional performance | Compact regional table (full GeoJSON map under QoS Map) |
| Time analysis | `hourly` (UTC hour-of-day) · daily · weekly · monthly |
| Package performance | Advertised vs measured + fulfilment % |

## API

```http
GET /admin/dashboard?days=90
GET /admin/history?granularity=hourly|daily|weekly|monthly&days=90
GET /admin/package-performance?days=90
GET /admin/heatmap?days=90
GET /admin/map?...
```

## UI

Admin portal → **Overview**, **History**, **Packages**, **QoS Map**.
