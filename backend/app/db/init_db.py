"""Database initialisation: create tables and seed default nodes.

The default nodes are imported from the Phase 2 simulator so the topology
stays consistent across the simulator, database, and dashboard.
"""

from __future__ import annotations

import logging

from sqlalchemy import inspect, select, text
from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.models.network import NetworkNode
from app.models import speedtest as _speedtest_model  # noqa: F401 — register table
from app.models import monitoring as _monitoring_model  # noqa: F401 — register table

logger = logging.getLogger(__name__)


def create_tables() -> None:
    """Create all tables that do not yet exist."""
    Base.metadata.create_all(bind=engine)


def _default_nodes() -> list[dict]:
    """Load default node definitions from the simulator catalogue."""
    try:
        from backend.simulator.nodes import get_default_nodes
    except ImportError:  # pragma: no cover - fallback when run as installed pkg
        from simulator.nodes import get_default_nodes  # type: ignore

    nodes = []
    for node in get_default_nodes():
        nodes.append(
            {
                "node_code": node.node_code,
                "region": node.region,
                "access_technology": node.access_technology,
                "service_tier_mbps": node.service_tier_mbps,
                "subscriber_count": node.subscriber_count,
                "baseline_latency_ms": node.baseline_latency_ms,
                "max_bandwidth_mbps": node.max_bandwidth_mbps,
            }
        )
    return nodes


def seed_nodes(db: Session) -> int:
    """Insert default nodes if they are not already present. Returns count added."""
    added = 0
    for node_data in _default_nodes():
        exists = db.scalar(
            select(NetworkNode).where(NetworkNode.node_code == node_data["node_code"])
        )
        if exists is None:
            db.add(NetworkNode(**node_data))
            added += 1
    if added:
        db.commit()
    return added


def ensure_speed_test_columns() -> None:
    """Add nullable Phase 1–2 columns to existing SQLite/Postgres speed_tests tables."""
    inspector = inspect(engine)
    if "speed_tests" not in inspector.get_table_names():
        return
    existing = {col["name"] for col in inspector.get_columns("speed_tests")}
    statements = {
        "detected_region": "ALTER TABLE speed_tests ADD COLUMN detected_region VARCHAR(120)",
        "detected_city": "ALTER TABLE speed_tests ADD COLUMN detected_city VARCHAR(120)",
        "latitude": "ALTER TABLE speed_tests ADD COLUMN latitude FLOAT",
        "longitude": "ALTER TABLE speed_tests ADD COLUMN longitude FLOAT",
        "server_id": "ALTER TABLE speed_tests ADD COLUMN server_id VARCHAR(80)",
        "selection_mode": "ALTER TABLE speed_tests ADD COLUMN selection_mode VARCHAR(20)",
        "selection_score": "ALTER TABLE speed_tests ADD COLUMN selection_score FLOAT",
        "ping_min_ms": "ALTER TABLE speed_tests ADD COLUMN ping_min_ms FLOAT",
        "ping_max_ms": "ALTER TABLE speed_tests ADD COLUMN ping_max_ms FLOAT",
        "ping_median_ms": "ALTER TABLE speed_tests ADD COLUMN ping_median_ms FLOAT",
        "packets_sent": "ALTER TABLE speed_tests ADD COLUMN packets_sent INTEGER",
        "packets_received": "ALTER TABLE speed_tests ADD COLUMN packets_received INTEGER",
        "packets_lost": "ALTER TABLE speed_tests ADD COLUMN packets_lost INTEGER",
        "latency_samples_json": "ALTER TABLE speed_tests ADD COLUMN latency_samples_json TEXT",
        "download_bytes": "ALTER TABLE speed_tests ADD COLUMN download_bytes INTEGER",
        "download_duration_s": "ALTER TABLE speed_tests ADD COLUMN download_duration_s FLOAT",
        "download_connections": "ALTER TABLE speed_tests ADD COLUMN download_connections INTEGER",
        "download_peak_mbps": "ALTER TABLE speed_tests ADD COLUMN download_peak_mbps FLOAT",
        "upload_bytes": "ALTER TABLE speed_tests ADD COLUMN upload_bytes INTEGER",
        "upload_duration_s": "ALTER TABLE speed_tests ADD COLUMN upload_duration_s FLOAT",
        "upload_connections": "ALTER TABLE speed_tests ADD COLUMN upload_connections INTEGER",
        "upload_peak_mbps": "ALTER TABLE speed_tests ADD COLUMN upload_peak_mbps FLOAT",
        "dns_ok": "ALTER TABLE speed_tests ADD COLUMN dns_ok BOOLEAN",
        "dns_resolver": "ALTER TABLE speed_tests ADD COLUMN dns_resolver VARCHAR(80)",
        "tcp_connect_ms": "ALTER TABLE speed_tests ADD COLUMN tcp_connect_ms FLOAT",
        "tls_handshake_ms": "ALTER TABLE speed_tests ADD COLUMN tls_handshake_ms FLOAT",
        "http_ok": "ALTER TABLE speed_tests ADD COLUMN http_ok BOOLEAN",
        "measurement_config_version": "ALTER TABLE speed_tests ADD COLUMN measurement_config_version VARCHAR(20)",
    }
    with engine.begin() as conn:
        for name, sql in statements.items():
            if name not in existing:
                conn.execute(text(sql))
                logger.info("Added speed_tests.%s", name)


def init_db(seed: bool = True) -> None:
    """Create tables and optionally seed default nodes."""
    create_tables()
    ensure_speed_test_columns()
    if seed:
        with SessionLocal() as db:
            count = seed_nodes(db)
            if count:
                logger.info("Seeded %s default network nodes", count)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    init_db(seed=True)
    print("Database initialised.")
