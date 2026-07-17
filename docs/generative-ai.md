# Phase 6 — Generative AI Analysis

## Purpose

Turn anomaly / QoS context into natural-language explanations and corrective
actions for the NOC dashboard.

## Behaviour

1. `POST /api/analyze` accepts `anomaly_id` and/or `node_code`.
2. The service builds a structured context (node metadata, latest sample,
   anomaly score, recent history).
3. If `QOS_OPENAI_API_KEY` is set, an OpenAI-compatible chat model is called.
4. Otherwise (or on LLM failure / `QOS_AI_FORCE_FALLBACK=true`), the offline
   telecom playbook generator is used.
5. Results are stored in `ai_recommendations` and listed by
   `GET /api/recommendations`.

## Configuration

```bash
# backend/.env
QOS_OPENAI_API_KEY=sk-...
QOS_OPENAI_MODEL=gpt-4o-mini
QOS_OPENAI_BASE_URL=https://api.openai.com/v1
# QOS_AI_FORCE_FALLBACK=true
```

## Example

```bash
curl -X POST http://127.0.0.1:8000/api/analyze \
  -H "Content-Type: application/json" \
  -d "{\"node_code\": \"BNG-DXB-001\", \"include_recent_history\": true}"
```

## Dashboard

The AI panel includes an **Analyse** button that calls `/api/analyze` for the
selected node and refreshes saved recommendations.
