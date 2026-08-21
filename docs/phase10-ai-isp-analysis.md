# Phase 10 — AI ISP analysis

Extend the Network Assistant so it can answer **ISP analytics questions** using
retrieved database aggregates only. Statistics are never invented.

## Example questions

- Which ISP has the best average latency?
- Which ISP has the best package fulfilment?
- Which regions experience the greatest degradation?
- When does Emtel experience its worst performance?
- How has Mauritius broadband performance changed?
- Which packages consistently underperform?

## Grounding

1. Retrieve facts from `speed_tests` aggregates (ISP analytics, packages, peak
   hours, heatmap, daily history).
2. Classify the question intent.
3. Answer offline from those facts (with `n=` sample sizes).
4. If an LLM key is configured, it may only add brief notes — numeric claims
   stay tied to the offline fact answer.

## API

```http
GET  /admin/ai/isp-analysis?days=90
GET  /admin/ai/facts?days=90
GET  /admin/ai/ask?q=Which%20ISP%20has%20the%20best%20average%20latency%3F&days=90
POST /admin/ai/ask?days=90
Content-Type: application/json
{ "question": "How has Mauritius broadband performance changed?" }
```

## UI

Admin portal → **AI Analysis** → Ask the ISP analyst (example chips + free text).

## Module

`backend/app/services/isp_ai_qa.py`
