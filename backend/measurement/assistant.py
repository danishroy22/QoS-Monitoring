"""AI Network Assistant — trend-aware internet quality recommendations."""

from __future__ import annotations

from typing import Any, Sequence

from app.core.config import Settings, get_settings
from app.services.ai_llm import LLMError, call_chat_completion
from app.services.ai_prompts import SYSTEM_PROMPT


def _pct_change(old: float | None, new: float | None) -> float | None:
    if old is None or new is None or old == 0:
        return None
    return ((new - old) / abs(old)) * 100.0


def build_assistant_context(
    latest: dict[str, Any],
    history: Sequence[dict[str, Any]],
    health: dict[str, Any],
) -> dict[str, Any]:
    """Derive trend signals from recent tests for the assistant."""
    previous = history[-2] if len(history) >= 2 else None
    ping_change = _pct_change(
        previous.get("ping_ms") if previous else None,
        latest.get("ping_ms"),
    )
    down_change = _pct_change(
        previous.get("download_mbps") if previous else None,
        latest.get("download_mbps"),
    )

    window_note = None
    if len(history) >= 3:
        recent = history[-6:]
        pings = [h.get("ping_ms") for h in recent if h.get("ping_ms") is not None]
        if pings:
            avg_recent = sum(pings) / len(pings)
            window_note = {
                "from": recent[0].get("timestamp"),
                "to": recent[-1].get("timestamp"),
                "avg_ping_ms": round(avg_recent, 2),
                "samples": len(pings),
            }

    return {
        "latest": latest,
        "health": health,
        "ping_change_pct": round(ping_change, 1) if ping_change is not None else None,
        "download_change_pct": round(down_change, 1) if down_change is not None else None,
        "window": window_note,
        "history_count": len(history),
    }


def generate_network_assistant(
    context: dict[str, Any],
    settings: Settings | None = None,
) -> dict[str, Any]:
    """Produce Analysis / Possible reasons / Recommended actions."""
    settings = settings or get_settings()
    latest = context.get("latest") or {}
    health = context.get("health") or {}
    ping_change = context.get("ping_change_pct")
    overall = health.get("overall_rating", "Unknown")
    score = health.get("overall_score", 0)

    analysis_bits = [f"Overall network health is {overall} ({score}/100)."]
    if ping_change is not None and abs(ping_change) >= 20:
        direction = "increased" if ping_change > 0 else "decreased"
        analysis_bits.append(
            f"Your latency {direction} by {abs(ping_change):.0f}% compared with the previous test."
        )
    if latest.get("packet_loss_pct", 0) and latest["packet_loss_pct"] >= 1:
        analysis_bits.append(
            f"Packet loss is elevated at {latest['packet_loss_pct']}%."
        )
    if latest.get("download_mbps") is not None and latest["download_mbps"] < 25:
        analysis_bits.append(
            f"Download speed is only {latest['download_mbps']} Mbps, which may feel slow for HD streaming."
        )

    window = context.get("window")
    if window and window.get("avg_ping_ms", 0) > 60:
        analysis_bits.append(
            f"Recent average ping over the last {window['samples']} tests is {window['avg_ping_ms']} ms."
        )

    metric_list = health.get("metrics", [])
    dominant = min(
        (m for m in metric_list if m.get("score") is not None),
        key=lambda m: m["score"],
        default=None,
    )
    issue = (dominant or {}).get("name", "Ping")

    reasons_map = {
        "Ping": [
            "ISP congestion during busy hours",
            "Wi-Fi interference or weak signal",
            "Background cloud sync / downloads",
            "VPN or suboptimal routing",
        ],
        "Jitter": [
            "Unstable Wi-Fi channel",
            "Bufferbloat on the home router",
            "Competing real-time applications",
        ],
        "Packet Loss": [
            "Wi-Fi interference or distance from router",
            "Faulty Ethernet / modem link",
            "ISP access-network impairment",
        ],
        "Download": [
            "Plan speed limitation or ISP throttling",
            "Wi-Fi bottleneck instead of line rate",
            "Peak-hour congestion",
        ],
        "Upload": [
            "Asymmetric broadband plan",
            "Upload-heavy apps (backup, calls, streams)",
            "Router QoS misconfiguration",
        ],
        "DNS Lookup": [
            "Slow ISP DNS resolver",
            "DNS hijacking / filtering appliance",
            "Local network congestion before resolution",
        ],
        "HTTP Response": [
            "Path latency to popular CDNs",
            "Local DNS + TLS handshake delay",
            "Temporary upstream congestion",
        ],
    }
    actions_map = {
        "Ping": [
            "Move closer to the router or switch to Ethernet",
            "Restart the router and optical/modem device",
            "Pause large downloads and cloud backups",
            "Contact your ISP if wired tests stay poor",
        ],
        "Jitter": [
            "Use Ethernet for calls and gaming",
            "Enable SQM / QoS if your router supports it",
            "Change Wi-Fi channel (prefer 5 GHz)",
        ],
        "Packet Loss": [
            "Test over Ethernet to isolate Wi-Fi issues",
            "Restart router and check cable seating",
            "Contact ISP if wired loss persists",
        ],
        "Download": [
            "Retest on Ethernet at different times of day",
            "Check subscribed plan speed with your ISP",
            "Reduce concurrent device load during tests",
        ],
        "Upload": [
            "Pause backups and camera uploads during important calls",
            "Verify plan upload entitlement with ISP",
            "Prefer wired connection for uploads",
        ],
        "DNS Lookup": [
            "Try a public DNS resolver (1.1.1.1 or 8.8.8.8)",
            "Flush local DNS cache and retest",
            "Disable VPN temporarily to compare",
        ],
        "HTTP Response": [
            "Retest after switching to Ethernet",
            "Check whether a VPN is adding delay",
            "Compare results at off-peak hours",
        ],
    }

    offline = {
        "analysis": " ".join(analysis_bits),
        "possible_reasons": reasons_map.get(issue, reasons_map["Ping"])[:4],
        "recommended_actions": actions_map.get(issue, actions_map["Ping"])[:4],
        "focus_metric": issue,
        "overall_rating": overall,
        "overall_score": score,
        "model_provider": "network-assistant-fallback-v1",
    }

    if not settings.ai_enabled:
        return offline

    user_prompt = f"""You are an AI Network Assistant for a home/broadband internet quality app.
Given this JSON context, return JSON with keys:
summary (string analysis), likely_causes (array), recommended_actions (array), severity (string).

Context:
{context}
"""
    try:
        result = call_chat_completion(
            settings=settings,
            system_prompt=SYSTEM_PROMPT,
            user_prompt=user_prompt,
        )
        return {
            "analysis": result.get("summary") or offline["analysis"],
            "possible_reasons": result.get("likely_causes") or offline["possible_reasons"],
            "recommended_actions": result.get("recommended_actions")
            or offline["recommended_actions"],
            "focus_metric": offline["focus_metric"],
            "overall_rating": overall,
            "overall_score": score,
            "model_provider": result.get("model_provider", f"openai:{settings.openai_model}"),
        }
    except LLMError:
        return offline
