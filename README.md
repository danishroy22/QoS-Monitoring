# AI-Driven Internet Quality & Broadband QoS Platform

Dissertation project with a **real Network Measurement Engine**, QoS health scoring,
Ookla-style dashboard, and an **AI Network Assistant**.

## What it does

1. **Measures** your real internet connection (download, upload, ping, jitter, loss, DNS, HTTP, IP/ISP)
2. **Stores** every result
3. **Scores** network health (Excellent → Critical)
4. **Explains** problems with an AI Network Assistant

## Quick start

```bash
# Backend
pip install -r backend/requirements.txt
python scripts/run_backend.py

# Frontend (new terminal)
cd frontend
npm install
npm run dev
```

Open **http://127.0.0.1:5173** and click **GO**.

## Primary API

| Method | Path | Description |
|--------|------|-------------|
| POST | `/speedtest` | Run a real measurement and store it |
| GET | `/history` | Past results |
| GET | `/dashboard` | Latest + health + stats + history + ISP |
| GET | `/statistics` | Aggregate averages |
| GET | `/isp` | Public IP / ISP from last test |
| GET | `/recommendation` | AI Network Assistant |
| GET | `/monitoring/status` | Continuous monitoring status |
| POST | `/monitoring/start` | Enable background monitoring |
| POST | `/monitoring/stop` | Disable background monitoring |
| GET | `/health` | API + database status |

Example:

```bash
curl -X POST http://127.0.0.1:8000/speedtest -H "Content-Type: application/json" -d "{\"quick\": true}"
curl http://127.0.0.1:8000/dashboard
curl http://127.0.0.1:8000/recommendation
```

## Architecture (redesign)

```text
Browser Dashboard  →  FastAPI
                         ├─ Network Measurement Engine (real probes)
                         ├─ QoS Analysis Engine (scores / ratings)
                         ├─ SQLite / PostgreSQL storage
                         └─ AI Network Assistant (LLM or offline playbook)
```

## Project layout

- `backend/measurement/` — real measurement + QoS scoring + AI assistant
- `backend/app/` — FastAPI, models, services, routes
- `frontend/` — Internet Quality Dashboard
- `backend/simulator/` — legacy synthetic NOC generator (still available under `/api`)

## Optional Generative AI

Set in `backend/.env`:

```bash
QOS_OPENAI_API_KEY=sk-...
```

Without a key, the offline Network Assistant playbook is used.
