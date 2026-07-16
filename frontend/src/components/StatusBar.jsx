import { healthTone } from "../utils/format";

export default function StatusBar({ metrics }) {
  const rows = Array.isArray(metrics) ? metrics : [];
  const counts = {
    healthy: rows.filter((r) => r.health_status === "healthy").length,
    degraded: rows.filter((r) => r.health_status === "degraded").length,
    critical: rows.filter((r) => r.health_status === "critical").length,
  };
  const avgLatency =
    rows.length === 0
      ? null
      : rows.reduce((sum, r) => sum + Number(r.latency_ms), 0) / rows.length;

  const items = [
    { label: "Nodes", value: rows.length, tone: "neutral" },
    { label: "Healthy", value: counts.healthy, tone: "ok" },
    { label: "Degraded", value: counts.degraded, tone: "warn" },
    { label: "Critical", value: counts.critical, tone: "crit" },
    {
      label: "Avg latency",
      value: avgLatency === null ? "—" : `${avgLatency.toFixed(1)} ms`,
      tone: healthTone(
        avgLatency === null
          ? "healthy"
          : avgLatency >= 120
            ? "critical"
            : avgLatency >= 60
              ? "degraded"
              : "healthy"
      ),
    },
  ];

  return (
    <section className="status-bar" aria-label="Network health summary">
      {items.map((item) => (
        <article key={item.label} className={`stat-chip ${item.tone}`}>
          <span className="stat-value">{item.value}</span>
          <span className="stat-label">{item.label}</span>
        </article>
      ))}
    </section>
  );
}
