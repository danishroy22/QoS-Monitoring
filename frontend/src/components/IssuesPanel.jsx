import { formatDateTime, scenarioLabel } from "../utils/format";

/**
 * Issues panel.
 * Shows ML anomalies when Phase 4 has written them. Until then, derives
 * operational issues from live health_status so the NOC is never empty
 * while the simulator is feeding degraded data.
 */
export default function IssuesPanel({ metrics, anomalies }) {
  const anomalyRows = Array.isArray(anomalies) ? anomalies : [];
  const derived = (Array.isArray(metrics) ? metrics : [])
    .filter((m) => m.health_status !== "healthy")
    .map((m) => ({
      id: `health-${m.node_code}`,
      node_code: m.node_code,
      severity: m.health_status === "critical" ? "critical" : "medium",
      suspected_issue: scenarioLabel(m.scenario_label),
      source: "health-rules",
      created_at: m.timestamp,
      detail: `Latency ${m.latency_ms} ms · Loss ${m.packet_loss_pct}% · Util ${m.bandwidth_utilisation_pct}%`,
    }));

  const rows =
    anomalyRows.length > 0
      ? anomalyRows.map((a) => ({
          id: a.id,
          node_code: a.node_code,
          severity: a.severity,
          suspected_issue: a.suspected_issue ?? "Anomaly detected",
          source: a.model_name,
          created_at: a.created_at,
          detail: `Score ${Number(a.anomaly_score).toFixed(3)}`,
        }))
      : derived;

  return (
    <section className="panel">
      <div className="panel-head">
        <h2>Detected issues</h2>
        <p>
          {anomalyRows.length > 0
            ? "Machine learning anomaly results"
            : "Rule-based health alerts (ML arrives in Phase 4)"}
        </p>
      </div>

      {rows.length === 0 ? (
        <p className="empty-copy">No active issues. Network appears healthy.</p>
      ) : (
        <ul className="issue-list">
          {rows.map((issue) => (
            <li key={issue.id} className={`issue-item ${issue.severity}`}>
              <div className="issue-top">
                <strong>{issue.node_code}</strong>
                <span className={`severity-pill ${issue.severity}`}>
                  {issue.severity}
                </span>
              </div>
              <p className="issue-title">{issue.suspected_issue}</p>
              <p className="issue-detail">{issue.detail}</p>
              <div className="issue-foot">
                <span>{issue.source}</span>
                <span>{formatDateTime(issue.created_at)}</span>
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
