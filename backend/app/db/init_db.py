"""Database initialisation: create tables and seed default nodes.

The default nodes are imported from the Phase 2 simulator so the topology
stays consistent across the simulator, database, and dashboard.
"""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.models.network import NetworkNode
from app.models import speedtest as _speedtest_model  # noqa: F401 — register table

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


def init_db(seed: bool = True) -> None:
    """Create tables and optionally seed default nodes."""
    create_tables()
    if seed:
        with SessionLocal() as db:
            count = seed_nodes(db)
            if count:
                logger.info("Seeded %s default network nodes", count)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    init_db(seed=True)
    print("Database initialised.")
