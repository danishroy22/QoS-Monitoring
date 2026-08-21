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
| POST | `/speedtest/identify` | Approximate IP / ISP / region |
| POST | `/speedtest/find-server` | Probe and score Mauritius servers |
| GET | `/speedtest/config` | Documented measurement parameters |
| GET | `/aggregations` | Traceable aggregates by ISP/package/region/date/… |
| GET | `/packages` | Active ISP packages (admin-configured) |
| GET | `/admin/packages` | Manage ISP packages (CRUD) |
| GET | `/admin/map` | Mauritius district QoS GeoJSON map |
| GET | `/admin/comparison` | Fair ISP comparison (stats + filters) |
| GET | `/admin/benchmark-profiles` | Ideal / use-case QoS profiles (Phase 7) |
| GET | `/admin/peak-hours` | Peak-hour / congestion-pattern analysis (Phase 8) |
| GET | `/admin/dashboard` | Administrator KPIs and ISP leaderboard |
| GET | `/admin/report` | Administrator QoS PDF report |

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

Full module map: **[PROGRAM_STRUCTURE.md](PROGRAM_STRUCTURE.md)**

- `backend/measurement/` — real measurement + QoS scoring + AI assistant
- `backend/app/` — FastAPI, models, services, routes
- `frontend/` — Internet Quality Dashboard + Administrator Portal
- `docs/admin-portal.md` — Phase 18 operator analytics
- `docs/server-selection-methodology.md` — Phase 1 server ranking
- `docs/measurement-methodology.md` — Phase 2 measurement parameters
- `docs/phase3-supabase.md` — Phase 3 traceable DB on Supabase
- `docs/phase4-packages.md` — Phase 4 ISP packages + fulfilment %
- `docs/phase5-qos-map.md` — Phase 5 Mauritius QoS map
- `docs/phase6-isp-comparison.md` — Phase 6 fair ISP comparison
- `docs/phase7-benchmark-profiles.md` — Phase 7 Ideal QoS / benchmark profiles
- `docs/phase8-peak-hours.md` — Phase 8 peak-hour / congestion patterns
- `backend/simulator/` — legacy synthetic NOC generator (still available under `/api`)

## Optional Generative AI

Set in `backend/.env`:

```bash
QOS_OPENAI_API_KEY=sk-...
```

Without a key, the offline Network Assistant playbook is used.
