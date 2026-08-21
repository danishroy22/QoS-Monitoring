"""Phase 12 — filtered Administrator QoS report payload builder."""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.speedtest import SpeedTestResult
from app.services import admin_ai, peak_hour_service, root_cause_service
from app.services.admin_service import (
    get_benchmarks,
    get_dashboard,
    get_heatmap,
    get_history,
    get_isp_analytics,
    get_package_performance,
    normalize_isp,
    region_from_label,
)
from app.services.comparison_service import compare_isps

BACKEND_DIR = Path(__file__).resolve().parents[2]
MEASUREMENT_CONFIG_PATH = BACKEND_DIR / "measurement" / "measurement_config.json"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def _parse_date(value: str | None) -> datetime | None:
    if not value:
        return None
    text = value.strip()
    try:
        if len(text) == 10:
            return datetime.fromisoformat(text).replace(tzinfo=timezone.utc)
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None


def _mean(values) -> float | None:
    nums = [float(v) for v in values if v is not None]
    if not nums:
        return None
    return round(sum(nums) / len(nums), 2)


def _load_measurement_config() -> dict[str, Any]:
    try:
        return json.loads(MEASUREMENT_CONFIG_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"version": "unknown", "note": "measurement_config.json unavailable"}


def _filter_rows(
    rows: list[SpeedTestResult],
    *,
    isp: str | None,
    package: str | None,
    region: str | None,
    date_from: str | None,
    date_to: str | None,
    days: int | None,
) -> list[SpeedTestResult]:
    start = _parse_date(date_from)
    end = _parse_date(date_to)
    if end and len((date_to or "").strip()) == 10:
        end = end + timedelta(days=1)
    if start is None and end is None and days:
        start = _utcnow() - timedelta(days=int(days))

    isp_key = normalize_isp(isp) if isp else None
    package_key = (package or "").strip().lower() or None
    region_key = (region or "").strip().lower() or None

    out: list[SpeedTestResult] = []
    for row in rows:
        ts = _aware(row.timestamp)
        if start and (ts is None or ts < start):
            continue
        if end and (ts is None or ts >= end):
            continue
        if isp_key and normalize_isp(row.isp_name) != isp_key:
            continue
        if package_key and (row.internet_package or "").strip().lower() != package_key:
            continue
        region_val = (row.detected_region or "").strip() or region_from_label(row.server_label)
        if region_key and region_val.lower() != region_key:
            continue
        out.append(row)
    return out


def _metric_series(rows: list[SpeedTestResult], attr: str) -> dict[str, Any]:
    vals = [getattr(r, attr) for r in rows if getattr(r, attr, None) is not None]
    if not vals:
        return {"count": 0, "avg": None, "min": None, "max": None}
    return {
        "count": len(vals),
        "avg": round(sum(vals) / len(vals), 2),
        "min": round(min(vals), 2),
        "max": round(max(vals), 2),
    }


def _servers_used(rows: list[SpeedTestResult]) -> list[dict[str, Any]]:
    buckets: dict[str, list[SpeedTestResult]] = defaultdict(list)
    for row in rows:
        key = row.server_label or row.server_id or "unknown"
        buckets[str(key)].append(row)
    out = []
    for label, items in sorted(buckets.items(), key=lambda kv: -len(kv[1])):
        out.append(
            {
                "server": label,
                "tests": len(items),
                "operator": items[0].server_operator,
                "location": items[0].server_location or region_from_label(label),
            }
        )
    return out[:20]


def build_report_bundle(
    db: Session,
    *,
    days: int | None = 90,
    isp: str | None = None,
    package: str | None = None,
    region: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    metric: str = "qos",
    comparison: str = "isp_vs_isp",
) -> dict[str, Any]:
    """Assemble all sections required by the Phase 12 PDF report."""
    effective_days = None if (date_from or date_to) else days
    all_rows = list(db.scalars(select(SpeedTestResult)).all())
    rows = _filter_rows(
        all_rows,
        isp=isp,
        package=package,
        region=region,
        date_from=date_from,
        date_to=date_to,
        days=effective_days,
    )

    # Unfiltered catalogue helpers for UI selects / availability.
    available_isps = sorted({normalize_isp(r.isp_name) for r in all_rows})
    available_packages = sorted(
        {(r.internet_package or "").strip() for r in all_rows if (r.internet_package or "").strip()}
    )
    available_regions = sorted(
        {
            (r.detected_region or "").strip() or region_from_label(r.server_label)
            for r in all_rows
        }
    )

    dashboard = get_dashboard(db, days=effective_days or days)
    # If filters applied, override KPIs/leaderboard from filtered rows.
    if isp or package or region or date_from or date_to:
        from app.services.admin_service import _isp_rows  # local reuse

        leaderboard = _isp_rows(rows)
        dashboard.leaderboard = leaderboard
        dashboard.kpis.total_tests = len(rows)
        dashboard.kpis.isp_count = len(leaderboard)
        dashboard.kpis.region_count = len(
            {
                (r.detected_region or "").strip() or region_from_label(r.server_label)
                for r in rows
            }
        )
        dashboard.kpis.avg_qos_score = _mean(r.overall_score for r in rows)
        dashboard.kpis.avg_download_mbps = _mean(r.download_mbps for r in rows)
        dashboard.kpis.avg_upload_mbps = _mean(r.upload_mbps for r in rows)
        dashboard.kpis.avg_ping_ms = _mean(r.ping_ms for r in rows)
        dashboard.kpis.avg_jitter_ms = _mean(r.jitter_ms for r in rows)
        dashboard.kpis.avg_packet_loss_pct = _mean(r.packet_loss_pct for r in rows)

    benchmarks = get_benchmarks(db, days=effective_days or days)
    history = get_history(db, granularity="daily", days=effective_days or days)
    heatmap = get_heatmap(db, days=effective_days or days)
    packages = get_package_performance(db, days=effective_days or days)
    peak = peak_hour_service.analyze_peak_hours(
        db,
        isp=isp,
        package=package,
        region=region,
        date_from=date_from,
        date_to=date_to,
        days=effective_days or days,
    )
    root = root_cause_service.analyze_root_cause(
        db,
        isp=isp,
        package=package,
        region=region,
        days=effective_days or days,
    )
    ai = admin_ai.generate_isp_analysis(db, days=effective_days or days)
    try:
        comparison_payload = compare_isps(
            db,
            mode=comparison,  # type: ignore[arg-type]
            package=package,
            region=region,
            date_from=date_from,
            date_to=date_to,
            days=effective_days or days,
        )
    except ValueError:
        comparison_payload = {"isps": [], "ranking_note": "Comparison unavailable for filters."}

    stamps = [_aware(r.timestamp) for r in rows if _aware(r.timestamp)]
    period = {
        "from": min(stamps).isoformat() if stamps else None,
        "to": max(stamps).isoformat() if stamps else None,
        "days": effective_days or days,
        "date_from": date_from,
        "date_to": date_to,
    }

    metric_key = {
        "download": "download_mbps",
        "upload": "upload_mbps",
        "latency": "ping_ms",
        "jitter": "jitter_ms",
        "packet_loss": "packet_loss_pct",
        "qos": "overall_score",
    }.get((metric or "qos").lower(), "overall_score")

    return {
        "dashboard": dashboard,
        "benchmarks": benchmarks,
        "history": history,
        "heatmap": heatmap,
        "packages": packages,
        "peak": peak,
        "root_cause": root,
        "ai": ai,
        "comparison": comparison_payload,
        "isp_analytics": get_isp_analytics(db, days=effective_days or days),
        "measurement_config": _load_measurement_config(),
        "servers": _servers_used(rows),
        "metric_focus": metric or "qos",
        "metric_stats": {
            "download": _metric_series(rows, "download_mbps"),
            "upload": _metric_series(rows, "upload_mbps"),
            "latency": _metric_series(rows, "ping_ms"),
            "jitter": _metric_series(rows, "jitter_ms"),
            "packet_loss": _metric_series(rows, "packet_loss_pct"),
            "qos": _metric_series(rows, "overall_score"),
        },
        "focus_series": _metric_series(rows, metric_key),
        "filters": {
            "isp": isp,
            "package": package,
            "region": region,
            "date_from": date_from,
            "date_to": date_to,
            "days": effective_days or days,
            "metric": metric or "qos",
            "comparison": comparison,
        },
        "available_isps": available_isps,
        "available_packages": available_packages,
        "available_regions": available_regions,
        "period": period,
        "total_tests": len(rows),
        "days": effective_days or days,
        "generated_at": _utcnow().isoformat(),
        "limitations": [
            "Measurements reflect end-to-end client paths to selected servers, not exclusive ISP backbone telemetry.",
            "IP-based ISP identification and region labels may be approximate.",
            "Package fulfilment requires administrator-configured advertised rates.",
            "Peak-hour / root-cause narratives are pattern explanations and do not confirm congestion.",
            "Sample sizes (n=) vary by filter; small n reduces statistical confidence.",
        ],
    }
