# SmartQoS — Program Structure

This document describes how the SmartQoS codebase is organised: folders, modules,
data flow, and how the consumer app, monitoring, administrator portal, and
legacy NOC stack fit together.

For how to run the project, see [README.md](README.md).

---

## 1. High-level architecture

```text
Browser (React + Vite)          http://127.0.0.1:5173
        │  Vite proxy
        ▼
FastAPI (Uvicorn)               http://127.0.0.1:8000
        ├─ Network Measurement Engine     backend/measurement/
        ├─ QoS Analysis Engine            measurement/qos_analysis.py
        ├─ AI Network Assistant           measurement/assistant.py
        ├─ Continuous Monitoring          app/services/monitoring_service.py
        ├─ Administrator Analytics        app/services/admin_service.py
        ├─ SQLite / PostgreSQL            speed_tests + monitoring_state
        └─ Legacy NOC APIs                /api/*  (simulator + ML)
```

**Stack**

| Layer | Technology |
|-------|------------|
| Frontend | React 18, Vite 6, Framer Motion, Chart.js, Lucide |
| Backend | FastAPI, Uvicorn, SQLAlchemy 2, Pydantic |
| Database | SQLite by default (`backend/qos_monitoring.db`) |
| AI | Optional OpenAI-compatible API; offline playbook otherwise |
| Measurement | Cloudflare speed endpoints + OS ping/TCP; ISP via ip-api |

---

## 2. Repository tree

```text
FYP/
├── README.md                      # Quick start and primary APIs
├── PROGRAM_STRUCTURE.md           # This file
├── docs/                          # Design notes, schema, phase docs
├── scripts/                       # Launchers, training, smoke tests
├── backend/                       # FastAPI, engines, ML, tests
└── frontend/                      # React Internet Quality UI
```

---

## 3. `scripts/` — how the system is started

| Script | Purpose |
|--------|---------|
| `run_backend.py` | Start FastAPI on port 8000 |
| `run_simulator.py` | Generate synthetic NOC measurements |
| `train_anomaly_model.py` | Train Isolation Forest (legacy) |
| `run_detection.py` | Run anomaly detection (legacy) |
| `run_analyze.py` | Trigger GenAI analyse helper (legacy) |
| `smoke_check.py` | General API smoke test |
| `smoke_internet.py` | Internet Quality API smoke test |

Typical run (two terminals):

```bash
python scripts/run_backend.py

cd frontend
npm install
npm run dev
```

---

## 4. `backend/` — server structure

```text
backend/
├── requirements.txt
├── qos_monitoring.db              # Created at runtime (SQLite)
├── app/                           # Web application (HTTP + persistence)
├── measurement/                   # Real speed-test + QoS + consumer AI
├── simulator/                     # Synthetic broadband node generator
├── ml/                            # Isolation Forest anomaly detection
└── tests/                         # Pytest
```

### 4.1 `backend/app/` — FastAPI application

Entry point: `backend/app/main.py` → `create_app()`.

On startup the app:

1. Creates database tables (`init_db`)
2. Starts the monitoring scheduler
3. Mounts routers (Internet Quality, monitoring, admin, legacy `/api`)

```text
app/
├── main.py                        # Application factory, CORS, routers
├── qos_benchmarks.json            # Ideal Broadband Profile (admin)
├── core/
│   └── config.py                  # QOS_* settings, DB URL, OpenAI
├── db/
│   ├── base.py                    # SQLAlchemy Base
│   ├── session.py                 # Engine + get_db()
│   └── init_db.py                 # create_all + optional node seed
├── models/                        # ORM tables
│   ├── speedtest.py               # speed_tests
│   ├── monitoring.py              # monitoring_state
│   └── network.py                 # Legacy NOC tables
├── schemas/                       # Pydantic contracts
│   ├── internet.py
│   ├── monitoring.py
│   ├── admin.py
│   └── qos.py
├── services/                      # Business logic
│   ├── internet_service.py        # Run/store tests, dashboard
│   ├── monitoring_service.py      # Background interval tests
│   ├── admin_service.py           # ISP aggregations, heatmap
│   ├── map_service.py             # Mauritius GeoJSON QoS map (Phase 5)
│   ├── comparison_service.py      # Fair ISP comparison (Phase 6)
│   ├── package_service.py         # ISP packages + fulfilment (Phase 4)
│   ├── admin_ai.py                # Admin ISP narratives
│   ├── admin_report.py            # PDF report
│   ├── ai_service.py              # Legacy NOC GenAI
│   ├── ai_llm.py
│   ├── ai_fallback.py
│   └── ai_prompts.py
└── api/routes/                    # HTTP endpoints
    ├── internet.py                # /speedtest, /dashboard, /history, …
    ├── monitoring.py              # /monitoring/*
    ├── admin.py                   # /admin/*
    ├── health.py                  # /health
    ├── measurements.py            # /api/measurements  (legacy)
    ├── metrics.py                 # /api/metrics       (legacy)
    ├── anomalies.py               # /api/anomalies     (legacy)
    └── analyze.py                 # /api/analyze       (legacy)
```

**Request path inside the backend**

```text
Route (api/routes/*.py)
    → Service (app/services/*.py)
        → Model / Engine (models, measurement/)
            → SQLite
```

### 4.2 `backend/measurement/` — Network Measurement Engine

This is the **real** internet test used by the GO button.

| File | Responsibility |
|------|----------------|
| `engine.py` | Download, upload, ping, jitter, loss, DNS, HTTP, ISP/IP |
| `config.py` / `measurement_config.json` | Documented duration, packet, connection parameters |
| `qos_analysis.py` | Weighted score and Excellent → Critical ratings |
| `servers.py` | Load and normalise Mauritius server catalog |
| `mauritius_servers.json` | Server metadata (name, location, host, …) |
| `assistant.py` | Consumer AI Network Assistant |

Throughput uses a shared Cloudflare measurement backend. Mauritius entries
supply ISP identity, region, and host metadata.

### 4.3 `backend/simulator/` and `backend/ml/` — legacy research path

Kept for dissertation continuity. Not used by the consumer GO flow.

| Path | Responsibility |
|------|----------------|
| `simulator/` | Virtual nodes, scenarios, CSV / live API publish |
| `ml/` | Feature engineering, Isolation Forest train/detect/evaluate |

Legacy HTTP surface remains under `/api/*`.

---

## 5. Database

Default: SQLite at `backend/qos_monitoring.db`.  
**Dissertation target:** Supabase Postgres via `QOS_SUPABASE_DB_URL`
(see `docs/phase3-supabase.md`). Optional local PostgreSQL via `QOS_DATABASE_URL`.

| Table | Model | Used by |
|-------|--------|---------|
| `speed_tests` | `SpeedTestResult` | Consumer tests, monitoring samples, admin analytics, Phase 3 aggregations |
| `monitoring_state` | `MonitoringState` | Enable/disable, interval, counters |
| `network_nodes` | `NetworkNode` | Legacy NOC |
| `qos_measurements` | `QoSMeasurement` | Legacy NOC |
| `anomaly_results` | `AnomalyResult` | Legacy ML |
| `ai_recommendations` | `AiRecommendation` | Legacy GenAI |

Admin and monitoring **reuse** `speed_tests`. They do not introduce a second measurement store.

---

## 6. `frontend/` — user interface

```text
frontend/
├── package.json
├── vite.config.js                 # Dev server :5173, proxies API → :8000
└── src/
    ├── main.jsx                   # React mount
    ├── App.jsx                    # Shell + view switcher
    ├── api/client.js              # fetch + SSE helpers
    ├── styles/index.css           # Dark glass design system
    ├── utils/format.js
    ├── admin/                     # Phase 18 portal (lazy-loaded)
    │   ├── AdminPortal.jsx
    │   └── AdminCharts.jsx
    └── components/
        ├── SpeedTestExperience.jsx
        ├── Speedometer.jsx
        ├── MauritiusServerPicker.jsx
        ├── FindServerPanel.jsx
        ├── TestStageProgress.jsx
        ├── ResultsView.jsx
        ├── MonitoringView.jsx
        ├── SpeedGraph.jsx
        ├── HistoryTable.jsx
        ├── AiAssistant.jsx
        └── ui/                    # GlassCard, MetricStatCard, SoftButton, …
```

### 6.1 Views in `App.jsx`

| View | UI | Purpose |
|------|-----|---------|
| `dashboard` | Speedometer, GO, metric cards, history, AI | Consumer Internet Quality |
| `monitoring` | `MonitoringView` | Continuous background tests |
| `admin` | `AdminPortal` (lazy) | Operator ISP analytics |
| `results` | `ResultsView` (lazy) | Post-test report |

Header navigation: **Dashboard · Monitoring · Admin**.  
The Administrator Portal does not modify the GO / speedometer experience.

### 6.2 Shared UI kit

Reusable pieces live in `components/ui/`:

- `GlassCard.jsx` — glassmorphic panel
- `MetricStatCard.jsx` — KPI card (supports live/pending)
- `SoftButton.jsx` — primary/ghost buttons
- `PanelHeader.jsx` — title + subtitle
- `LoadingPulse.jsx` — skeletons / loaders

---

## 7. Runtime data flow

### Consumer speed test

```text
User clicks GO
    SpeedTestExperience
        POST /speedtest/measure/server
        GET  /speedtest/stream/download     (SSE live Mbps)
        GET  /speedtest/stream/upload       (SSE)
        POST /speedtest/measure/latency
        POST /speedtest/complete            → analyse_qos → INSERT speed_tests
    Dashboard metric cards update live
    Results view + GET /recommendation
```

### Continuous monitoring

```text
POST /monitoring/start
    Scheduler thread (every few seconds)
        when due → internet_service.run_speedtest()
        row stored in speed_tests
POST /monitoring/stop
```

### Administrator portal

```text
Admin UI
    GET /admin/dashboard
    GET /admin/isp-analytics
    GET /admin/benchmarks
    GET /admin/history
    GET /admin/heatmap
    GET /admin/ai/isp-analysis
    GET /admin/report                    → PDF from speed_tests aggregates
```

All admin reads come from existing `speed_tests` rows.

---

## 8. HTTP surface (summary)

**Internet Quality (primary)**

| Method | Path |
|--------|------|
| POST | `/speedtest` |
| GET | `/speedtest/servers` |
| POST | `/speedtest/find-server` |
| GET | `/speedtest/stream/download` |
| GET | `/speedtest/stream/upload` |
| POST | `/speedtest/measure/server` |
| POST | `/speedtest/measure/latency` |
| POST | `/speedtest/complete` |
| GET | `/dashboard` `/history` `/statistics` `/isp` `/recommendation` `/health` |

**Monitoring**

| Method | Path |
|--------|------|
| GET | `/monitoring/status` |
| POST | `/monitoring/start` |
| POST | `/monitoring/stop` |

**Administrator**

| Method | Path |
|--------|------|
| GET | `/admin/dashboard` |
| GET | `/admin/isp-analytics` |
| GET | `/admin/benchmarks` |
| PUT | `/admin/benchmarks` |
| GET | `/admin/history` |
| GET | `/admin/heatmap` |
| GET | `/admin/ai/isp-analysis` |
| GET | `/admin/report` |

**Legacy NOC** (`api_prefix=/api`)

`/api/measurements`, `/api/nodes`, `/api/metrics/*`, `/api/anomalies`, `/api/analyze`

Interactive docs: http://127.0.0.1:8000/docs

---

## 9. Dual-product map (dissertation)

| Product surface | Audience | Main code |
|-----------------|----------|-----------|
| Internet Quality dashboard | Consumer | `measurement/` + `internet.py` + `App.jsx` dashboard |
| Continuous monitoring | Same user | `monitoring_service.py` + `MonitoringView.jsx` |
| Administrator portal | Operator / ISP analyst | `/admin` + `frontend/src/admin/` |
| Simulated NOC + ML | Evaluation / write-up | `simulator/` + `ml/` + `/api/*` |

The consumer measurement APIs are not replaced by later phases. Monitoring and
admin **add** modules on top of `speed_tests`.

---

## 10. Configuration

`backend/.env` (prefix `QOS_`):

```bash
QOS_DATABASE_URL=sqlite:///...          # optional; SQLite is default
QOS_OPENAI_API_KEY=sk-...               # optional
QOS_OPENAI_MODEL=gpt-4o-mini
```

Without an API key, both the consumer assistant and admin ISP analysis use the
offline playbook.

Frontend API base: optional `VITE_API_BASE`. In development, Vite proxies
`/speedtest`, `/dashboard`, `/monitoring`, `/admin`, and related paths to
`http://127.0.0.1:8000`.

---

## 11. Related documentation

| File | Contents |
|------|----------|
| [README.md](README.md) | Quick start |
| [docs/architecture.md](docs/architecture.md) | Original system architecture |
| [docs/database-schema.md](docs/database-schema.md) | Schema notes |
| [docs/internet-quality-redesign.md](docs/internet-quality-redesign.md) | Phases 2–7 + 18 |
| [docs/monitoring.md](docs/monitoring.md) | Continuous monitoring |
| [docs/admin-portal.md](docs/admin-portal.md) | Administrator portal |
| [docs/api-design.md](docs/api-design.md) | API contract notes |
| [docs/ml-anomaly-detection.md](docs/ml-anomaly-detection.md) | Isolation Forest path |
