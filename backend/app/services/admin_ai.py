"""Natural-language ISP analysis for the Administrator Portal (Phase 18).

Uses the existing OpenAI-compatible client when configured, otherwise the
offline playbook — same pattern as the consumer Network Assistant.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.schemas.admin import AdminAiResponse, IspAiCard
from app.services.admin_service import get_benchmarks, get_dashboard, get_isp_analytics
from measurement.qos_analysis import rating_from_score

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are the SmartQoS Administrator analyst for Mauritius broadband. "
    "Return JSON with keys: market_summary (string), recommendations (string array), "
    "isps (array of {isp, summary, strengths, weaknesses, recommendations}). "
    "Be concise, factual, and operator-facing. Do not invent measurements."
)


def _offline_isp_card(row) -> IspAiCard:
    score = row.avg_qos_score
    rating = rating_from_score(int(round(score))) if score is not None else "Unknown"
    strengths: list[str] = []
    weaknesses: list[str] = []
    recs: list[str] = []

    if row.avg_download_mbps is not None and row.avg_download_mbps >= 80:
        strengths.append(f"Download averages {row.avg_download_mbps:.1f} Mbps across {row.tests} tests.")
    elif row.avg_download_mbps is not None:
        weaknesses.append(f"Download averages only {row.avg_download_mbps:.1f} Mbps.")
        recs.append("Investigate peak-hour congestion and access-network contention on download.")

    if row.avg_upload_mbps is not None and row.avg_upload_mbps >= 15:
        strengths.append(f"Upload is healthy at {row.avg_upload_mbps:.1f} Mbps.")
    elif row.avg_upload_mbps is not None:
        weaknesses.append(f"Upload averages {row.avg_upload_mbps:.1f} Mbps.")
        recs.append("Review asymmetric plans and upstream contention for this ISP.")

    if row.avg_ping_ms is not None and row.avg_ping_ms <= 25:
        strengths.append(f"Latency is competitive at {row.avg_ping_ms:.0f} ms.")
    elif row.avg_ping_ms is not None:
        weaknesses.append(f"Average ping is elevated at {row.avg_ping_ms:.0f} ms.")
        recs.append("Check routing, last-mile buffering, and busy-hour latency.")

    if row.avg_jitter_ms is not None and row.avg_jitter_ms > 10:
        weaknesses.append(f"Jitter averages {row.avg_jitter_ms:.1f} ms.")
        recs.append("Prioritise stability (bufferbloat / radio interference) for real-time traffic.")
    elif row.avg_jitter_ms is not None:
        strengths.append(f"Jitter is controlled at {row.avg_jitter_ms:.1f} ms.")

    if row.avg_packet_loss_pct is not None and row.avg_packet_loss_pct >= 1:
        weaknesses.append(f"Packet loss averages {row.avg_packet_loss_pct:.2f}%.")
        recs.append("Escalate access-network impairment if wired loss persists.")
    elif row.avg_packet_loss_pct is not None:
        strengths.append("Packet loss remains within a healthy range.")

    if not strengths:
        strengths.append("Insufficient strong metrics — treat this ISP as needing closer observation.")
    if not recs:
        recs.append("Maintain current monitoring cadence and compare against the Ideal Broadband Profile.")

    bits = [f"{row.isp} scores {score:.0f}/100 ({rating}) over {row.tests} samples."]
    if weaknesses:
        bits.append("Primary gaps: " + "; ".join(weaknesses[:2]))
    else:
        bits.append("Performance is broadly aligned with the Ideal Broadband Profile.")

    return IspAiCard(
        isp=row.isp,
        tests=row.tests,
        summary=" ".join(bits),
        strengths=strengths[:4],
        weaknesses=weaknesses[:4],
        recommendations=recs[:4],
        rating=rating,
    )


def _offline_analysis(db: Session, *, days: int | None, isp: str | None = None) -> AdminAiResponse:
    dashboard = get_dashboard(db, days=days, isp=isp)
    analytics = get_isp_analytics(db, days=days, isp=isp)
    cards = [_offline_isp_card(row) for row in analytics.isps]
    kpis = dashboard.kpis
    if not cards:
        market = "No speed-test samples are stored yet. Run consumer tests or enable monitoring to populate ISP analytics."
        recs = ["Collect at least a week of measurements before ranking ISPs."]
    else:
        leader = analytics.isps[0]
        market = (
            f"Across {kpis.total_tests} tests and {kpis.isp_count} ISPs, mean QoS is "
            f"{kpis.avg_qos_score if kpis.avg_qos_score is not None else 'n/a'}/100. "
            f"{leader.isp} currently leads the leaderboard"
            + (f" at {leader.avg_qos_score:.0f}/100." if leader.avg_qos_score is not None else ".")
        )
        recs = []
        for card in cards:
            recs.extend(f"{card.isp}: {item}" for item in card.recommendations[:1])
        recs.append("Re-benchmark ISPs monthly against the Ideal Broadband Profile.")
    return AdminAiResponse(
        market_summary=market,
        isps=cards,
        recommendations=recs[:8],
        model_provider="offline-playbook",
        generated_at=datetime.now(timezone.utc),
    )


def _llm_json(settings, user_prompt: str) -> dict[str, Any] | None:
    if not settings.ai_enabled:
        return None
    endpoint = settings.openai_base_url.rstrip("/") + "/chat/completions"
    payload = {
        "model": settings.openai_model,
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
    }
    body = json.dumps(payload).encode("utf-8")
    request = Request(
        endpoint,
        data=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {settings.openai_api_key}",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=settings.ai_timeout_seconds) as response:
            raw = json.loads(response.read().decode("utf-8"))
        content = raw["choices"][0]["message"]["content"]
        parsed = json.loads(content)
        if not isinstance(parsed, dict):
            return None
        return parsed
    except (HTTPError, URLError, TimeoutError, OSError, json.JSONDecodeError, KeyError, IndexError, TypeError) as exc:
        logger.warning("Admin ISP LLM analysis unavailable: %s", exc)
        return None


def generate_isp_analysis(
    db: Session, *, days: int | None = 90, isp: str | None = None
) -> AdminAiResponse:
    fallback = _offline_analysis(db, days=days, isp=isp)
    settings = get_settings()
    analytics = get_isp_analytics(db, days=days, isp=isp)
    benchmarks = get_benchmarks(db, days=days, isp=isp)
    user_prompt = json.dumps(
        {
            "window_days": days,
            "isps": [row.model_dump() for row in analytics.isps],
            "benchmarks": [row.model_dump() for row in benchmarks.rankings],
            "profile": benchmarks.profile.model_dump(),
        },
        default=str,
    )
    parsed = _llm_json(settings, user_prompt)
    if not parsed:
        return fallback

    cards: list[IspAiCard] = []
    by_isp = {c.isp: c for c in fallback.isps}
    llm_isps = parsed.get("isps") or []
    if isinstance(llm_isps, list):
        for item in llm_isps:
            if not isinstance(item, dict):
                continue
            name = str(item.get("isp") or "").strip()
            base = by_isp.get(name)
            if not base:
                continue
            cards.append(
                IspAiCard(
                    isp=name,
                    tests=base.tests,
                    summary=str(item.get("summary") or base.summary),
                    strengths=list(item.get("strengths") or base.strengths)[:6],
                    weaknesses=list(item.get("weaknesses") or base.weaknesses)[:6],
                    recommendations=list(item.get("recommendations") or base.recommendations)[:6],
                    rating=base.rating,
                )
            )
    if not cards:
        cards = fallback.isps
    recs = parsed.get("recommendations")
    if not isinstance(recs, list) or not recs:
        recs = fallback.recommendations
    return AdminAiResponse(
        market_summary=str(parsed.get("market_summary") or fallback.market_summary),
        isps=cards,
        recommendations=[str(r) for r in recs][:10],
        model_provider=f"openai:{settings.openai_model}",
        generated_at=datetime.now(timezone.utc),
    )
