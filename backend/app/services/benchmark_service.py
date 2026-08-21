"""Multi-profile QoS benchmark catalogue."""

from __future__ import annotations

import json
import logging
from copy import deepcopy
from pathlib import Path
from typing import Any

from app.schemas.admin import (
    BenchmarkMetricThreshold,
    BenchmarkProfile,
    BenchmarkProfileDetail,
    BenchmarkProfilesResponse,
)

logger = logging.getLogger(__name__)

BACKEND_DIR = Path(__file__).resolve().parents[2]
PROFILES_PATH = BACKEND_DIR / "app" / "qos_benchmark_profiles.json"
LEGACY_PATH = BACKEND_DIR / "app" / "qos_benchmarks.json"

METRIC_KEYS = (
    "download_mbps",
    "upload_mbps",
    "ping_ms",
    "jitter_ms",
    "packet_loss_pct",
    "dns_lookup_ms",
    "overall_score",
)


def _empty_metric(key: str, threshold: float, unit: str) -> dict[str, Any]:
    return {
        "threshold": threshold,
        "unit": unit,
        "source": "Administrator override",
        "rationale": "Configured by administrator; not a universal standard.",
        "description": f"Threshold for {key}.",
    }


def _legacy_to_catalog(payload: dict[str, Any]) -> dict[str, Any]:
    metrics = {
        "download_mbps": _empty_metric("download_mbps", float(payload.get("download_mbps", 100)), "Mbps"),
        "upload_mbps": _empty_metric("upload_mbps", float(payload.get("upload_mbps", 20)), "Mbps"),
        "ping_ms": _empty_metric("ping_ms", float(payload.get("ping_ms", 20)), "ms"),
        "jitter_ms": _empty_metric("jitter_ms", float(payload.get("jitter_ms", 5)), "ms"),
        "packet_loss_pct": _empty_metric(
            "packet_loss_pct", float(payload.get("packet_loss_pct", 0.5)), "%"
        ),
        "dns_lookup_ms": _empty_metric("dns_lookup_ms", 50.0, "ms"),
        "overall_score": _empty_metric(
            "overall_score", float(payload.get("overall_score", 85)), "/100"
        ),
    }
    return {
        "active_profile_id": "legacy-ideal",
        "disclaimer": (
            "Migrated from the single Ideal Broadband Profile. Thresholds are "
            "configurable and not universal standards."
        ),
        "profiles": [
            {
                "id": "legacy-ideal",
                "name": payload.get("name") or "Ideal Broadband Profile",
                "description": payload.get("description")
                or "Legacy single-profile benchmark migrated in Phase 7.",
                "metrics": metrics,
            }
        ],
    }


def load_catalog() -> dict[str, Any]:
    if PROFILES_PATH.exists():
        try:
            payload = json.loads(PROFILES_PATH.read_text(encoding="utf-8"))
            if isinstance(payload, dict) and payload.get("profiles"):
                return payload
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            logger.warning("Could not load benchmark profiles: %s", exc)
    if LEGACY_PATH.exists():
        try:
            legacy = json.loads(LEGACY_PATH.read_text(encoding="utf-8"))
            if isinstance(legacy, dict) and "download_mbps" in legacy:
                catalog = _legacy_to_catalog(legacy)
                save_catalog(catalog)
                return catalog
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            logger.warning("Could not migrate legacy benchmarks: %s", exc)
    # Fall back to shipping defaults file if present next to this module.
    defaults = Path(__file__).with_name("qos_benchmark_profiles.json")
    if defaults.exists():
        return json.loads(defaults.read_text(encoding="utf-8"))
    return {
        "active_profile_id": "general-broadband",
        "disclaimer": "No profiles configured.",
        "profiles": [],
    }


def save_catalog(catalog: dict[str, Any]) -> dict[str, Any]:
    PROFILES_PATH.parent.mkdir(parents=True, exist_ok=True)
    PROFILES_PATH.write_text(json.dumps(catalog, indent=2), encoding="utf-8")
    # Keep legacy file in sync for older readers (flat active thresholds).
    active = get_profile(catalog.get("active_profile_id"), catalog=catalog)
    if active is not None:
        flat = profile_to_flat(active)
        LEGACY_PATH.write_text(json.dumps(flat.model_dump(), indent=2), encoding="utf-8")
    return catalog


def get_profile(profile_id: str | None, *, catalog: dict[str, Any] | None = None) -> dict[str, Any] | None:
    data = catalog or load_catalog()
    wanted = (profile_id or data.get("active_profile_id") or "").strip()
    for profile in data.get("profiles") or []:
        if profile.get("id") == wanted:
            return deepcopy(profile)
    profiles = data.get("profiles") or []
    return deepcopy(profiles[0]) if profiles else None


def profile_to_flat(profile: dict[str, Any]) -> BenchmarkProfile:
    metrics = profile.get("metrics") or {}

    def thr(key: str, default: float) -> float:
        block = metrics.get(key) or {}
        try:
            return float(block.get("threshold", default))
        except (TypeError, ValueError):
            return default

    return BenchmarkProfile(
        name=str(profile.get("name") or "Benchmark Profile"),
        description=profile.get("description"),
        download_mbps=thr("download_mbps", 100),
        upload_mbps=thr("upload_mbps", 20),
        ping_ms=thr("ping_ms", 20),
        jitter_ms=thr("jitter_ms", 5),
        packet_loss_pct=thr("packet_loss_pct", 0.5),
        overall_score=int(round(thr("overall_score", 85))),
    )


def _to_detail(profile: dict[str, Any]) -> BenchmarkProfileDetail:
    metrics = {}
    for key, block in (profile.get("metrics") or {}).items():
        metrics[key] = BenchmarkMetricThreshold.model_validate(block)
    return BenchmarkProfileDetail(
        id=str(profile["id"]),
        name=str(profile.get("name") or profile["id"]),
        description=profile.get("description"),
        metrics=metrics,
    )


def list_profiles() -> BenchmarkProfilesResponse:
    catalog = load_catalog()
    profiles = [_to_detail(p) for p in catalog.get("profiles") or []]
    active_id = catalog.get("active_profile_id") or (profiles[0].id if profiles else "")
    active = next((p for p in profiles if p.id == active_id), profiles[0] if profiles else None)
    return BenchmarkProfilesResponse(
        active_profile_id=active_id,
        disclaimer=str(
            catalog.get("disclaimer")
            or "Thresholds are configurable and not universal standards."
        ),
        profiles=profiles,
        active=active,
    )


def set_active_profile(profile_id: str) -> BenchmarkProfilesResponse:
    catalog = load_catalog()
    ids = {p.get("id") for p in catalog.get("profiles") or []}
    if profile_id not in ids:
        raise ValueError(f"Unknown profile id '{profile_id}'")
    catalog["active_profile_id"] = profile_id
    save_catalog(catalog)
    return list_profiles()


def update_profile(profile_id: str, detail: BenchmarkProfileDetail) -> BenchmarkProfilesResponse:
    catalog = load_catalog()
    found = False
    for idx, profile in enumerate(catalog.get("profiles") or []):
        if profile.get("id") != profile_id:
            continue
        found = True
        metrics = {
            key: detail.metrics[key].model_dump()
            for key in detail.metrics
        }
        catalog["profiles"][idx] = {
            "id": profile_id,
            "name": detail.name.strip() or profile_id,
            "description": detail.description,
            "metrics": metrics,
        }
        break
    if not found:
        raise ValueError(f"Unknown profile id '{profile_id}'")
    save_catalog(catalog)
    return list_profiles()


def active_flat_profile() -> BenchmarkProfile:
    profile = get_profile(None)
    if profile is None:
        return BenchmarkProfile()
    return profile_to_flat(profile)
