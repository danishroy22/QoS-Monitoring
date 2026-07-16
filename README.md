# AI-Driven Broadband Network QoS Monitoring Platform

Final year dissertation project:

**AI-Driven Broadband Network Quality of Service (QoS) Monitoring, Analysis and Performance Optimisation using Generative AI**

This project implements a simplified Network Operations Centre (NOC) platform for broadband QoS monitoring. It uses a realistic network simulator, a Python FastAPI backend, PostgreSQL time-series storage, anomaly detection, and Generative AI explanations.

## Objectives

1. Simulate broadband network QoS measurements.
2. Collect and analyse latency, jitter, packet loss, throughput, bandwidth utilisation, signal quality, and availability.
3. Build a Python backend for ingestion, processing, anomaly detection, and AI-assisted analysis.
4. Build a web dashboard for live metrics, historical trends, health status, detected issues, and recommendations.
5. Integrate Generative AI to explain network degradation and suggest corrective actions.

## Recommended Stack

- **Frontend:** React, Vite, Chart.js
- **Backend:** Python, FastAPI, SQLAlchemy, Pydantic
- **Database:** PostgreSQL
- **ML:** scikit-learn Isolation Forest baseline, with optional Autoencoder or Random Forest extension
- **AI:** OpenAI-compatible LLM API, with rule-based fallback for offline demonstrations
- **Testing:** pytest, FastAPI TestClient, frontend component tests, simulator scenario validation

## High-Level Architecture

```mermaid
flowchart LR
    Simulator[QoS Simulator] --> API[FastAPI Ingestion API]
    API --> DB[(PostgreSQL)]
    DB --> Processor[Processing and Feature Pipeline]
    Processor --> ML[Anomaly Detection]
    ML --> Events[Anomaly Events]
    Events --> AI[Generative AI Explanation Service]
    DB --> Dashboard[React NOC Dashboard]
    Events --> Dashboard
    AI --> Dashboard
```

## Folder Structure

```text
FYP/
  backend/
    app/
      api/
      core/
      db/
      models/
      schemas/
      services/
      main.py
    ml/
      features/
      models/
      training/
    simulator/
      scenarios/
      generator.py
    tests/
  frontend/
    src/
      components/
      pages/
      services/
      charts/
      styles/
    public/
  database/
    schema.sql
    seed.sql
  docs/
    architecture.md
    api-design.md
    database-schema.md
    roadmap.md
    testing-methodology.md
  scripts/
```

## Development Phases

1. **Phase 1: Architecture and structure**
   Define architecture, data model, APIs, folder layout, simulation scenarios, and testing approach.

2. **Phase 2: QoS simulator**
   Generate realistic broadband metrics for normal service, congestion, latency spikes, packet loss, bandwidth limits, and outage scenarios.

3. **Phase 3: Backend and database**
   Implement FastAPI ingestion, PostgreSQL persistence, and historical metric query endpoints.

4. **Phase 4: ML anomaly detection**
   Add feature engineering and Isolation Forest anomaly detection, then evaluate against simulator ground truth.

5. **Phase 5: Dashboard**
   Build a responsive React dashboard with live health cards, charts, event lists, and recommendations.

6. **Phase 6: Generative AI analysis**
   Add natural-language performance summaries, likely causes, and corrective actions.

7. **Phase 7: Testing and dissertation documentation**
   Validate the system, collect results, create screenshots, write evaluation, and prepare dissertation material.

## First Build Milestone

The first working version should run locally with:

- One simulator process producing QoS measurements every few seconds.
- One FastAPI backend receiving and storing measurements.
- One React dashboard polling latest metrics.
- One ML service flagging obvious anomalies.
- One AI endpoint summarising the latest network condition.
