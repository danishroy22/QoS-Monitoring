"""FastAPI application factory for the AI Internet Quality platform.

Primary product surface (Ookla-style):
  POST /speedtest, GET /history, GET /dashboard, GET /statistics,
  GET /isp, GET /recommendation, GET /health

Legacy NOC simulator APIs remain under /api/* for dissertation continuity.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import analyze, anomalies, health, internet, measurements, metrics, monitoring
from app.core.config import get_settings
from app.db.init_db import init_db
from app.services.monitoring_service import start_scheduler, stop_scheduler

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    logger.info("Initialising database (%s)", settings.database_url)
    init_db(seed=settings.seed_nodes)
    start_scheduler()
    yield
    stop_scheduler()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="AI-Driven Internet Quality & Broadband QoS Platform",
        version="1.0.0",
        description=(
            "Real network measurement engine, QoS health scoring, historical "
            "analytics, and an AI Network Assistant — with legacy NOC APIs under /api."
        ),
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Primary Internet Quality API (Phases 2–6 redesign)
    app.include_router(internet.router)
    # Phase 7 — Continuous QoS Monitoring
    app.include_router(monitoring.router)
    # Keep a single health endpoint from the dedicated health router as well
    # (internet.router also exposes /health — FastAPI will use the first match).
    # Legacy simulated NOC platform
    prefix = settings.api_prefix
    app.include_router(health.router)
    app.include_router(measurements.router, prefix=prefix)
    app.include_router(metrics.router, prefix=prefix)
    app.include_router(anomalies.router, prefix=prefix)
    app.include_router(analyze.router, prefix=prefix)

    @app.get("/", tags=["root"])
    def root() -> dict[str, str]:
        return {
            "service": settings.app_name,
            "docs": "/docs",
            "health": "/health",
            "dashboard": "/dashboard",
            "speedtest": "POST /speedtest",
            "monitoring": "GET /monitoring/status",
        }

    return app


app = create_app()
