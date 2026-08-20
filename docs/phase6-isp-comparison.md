# Phase 6 — Fair ISP comparison

Administrator module to compare ISPs without ranking them by raw download
speed alone.

## Modes

| Mode | Purpose |
|------|---------|
| `isp_vs_isp` | Side-by-side ISPs (optional A vs B pairwise deltas) |
| `isp_vs_benchmark` | Each ISP vs Ideal Broadband Profile targets |
| `isp_vs_ideal` | Same profile comparison (dissertation wording) |

## Metrics

Download, upload, ping, jitter, packet loss, DNS, HTTP, QoS score, package
fulfilment.

For each metric the API returns:

`count` (n=), `avg`, `median`, `min`, `max`, `stdev`

## Fairness

- Primary ordering: **mean QoS score**, then sample size — **not** raw Mbps.
- Filters: `package`, `region`, `date_from` / `date_to` / `days`, `hour_from` /
  `hour_to` so different plan tiers or geographies are not mixed.

## API

```http
GET /admin/comparison?mode=isp_vs_isp&days=90
GET /admin/comparison?mode=isp_vs_isp&isp_a=Emtel&isp_b=Rogers&package=Fibre%20100
GET /admin/comparison?mode=isp_vs_ideal&region=Plaines%20Wilhems&hour_from=18&hour_to=21
```

## UI

Admin portal → **Compare**.
