"""Automatic measurement-server selection (Phase 1).

Probes catalogue hosts with TCP connect RTT (ICMP is often blocked on
Windows). Scores candidates with documented, configurable weights.
ISP name overlap is a small bonus — never a hard assignment rule.
"""

from __future__ import annotations

import json
import logging
import socket
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import lru_cache
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

CONFIG_PATH = Path(__file__).with_name("server_selection.json")

ISP_TOKENS = (
    "emtel",
    "orange",
    "mauritius telecom",
    "rogers",
    "bharat",
)


@lru_cache(maxsize=1)
def load_selection_config() -> dict[str, Any]:
    with CONFIG_PATH.open(encoding="utf-8") as handle:
        return json.load(handle)


def reload_selection_config() -> None:
    load_selection_config.cache_clear()


def parse_host_port(host: str | None, default_port: int = 443) -> tuple[str | None, int]:
    if not host or not str(host).strip():
        return None, default_port
    raw = str(host).strip()
    if "://" in raw:
        raw = raw.split("://", 1)[1]
    raw = raw.split("/")[0]
    if ":" in raw:
        name, port_s = raw.rsplit(":", 1)
        try:
            return name.strip() or None, int(port_s)
        except ValueError:
            return name.strip() or None, default_port
    return raw, default_port


def isp_affinity(detected_isp: str | None, *labels: str | None) -> bool:
    """True when a known operator token appears in both the detected ISP and server labels."""
    detected = (detected_isp or "").strip().lower()
    if not detected:
        return False
    blob = " ".join(str(x).lower() for x in labels if x)
    return any(token in detected and token in blob for token in ISP_TOKENS)


def score_candidate(
    *,
    latency_ms: float | None,
    packet_loss_pct: float | None,
    distance_km: float | int | None,
    online: bool,
    affinity: bool,
    weights: dict[str, float] | None = None,
    caps: dict[str, float] | None = None,
) -> float:
    """Return 0–100 composite score. Unreachable or offline servers score 0."""
    cfg = load_selection_config()
    weights = weights or cfg["weights"]
    caps = caps or cfg["caps"]
    if not online:
        return 0.0
    if latency_ms is None:
        return 0.0

    lat_cap = float(caps.get("latency_ms") or 80)
    dist_cap = float(caps.get("distance_km") or 40)
    latency_score = max(0.0, 100.0 * (1.0 - min(float(latency_ms), lat_cap) / lat_cap))
    loss = 0.0 if packet_loss_pct is None else float(packet_loss_pct)
    loss_score = max(0.0, 100.0 * (1.0 - min(loss, 100.0) / 100.0))
    if distance_km is None:
        proximity_score = 50.0
    else:
        proximity_score = max(0.0, 100.0 * (1.0 - min(float(distance_km), dist_cap) / dist_cap))
    status_score = 100.0
    affinity_score = 100.0 if affinity else 0.0

    total_w = sum(float(weights.get(k, 0.0)) for k in ("latency", "packet_loss", "proximity", "status", "isp_affinity"))
    if total_w <= 0:
        total_w = 1.0
    composite = (
        latency_score * float(weights.get("latency", 0))
        + loss_score * float(weights.get("packet_loss", 0))
        + proximity_score * float(weights.get("proximity", 0))
        + status_score * float(weights.get("status", 0))
        + affinity_score * float(weights.get("isp_affinity", 0))
    ) / total_w
    return round(composite, 2)


def tcp_probe(
    hostname: str,
    port: int,
    *,
    samples: int,
    timeout: float,
) -> dict[str, Any]:
    rtts: list[float] = []
    failures = 0
    for _ in range(max(1, samples)):
        started = time.perf_counter()
        try:
            socket.create_connection((hostname, port), timeout=timeout).close()
            rtts.append((time.perf_counter() - started) * 1000.0)
        except OSError:
            failures += 1
    sent = max(1, samples)
    if not rtts:
        return {
            "latency_ms": None,
            "packet_loss_pct": 100.0,
            "packets_sent": sent,
            "packets_received": 0,
            "probe_method": "tcp_connect",
            "reachable": False,
        }
    return {
        "latency_ms": round(sum(rtts) / len(rtts), 1),
        "packet_loss_pct": round((failures / sent) * 100.0, 1),
        "packets_sent": sent,
        "packets_received": len(rtts),
        "probe_method": "tcp_connect",
        "reachable": True,
    }


def probe_and_score_servers(
    servers: list[dict[str, Any]],
    *,
    detected_isp: str | None = None,
) -> dict[str, Any]:
    """Probe catalogue servers and return ranked results."""
    cfg = load_selection_config()
    probe_cfg = cfg.get("probe") or {}
    samples = int(probe_cfg.get("samples") or 2)
    timeout = float(probe_cfg.get("timeout_seconds") or 1.8)
    workers = int(probe_cfg.get("max_workers") or 8)

    def _one(server: dict[str, Any]) -> dict[str, Any]:
        online = str(server.get("status") or "Online").lower() == "online"
        hostname, port = parse_host_port(server.get("host"))
        probe: dict[str, Any]
        if not online or not hostname:
            probe = {
                "latency_ms": None,
                "packet_loss_pct": None,
                "packets_sent": 0,
                "packets_received": 0,
                "probe_method": "skipped",
                "reachable": False,
            }
        else:
            probe = tcp_probe(hostname, port, samples=samples, timeout=timeout)
        affinity = isp_affinity(
            detected_isp,
            server.get("operator"),
            server.get("name"),
        )
        score = score_candidate(
            latency_ms=probe.get("latency_ms"),
            packet_loss_pct=probe.get("packet_loss_pct"),
            distance_km=server.get("distance_km"),
            online=online,
            affinity=affinity,
        )
        return {
            "id": server["id"],
            "name": server["name"],
            "location": server.get("location"),
            "type": server.get("type"),
            "status": server.get("status") or "Online",
            "host": server.get("host"),
            "operator": server.get("operator") or server.get("name"),
            "distance_km": server.get("distance_km"),
            "latency_ms": probe.get("latency_ms") if probe.get("latency_ms") is not None else 9999.0,
            "measured_latency_ms": probe.get("latency_ms"),
            "packet_loss_pct": probe.get("packet_loss_pct"),
            "score": score,
            "isp_affinity": affinity,
            "reachable": probe.get("reachable"),
            "probe_method": probe.get("probe_method"),
        }

    results: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        futures = [pool.submit(_one, server) for server in servers]
        for fut in as_completed(futures):
            try:
                results.append(fut.result())
            except Exception as exc:  # noqa: BLE001
                logger.warning("Server probe failed: %s", exc)

    results.sort(key=lambda row: (-float(row.get("score") or 0), float(row.get("latency_ms") or 9999)))
    reachable = [row for row in results if row.get("reachable") and (row.get("score") or 0) > 0]
    best = reachable[0] if reachable else (results[0] if results else None)

    # API compatibility: latency_ms must be a float; keep 9999 only internally then map
    public: list[dict[str, Any]] = []
    for row in results:
        item = dict(row)
        if item.get("measured_latency_ms") is None:
            item["latency_ms"] = item.get("measured_latency_ms")
        else:
            item["latency_ms"] = item["measured_latency_ms"]
        public.append(item)

    # Sort public list by score; unreachable last
    public.sort(
        key=lambda row: (
            0 if row.get("reachable") else 1,
            -(row.get("score") or 0),
            row.get("latency_ms") if row.get("latency_ms") is not None else 9999,
        )
    )
    best_public = next((row for row in public if row.get("reachable")), public[0] if public else None)
    return {
        "probes": public,
        "best_server_id": best_public["id"] if best_public else None,
        "best_server": best_public,
        "weights": cfg.get("weights"),
        "detected_isp": detected_isp,
    }
