# Backend API (Phase 3)

FastAPI + SQLAlchemy backend for QoS ingestion, storage, and metric queries.

## Layout

| Path | Role |
|------|------|
| `app/core/config.py` | Environment settings (DB URL, CORS, seeding) |
| `app/db/base.py` | SQLAlchemy declarative base |
| `app/db/session.py` | Engine + session factory + `get_db` dependency |
| `app/db/init_db.py` | Table creation + default node seeding |
| `app/models/network.py` | ORM models (nodes, measurements, events, anomalies, recommendations) |
| `app/schemas/qos.py` | Pydantic request/response models |
| `app/services/` | Measurement storage, queries, health rules |
| `app/api/routes/` | Route handlers |
| `app/main.py` | Application factory |

## Database

Defaults to **SQLite** (`backend/qos_monitoring.db`) so it runs with zero setup.
To use **PostgreSQL** (dissertation target), install the driver and set the URL:

```bash
pip install "psycopg[binary]"
# backend/.env
QOS_DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/qos_monitoring
```

Tables are created automatically on startup, and the four default simulator
nodes are seeded when `QOS_SEED_NODES=true`.

## Run

```bash
# From repository root
python scripts/run_backend.py --reload
# API docs: http://localhost:8000/docs
```

## Endpoints (implemented in Phase 3)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Service + DB status |
| GET | `/api/nodes` | List network nodes |
| POST | `/api/measurements` | Ingest a QoS measurement |
| GET | `/api/metrics/latest` | Latest sample per node + health status |
| GET | `/api/metrics/history` | Time-series for one node/metric |
| GET | `/api/anomalies` | List anomaly results (populated in Phase 4) |
| GET | `/api/recommendations` | List AI recommendations (populated in Phase 6) |

Endpoints returning HTTP 501 until later phases: `POST /api/anomalies/run`
(Phase 4) and `POST /api/analyze` (Phase 6).

## Feed it live data

```bash
# Start backend (terminal 1)
python scripts/run_backend.py

# Publish simulator data (terminal 2)
python -m backend.simulator --mode live --ticks 20 --interval 2 --publish-api
```
