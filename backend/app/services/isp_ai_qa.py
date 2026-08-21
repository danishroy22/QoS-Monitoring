"""Phase 10 — AI ISP analysis Q&A grounded in aggregated database facts.

Answers are derived from structured retrieval (ISP analytics, packages, peak
hours, regional heatmap). The LLM may only rephrase facts; it must not invent
statistics. When the LLM is unavailable, the offline playbook answers directly
from the same facts.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.schemas.admin import IspAiAskResponse, IspAiCitation, IspAiFactsResponse
from app.services import peak_hour_service
from app.services.admin_service import (
    get_dashboard,
    get_heatmap,
    get_history,
    get_isp_analytics,
    get_package_performance,
    normalize_isp,
)

logger = logging.getLogger(__name__)

EXAMPLE_QUESTIONS = [
    "Which ISP has the best average latency?",
    "Which ISP has the best package fulfilment?",
    "Which regions experience the greatest degradation?",
    "When does Emtel experience its worst performance?",
    "How has Mauritius broadband performance changed?",
    "Which packages consistently underperform?",
]

ASK_SYSTEM_PROMPT = (
    "You are the SmartQoS ISP analyst. Answer ONLY using the provided facts JSON. "
    "Do not invent numbers, ISPs, regions, or packages. If facts are insufficient, "
    "say so. Return JSON with keys: answer (string), notes (string array)."
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _fmt(value: float | None, digits: int = 1, suffix: str = "") -> str:
    if value is None:
        return "n/a"
    return f"{value:.{digits}f}{suffix}"


def build_isp_facts(db: Session, *, days: int | None = 90) -> dict[str, Any]:
    """Retrieve structured aggregates used by every Phase 10 answer."""
    dashboard = get_dashboard(db, days=days)
    analytics = get_isp_analytics(db, days=days)
    packages = get_package_performance(db, days=days)
    heatmap = get_heatmap(db, days=days)
    peak = peak_hour_service.analyze_peak_hours(db, days=days)
    history_daily = get_history(db, granularity="daily", days=days)

    isps = [row.model_dump() for row in analytics.isps]
    by_latency = sorted(
        [r for r in analytics.isps if r.avg_ping_ms is not None],
        key=lambda r: (r.avg_ping_ms, -r.tests),
    )
    fulfilment_rows = [
        p
        for p in packages.packages
        if p.avg_download_fulfilment_pct is not None or p.avg_upload_fulfilment_pct is not None
    ]

    def _fulfil_score(row) -> float:
        vals = [
            v
            for v in (row.avg_download_fulfilment_pct, row.avg_upload_fulfilment_pct)
            if v is not None
        ]
        return sum(vals) / len(vals) if vals else -1.0

    by_fulfilment_isp: dict[str, list[float]] = {}
    for row in fulfilment_rows:
        by_fulfilment_isp.setdefault(row.isp, []).append(_fulfil_score(row))
    isp_fulfilment = [
        {
            "isp": isp,
            "avg_fulfilment_pct": round(sum(vals) / len(vals), 1),
            "packages": len(vals),
        }
        for isp, vals in by_fulfilment_isp.items()
        if vals
    ]
    isp_fulfilment.sort(key=lambda r: (-r["avg_fulfilment_pct"], -r["packages"]))

    underperforming = [
        {
            "isp": p.isp,
            "package": p.package,
            "tests": p.tests,
            "advertised_download_mbps": p.advertised_download_mbps,
            "avg_download_mbps": p.avg_download_mbps,
            "avg_download_fulfilment_pct": p.avg_download_fulfilment_pct,
            "avg_upload_fulfilment_pct": p.avg_upload_fulfilment_pct,
            "avg_qos_score": p.avg_qos_score,
        }
        for p in fulfilment_rows
        if (p.avg_download_fulfilment_pct is not None and p.avg_download_fulfilment_pct < 80)
        or (p.avg_upload_fulfilment_pct is not None and p.avg_upload_fulfilment_pct < 80)
    ]
    underperforming.sort(
        key=lambda r: (
            r["avg_download_fulfilment_pct"]
            if r["avg_download_fulfilment_pct"] is not None
            else 999
        )
    )

    regions = [
        {
            "region": c.region,
            "tests": c.tests,
            "avg_qos_score": c.avg_qos_score,
            "avg_download_mbps": c.avg_download_mbps,
            "avg_ping_ms": c.avg_ping_ms,
            "rating": c.rating,
        }
        for c in heatmap.cells
        if c.tests > 0
    ]
    regions_by_qos = sorted(
        [r for r in regions if r["avg_qos_score"] is not None],
        key=lambda r: (r["avg_qos_score"], -r["tests"]),
    )

    peak_regions = peak.get("breakdowns", {}).get("region") or []
    degraded_regions = [
        {
            "region": r["label"],
            "tests": r["tests"],
            "peak_tests": r["peak_tests"],
            "degradation_score": r["degradation_score"],
            "metrics": r["metrics"],
        }
        for r in peak_regions
        if (r.get("degradation_score") or 0) > 0 and r.get("peak_tests", 0) > 0
    ]

    isp_peak: dict[str, Any] = {}
    for row in peak.get("breakdowns", {}).get("isp") or []:
        isp_peak[str(row["label"])] = {
            "peak_window": (peak.get("peak_window") or {}).get("label"),
            "degradation_score": row.get("degradation_score"),
            "peak_tests": row.get("peak_tests"),
            "baseline_tests": row.get("baseline_tests"),
            "metrics": row.get("metrics"),
        }

    # Mauritius trend: compare older half of daily points vs newer half.
    points = history_daily.points
    trend: dict[str, Any] = {"samples_days": len(points), "insufficient": len(points) < 2}
    if len(points) >= 2:
        mid = len(points) // 2
        older, newer = points[:mid], points[mid:]

        def _avg(attr: str, series) -> float | None:
            vals = [getattr(p, attr) for p in series if getattr(p, attr) is not None]
            return round(sum(vals) / len(vals), 2) if vals else None

        older_qos = _avg("avg_qos_score", older)
        newer_qos = _avg("avg_qos_score", newer)
        older_dl = _avg("avg_download_mbps", older)
        newer_dl = _avg("avg_download_mbps", newer)
        older_ping = _avg("avg_ping_ms", older)
        newer_ping = _avg("avg_ping_ms", newer)
        trend = {
            "samples_days": len(points),
            "insufficient": False,
            "older_period": f"{older[0].period} → {older[-1].period}",
            "newer_period": f"{newer[0].period} → {newer[-1].period}",
            "older": {
                "avg_qos_score": older_qos,
                "avg_download_mbps": older_dl,
                "avg_ping_ms": older_ping,
                "days": len(older),
            },
            "newer": {
                "avg_qos_score": newer_qos,
                "avg_download_mbps": newer_dl,
                "avg_ping_ms": newer_ping,
                "days": len(newer),
            },
            "delta": {
                "qos_score": (
                    round(newer_qos - older_qos, 1)
                    if older_qos is not None and newer_qos is not None
                    else None
                ),
                "download_mbps": (
                    round(newer_dl - older_dl, 1)
                    if older_dl is not None and newer_dl is not None
                    else None
                ),
                "ping_ms": (
                    round(newer_ping - older_ping, 1)
                    if older_ping is not None and newer_ping is not None
                    else None
                ),
            },
        }

    kpis = dashboard.kpis.model_dump()
    return {
        "window_days": days,
        "generated_at": _utcnow().isoformat(),
        "kpis": kpis,
        "isps": isps,
        "best_latency_isp": (
            {
                "isp": by_latency[0].isp,
                "avg_ping_ms": by_latency[0].avg_ping_ms,
                "tests": by_latency[0].tests,
            }
            if by_latency
            else None
        ),
        "latency_ranking": [
            {"isp": r.isp, "avg_ping_ms": r.avg_ping_ms, "tests": r.tests}
            for r in by_latency[:8]
        ],
        "best_fulfilment_isp": isp_fulfilment[0] if isp_fulfilment else None,
        "fulfilment_ranking": isp_fulfilment[:8],
        "underperforming_packages": underperforming[:12],
        "regions_lowest_qos": regions_by_qos[:8],
        "regions_peak_degradation": degraded_regions[:8],
        "peak_window": peak.get("peak_window"),
        "isp_peak": isp_peak,
        "mauritius_trend": trend,
        "example_questions": EXAMPLE_QUESTIONS,
        "disclaimer": (
            "All figures come from stored speed_tests aggregates. "
            "Sample sizes (n=) must be considered before drawing conclusions."
        ),
    }


def _detect_intent(question: str) -> tuple[str, str | None]:
    q = question.lower().strip()
    isp_hint = None
    for name in (
        "emtel",
        "mauritius telecom",
        "orange",
        "rogers",
        "bharat",
        "mtml",
        "cholos",
    ):
        if name in q:
            isp_hint = normalize_isp(name.title() if name != "mauritius telecom" else "Mauritius Telecom")
            if name == "orange":
                isp_hint = "Mauritius Telecom / Orange"
            break
    # Explicit "when does X" capture
    m = re.search(r"when does\s+(.+?)\s+experience", q)
    if m:
        isp_hint = normalize_isp(m.group(1).strip())

    if "fulfil" in q or "advertised" in q:
        if "underperform" in q or "worst" in q or "poor" in q:
            return "underperforming_packages", isp_hint
        return "best_fulfilment", isp_hint
    if "latency" in q or "ping" in q:
        return "best_latency", isp_hint
    if "region" in q and ("degrad" in q or "worst" in q or "greatest" in q or "poor" in q):
        return "region_degradation", isp_hint
    if "when does" in q or ("worst performance" in q and isp_hint):
        return "isp_worst_time", isp_hint
    if "mauritius" in q or "changed" in q or "trend" in q or "over time" in q:
        return "mauritius_trend", isp_hint
    if "underperform" in q and "package" in q:
        return "underperforming_packages", isp_hint
    if "package" in q and ("best" in q or "fulfil" in q):
        return "best_fulfilment", isp_hint
    return "general", isp_hint


def _offline_answer(intent: str, facts: dict[str, Any], isp_hint: str | None) -> tuple[str, list[IspAiCitation]]:
    citations: list[IspAiCitation] = []
    kpis = facts.get("kpis") or {}

    if intent == "best_latency":
        best = facts.get("best_latency_isp")
        citations.append(IspAiCitation(source="isp_analytics", detail="avg_ping_ms ranking"))
        if not best:
            return (
                "No ISP latency samples are available in this window (n=0). "
                "Collect speed tests before ranking latency.",
                citations,
            )
        ranking = facts.get("latency_ranking") or []
        extras = "; ".join(
            f"{r['isp']} {_fmt(r['avg_ping_ms'], 0, ' ms')} (n={r['tests']})"
            for r in ranking[1:4]
        )
        answer = (
            f"{best['isp']} has the best average latency at "
            f"{_fmt(best['avg_ping_ms'], 0, ' ms')} (n={best['tests']})"
            f" over the last {facts.get('window_days')} days."
        )
        if extras:
            answer += f" Next: {extras}."
        return answer, citations

    if intent == "best_fulfilment":
        best = facts.get("best_fulfilment_isp")
        citations.append(
            IspAiCitation(source="package_performance", detail="mean download/upload fulfilment by ISP")
        )
        if not best:
            return (
                "No package fulfilment data is available yet. Configure packages and "
                "ensure tests store advertised vs measured fulfilment.",
                citations,
            )
        answer = (
            f"{best['isp']} currently shows the best package fulfilment at "
            f"{_fmt(best['avg_fulfilment_pct'], 1, '%')} across {best['packages']} "
            f"package group(s)."
        )
        return answer, citations

    if intent == "region_degradation":
        peak_regs = facts.get("regions_peak_degradation") or []
        low_qos = facts.get("regions_lowest_qos") or []
        citations.append(IspAiCitation(source="peak_hours", detail="region peak vs off-peak degradation"))
        citations.append(IspAiCitation(source="heatmap", detail="regional mean QoS"))
        if peak_regs:
            top = peak_regs[0]
            answer = (
                f"{top['region']} shows the greatest peak-hour degradation score "
                f"({_fmt(top.get('degradation_score'), 3)}; peak n={top.get('peak_tests')}). "
                "This is consistent with a possible congestion pattern and is not a confirmed root cause."
            )
            if len(peak_regs) > 1:
                answer += " Also elevated: " + ", ".join(r["region"] for r in peak_regs[1:4]) + "."
            return answer, citations
        if low_qos:
            top = low_qos[0]
            return (
                f"{top['region']} has the lowest mean QoS "
                f"({_fmt(top['avg_qos_score'], 0)}/100, n={top['tests']}). "
                "Peak-hour degradation samples were insufficient to rank congestion patterns.",
                citations,
            )
        return "No regional samples are available in this window.", citations

    if intent == "isp_worst_time":
        citations.append(IspAiCitation(source="peak_hours", detail="ISP peak-window metrics"))
        peak_window = facts.get("peak_window") or {}
        isp_peak = facts.get("isp_peak") or {}
        target = isp_hint or "Emtel"
        # Fuzzy match keys
        match_key = None
        for key in isp_peak:
            if target.lower() in key.lower() or key.lower() in target.lower():
                match_key = key
                break
        if not match_key:
            label = peak_window.get("label") if peak_window else None
            if label:
                return (
                    f"No ISP-specific peak breakdown for '{target}'. "
                    f"Across Mauritius, the strongest degradation window is {label} "
                    f"(peak n={peak_window.get('tests')}).",
                    citations,
                )
            return (
                f"Insufficient hourly samples to identify when {target} performs worst.",
                citations,
            )
        block = isp_peak[match_key]
        metrics = {m["key"]: m for m in (block.get("metrics") or [])}
        dl = metrics.get("download_mbps") or {}
        ping = metrics.get("ping_ms") or {}
        answer = (
            f"{match_key} shows its weakest measured performance in the peak window "
            f"{block.get('peak_window') or peak_window.get('label') or 'n/a'} "
            f"(peak n={block.get('peak_tests')}, off-peak n={block.get('baseline_tests')}). "
            f"Download change {_fmt(dl.get('delta_pct'), 1, '%')}; "
            f"latency change {_fmt(ping.get('delta_pct'), 1, '%')}. "
            "Interpretation remains cautious — measurements may be consistent with congestion "
            "but cannot independently confirm the cause."
        )
        return answer, citations

    if intent == "mauritius_trend":
        trend = facts.get("mauritius_trend") or {}
        citations.append(IspAiCitation(source="history", detail="daily averages older half vs newer half"))
        if trend.get("insufficient"):
            return (
                "Not enough daily history to describe a Mauritius broadband trend yet "
                f"(daily buckets={trend.get('samples_days', 0)}).",
                citations,
            )
        delta = trend.get("delta") or {}
        newer = trend.get("newer") or {}
        older = trend.get("older") or {}
        qos_delta = delta.get("qos_score")
        direction = "stable"
        if qos_delta is not None:
            if qos_delta >= 2:
                direction = "improved"
            elif qos_delta <= -2:
                direction = "worsened"
        answer = (
            f"Mauritius broadband QoS has {direction} when comparing "
            f"{trend.get('older_period')} (QoS {_fmt(older.get('avg_qos_score'), 0)}) with "
            f"{trend.get('newer_period')} (QoS {_fmt(newer.get('avg_qos_score'), 0)}; "
            f"Δ {_fmt(qos_delta, 1)}). "
            f"Download Δ {_fmt(delta.get('download_mbps'), 1, ' Mbps')}; "
            f"latency Δ {_fmt(delta.get('ping_ms'), 1, ' ms')}. "
            f"Window covers {kpis.get('total_tests', 0)} tests."
        )
        return answer, citations

    if intent == "underperforming_packages":
        rows = facts.get("underperforming_packages") or []
        citations.append(
            IspAiCitation(
                source="package_performance",
                detail="packages with fulfilment below 80%",
            )
        )
        if not rows:
            return (
                "No packages currently fall below the 80% fulfilment advisory threshold "
                "in this window (or fulfilment fields are missing).",
                citations,
            )
        bits = [
            f"{r['isp']} / {r['package']}: ↓ {_fmt(r.get('avg_download_fulfilment_pct'), 0, '%')} "
            f"(meas {_fmt(r.get('avg_download_mbps'), 1)} vs adv {_fmt(r.get('advertised_download_mbps'), 0)} Mbps, n={r['tests']})"
            for r in rows[:5]
        ]
        return (
            "Packages consistently underperforming on fulfilment: " + "; ".join(bits) + ".",
            citations,
        )

    # general
    citations.append(IspAiCitation(source="dashboard", detail="overall Mauritius KPIs"))
    if not kpis.get("total_tests"):
        return (
            "No speed-test samples are stored yet, so ISP analysis cannot be produced.",
            citations,
        )
    leader = (facts.get("isps") or [{}])[0]
    best_lat = facts.get("best_latency_isp")
    answer = (
        f"Across {kpis.get('total_tests')} tests and {kpis.get('isp_count')} ISPs, "
        f"mean QoS is {_fmt(kpis.get('avg_qos_score'), 0)}/100. "
    )
    if leader.get("isp"):
        answer += f"Leaderboard lead: {leader.get('isp')} at {_fmt(leader.get('avg_qos_score'), 0)}/100. "
    if best_lat:
        answer += f"Best latency: {best_lat['isp']} at {_fmt(best_lat['avg_ping_ms'], 0, ' ms')}."
    return answer.strip(), citations


def list_isp_facts(db: Session, *, days: int | None = 90) -> IspAiFactsResponse:
    facts = build_isp_facts(db, days=days)
    return IspAiFactsResponse(
        window_days=days,
        facts=facts,
        example_questions=EXAMPLE_QUESTIONS,
        disclaimer=str(facts.get("disclaimer") or ""),
        generated_at=_utcnow(),
    )


def answer_isp_question(
    db: Session, *, question: str, days: int | None = 90
) -> IspAiAskResponse:
    cleaned = (question or "").strip()
    if not cleaned:
        cleaned = EXAMPLE_QUESTIONS[0]
    facts = build_isp_facts(db, days=days)
    intent, isp_hint = _detect_intent(cleaned)
    offline_answer, citations = _offline_answer(intent, facts, isp_hint)

    settings = get_settings()
    provider = "offline-playbook"
    answer = offline_answer

    fact_slice = {
        "intent": intent,
        "isp_hint": isp_hint,
        "question": cleaned,
        "facts": {
            "best_latency_isp": facts.get("best_latency_isp"),
            "latency_ranking": facts.get("latency_ranking"),
            "best_fulfilment_isp": facts.get("best_fulfilment_isp"),
            "fulfilment_ranking": facts.get("fulfilment_ranking"),
            "underperforming_packages": facts.get("underperforming_packages"),
            "regions_lowest_qos": facts.get("regions_lowest_qos"),
            "regions_peak_degradation": facts.get("regions_peak_degradation"),
            "peak_window": facts.get("peak_window"),
            "isp_peak": facts.get("isp_peak"),
            "mauritius_trend": facts.get("mauritius_trend"),
            "kpis": facts.get("kpis"),
            "disclaimer": facts.get("disclaimer"),
        },
        "offline_answer": offline_answer,
    }
    parsed = _ask_llm(settings, fact_slice) if settings.ai_enabled else None
    if parsed:
        notes = parsed.get("notes") if isinstance(parsed.get("notes"), list) else []
        # Numbers stay grounded in the offline fact answer; LLM may only add brief notes.
        if notes:
            answer = offline_answer + " " + " ".join(str(n) for n in notes[:2])
            provider = f"openai:{settings.openai_model}+facts"
        else:
            provider = f"openai:{settings.openai_model}+facts"

    return IspAiAskResponse(
        question=cleaned,
        intent=intent,
        answer=answer,
        facts_used=_facts_used_for_intent(intent, facts, isp_hint),
        citations=citations,
        example_questions=EXAMPLE_QUESTIONS,
        model_provider=provider,
        days=days,
        generated_at=_utcnow(),
    )


def _facts_used_for_intent(
    intent: str, facts: dict[str, Any], isp_hint: str | None
) -> list[dict[str, Any]]:
    if intent == "best_latency":
        return [facts["best_latency_isp"]] if facts.get("best_latency_isp") else []
    if intent == "best_fulfilment":
        return [facts["best_fulfilment_isp"]] if facts.get("best_fulfilment_isp") else []
    if intent == "region_degradation":
        return list(facts.get("regions_peak_degradation") or facts.get("regions_lowest_qos") or [])[:5]
    if intent == "isp_worst_time":
        isp_peak = facts.get("isp_peak") or {}
        if isp_hint:
            for key, val in isp_peak.items():
                if isp_hint.lower() in key.lower():
                    return [{"isp": key, **val}]
        return [facts.get("peak_window")] if facts.get("peak_window") else []
    if intent == "mauritius_trend":
        return [facts.get("mauritius_trend") or {}]
    if intent == "underperforming_packages":
        return list(facts.get("underperforming_packages") or [])[:5]
    return [{"kpis": facts.get("kpis")}]


def _ask_llm(settings, fact_slice: dict[str, Any]) -> dict[str, Any] | None:
    """LLM call constrained to provided facts (separate prompt from market summary)."""
    if not settings.ai_enabled:
        return None
    endpoint = settings.openai_base_url.rstrip("/") + "/chat/completions"
    payload = {
        "model": settings.openai_model,
        "temperature": 0.1,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": ASK_SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps(fact_slice, default=str)},
        ],
    }
    body = json.dumps(payload).encode("utf-8")
    from urllib.error import HTTPError, URLError
    from urllib.request import Request, urlopen

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
        return parsed if isinstance(parsed, dict) else None
    except (HTTPError, URLError, TimeoutError, OSError, json.JSONDecodeError, KeyError, IndexError, TypeError) as exc:
        logger.warning("ISP AI ask LLM unavailable: %s", exc)
        return None
