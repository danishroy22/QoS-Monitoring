# SmartQoS Frontend

React + Vite Internet Quality dashboard with an animated speed-test experience.

## Run

```bash
# Terminal 1 — backend
python scripts/run_backend.py

# Terminal 2 — frontend
cd frontend
npm install
npm run dev
```

Open http://127.0.0.1:5173

## UX flow

1. **Dashboard** — score, metrics, history, AI panel, **GO**
2. **Testing** — animated speedometer + staged progress (uses `POST /speedtest`)
3. **Results** — download/upload/ping/jitter/loss, score, AI analysis

APIs are unchanged (`/dashboard`, `/speedtest`, `/recommendation`, etc.).
