"""Deterministic offline AI fallback for demos without an LLM API key.

Purpose
-------
Guarantee dissertation demonstrations always produce telecom-relevant
explanations even when OpenAI (or compatible) credentials are unavailable.
"""

from __future__ import annotations

from typing import Any


ISSUE_PLAYBOOK: dict[str, dict[str, list[str] | str]] = {
    "congestion": {
        "summary": (
            "{node} in {region} shows congestion-like degradation: elevated "
            "utilisation ({util}%), latency ({latency} ms), and reduced effective throughput."
        ),
        "causes": [
            "Peak-hour subscriber demand exceeding access-segment capacity",
            "Backhaul or aggregation link approaching saturation",
            "Insufficient traffic engineering / QoS prioritisation for real-time flows",
        ],
        "actions": [
            "Check access node and backhaul utilisation counters for the affected region",
            "Correlate with busy-hour traffic reports and subscriber density",
            "Plan capacity upgrade or temporary traffic shaping for non-critical bulk traffic",
        ],
    },
    "high_latency": {
        "summary": (
            "{node} exhibits a high-latency pattern ({latency} ms) with comparatively "
            "moderate packet loss ({loss}%), consistent with routing or backhaul delay."
        ),
        "causes": [
            "Suboptimal routing or increased path length",
            "Backhaul delay or intermediate queueing",
            "Upstream transit congestion outside the access segment",
        ],
        "actions": [
            "Run path tracing / latency probes toward core and peering edges",
            "Review recent routing or policy changes",
            "Escalate to backhaul/core team if access utilisation is not elevated",
        ],
    },
    "packet_loss": {
        "summary": (
            "{node} is experiencing elevated packet loss ({loss}%) and jitter "
            "({jitter} ms), which typically impairs VoIP and interactive video."
        ),
        "causes": [
            "Queue overflow on a congested interface",
            "Noisy or impaired access/wireless link",
            "Faulty CPE, optics, or intermittent Layer-1 errors",
        ],
        "actions": [
            "Inspect interface error counters and optical/SNR statistics",
            "Test alternate CPE or segment isolation if loss is localised",
            "Reduce offered load while investigating physical-layer health",
        ],
    },
    "bandwidth_limit": {
        "summary": (
            "{node} throughput ({throughput} Mbps) remains well below the "
            "{tier} Mbps service tier despite sustained demand, suggesting capping or capacity limits."
        ),
        "causes": [
            "Service-tier policing or misconfigured rate limit",
            "Access capacity constraint below marketed tier",
            "Application or CPE bottleneck limiting achieved rate",
        ],
        "actions": [
            "Verify subscriber profile / rate-limit configuration against the service tier",
            "Run controlled speed tests from the affected segment",
            "Correct policing settings or schedule an access capacity review",
        ],
    },
    "outage": {
        "summary": (
            "{node} shows severe availability degradation ({availability}%), "
            "indicating a partial or full service outage condition."
        ),
        "causes": [
            "Access node, power, or transport failure",
            "Fibre cut or wireless backhaul loss",
            "Critical software/hardware fault on the serving equipment",
        ],
        "actions": [
            "Declare/confirm incident severity and open an NOC ticket",
            "Check power, optics, and upstream adjacency status immediately",
            "Invoke failover or field dispatch according to the outage runbook",
        ],
    },
    "performance_degradation": {
        "summary": (
            "{node} shows general QoS degradation (latency {latency} ms, loss {loss}%, "
            "utilisation {util}%) requiring operator investigation."
        ),
        "causes": [
            "Emerging congestion or intermittent impairment",
            "Deviation from the node baseline performance envelope",
            "Combined latency, loss, and utilisation pressure",
        ],
        "actions": [
            "Compare against baseline and neighbouring nodes",
            "Increase monitoring frequency for the next busy hour",
            "Escalate if metrics continue to breach warning thresholds",
        ],
    },
}


def _severity_from_context(context: dict[str, Any]) -> str:
    hint = str(context.get("severity_hint") or "").lower()
    if hint in {"low", "medium", "high", "critical"}:
        return hint
    availability = float(context.get("availability_pct") or 100)
    loss = float(context.get("packet_loss_pct") or 0)
    latency = float(context.get("latency_ms") or 0)
    if availability < 50 or loss >= 8:
        return "critical"
    if loss >= 3 or latency >= 120:
        return "high"
    if loss >= 1 or latency >= 60:
        return "medium"
    return "low"


def generate_fallback_analysis(context: dict[str, Any]) -> dict[str, Any]:
    """Return a structured analysis dict using telecom playbooks."""
    issue = str(context.get("suspected_issue") or "performance_degradation")
    playbook = ISSUE_PLAYBOOK.get(issue, ISSUE_PLAYBOOK["performance_degradation"])

    summary = str(playbook["summary"]).format(
        node=context.get("node_code", "Unknown node"),
        region=context.get("region", "unknown region"),
        util=context.get("bandwidth_utilisation_pct", "n/a"),
        latency=context.get("latency_ms", "n/a"),
        loss=context.get("packet_loss_pct", "n/a"),
        jitter=context.get("jitter_ms", "n/a"),
        throughput=context.get("throughput_mbps", "n/a"),
        tier=context.get("service_tier_mbps", "n/a"),
        availability=context.get("availability_pct", "n/a"),
    )

    return {
        "summary": summary,
        "likely_causes": list(playbook["causes"]),
        "recommended_actions": list(playbook["actions"]),
        "severity": _severity_from_context(context),
        "model_provider": "offline-fallback-v1",
    }
