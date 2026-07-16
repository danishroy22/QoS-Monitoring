"""FastAPI application factory for the broadband QoS monitoring backend.

Run locally from the repository root (d:\\FYP):

    uvicorn backend.app.main:app --reload

or via the helper script:

    python scripts/run_backend.py
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import analyze, anomalies, health, measurements, metrics
from app.core.config import get_settings
from app.db.init_db import init_db

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    logger.info("Initialising database (%s)", settings.database_url)
    init_db(seed=settings.seed_nodes)
    yield


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()
    app = FastAPI(
        title="AI-Driven Broadband QoS Monitoring API",
        version="0.3.0",
        description=(
            "Backend for a simplified NOC platform: QoS ingestion, storage, and "
            "metric queries. Anomaly detection (Phase 4) and Generative AI "
            "analysis (Phase 6) extend this API."
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
        }

    return app


app = create_app()
