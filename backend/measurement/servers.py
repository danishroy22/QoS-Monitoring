"""Mauritius broadband test-server catalog for SmartQoS.

Server identity/metadata is loaded from ``mauritius_servers.json`` so new
servers can be added without UI changes. Throughput measurements use a shared
local measurement backend (not third-party branded Speedtest nodes).
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

CONFIG_PATH = Path(__file__).with_name("mauritius_servers.json")
DEFAULT_SERVER_ID = "emtel-ebene-18276"

# Shared measurement transport — not a public Speedtest brand endpoint list.
MEASUREMENT_BACKEND: dict[str, Any] = {
    "download_mode": "bytes",
    "download_base_url": "https://speed.cloudflare.com/__down",
    "upload_url": "https://speed.cloudflare.com/__up",
    "ping_host": "1.1.1.1",
    "dns_host": "cloudflare.com",
    "http_url": "https://www.cloudflare.com/cdn-cgi/trace",
    "supports_upload": True,
}


@lru_cache(maxsize=1)
def _load_raw_servers() -> tuple[dict[str, Any], ...]:
    with CONFIG_PATH.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, list) or not payload:
        raise ValueError(f"Server config at {CONFIG_PATH} must be a non-empty list")
    return tuple(payload)


def reload_servers() -> None:
    """Clear cached config (useful after editing the JSON file)."""
    _load_raw_servers.cache_clear()


def _normalize(entry: dict[str, Any]) -> dict[str, Any]:
    server_id = str(entry.get("id") or "").strip()
    if not server_id:
        raise ValueError("Each Mauritius server entry requires an id")
    host = entry.get("host")
    ping_host = MEASUREMENT_BACKEND["ping_host"]
    dns_host = MEASUREMENT_BACKEND["dns_host"]
    if isinstance(host, str) and host.strip():
        # Prefer the configured host hostname for identity / future probes.
        hostname = host.split(":")[0].strip()
        if hostname and not hostname.replace(".", "").isdigit():
            ping_host = hostname
            dns_host = hostname
    return {
        "id": server_id,
        "name": str(entry.get("name") or server_id),
        "operator": str(entry.get("operator") or entry.get("name") or server_id),
        "location": str(entry.get("location") or "Mauritius"),
        "country": str(entry.get("country") or "Mauritius"),
        "type": str(entry.get("type") or "ISP Test Server"),
        "status": str(entry.get("status") or "Online"),
        "host": host,
        "ookla_server_id": entry.get("ookla_server_id"),
        "distance_km": entry.get("distance_km"),
        "latitude": entry.get("latitude"),
        "longitude": entry.get("longitude"),
        "base_latency_ms": float(entry.get("base_latency_ms") or 20),
        **MEASUREMENT_BACKEND,
        "ping_host": ping_host,
        "dns_host": dns_host,
    }


def _catalog() -> dict[str, dict[str, Any]]:
    return {item["id"]: _normalize(item) for item in _load_raw_servers()}


def list_servers() -> list[dict[str, Any]]:
    """Public metadata for the Mauritius server picker."""
    return [
        {
            "id": s["id"],
            "name": s["name"],
            "operator": s.get("operator"),
            "location": s["location"],
            "country": s.get("country"),
            "type": s["type"],
            "status": s["status"],
            "host": s.get("host"),
            "ookla_server_id": s.get("ookla_server_id"),
            "distance_km": s.get("distance_km"),
            "latitude": s.get("latitude"),
            "longitude": s.get("longitude"),
            "supports_upload": True,
            "upload_note": None,
        }
        for s in _catalog().values()
    ]


def get_server(server_id: str | None) -> dict[str, Any]:
    catalog = _catalog()
    if not server_id or server_id not in catalog:
        return catalog.get(DEFAULT_SERVER_ID) or next(iter(catalog.values()))
    return catalog[server_id]


def probe_mauritius_servers(detected_isp: str | None = None) -> dict[str, Any]:
    """Probe catalogue hosts and score them. Replaces simulated latency ranking."""
    from measurement.server_selection import probe_and_score_servers

    payload = probe_and_score_servers(list(_catalog().values()), detected_isp=detected_isp)
    if not payload.get("best_server_id"):
        payload["best_server_id"] = DEFAULT_SERVER_ID
        catalog = _catalog()
        fallback = catalog.get(DEFAULT_SERVER_ID) or next(iter(catalog.values()), None)
        if fallback and not payload.get("best_server"):
            payload["best_server"] = {
                "id": fallback["id"],
                "name": fallback["name"],
                "location": fallback["location"],
                "type": fallback.get("type"),
                "status": fallback.get("status") or "Online",
                "host": fallback.get("host"),
                "distance_km": fallback.get("distance_km"),
                "latency_ms": None,
                "score": 0,
            }
    return payload
