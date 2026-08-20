# Phase 7 — Ideal QoS / Benchmark profiles

Configurable use-case profiles for dissertation comparisons. Thresholds are
**experimental anchors**, not universal industry standards.

## Profiles (defaults)

| Id | Name |
|----|------|
| `general-broadband` | General Broadband |
| `gaming` | Gaming |
| `video-conferencing` | Video Conferencing |
| `streaming` | Streaming |
| `voip` | VoIP |
| `enterprise` | Enterprise |

Each metric stores: **threshold**, **unit**, **source**, **rationale**, **description**.

Catalog file: `backend/app/qos_benchmark_profiles.json`  
Legacy flat sync: `backend/app/qos_benchmarks.json` (active profile thresholds only)

## API

```http
GET  /admin/benchmarks?days=90
GET  /admin/benchmarks?days=90&profile_id=gaming
PUT  /admin/benchmarks?days=90          # update active profile numeric thresholds
GET  /admin/benchmark-profiles
PUT  /admin/benchmark-profiles/active?profile_id=gaming
PUT  /admin/benchmark-profiles/{profile_id}
```

## UI

Admin portal → **Benchmarks**: profile tabs, disclaimer, quick thresholds,
per-metric documentation editor, compliance charts.
