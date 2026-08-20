"""Administrator analytics over existing ``speed_tests`` rows (Phase 18).

Read-only aggregations for the ISP portal. Does not change measurement or
consumer speed-test APIs.
"""

from __future__ import annotations

import json
import logging
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.monitoring import MonitoringState
from app.models.speedtest import SpeedTestResult
from app.schemas.admin import (
    AdminDashboardResponse,
    AdminKpis,
    AdminLiveStats,
    BenchmarkProfile,
    BenchmarkResponse,
    HeatmapCell,
    HeatmapResponse,
    HistoryAnalyticsResponse,
    HistoryPoint,
    IspAnalyticsResponse,
    IspBenchmarkRow,
    IspMetricRow,
    MetricCompliance,
    QosBucket,
)
from measurement.qos_analysis import rating_from_score

logger = logging.getLogger(__name__)

BACKEND_DIR = Path(__file__).resolve().parents[2]
BENCHMARK_PATH = BACKEND_DIR / "app" / "qos_benchmarks.json"

KNOWN_REGIONS = (
    ("la tour", "La Tour Koenig"),
    ("port louis", "Port Louis"),
    ("rose-hill", "Rose Hill"),
    ("rose hill", "Rose Hill"),
    ("arsenal", "Arsenal"),
    ("ebene", "Ebene"),
    ("floreal", "Floreal"),
)

ISP_ALIASES = (
    ("emtel", "Emtel"),
    ("bharat", "Bharat Telecom"),
    ("rogers", "Rogers"),
    ("mauritius telecom", "Mauritius Telecom / Orange"),
    ("orange", "Mauritius Telecom / Orange"),
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def _mean(values: Iterable[float | int | None]) -> float | None:
    nums = [float(v) for v in values if v is not None]
    if not nums:
        return None
    return round(sum(nums) / len(nums), 2)


def _pct(part: int, whole: int) -> float:
    if whole <= 0:
        return 0.0
    return round((part / whole) * 100.0, 1)


def normalize_isp(name: str | None) -> str:
    """Collapse noisy ip-api / server names into stable ISP brands."""
    raw = (name or "").strip()
    if not raw:
        return "Unknown"
    key = raw.lower()
    for needle, label in ISP_ALIASES:
        if needle in key:
            return label
    return raw


def region_from_label(label: str | None) -> str:
    """Map ``server_label`` (e.g. 'Emtel Ltd · Ebene') to a Mauritius region."""
    text = (label or "").strip()
    if not text:
        return "Unknown"
    lowered = text.lower()
    for needle, region in KNOWN_REGIONS:
        if needle in lowered:
            return region
    if "·" in text:
        tail = text.split("·")[-1].strip()
        if tail:
            return tail
    return "Unknown"


def _load_rows(db: Session, *, days: int | None) -> list[SpeedTestResult]:
    stmt = select(SpeedTestResult).order_by(SpeedTestResult.timestamp.asc())
    if days:
        cutoff = _utcnow() - timedelta(days=days)
        stmt = stmt.where(SpeedTestResult.timestamp >= cutoff)
    return list(db.scalars(stmt))


def _isp_rows(rows: list[SpeedTestResult]) -> list[IspMetricRow]:
    buckets: dict[str, list[SpeedTestResult]] = defaultdict(list)
    for row in rows:
        buckets[normalize_isp(row.isp_name)].append(row)

    out: list[IspMetricRow] = []
    for isp, items in buckets.items():
        latest = max(items, key=lambda r: _aware(r.timestamp) or datetime.min.replace(tzinfo=timezone.utc))
        scores = [int(r.overall_score) for r in items if r.overall_score is not None]
        out.append(
            IspMetricRow(
                isp=isp,
                tests=len(items),
                avg_download_mbps=_mean(r.download_mbps for r in items),
                avg_upload_mbps=_mean(r.upload_mbps for r in items),
                avg_ping_ms=_mean(r.ping_ms for r in items),
                avg_jitter_ms=_mean(r.jitter_ms for r in items),
                avg_packet_loss_pct=_mean(r.packet_loss_pct for r in items),
                avg_qos_score=_mean(r.overall_score for r in items),
                avg_dns_lookup_ms=_mean(r.dns_lookup_ms for r in items),
                avg_http_response_ms=_mean(r.http_response_ms for r in items),
                best_score=max(scores) if scores else None,
                worst_score=min(scores) if scores else None,
                latest_rating=latest.overall_rating,
            )
        )
    out.sort(
        key=lambda r: (
            -(r.avg_qos_score if r.avg_qos_score is not None else -1),
            -r.tests,
        )
    )
    for index, row in enumerate(out, start=1):
        row.rank = index
    return out


def get_dashboard(db: Session, *, days: int | None = 90) -> AdminDashboardResponse:
    rows = _load_rows(db, days=days)
    now = _utcnow()
    day_ago = now - timedelta(hours=24)
    tests_24h = sum(1 for r in rows if (_aware(r.timestamp) or now) >= day_ago)
    excellent = sum(1 for r in rows if (r.overall_rating or "").lower() == "excellent")
    leaderboard = _isp_rows(rows)

    rating_counts: dict[str, int] = defaultdict(int)
    for row in rows:
        rating_counts[row.overall_rating or "Unknown"] += 1
    order = ["Excellent", "Good", "Fair", "Poor", "Critical", "Unknown"]
    overview = [
        QosBucket(rating=name, count=rating_counts.get(name, 0), pct=_pct(rating_counts.get(name, 0), len(rows)))
        for name in order
        if rating_counts.get(name, 0) or name in ("Excellent", "Good", "Fair", "Poor", "Critical")
    ]

    latest = rows[-1] if rows else None
    monitoring = db.get(MonitoringState, 1)
    live = AdminLiveStats(
        monitoring_enabled=bool(monitoring and monitoring.enabled),
        monitoring_running=bool(monitoring and monitoring.running),
        last_isp=normalize_isp(latest.isp_name) if latest else None,
        last_region=region_from_label(latest.server_label) if latest else None,
        last_score=latest.overall_score if latest else None,
        last_rating=latest.overall_rating if latest else None,
    )

    kpis = AdminKpis(
        total_tests=len(rows),
        isp_count=len(leaderboard),
        region_count=len({region_from_label(r.server_label) for r in rows}),
        tests_24h=tests_24h,
        avg_qos_score=_mean(r.overall_score for r in rows),
        avg_download_mbps=_mean(r.download_mbps for r in rows),
        avg_upload_mbps=_mean(r.upload_mbps for r in rows),
        avg_ping_ms=_mean(r.ping_ms for r in rows),
        avg_jitter_ms=_mean(r.jitter_ms for r in rows),
        avg_packet_loss_pct=_mean(r.packet_loss_pct for r in rows),
        excellent_pct=_pct(excellent, len(rows)) if rows else None,
        last_test_at=_aware(latest.timestamp) if latest else None,
    )
    return AdminDashboardResponse(
        kpis=kpis,
        live=live,
        leaderboard=leaderboard,
        qos_overview=overview,
        generated_at=now,
    )


def get_isp_analytics(db: Session, *, days: int | None = 90) -> IspAnalyticsResponse:
    rows = _load_rows(db, days=days)
    return IspAnalyticsResponse(isps=_isp_rows(rows), generated_at=_utcnow())


def default_profile() -> BenchmarkProfile:
    from app.services.benchmark_service import active_flat_profile

    try:
        return active_flat_profile()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Could not load active benchmark profile: %s", exc)
    if BENCHMARK_PATH.exists():
        try:
            payload = json.loads(BENCHMARK_PATH.read_text(encoding="utf-8"))
            return BenchmarkProfile.model_validate(payload)
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            logger.warning("Could not load QoS benchmarks: %s", exc)
    return BenchmarkProfile()


def save_profile(profile: BenchmarkProfile) -> BenchmarkProfile:
    """Update the active profile's numeric thresholds (legacy flat editor)."""
    from app.services import benchmark_service

    catalog = benchmark_service.load_catalog()
    active = benchmark_service.get_profile(catalog.get("active_profile_id"), catalog=catalog)
    if active is None:
        BENCHMARK_PATH.parent.mkdir(parents=True, exist_ok=True)
        BENCHMARK_PATH.write_text(
            json.dumps(profile.model_dump(), indent=2),
            encoding="utf-8",
        )
        return profile

    metrics = active.setdefault("metrics", {})
    mapping = {
        "download_mbps": profile.download_mbps,
        "upload_mbps": profile.upload_mbps,
        "ping_ms": profile.ping_ms,
        "jitter_ms": profile.jitter_ms,
        "packet_loss_pct": profile.packet_loss_pct,
        "overall_score": float(profile.overall_score),
    }
    for key, value in mapping.items():
        block = metrics.get(key) or {
            "unit": "Mbps",
            "source": "Administrator override",
            "rationale": "Configured by administrator; not a universal standard.",
            "description": f"Threshold for {key}.",
        }
        block["threshold"] = float(value)
        metrics[key] = block
    active["name"] = profile.name
    active["description"] = profile.description
    active["metrics"] = metrics
    for idx, item in enumerate(catalog.get("profiles") or []):
        if item.get("id") == active.get("id"):
            catalog["profiles"][idx] = active
            break
    benchmark_service.save_catalog(catalog)
    return profile


def _compliance(
    *,
    metric: str,
    unit: str,
    target: float,
    actual: float | None,
    samples: list[float | None],
    higher_is_better: bool,
) -> MetricCompliance:
    meets: bool | None = None
    gap: float | None = None
    if actual is not None:
        meets = actual >= target if higher_is_better else actual <= target
        gap = round(actual - target, 2)
    valid = [float(v) for v in samples if v is not None]
    if valid:
        ok = sum(1 for v in valid if (v >= target if higher_is_better else v <= target))
        compliance = _pct(ok, len(valid))
    else:
        compliance = None
    return MetricCompliance(
        metric=metric,
        unit=unit,
        target=target,
        actual=actual,
        higher_is_better=higher_is_better,
        meets_target=meets,
        gap=gap,
        compliance_pct=compliance,
    )


def _composite(metrics: list[MetricCompliance]) -> float | None:
    parts = [m.compliance_pct for m in metrics if m.compliance_pct is not None]
    if not parts:
        return None
    return round(sum(parts) / len(parts), 1)


def get_benchmarks(
    db: Session, *, days: int | None = 90, profile_id: str | None = None
) -> BenchmarkResponse:
    from app.services import benchmark_service

    catalog = benchmark_service.list_profiles()
    detail = None
    if profile_id:
        detail = next((p for p in catalog.profiles if p.id == profile_id), None)
    if detail is None:
        detail = catalog.active
    if detail is not None:
        profile = benchmark_service.profile_to_flat(detail.model_dump())
    else:
        profile = default_profile()

    rows = _load_rows(db, days=days)
    grouped: dict[str, list[SpeedTestResult]] = defaultdict(list)
    for row in rows:
        grouped[normalize_isp(row.isp_name)].append(row)

    rankings: list[IspBenchmarkRow] = []
    for isp, items in grouped.items():
        metrics = [
            _compliance(
                metric="Download",
                unit="Mbps",
                target=profile.download_mbps,
                actual=_mean(r.download_mbps for r in items),
                samples=[r.download_mbps for r in items],
                higher_is_better=True,
            ),
            _compliance(
                metric="Upload",
                unit="Mbps",
                target=profile.upload_mbps,
                actual=_mean(r.upload_mbps for r in items),
                samples=[r.upload_mbps for r in items],
                higher_is_better=True,
            ),
            _compliance(
                metric="Ping",
                unit="ms",
                target=profile.ping_ms,
                actual=_mean(r.ping_ms for r in items),
                samples=[r.ping_ms for r in items],
                higher_is_better=False,
            ),
            _compliance(
                metric="Jitter",
                unit="ms",
                target=profile.jitter_ms,
                actual=_mean(r.jitter_ms for r in items),
                samples=[r.jitter_ms for r in items],
                higher_is_better=False,
            ),
            _compliance(
                metric="Packet Loss",
                unit="%",
                target=profile.packet_loss_pct,
                actual=_mean(r.packet_loss_pct for r in items),
                samples=[r.packet_loss_pct for r in items],
                higher_is_better=False,
            ),
            _compliance(
                metric="QoS Score",
                unit="/100",
                target=float(profile.overall_score),
                actual=_mean(r.overall_score for r in items),
                samples=[r.overall_score for r in items],
                higher_is_better=True,
            ),
        ]
        rankings.append(
            IspBenchmarkRow(
                isp=isp,
                tests=len(items),
                composite_score=_composite(metrics),
                metrics=metrics,
            )
        )
    rankings.sort(key=lambda r: (-(r.composite_score or -1), -r.tests))
    return BenchmarkResponse(
        profile=profile,
        profile_detail=detail,
        active_profile_id=catalog.active_profile_id,
        disclaimer=catalog.disclaimer,
        profiles=catalog.profiles,
        rankings=rankings,
        generated_at=_utcnow(),
    )


def _period_key(stamp: datetime, granularity: str) -> str:
    stamp = _aware(stamp) or _utcnow()
    if granularity == "weekly":
        iso = stamp.isocalendar()
        return f"{iso.year}-W{iso.week:02d}"
    if granularity == "monthly":
        return stamp.strftime("%Y-%m")
    return stamp.strftime("%Y-%m-%d")


def get_history(db: Session, *, granularity: str = "daily", days: int | None = 90) -> HistoryAnalyticsResponse:
    if granularity not in {"daily", "weekly", "monthly"}:
        granularity = "daily"
    rows = _load_rows(db, days=days)
    buckets: dict[str, list[SpeedTestResult]] = defaultdict(list)
    for row in rows:
        buckets[_period_key(row.timestamp, granularity)].append(row)
    points = []
    for period in sorted(buckets):
        items = buckets[period]
        points.append(
            HistoryPoint(
                period=period,
                tests=len(items),
                avg_download_mbps=_mean(r.download_mbps for r in items),
                avg_upload_mbps=_mean(r.upload_mbps for r in items),
                avg_ping_ms=_mean(r.ping_ms for r in items),
                avg_jitter_ms=_mean(r.jitter_ms for r in items),
                avg_packet_loss_pct=_mean(r.packet_loss_pct for r in items),
                avg_qos_score=_mean(r.overall_score for r in items),
            )
        )
    return HistoryAnalyticsResponse(
        granularity=granularity,  # type: ignore[arg-type]
        points=points,
        generated_at=_utcnow(),
    )


def get_heatmap(db: Session, *, days: int | None = 90) -> HeatmapResponse:
    rows = _load_rows(db, days=days)
    buckets: dict[str, list[SpeedTestResult]] = defaultdict(list)
    for row in rows:
        buckets[region_from_label(row.server_label)].append(row)
    preferred = [
        "Port Louis",
        "Ebene",
        "Rose Hill",
        "Arsenal",
        "Floreal",
        "La Tour Koenig",
    ]
    cells: list[HeatmapCell] = []
    seen: set[str] = set()
    for name in [*preferred, *sorted(buckets)]:
        if name in seen:
            continue
        seen.add(name)
        items = buckets.get(name, [])
        score = _mean(r.overall_score for r in items)
        cells.append(
            HeatmapCell(
                region=name,
                tests=len(items),
                avg_qos_score=score,
                avg_download_mbps=_mean(r.download_mbps for r in items),
                avg_ping_ms=_mean(r.ping_ms for r in items),
                rating=rating_from_score(int(round(score))) if score is not None else None,
            )
        )
    return HeatmapResponse(cells=cells, generated_at=_utcnow())


def report_payload(db: Session, *, days: int | None = 90) -> dict[str, Any]:
    """Bundle analytics used by the PDF generator and AI layer."""
    dashboard = get_dashboard(db, days=days)
    benchmarks = get_benchmarks(db, days=days)
    history = get_history(db, granularity="daily", days=days)
    heatmap = get_heatmap(db, days=days)
    return {
        "dashboard": dashboard,
        "benchmarks": benchmarks,
        "history": history,
        "heatmap": heatmap,
        "days": days,
    }
