# Phase 4 — Internet package data model

Distinguish **advertised package speed** from **measured speed**.

## Rules

- Packages are **administrator-configured** (`internet_packages` table).
- **No commercial package catalogue is hard-coded.**
- When a test is linked to a package, SmartQoS stores:

```text
download_fulfilment_pct = measured_download_mbps / advertised_download_mbps × 100
upload_fulfilment_pct   = measured_upload_mbps   / advertised_upload_mbps   × 100
```

Values may exceed 100% if the line outperforms the advertised plan.

## Admin configuration

In the Administrator portal → **Packages** tab, or via API:

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/admin/packages` | List all packages |
| POST | `/admin/packages` | Create |
| PUT | `/admin/packages/{id}` | Update |
| DELETE | `/admin/packages/{id}` | Soft-deactivate |

Example body:

```json
{
  "isp_name": "Emtel",
  "package_name": "100 Mbps",
  "advertised_download_mbps": 100,
  "advertised_upload_mbps": 40,
  "notes": "Optional operator note"
}
```

## Consumer selection

Active packages are listed at `GET /packages`.

Under **Advanced Settings**, the user may optionally pick a package before GO.
That sets `package_id` / `internet_package` on `/speedtest/complete`. Fulfilment
is computed on the server when the package resolves.

## Supabase

Run [`database/supabase/internet_packages.sql`](../database/supabase/internet_packages.sql)
after the Phase 3 speed_tests script (or together when you add the Supabase URL later).

## What is stored on each test

When a package matches: `package_id`, `internet_package`, `advertised_download_mbps`,
`advertised_upload_mbps`, `download_fulfilment_pct`, `upload_fulfilment_pct`.
