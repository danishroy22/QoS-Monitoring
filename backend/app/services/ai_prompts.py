"""Prompt templates for Generative AI QoS analysis."""

from __future__ import annotations

from typing import Any


SYSTEM_PROMPT = """You are a senior telecommunications network operations engineer.
Analyse broadband QoS telemetry and produce concise, practical NOC guidance.

Rules:
- Use clear technical language suitable for an ISP Network Operations Centre.
- Base conclusions only on the provided metrics and context.
- Do not invent equipment IDs or alarms that are not implied by the data.
- Prefer actionable recommendations (capacity, backhaul, CPE, routing, QoS policy).
- Respond with valid JSON only, matching the schema exactly.
"""


RESPONSE_SCHEMA_HINT = """
Return JSON with this exact shape:
{
  "summary": "one short paragraph",
  "likely_causes": ["cause 1", "cause 2", "cause 3"],
  "recommended_actions": ["action 1", "action 2", "action 3"],
  "severity": "low|medium|high|critical"
}
"""


def build_user_prompt(context: dict[str, Any]) -> str:
    """Build the user message from structured network context."""
    history_lines = context.get("recent_history") or []
    history_block = "\n".join(f"- {line}" for line in history_lines) or "- (none)"

    return f"""Analyse this broadband QoS incident.

Node: {context.get("node_code")}
Region: {context.get("region")}
Access technology: {context.get("access_technology")}
Service tier: {context.get("service_tier_mbps")} Mbps
Suspected issue: {context.get("suspected_issue")}
Anomaly score: {context.get("anomaly_score")}
Severity hint: {context.get("severity_hint")}

Latest QoS sample:
- Timestamp: {context.get("timestamp")}
- Latency: {context.get("latency_ms")} ms
- Jitter: {context.get("jitter_ms")} ms
- Packet loss: {context.get("packet_loss_pct")} %
- Throughput: {context.get("throughput_mbps")} Mbps
- Bandwidth utilisation: {context.get("bandwidth_utilisation_pct")} %
- Signal quality: {context.get("signal_quality")}
- Availability: {context.get("availability_pct")} %
- Scenario label (simulator ground truth if present): {context.get("scenario_label")}

Recent history snapshots:
{history_block}

{RESPONSE_SCHEMA_HINT}
"""
