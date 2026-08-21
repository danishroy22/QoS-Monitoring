"""Phase 16 — data quality marking (never silent deletion).

Flags incomplete / failed / outlier / duplicate-suspect rows and excludes them
from analytics by default while keeping every row in the database.
"""

from __future__ import annotations

import json
import statistics
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.speedtest import SpeedTestResult
from app.services.admin_service import normalize_isp, region_from_label

# Soft outlier fences (dissertation heuristics, not standards).
OUTLIER_DOWNLOAD_MAX = 2500.0
OUTLIER_UPLOAD_MAX = 2500.0
OUTLIER_PING_MAX = 2000.0
OUTLIER_LOSS_MAX = 100.0
DUPLICATE_WINDOW_SECONDS = 20


def _aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def assess_measurement(
    *,
    download_mbps: float | None,
    upload_mbps: float | None,
    ping_ms: float | None,
    jitter_ms: float | None,
    packet_loss_pct: float | None,
    isp_name: str | None,
    detected_region: str | None,
    server_label: str | None,
    internet_package: str | None,
    errors: list[str] | None,
    http_ok: bool | None,
    dns_ok: bool | None,
) -> dict[str, Any]:
    flags: list[str] = []

    core = [download_mbps, upload_mbps, ping_ms]
    if any(v is None for v in core):
        flags.append("incomplete_core_metrics")
    if errors:
        flags.append("measurement_errors")
    if http_ok is False:
        flags.append("http_failure")
    if dns_ok is False:
        flags.append("dns_failure")
    if not (isp_name or "").strip() or normalize_isp(isp_name) == "Unknown":
        flags.append("isp_detection_failed")
    region = (detected_region or "").strip() or region_from_label(server_label)
    if not region or region == "Unknown":
        flags.append("missing_geographic_information")
    if not (internet_package or "").strip():
        flags.append("missing_package_information")

    if download_mbps is not None and (download_mbps < 0 or download_mbps > OUTLIER_DOWNLOAD_MAX):
        flags.append("outlier_download")
    if upload_mbps is not None and (upload_mbps < 0 or upload_mbps > OUTLIER_UPLOAD_MAX):
        flags.append("outlier_upload")
    if ping_ms is not None and (ping_ms < 0 or ping_ms > OUTLIER_PING_MAX):
        flags.append("outlier_ping")
    if packet_loss_pct is not None and (
        packet_loss_pct < 0 or packet_loss_pct > OUTLIER_LOSS_MAX
    ):
        flags.append("outlier_packet_loss")
    if jitter_ms is not None and jitter_ms < 0:
        flags.append("outlier_jitter")

    if "measurement_errors" in flags or "http_failure" in flags:
        status = "failed"
    elif "incomplete_core_metrics" in flags:
        status = "incomplete"
    elif any(f.startswith("outlier_") for f in flags):
        status = "outlier"
    else:
        status = "valid"

    # Missing package/geo alone does not invalidate analytics, but is flagged.
    analytics_eligible = status == "valid"
    return {
        "quality_status": status,
        "quality_flags": flags,
        "analytics_eligible": analytics_eligible,
    }


def mark_duplicate_suspects(db: Session, row: SpeedTestResult) -> bool:
    """If a near-identical test exists within a short window, flag duplicate_suspect."""
    ts = _aware(row.timestamp)
    if ts is None:
        return False
    window_start = ts - timedelta(seconds=DUPLICATE_WINDOW_SECONDS)
    candidates = list(
        db.scalars(
            select(SpeedTestResult)
            .where(SpeedTestResult.id != row.id)
            .where(SpeedTestResult.timestamp >= window_start)
            .where(SpeedTestResult.timestamp <= ts)
            .where(SpeedTestResult.client_hash == row.client_hash)
            .limit(20)
        )
    )
    for other in candidates:
        same_server = (other.server_label or "") == (row.server_label or "")
        close_down = (
            other.download_mbps is not None
            and row.download_mbps is not None
            and abs(other.download_mbps - row.download_mbps) < 0.5
        )
        close_ping = (
            other.ping_ms is not None
            and row.ping_ms is not None
            and abs(other.ping_ms - row.ping_ms) < 1.0
        )
        if same_server and close_down and close_ping:
            flags = []
            if row.quality_flags_json:
                try:
                    flags = json.loads(row.quality_flags_json)
                except json.JSONDecodeError:
                    flags = []
            if "duplicate_suspect" not in flags:
                flags.append("duplicate_suspect")
            row.quality_flags_json = json.dumps(flags)
            if row.quality_status == "valid":
                row.quality_status = "duplicate_suspect"
            row.analytics_eligible = False
            return True
    return False


def apply_quality_to_row(db: Session, row: SpeedTestResult) -> SpeedTestResult:
    errors = []
    if row.errors_json:
        try:
            parsed = json.loads(row.errors_json)
            if isinstance(parsed, list):
                errors = [str(x) for x in parsed]
        except json.JSONDecodeError:
            errors = [row.errors_json]
    assessed = assess_measurement(
        download_mbps=row.download_mbps,
        upload_mbps=row.upload_mbps,
        ping_ms=row.ping_ms,
        jitter_ms=row.jitter_ms,
        packet_loss_pct=row.packet_loss_pct,
        isp_name=row.isp_name,
        detected_region=row.detected_region,
        server_label=row.server_label,
        internet_package=row.internet_package,
        errors=errors,
        http_ok=row.http_ok,
        dns_ok=row.dns_ok,
    )
    row.quality_status = assessed["quality_status"]
    row.quality_flags_json = json.dumps(assessed["quality_flags"])
    row.analytics_eligible = bool(assessed["analytics_eligible"])
    mark_duplicate_suspects(db, row)
    return row


def filter_analytics_eligible(rows: list[SpeedTestResult]) -> list[SpeedTestResult]:
    """Keep rows eligible for analytics (legacy unmarked rows stay in)."""
    return [r for r in rows if r.analytics_eligible is not False]


def quality_summary(db: Session, *, days: int | None = 90, isp: str | None = None) -> dict[str, Any]:
    stmt = select(SpeedTestResult)
    if days:
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        stmt = stmt.where(SpeedTestResult.timestamp >= cutoff)
    rows = list(db.scalars(stmt))
    if isp:
        rows = [r for r in rows if normalize_isp(r.isp_name) == normalize_isp(isp)]

    counts: dict[str, int] = {
        "total": len(rows),
        "analytics_eligible": 0,
        "valid": 0,
        "incomplete": 0,
        "failed": 0,
        "outlier": 0,
        "duplicate_suspect": 0,
        "missing_package_information": 0,
        "missing_geographic_information": 0,
        "isp_detection_failed": 0,
        "server_or_http_failure": 0,
    }
    flag_counts: dict[str, int] = {}
    eligible_downloads: list[float] = []

    for row in rows:
        status = (row.quality_status or "valid").lower()
        if row.analytics_eligible is None:
            # Legacy rows without quality columns — treat as eligible.
            counts["analytics_eligible"] += 1
            counts["valid"] += 1
            if row.download_mbps is not None:
                eligible_downloads.append(float(row.download_mbps))
            continue
        if row.analytics_eligible:
            counts["analytics_eligible"] += 1
            if row.download_mbps is not None:
                eligible_downloads.append(float(row.download_mbps))
        if status in counts:
            counts[status] += 1
        try:
            flags = json.loads(row.quality_flags_json or "[]")
        except json.JSONDecodeError:
            flags = []
        if not isinstance(flags, list):
            flags = []
        for flag in flags:
            flag_counts[flag] = flag_counts.get(flag, 0) + 1
            if flag in counts:
                counts[flag] += 1
            if flag in {"http_failure", "dns_failure", "measurement_errors"}:
                counts["server_or_http_failure"] += 1

    avg_download = (
        round(statistics.mean(eligible_downloads), 2) if eligible_downloads else None
    )
    return {
        "days": days,
        "isp": isp,
        "counts": counts,
        "flag_counts": dict(sorted(flag_counts.items(), key=lambda kv: -kv[1])),
        "analytics_example": (
            f"Average Download: {avg_download} Mbps (n={len(eligible_downloads)})"
            if avg_download is not None
            else "Average Download: — (n=0)"
        ),
        "note": (
            "Rows are never silently deleted. Invalid/incomplete/outlier/duplicate-suspect "
            "tests remain stored but are excluded from analytics when analytics_eligible=false."
        ),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
