import { formatNumber, healthTone, scenarioLabel } from "../utils/format";

function Metric({ label, value, unit }) {
  return (
    <div className="metric-cell">
      <span className="metric-label">{label}</span>
      <span className="metric-value">
        {value}
        {unit ? <span className="metric-unit">{unit}</span> : null}
      </span>
    </div>
  );
}

export default function NodeCard({ node, selected, onSelect }) {
  const tone = healthTone(node.health_status);

  return (
    <button
      type="button"
      className={`node-card ${tone} ${selected ? "selected" : ""}`}
      onClick={() => onSelect(node.node_code)}
      aria-pressed={selected}
    >
      <div className="node-card-top">
        <div>
          <h3 className="node-code">{node.node_code}</h3>
          <p className="node-region">
            {node.region} · {node.access_technology}
          </p>
        </div>
        <span className={`status-badge ${tone}`}>{node.health_status}</span>
      </div>

      <div className="node-metrics">
        <Metric label="Latency" value={formatNumber(node.latency_ms)} unit="ms" />
        <Metric label="Jitter" value={formatNumber(node.jitter_ms)} unit="ms" />
        <Metric
          label="Loss"
          value={formatNumber(node.packet_loss_pct, 2)}
          unit="%"
        />
        <Metric
          label="Throughput"
          value={formatNumber(node.throughput_mbps)}
          unit="Mbps"
        />
        <Metric
          label="Utilisation"
          value={formatNumber(node.bandwidth_utilisation_pct)}
          unit="%"
        />
        <Metric
          label="Availability"
          value={formatNumber(node.availability_pct)}
          unit="%"
        />
      </div>

      <div className="node-card-foot">
        <span className="scenario-tag">{scenarioLabel(node.scenario_label)}</span>
        <span className="tier-tag">{node.service_tier_mbps} Mbps tier</span>
      </div>
    </button>
  );
}
