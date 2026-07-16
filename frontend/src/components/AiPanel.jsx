import { formatDateTime, scenarioLabel } from "../utils/format";

/**
 * AI recommendations panel.
 * Displays persisted Generative AI output when available (Phase 6).
 * Until then, shows a deterministic operational synopsis from live metrics
 * so the dissertation demo has a complete NOC story.
 */
function buildSynopsis(metrics) {
  const rows = Array.isArray(metrics) ? metrics : [];
  if (rows.length === 0) {
    return {
      summary: "Waiting for live QoS telemetry from the simulator.",
      likely_causes: ["No measurements ingested yet"],
      recommended_actions: [
        "Start the backend API",
        "Run the simulator with --publish-api",
      ],
      provider: "rule-synopsis",
    };
  }

  const critical = rows.filter((r) => r.health_status === "critical");
  const degraded = rows.filter((r) => r.health_status === "degraded");
  const focus = critical[0] ?? degraded[0] ?? rows[0];

  if (critical.length === 0 && degraded.length === 0) {
    return {
      summary:
        "All monitored broadband nodes are operating within expected QoS thresholds.",
      likely_causes: ["Stable demand", "No active congestion or loss events"],
      recommended_actions: [
        "Continue routine monitoring",
        "Retain current capacity plan",
      ],
      provider: "rule-synopsis",
      stamped: focus.timestamp,
    };
  }

  const scenario = scenarioLabel(focus.scenario_label);
  return {
    summary: `${focus.node_code} (${focus.region}) is ${focus.health_status}. Current pattern resembles ${scenario.toLowerCase()}, with latency at ${focus.latency_ms} ms and packet loss at ${focus.packet_loss_pct}%.`,
    likely_causes: [
      focus.bandwidth_utilisation_pct >= 80
        ? "Elevated bandwidth utilisation on the access segment"
        : "Service quality deviation from baseline",
      focus.latency_ms >= 60
        ? "Increased path delay (congestion or backhaul)"
        : "Throughput or availability pressure",
      focus.packet_loss_pct >= 1
        ? "Packet loss consistent with queue overflow or link impairment"
        : "Jitter variation affecting real-time traffic",
    ],
    recommended_actions: [
      "Inspect access node and backhaul utilisation",
      "Correlate with peak-hour subscriber demand",
      "Prioritise capacity or traffic-engineering review for affected region",
    ],
    provider: "rule-synopsis (Phase 6 replaces with Generative AI)",
    stamped: focus.timestamp,
  };
}

export default function AiPanel({ metrics, recommendations }) {
  const saved = Array.isArray(recommendations) ? recommendations : [];
  const live = buildSynopsis(metrics);
  const primary =
    saved.length > 0
      ? {
          summary: saved[0].summary,
          likely_causes: String(saved[0].likely_causes)
            .split(/\n|;/)
            .map((s) => s.trim())
            .filter(Boolean),
          recommended_actions: String(saved[0].recommended_actions)
            .split(/\n|;/)
            .map((s) => s.trim())
            .filter(Boolean),
          provider: saved[0].model_provider,
          stamped: saved[0].created_at,
        }
      : live;

  return (
    <section className="panel ai-panel">
      <div className="panel-head">
        <h2>AI analysis</h2>
        <p>
          {saved.length > 0
            ? "Generative AI recommendation"
            : "Operational synopsis · Generative AI in Phase 6"}
        </p>
      </div>

      <p className="ai-summary">{primary.summary}</p>

      <div className="ai-columns">
        <div>
          <h3>Likely causes</h3>
          <ul>
            {primary.likely_causes.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </div>
        <div>
          <h3>Recommended actions</h3>
          <ul>
            {primary.recommended_actions.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </div>
      </div>

      <div className="ai-foot">
        <span>{primary.provider}</span>
        <span>{primary.stamped ? formatDateTime(primary.stamped) : "—"}</span>
      </div>
    </section>
  );
}
