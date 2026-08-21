# Phase 11 — AI root-cause style analysis

Identify co-occurring QoS patterns and explain them **cautiously**.

## Example narrative

> Latency increased by 32% between 18:00 and 21:00 while download throughput
> decreased by 18%. This pattern is consistent with increased network
> utilisation or congestion, although the available measurements cannot
> independently confirm the underlying network cause.

## Rules

- Do **not** claim certainty where the data does not support it.
- Prefer wording: *consistent with*, *may be*, *cannot independently confirm*.
- Always publish sample sizes (`n=`) and low confidence.
- List what the pattern is consistent with **and** what it cannot confirm.

## API

```http
GET /admin/ai/root-cause?days=90
GET /admin/ai/root-cause?isp=Emtel&region=Ebene&days=30
```

## UI

Admin portal → **Root Cause**.

## Module

`backend/app/services/root_cause_service.py`
