"""Phase 11 — AI root-cause *style* analysis (cautious pattern explanations).

Identifies co-occurring QoS patterns (e.g. latency up + download down in a peak
window) and explains them carefully. Never claims a confirmed network root cause.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.schemas.admin import (
    RootCauseEvidence,
    RootCausePattern,
    RootCauseResponse,
)
from app.services import peak_hour_service
from app.services.admin_service import get_history, normalize_isp

LIMITATION = (
    "The available measurements cannot independently confirm the underlying "
    "network cause. Alternative explanations (server path effects, client Wi-Fi, "
    "measurement noise, or sampling bias) remain possible."
)

CONSISTENT_CLOSING = (
    "This pattern is consistent with increased network utilisation or congestion, "
    "although the available measurements cannot independently confirm the underlying "
    "network cause."
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _metric_map(metrics: list[dict[str, Any]] | None) -> dict[str, dict[str, Any]]:
    return {str(m.get("key")): m for m in (metrics or []) if m.get("key")}


def _pct_phrase(delta_pct: float | None, *, higher_worse: bool) -> str | None:
    if delta_pct is None:
        return None
    abs_pct = abs(delta_pct)
    if abs_pct < 1:
        return None
    if higher_worse:
        # latency/jitter/loss: positive delta = worse
        direction = "increased" if delta_pct > 0 else "decreased"
    else:
        # download/upload/qos: negative delta = worse
        direction = "decreased" if delta_pct < 0 else "increased"
    return f"{direction} by {abs_pct:.0f}%"


def _build_peak_narrative(window: dict[str, Any]) -> tuple[str | None, list[RootCauseEvidence], str]:
    """Return (narrative, evidence, pattern_id) for a peak window."""
    metrics = _metric_map(window.get("metrics"))
    label = window.get("label") or "the observed peak window"
    evidence: list[RootCauseEvidence] = []

    dl = metrics.get("download_mbps") or {}
    up = metrics.get("upload_mbps") or {}
    ping = metrics.get("ping_ms") or {}
    jitter = metrics.get("jitter_ms") or {}
    loss = metrics.get("packet_loss_pct") or {}
    qos = metrics.get("overall_score") or {}

    for key, block, unit in (
        ("download_mbps", dl, "Mbps"),
        ("upload_mbps", up, "Mbps"),
        ("ping_ms", ping, "ms"),
        ("jitter_ms", jitter, "ms"),
        ("packet_loss_pct", loss, "%"),
        ("overall_score", qos, "/100"),
    ):
        if block.get("delta_pct") is None and block.get("peak_avg") is None:
            continue
        evidence.append(
            RootCauseEvidence(
                metric=key,
                label=str(block.get("label") or key),
                unit=unit,
                peak_avg=block.get("peak_avg"),
                baseline_avg=block.get("baseline_avg"),
                delta_pct=block.get("delta_pct"),
                degraded=block.get("degraded"),
            )
        )

    ping_phrase = _pct_phrase(ping.get("delta_pct"), higher_worse=True)
    dl_phrase = _pct_phrase(dl.get("delta_pct"), higher_worse=False)
    loss_phrase = _pct_phrase(loss.get("delta_pct"), higher_worse=True)
    jitter_phrase = _pct_phrase(jitter.get("delta_pct"), higher_worse=True)

    ping_worse = bool(ping.get("degraded") and (ping.get("delta_pct") or 0) >= 5)
    dl_worse = bool(dl.get("degraded") and (dl.get("delta_pct") or 0) <= -5)
    loss_worse = bool(loss.get("degraded") and (loss.get("delta_pct") or 0) >= 10)
    jitter_worse = bool(jitter.get("degraded") and (jitter.get("delta_pct") or 0) >= 10)

    pattern_id = "insufficient_change"
    parts: list[str] = []

    if ping_worse and dl_worse and ping_phrase and dl_phrase:
        pattern_id = "latency_up_throughput_down"
        parts.append(
            f"Latency {ping_phrase} between {label} while download throughput {dl_phrase}."
        )
        parts.append(CONSISTENT_CLOSING)
    elif ping_worse and ping_phrase and not dl_worse:
        pattern_id = "latency_dominated"
        parts.append(f"Latency {ping_phrase} between {label}.")
        parts.append(
            "This pattern can be consistent with path delay, routing change, or access-network "
            f"buffering. {LIMITATION}"
        )
    elif dl_worse and dl_phrase and not ping_worse:
        pattern_id = "throughput_dominated"
        parts.append(f"Download throughput {dl_phrase} between {label}.")
        parts.append(
            f"This pattern can be consistent with capacity contention or rate limiting. {LIMITATION}"
        )
    elif loss_worse and jitter_worse and loss_phrase and jitter_phrase:
        pattern_id = "loss_jitter_instability"
        parts.append(
            f"Packet loss {loss_phrase} and jitter {jitter_phrase} between {label}."
        )
        parts.append(
            f"This pattern can be consistent with impairment or radio/access instability. {LIMITATION}"
        )
    elif any([ping_worse, dl_worse, loss_worse, jitter_worse]):
        pattern_id = "mixed_degradation"
        bits = [p for p in (ping_phrase, dl_phrase, loss_phrase, jitter_phrase) if p]
        parts.append(
            f"Several QoS metrics changed during {label}: " + "; ".join(bits[:3]) + "."
        )
        parts.append(CONSISTENT_CLOSING)
    else:
        return None, evidence, pattern_id

    n_peak = window.get("tests")
    n_base = window.get("baseline_tests")
    parts.append(f"Sample sizes: peak n={n_peak}, off-peak n={n_base}.")
    return " ".join(parts), evidence, pattern_id


def _trend_narrative(history_points: list[Any]) -> tuple[str | None, list[RootCauseEvidence], str]:
    if len(history_points) < 4:
        return None, [], "insufficient_trend"
    mid = len(history_points) // 2
    older, newer = history_points[:mid], history_points[mid:]

    def avg(attr: str, series: list[Any]) -> float | None:
        vals = [getattr(p, attr) for p in series if getattr(p, attr) is not None]
        return sum(vals) / len(vals) if vals else None

    o_ping, n_ping = avg("avg_ping_ms", older), avg("avg_ping_ms", newer)
    o_dl, n_dl = avg("avg_download_mbps", older), avg("avg_download_mbps", newer)

    evidence: list[RootCauseEvidence] = []
    ping_pct = None
    dl_pct = None
    if o_ping and n_ping and abs(o_ping) > 1e-9:
        ping_pct = round(((n_ping - o_ping) / abs(o_ping)) * 100.0, 1)
        evidence.append(
            RootCauseEvidence(
                metric="ping_ms",
                label="Latency (trend)",
                unit="ms",
                peak_avg=round(n_ping, 2),
                baseline_avg=round(o_ping, 2),
                delta_pct=ping_pct,
                degraded=n_ping > o_ping,
            )
        )
    if o_dl and n_dl and abs(o_dl) > 1e-9:
        dl_pct = round(((n_dl - o_dl) / abs(o_dl)) * 100.0, 1)
        evidence.append(
            RootCauseEvidence(
                metric="download_mbps",
                label="Download (trend)",
                unit="Mbps",
                peak_avg=round(n_dl, 2),
                baseline_avg=round(o_dl, 2),
                delta_pct=dl_pct,
                degraded=n_dl < o_dl,
            )
        )

    ping_phrase = _pct_phrase(ping_pct, higher_worse=True)
    dl_phrase = _pct_phrase(dl_pct, higher_worse=False)
    period = f"{older[0].period} → {newer[-1].period}"

    if ping_pct is not None and dl_pct is not None and ping_pct >= 8 and dl_pct <= -8:
        text = (
            f"Latency {ping_phrase} across {period} while download throughput {dl_phrase}. "
            f"{CONSISTENT_CLOSING}"
        )
        return text, evidence, "trend_latency_up_throughput_down"
    if ping_pct is not None and ping_pct >= 10:
        text = (
            f"Average latency {ping_phrase} across {period}. "
            f"This may be consistent with path or access delay growth. {LIMITATION}"
        )
        return text, evidence, "trend_latency_up"
    if dl_pct is not None and dl_pct <= -10:
        text = (
            f"Average download throughput {dl_phrase} across {period}. "
            f"This may be consistent with rising contention. {LIMITATION}"
        )
        return text, evidence, "trend_throughput_down"
    return None, evidence, "no_material_trend"


def analyze_root_cause(
    db: Session,
    *,
    isp: str | None = None,
    package: str | None = None,
    region: str | None = None,
    days: int | None = 90,
) -> RootCauseResponse:
    peak = peak_hour_service.analyze_peak_hours(
        db,
        isp=isp,
        package=package,
        region=region,
        days=days,
    )
    history = get_history(db, granularity="daily", days=days)

    patterns: list[RootCausePattern] = []
    window = peak.get("peak_window")
    if window:
        narrative, evidence, pattern_id = _build_peak_narrative(window)
        if narrative:
            patterns.append(
                RootCausePattern(
                    id=pattern_id,
                    title="Peak-window co-occurring metric pattern",
                    window_label=window.get("label"),
                    confidence="low",
                    narrative=narrative,
                    evidence=evidence,
                    consistent_with=[
                        "increased network utilisation",
                        "busy-hour congestion",
                        "access-network contention",
                    ],
                    cannot_confirm=[
                        "physical capacity exhaustion",
                        "specific fault location",
                        "ISP backhaul vs last-mile attribution",
                    ],
                )
            )

    # Per-ISP peak notes when no ISP filter (top degraded ISP)
    if not isp:
        isp_rows = peak.get("breakdowns", {}).get("isp") or []
        for row in isp_rows[:2]:
            if not row.get("peak_tests"):
                continue
            fake_window = {
                "label": (window or {}).get("label") or "peak hours",
                "tests": row.get("peak_tests"),
                "baseline_tests": row.get("baseline_tests"),
                "metrics": row.get("metrics"),
            }
            narrative, evidence, pattern_id = _build_peak_narrative(fake_window)
            if not narrative:
                continue
            patterns.append(
                RootCausePattern(
                    id=f"isp_{pattern_id}",
                    title=f"Pattern note · {row.get('label')}",
                    window_label=fake_window["label"],
                    confidence="low",
                    narrative=f"{row.get('label')}: {narrative}",
                    evidence=evidence,
                    consistent_with=["busy-hour degradation for this ISP"],
                    cannot_confirm=["confirmed congestion on this ISP's network"],
                )
            )

    trend_text, trend_evidence, trend_id = _trend_narrative(history.points)
    if trend_text:
        patterns.append(
            RootCausePattern(
                id=trend_id,
                title="Multi-day trend pattern",
                window_label=None,
                confidence="low",
                narrative=trend_text,
                evidence=trend_evidence,
                consistent_with=["sustained utilisation growth", "path quality change"],
                cannot_confirm=["a single root cause across the full period"],
            )
        )

    scope = []
    if isp:
        scope.append(f"ISP={normalize_isp(isp)}")
    if package:
        scope.append(f"package={package}")
    if region:
        scope.append(f"region={region}")
    scope_label = ", ".join(scope) if scope else "all Mauritius samples in window"

    if not patterns:
        summary = (
            f"No material co-occurring degradation pattern was identified for {scope_label} "
            f"(days={days}). Collect more peak/off-peak samples before interpreting causes."
        )
    else:
        # Prefer the primary peak narrative as headline summary.
        summary = patterns[0].narrative

    return RootCauseResponse(
        summary=summary,
        limitation=LIMITATION,
        patterns=patterns,
        filters={
            "isp": isp,
            "package": package,
            "region": region,
            "days": days,
        },
        available_isps=peak.get("available_isps") or [],
        available_packages=peak.get("available_packages") or [],
        available_regions=peak.get("available_regions") or [],
        total_tests=peak.get("total_tests") or 0,
        peak_window=window,
        model_provider="root-cause-playbook-v1",
        generated_at=_utcnow(),
    )
