"""FastAPI application for the Internet Quality platform."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import admin, analyze, anomalies, health, internet, measurements, metrics, monitoring
from app.core.config import get_settings
from app.db.init_db import init_db
from app.services.monitoring_service import start_scheduler, stop_scheduler

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.db.session import active_database_url, _redact_url

    settings = get_settings()
    logger.info("Initialising database (%s)", _redact_url(active_database_url))
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

    app.include_router(internet.router)
    app.include_router(monitoring.router)
    app.include_router(admin.router)
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
            "admin": "GET /admin/dashboard",
        }

    return app


app = create_app()
