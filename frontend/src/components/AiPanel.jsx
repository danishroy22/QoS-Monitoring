import { useState } from "react";
import { runAnalysis } from "../api/client";
import { formatDateTime, scenarioLabel } from "../utils/format";

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
      provider: "awaiting-data",
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
      provider: "live-synopsis",
      stamped: focus.timestamp,
      nodeCode: focus.node_code,
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
    provider: "live-synopsis",
    stamped: focus.timestamp,
    nodeCode: focus.node_code,
  };
}

function toViewModel(payload) {
  if (!payload) return null;
  if (payload.likely_causes && Array.isArray(payload.likely_causes)) {
    return {
      summary: payload.summary,
      likely_causes: payload.likely_causes,
      recommended_actions: payload.recommended_actions,
      provider: payload.model_provider,
      stamped: payload.created_at,
      severity: payload.severity,
      nodeCode: payload.node_code,
    };
  }
  return {
    summary: payload.summary,
    likely_causes: String(payload.likely_causes || "")
      .split(/\n|;/)
      .map((s) => s.replace(/^\-\s*/, "").trim())
      .filter(Boolean),
    recommended_actions: String(payload.recommended_actions || "")
      .split(/\n|;/)
      .map((s) => s.replace(/^\-\s*/, "").trim())
      .filter(Boolean),
    provider: payload.model_provider,
    stamped: payload.created_at,
  };
}

export default function AiPanel({
  metrics,
  recommendations,
  selectedNode,
  onAnalyzed,
}) {
  const [analysis, setAnalysis] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  const saved = Array.isArray(recommendations) ? recommendations : [];
  const live = buildSynopsis(metrics);
  const focusNode =
    selectedNode ||
    analysis?.nodeCode ||
    live.nodeCode ||
    (Array.isArray(metrics) && metrics[0]?.node_code) ||
    null;

  const primary =
    analysis ||
    (saved.length > 0 ? toViewModel(saved[0]) : null) ||
    live;

  const handleAnalyze = async () => {
    if (!focusNode) return;
    setBusy(true);
    setError(null);
    try {
      const result = await runAnalysis({ nodeCode: focusNode });
      setAnalysis(toViewModel(result));
      onAnalyzed?.(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="panel ai-panel">
      <div className="panel-head row">
        <div>
          <h2>AI analysis</h2>
          <p>
            {analysis || saved.length > 0
              ? "Generative AI / offline playbook recommendation"
              : "Live synopsis — click generate for full AI analysis"}
          </p>
        </div>
        <button
          type="button"
          className="action-btn"
          onClick={handleAnalyze}
          disabled={busy || !focusNode}
        >
          {busy ? "Analysing…" : `Analyse ${focusNode || "node"}`}
        </button>
      </div>

      {error && <p className="empty-copy error">{error}</p>}

      {primary.severity && (
        <p className={`severity-inline ${primary.severity}`}>
          Severity: {primary.severity}
        </p>
      )}

      <p className="ai-summary">{primary.summary}</p>

      <div className="ai-columns">
        <div>
          <h3>Likely causes</h3>
          <ul>
            {(primary.likely_causes || []).map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </div>
        <div>
          <h3>Recommended actions</h3>
          <ul>
            {(primary.recommended_actions || []).map((item) => (
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
