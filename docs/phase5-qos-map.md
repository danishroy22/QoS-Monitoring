# Phase 5 — Mauritius geographic QoS map

Administrator interactive map of Mauritius districts with filtered QoS
aggregates and a documented Excellent→Critical colour scale.

## API

```http
GET /admin/map?metric=qos&days=30
GET /admin/map?metric=download&isp=Emtel&package=100%20Mbps&hour_from=18&hour_to=21
```

### Query parameters

| Param | Meaning |
|-------|---------|
| `metric` | `download` · `upload` · `latency` · `jitter` · `packet_loss` · `qos` · `fulfilment` |
| `isp` | Normalised ISP name |
| `package` | `internet_package` string |
| `region` | District / locality filter |
| `days` | Rolling window (ignored if `date_from` / `date_to` set) |
| `date_from` / `date_to` | Custom date range (ISO) |
| `day_of_week` | Monday=0 … Sunday=6 |
| `hour_from` / `hour_to` | UTC hour window (supports overnight) |

Response is a GeoJSON `FeatureCollection` plus `meta`, `legend`, and `metrics`.

Geometry: `backend/measurement/mauritius_districts.geojson` (simplified
district polygons for dissertation visualisation — not official cadastral data).

## Colour scale

Raw district averages appear in tooltips and the summary table. Fill colour uses
a **normalised 0–100 quality score** mapped to:

| Rating | Colour | Min score |
|--------|--------|-----------|
| Excellent | `#059669` | 90 |
| Good | `#10b981` | 75 |
| Fair | `#f59e0b` | 60 |
| Poor | `#f97316` | 40 |
| Critical | `#e11d48` | 0 |

Latency / jitter / loss invert quality (lower measured value → higher score).

## UI

Admin portal → **QoS Map**: metric modes, filters, Leaflet map, legend, district
table. Legacy locality cards remain below for report continuity (`/admin/heatmap`).
