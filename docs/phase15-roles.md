# Phase 15 — Administrator / ISP roles

SmartQoS separates **Consumer**, **Administrator**, and **ISP Administrator** access.

## Roles

| Role | Capabilities |
|------|----------------|
| Consumer | Run tests, view own results / history (`X-Client-Hash` optional on `GET /history`) |
| Administrator | National Mauritius aggregates, ISP compare, reports, heatmaps, benchmarks, packages, data quality reassess |
| ISP Administrator | Own ISP only: packages, regional/map, alerts-style analytics, AI, reports scoped to that ISP |

ISP Administrators **cannot** request another ISP’s private operational aggregates (`403` on cross-ISP filters). Cross-ISP comparison mode is forced to `isp_vs_benchmark` for ISP admins. Benchmark profile edits require the national Administrator.

## Auth (dissertation-friendly tokens)

Headers:

- `X-SmartQoS-Role`: `consumer` \| `administrator` \| `isp_administrator`
- `X-SmartQoS-Token`: shared secret from env
- `X-SmartQoS-ISP`: required for ISP admin in demo mode (must match token mapping when `QOS_AUTH_REQUIRED=true`)

Env (`backend/.env`):

```text
QOS_AUTH_REQUIRED=false
QOS_ADMIN_TOKEN=admin-demo-token
QOS_ISP_TOKENS=Emtel:emtel-demo-token,Rogers:rogers-demo-token
```

When `QOS_AUTH_REQUIRED=false` (default), local demos keep working; the Admin portal role picker still sends headers so you can exercise ISP scoping.

## API

- `GET /admin/auth/status` — current principal + permissions
- All `/admin/*` routes require a non-consumer principal

## UI

The Admin portal does not expose a role picker. Roles are enforced at the API when
`QOS_AUTH_REQUIRED=true` (headers above). Consumer speed-test UI is unchanged.
