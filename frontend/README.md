# Frontend Dashboard (Phase 5)

React + Vite Network Operations Centre (NOC) dashboard for the AI-driven broadband QoS platform.

## Features

- Live node health cards (latency, jitter, loss, throughput, utilisation, availability)
- Network summary status bar
- Historical Chart.js graphs per node and metric
- Detected issues panel (rule-based now; ML anomalies in Phase 4)
- AI analysis panel (operational synopsis now; Generative AI in Phase 6)
- Auto-refresh every 4 seconds via the FastAPI backend

## Run

```bash
# Terminal 1 — backend
python scripts/run_backend.py

# Terminal 2 — feed live data
python -m backend.simulator --mode live --ticks 0 --interval 3 --publish-api

# Terminal 3 — dashboard
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173**

Vite proxies `/api` and `/health` to `http://127.0.0.1:8000`.

## Layout

| Path | Role |
|------|------|
| `src/api/client.js` | Backend API client |
| `src/hooks/usePolling.js` | Live polling hook |
| `src/components/` | Header, status bar, node cards, chart, issues, AI panel |
| `src/styles/index.css` | NOC visual system |
| `src/App.jsx` | Dashboard composition |
